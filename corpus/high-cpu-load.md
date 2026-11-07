---
title: Sustained high CPU load
category: linux
tags: cpu, performance, load average
---
## Symptoms
The server feels slow, requests time out and the load average reported by `uptime` stays well above the number of CPU cores for minutes at a time.

## Diagnosis
Use `top` or `htop` sorted by CPU to find the busiest processes. Load average counts runnable and uninterruptible tasks, so a high load with idle CPUs points at processes blocked on disk or network I/O; check the `wa` column in `top` and run `iostat -x 1`. Use `pidstat -u 1` to see per-process usage over time and `perf top` to see hot functions. On virtual machines a high `st` (steal) value means the hypervisor is starving the guest.

## Resolution
Restart or throttle the runaway process, lower its priority with `renice +10 -p PID`, or cap it with a systemd `CPUQuota=` setting. If steal time is high, move to a larger or non-burstable instance type. Fix the root cause in code, such as busy loops, missing caching or unbounded retries.

## Prevention
Track CPU, load average and steal time per host, set CPU limits on containers and systemd units, and load-test before releases so regressions are caught early.
