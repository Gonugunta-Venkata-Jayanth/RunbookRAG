---
title: Root filesystem is full
category: linux
tags: disk, filesystem, logs, journald
---
## Symptoms
Writes fail with "No space left on device". Services crash while writing logs or temporary files, package installs abort, and `df -h /` reports 100% use on the root filesystem.

## Diagnosis
Run `df -h` to confirm which mount is full, then `sudo du -xh --max-depth=1 / | sort -h` to find the largest top-level directories without crossing into other mounts. The usual culprits are /var/log, /var/lib/docker, /tmp and core dumps. Check the systemd journal size with `journalctl --disk-usage`. A file that was deleted while a process still holds it open keeps consuming space; list those with `sudo lsof +L1`.

## Resolution
Vacuum the journal with `sudo journalctl --vacuum-size=500M`. Compress or remove rotated logs under /var/log. Clean the package cache with `sudo apt-get clean` or `sudo dnf clean all`. For deleted-but-open files, restart the owning service so the kernel releases the blocks. Remove old kernels with `sudo apt-get autoremove`.

## Prevention
Set `SystemMaxUse=` in /etc/systemd/journald.conf, configure logrotate with compression and a retention count, and alert when disk usage crosses 80%. Keep application data on a separate volume so a runaway log cannot fill the root filesystem.
