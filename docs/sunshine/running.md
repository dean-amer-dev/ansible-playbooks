# sunshine — running

Sunshine game-stream host (AUR) with VA-API/KWin capture on the AMD Wayland desktop. Installs the
package, prep/undo scripts (thin wrappers around joystick-notify's wizard API for screen
unlock/lock only — **not** a full couch-mode transition; no CEC TV/receiver wake, since a Sunshine
stream is often remote, e.g. a Steam Deck, and has no business waking hardware nobody's in front
of), virtual-display scripts (a `krfb-virtualmonitor` output sized to the client's requested
resolution, since Sunshine's own `dd_resolution_option` doesn't work under `capture=kwin`),
config, and the user service. Runs in `setup-cachyos.yml` Play 7, after `moondeck`.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags sunshine
```

`sunshine_api_token` is **required** and passed as an extra-var (BWS secret
`joystick-notify-dean-sunshine-api-token`) — deliberately **not** fetched via `fetch-secrets.yml`
(that play only targets `localhost` and needs `bws_access_token`; this role is routinely run
`--limit archlinux` alone):

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --limit archlinux --tags sunshine \
  -e sunshine_api_token=<value from BWS secret joystick-notify-dean-sunshine-api-token>
```

Without it, the role fails fast with an explicit `assert` message.

## What a clean run looks like

- `changed=0` on repeat except the always-run token-hash-install command
  (`jn-daemon --install-api-token`, `changed_when: false` — installing the same token twice is
  idempotent by design).
- Web UI reachable: `http://localhost:47990`.
- The AUR sunshine package ships
  `app-dev.lizardbyte.app.Sunshine.service`, **not** `sunshine.service` — verified via
  `pacman -Ql sunshine | grep systemd`; the role enables that exact unit name.

## Ports (UFW)

TCP `47984 47989 47990 48010`; UDP `47998 47999 48000 48002 48010`; plus mDNS discovery
(`5353/udp`, tagged `mdns` separately — see recovery.md) shared with Moonlight-client-only hosts
elsewhere in the same playbook.

## Tags

`sunshine`, plus sub-tags `groups`, `aur`, `scripts`, `api-token`, `config`, `ufw`, `mdns`, `udev`,
`service`.
