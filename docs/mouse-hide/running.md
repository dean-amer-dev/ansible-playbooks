# mouse-hide — running

Builds a fully transparent "invisible" Xcursor theme (from a 1x1 transparent PNG via
`xcursorgen`) and applies it, so the cursor has no visible pixels regardless of what re-triggers
KDE's idle-based cursor-visibility timer — sidesteps fighting that timer directly (out of scope
by design; any input event, including whatever couch-mode's controller generates, would just make
the real cursor reappear). Runs in `setup-cachyos.yml` Play 5a, deliberately **independent** of
joystick-notify — it never touches that daemon, Sunshine, or CEC, so running this role alone never
risks a live couch-mode/CEC/Steam Big Picture session.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags mouse-hide
```

To restore the normal cursor:

```bash
ansible-playbook ... --tags mouse-hide -e mouse_hide_theme=breeze_cursors
```

## What a clean run looks like

- The cursor compile step (`xcursorgen`) uses `creates:`, so it only runs once — `changed=0` on
  every subsequent run unless the theme is removed.
- `kwriteconfig6`/`qdbus6 reconfigure` tasks apply the theme **live** under Wayland (no logout
  needed) — `kapplymousetheme` is not used because it hard-refuses to run under Wayland.

## Why this is independent of joystick-notify

Deliberately not wired into automatic couch/desk switching — running this role never risks
restarting `joystick-notify.service`, Sunshine, or interrupting a live CEC/Steam Big Picture
session. Automatic cursor hiding on couch-mode entry is a separate joystick-notify code change
(`actions/cursor.py`), deployed on its own schedule, not part of this role.

## Tags

`mouse-hide`.
