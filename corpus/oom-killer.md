---
title: Process killed by the OOM killer
category: linux
tags: memory, oom, cgroups, swap
---
## Symptoms
A process disappears without an application error, a container exits with code 137, or a service restarts unexpectedly. Kernel logs contain "Out of memory: Killed process".

## Diagnosis
Search the kernel ring buffer with `dmesg -T | grep -i -E "killed process|out of memory"` or `journalctl -k`. The log lists the victim, its resident memory and the cgroup that hit its limit. Compare against the memory limit of the container or systemd unit (`systemctl show -p MemoryMax unit`). Use `free -h` and `ps aux --sort=-rss | head` to see current consumers.

## Resolution
Raise the memory limit if the workload legitimately needs more, or reduce memory use by lowering worker counts, heap sizes or batch sizes. For a JVM, set `-Xmx` below the container limit. Add a modest swap file to absorb short spikes on small instances. Protect critical daemons by setting `OOMScoreAdjust=-500` in their unit files.

## Prevention
Alert on memory usage approaching limits, set explicit requests and limits for every container, and profile memory growth to catch leaks before they reach production.
