# Post-Shadow P0 — Connection Pool Root-Cause Analysis

Date: 04 September 2026
Last evidence update: 06 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Status

**Development RCA: CLOSED / NON-BLOCKING**  
**Historical 10-second checkout timeout: NOT REPRODUCED DIRECTLY**  
**Production follow-up: OPEN as observation debt in GitHub Issue #2**

Gate A (migration/observability) and Gate B (OneDir Windows runtime deployment) are complete. Gate C produced sufficient development evidence to classify the historical PostgreSQL pool failures without changing pool sizing, acquisition timeout, scheduler cadence, retry policy or model behavior.

The historical error family is:

```text
couldn't get a connection after 10.00 sec
```

The remaining uncertainty is intentionally moved to production observation. Development work is no longer blocked on reproducing an exact 10-second timeout.

## Runtime invariants

`DatabaseService` uses one synchronous `psycopg_pool.ConnectionPool`:

```text
min_size = 1
max_size = 6
timeout  = 10 seconds
psycopg      = 3.3.4
psycopg_pool = 3.3.1
```

The scheduler uses `max_instances=1` per job. Different jobs and background consumers may still overlap.

No evidence from this RCA justifies changing:

```text
max_size = 6
timeout = 10 seconds
generic retry policy
scheduler serialization
model thresholds / weights
K1 / K2 / reversal / reset / sizing
Mode = SHADOW
Realtime Execution = OFF
```

## Historical baseline

`verification/verify_connection_pool_rca_baseline.sql` identified five historical 10-second checkout timeouts across `hourly_job` and `sec_event_job`.

The highest recorded scheduler concurrency was `2`, while configured pool capacity is `6`. `system.job_runs` is not a complete inventory of database consumers, because background paths such as `notification_dispatcher` also use PostgreSQL.

The post-Task7 `sec_event_job` ERROR was later rechecked directly from `system.job_runs`:

```text
id: 1642
started_at: 2026-08-29 03:35:15.183358+00
job_name: sec_event_job
status: ERROR
message: couldn't get a connection after 10.00 sec
```

Therefore this SEC ERROR is not a separate SEC-provider RCA. It belongs to the same historical connection-pool timeout family tracked here and in GitHub Issue #2.

## Runtime instrumentation

Behavior-preserving instrumentation around `DatabaseService.connection()` records:

- checkout wait milliseconds,
- connection hold milliseconds,
- pool size / available / waiting statistics,
- queue/error/loss counters,
- root job name and run kind,
- repository/call-site operation,
- thread name,
- acquisition timeout/error events,
- connection creation lifecycle,
- connection expiry observed on return.

Telemetry is written to dedicated rotating JSONL files and does not write its own observations through PostgreSQL.

The summary tool is:

```text
verification/summarize_connection_pool_telemetry.ps1
```

The final lifecycle-attribution instrumentation was added in commit:

```text
1c2b0a82d6c9925b4faa159288373c5f48fc0909
Add connection lifecycle attribution telemetry
```

## Evidence established in development

### 1. Pressure repeatedly follows the connection lifetime window

Repeated pressure events occurred approximately every 56–60 minutes. This closely matches the randomized one-hour lifetime behavior of the deployed psycopg pool version.

Direct lifecycle telemetry subsequently observed multiple:

```text
connection_expired_on_return
```

events with connection ages around 57–60 minutes.

Replacement connections were then created successfully.

This upgrades the earlier counter-only correlation to direct lifecycle attribution: normal connection retirement/replacement is occurring during the same timing window in which checkout latency rises.

### 2. Connection establishment latency rises while substantial pool headroom remains

Observed pressured checkouts included waits around:

```text
~0.8 s
~1.4 s
~1.9 s
~2.3 s
~2.8 s
~3.8–3.9 s
```

Pool size during pressure reached at most `3` of configured `6` in the development evidence set.

Normal replacement connection creation was typically around `1.4–1.6 s`; under heavier host pressure, establishment was observed around `1.9 s` and approximately `3.8 s`.

This is inconsistent with a simple six-of-six capacity exhaustion explanation.

### 3. Error/loss counters do not support stale or broken connections as the primary mechanism

Across the collected lifecycle evidence:

