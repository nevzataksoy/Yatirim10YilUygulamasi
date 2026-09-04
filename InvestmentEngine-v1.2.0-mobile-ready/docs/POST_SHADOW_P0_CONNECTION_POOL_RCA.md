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

The pool constructor does not override psycopg pool lifecycle defaults such as `max_idle` or `max_lifetime`. The project dependency accepts `psycopg[binary,pool]>=3.2,<4`; psycopg 3.x documents a default `max_idle` of 600 seconds and `max_lifetime` of 3600 seconds, with lifetime shortened by a small random amount to avoid synchronized retirement. This is relevant to lifecycle correlation below, but it is not itself proof of the historical timeout mechanism.

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

### C2 lifecycle / connection-establishment evidence

A second pressured checkout was captured by the previous telemetry process (`PID 11496`) under the `notification_dispatcher` maintenance root context:

```text
ts                  2026-09-04T16:31:03.330853+00:00
root_job_name       notification_dispatcher
run_kind            maintenance
wait_ms             2231.766

stats_before:
pool_size           1
pool_available      0
requests_queued     1
requests_wait_ms    1519
connections_num     2
connections_ms      3030
requests_errors     0
returns_bad         0
connections_errors  0
connections_lost    0

stats_acquired:
pool_size           2
pool_available      0
requests_queued     2
requests_wait_ms    3750
connections_num     4
connections_ms      5221
requests_errors     0
returns_bad         0
connections_errors  0
connections_lost    0
```

When that connection was returned approximately 1.26 seconds later, pool state was:

```text
pool_size           2
pool_available      2
connections_num     4
connections_ms      7388
requests_errors     0
returns_bad         0
connections_errors  0
connections_lost    0
```

This event is important because pressure occurred with `pool_size=1`, not with the pool near the configured `max_size=6`. During the request, `connections_num` increased from `2` to `4`, while cumulative connection-establishment time increased materially. The request was served after about 2.23 seconds and the pool then returned to two available connections.

The same structural pattern was present in the initial startup event: `pool_size=1`, `pool_available=0`, queueing while connection attempts were in progress, and pool growth to `2` after roughly 1.5 seconds. Together these events directly demonstrate that this runtime can queue requests while substantial pool-capacity headroom exists because connections are being prepared / established / replaced. They do **not** demonstrate six-slot capacity exhaustion.

The second pressure event occurred about 3485 seconds (58.1 minutes) after the initial startup pressure. Because the application leaves psycopg's connection-lifetime settings at their defaults, this timing falls inside the documented randomized one-hour lifetime-retirement window. A lifecycle replacement occurring near `max_lifetime`, combined with demand-triggered growth, is therefore a plausible and testable explanation for why two new connection attempts appeared around this event. This timing correlation is **not yet proof** that lifetime retirement caused the checkout wait; a repeat event with the fixed concrete callsite/process telemetry is required before promoting it to a root-cause finding.

A separate `notification_dispatcher` event recorded a `2441.983 ms` connection hold with only `0.017 ms` checkout wait. This confirms that ~2.4-second hold durations can occur, but this hold was not correlated with checkout pressure or a timeout in the observed sample and therefore does not currently establish long-hold contention as the cause.

Across the collected telemetry so far:

```text
checkout_timeout    0
requests_errors     0
returns_bad         0
connections_errors  0
connections_lost    0
max observed pool_size during pressure  2 of 6
```

Current evidence therefore weakens real pool-capacity saturation and strengthens connection establishment / lifecycle replacement / database-network latency as the mechanism to investigate next. It still does not explain why historical failures reached the full 10-second checkout timeout. C2 must capture either a future `checkout_timeout` or a materially slower pressure event and correlate it with connection-attempt counters, pool occupancy, callsite, root job, lifecycle timing, and connection-health counters.

The currently deployed callsite-fix process (`PID 15180`) has so far shown the startup `publish_health` pressure event followed by normal `notification_dispatcher` callsites with sub-millisecond checkout waits. A future lifecycle-turnover event from this process is especially valuable because concrete callsite attribution is now available.

## Decision gate after evidence

Only after sufficient C2 production evidence should remediation be selected. Causes to distinguish include:

- real pool-capacity saturation,
- long SQL/transaction hold times,
- nested connection acquisition,
- scheduler/background-consumer overlap,
- connection establishment or replacement latency while capacity headroom exists,
- database/network latency while opening or using PostgreSQL connections,
- stale/bad connection discard or replacement behavior,
- database/server connection reset or loss,
- another caller outside the expected scheduler path.

Any eventual remediation must be proportional to the measured cause and remain behavior-preserving unless a separate model/runtime behavior change is explicitly approved.
