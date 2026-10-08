#!/usr/bin/env python3
"""Read-only: are all pods bound to one node healthy? Prints JSON, exit 0 = all healthy, 1 = not.

Used by the rolling-reboot role to notice that a node's pods are stuck (the Cilium endpoint stall).
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_health import pod_healthy, pod_state  # noqa: E402


def summarize(pods, node):
    mine = [p for p in pods if p["spec"].get("nodeName") == node and p["status"].get("phase") != "Succeeded"]
    bad = [{"pod": "%s/%s" % (p["metadata"]["namespace"], p["metadata"]["name"]), "state": pod_state(p)}
           for p in mine if not pod_healthy(p)]
    return {"node": node, "total": len(mine), "not_ready": bad, "all_ready": not bad}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kubeconfig", required=True)
    ap.add_argument("--node", required=True)
    args = ap.parse_args(argv)
    proc = subprocess.run(["kubectl", "--kubeconfig", args.kubeconfig, "get", "pods", "-A",
                           "--field-selector", "spec.nodeName=" + args.node, "-o", "json"],
                          capture_output=True, text=True, timeout=90)
    if proc.returncode != 0:
        print(json.dumps({"error": proc.stderr.strip()[-300:]}))
        return 2
    result = summarize(json.loads(proc.stdout)["items"], args.node)
    print(json.dumps(result))
    return 0 if result["all_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
