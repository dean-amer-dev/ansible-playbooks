# mouse-hide — recovery

## Cursor is visible again after being hidden

```bash
cat ~/.config/kcminputrc | grep -A2 '\[Mouse\]'
cat ~/.icons/default/index.theme
```

Both should point at `invisible` (or whatever `mouse_hide_theme` was last set to). If they do but
the cursor still shows, KWin may need a live reconfigure:

```bash
qdbus6 org.kde.KWin /KWin reconfigure
```

If an app-specific override (Steam overlay, a GTK app) still shows a themed cursor despite this,
check `roles/mouse-hide/vars/main.yml`'s `mouse_hide_cursor_names` list covers the cursor name that
app actually requests — add it and re-run if not.

## Restoring the normal cursor didn't fully take effect

```bash
ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=<TOKEN>" --limit "archlinux,localhost" \
  --tags mouse-hide -e mouse_hide_theme=breeze_cursors
qdbus6 org.kde.KWin /KWin reconfigure
```

Some apps cache the cursor theme for the life of their process — a restart of that specific app
(not just the reconfigure) may be needed on top of the Ansible change.

## `xcursorgen` compile step never re-runs after changing the source image

The compile task uses `creates: /usr/share/icons/invisible/cursors/invisible_cursor` — once that
file exists, Ansible will never recompile it, even if the source PNG
(`mouse_hide_transparent_png_b64`) changes. Remove that file manually before re-running if the
underlying source ever needs to change (unlikely — it's a static 1x1 transparent PNG by design).
