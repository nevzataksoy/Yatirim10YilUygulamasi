# Post-Shadow P0 — Connection Pool Root-Cause Analysis

Date: 04 September 2026
Last evidence update: 05 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Status

**Gate C: OPEN — C2 LIFECYCLE CORRELATION ESTABLISHED; HISTORICAL 10-SECOND TIMEOUT NOT YET REPRODUCED**

Gate A (migration/observability) and Gate B (OneDir Windows runtime deployment) are complete. Gate C is collecting production pool telemetry to explain historical PostgreSQL pool acquisition failures such as:

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

The build environment used for the deployed callsite-fix runtime was explicitly checked and reports:

```text
psycopg      = 3.3.4
psycopg_pool = 3.3.1
```

The pool constructor does not override psycopg pool lifecycle defaults such as `max_idle` or `max_lifetime`. `psycopg_pool` 3.3.x documents a default `max_idle` of 600 seconds and `max_lifetime` of 3600 seconds, with lifetime reduced by a random amount up to 5% to avoid synchronized retirement. The observed recurrence below is strongly correlated with this lifecycle window, but the current telemetry does not record an explicit retirement reason and therefore does not by itself prove that `max_lifetime` is the retirement trigger.

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

Concrete callsite attribution is verified in production.

The first recorded pressured checkout from `PID 15180` was:

```text
ts               2026-09-04T16:39:01.776274+00:00
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

A following sample returned both connections to the available pool and recorded a sub-second hold. This startup sample shows pool growth / connection establishment during pressure, not pool-capacity saturation: pool size reached only `2` of `6`, while connection-health error/loss counters remained zero.

### C2 lifecycle / connection-establishment evidence

An earlier telemetry process (`PID 11496`) captured the same structural pattern under `notification_dispatcher`: pressure with `pool_size=1`, `pool_available=0`, pool growth while connection attempts were active, and no connection-health error/loss counters. The request waited `2231.766 ms` and the pool subsequently returned two connections as available.

The deployed callsite-fix process (`PID 15180`) then produced a repeated lifecycle-correlated series rather than a single startup-only event.

#### Recurrent pressure series in PID 15180

The primary pressure timestamps and approximate intervals are:

```text
2026-09-04T16:39:01.776274+00:00  startup / publish_health
2026-09-04T17:35:01.025789+00:00  +55m59s
2026-09-04T18:35:02.654610+00:00  +60m02s
2026-09-04T19:33:05.868580+00:00  +58m03s
2026-09-04T20:32:04.243825+00:00  +58m58s
2026-09-04T21:30:03.101150+00:00  +57m59s
```

These intervals repeatedly fall inside or immediately adjacent to the documented randomized one-hour `max_lifetime` window for `psycopg_pool 3.3.1`.

This is now a strong lifecycle correlation, not a one-off coincidence. However, because current telemetry observes pool counters rather than an explicit psycopg connection-retirement reason, this remains a mechanism-level finding rather than a final root-cause declaration.

#### 17:35 UTC overlap: scheduled + background consumer

At the first fixed-process lifecycle window, `sec_event_job` and `notification_dispatcher` overlapped.

`sec_event_job` / `database.repository.get_latest_holdings_tickers`:

```text
wait_ms             826.298
stats_before:
  pool_size         1
  pool_available    0
  connections_num   2
  connections_ms    2964

stats_acquired:
  pool_size         2
  pool_available    0
  requests_queued   2
  requests_wait_ms  2303
  connections_num   3
  connections_ms    2964
```

Immediately afterward, `notification_dispatcher` / `notifications.dispatcher._claim` waited `1058.41 ms` while both observed pool slots were unavailable.

This confirms that scheduler/background overlap can increase simultaneous demand during a lifecycle turnover window. It does **not** demonstrate six-slot exhaustion.

#### 18:35 UTC overlap: pool grows 1 -> 3 while demand queues

At the next lifecycle window, `sec_event_job` again overlapped with `notification_dispatcher`.

`sec_event_job`:

```text
wait_ms             2367.975
stats_before:
  pool_size         1
  pool_available    0
  requests_waiting  0
  connections_num   4
  connections_ms    6295

stats_acquired:
  pool_size         3
  pool_available    0
  requests_waiting  1
  requests_queued   5
  requests_wait_ms  5728
  connections_num   7
  connections_ms    8604
