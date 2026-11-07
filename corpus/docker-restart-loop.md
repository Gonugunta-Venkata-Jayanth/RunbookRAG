---
title: Container stuck in a restart loop
category: containers
tags: docker, containers, exit codes, healthcheck
---
## Symptoms
`docker ps` shows a container with status "Restarting" or an uptime that never exceeds a few seconds, and the service is intermittently unavailable.

## Diagnosis
Read the output of the last attempt with `docker logs --tail 100 container`. Inspect the exit code with `docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}}' container`. Exit code 137 means the process was killed, usually by the OOM killer; 1 is an application error; 126 and 127 mean the entrypoint is not executable or not found. A failing HEALTHCHECK combined with an orchestrator restart policy produces the same pattern.

## Resolution
Fix the configuration error reported in the logs, such as a missing environment variable or an unreachable database. Raise the memory limit if OOMKilled is true. Run the image interactively with `docker run --rm -it --entrypoint sh image` to debug the entrypoint. Temporarily set `--restart no` to stop the loop while investigating.

## Prevention
Validate configuration at start-up with clear error messages, add backoff when waiting for dependencies, and test images in CI with a smoke test that calls the health endpoint.
