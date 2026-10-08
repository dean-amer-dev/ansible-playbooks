#!/usr/bin/env bash
# Read-only snapshot of one node's Cilium agent / cilium-envoy state, for diagnosing the post-reboot
# endpoint stall (INC-2026-10-05b). Never changes anything. Usage:
#   capture_cilium.sh <kubeconfig> <node> <out-dir>
# Each command is allowed to fail; whatever it printed is kept.
set -u
KC=$1; NODE=$2; OUT=$3
mkdir -p "$OUT"
k() { kubectl --kubeconfig "$KC" "$@"; }

AG=$(k -n kube-system get pods -l k8s-app=cilium --field-selector spec.nodeName="$NODE" -o name 2>/dev/null | head -1)
EN=$(k -n kube-system get pods -l k8s-app=cilium-envoy --field-selector spec.nodeName="$NODE" -o name 2>/dev/null | head -1)
{ echo "captured_utc=$(date -u +%FT%TZ)"; echo "node=$NODE"; echo "agent=$AG"; echo "envoy=$EN"; } > "$OUT/meta.txt"

k get pods -A -o wide --field-selector spec.nodeName="$NODE" > "$OUT/pods-on-node.txt" 2>&1
[ -n "$AG" ] && k -n kube-system logs "$AG" -c cilium-agent > "$OUT/agent.log" 2>&1
[ -n "$EN" ] && k -n kube-system logs "$EN" > "$OUT/envoy.log" 2>&1
if [ -n "$AG" ]; then
  k -n kube-system exec "$AG" -c cilium-agent -- cilium-dbg status --all-controllers > "$OUT/agent-status.txt" 2>&1
  k -n kube-system exec "$AG" -c cilium-agent -- cilium-dbg metrics list > "$OUT/agent-metrics.txt" 2>&1
  # The agent image has no curl; it ships `cilium-dbg envoy admin` for Envoy's admin interface
  for sub in metrics config listeners clusters; do
    k -n kube-system exec "$AG" -c cilium-agent -- cilium-dbg envoy admin "$sub" > "$OUT/envoy-admin-$sub.txt" 2>&1
  done
fi
echo "$OUT"
