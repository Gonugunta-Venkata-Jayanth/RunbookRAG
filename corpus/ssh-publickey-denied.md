---
title: SSH "Permission denied (publickey)"
category: linux
tags: ssh, keys, permissions
---
## Symptoms
Connecting with `ssh user@host` fails immediately with "Permission denied (publickey)" even though the key was added to the server.

## Diagnosis
Run the client with `ssh -vvv` to see which keys are offered and whether the server rejects them. On the server, check `journalctl -u ssh` for "Authentication refused: bad ownership or modes". sshd ignores authorized_keys when the home directory, ~/.ssh or the file is writable by group or others. Confirm the login user is correct; Amazon Linux uses ec2-user and Ubuntu images use ubuntu.

## Resolution
Fix permissions with `chmod 700 ~/.ssh` and `chmod 600 ~/.ssh/authorized_keys`, and make sure the user owns both. Pass the right key explicitly with `ssh -i key.pem`. On SELinux systems run `restorecon -Rv ~/.ssh`. For a lost key on EC2, use EC2 Instance Connect or Session Manager to add a new public key.

## Prevention
Manage authorized keys through configuration management, keep a second access path such as Session Manager, and document the default user for each image.
