# ssh-keys — running

Fetches alex's main identity key and the GitHub deploy key from BWS and writes them to
`~/.ssh/` on the target (non-root — `become: false` at the play level). Runs in `setup-cachyos.yml`
Play 3, after `common`/GPU/desktop roles and **before** `dotfiles` (dotbot later symlinks
`~/.ssh` → `~/projects/dotfiles/ssh/`; the `dotfiles` role itself is responsible for copying these
keys into that destination before running dotbot, so they survive the symlink swap).

Keys written: `alex_id_ed25519` (+ `.pub`), `github` (+ `.pub`), and the alex public key appended
to `authorized_keys`.

## Invocation

```bash
ansible-playbook -i inventory/inventory.ini \
  playbooks/infrastructure/setup-cachyos.yml \
  --extra-vars "bws_access_token=$BWS_RO_TOKEN" \
  --limit "archlinux,localhost" \
  --tags ssh-keys
```

`bws_access_token` is required for this role specifically — the play's `pre_tasks` assert it's set
and fail immediately with a clear message if not (independent of whether `fetch-secrets.yml`
already ran for other roles, since this role does its own `bws secret list` on localhost).

## What a clean run looks like

- `changed=0` on a repeat run — all four `copy` tasks and the `authorized_key` task are idempotent
  against identical content.
- No output showing key material — every task here is `no_log: true`.

## Tags

`ssh-keys`.
