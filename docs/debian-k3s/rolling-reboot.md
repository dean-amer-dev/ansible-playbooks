# debian-k3s: rolling reboot (health-gated, one node at a time)

Playbook `playbooks/infrastructure/rolling-reboot-debian-k3s.yml`, role `roles/k3s-rolling-reboot`.
Written after the 2026-10-05 reboots (INC-2026-10-05b) so reboots are a repeatable, gated procedure
instead of someone watching a terminal.

## What it does, per node, strictly one at a time
1. **Gate (pre)** - refuses unless ALL hold (read-only, `files/cluster_health.py`):
   - every control-plane node is Ready and none is cordoned (so nothing else is mid-maintenance)
   - etcd and the API report ready
   - every pod bound to a control-plane node, or not yet scheduled, is healthy (Pending/Unknown/
     crash-looping pods block; finished Job pods are fine)
   - every replicated service (Postgres, MongoDB, CouchDB, Technitium, CoreDNS) has ALL replicas
     healthy AND at least `rolling_reboot_min_healthy_replicas` (2) healthy replicas on the OTHER nodes
   - Postgres: cluster in "healthy state", all instances ready, no switchover in progress
   - CouchDB: every pod sees all 3 nodes and every database has the same doc_count on every pod
   - MongoDB resource Running; every ArgoCD Application Healthy
   Desktop/GPU agents (archlinux, murderbot) do not count: they say nothing about whether a reboot is safe.
2. If the Postgres primary is on this node: `kubectl cnpg promote` a healthy replica elsewhere,
   wait for a healthy cluster, re-run the gate.
3. Cordon, then `kubectl drain --ignore-daemonsets --delete-emptydir-data --force` (PodDisruptionBudgets apply).
4. Reboot (`ansible.builtin.reboot`, waits for ssh).
5. Wait for the node Ready, then for its Cilium agent and cilium-envoy to be Ready (the node stays
   cordoned until then, so pods start into a working CNI; Cilium can take ~5.5 min, see the incident).
6. Uncordon, then **gate (post)**: retried for up to 30 minutes until everything is healthy again and
   every replica has caught up. Then a 60 s settle pause, then the next node.

The first failure anywhere stops the whole run (`any_errors_fatal`, `serial: 1`). The node that
failed is left exactly as it was (cordoned/drained if it got that far) for a human to look at. Nothing
is rolled back automatically.

## Running it
Needs Alex's permission for every run. Prerequisites on the control host: `kubectl`, `~/.kube/dean.yaml`
(API VIP), `kubectl-cnpg` (pinned 1.30.1 in `~/.local/bin`; only used if the primary is on the node).
```
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/rolling-reboot-debian-k3s.yml \
    -e rolling_reboot_confirm=yes            # add --limit gmktec-2 for a single node
```
A run without `-e rolling_reboot_confirm=yes` refuses. `--check` is not supported.

To see what the gate says right now without any risk (read-only, exit code 1 = not healthy):
```
python3 roles/k3s-rolling-reboot/files/cluster_health.py --kubeconfig ~/.kube/dean.yaml \
  --phase pre --target gmktec-1 --services '<rolling_reboot_replica_services as JSON>'
```
Unit tests: `python3 -m unittest roles/k3s-rolling-reboot/files/test_cluster_health.py`.

## Known limits
- The gate cannot see data-level problems it is not told about (for example Postgres replication
  lag on a replica that is Ready, MongoDB member state beyond the operator's phase).
- A node taking ~4-6 minutes to reach its kernel is currently normal here (the shutdown delay is an
  open issue in INC-2026-10-05b); the reboot timeout allows 20 minutes.
- Local-volume pods (pg, couchdb, mongodb, technitium replica on the node) stay Pending while the node is
  down; that is why every service must be 3/3 before the reboot starts.
