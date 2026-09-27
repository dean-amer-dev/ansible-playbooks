# power-profiles — recovery

## Profile never switches / stuck on one profile

```bash
systemctl --user status idle-power-profile.service
tail -50 ~/.local/state/power-profile-switch.log
```

The wrapper script (`power-profile-switch.sh`) logs every switch attempt — check there first for
what it thinks the current idle state is versus what `swayidle` is actually reporting.

## `power-profiles-daemon` calls fail (permission denied / polkit)

This service **must** run as a user unit, not root/system — `power-profiles-daemon`'s polkit
policy requires an authenticated active local session; a system-level caller is denied outright.
If you see permission errors, confirm the unit really is running under
`systemctl --user` (not accidentally installed as a system unit):

```bash
systemctl --user status idle-power-profile.service
systemctl status idle-power-profile.service   # should show "not found" — it's user-scope only
```

## Service isn't running at all after boot (no active session)

User lingering (`loginctl enable-linger <user>`) is what lets this run without an active login —
confirm it's still enabled:

```bash
loginctl show-user $(whoami) | grep Linger
```

If lingering was somehow disabled outside Ansible, re-run this role's tag to restore it.

## Changed the idle timeout/profile vars but nothing changed on the host

The unit-file template task only restarts the service `when: idle_power_profile_unit.changed` —
confirm the rendered file on disk actually reflects the new vars:

```bash
cat ~/.config/systemd/user/idle-power-profile.service
```

If it's stale, the templating itself didn't pick up the new `group_vars` value — check for a typo
in the var name/override, not a bug in the restart logic.
