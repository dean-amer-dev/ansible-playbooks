# restic — running

Installs the restic backup systemd timer from dotfiles (`backup.service`/`backup.timer` sourced
from `~/projects/dotfiles/scripts/meta/backup/`) and symlinks `/usr/local/sbin/backup.sh` to the
dotfiles-managed script. The `restic` package itself comes from `common`
(`cachyos_pacman_packages`). Runs in `setup-cachyos.yml` Play 11, **after** `dotfiles` (it needs
the dotfiles repo already cloned to source the service/timer/script files from) and after Komodo
Periphery bootstrap.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags restic
```

Must run after (or together with) `dotfiles` — running `restic` alone on a host where dotfiles
hasn't been cloned yet leaves the copy/symlink tasks quietly failing
(`failed_when: false` throughout this role, deliberately — see recovery.md).

## What a clean run looks like

- `changed=0` on repeat.
- `backup.timer` should be `enabled`+`active`: `systemctl status backup.timer`.

## Tags

`restic`, `service`.