```text
checkout_timeout    0
requests_errors     0
returns_bad         0
connections_errors  0
connections_lost    0
```

No directly instrumented checkout crossed the configured 10-second threshold during the development observation period.

### 4. Scheduler/background overlap can amplify pressure but is not required

Some lifecycle windows included overlap between `sec_event_job` and `notification_dispatcher`.

Other pressured windows occurred with `notification_dispatcher` alone. Therefore overlap is a contributor in some intervals, but it is not required for the observed replacement/establishment pressure mechanism.

### 5. Development host resource pressure is a plausible amplifier, not a proven root cause

The development machine has approximately 8 GB RAM. During heavier observations, host telemetry included approximately:

```text
RAM used        ~86.8%
available RAM   ~425 MB
commit usage    ~66%
pagefile size   ~18 GB
CPU             ~18%
```

Resource pressure can plausibly increase connection-establishment latency, but current evidence does not prove that host memory pressure caused the historical 10-second timeout.

### 6. Long DB holds are a separate optimization topic

A separate long-hold example was observed in:

```text
weekly_job / database.repository.calculate_and_upsert_ura_breadth
hold time ≈ 14.657 s
checkout wait ≈ very low
```

This proves that long holds can exist, but this event did not exhibit the same checkout-pressure signature. It must not be automatically conflated with the historical pool timeout family.

## Development classification

The development evidence supports this ranking:

1. **Normal pool lifecycle retirement + replacement / connection-establishment latency — DIRECTLY OBSERVED AND STRONGLY CORRELATED.**
2. **Database/network/host latency during new connection establishment — PLAUSIBLE AMPLIFIER.**
3. **Scheduler/background overlap — CONFIRMED CONTRIBUTOR IN SOME WINDOWS, NOT REQUIRED.**
4. **Real pool-capacity saturation — WEAKLY SUPPORTED.**
5. **Stale/bad/reset/lost connections — NO CURRENT COUNTER EVIDENCE.**
6. **Long DB hold — REAL BUT NOT ESTABLISHED AS THE PRIMARY HISTORICAL TIMEOUT MECHANISM.**

The exact historical checkout that crossed 10 seconds was not reproduced. That missing reproduction does not justify keeping the development roadmap blocked because the lifecycle mechanism, capacity headroom and replacement behavior are now sufficiently characterized for a behavior-preserving decision.

## Final development decision

The Post-Shadow connection-pool RCA is **non-blocking for further development**.

No remediation is applied in development solely from the historical timeout evidence.

Specifically:

- do not increase `max_size=6`,
- do not increase the 10-second checkout timeout,
- do not add generic retry loops,
- do not serialize scheduler jobs,
- do not change signal/model behavior.

If the same timeout recurs in the actual Windows Server production environment, remediation must be selected only after correlating the exact event with production telemetry.

## Production observation debt — GitHub Issue #2

GitHub Issue #2 remains the follow-up record:

```text
Production follow-up: validate historical PostgreSQL pool timeouts
```

When the engine is deployed to the real Windows Server, retain lifecycle telemetry and correlate any new timeout with:

- `connection_expired_on_return`,
- `connection_created`,
- checkout wait and hold duration,
- pool size / available / waiting values,
- PostgreSQL error/loss counters,
- active root job / background consumer / callsite,
- host CPU,
- physical RAM / available RAM,
- commit / paging pressure,
- disk latency,
- network latency,
- Supabase/PostgreSQL connection-establishment latency.

A production recurrence may justify a targeted runtime change, but only after the measured cause is known.

## P0 roadmap consequence

The pool investigation no longer blocks Post-Shadow development. The remaining scheduler ERROR review was completed separately:

- pre-Shadow `daily_ura_job` rate-limit event: historical provider-limit observation,
- Shadow `daily_ura_job` 08 August event: isolated unexpected Alpha Vantage response shape, automatically recovered on the next scheduled run, exact historical payload unavailable,
- `sec_event_job` 29 August ERROR: same connection-pool timeout family already tracked by Issue #2.

With those classifications, Post-Shadow P0 development reliability is considered closed. The next roadmap phase is **P1 — Validation parity / point-in-time evidence**, beginning with real rolling/expanding walk-forward validation.
