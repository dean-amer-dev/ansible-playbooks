# joystick-notify — recovery

## A git pull of new commits doesn't reach the running daemon

Found live 2026-08-30: `makepkg -si --needed` silently no-op'd a real deploy — makepkg saw the
existing build artifact and skipped rebuilding, then pacman's `--needed` saw the matching
installed version and skipped reinstalling, so a PR's commits built "cleanly" on the surface but
never reached the running package. Fixed by using `makepkg -sfi` (force rebuild) with no
`--needed` (always reinstall). If you ever see this regress:

```bash
cd ~/joystick-notify-build/packaging
makepkg -sfi --noconfirm   # never -si --needed for this package
```

## Old config/behavior persists after an upgrade (stale per-user systemd overrides)

Earlier iterations (v1, and a stopgap hand-templated v2 unit) left per-user overrides in
`~/.config/systemd/user/` — systemd resolves these **ahead of** the package's real shipped units
at `/usr/lib/systemd/user/`, so stale content there silently shadows a correctly-upgraded package.
This role removes known stale unit names on every run
(`joystick-notify.service`, `joystick-notify-tray.service`,
`joystick-notify-steam-shutdown.service`, `joystick-notify-steam-shutdown.path` — the last two are
v1-only concepts that don't exist in v2 at all). If something still looks stale:

```bash
ls -la ~/.config/systemd/user/ | grep joystick-notify
ls -la ~/.config/systemd/user/graphical-session.target.wants/ | grep joystick-notify
```

A dangling `graphical-session.target.wants/` symlink pointing at a removed override (found live
2026-08-30) doesn't break anything on its own — systemd still resolves the real packaged unit
despite it — but this role explicitly cleans it up anyway rather than relying on a later `enable`
call's incidental repair behavior.

## CEC adapter (`/dev/cec0`) not configured despite `pulse8-cec-attach@` running

Two distinct historical failure modes, both fixed by this role but worth knowing if they resurface:

1. **Masked service**: `pulse8-cec-attach@.service` was masked system-wide during the 2026-08-28
   incident bisection and never unmasked — this is why `/dev/cec0` was missing entirely for a
   period. Check: `systemctl status pulse8-cec-attach@*.service` (look for `masked`).

2. **Stale v1 udev rules shadowing the packaged ones**: untracked v1 leftover rule files (no
   `joystick-notify-` filename prefix, predating the v2 package) sort **after** the package's
   namespaced `70-joystick-notify-cec-configure-autostart.rules` and silently overwrite
   `SYSTEMD_WANTS` with the old v1 template unit name
   (`cec0-configure@card1-HDMI-A-1.service`, which doesn't exist in v2). Confirmed live 2026-08-29
   via `udevadm info /dev/cec0` showing the stale value. This role removes
   `cec-configure-autostart.rules`, `pulse8-cec-autoattach.rules`, `98-cec-fixup.rules` on every
   run. If a *new* untracked rule file appears with this problem, add it to that removal list.

```bash
udevadm info /dev/cec0 | grep SYSTEMD_WANTS   # should reference the packaged unit, not a v1 template name
cec-ctl -S                                     # should show a claimed logical address
```

3. **`cec0-configure.service` runs but no-ops (`HOME` resolves to `/root`)**: this service runs at
   **system** scope (triggered by udev, no login session), so `config.py`'s `Path.home()`
   resolves to `/root`, not the real user's home — it silently reads a nonexistent
   `/root/.config/joystick-notify` config, gets schema defaults (`cec.enabled=False`), and exits
   early with "CEC disabled or couch port not configured, skipping" even with a real config
   present. Fixed via a systemd drop-in
   (`/etc/systemd/system/cec0-configure.service.d/override.conf`) forcing the correct `HOME` —
   this is host-specific, so it's a drop-in, not a packaging-level fix.

```bash
cat /etc/systemd/system/cec0-configure.service.d/override.conf
journalctl -u cec0-configure.service -n 50
```

## Couch/desk mode fighting itself at the login greeter (legacy desk-primary subsystem)

`tasks/legacy-desk-primary.yml` manages 5 files predating the v2 rewrite that were never carried
into it — still live and doing real work (forcing the desk monitor primary and disabling the
couch TV output whenever KDE returns to the login greeter, at boot or on any plasmalogin
restart), so the TV doesn't stay stuck extended at the login screen.

**2026-08-31 fix, still worth knowing about**: `force-desk-primary-greeter.sh` never checked couch
mode before disabling the couch output, and even where the check existed
(`force-desk-primary.sh`), it read a v1 lock file (`/tmp/joystick-notify/locks/owner.lock`) the v2
daemon never writes — so it always evaluated false. A spurious plasmalogin restart mid-session
(the documented CachyOS "double login" bug) refired the greeter unit while the desk user was
actively in couch mode gaming, and it disabled the TV output outright with no CEC involved. Both
scripts now share a fixed `is_couch_mode()` in `config-env.sh` that reads real v2 state from
`health.json` instead.

```bash
cat /usr/local/lib/joystick-notify/config-env.sh   # shared is_couch_mode() source of truth
systemctl status plasmalogin-desk-primary.service
journalctl --user -u force-desk-primary.service -n 50
```

If the TV gets disabled during an active couch-mode session again, check `health.json` is being
read correctly by `is_couch_mode()` before assuming it's a new bug — this exact failure mode has a
known fix already in place.

## Shutdown takes longer than expected / hangs briefly

`logind.conf.d/joystick-notify-shutdown-inhibit.conf` (rendered from
`logind-shutdown-inhibit.conf.j2`) delays shutdown for `shutdown_watcher.py`'s teardown — this is
deploy-only (no live `systemctl restart systemd-logind` after changing it; the config takes effect
at the next real logind start, i.e. next reboot). If the inhibit delay ever seems wrong, confirm
`joystick_notify_shutdown_inhibit_delay_max_s` (group_vars) matches
`config.shutdown.teardown_timeout_s` plus margin, and remember a change to this file needs a
reboot to verify, not just a re-run.
