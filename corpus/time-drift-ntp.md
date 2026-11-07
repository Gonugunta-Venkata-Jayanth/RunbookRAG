---
title: System clock drift
category: linux
tags: time, ntp, chrony, clock
---
## Symptoms
TLS handshakes fail with "certificate is not yet valid", AWS API calls return "Signature expired" or "RequestTimeTooSkewed", Kerberos logins fail and log timestamps disagree between hosts.

## Diagnosis
Check synchronisation with `timedatectl status` and look for "System clock synchronized: yes". With chrony, run `chronyc tracking` for the current offset and `chronyc sources -v` for reachable servers. Confirm outbound UDP port 123 is allowed.

## Resolution
Enable time sync with `sudo timedatectl set-ntp true` and restart chronyd. Step a large offset immediately with `sudo chronyc makestep`. On EC2, use the Amazon Time Sync Service at 169.254.169.123, which needs no internet access.

## Prevention
Run chrony on every host, alert when the offset exceeds 100 ms, and avoid manually setting the clock on servers.
