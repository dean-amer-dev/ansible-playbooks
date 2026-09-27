# amd-gpu — running

AMD RDNA 4 (`gfx1201` / RX 9070 XT) GPU config: adds the user to `video`/`render` groups, sets the
`HSA_OVERRIDE_GFX_VERSION` ROCm compatibility override, prefers Mesa RADV as the Vulkan ICD, and
loads the `amdgpu` kernel module at boot with full hardware video encode/decode enabled
(`ppfeaturemask=0xffffffff`). Packages themselves (mesa, ROCm, Vulkan) are installed by the
`common` role (`cachyos_pacman_packages`) — this role is config/group-membership only. Runs in
`setup-cachyos.yml` Play 2, after `kde-plasma`.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags amd-gpu
```

## What a clean run looks like

- `changed=0` on a repeat run — all tasks are `copy`/`user` with static content.
- Group membership (`video`, `render`) only takes effect on the user's **next login** — noted in
  the `setup-cachyos.yml` final summary, not something this role can force live.

## Tags

`amd-gpu`, plus sub-tags `groups`, `rocm`, `vulkan`, `kernel`.
