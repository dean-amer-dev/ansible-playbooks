# gaming — running

Steam, Proton-GE (AUR), Lutris, GameMode, MangoHud config — most packages come from
`cachyos_pacman_packages`/`cachyos_aur_packages` (installed by `common`/`desktop-apps`); this role
installs the two remaining AUR packages (`proton-ge-custom-bin`, `game-devices-udev`), enables
`gamemoded`, and fixes Steam's bundled `libusb`. Runs in `setup-cachyos.yml` Play 2, after
`amd-gpu`.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags gaming
```

## What a clean run looks like

- AUR loop and group/service tasks: `changed=0` on repeat (group-membership and service-enable
  tasks are `failed_when: false` so a harmless "already in group"/"already enabled" never fails
  the run).
- The Steam bundled-`libusb` symlink tasks back up the original file (`.orig` suffix, `force:
  false` so it never overwrites a pre-existing backup) before symlinking it to the host's real
  `libusb-1.0.so.0` — on a repeat run the backup-check (`not item.stat.islnk`) skips re-backing-up
  once the symlink is in place.

## Why the Steam libusb fix exists

Steam's bundled steam-runtime ships an ancient `libusb 1.0.19` that fails to load, breaking
HIDAPI-based controller discovery for devices needing real USB-level probing (e.g. 8BitDo Ultimate
2, vendor HID usage page `0xFF7A`). This role symlinks both the x86_64 and i386 bundled paths to
the host's real, working `libusb 1.0.30` instead of removing the bundled files outright — Steam's
loader expects a file to exist at those exact paths. See
`Projects/Archlinux/Plans/8bitdo-ultimate-2-controller-fix.md` (Obsidian) for the original
investigation.

## Tags

`gaming`, plus sub-tags `aur`, `groups`, `gamemode`, `steam`, `libusb`.
