---
title: TLS certificate expired or about to expire
category: security
tags: tls, ssl, certificates, certbot
---
## Symptoms
Browsers show "Your connection is not private" with NET::ERR_CERT_DATE_INVALID, API clients fail with "certificate has expired", and monitoring reports a falling days-to-expiry value.

## Diagnosis
Check the served certificate with `echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null | openssl x509 -noout -dates -issuer`. Confirm the web server is serving the renewed file and not a stale copy. For Let's Encrypt, run `sudo certbot certificates` and inspect the renewal timer with `systemctl list-timers | grep certbot`.

## Resolution
Renew with `sudo certbot renew`, then reload nginx or Apache so the new certificate is loaded. If HTTP-01 validation fails, ensure port 80 is reachable and not redirected away from /.well-known/acme-challenge. Install the full chain, not only the leaf certificate, to avoid intermediate errors on some clients.

## Prevention
Automate renewal with a timer and a deploy hook that reloads the server, and alert when any certificate has fewer than 21 days remaining. Managed certificates from AWS Certificate Manager renew automatically.
