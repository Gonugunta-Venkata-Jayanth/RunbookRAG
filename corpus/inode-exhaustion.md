---
title: Inodes exhausted while disk space remains
category: linux
tags: disk, inodes, filesystem
---
## Symptoms
New files cannot be created and the error is "No space left on device", yet `df -h` still shows free gigabytes. Mail queues, PHP session directories and cache folders stop accepting new entries.

## Diagnosis
Run `df -i` and look for a mount at or near 100% IUse. Find the directory holding millions of small files with `sudo find / -xdev -type f | cut -d/ -f2-3 | sort | uniq -c | sort -n | tail`. Common sources are session files, cache shards, unprocessed mail and orphaned build artefacts.

## Resolution
Delete the small files in bulk with `find /path -type f -mtime +7 -delete`, which is far faster than `rm *` and avoids "argument list too long". If the directory belongs to an application, stop the application first. Inode counts on ext4 are fixed at format time, so a filesystem that legitimately needs more inodes must be recreated with `mkfs.ext4 -N` or migrated to XFS, which allocates inodes dynamically.

## Prevention
Monitor inode usage alongside byte usage, add cleanup timers for session and cache directories, and store large numbers of tiny objects in a database or object store instead of the filesystem.
