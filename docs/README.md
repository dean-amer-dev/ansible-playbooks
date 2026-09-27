# ansible-playbooks — docs index

One `running.md` + `recovery.md` pair per role. `running.md` covers what the role does and exactly
how to invoke it; `recovery.md` covers known failure modes and how to fix them. Roles are grouped
below by where they're used, matching the playbooks in `playbooks/infrastructure/`.

## GMKtec Debian k3s cluster (Infrastructure 2.0)

| Role | Purpose |
|------|---------|
| [debian-k3s](debian-k3s/running.md) | Baseline + k3s HA server (embedded etcd), Cilium, CoreDNS, kube-vip for the `debian_k3s` GMKtec boxes. ([recovery](debian-k3s/recovery.md)) |

## CachyOS / Arch workstation bootstrap (`setup-cachyos.yml`)

| Role | Purpose |
|------|---------|
| [common](common/running.md) | Timezone, locale, hostname, multilib, base packages, `paru` AUR helper, default shell. ([recovery](common/recovery.md)) |
| [kde-plasma](kde-plasma/running.md) | KDE Plasma 6 + SDDM, autologin/lock pairing, DPMS-sleep-wake fix, power/display config, Bluetooth wakeup. ([recovery](kde-plasma/recovery.md)) |
| [amd-gpu](amd-gpu/running.md) | AMD RDNA 4 group membership, ROCm/Vulkan env config, `amdgpu` kernel module. ([recovery](amd-gpu/recovery.md)) |
| [gaming](gaming/running.md) | Steam/Proton-GE/GameMode config, Steam bundled-`libusb` fix for controller support. ([recovery](gaming/recovery.md)) |
| [docker](docker/running.md) | Docker daemon, group membership, DNS pinning, ARC runner GID alignment. ([recovery](docker/recovery.md)) |
| [desktop-apps](desktop-apps/running.md) | AUR desktop apps (VS Code, Cursor, Dropbox, NordPass, WinBoat). ([recovery](desktop-apps/recovery.md)) |
| [ssh-keys](ssh-keys/running.md) | Fetches alex's + GitHub SSH keys from BWS onto the workstation. ([recovery](ssh-keys/recovery.md)) |
| [dotfiles](dotfiles/running.md) | Clones `amerenda/dotfiles` and runs dotbot. ([recovery](dotfiles/recovery.md)) |
| [hardware-tweaks](hardware-tweaks/running.md) | Audio latency, HDMI EDID override, `keyd` remap, udev power-save/controller rules. ([recovery](hardware-tweaks/recovery.md)) |
| [mouse-hide](mouse-hide/running.md) | Invisible Xcursor theme for couch-mode mouse hiding. ([recovery](mouse-hide/recovery.md)) |
| [power-profiles](power-profiles/running.md) | Idle-based `power-profiles-daemon` switching via `swayidle`. ([recovery](power-profiles/recovery.md)) |
| [auto-updates](auto-updates/running.md) | Daily unattended `pacman -Syu` with snapper rollback. ([recovery](auto-updates/recovery.md)) |
| [moondeck](moondeck/running.md) | MoonDeckBuddy companion service for the MoonDeck SteamDeck plugin. ([recovery](moondeck/recovery.md)) |
| [sunshine](sunshine/running.md) | Sunshine game-stream host, screen unlock hooks, virtual display. ([recovery](sunshine/recovery.md)) |
| [joystick-notify](joystick-notify/running.md) | Controller-driven couch-mode automation, CEC wiring. ([recovery](joystick-notify/recovery.md)) |
| [restic](restic/running.md) | restic backup timer (script/units sourced from dotfiles). ([recovery](restic/recovery.md)) |

## k3s agent join (legacy Pi cluster)

| Role | Purpose |
|------|---------|
| [k3s-agent](k3s-agent/running.md) | Installs k3s agent and joins the legacy `[k3s]` cluster — used by `setup-cachyos.yml` (archlinux), `archlinux-k3s-agent.yml`, and `murderbot-k3s-agent.yml`. ([recovery](k3s-agent/recovery.md)) |

## Recovery/runbook playbooks (not tied to a single role)

Linked from the relevant role's `recovery.md` rather than duplicated here:

- `playbooks/infrastructure/k3s-recover.yml` — legacy Pi cluster smart recovery.
- `playbooks/infrastructure/k3s-full-recovery.yml` — legacy Pi cluster break-glass restore.
- `playbooks/infrastructure/k3s-image-gc.yml` — fleet-wide k3s/containerd image GC.
- `playbooks/infrastructure/smoke-test.yml` — read-only cluster health validation.
- `playbooks/infrastructure/fetch-secrets.yml` — BWS secret fetch, imported by most other playbooks.
- `playbooks/infrastructure/enable-etcd-metrics.yml`, `etcd-tmpfs.yml` — legacy Pi cluster etcd tuning.
