#!/usr/bin/env python3
"""Turn the timestamps collected during one node's rolling reboot into a readable summary and a
JSON record. Tolerates missing stamps (a failed run still records what it reached)."""
import argparse
import datetime
import json
import os
import sys

# (label, start stamp, end stamp)
SPANS = [
    ("drain", "cordoned", "drained"),
    ("taint wait", "tainted", "taint_settled"),
    ("reboot command -> ssh back", "reboot_cmd", "ssh_back"),
    ("ssh back -> node Ready", "ssh_back", "node_ready"),
    ("node Ready -> stall check", "node_ready", "stall_checked"),
    ("node Ready -> Cilium Ready", "node_ready", "cilium_ready"),
    ("uncordon -> post gate ok", "uncordoned", "post_ok"),
    ("TOTAL start -> post gate ok", "start", "post_ok"),
]


def parse_gap(text):
    """`<last log line epoch of previous boot> <first kernel line epoch of this boot>`."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None
    try:
        last, first = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    return {"last_log_prev_boot": last, "kernel_start": first, "gap_seconds": round(first - last, 1)}


def build(host, stamps, gap_text, options, capture_dir, reached_post_gate):
    spans = {}
    for label, a, b in SPANS:
        if a in stamps and b in stamps:
            spans[label] = round(stamps[b] - stamps[a], 1)
    gap = parse_gap(gap_text)
    if gap:
        spans["SHUTDOWN GAP (last journal line -> kernel start)"] = gap["gap_seconds"]
    return {
        "host": host,
        "finished_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completed": bool(reached_post_gate),
        "options": options,
        "capture_dir": capture_dir or None,
        "spans_seconds": spans,
        "stamps": stamps,
        "journal_gap": gap,
    }


def render(rec):
    lines = ["Rolling reboot timing for %s (%s)" % (rec["host"], "completed" if rec["completed"] else "STOPPED EARLY")]
    for label, secs in rec["spans_seconds"].items():
        lines.append("  %-52s %8.1f s  (%d m %02d s)" % (label, secs, secs // 60, secs % 60))
    if rec["options"]:
        lines.append("  options: %s" % json.dumps(rec["options"]))
    if rec["capture_dir"]:
        lines.append("  captures: %s" % rec["capture_dir"])
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", required=True)
    ap.add_argument("--stamps", default="{}", help="JSON object name -> epoch seconds")
    ap.add_argument("--gap", default="", help="'<last prev-boot log epoch> <first kernel epoch>'")
    ap.add_argument("--options", default="{}")
    ap.add_argument("--capture-dir", default="")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    stamps = json.loads(args.stamps)
    rec = build(args.host, stamps, args.gap, json.loads(args.options), args.capture_dir, "post_ok" in stamps)
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, "%s-%s.json" % (args.host, rec["finished_utc"].replace(":", "")))
    with open(path, "w") as f:
        json.dump(rec, f, indent=2)
    print(render(rec))
    print("  record: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
