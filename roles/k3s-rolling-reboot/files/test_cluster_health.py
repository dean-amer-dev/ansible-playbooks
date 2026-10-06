import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import cluster_health as ch  # noqa: E402

SERVICES = [
    {"name": "postgres", "namespace": "postgres", "selector": "cnpg.io/cluster=pg", "replicas": 3},
    {"name": "couchdb", "namespace": "couchdb", "selector": "app=couchdb", "replicas": 3},
]
NODES = ["gmktec-1", "gmktec-2", "gmktec-3"]


def node(name, ready=True, cordoned=False, core=True, taints=None):
    labels = {"node-role.kubernetes.io/control-plane": "true"} if core else {}
    return {"metadata": {"name": name, "labels": labels}, "spec": {"unschedulable": cordoned, "taints": taints or []},
            "status": {"conditions": [{"type": "Ready", "status": "True" if ready else "Unknown"}]}}


def pod(ns, name, node_name, labels, ready=True, phase="Running"):
    return {"metadata": {"namespace": ns, "name": name, "labels": labels},
            "spec": {"nodeName": node_name},
            "status": {"phase": phase,
                       "conditions": [{"type": "Ready", "status": "True" if ready else "False"}],
                       "containerStatuses": [{"ready": ready}]}}


def healthy_snapshot():
    pods = []
    for i, n in enumerate(NODES, 1):
        pods.append(pod("postgres", "pg-%d" % i, n, {"cnpg.io/cluster": "pg"}))
        pods.append(pod("couchdb", "couchdb-couchdb-%d" % (i - 1), n, {"app": "couchdb"}))
    couch = {"couchdb-couchdb-%d" % i: {"dbs": {"obsidian-dean": 100}, "cluster_nodes": 3, "all_nodes": 3} for i in range(3)}
    return {
        "nodes": [node(n) for n in NODES],
        "pods": pods,
        "readyz": "[+]etcd ok\n[+]etcd-readiness ok\nreadyz check passed",
        "apps": [{"metadata": {"name": "a"}, "status": {"health": {"status": "Healthy"}}}],
        "mongo": [{"metadata": {"name": "unifi-mongodb"}, "status": {"phase": "Running"}}],
        "cnpg": {"spec": {"instances": 3},
                 "status": {"phase": "Cluster in healthy state", "readyInstances": 3,
                            "currentPrimary": "pg-2", "targetPrimary": "pg-2"}},
        "couch": couch,
    }


def run(snap, phase="pre", target="gmktec-1", min_elsewhere=2):
    return ch.evaluate(snap, phase, target, min_elsewhere, SERVICES, [], 3)


