---
title: Port already in use
category: linux
tags: networking, ports, sockets
---
## Symptoms
A service fails to start with "bind: address already in use" or "EADDRINUSE", or Docker reports "port is already allocated".

## Diagnosis
Find the listener with `sudo ss -ltnp 'sport = :8080'` or `sudo lsof -i :8080`. The holder is often an earlier instance of the same service, a container that publishes the port, or a socket-activated systemd unit. Sockets in TIME_WAIT do not block a new listener when the application sets SO_REUSEADDR.

## Resolution
Stop the conflicting process or container, or move one of the services to a different port. If an old instance did not exit, check why its shutdown hangs and kill it with `kill -TERM PID`, escalating to `kill -9` only if needed. For a socket-activated unit, stop both the .socket and the .service units.

## Prevention
Document port assignments per host, manage services through systemd or Compose so duplicate instances are not started by hand, and make applications read the port from configuration.
