import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import node_pods  # noqa: E402
import record_result  # noqa: E402


def pod(name, node, ready=True, phase="Running"):
    return {"metadata": {"namespace": "ns", "name": name}, "spec": {"nodeName": node},
            "status": {"phase": phase, "conditions": [{"type": "Ready", "status": "True" if ready else "False"}],
                       "containerStatuses": [{"ready": ready}]}}


class NodePodsTests(unittest.TestCase):
    def test_all_ready(self):
        r = node_pods.summarize([pod("a", "n1"), pod("b", "n2", ready=False)], "n1")
        self.assertTrue(r["all_ready"])
        self.assertEqual(r["total"], 1)

    def test_not_ready_listed_and_other_nodes_ignored(self):
        r = node_pods.summarize([pod("a", "n1"), pod("b", "n1", ready=False), pod("c", "n2", ready=False)], "n1")
        self.assertFalse(r["all_ready"])
        self.assertEqual([x["pod"] for x in r["not_ready"]], ["ns/b"])

    def test_succeeded_pods_do_not_count(self):
        r = node_pods.summarize([pod("job", "n1", ready=False, phase="Succeeded")], "n1")
        self.assertTrue(r["all_ready"])
        self.assertEqual(r["total"], 0)


class RecordResultTests(unittest.TestCase):
    def test_gap_parsing(self):
        g = record_result.parse_gap("1000.5 1225.7")
        self.assertEqual(g["gap_seconds"], 225.2)
        self.assertIsNone(record_result.parse_gap(""))
        self.assertIsNone(record_result.parse_gap("1000.5"))

    def test_spans_use_only_available_stamps(self):
        stamps = {"start": 0.0, "cordoned": 10.0, "drained": 40.0, "reboot_cmd": 50.0, "ssh_back": 300.0}
        rec = record_result.build("gmktec-2", stamps, "100.0 325.0", {"taint": ""}, "", False)
        self.assertEqual(rec["spans_seconds"]["drain"], 30.0)
        self.assertEqual(rec["spans_seconds"]["reboot command -> ssh back"], 250.0)
        self.assertEqual(rec["spans_seconds"]["SHUTDOWN GAP (last journal line -> kernel start)"], 225.0)
        self.assertNotIn("TOTAL start -> post gate ok", rec["spans_seconds"])
        self.assertFalse(rec["completed"])
        self.assertIn("STOPPED EARLY", record_result.render(rec))

    def test_completed_run(self):
        stamps = {"start": 0.0, "node_ready": 100.0, "cilium_ready": 460.0, "post_ok": 500.0, "uncordoned": 470.0}
        rec = record_result.build("gmktec-1", stamps, "", {}, "/tmp/x", True)
        self.assertEqual(rec["spans_seconds"]["node Ready -> Cilium Ready"], 360.0)
        self.assertEqual(rec["spans_seconds"]["TOTAL start -> post gate ok"], 500.0)
        self.assertTrue(rec["completed"])


if __name__ == "__main__":
    unittest.main()
