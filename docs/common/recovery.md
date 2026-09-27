# common — recovery

## Multilib "always shows changed" (fixed)

The task enabling `[multilib]` in `pacman.conf` used to report `changed` on every run because its
`changed_when` check did a plain substring match for `enabled` — which also matches the
`already_enabled` sentinel the script prints when multilib is already on. Fixed with an exact
`== 'enabled'` comparison. If you see this regress (multilib task always shows `changed` even
though `grep '\[multilib\]' /etc/pacman.conf` shows it's already enabled), check
`roles/common/tasks/main.yml`'s `changed_when` on that task hasn't reverted to a substring match.

## paru / AUR build failures

`paru` is built from source via `makepkg -si` under `~/.cache/paru-build/paru` (cloned from the
AUR, non-root). If this fails:

```bash
# Re-run just the paru tasks
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=<TOKEN>" --limit "archlinux,localhost" --tags paru

# Inspect the build directory directly on the host
ssh archlinux
cd ~/.cache/paru-build/paru && makepkg -si
```

A stale/corrupt clone in `~/.cache/paru-build/paru` is the most common cause — remove that
directory and re-run; the role clones fresh via `ansible.builtin.git` with `update: true`.

## Sudo lockout

If passwordless sudo is somehow broken (bad edit to
`/etc/sudoers.d/<user>-ansible-bootstrap`), the file is written with
`validate: "visudo -cf %s"`, so Ansible itself refuses to write a syntactically broken sudoers
file — a broken sudo state on a live host means something else touched that file outside this
role. Fix: log in as the user directly (their SSH key still works independent of sudo) and inspect
`/etc/sudoers.d/` by hand, or re-run with `--tags sudo-bootstrap --ask-become-pass` to rewrite it
from a known-good state.
