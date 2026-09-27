# docker — running

Enables the Docker daemon, adds the user to the `docker` group, and merges DNS pinning
(`10.100.20.240`, `1.1.1.1`) into `/etc/docker/daemon.json` without clobbering any other keys
already there. On `archlinux_k3s` hosts specifically, also aligns the `docker` group GID to match
murderbot's (Debian, GID 989) so ARC (Actions Runner Controller) k3s runner pods can share the
host Docker socket across differently-provisioned hosts. `docker`/`docker-compose`/`docker-buildx`
packages themselves come from `common` (`cachyos_pacman_packages`). Runs in `setup-cachyos.yml`
Play 2, after `amd-gpu`/`gaming`.

Note: the Komodo Periphery playbooks (`setup-archlinux-komodo.yml`, `setup-debian-komodo.yml`)
install and configure Docker themselves inline — they do **not** use this role.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags docker
```

Standalone GID-alignment only (no full Komodo bootstrap needed):

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-archlinux-arc-docker.yml --limit archlinux
```

## What a clean run looks like

- `changed=0` on repeat — `daemon.json` merge only reports `changed` if the resulting merged JSON
  actually differs from what's on disk; Docker only restarts (`when: daemon_json_updated.changed`)
  when that merge changed something.
- Group membership (`docker`) needs next login to take effect.

## Tags

`docker`, `groups`, `arc-gid`.
