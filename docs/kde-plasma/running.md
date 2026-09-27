# kde-plasma — running

Installs and configures KDE Plasma 6 + display manager, plus a set of display-stability fixes for
the couch-mode/CachyOS setup: autologin + immediate lock (security boundary without a physical
login screen), dark theme, a DPMS-sleep-wake bug workaround (`output-topology-guard.service`),
display power-off idle timeouts, a periodic Powerdevil self-heal restart, and USB remote-wakeup
for Bluetooth. `plasma-meta`/`sddm` packages come from `common`. Runs in `setup-cachyos.yml`
Play 2, first among the desktop roles (before `amd-gpu`).

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags kde
```

## What a clean run looks like

- `changed=0` on repeat for every `copy`/`file`/`systemd` task; the `kwriteconfig6` shell tasks are
  always `changed_when: false` (they're idempotent by nature — writing the same value twice is a
  no-op to the underlying config file, and there's no cheap way to detect "would have changed"
  from the shell command itself).
- The DPMS-sleep-fix block (`dpms_sleep_fix_desk_connector` gated) only runs on hosts where that
  var is defined (currently `archlinux`) — other `cachyos_workstations` members instead get the
  plain idle-timeout config path.
- `output-topology-guard.service` and `powerdevil-refresh.timer` (both systemd **user** units)
  should show `enabled`/`active` after the run — verify with
  `systemctl --user status output-topology-guard.service powerdevil-refresh.timer`.

## Why autologin + LockOnStart is paired the way it is

Autologin skips the login screen (so `graphical-session.target` — and therefore Sunshine/
MoonDeckBuddy/joystick-notify — comes up without a physical login), but `LockOnStart` in
`kscreenlockerrc` re-locks the session immediately as the real security boundary instead. **Both
must be flipped together** — enabling autologin without `LockOnStart: true` would hand out an
already-open desktop to physical access. An earlier design (PR #65) paired autologin with a
hand-rolled `lock-on-login.sh` autostart script instead; that's gone, replaced by native
`LockOnStart` (PR #73).

## Tags

`kde`, plus sub-tags `sddm`, `avahi`, `wayland`, `plasmalogin`, `autologin`, `display`, `theme`,
`dpms-sleep-fix`, `power`, `bluetooth`.
