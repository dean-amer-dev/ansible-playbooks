# amd-gpu — recovery

## GPU tools report the wrong gfx version / ROCm tool fails to detect the GPU

`HSA_OVERRIDE_GFX_VERSION` (written to `/etc/environment.d/99-rocm-gfx-override.conf`) exists
specifically because some ROCm tooling doesn't yet list `gfx1201` (RDNA 4) in its supported
version table and needs this override to run at all. If a ROCm tool misbehaves:

```bash
cat /etc/environment.d/99-rocm-gfx-override.conf
env | grep HSA_OVERRIDE
rocminfo | grep gfx
```

Confirm the override is actually loaded in the shell/session you're testing from — a fresh login
is required after this role first runs (`/etc/environment.d` is read at login, not live).

## Wrong Vulkan driver in use (AMDVLK instead of RADV)

```bash
vulkaninfo --summary | grep driverName
```

If it's not RADV, check `/etc/environment.d/99-amd-vulkan.conf` is present and the session was
started after this role ran (same login-time-read caveat as above). `VK_ICD_FILENAMES` there
explicitly lists only the RADV ICD JSONs.

## No hardware acceleration / amdgpu module not loaded

```bash
lsmod | grep amdgpu
cat /etc/modules-load.d/amdgpu.conf
cat /etc/modprobe.d/amdgpu.conf
```

If `amdgpu` isn't loaded, this is almost certainly a kernel/driver issue outside this role's
scope (the role only writes the boot-time load config and the `ppfeaturemask` option) — check
`dmesg | grep amdgpu` for a hardware/firmware error before assuming the Ansible config is wrong.
