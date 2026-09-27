# dotfiles — recovery

## dotbot reports "already exists" and skips a file

Dotbot cannot turn a real file/directory into a symlink — it reports `already exists` (exit 1 for
that item) and moves on rather than failing the whole run. This role pre-clears the three known
offenders on a fresh CachyOS account (`~/.ssh`, `~/.vim`, `~/.zshrc`) but **only when they are real
files, not symlinks** (checked via `ansible.builtin.stat` + `not item.stat.islnk`). If dotbot
reports this for some other path:

```bash
ssh archlinux
ls -la ~/<path>          # confirm it's a real file/dir, not already a symlink
rm -rf ~/<path>          # only after confirming — dotbot will symlink its own version in
ansible-playbook ... --tags dotfiles   # re-run
```

## SSH keys "disappeared" after this role ran

Expected if `ssh-keys` didn't run first in the same session — see `../ssh-keys/recovery.md`. This
role's own copy-before-symlink step (`Copy SSH keys into dotfiles/ssh/`) is `failed_when: false`,
so if the source files don't exist yet (because `ssh-keys` hasn't run), it silently no-ops instead
of failing loudly, and dotbot then symlinks `~/.ssh` to an empty `dotfiles/ssh/`. Fix: re-run both
roles together, `ssh-keys` before `dotfiles`.

## Clone fails via SSH

The initial clone uses `key_file: ~/.ssh/github` with `GIT_SSH_COMMAND` pointed at the same key —
if it fails, confirm that key exists and is authorized on GitHub for the `amerenda/dotfiles` repo
(the `ssh-keys` role must have already run and the deploy key must actually be added to the repo
on GitHub's side, which Ansible can't do for you).

## Pull fails / repo is in a weird state

The re-pull task uses `git pull --rebase --autostash`, which handles the common case (local dotbot
run left uncommitted generated files) automatically. If it still fails (real merge conflict,
detached HEAD, etc.), fix it directly on the host — `cd ~/projects/dotfiles && git status` — rather
than fighting it through Ansible; this role doesn't attempt any conflict resolution.
