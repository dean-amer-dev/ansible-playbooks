# moondeck — recovery

## MoonDeck plugin can't reach the host

```bash
systemctl --user status moondeckbuddy.service
ss -ltn | grep 59999
sudo ufw status | grep 59999
```

Check the service is actually running as a **user** unit (not system) and the UFW rule for
`59999/tcp` is present — both are applied by this role.

## Need to pair a new client (PIN dialog required)

The service normally runs headless (`NO_GUI=true`). To show the pairing dialog:

```bash
MOONDECKBUDDY_NO_GUI=false systemctl --user restart moondeckbuddy.service
# pair the client, then revert:
systemctl --user restart moondeckbuddy.service   # picks NO_GUI back up from the unit default
```

## Legacy `/opt/moondeck` leftovers reappear

This role actively removes `/opt/moondeck` and `/etc/profile.d/moondeck.sh` (superseded by the
AUR package) on every run — if they keep reappearing, something outside Ansible is reinstalling
the old raw-AppImage path; find and stop that source rather than fighting it here.

## Game launch via MoonDeck doesn't unlock the screen

By design — MoonDeck is not wired to joystick-notify's wizard API at all (see `running.md`). The
actual stream is a Sunshine stream underneath, so **Sunshine's own** `global_prep_cmd` (see
`../sunshine/`) is what handles screen unlock — if that's not firing, the issue is in the
`sunshine` role/config, not here.
