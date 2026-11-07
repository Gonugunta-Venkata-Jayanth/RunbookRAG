---
title: PostgreSQL "too many clients already"
category: database
tags: postgres, database, connections, pgbouncer
---
## Symptoms
Applications fail with "FATAL: sorry, too many clients already" or "remaining connection slots are reserved", typically during traffic peaks or after scaling out application instances.

## Diagnosis
Compare current connections with the limit using `SELECT count(*) FROM pg_stat_activity;` and `SHOW max_connections;`. Group by application and state to find idle connections held by pools that are too large. Many sessions in "idle in transaction" indicate application code that opens a transaction and never commits.

## Resolution
Reduce per-instance pool sizes so that instances multiplied by pool size stays below max_connections. Put PgBouncer in transaction pooling mode in front of the database. Terminate stuck sessions with `pg_terminate_backend(pid)` and set `idle_in_transaction_session_timeout`. Raise max_connections only with matching memory, because each connection reserves its own memory.

## Prevention
Size connection pools deliberately, use a pooler or Amazon RDS Proxy for serverless clients, and alert when connections exceed 80% of the limit.
