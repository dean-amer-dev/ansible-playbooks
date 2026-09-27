# debian-k3s — recovery

## Rebuilding/reinstalling the init host (split-brain guard: ansible-playbooks#114)

`debian_k3s_init_host` is an ordinary Ansible variable (`roles/debian-k3s/defaults/main.yml`),
defaulting to `groups['debian_k3s'][0]` (currently `gmktec-1`) — it is **not** a fixed cluster
identity. The risk: if that default host is ever rebuilt/reinstalled from scratch and the playbook
is re-run unmodified, it would look "fresh" (no `/var/lib/rancher/k3s/server/db`) and Ansible would
render `cluster-init: true` for it again — bootstrapping a **second, competing cluster** instead of
rejoining the real one that's still running on the surviving peers. Split-brain at best, silently
replacing the live cluster at worst.

**The safety check** (`roles/debian-k3s/tasks/k3s.yml`, "Init-host safety check" block) runs before
anything else in `k3s.yml`, only when `inventory_hostname == debian_k3s_init_host`:

1. Checks whether this host already has k3s server data. If it does, it's not actually fresh —
   nothing to guard against, proceed normally.
2. If it looks fresh, it queries every **other** node in the `debian_k3s` group for a live
   `/readyz`.
3. If any peer answers, the play **fails** with an explicit message naming which peer(s) are
   live and the exact fix.

**Recovery when you hit this failure:**

```bash
export BWS_ACCESS_TOKEN="$(cat /home/alex/claude/bws-ro-token)"
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-debian-k3s.yml \
  -e debian_k3s_init_host=<a surviving peer, e.g. gmktec-2>
```

