# ansible-playbooks

Ansible playbooks for provisioning and managing:

- a legacy high-availability k3s cluster on Raspberry Pi nodes (`[k3s]` inventory group),
- the Infrastructure 2.0 k3s cluster on GMKtec Debian 13 boxes (`[debian_k3s]` group — see
  [`docs/debian-k3s/`](docs/debian-k3s/running.md)),
- the `archlinux`/CachyOS gaming workstation (`[cachyos_workstations]` group — see
  [`docs/README.md`](docs/README.md) for its 17 roles),
- and Komodo Periphery / Docker hosts (Mac Mini, murderbot, archlinux).

**Role-by-role how-to-run and how-to-recover docs live in [`docs/`](docs/README.md).** This file
covers only what's shared across the whole repo: inventory, secrets, and control-machine setup.

## Cluster Inventory

| Host | Role | IP | Notes |
|------|------|----|-------|
| rpi5-0 / rpi5-1 / rpi4-0 | Legacy k3s controllers | 10.100.20.10 / .11 / .12 | rpi5-1 is preferred restore leader; rpi4-0 has 4GB RAM, tight memory |
| gmktec-1 / gmktec-2 / gmktec-3 | Infrastructure 2.0 k3s servers | 10.100.20.20 / .21 / .22 | Debian 13, embedded etcd — see `docs/debian-k3s/` |
| murderbot | GPU host (bare metal Docker) | 10.100.20.19 | Not part of k3s |
| archlinux | CachyOS workstation + k3s agent + GPU/Docker host | 10.100.20.25 | Joins the legacy k3s cluster as agent |
| lemurpro | Workstation (Komodo); not a k3s node | — (Tailscale) | `ansible_host` is a Tailscale IP; ufw denies inbound on LAN |
| mac-mini-m4 | Docker host (OrbStack) | 10.100.20.18 | Not part of k3s |

All nodes are accessed as user `alex` with SSH key `~/.ssh/alex_id_ed25519` (`inventory/inventory.ini`
`[all:vars]`). Inventory groups are documented inline in `inventory/inventory.ini`.

## Secrets Policy

**All secrets MUST live in Bitwarden Secrets Manager (BWS). No exceptions.** The only credential
you ever pass to Ansible is a BWS machine-account access token:

```bash
export BWS_ACCESS_TOKEN="$(cat /home/alex/claude/bws-ro-token)"
# or, where a playbook takes it as an extra-var instead of an env var:
ansible-playbook -i inventory/inventory.ini all.yml -e bws_access_token=<TOKEN>
```

Secret UUIDs live in `group_vars/*.yml` (`bws_secrets` dicts, or per-role `*_bws_*_id` vars) — they
are identifiers, not secrets, safe to commit. Never pass a cluster token, password, or PAT via
`-e` or inventory directly.

## Prerequisites

