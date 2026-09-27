# hardware-tweaks — running

Machine-specific hardware configuration for the archlinux/CachyOS workstation: low-latency audio
(RTC/HPET max user frequency), HDMI EDID override + forced 4:2:0 chroma (TV/receiver with no DDC
at boot, inline CEC dongle can't carry 4K60 at full chroma), `keyd` capslock→esc remap, and udev
rules (ethernet/USB-hub power-save disable, 8BitDo controller fixes). Also disables broken
LAN-ULA IPv6, scoped to `archlinux` only within this role. Runs in `setup-cachyos.yml` Play 5,
after `dotfiles`.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags hardware-tweaks
```

## What a clean run looks like

- `changed=0` on a repeat run for every `copy`/`file`/`systemd` task.
- Handlers (`Reload systemd daemon`, `Restart keyd`, `Reload udev rules`) only fire when their
  triggering file actually changed — a no-drift run touches nothing live.

## Why `force_yuv420_output` is set

Confirmed live 2026-08-29: the Pulse-Eight CEC dongle sitting inline in the video path (GPU →
dongle → receiver → TV) can't carry 3840x2160@60 at the driver's default higher-bandwidth
chroma/bit-depth negotiation, even though the TV's real EDID legitimately advertises 4K60 support
— the injected EDID has no way to represent the dongle's own separate bandwidth ceiling. Forcing
4:2:0 chroma halves the required bandwidth and gets a real picture through at full
resolution/refresh. This has been confirmed to persist across the daemon's own
`udevadm trigger --action=change` connector rescans, so it's set once here rather than re-applied
per activation.

## Tags

`hardware-tweaks`, plus sub-tags `audio`, `edid`, `keyd`, `udev`, `network`, `ipv6`.
