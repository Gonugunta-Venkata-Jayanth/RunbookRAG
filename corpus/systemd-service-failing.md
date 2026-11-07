---
title: systemd service fails to start
category: linux
tags: systemd, services, journald
---
## Symptoms
`systemctl start app` returns an error, the unit shows "failed" or "activating (auto-restart)" in `systemctl status`, and the application is unreachable after a reboot.

## Diagnosis
Run `systemctl status app` for the last log lines and exit code, then `journalctl -u app -b --no-pager -n 100` for the full output of the current boot. Exit status 203/EXEC means the ExecStart binary is missing or not executable; 217/USER means the configured user does not exist. Check that environment files referenced by `EnvironmentFile=` exist. Validate the unit with `systemd-analyze verify /etc/systemd/system/app.service`.

## Resolution
Fix the path, permissions or user in the unit file, then run `sudo systemctl daemon-reload` before restarting, because systemd caches unit definitions. If the unit hit its start limit, clear it with `systemctl reset-failed app`. Enable it at boot with `systemctl enable --now app`.

## Prevention
Use `Restart=on-failure` with `RestartSec=` to recover from transient errors, declare dependencies with `After=` and `Wants=network-online.target`, and keep unit files in version control.
