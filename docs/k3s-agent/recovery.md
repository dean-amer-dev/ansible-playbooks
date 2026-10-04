# k3s-agent — recovery

> **murderbot is no longer managed by this role** (2026-10-04): it joined the Infrastructure 2.0 cluster via the `gpu-worker` role (`playbooks/infrastructure/setup-gpu-worker.yml`); `murderbot-k3s-agent.yml` and `host_vars/murderbot.yml` were removed. References to them below are historical.

## Node stuck `NotReady`, containerd boot is slow (meta.db bloat)

Root cause of the 2026-09-08 murderbot `NotReady` incident: containerd generates a message that
exceeds the 16MiB CRI response cap, which combined with a bloated `meta.db` (containerd's
metadata boltdb) can slow containerd's boot to a crawl. boltdb's random small-page I/O pattern
pairs badly with slow/high-latency storage (e.g. spinning-disk RAID).

**Fix**: set `k3s_agent_containerd_meta_ssd_dir` (role defaults, empty by default) to a directory
on fast local storage for the affected host, then re-run. The role handles the one-time migration
automatically:

```bash
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/murderbot-k3s-agent.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN"
```

It stops `k3s-agent`, copies the existing `meta.db` to the new SSD path (`cp --preserve=all`,
`creates:`-gated so it only copies once), removes the original, and symlinks the data-dir path to
the new location — then restarts `k3s-agent` (via the `Restart k3s-agent` handler, triggered by
the symlink/config-template tasks).

```bash
ls -la /var/lib/rancher/k3s/agent/containerd/io.containerd.metadata.v1.bolt/meta.db  # should be a symlink
```

## Related: k3s/containerd image bloat filling disk

A related but separate issue (not this role's job to fix): `k3s crictl images` accumulating
hundreds of dead CI-tag layers that k3s/containerd never garbage-collects on its own until
kubelet's disk-pressure GC crosses its 85% high-watermark. See
`playbooks/infrastructure/k3s-image-gc.yml` (deploys a daily prune timer +
`/etc/crictl.yaml`) — a separate playbook, applied fleet-wide to every k3s node (`k3s:murderbot`
host pattern), not part of this role.

```bash
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/k3s-image-gc.yml
```

## Agent won't join / can't reach the cluster

```bash
systemctl status k3s-agent
journalctl -u k3s-agent -n 200 --no-pager
cat /etc/rancher/k3s/config.yaml   # check server: URL and token are correct
```

The join token comes from `k3s_token` (a hostvars fact set by `fetch-secrets.yml`, sourced from
BWS) — if it's stale/wrong, the agent will fail to register. Re-run `fetch-secrets.yml` (or the
wrapping playbook, which imports it) with a fresh `bws_access_token` rather than hand-editing the
config file.

## Scoping accidentally hit every agent instead of one host

If `archlinux-k3s-agent.yml` was run without `-e k3s_agent_hosts=<pattern>`, the imported
`k3s-agent.yml` playbook targets its full default host group — check what actually got touched
(`ansible-playbook ... --list-hosts` before a real run is the safe way to verify scope next time)
and re-run correctly scoped if something unintended changed.

## murderbot config drifted from `host_vars`

If murderbot's live `/etc/rancher/k3s/config.yaml` or
`/etc/systemd/system/k3s-agent.service.env` don't match `inventory/host_vars/murderbot.yml`
anymore, something changed it outside Ansible — diff them directly before re-running, since this
role will otherwise just overwrite whatever's live with the `host_vars` values (which is usually
what you want, but confirm the drift wasn't intentional first).
