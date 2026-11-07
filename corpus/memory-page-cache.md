---
title: Free memory looks low because of page cache
category: linux
tags: memory, page cache, free
---
## Symptoms
Monitoring shows almost no free memory on a healthy server, and `free -h` reports a small "free" value while applications run normally.

## Diagnosis
Read the "available" column in `free -h`, not "free". Linux uses otherwise idle RAM for the page cache to speed up file access, and that cache is released immediately when applications need memory. Real memory pressure shows up as a low available value, swap activity in `vmstat 1` (si and so columns), or OOM killer events.

## Resolution
No action is needed when available memory is healthy. Do not routinely run `echo 3 > /proc/sys/vm/drop_caches`, which only discards useful cache and slows the system. If available memory is genuinely low, find the largest consumers with `ps aux --sort=-rss` and reduce their usage or add RAM.

## Prevention
Alert on available memory and swap-in rate rather than free memory, and document the difference for anyone reading dashboards.
