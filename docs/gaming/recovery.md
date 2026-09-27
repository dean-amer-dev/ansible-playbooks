# gaming — recovery

## Controller not detected (8BitDo or similar needing real USB probing)

```bash
# Confirm the libusb symlink actually landed
ls -la ~/.local/share/Steam/ubuntu12_32/steam-runtime/lib/x86_64-linux-gnu/libusb-1.0.so.0
ls -la ~/.local/share/Steam/ubuntu12_32/steam-runtime/lib/i386-linux-gnu/libusb-1.0.so.0
# Should point at /usr/lib/libusb-1.0.so.0 and /usr/lib32/libusb-1.0.so.0 respectively
```

If Steam or an update has overwritten the symlink with a real file again (Steam Runtime updates
can do this), re-run this role's `libusb` tag — it re-applies the symlink with `force: true`. The
original bundled files remain backed up at the same path with a `.orig` suffix if you ever need
to restore Steam's default (broken) behavior.

## GameMode not activating in-game

```bash
systemctl status gamemoded
gamemoded -s          # should print "gamemode active: no" when idle
groups $(whoami) | grep gamemode
```

Group membership (`gamemode`) only takes effect on next login — if a user was just added to the
group in this run, log out/in (or reboot the session) before assuming it's broken.

## Steam won't launch under Proton-GE

```bash
paru -Qi proton-ge-custom-bin
```

If the package isn't there, this role's AUR loop failed silently in a prior run (check for a real
error in that run's output) — re-run `--tags gaming` to retry the install.
