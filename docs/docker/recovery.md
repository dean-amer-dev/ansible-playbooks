# docker — recovery

## daemon.json got clobbered / lost a hand-edited key

The merge task reads the existing `daemon.json` (base64-decoded, `from_json`), combines the `dns`
key into it, and writes the result back — it should never drop unrelated keys. If a key is
missing after a run:

```bash
cat /etc/docker/daemon.json
```

Check whether the file was **invalid JSON** before this role ran — the read task uses
`failed_when: false` and defaults to `e30=` (base64 `{}`) if the read/decode fails, which means a
malformed pre-existing file gets silently replaced with just `{"dns": [...]}`\, losing everything
else. Fix: restore the intended keys by hand once, then let this role keep managing `dns` going
forward.

## ARC runner pods can't reach the Docker socket (permission denied)

```bash
getent group docker              # check GID on archlinux
ssh mini "getent group docker"   # or wherever murderbot/mac-mini's GID lives — must match
```

The GID-alignment task (`tasks/archlinux-arc-docker-gid.yml`, imported by this role) only runs
`when: inventory_hostname in (groups['archlinux_k3s'] | default([]))` — if a host isn't in that
inventory group, the GID is never touched, by design. Re-run `--tags arc-gid` (or the standalone
`setup-archlinux-arc-docker.yml`) after confirming the host actually needs it.

## Docker won't start after a daemon.json change

```bash
sudo dockerd --validate --config-file /etc/docker/daemon.json
journalctl -u docker -n 100 --no-pager
```

A syntactically valid but semantically wrong `daemon.json` (e.g. unreachable DNS entries) won't be
caught by Ansible — Docker itself will refuse to start or misbehave. Fix the file directly, then
either let a future Ansible run reconcile it or leave the manual fix in place if it's a genuine
override this role's merge logic should keep respecting.