```

The overlapping `notification_dispatcher` checkout then waited `1431.755 ms`; by acquisition, cumulative `connections_ms` had risen to `10037` while `connections_num` was `7`. No request, return-bad, connection-error or connection-lost counter increased.

This is direct evidence of queued demand while the pool still has large configured headroom and is actively creating / preparing additional connections.

#### 19:33 UTC lifecycle event without scheduler job requirement

A later `notification_dispatcher`-only pressure event occurred with:

```text
wait_ms             3906.19
stats_before:
  pool_size         1
  pool_available    0
  requests_waiting  0
  connections_num   8
  connections_ms    11553

stats_acquired:
  pool_size         2
  pool_available    0
  requests_queued   6
  requests_wait_ms  11065
  connections_num   9
  connections_ms    15451

on return:
  pool_size         2
  pool_available    2
  connections_num   9
  connections_ms    19747
```

This event is especially important because it shows that scheduler/background overlap is not required for the pressure mechanism. A single `notification_dispatcher` checkout can wait several seconds while connection establishment / replacement is occurring and configured pool capacity remains far from `max_size=6`.

#### 20:32 UTC and 21:30 UTC recurrence

The pattern continued:

```text
20:32 UTC notification_dispatcher wait_ms = 2826.701
  before: pool_size=1, available=0, connections_num=10, connections_ms=19747
  acquired: pool_size=2, available=0, connections_num=11, connections_ms=22472
  returned: pool_size=2, available=2, connections_ms=25228

21:30 UTC notification_dispatcher wait_ms = 1851.238
  before: pool_size=1, available=0, connections_num=12, connections_ms=25228
  acquired: pool_size=2, available=0, connections_num=13, connections_ms=27078
```

Later normal samples returned to the steady state:

```text
pool_size           1
pool_available      1
requests_waiting    0
connections_num     13
connections_ms      29024
requests_errors     0
returns_bad         0
connections_errors  0
connections_lost    0
```

This repeated grow-and-shrink / replacement-associated pressure series substantially weakens real pool-capacity saturation as the primary explanation for the observed sub-10-second pressure events.

### Long-hold evidence

Long holds do occur independently:

```text
notification_dispatcher / notifications.dispatcher._enqueue_due
hold_ms = 2072.893
checkout wait_ms = 0.038

macro_job / database.repository.get_latest_macro_observations
hold_ms = 2809.409
checkout wait_ms = 0.023
```

These examples confirm that 2-3 second connection holds exist, but neither was correlated with checkout pressure or timeout at the same event. Long-hold contention therefore remains possible under overlap, but the current evidence does not make it the primary mechanism.

### Current classification

Across the collected fixed-process telemetry so far:

```text
checkout_timeout    0
requests_errors     0
returns_bad         0
connections_errors  0
connections_lost    0
max observed pool_size during pressure  3 of 6
```

Current evidence supports the following ranking:

1. **Connection lifecycle replacement / connection establishment latency — STRONGLY CORRELATED.**
   - pressure recurs on an approximately 56-60 minute cadence,
   - this matches the deployed `psycopg_pool 3.3.1` randomized one-hour lifetime window,
   - connection-attempt counters and cumulative establishment time rise during pressure,
   - pressure occurs with substantial capacity headroom.
2. **Database/network latency during new connection establishment — PLAUSIBLE CONTRIBUTOR.**
   - observed establishment-related waits range from sub-second to about 3.9 seconds,
   - no connection error/loss counters are required for the delay.
3. **Scheduler/background-consumer overlap — CONFIRMED CONTRIBUTOR IN SOME WINDOWS, NOT REQUIRED.**
   - `sec_event_job` and `notification_dispatcher` overlapped at lifecycle windows,
   - later `notification_dispatcher`-only events reproduced the same mechanism.
4. **Real pool-capacity saturation — CURRENTLY WEAK.**
   - maximum observed pool size during pressure is `3` of configured `6`.
5. **Stale/bad connection or connection reset/loss — NO CURRENT COUNTER EVIDENCE.**
   - `returns_bad`, `connections_errors`, `connections_lost` remain zero.
6. **Long hold / nested checkout — NOT ESTABLISHED AS PRIMARY CAUSE.**
   - isolated 2-3 second holds exist but are not yet causally correlated with pressure.

The remaining unresolved question is the historical `10.00 sec` timeout. The telemetry has now reproduced the likely pressure mechanism repeatedly but has not yet captured a checkout that crosses the configured 10-second acquisition timeout.

Therefore Gate C remains open. The next evidentiary milestone is either:

- a real `checkout_timeout` with the same lifecycle / connection-establishment signature, or
- enough additional lifecycle cycles to show whether connection-establishment latency occasionally approaches the 10-second threshold under production network / database conditions.

No `max_size`, timeout, retry, scheduler serialization, model threshold, factor-weight, K1/K2, sizing, mode or Realtime Execution change is justified at this point.

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