This makes the surviving peer the one Ansible treats as `cluster-init: true` (it already is, in
etcd terms — this only affects which host's `k3s.yaml`/join-token Ansible reads from), and the
rebuilt host rejoins as a normal member instead. Do **not** override/skip the check itself — it
exists specifically so this can't happen by accident. If you're rebuilding a *non*-init host, no
special handling is needed; it's just another joiner.

## Ansible-triggered reboots (lan0 rename + /home LV migration — ansible-playbooks#113)

CLAUDE.md's blanket "never reboot a server" rule has exactly one carve-out, scoped to this role
only: `roles/debian-k3s/tasks/network.yml` (NIC rename) and `roles/debian-k3s/tasks/storage.yml`
(`/home` LV migration) each contain an `ansible.builtin.reboot` task, gated so it only fires when
the change it's for is actually pending:

- **NIC rename to `lan0`**: the rename is a systemd `.link` file matched by MAC; it can't take
  effect while the interface is up and carrying the SSH session, so it needs a reboot. Only fires
  when the current default-route interface isn't already named `lan0`.
- **`/home` LV migration**: `/home` can't shrink while mounted, so a new right-sized LV is
  created, populated via `rsync`, and `fstab` is repointed at it — but the box has to reboot to
  actually mount the new LV before the old one can be safely removed. Only fires when the LV
  behind `/home` is still the oversized original.

**Why this is safe** (the reasoning the carve-out in CLAUDE.md exists for): the play runs with
`serial: 1` — one host at a time — and each reboot task uses `reboot_timeout`/`connect_timeout`
plus a `test_command` (the new IP coming up on `lan0`, or `/home` reporting mounted) so Ansible
waits for the host to actually come back in the expected state before continuing, and asserts on
it explicitly afterward. Nothing about this generalizes to any other role, host, or script —
every other case is still "tell Alex, he reboots it."

**What to expect when it fires:** a normal `setup-debian-k3s.yml` run against a from-scratch
GMKtec box reboots it up to twice (once for each independent trigger, though in practice both
land in the same run) and takes noticeably longer than a no-op re-run — this is expected, not a
hang. If a run is interrupted mid-reboot (Ansible control node lost network, etc.), just re-run
the same command: both tasks are idempotent and no-op once the target state (`lan0` up, `/home`
on the new LV) is already reached.

## Preflight failures

`playbooks/infrastructure/setup-debian-k3s.yml --tags preflight` (or the `preflight` step inside
a full run) is read-only and lists **every** problem it finds at once rather than failing on the
first — the `NOT READY: ...` message enumerates all of them, semicolon-separated. Common ones and
their fix:

| Problem | Fix |
|---|---|
| `cgroup v2 cpu/memory/pids controllers not available` | Debian 13 ships cgroup v2 by default; check `/boot/cmdline`/GRUB for `systemd.unified_cgroup_hierarchy=0` or similar overrides. |
| `kernel BPF options incomplete for Cilium` | Kernel config missing `CONFIG_BPF_SYSCALL`/`CONFIG_CGROUP_BPF`/etc. — needs a kernel with those enabled (stock Debian 13 kernel has them). |
| `module-missing:<name>` | One of `overlay br_netfilter dm_snapshot dm_thin_pool` didn't load — re-run `--tags packages` (loads them via `modprobe` and `/etc/modules-load.d/k3s.conf`). |
| `ip_forward-off` | Re-run `--tags packages` (sets the sysctl) — or check something else reset it. |
| `swap-on` | Re-run `--tags packages` (`swapoff -a` + fstab comment-out), or check a manual `swapon` happened after. |
| `a k3s/etcd port is already in use` | Something other than k3s is bound to 6443/2379/2380/10250 — `ss -ltnp` to find it. If k3s itself is already active on this host, this check is skipped automatically. |
| `node IP ... is not on this host` | `debian_k3s_node_ip` (defaults to `ansible_host`) doesn't match reality — fix the inventory/group_vars entry, don't override the var per-run. |
| `chrony not synchronised yet` | Freshly booted box, chrony hasn't settled — wait a minute and re-check, or `chronyc makestep`. |
| `unreachable: https://get.k3s.io` / `.../releases` | No outbound internet from this host — check DNS/gateway/firewall. |
| `/var has under 25 GiB free` | Storage step (`--tags storage`) hasn't run yet, or the LVM layout is genuinely short on space — see below. |

## Storage: LVM layout and the OS/kube-volume-pool split

`roles/debian-k3s/tasks/storage.yml` never touches an existing VG's *contents* — it only grows
`/`, `/var`, `/tmp` online (grow-only, `resizefs: true`) and migrates `/home` to a right-sized LV
(see reboot section above). The remaining free space in the VG becomes the OpenEBS Local PV LVM
pool (`vgpattern = ^{{ debian_k3s_storage_vg }}$`).

- **"No dedicated VG and no free disk space" assertion failure**: means neither a pre-existing
  `data` VG, nor a `k3s-data`-partlabeled partition, nor enough trailing free space
  (`debian_k3s_lvm_min_free_gib`, default 50 GiB) exists on `debian_k3s_lvm_disk` (default
  `/dev/nvme0n1`), *and* the VG behind `/` doesn't have enough free extents either. Free up space
  or attach more disk — this task creates nothing destructively, so there's no unwind needed.
- **"/home is in fstab but is NOT mounted" assertion failure**: storage tasks refuse to run at all
  in this state (a previous migration or manual intervention could have left `/home` unmounted).
  `mount /home` (or reboot) on the affected host, then re-run.
- **Old `/home` LV not cleaned up**: if a run gets interrupted after the migration reboot but
  before the "Finish the /home migration" block runs, just re-run the same playbook — it detects
  the LV naming pattern (`<name>2` = the new, active one) and removes the old one safely.
- **Do not `lvrename` a mounted LV by hand.** The new `/home` LV intentionally keeps the name
  `<original>2` rather than being renamed to match the old one — a manual rename on a mounted LV
  has caused udev to recreate the device node and systemd to unmount `/home` out from under an
  active session on 3 hosts historically (dropped SSH sessions, `~/.ssh` vanishing, key login
  refused). Leave the `2`-suffixed name as-is.

## k3s server won't come up / etcd unhealthy

`k3s.yml`'s final check is `k3s kubectl get --raw '/readyz?verbose'` (retried 30× over 5 minutes)
asserting `[+]etcd ok` in the output. If this times out or asserts false:

```bash
sudo systemctl status k3s
sudo journalctl -u k3s -n 200 --no-pager
sudo k3s kubectl get --raw '/readyz?verbose'
```

A joiner waits for the init host's `:6443` to answer before starting its own `k3s` service
(`wait_for`, 300s timeout) — if a joiner fails here, check the init host is actually up and
`k3s.yaml`'s `server:` fields (rendered from `k3s-config.yaml.j2`) point at the right address.

## Cilium / CoreDNS / kube-vip only apply from the init host

All three (`cilium.yml`, `coredns.yml`, `kube-vip.yml`) gate their entire task list on
`inventory_hostname == debian_k3s_init_host` and talk to the API via the init host's local
`/etc/rancher/k3s/k3s.yaml` kubeconfig. If a Helm install or `kubernetes.core.k8s` apply fails,
re-run targeting just the init host: `--limit <init_host> --tags cilium` (or `coredns`,
`kube-vip`). **kube-vip must stay a DaemonSet, not a static pod** — an earlier revision of this
role shipped kube-vip as a static pod; `kube-vip.yml`'s first task removes that manifest
wherever it might still be sitting (`/var/lib/rancher/k3s/agent/pod-manifests/kube-vip.yaml`)
before applying the DaemonSet form, so this cleanup is safe to leave in even though the static-pod
form has never actually shipped to real hosts.

## Dedicated recovery/runbook playbooks (legacy Pi cluster — not `debian_k3s`)

These target the **legacy** `[k3s]` group (`controllers`/`agents` — the Raspberry Pi HA cluster),
not the GMKtec `debian_k3s` group documented above. Linked here because they're the closest
existing recovery playbooks in this repo and the pattern (etcd snapshot/restore, `serial: 1` +
health gates) is the template this role's own recovery would follow if/when it's needed:

- `playbooks/infrastructure/k3s-recover.yml` — smart recovery: config/tmpfs fixes, token
  rotation, single-node force-restore from snapshot.
- `playbooks/infrastructure/k3s-full-recovery.yml` — break-glass: restores all controllers from
  the most recent snapshot when the whole cluster is down.
- `playbooks/infrastructure/smoke-test.yml` — read-only validation, safe to run anytime.

The GMKtec cluster has no etcd-snapshot-and-restore automation of its own yet (embedded etcd
snapshots are enabled via `debian_k3s_etcd_snapshot_schedule`/`_retention` in defaults, but there
is no `k3s-recover.yml`-equivalent playbook for this group) — a full cluster loss today would be
a manual `k3s server --cluster-reset` restore from the newest `/var/lib/rancher/k3s/server/db/snapshots/`
file, following the same shape as `k3s-full-recovery.yml`.
