# ssh-keys — recovery

## "bws_access_token is required" / BWS fetch fails

This role fetches secrets itself (via `bws secret list` delegated to `localhost`), separately from
`fetch-secrets.yml`. If the fetch fails:

```bash
# Confirm the token works directly
bws secret list --access-token "$BWS_RO_TOKEN" --output json | head
```

A 401/403 here means the token itself is bad or lacks project access — get a fresh one before
re-running Ansible, don't retry the playbook against a token you haven't verified.

## Keys don't match what's expected on disk

Every key-writing task is `no_log: true`, so a diagnosis has to compare on the host, not in
Ansible output:

```bash
ssh archlinux
ls -la ~/.ssh/
ssh-keygen -lf ~/.ssh/alex_id_ed25519.pub   # fingerprint, safe to print
```

If the fingerprint doesn't match what BWS holds, the BWS secret itself was rotated — re-run this
role's tag (`--tags ssh-keys`) to push the current BWS value down; it always overwrites.

## Keys "disappear" after a later dotfiles run

This is expected, not a bug in this role — see `../dotfiles/recovery.md`. `dotfiles`'s dotbot run
symlinks `~/.ssh` to `~/projects/dotfiles/ssh/`; if that role's key-copy step didn't run first (or
was skipped with `--tags`), the keys these tasks wrote will appear to vanish because `~/.ssh` now
resolves to an empty (or stale) directory. Re-run `ssh-keys` then `dotfiles` together, in that
order, rather than `dotfiles` alone.
