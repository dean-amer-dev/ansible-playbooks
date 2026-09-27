# desktop-apps — running

AUR desktop applications not covered by pacman packages: VS Code, Cursor, Dropbox, NordPass,
NordVPN, `amdgpu_top`, WinBoat (Windows-app-via-Docker+KVM+FreeRDP). Firefox and Bitwarden are
installed by `common` instead (they're in `cachyos_pacman_packages`, not AUR). Runs in
`setup-cachyos.yml` Play 2, after `gaming` and `docker`, before `common`'s post-tasks enable
services.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags desktop-apps
```

## What a clean run looks like

- AUR install loop reports `changed` per-package only when `paru`'s output doesn't contain
  `there is nothing to do` — a repeat run with everything already installed shows `changed=0` for
  every item.
- A `WARNING: /dev/kvm not found` debug message is expected and harmless on hardware without
  virtualization enabled in BIOS/UEFI — WinBoat just won't work until that's flipped; this role
  doesn't fail because of it.
- Dropbox's user service enable is `failed_when: false` — it's fine for this to report a failure
  on a host where Dropbox hasn't been logged into yet.

## Tags

`desktop-apps`, plus sub-tags `aur`, `winboat`, `dropbox`.