- Ansible on the control machine (Arch: `sudo pacman -S ansible python openssh unzip curl`;
  elsewhere: your distro's `ansible`/`ansible-core`).
- SSH access to remote nodes (key-based, `~/.ssh/alex_id_ed25519`).
- A BWS machine-account access token.
- Collections: `ansible-galaxy collection install -r requirements.yml`.
- **`unzip`/`curl`** are needed only if the `bws` CLI isn't already on `PATH` — `fetch-secrets.yml`
  downloads and installs it automatically otherwise.

### Control machine: Arch Linux (`localhost`)

Most playbooks are written assuming `ansible-playbook` runs **on the Arch control box** — the
first play is almost always `localhost` (fetches BWS secrets there, never sends the token over
SSH). For `archlinux` itself as a managed host: keep its real LAN `ansible_host` (not `127.0.0.1`),
set `ansible_connection=local` and `archlinux_ip` on its inventory line so k3s `node-ip` stays
correct. To drive `archlinux` from a *different* control machine over SSH instead, remove
`ansible_connection=local` from its inventory line.

## Directory Structure

```
ansible-playbooks/
├── all.yml                 Master playbook (full legacy-cluster setup)
├── requirements.yml        Ansible collection dependencies
├── inventory/inventory.ini Node inventory (groups + host vars)
├── group_vars/              Group-level variables (no secrets — BWS UUIDs only)
├── tasks/                   Shared cross-role tasks (health gates, confirmation prompts, etc.)
├── roles/                   One role per concern — see docs/README.md for all 18
├── playbooks/
│   ├── infrastructure/      Host/cluster provisioning and recovery — see below
│   └── applications/        ArgoCD bootstrap, Z2M backup/restore
└── docs/                     Per-role running/recovery docs — see docs/README.md
```

## Playbook quick reference

Role-driven playbooks (`setup-cachyos.yml`, `setup-debian-k3s.yml`, `*-k3s-agent.yml`,
`debian-k3s-access.yml`) are documented in their role's `docs/<role>/running.md`. The rest:

| Playbook | What it does |
|----------|---------------|
| `fetch-secrets.yml` | Fetches BWS secrets on localhost; imported by most other playbooks. |
| `setup-rpi.yml` | Raspberry Pi OS prep for the legacy k3s controllers. |
| `k3s-controller.yml` / `k3s-agent.yml` | Install k3s server/agent on the legacy Pi cluster. |
| `longhorn-storage.yml` | iSCSI/NFS/kernel-module prereqs + Longhorn scheduling config. |
| `post-k3s.yml` | Node labels and taints (legacy cluster). |
| `etcd-tmpfs.yml` | Migrates legacy-cluster etcd to a tmpfs RAM disk. |
| `nvme-setup.yml` | RPi 5 NVMe HAT+ configuration. |
| `k3s-recover.yml` / `k3s-full-recovery.yml` | Legacy-cluster smart recovery / break-glass full restore — see [Cluster Recovery](#cluster-recovery). |
| `enable-etcd-metrics.yml` | Exposes legacy-cluster etcd metrics for Prometheus. |
| `k3s-image-gc.yml` | Fleet-wide daily k3s/containerd image GC (all k3s nodes + murderbot). |
| `smoke-test.yml` | Read-only end-to-end legacy-cluster health validation. |
| `docker-storage.yml` | Moves Docker's data root to `/mnt/storage` on GPU hosts. |
| `setup-macmini.yml` | OrbStack, Komodo, Tailscale, BlueBubbles on Mac Mini; `--tags mini-dns` refreshes the DNS proxy LaunchDaemons only. |
| `setup-archlinux-komodo.yml` / `setup-debian-komodo.yml` | Docker + Komodo Periphery + `compose.env` from BWS, on archlinux / murderbot respectively. |
| `setup-archlinux-arc-docker.yml` | Docker group GID alignment for ARC k3s runners (also run from `docker` role — see `docs/docker/`). |
| `sysctl-tuning.yml` | Raises inotify limits on k3s + GPU agent hosts. |
| `set-static-ip.yml` | Pins a host's current DHCP address as static (defaults to `laptop`). |
| `post-k3s-setup.yml` (applications) | ArgoCD bootstrap + GitOps root-app. |
| `z2m-backup.yml` / `z2m-restore.yml` (applications) | Zigbee2MQTT config backup/restore. |

## Cluster Safety (legacy Pi k3s cluster)

Playbooks that restart k3s or take legacy-cluster nodes offline enforce: `serial: 1` (one node at
a time), a pre-flight health gate (abort if any node is already `NotReady`), a post-flight health
gate (wait for rejoin + verify health before moving to the next node), and human confirmation for
destructive operations (force restore, token rotation, full recovery). The 3-controller etcd
cluster tolerates 1 node down — the health gate prevents touching a second node while the first is
still recovering.

## High Availability (legacy Pi k3s cluster)

- **etcd on tmpfs**: a 1G RAM disk (SD card I/O is too slow); wiped on every reboot, recovery
  depends on snapshots.
- **Snapshots**: every 5 minutes to SD card, 12 retained, each controller offset by its inventory
  index so a snapshot exists somewhere roughly every 100 seconds.
- **Auto-recovery service**: `k3s-etcd-recovery.service`, runs before k3s on every boot — rejoins
  from peers on a single-node reboot, or leader-elects + restores from snapshot on full power loss.
- **Restore priority**: rpi5-1 → rpi5-0 → rpi4-0.

## Cluster Recovery (legacy Pi k3s cluster)

**Automatic first (wait ~15 min)** — `k3s-etcd-recovery.service` handles both a single-node reboot
(rejoin from peers, no data loss) and full power loss (leader election + snapshot restore, up to
5 min data-loss window) with no intervention. Check:

```bash
ssh alex@10.100.20.10
sudo journalctl -u k3s-etcd-recovery.service --no-pager -n 30
sudo systemctl is-active k3s
curl -k https://localhost:6443/healthz
```

**`k3s-recover.yml`** (partial failures / config issues):

```bash
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/k3s-recover.yml -e bws_access_token=<TOKEN>
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/k3s-recover.yml -e bws_access_token=<TOKEN> -e force_restore=true --limit rpi5-1
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/k3s-recover.yml -e bws_access_token=<TOKEN> -e rotate_token=true
```

**`k3s-full-recovery.yml`** (break-glass, all controllers down): finds the most recent snapshot
across all controllers, restores the leader, rejoins the others.

```bash
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/k3s-full-recovery.yml -e bws_access_token=<TOKEN> --check   # dry run
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/k3s-full-recovery.yml -e bws_access_token=<TOKEN>
```

**Verify after recovery**: `ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/smoke-test.yml`, or
`kubectl get nodes`, `kubectl get --raw /healthz/etcd`, `kubectl get applications -A`,
`kubectl get volumes -A -n longhorn-system`.

## archlinux node taint (legacy cluster, infra-only by default)

`post-k3s.yml` labels `archlinux=true` and taints the `archlinux_k3s` host with
`archlinux=true:NoSchedule`, so ordinary workloads stay off it by default. Flannel already
tolerates all `NoSchedule` taints; MetalLB and Longhorn need the matching toleration in GitOps
(`k3s-dean-gitops` `infra/metallb/values.yaml` and `infra/longhorn/values.yaml`). To run a
workload only on `archlinux`, add both a `nodeSelector: {archlinux: "true"}` and the matching
`archlinux:NoSchedule` toleration.

## Komodo on archlinux (Periphery): "Invalid passkey" / login failure

Komodo Core (mac-mini-m4) opens a TLS connection to Periphery on the Arch box
(`https://10.100.20.25:8120`). The Core "server" resource passkey must match
`PERIPHERY_PASSKEYS` in `~/komodo-dean-gitops/archlinux/komodo/compose.env` on Arch — both come
from the same Bitwarden secret `komodo-dean-passkey`.

**What the error means**: "Failed to receive Login Success message" / "Invalid passkey" is almost
always a **string mismatch** (wrong secret, stale file, invisible whitespace), not TLS or
firewall. **Gotcha**: `passkey = "[[SOME_VARIABLE]]"` on a `[[server]]` in
`resource-sync/stacks.toml` can get stored in Core **literally** (including the brackets) — prefer
`passkey = ""` so Core uses its global passkey instead.

**Checklist**: (1) `resource-sync/stacks.toml` → `passkey = ""` for the archlinux server, re-sync
after changing. (2) Arch `compose.env` → if `PERIPHERY_PASSKEYS` is still
`ANSIBLE_WILL_REPLACE_THIS`, re-run `setup-archlinux-komodo.yml`. (3) If `komodo-dean-passkey` was
rotated in Bitwarden, re-inject mac-mini secrets, re-run `setup-archlinux-komodo.yml`, restart
Komodo Core on the Mini if still stale.

**Refresh**: re-run `setup-archlinux-komodo.yml` (always re-renders `compose.env` from BWS and
`docker compose ... --force-recreate`s Periphery). Omit `bws_access_token` once
`/etc/komodo/.bws-secret` already exists; pass it for first bootstrap or token rotation. Then
**Sync** resources in Komodo Core and confirm the archlinux server shows healthy.

## Notes

- GPU host `murderbot` is bare metal Docker only, not part of k3s; `archlinux` is both a legacy
  k3s agent and a Docker host.
- After a full legacy-cluster reset, ArgoCD auto-reconciles all applications from git within a
  few minutes.
- After Ansible completes on a fresh cluster, apply bootstrap secrets and the root-app from
  `k3s-dean-gitops` to finish GitOps setup.
