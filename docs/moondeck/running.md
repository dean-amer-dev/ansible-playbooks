# moondeck — running

MoonDeckBuddy — the paired HTTPS+WebSocket companion the MoonDeck SteamDeck plugin queries for
Steam/PC state and control. **Not a Sunshine hook** — the actual game stream is still a Sunshine
stream (MoonDeck adds its own `apps.json` entry running `MoonDeckStream`), so Sunshine's existing
`global_prep_cmd` already covers screen unlock for MoonDeck-launched games; this role does not
wire anything to joystick-notify's wizard API. See
`Areas/Archlinux/notes/joystick-notify-sunshine-reenable-phase3-notes.md` (Obsidian) for the full
research. Installed via AUR (`moondeckbuddy-appimage`, installed by the `desktop-apps` role's paru
loop) — this role only wires the gamescope wrapper script and the systemd **user** service. Runs
in `setup-cachyos.yml` Play 6, after `sunshine`... actually before `sunshine` (Play 6, `sunshine`
is Play 7).

Headless by default (`NO_GUI=true`) bound to `default.target`, not `graphical-session.target` —
the paired REST/WS API needs no display.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags moondeck
```

One-off GUI/systray run (only needed to show the pairing PIN dialog for a **new** client — pairing
is a manual, occasional action, not something this role automates):

```bash
MOONDECKBUDDY_NO_GUI=false systemctl --user restart moondeckbuddy.service
```

## What a clean run looks like

- `changed=0` on repeat.
- `moondeckbuddy.service` (user scope) `enabled`+`active`, listening on `:59999`.
- UFW allows `59999/tcp`.

## Tags

`moondeck`, `service`, `ufw`.
