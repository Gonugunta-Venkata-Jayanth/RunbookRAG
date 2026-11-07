---
title: EC2 instance unreachable
category: aws
tags: aws, ec2, security groups, vpc
---
## Symptoms
SSH or HTTP connections to an EC2 instance time out, although the console shows the instance as running.

## Diagnosis
Check the instance status checks: a failed system check points at AWS hardware, a failed instance check points at the operating system, such as a full disk or a broken fstab. Verify the security group allows the port from your IP, the network ACL allows both inbound traffic and the outbound ephemeral port range, and the subnet route table sends 0.0.0.0/0 to an internet gateway. Confirm the instance has a public IP or Elastic IP. Use the EC2 serial console or "Get system log" to read boot messages.

## Resolution
Add the missing security group or NACL rule, attach an Elastic IP, or fix the route table. For a failed system check, stop and start the instance to move it to new hardware. For an operating system problem, detach the root volume, attach it to a rescue instance and repair it.

## Prevention
Manage network rules with infrastructure as code, enable CloudWatch alarms with automatic recovery on status check failure, and use Session Manager so access does not depend on open inbound ports.
