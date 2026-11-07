---
title: Docker consuming all disk space
category: containers
tags: docker, disk, images, volumes
---
## Symptoms
/var/lib/docker grows until the host runs out of space, image pulls fail, and builds stop with "no space left on device".

## Diagnosis
Run `docker system df -v` to break usage down into images, containers, local volumes and build cache. Dangling images from repeated builds, stopped containers, unused volumes and an unbounded BuildKit cache are the usual causes. Large container log files live under /var/lib/docker/containers/*/*-json.log.

## Resolution
Remove unused objects with `docker system prune`; add `-a` to remove all images not used by a container and `--volumes` only after confirming no volume holds data you need. Clear the build cache with `docker builder prune --keep-storage 5GB`. Truncate an oversized container log with `truncate -s 0` on the JSON log file.

## Prevention
Configure log rotation in /etc/docker/daemon.json with `"log-opts": {"max-size": "10m", "max-file": "3"}`, schedule a weekly prune with a systemd timer, and keep /var/lib/docker on its own volume.
