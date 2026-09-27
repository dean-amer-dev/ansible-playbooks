# desktop-apps — recovery

## An AUR package fails to build/install

```bash
# Re-run just this role
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=<TOKEN>" --limit "archlinux,localhost" --tags desktop-apps

# Or build it directly on the host to see the real paru/makepkg output
ssh archlinux
paru -S <package>
```

The Ansible task's `changed_when` only inspects stdout for `there is nothing to do` — any real
build failure surfaces as a normal Ansible task failure with paru's own error in the output, so
check that first before re-running blind.

## WinBoat doesn't work

Confirm `/dev/kvm` exists (`ls -la /dev/kvm`) — this role only warns if it's missing, it cannot
enable virtualization for you. Enable VT-x/AMD-V in BIOS/UEFI, reboot (tell Alex — see CLAUDE.md's
no-reboot rule), then re-run this role's tag to clear the warning.

## Dropbox service won't stay running

This task is `failed_when: false` by design (a host where Dropbox has never been paired/logged in
will legitimately fail to start) — check manually:

```bash
systemctl --user status dropbox
journalctl --user -u dropbox -n 50
```

If it's failing because Dropbox isn't linked to an account yet, that's a one-time manual
`dropbox start -i` / GUI login step, not something this role automates.
