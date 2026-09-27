# auto-updates — running

Daily unattended `pacman -Syu` with `snap-pac`/`limine-snapper-sync` rollback on failure and a
conditional, session-aware reboot when a reboot-flagged package was touched. Adopts existing
snapper/limine-snapper-sync configs into the repo (no functional change), then installs the
update script + systemd service/timer pair. Full design and open decisions:
`Areas/Archlinux/Plans/auto-updates.md` (Obsidian). Runs in `setup-cachyos.yml` Play 5c, after
`power-profiles`.

**Scope guard**: this play applies to the whole `cachyos_workstations` group by default
(`archlinux` + `lemurpro`) — **until validated, every run against real infrastructure must pass
`--limit archlinux`.**

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit archlinux \
  --tags auto-updates
```

## What a clean run looks like

- `changed=0` on repeat for the config-adoption and script/unit-template tasks.
- `auto-update.timer` should be `enabled`+`active`:
  `systemctl status auto-update.timer`.
- Default run time is `04:00` local time (`auto_updates_time`, `roles/auto-updates/defaults/main.yml`).

## Tags

`auto-updates`.
