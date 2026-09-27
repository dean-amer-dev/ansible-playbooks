# kde-plasma — recovery

## Monitor sleeps then instantly wakes (DPMS bug)

Root cause (confirmed 2026-08-22 investigation, see `roles/kde-plasma/tasks/main.yml` comments for
the full writeup): a real KWin bug where, if the enabled-output count ever drops to zero, KWin
force-restores every output as DPMS-On the moment any output reappears. On this box,
joystick-notify's `force-desk-primary.sh` fully disables the couch TV output while in desk mode,
leaving only the desk monitor enabled — a DPMS-off on it alone drops the count to zero and trips
the bug.

**The fix is `output-topology-guard.service`** — it does *not* touch DPMS state (an earlier
reactive DPMS-reassert attempt caused visible flicker; see git history). It only watches output
*topology* every 15s and re-enables the TV output if found disabled, since topology only changes
on login or couch/desk-mode switches, not every idle cycle.

```bash
systemctl --user status output-topology-guard.service
journalctl --user -u output-topology-guard.service -n 50
```

If the monitor is still waking immediately after DPMS-off, confirm this service is actually
running (`dpms_sleep_fix_desk_connector` must be defined for this host in `group_vars/` — it's
currently only set for `archlinux`) — a host without that var goes through the plain idle-timeout
path instead and won't have this guard at all.

A second, related config bug: `DimDisplayIdleTimeoutSec` set to `2147483647` (meant as "never
dim") overflows powerdevil's internal ms conversion, producing continuous
`KIdleTime::addIdleTimeout: invalid timeout: -1000` log spam and a redetection storm independent of
any real DPMS event. This role sets it to `0` (the correct "disabled" sentinel) instead — if you
see that log line again, something reset this value outside Ansible; re-run `--tags dpms-sleep-fix`.

## Powerdevil screen-off timeout silently stops working

Powerdevil tracks connected displays via `libddcutil`/DDC-CI polling for its idle-timeout feature.
Repeated output enable/disable cycles (joystick-notify's couch↔desk switching, or manual
`kscreen-doctor` testing) can leave that internal tracking confused, breaking the timeout until
powerdevil restarts — even though the config on disk stays correct throughout. `powerdevil-refresh.timer`
periodically restarts the service defensively (every `kde_powerdevil_refresh_interval`, default
4h) to work around this, skipping the restart while a joystick-notify couch-mode session is
active (checked via its owner-lock file at `/tmp/joystick-notify/locks/owner.lock`).

```bash
systemctl --user status powerdevil-refresh.timer
systemctl --user status powerdevil-refresh.service
# Manual restart if you don't want to wait for the timer:
systemctl --user restart plasma-powerdevil.service
```

## Display manager conflict ("already exists and is a symlink to plasmalogin.service")

CachyOS ships `plasmalogin.service` enabled by default instead of `sddm.service` — both want to
own `/etc/systemd/system/display-manager.service`. This role deliberately does **not** force sddm
on top of an already-working `plasmalogin` — it only enables sddm as a fallback if
`/etc/systemd/system/display-manager.service` doesn't exist yet (no display manager enabled at
all). If you see this conflict error, something tried to force sddm manually outside this role's
logic — check which display manager is actually running (`systemctl status display-manager`)
before intervening further.

## Autologin works but the session isn't locked (security issue)

`LockOnStart` and autologin must always move together — if you ever see autologin enabled without
`kscreenlockerrc`'s `Daemon.LockOnStart = true`, that's a real security gap, not a cosmetic bug.
Re-run this role's `autologin` tag to restore both together; never disable `LockOnStart` alone
while leaving autologin on.

## Bluetooth controller doesn't wake the host from suspend

```bash
cat /etc/udev/rules.d/99-bluetooth-wakeup.rules
# Check the adapter's wakeup attribute directly:
for d in /sys/bus/usb/devices/*/power/wakeup; do echo "$d: $(cat $d)"; done
```

The rule matches by USB device class (`0xe0/0x01/0x01` — Bluetooth), not vendor/product ID, so it
should survive an adapter swap. If a specific adapter still isn't waking the host, confirm the
xHCI host controller itself is still an enabled ACPI wake source (`cat /proc/acpi/wakeup`) —
that's outside this role's control (BIOS/firmware-level), not something Ansible manages.
