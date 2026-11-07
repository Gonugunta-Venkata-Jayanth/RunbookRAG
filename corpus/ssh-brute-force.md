---
title: SSH brute-force login attempts
category: security
tags: ssh, security, fail2ban, auth.log
---
## Symptoms
/var/log/auth.log or `journalctl -u ssh` fills with "Failed password" and "Invalid user" lines from many IP addresses, and CPU rises from sshd handling connections.

## Diagnosis
Count attempts per source with `grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -n`. Check whether any attempt succeeded by searching for "Accepted" lines from unknown addresses, and review `last` and `lastb`.

## Resolution
Disable password logins by setting `PasswordAuthentication no` and `PermitRootLogin no` in /etc/ssh/sshd_config, then reload sshd. Install fail2ban with an sshd jail to ban addresses after repeated failures. Restrict port 22 in the firewall or cloud security group to known administrative IP ranges. If any login succeeded unexpectedly, treat the host as compromised and rotate keys.

## Prevention
Use key-based authentication only, prefer a bastion host or AWS Systems Manager Session Manager instead of public SSH, and alert on bursts of authentication failures.
