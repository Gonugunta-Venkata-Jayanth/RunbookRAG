---
title: Too many open files
category: linux
tags: ulimit, file descriptors, systemd
---
## Symptoms
Applications log "Too many open files" or "EMFILE", new connections are refused under load and the error disappears after a restart.

## Diagnosis
Count descriptors held by the process with `ls /proc/PID/fd | wc -l` and compare with its limit in `cat /proc/PID/limits`. Services started by systemd ignore /etc/security/limits.conf and use the unit's `LimitNOFILE=` value. A steadily rising count indicates a descriptor leak, such as sockets or files that are never closed.

## Resolution
Raise the limit for the service by adding `LimitNOFILE=65536` in a drop-in created with `systemctl edit app`, then restart it. For interactive shells, raise it with `ulimit -n`. Fix leaks in code by closing files and sockets, for example with context managers.

## Prevention
Export the open descriptor count as a metric, set explicit limits in unit files and container runtimes, and include connection churn in load tests.
