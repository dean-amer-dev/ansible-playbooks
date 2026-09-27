# common — running

Base setup for a CachyOS/Arch workstation: timezone, locale, hostname, multilib repo, base pacman
packages (`cachyos_pacman_packages`), the `paru` AUR helper, and default shell (`zsh`). Runs first
in `setup-cachyos.yml`'s Play 2, before every other role in that playbook.

## Invocation

Part of the full CachyOS bootstrap:

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags common
```

`--limit` must include `localhost` even for a `common`-only run, because Play 1
(`fetch-secrets.yml`) always runs first as part of the same playbook file.

### One-time sudo bootstrap (fresh install only)

A brand-new CachyOS install has no passwordless sudo yet, which every other `become: true` task in
this whole playbook needs. Run this once, interactively, entering the real sudo password:

```bash
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=<TOKEN>" --limit "archlinux,localhost" \
  --tags sudo-bootstrap --ask-become-pass
```

Every run after that — including after a full re-wipe, once this has run once on the fresh
install — needs no password.

## What a clean run looks like

- `changed=0` on a repeat run except the always-run `pacman -Sy` cache update and the `paru`
  presence check (both `changed_when: false`/harmless no-ops).
- `paru` build/install tasks (`Clone paru from AUR`, `Build and install paru`) are skipped
  entirely once `which paru` succeeds — they don't re-run on every play.
- Group changes (docker/video/render, applied by other roles) and the default-shell change need
  the next login to take effect — noted in the final playbook summary.

## Tags

`common`, plus finer-grained sub-tags: `sudo-bootstrap`, `timezone`, `locale`, `hostname`,
`multilib`, `pacman`, `packages`, `paru`, `aur`, `shell`, `services`, `tailscale`.
