# hardware-tweaks — recovery

## TV/receiver shows no picture or wrong resolution at boot

```bash
sudo systemctl status hdmi-edid-override.service
cat /sys/kernel/debug/dri/1/HDMI-A-1/edid_override    # should reflect tv.bin
cat /sys/kernel/debug/dri/1/HDMI-A-1/force            # should be "on"
cat /sys/kernel/debug/dri/1/HDMI-A-1/force_yuv420_output   # should be "1"
```

If the service ran but the picture is still wrong, re-trigger a connector rescan without a reboot:

```bash
sudo systemctl restart hdmi-edid-override
```

If `/sys/kernel/debug/dri/1/HDMI-A-1` doesn't exist at all, the DRM connector index (`1`, `HDMI-A-1`)
may not match this host's actual GPU/output layout anymore (e.g. after a GPU swap) — check
`ls /sys/kernel/debug/dri/` and update the hardcoded paths in `roles/hardware-tweaks/tasks/main.yml`
if they've shifted.

## keyd remap not applying

```bash
sudo systemctl status keyd
cat /etc/keyd/default.conf
```

`[ids] *` matches every keyboard — if capslock→esc isn't remapping, check `keyd` itself is
running (not masked) and the config was actually reloaded (`notify: Restart keyd` fires only when
the file content changed).

## Controller (8BitDo) still not recognized after udev rules install

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
cat /etc/udev/rules.d/98-local-8bitdo.rules
```

If the rule file is present but the device still isn't recognized, capture `udevadm info` for the
actual connected device and compare vendor/product IDs against what's in the rule file — a new
8BitDo model/firmware revision may need a rule addition, which is a role file change, not a
runtime fix.

## Archlinux IPv6 disable didn't take / LAN feels slow again

This role's IPv6 disable is scoped to `archlinux` only (`when: inventory_hostname == 'archlinux'`)
and delegates to the shared `tasks/disable-broken-ipv6.yml` (repo root `tasks/`) — see that file's
own comments for the underlying root cause (broken EdgeRouter RA ULA). murderbot and the Pi k3s
nodes get the same shared task from their own playbooks (`setup-debian-komodo.yml`,
`setup-rpi.yml`), not from this role — if a *different* cachyos_workstations member (e.g.
`lemurpro`) needs the same fix, it needs its own explicit handling; this role doesn't assume it's
safe there without checking that host's real upstream IPv6 situation first.
