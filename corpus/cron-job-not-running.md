---
title: Cron job does not run
category: linux
tags: cron, scheduling, environment
---
## Symptoms
A scheduled script works when run by hand but produces no output or side effects when started by cron.

## Diagnosis
Confirm cron started the job with `grep CRON /var/log/syslog` or `journalctl -u cron`. Cron runs with a minimal environment: PATH is usually only /usr/bin:/bin, the working directory is the home directory and no shell profile is loaded. Errors are mailed to the user and silently lost when no mail transfer agent is installed. A crontab line without a trailing newline, or a `%` character that is not escaped, also breaks the entry.

## Resolution
Use absolute paths for commands and files, set PATH at the top of the crontab, and redirect output with `>> /var/log/job.log 2>&1` so failures are visible. Escape `%` as `\%`. Make the script executable and give it a shebang line.

## Prevention
Consider systemd timers, which log to the journal and support `Persistent=true` to catch up on missed runs, and add a heartbeat check that alerts when a job has not completed on schedule.
