---
title: DNS resolution failures
category: networking
tags: dns, networking, resolv.conf, systemd-resolved
---
## Symptoms
Commands fail with "Temporary failure in name resolution" or "Could not resolve host", while connecting by IP address still works.

## Diagnosis
Check which resolver is configured in /etc/resolv.conf; on systemd-resolved hosts it points to 127.0.0.53 and `resolvectl status` shows the upstream servers. Query directly with `dig example.com @1.1.1.1` to separate resolver problems from network problems. Confirm outbound UDP and TCP port 53 are allowed by the firewall. Inside Docker, containers copy the host resolver configuration at start-up.

## Resolution
Restart the resolver with `sudo systemctl restart systemd-resolved`, correct the upstream servers in the netplan or NetworkManager configuration, or point resolv.conf at a working resolver. In a VPC, make sure DNS resolution and DNS hostnames are enabled. Restart containers after fixing the host resolver.

## Prevention
Configure at least two resolvers, monitor resolution latency from each host, and avoid hand-editing resolv.conf on systems where a network manager regenerates it.
