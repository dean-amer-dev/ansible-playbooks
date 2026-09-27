# power-profiles — running

Idle-based `power-profiles-daemon` switching: performance while in use, `power-saver` when idle.
`power-profiles-daemon` has no idle detection of its own (confirmed — only manual/app-requested
switching), so this pairs it with `swayidle` (standard Wayland `ext-idle-notify-v1` protocol,
which KWin implements) running as a **user** service, since `power-profiles-daemon`'s polkit
check requires an authenticated active local session (a root/system-level caller is denied). Runs
in `setup-cachyos.yml` Play 5b, after `mouse-hide`.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags power-profiles
```

## What a clean run looks like

- `changed=0` on repeat for package/service tasks.
- The unit-file `template` task explicitly restarts `idle-power-profile.service` when its content
  changes (`state: started` alone won't restart an already-running unit just because the file
  changed underneath it, so this role does it explicitly) — expect one restart whenever the
  timeout/profile vars in `group_vars/cachyos_workstations.yml` (`cachyos_power_idle_timeout_seconds`,
  `cachyos_power_active_profile`, `cachyos_power_idle_profile`) change.

## Checking current state

```bash
systemctl --user status idle-power-profile.service
powerprofilesctl get
tail -f ~/.local/state/power-profile-switch.log   # logs every switch
```

## Tags

`power-profiles`, plus sub-tags `packages`, `service`.
