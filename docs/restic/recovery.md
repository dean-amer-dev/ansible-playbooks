# restic — recovery

## Timer/service never installed, no error shown

Every copy/symlink task in this role is `failed_when: false` — by design, so a host that hasn't
run `dotfiles` yet doesn't hard-fail this role, but that also means a missing source file fails
**silently**. Check directly:

```bash
systemctl status backup.timer backup.service
ls -la /usr/local/sbin/backup.sh
ls ~/projects/dotfiles/scripts/meta/backup/
```

If the dotfiles paths don't exist, run (or re-run) the `dotfiles` role first, then re-run `restic`.

## Backup runs but fails

```bash
systemctl status backup.service
journalctl -u backup.service -n 100 --no-pager
/usr/local/sbin/backup.sh   # run directly to see live output
```

The actual backup logic lives in the dotfiles repo
(`scripts/meta/backup/backup.service`/`.timer`, sourced by this role with `remote_src: true`), not
in this Ansible role — a failing backup is almost always a dotfiles-repo-level issue (repo config,
restic repository/credentials, target storage), not something to chase in
`roles/restic/tasks/main.yml`.

## Timer isn't enabled after a run

```bash
systemctl is-enabled backup.timer
```

If disabled, this role's last task (`Enable restic backup timer`) is also `failed_when: false` —
check for an earlier silent failure (missing timer file) before re-running; enabling a
nonexistent unit fails quietly here too.
