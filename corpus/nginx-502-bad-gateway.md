---
title: nginx returns 502 Bad Gateway
category: web
tags: nginx, proxy, upstream, gunicorn
---
## Symptoms
Users see "502 Bad Gateway" from nginx while nginx itself is running. The error log shows "connect() failed (111: Connection refused) while connecting to upstream" or "upstream prematurely closed connection".

## Diagnosis
Read /var/log/nginx/error.log for the exact upstream error. Confirm the backend process (gunicorn, uvicorn, php-fpm, Node) is running and listening on the address in `proxy_pass` with `ss -ltnp`. For Unix sockets, check that the socket file exists and that the nginx worker user can read it. Test the backend directly with `curl http://127.0.0.1:8000/health`.

## Resolution
Start or restart the backend service, fix a mismatched port or socket path, and correct socket permissions. If workers crash under load, increase their count or memory. When responses are slow rather than refused, raise `proxy_read_timeout`, though a 504 Gateway Timeout is the more typical symptom of slowness.

## Prevention
Run backends under systemd with restart policies, add a health check endpoint, and alert on the rate of 5xx responses in the nginx access log.
