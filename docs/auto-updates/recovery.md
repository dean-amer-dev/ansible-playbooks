# auto-updates — recovery

## An update broke something — need to roll back

The whole point of pairing this with `snap-pac`/`limine-snapper-sync` is that a snapper snapshot
exists from just before the update. From the CachyOS boot menu (Limine), select the pre-update
snapshot entry and boot into it, or roll back live:

```bash
snapper list
sudo snapper rollback <pre-update snapshot number>
```

See `Areas/Archlinux/Plans/auto-updates.md` (Obsidian) for the full rollback design and any
open decisions not yet reflected here.

## Timer isn't firing / didn't run overnight

```bash
systemctl status auto-update.timer
systemctl list-timers auto-update.timer
journalctl -u auto-update.service -n 100 --no-pager
cat /var/lib/auto-updates/*   # flag files: disabled-after-rollback, reboot-pending-across-a-deferred-day
```

A flag file left over from a previous failed run (`auto_updates_flag_dir`,
`/var/lib/auto-updates` by default) can suppress the next scheduled run by design — check for one
before assuming the timer itself is broken.

## Update script never reboots after a kernel/reboot-flagged package update

Check the flag-file logic in `templates/auto-update.sh.j2` for the exact "session-aware" condition
(it defers a reboot if a user session is active, rather than rebooting under someone). If a reboot
never happens even with no active session, inspect the flag dir for a stuck
"reboot-pending-across-a-deferred-day" marker that might be preventing it from re-attempting.

## Re-scoping to more hosts

Do not remove the `--limit archlinux` guard from routine runs until the design in
`Areas/Archlinux/Plans/auto-updates.md` is explicitly validated on `lemurpro` too — the play
targets the whole `cachyos_workstations` group by default specifically so that validation is a
one-flag change, not a code change, when the time comes.
