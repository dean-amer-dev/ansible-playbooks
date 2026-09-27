# joystick-notify — running

Controller-driven couch-mode automation for KDE Plasma. Installed as a real package
(`packaging/PKGBUILD`, `makepkg -si`) built from a fresh clone of the joystick-notify repo on the
target host — same pattern the `sunshine` role uses for its AUR install, not an AUR package
itself. Ships exactly two systemd **user** units: `joystick-notify.service` (daemon) and
`joystick-notify-tray.service` (tray icon). Also manages CEC adapter wiring
(`pulse8-cec-attach@.service` unmasking + stale udev rule cleanup) and a legacy pre-v2
"desk-primary-enforcement" subsystem (see `tasks/legacy-desk-primary.yml`). Runs in
`setup-cachyos.yml` Play 8, after `sunshine`.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags joystick-notify
```

Deploy a feature branch for a live test before merging (default ref is `main`):

```bash
ansible-playbook ... --tags joystick-notify -e joystick_notify_repo_version=<branch>
```

## What a clean run looks like

- The build step (`makepkg -sfi --noconfirm`, **not** `--needed`) always forces a rebuild and
  reinstall regardless of whether the version string matches what's already installed — this is
  intentional: pkgver/pkgrel are static (`0.1.0-1`), so `--needed` would silently no-op a real
  deploy of new commits on `main`. Every run of this tag means "deploy whatever the ref currently
  is," so expect a rebuild+reinstall on **every** run where the source changed, even without a
  version bump.
- `joystick-notify.service`/`-tray.service` restart (not just start) whenever the package rebuilt
  or stale unit overrides were removed — a plain `state: started` on an already-running unit
  would otherwise be a no-op and a real code change would silently never take effect.
- `pulse8-cec-attach@.service` should be unmasked (it has no `[Install]` section — udev's
  `SYSTEMD_WANTS` starts it directly; there's nothing to "enable").
- `/dev/cec0` should exist and be configured — check with `cec-ctl -S` (should show a claimed
  logical address, not `f.f.f.f`).

## Tags

`joystick-notify`, plus sub-tags `build`, `service`, `daemon`, `tray`, `cec`, `shutdown`,
`legacy-desk-primary`.
