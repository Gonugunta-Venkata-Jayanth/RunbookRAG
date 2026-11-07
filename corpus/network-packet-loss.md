---
title: Intermittent network packet loss
category: networking
tags: networking, latency, packet loss, mtu
---
## Symptoms
Connections stall or reset intermittently, throughput is far below the link speed, and latency to some destinations spikes while others are fine.

## Diagnosis
Run `mtr -rwzc 100 destination` to see loss and latency per hop; loss that starts at one hop and continues to the destination is real, while loss only at intermediate hops is often ICMP rate limiting. Check interface errors and drops with `ip -s link` and `ethtool -S eth0`. Test for MTU problems with `ping -M do -s 1472 destination`; failures at that size behind a VPN or tunnel indicate a path MTU issue.

## Resolution
Replace faulty cables or move to a healthy interface when error counters grow. Lower the MTU or enable TCP MSS clamping on tunnels. Raise NIC ring buffers with `ethtool -G` if drops are caused by bursts. Escalate to the provider with mtr output when loss starts outside your network.

## Prevention
Monitor interface error counters, latency and loss with continuous probes, and record MTU settings for every tunnel and VPN.
