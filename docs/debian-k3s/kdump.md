# debian-k3s: kernel crash dumps (kdump)

Added after gmktec-3 dropped off the cluster on 2026-10-05 with nothing in its logs that named a
cause. Tag: `kdump` (`roles/debian-k3s/tasks/kdump.yml`). The role never reboots a node.

## What it sets up
- `kdump-tools` + `kexec-tools` + `makedumpfile`; `crashkernel=512M-:192M` is added to grub by the
  package. The reservation only exists after a reboot, and the play prints "Reboot needed" until then.
- Dumps land in `/var/crash/<timestamp>/` (`dump.*` = vmcore, `dmesg.*`), newest 3 kept.
- The kernel now panics (and so dumps, then reboots) on: oops (already on), soft lockup, hard
  lockup (NMI watchdog), unknown/unrecovered/IO NMI. Panic timeout stays 10 s.
- `kernel.hung_task_panic` is NOT set. Hung tasks on these nodes are NFS waits (tdarr on murderbot's
  NFS); panicking on them would reboot every NFS client when the server stalls.
- `kernel.sysrq` = 446 (Debian's 438 + 8) so a wedged-but-alive kernel can be dumped on demand.

## Rolling it out
1. Run with Alex's permission, one host at a time:
   `ansible-playbook -i inventory/inventory.ini playbooks/infrastructure/setup-debian-k3s.yml --limit gmktec-3 --tags kdump`
   (token: `export BWS_ACCESS_TOKEN="$(cat /home/alex/claude/bws-ro-token)"`). Second run must report 0 changed.
2. Reboot that node yourself, then confirm: `sudo kdump-config status` says "ready to kdump" and
   `cat /sys/kernel/kexec_crash_size` is non-zero.
3. Wait until etcd, Postgres, MongoDB and CouchDB replicas are healthy again before the next node.
4. Prove it once, on one node, in a window: `echo c | sudo tee /proc/sysrq-trigger` crashes it on
   purpose. It should reboot by itself and leave a dump in `/var/crash`. An untested kdump is worthless.

## When a node wedges again (do this BEFORE rebooting it)
The kernel may be alive while the network is dead (that is what the 2026-10-05 logs suggest), so no
panic fires by itself. Capture state first, then force a dump:
1. If ssh works: `ip -s link show lan0; ethtool -S lan0; ethtool lan0; sudo dmesg | tail -200; ss -s`
   and save the output off the box.
2. Force the dump: `echo c | sudo tee /proc/sysrq-trigger`, or at the console keyboard Alt+SysRq+c.
   The node dumps and reboots itself (allow several minutes for a 28 GB machine).
3. Afterwards: `ls -la /var/crash/` and read `/var/crash/<ts>/dmesg.<ts>`; full analysis with the
   `crash` tool and the matching `linux-image-*-dbg` vmlinux.
