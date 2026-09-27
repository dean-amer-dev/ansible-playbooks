# dotfiles — running

Clones `github.com/amerenda/dotfiles` and runs `dotbot` to symlink it into place. Runs in
`setup-cachyos.yml` Play 4, immediately after `ssh-keys`. Because dotbot symlinks `~/.ssh` →
`~/projects/dotfiles/ssh/`, this role copies the SSH keys the `ssh-keys` role just wrote into
`dotfiles/ssh/` **before** running dotbot, so they survive the symlink swap instead of being
replaced/hidden by it.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags dotfiles
```

Run `ssh-keys` first (or together, `--tags ssh-keys,dotfiles`) on a fresh box — see
`../ssh-keys/recovery.md`.

## What a clean run looks like

- First run: clones the repo via SSH (using the `github` key from `ssh-keys`), builds/installs
  `dotbot` from AUR if missing, runs `dotbot -c install.conf.yaml`.
- Repeat runs: `git pull --rebase --autostash` (always reports `changed=false`, it's a plain
  shell task), then dotbot re-applies — reports `changed` only if dotbot actually created a new
  symlink/directory (`'Creating symlink' in stdout or 'Creating directory' in stdout`).
- Pre-existing stock files that would block dotbot's symlinks (`~/.ssh`, `~/.vim`, `~/.zshrc` —
  CachyOS ships real files/dirs at these paths on a fresh account) are removed automatically
  **only if they're real files, not already symlinks** — dotbot itself can't overwrite a real
  file/dir, it just silently reports "already exists" (exit code 1) and leaves it, which is why
  this role clears them first.

## Tags

`dotfiles`, `ssh-keys` (the SSH-key-copy sub-tasks specifically, shared with the `ssh-keys` role's
namespace).
