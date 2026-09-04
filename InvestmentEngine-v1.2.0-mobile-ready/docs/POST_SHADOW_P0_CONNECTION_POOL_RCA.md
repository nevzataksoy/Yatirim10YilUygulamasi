# Post-Shadow P0 — Connection Pool Root-Cause Analysis

Date: 04 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Status

**Gate C: OPEN — C2 PRODUCTION TELEMETRY COLLECTION**

Gate A (migration/observability) and Gate B (OneDir Windows runtime deployment) are complete. Gate C is now collecting production pool telemetry to explain historical PostgreSQL pool acquisition failures such as:

```text
couldn't get a connection after 10.00 sec
```

No pool sizing, scheduler cadence, retry policy or model behavior is changed by this RCA step.

## Current runtime facts

`DatabaseService` currently creates one synchronous `psycopg_pool.ConnectionPool` with:

```text
min_size = 1
max_size = 6
timeout  = 10 seconds
```

Repository methods use `DatabaseService.connection()` as a context manager and return the connection after their SQL scope completes.

The scheduler sets `max_instances=1` per job. This prevents duplicate concurrent instances of the same scheduler job, but different scheduler jobs may still overlap.

The engine code inspected in this gate generally performs external provider fetches before or between repository calls rather than deliberately holding one repository connection across the provider request. Therefore the current source does not by itself prove a long-held connection or prove that `max_size=6` is undersized.

## RCA rules

Until runtime evidence identifies a cause:

1. Do **not** increase `max_size` merely because a timeout occurred.
2. Do **not** increase the 10-second acquisition timeout to hide contention.
3. Do **not** add automatic retries to non-idempotent writes.
4. Do **not** serialize all scheduler jobs as a workaround.
5. Do **not** change signal thresholds, factor weights, K1/K2, reversal, reset, sizing, mode or Realtime Execution.

## Gate C1 — Historical baseline

Run:

```text
verification/verify_connection_pool_rca_baseline.sql
```

The file is SELECT-only and collects:

- exact pool-timeout rows from the last 30 days,
- all ERROR rows so unrelated failures remain distinguishable,
- jobs overlapping each pool-timeout interval,
- p50/p95/max job durations,
- highest job-run concurrency timestamps.

C1 evidence identified five historical 10-second pool checkout timeout records across `hourly_job` and `sec_event_job`. The highest recorded scheduler concurrency was `2`, while pool capacity is `6`, and no matching `system.job_runs` overlap explained the timeout intervals. This weakens the hypothesis that recorded scheduler-job concurrency alone exhausted all six pool slots.

`system.job_runs` is not a complete inventory of database consumers. Background paths such as `notification_dispatcher` also use PostgreSQL, so unrecorded concurrency remains an open hypothesis rather than a conclusion.

## Gate C2 — Runtime pool instrumentation

Status: **ACTIVE — PRODUCTION TELEMETRY COLLECTION**

Behavior-preserving local instrumentation is active around `DatabaseService.connection()` and records:

- connection checkout wait milliseconds,
- connection hold milliseconds,
- pool size / available / waiting statistics,
- queue/error/loss counters,
- root job name,
- run kind,
- repository/call-site operation,
- thread name,
- acquisition timeout/error events.

Instrumentation writes to dedicated per-process rotating JSONL logs and never writes its own telemetry back through PostgreSQL. The local summary script is:

```text
verification/summarize_connection_pool_telemetry.ps1
```

### Production rollout state

The frozen-runtime callsite parser fix has been rebuilt, preflight-tested and deployed to production. The production Windows Service is running from the OneDir installation and generated:

```text
C:\Program Files\Rosa\InvestmentEngine\logs\connection-pool-telemetry-15180.jsonl
```

Concrete callsite attribution is now verified in production. The first recorded pressured checkout was:

```text
callsite         database.repository.publish_health
wait_ms          1477.9
pool_size before 1
available before 0
pool_size after  2
requests_queued  1
requests_errors  0
returns_bad      0
connections_errors 0
connections_lost   0
```

A following sample returned both connections to the available pool and recorded a sub-second hold. This first production sample shows pool growth/connection creation during startup pressure, not pool-capacity saturation: pool size reached only `2` of `6`, while connection-health error/loss counters remained zero.

This single startup observation is not a root-cause finding. Historical 10-second failures still require longer production evidence that correlates `checkout_pressure`, `checkout_timeout`, `hold_slow`, `counter_delta` and `sample` events with pool occupancy, connection-establishment timing, callsite, root job and background database consumers.

## Decision gate after evidence

Only after sufficient C2 production evidence should remediation be selected. Causes to distinguish include:

- real pool-capacity saturation,
- long SQL/transaction hold times,
- nested connection acquisition,
- scheduler/background-consumer overlap,
- database/network latency while opening or using PostgreSQL connections,
- stale/bad connection discard or replacement behavior,
- database/server connection reset or loss,
- another caller outside the expected scheduler path.

Any eventual remediation must be proportional to the measured cause and remain behavior-preserving unless a separate model/runtime behavior change is explicitly approved.