class GateTests(unittest.TestCase):
    def test_healthy_cluster_passes_pre_and_post(self):
        self.assertEqual(run(healthy_snapshot())[0], [])
        self.assertEqual(run(healthy_snapshot(), "post", "")[0], [])

    def test_cordoned_node_blocks(self):
        s = healthy_snapshot()
        s["nodes"][1] = node("gmktec-2", cordoned=True)
        self.assertTrue(any("cordoned" in f for f in run(s)[0]))

    def test_node_not_ready_blocks(self):
        s = healthy_snapshot()
        s["nodes"][2] = node("gmktec-3", ready=False)
        self.assertTrue(any("not Ready" in f for f in run(s)[0]))

    def test_unhealthy_pod_anywhere_blocks(self):
        s = healthy_snapshot()
        s["pods"].append(pod("tdarr", "tdarr-x", "gmktec-3", {}, ready=False, phase="Pending"))
        self.assertTrue(any("tdarr-x" in f for f in run(s)[0]))

    def test_only_one_replica_elsewhere_blocks_pre(self):
        s = healthy_snapshot()
        # couchdb pod on gmktec-3 not ready: target gmktec-1 would leave only 1 healthy elsewhere
        s["pods"] = [p if p["metadata"]["name"] != "couchdb-couchdb-2" else
                     pod("couchdb", "couchdb-couchdb-2", "gmktec-3", {"app": "couchdb"}, ready=False)
                     for p in s["pods"]]
        failures, _ = run(s)
        self.assertTrue(any("couchdb" in f and "need 2" in f for f in failures))

    def test_postgres_primary_on_target_is_reported_with_candidates(self):
        failures, info = run(healthy_snapshot(), target="gmktec-2")
        self.assertEqual(failures, [])
        self.assertEqual(info["postgres_primary_node"], "gmktec-2")
        self.assertEqual(info["postgres_switchover_candidates"], ["pg-1", "pg-3"])

    def test_switchover_in_progress_blocks(self):
        s = healthy_snapshot()
        s["cnpg"]["status"]["targetPrimary"] = "pg-3"
        self.assertTrue(any("switchover in progress" in f for f in run(s)[0]))

    def test_couchdb_doc_count_mismatch_blocks(self):
        s = healthy_snapshot()
        s["couch"]["couchdb-couchdb-1"]["dbs"]["obsidian-dean"] = 99
        self.assertTrue(any("doc_count differs" in f for f in run(s)[0]))

    def test_etcd_not_ready_blocks(self):
        s = healthy_snapshot()
        s["readyz"] = "[-]etcd failed\n"
        self.assertTrue(any("etcd" in f for f in run(s)[0]))

    def test_argocd_progressing_blocks(self):
        s = healthy_snapshot()
        s["apps"][0]["status"]["health"]["status"] = "Progressing"
        self.assertTrue(any("argocd app a" in f for f in run(s)[0]))

    def test_mongo_not_running_blocks(self):
        s = healthy_snapshot()
        s["mongo"][0]["status"]["phase"] = "Pending"
        self.assertTrue(any("mongodb" in f for f in run(s)[0]))

    def test_desktop_agent_down_does_not_block(self):
        s = healthy_snapshot()
        s["nodes"].append(node("archlinux", ready=False, core=False))
        s["pods"].append(pod("kube-system", "cilium-arch", "archlinux", {}, ready=False))
        self.assertEqual(run(s)[0], [])

    def test_pending_unscheduled_pod_blocks(self):
        s = healthy_snapshot()
        p = pod("argocd", "redis-0", None, {}, ready=False, phase="Pending")
        p["spec"] = {}
        s["pods"].append(p)
        self.assertTrue(any("redis-0" in f for f in run(s)[0]))

    def test_running_but_unready_pod_message_is_specific(self):
        s = healthy_snapshot()
        p = pod("mcp", "obsidian-x", "gmktec-1", {}, ready=False)
        p["status"]["containerStatuses"] = [{"ready": False, "restartCount": 5,
                                              "state": {"waiting": {"reason": "CrashLoopBackOff"}}}]
        failures = run(s)[0] if False else run({**s, "pods": s["pods"] + [p]})[0]
        msg = [f for f in failures if "obsidian-x" in f][0]
        self.assertIn("0/1 containers ready", msg)
        self.assertIn("CrashLoopBackOff", msg)
        self.assertIn("5 restarts", msg)

    def test_leftover_diagnostic_taint_blocks(self):
        s = healthy_snapshot()
        s["nodes"][0] = node("gmktec-1", taints=[{"key": "bisect", "value": "1", "effect": "NoExecute"}])
        self.assertTrue(any("diagnostic taint" in f for f in run(s)[0]))

    def test_other_taints_are_fine(self):
        s = healthy_snapshot()
        s["nodes"][0] = node("gmktec-1", taints=[{"key": "node-role.kubernetes.io/control-plane", "effect": "NoSchedule"}])
        self.assertEqual(run(s)[0], [])

    def test_succeeded_job_pods_are_fine(self):
        s = healthy_snapshot()
        s["pods"].append(pod("postgres", "pg-backup-1", "gmktec-1", {}, ready=False, phase="Succeeded"))
        self.assertEqual(run(s)[0], [])

    def test_post_requires_all_replicas(self):
        s = healthy_snapshot()
        s["pods"] = [p for p in s["pods"] if p["metadata"]["name"] != "pg-1"]
        self.assertTrue(any("postgres: 2 of 3" in f for f in run(s, "post", "")[0]))


if __name__ == "__main__":
    unittest.main()
