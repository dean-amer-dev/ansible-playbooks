#!/usr/bin/env python3
"""Read-only cluster health gate for rolling reboots of the k3s servers.

Never changes anything: it only runs `kubectl get` and (for CouchDB) a read-only
`kubectl exec ... curl`. Prints one JSON document and exits 0 when the cluster is healthy,
1 when it is not, 2 on a usage or tooling error.

  --phase pre   the node named by --target is about to be taken down: every check must pass AND
                every replicated service must keep at least --min-elsewhere healthy replicas on
                OTHER nodes (so two stay up while the target is down)
  --phase post  the cluster must be fully healthy again (all replicas, all nodes schedulable)
"""
import argparse
import json
import re
import subprocess
import sys


def kubectl(kubeconfig, *args, timeout=90):
    proc = subprocess.run(
        ["kubectl", "--kubeconfig", kubeconfig, *args],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError("kubectl %s failed: %s" % (" ".join(args[:4]), proc.stderr.strip()[-300:]))
    return proc.stdout


def kubectl_json(kubeconfig, *args):
    return json.loads(kubectl(kubeconfig, *args, "-o", "json"))


CORE_LABEL = "node-role.kubernetes.io/control-plane"


def node_ready(node):
    return any(c["type"] == "Ready" and c["status"] == "True" for c in node["status"].get("conditions", []))


def pod_ready(pod):
    if pod["status"].get("phase") != "Running" or pod["metadata"].get("deletionTimestamp"):
        return False
    return any(c["type"] == "Ready" and c["status"] == "True" for c in pod["status"].get("conditions", []))


def pod_state(pod):
    """Short human description of why a pod is not healthy."""
    phase = pod["status"].get("phase", "?")
    if pod["metadata"].get("deletionTimestamp"):
        return "Terminating"
    statuses = pod["status"].get("containerStatuses") or []
    if phase == "Running" and statuses:
        ready = sum(1 for c in statuses if c.get("ready"))
        waiting = next((c["state"]["waiting"].get("reason") for c in statuses if c.get("state", {}).get("waiting")), None)
        restarts = sum(c.get("restartCount", 0) for c in statuses)
        return "Running, %d/%d containers ready, %s, %d restarts" % (ready, len(statuses), waiting or "not ready", restarts)
    return phase


def pod_healthy(pod):
    """Healthy = finished OK (Job pod), or running with every container ready and not terminating."""
    phase = pod["status"].get("phase")
    if phase == "Succeeded":
        return True
    if phase != "Running" or pod["metadata"].get("deletionTimestamp"):
        return False
    statuses = pod["status"].get("containerStatuses") or []
    return bool(statuses) and all(s.get("ready") for s in statuses)


def matches(labels, selector):
    want = dict(part.split("=", 1) for part in selector.split(","))
    return all(labels.get(k) == v for k, v in want.items())


def evaluate(snap, phase, target, min_elsewhere, services, ignore_pod_regex, expect_nodes):
    """Pure function over a snapshot of the cluster; returns (failures, info)."""
    failures, info = [], {}

    # --- nodes: only the control-plane (GMKtec) servers count. Desktop/GPU agents such as
    # archlinux or murderbot come and go and say nothing about whether a reboot is safe.
    all_nodes = snap["nodes"]
    nodes = [n for n in all_nodes if CORE_LABEL in n["metadata"].get("labels", {})] or all_nodes
    core = {n["metadata"]["name"] for n in nodes}
    if len(nodes) < expect_nodes:
        failures.append("only %d control-plane nodes registered, expected at least %d" % (len(nodes), expect_nodes))
    for n in nodes:
        name = n["metadata"]["name"]
        if not node_ready(n):
            failures.append("node %s is not Ready" % name)
        if n["spec"].get("unschedulable"):
            failures.append("node %s is cordoned (another maintenance may be in progress)" % name)
    if phase == "pre" and target not in core:
        failures.append("target node %s is not a control-plane node in this cluster" % target)

    # --- etcd / API
    readyz = snap["readyz"]
    for needle in ("[+]etcd ok", "[+]etcd-readiness ok"):
        if needle not in readyz:
            failures.append("API readyz does not report '%s'" % needle)

    # --- every pod bound to a control-plane node, or not yet scheduled
    ignore = [re.compile(r) for r in ignore_pod_regex]
    for p in snap["pods"]:
        full = "%s/%s" % (p["metadata"]["namespace"], p["metadata"]["name"])
        bound = p["spec"].get("nodeName")
        if bound and bound not in core:      # pods on desktop/GPU agents do not gate a reboot
            continue
        if any(r.search(full) for r in ignore):
            continue
        if not pod_healthy(p):
            failures.append("pod %s is not healthy (%s)" % (full, pod_state(p)))

    # --- replicated services: need every replica healthy, and min_elsewhere on other nodes
    for svc in services:
        pods = [p for p in snap["pods"]
                if p["metadata"]["namespace"] == svc["namespace"]
                and matches(p["metadata"].get("labels", {}), svc["selector"])]
        ready = [p for p in pods if pod_ready(p)]
        elsewhere = [p for p in ready if p["spec"].get("nodeName") != target]
        info["%s_ready" % svc["name"]] = "%d/%d" % (len(ready), svc["replicas"])
        if len(ready) < svc["replicas"]:
            failures.append("%s: %d of %d replicas healthy" % (svc["name"], len(ready), svc["replicas"]))
        if phase == "pre" and len(elsewhere) < min_elsewhere:
            failures.append("%s: only %d healthy replicas would remain on other nodes, need %d"
                            % (svc["name"], len(elsewhere), min_elsewhere))

    # --- CloudNativePG
    cnpg = snap.get("cnpg")
    if cnpg is None:
        failures.append("CloudNativePG cluster 'pg' not found")
    else:
        st = cnpg.get("status", {})
        if st.get("phase") != "Cluster in healthy state":
            failures.append("postgres cluster phase is '%s'" % st.get("phase"))
        if st.get("readyInstances") != cnpg["spec"]["instances"]:
            failures.append("postgres readyInstances %s of %s" % (st.get("readyInstances"), cnpg["spec"]["instances"]))
        if st.get("currentPrimary") != st.get("targetPrimary"):
            failures.append("postgres switchover in progress (%s -> %s)" % (st.get("currentPrimary"), st.get("targetPrimary")))
        primary = st.get("currentPrimary")
        pod_node = {p["metadata"]["name"]: p["spec"].get("nodeName") for p in snap["pods"]
                    if p["metadata"]["namespace"] == "postgres"}
        info["postgres_primary"] = primary
        info["postgres_primary_node"] = pod_node.get(primary)
        cands = sorted(name for name, node in pod_node.items()
                       if name != primary and node != target
                       and any(pod_ready(p) and p["metadata"]["name"] == name for p in snap["pods"]
                               if p["metadata"]["namespace"] == "postgres"))
        info["postgres_switchover_candidates"] = cands

    # --- MongoDB community operator
    for m in snap.get("mongo", []):
        if m.get("status", {}).get("phase") != "Running":
            failures.append("mongodb %s phase is %s" % (m["metadata"]["name"], m.get("status", {}).get("phase")))
    if not snap.get("mongo"):
        failures.append("no MongoDBCommunity resource found")

    # --- CouchDB: every pod must agree on membership and on each database's doc_count
    couch = snap.get("couch", {})
    counts = {}
    for pod, data in couch.items():
        if data.get("error"):
            failures.append("couchdb %s: %s" % (pod, data["error"]))
            continue
        if data["cluster_nodes"] < 3 or data["all_nodes"] < 3:
            failures.append("couchdb %s sees %d/%d cluster nodes" % (pod, data["all_nodes"], data["cluster_nodes"]))
        for db, n in data["dbs"].items():
            counts.setdefault(db, set()).add(n)
    for db, vals in counts.items():
        if len(vals) > 1:
            failures.append("couchdb %s doc_count differs between pods: %s" % (db, sorted(vals)))

    # --- ArgoCD applications
    for a in snap.get("apps", []):
        health = a.get("status", {}).get("health", {}).get("status")
        if health != "Healthy":
            failures.append("argocd app %s is %s" % (a["metadata"]["name"], health))

    return failures, info


def collect(kubeconfig, services):
    snap = {
        "nodes": kubectl_json(kubeconfig, "get", "nodes")["items"],
        "pods": kubectl_json(kubeconfig, "get", "pods", "-A")["items"],
        "readyz": kubectl(kubeconfig, "get", "--raw=/readyz?verbose"),
        "apps": kubectl_json(kubeconfig, "-n", "argocd", "get", "applications.argoproj.io")["items"],
        "mongo": kubectl_json(kubeconfig, "get", "mongodbcommunity", "-A")["items"],
    }
    try:
        snap["cnpg"] = kubectl_json(kubeconfig, "-n", "postgres", "get", "clusters.postgresql.cnpg.io", "pg")
    except RuntimeError:
        snap["cnpg"] = None
    snap["couch"] = {}
    for svc in services:
        if svc["name"] != "couchdb":
            continue
        for p in snap["pods"]:
            if p["metadata"]["namespace"] == svc["namespace"] and matches(p["metadata"].get("labels", {}), svc["selector"]) and pod_ready(p):
                snap["couch"][p["metadata"]["name"]] = couch_state(kubeconfig, svc["namespace"], p["metadata"]["name"])
    return snap


COUCH_CMD = (
    'A="-s -u $COUCHDB_USER:$COUCHDB_PASSWORD"; '
    'echo MEMBERSHIP $(curl $A localhost:5984/_membership | tr -d "\\n"); '
    'for d in $(curl $A localhost:5984/_all_dbs | tr -d "[]\\"" | tr "," " "); do '
    'case $d in _*) ;; *) echo DB $d $(curl $A localhost:5984/$d | tr "," "\\n" | grep \'"doc_count"\' | tr -dc 0-9);; esac; done'
)


def couch_state(kubeconfig, namespace, pod):
    try:
        out = kubectl(kubeconfig, "-n", namespace, "exec", pod, "-c", "couchdb", "--", "sh", "-c", COUCH_CMD, timeout=60)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        return {"error": "exec failed: %s" % exc}
    state = {"dbs": {}, "cluster_nodes": 0, "all_nodes": 0}
    for line in out.splitlines():
        if line.startswith("MEMBERSHIP "):
            try:
                m = json.loads(line[len("MEMBERSHIP "):])
                state["cluster_nodes"], state["all_nodes"] = len(m["cluster_nodes"]), len(m["all_nodes"])
            except (ValueError, KeyError):
                return {"error": "unreadable _membership"}
        elif line.startswith("DB "):
            _, db, n = line.split()
            state["dbs"][db] = int(n)
    return state


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kubeconfig", required=True)
    ap.add_argument("--phase", choices=["pre", "post"], required=True)
    ap.add_argument("--target", default="")
    ap.add_argument("--min-elsewhere", type=int, default=2)
    ap.add_argument("--expect-nodes", type=int, default=3)
    ap.add_argument("--services", required=True, help="JSON list of {name,namespace,selector,replicas}")
    ap.add_argument("--ignore-pods", default="[]", help="JSON list of regexes matched against namespace/name; those pods are not counted")
    args = ap.parse_args(argv)
    if args.phase == "pre" and not args.target:
        ap.error("--target is required for --phase pre")
    services = json.loads(args.services)
    try:
        snap = collect(args.kubeconfig, services)
    except (RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    failures, info = evaluate(snap, args.phase, args.target, args.min_elsewhere, services,
                              json.loads(args.ignore_pods), args.expect_nodes)
    print(json.dumps({"ok": not failures, "phase": args.phase, "target": args.target,
                      "failures": failures, "info": info}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
