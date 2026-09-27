# sunshine — recovery

## Moonlight can't discover the host (mDNS)

**UFW blocking inbound mDNS** — diagnosed 2026-09-06 when Moonlight on `lemurpro` never found this
host even though `avahi-browse` run locally on the Sunshine host saw its own advertisement fine
(that's the trap: a working local `avahi-browse` doesn't prove inbound UDP 5353 isn't being
dropped by ufw for *other* hosts' queries). Fixed by allowing `5353/udp` through ufw — tagged
`mdns` separately from `sunshine` since the same rule is applied to Moonlight-client-only hosts in
`setup-cachyos.yml` that don't get the rest of this role.

```bash
sudo ufw status | grep 5353
```

**Host discovered but connection fails (moonlight-qt only)** — diagnosed 2026-09-06 via
moonlight-qt's stdout: it resolves the host's mDNS name but avahi hands back **only** the
autoconfigured IPv6 ULA (`fd00::/8`) for A+AAAA records, and moonlight-qt's connection code
explicitly skips ULA when picking a "global IPv6" candidate but still falls back to using that
unreachable ULA when no IPv4 candidate comes back from its resolver. Fix (scoped to `archlinux`
only, since this is about what the Sunshine *host* publishes): `use-ipv6=no` in
`/etc/avahi/avahi-daemon.conf`, applied by this role.

```bash
grep use-ipv6 /etc/avahi/avahi-daemon.conf
```

**After changing the ipv6 setting, avahi restarted but discovery still doesn't work** — Sunshine's
own `avahi_client` connection doesn't survive `avahi-daemon` restarting out from under it and
won't automatically re-register `_nvstream._tcp`. The handler order in
`roles/sunshine/handlers/main.yml` restarts avahi-daemon **then** sunshine (handlers fire in
definition order, not notify order) specifically to cover this — if you restart avahi manually
outside Ansible, restart the Sunshine user service afterward too:

```bash
sudo systemctl restart avahi-daemon
systemctl --user restart app-dev.lizardbyte.app.Sunshine.service
```

## Screen doesn't unlock on stream connect

```bash
cat ~/.config/joystick-notify/sunshine-api-token   # should be non-empty, mode 0600
ls -la /usr/local/bin/sunshine-unlock-prep.sh /usr/local/bin/sunshine-unlock-undo.sh
```

These scripts call joystick-notify's wizard API (`POST /api/screen/unlock`/`/lock`) directly, the
same mechanism a controller connect uses — if the token is stale/wrong, joystick-notify itself
will reject the call. Re-run this role's `api-token` tag to reinstall (both the file **and** the
daemon's stored hash via `jn-daemon --install-api-token`) if it's out of sync.

## Steam Big Picture doesn't launch, or stays open after disconnect

Steam Big Picture launches via the daemon's own `config.on_connect` (set to `steam-bigpicture`,
fires on any couch-mode entry) — **not** this role's prep/undo scripts, which only handle screen
unlock. The per-app prep/undo pair for the "Steam Big Picture" `apps.json` entry
(`sunshine-launch-steam-bigpicture.sh` / `sunshine-exit-steam-bigpicture.sh`) is what actually
closes Big Picture on stream stop — see joystick-notify PR #33 (launch) and PR #36 (the undo half;
`apps.json`'s prior `"undo": "/bin/true"` left it running after disconnect since that app entry
has no `cmd` for Sunshine to kill itself with). If Big Picture doesn't close, confirm
`apps.json`'s `undo` field for that entry still points at the exit script, not `/bin/true`.

## Encoding priority / performance issues

```bash
cat /etc/security/limits.d/91-sunshine-nice.conf
groups $(whoami) | grep -E 'input|realtime'
```

Sunshine's encoding threads request `nice -15`; the `realtime` group alone only allows `-11` —
this role's `limits.d` drop-in raises the ceiling to `-20`. Group membership needs next login to
take effect.

## Virtual display / resolution switching doesn't work

Sunshine's `dd_resolution_option` automatic resolution switching does **not** work under
`capture=kwin` (confirmed live — zero display-device log activity during a session, the physical
output never actually resized). This role instead creates a `krfb-virtualmonitor` output at the
client's requested resolution and captures that directly — see
`roles/sunshine/files/sunshine-display-backend.sh` for the mechanism. If resolution switching
still fails, check `sunshine-vdisplay-connect.sh`/`-disconnect.sh` ran successfully
(`journalctl` around the connect event), not Sunshine's own resolution settings.
