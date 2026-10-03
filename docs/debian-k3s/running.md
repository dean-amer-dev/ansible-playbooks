# debian-k3s — running

Baseline + k3s HA server (embedded etcd) for the GMKtec Debian 13 boxes (inventory group
`debian_k3s`: `gmktec-1`, `gmktec-2`, `gmktec-3` — the Infrastructure 2.0 cluster, deliberately
**not** in `[k3s]`, which is the legacy Pi cluster with its own group_vars). Task order: ssh keys
→ packages/sysctls/time sync → remove GUI + disable auto-sleep → performance power mode → LVM
volume group for kube volumes → NIC rename to `lan0` → preflight readiness checks → k3s server →
Cilium CNI → CoreDNS → kube-vip control-plane VIP. Cilium, CoreDNS, and kube-vip are applied once,
from whichever host is `debian_k3s_init_host` (defaults to the first inventory host), against its
local kubeconfig — not by every node in the group.

## Invocation

The only secret input is `BWS_ACCESS_TOKEN` in the environment — never on the command line, never
sent to the target hosts (read on the control node only):

```bash
export BWS_ACCESS_TOKEN="$(cat /home/alex/claude/bws-ro-token)"

# Full run (all 3 GMKtec boxes, one at a time — the play is serial: 1)
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-debian-k3s.yml

# Single host
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-debian-k3s.yml --limit gmktec-1

# Baseline only, skip k3s
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-debian-k3s.yml --skip-tags k3s

# Read-only readiness check
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-debian-k3s.yml --tags preflight

# Dry run
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-debian-k3s.yml --check --diff
```

Tags: `ssh_keys packages headless power storage longhorn network preflight k3s cilium coredns kube-vip`.

**SSH access only** (installs alex's key + optional passwordless sudo, nothing else):

```bash
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/debian-k3s-access.yml
```

## First-run prompts

`setup-debian-k3s.yml` and `debian-k3s-access.yml` both import
`debian-k3s-ssh-bootstrap.yml` first. On a box that doesn't have alex's key yet, this prompts
**once** (hidden input) for alex's SSH password, installs the BWS-sourced key with
`ssh-copy-id`, and reuses that same password for sudo if `sudo -n` doesn't work. If sudo isn't
installed at all, it prompts for **root's** password instead and escalates via `su`. A host that
already has the key installed and passwordless sudo working prompts for nothing.

## What a clean run looks like

- Re-running with no drift: `changed=0` across the board except the always-`changed` operational
  tasks (report/debug tasks, and preflight's read-only checks which never claim `changed`).
- The **NIC rename to `lan0`** and the **`/home` LV migration** each trigger exactly one
  Ansible-driven reboot **the first time** they're needed, then converge to no-op on every
  subsequent run — see `recovery.md` for what that reboot does and how to tell it's mid-flight.
- `preflight` reports `READY for k3s` for every targeted host before `k3s.yml` runs.
- After `k3s.yml`, `k3s kubectl get --raw '/readyz?verbose'` includes `[+]etcd ok`.
- Nodes stay `NotReady` until Cilium installs (flannel is disabled) — expected on a from-scratch
  bootstrap, not a fault.

## `--limit` and ordering

The play is `serial: 1` (one host at a time) with no explicit health gate task, but everything
downstream (join-token read, Cilium/CoreDNS/kube-vip apply) is gated on `debian_k3s_init_host`
being reachable and already having live server data, so **run the init host before any joiner**
on a from-scratch bootstrap. On a rebuild of a single existing node, `--limit <host>` is safe on
its own.
