# k3s-agent — running

Installs the k3s binary via the official installer script (agent-only mode), writes
`/etc/rancher/k3s/config.yaml`, and enables the `k3s-agent` service — joining an existing k3s
cluster (the legacy `[k3s]` group / Pi HA controllers, **not** the `debian_k3s` Infrastructure 2.0
cluster, which has its own dedicated role — see `../debian-k3s/`). `k3s_token` must already be set
as a hostvars fact (fetched from BWS by `fetch-secrets.yml`). Also handles an optional
containerd `meta.db` SSD split for hosts with slow/high-latency primary storage.

Used by three different playbooks depending on host:

- **`setup-cachyos.yml`** (archlinux, via `cachyos_workstations` group) — Play 9, after
  `joystick-notify`.
- **`archlinux-k3s-agent.yml`** — standalone Arch-only join (imports `fetch-secrets.yml` +
  `setup-archlinux-k3s.yml` + this role).
- **`murderbot-k3s-agent.yml`** — brings murderbot's k3s-agent under Ansible management (it was
  originally joined via a bare `k3s agent` install outside this repo).

## Invocation

```bash
# As part of the full CachyOS bootstrap
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" --limit "archlinux,localhost" --tags k3s-agent

# Arch-only, standalone (must scope with k3s_agent_hosts or it targets every agent)
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/archlinux-k3s-agent.yml \
  -e bws_access_token="$BWS_ACCESS_TOKEN" \
  -e k3s_agent_hosts=archlinux_k3s

# murderbot (Debian, bare metal — not part of setup-cachyos.yml)
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/murderbot-k3s-agent.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN"
```

`k3s_agent_hosts` (a host or group pattern, e.g. `archlinux_k3s` or the bare hostname `archlinux`)
**must** be passed to `archlinux-k3s-agent.yml` — otherwise the imported `k3s-agent.yml` playbook
targets every agent in the cluster, not just this one host.

## What a clean run looks like

- `changed=0` on repeat once the binary is installed and config is unchanged.
- `systemctl status k3s-agent` shows `active (running)`.
- If `k3s_agent_containerd_meta_ssd_dir` is set for this host: `meta.db` should be a symlink
  pointing into that SSD directory, not a regular file on the data-dir volume.

## Before the first real run on murderbot

Diff `inventory/host_vars/murderbot.yml` against the host's live
`/etc/rancher/k3s/config.yaml` and `/etc/systemd/system/k3s-agent.service.env` to confirm nothing
has drifted since 2026-09-08 — murderbot opts out of the role's default Longhorn node-labels and
kubelet eviction args via that host_vars file.

## Tags

`k3s-agent`, plus sub-tags `config`, `containerd`, `storage`, `service`.
