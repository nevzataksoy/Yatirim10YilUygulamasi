# Post-Shadow P0 — Connection Pool Root-Cause Analysis

Date: 04 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Status

**Gate C: OPEN — BASELINE EVIDENCE COLLECTION**

Gate A (migration/observability) and Gate B (OneDir Windows runtime deployment) are complete. The next P0 task is to explain historical PostgreSQL pool acquisition failures such as:

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

Until runtime evidence exists:

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

The goal is to determine whether timeout events cluster around specific root jobs, long-duration jobs or scheduler overlaps before adding new runtime instrumentation.

## Gate C2 — Runtime pool instrumentation

Status: **PLANNED AFTER C1 REVIEW**

If C1 cannot explain the timeout mechanism, add behavior-preserving local instrumentation around `DatabaseService.connection()` to capture at minimum:

- connection checkout wait milliseconds,
- connection hold milliseconds,
- pool size / available / waiting statistics,
- root job name,
- run kind,
- repository/call-site operation,
- thread name,
- acquisition timeout/error events.

Instrumentation should write to a dedicated local rotating JSONL log instead of writing its own telemetry back through the same PostgreSQL pool. This avoids creating recursive measurement pressure on the resource being diagnosed.

A local CLI summary should then report p50/p95/max wait/hold times, timeouts, saturation samples and top operations/root jobs without opening a database connection.

## Decision gate after evidence

Only after C1/C2 evidence should remediation be selected. Possible causes to distinguish include:

- real pool-capacity saturation,
- long SQL/transaction hold times,
- nested connection acquisition,
- scheduler job overlap,
- database/network latency while opening or using PostgreSQL connections,
- connection leak/discard/replacement behavior,
- another caller outside the expected scheduler path.

Any eventual remediation must be proportional to the measured cause and remain behavior-preserving unless a separate model/runtime behavior change is explicitly approved.
