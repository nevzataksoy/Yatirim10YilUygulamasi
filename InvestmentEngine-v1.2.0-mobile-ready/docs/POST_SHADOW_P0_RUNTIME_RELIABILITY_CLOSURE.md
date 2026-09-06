# Post-Shadow P0 — Runtime Reliability Closure

Date: 06 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Decision

**Post-Shadow P0 development reliability: CLOSED / NON-BLOCKING**

This closure does not change model behavior, scheduler cadence, connection-pool sizing, retry policy or LIVE state.

The purpose of P0 was to classify real scheduler ERROR debt after the 30-day Shadow task calendar and to add enough runtime provenance to avoid evidence-free remediation.

## 1. Connection-pool timeout family

The historical PostgreSQL error family is:

```text
couldn't get a connection after 10.00 sec
```

Development RCA established direct connection lifecycle retirement/replacement evidence, recurring approximately in the 57–60 minute lifetime window, successful replacement connection creation, capacity headroom, and no new instrumented checkout timeout.

Final classification:

```text
Development RCA          CLOSED / NON-BLOCKING
Exact historical timeout NOT REPRODUCED
Production follow-up     OPEN — GitHub Issue #2
```

The detailed evidence is in:

```text
docs/POST_SHADOW_P0_CONNECTION_POOL_RCA.md
```

No evidence justifies changing `max_size=6`, `timeout=10`, adding generic retry, or serializing the scheduler.

## 2. Scheduler ERROR records reviewed

The ERROR review used real `system.job_runs` rows rather than inferred counts.

### 2.1 Pre-Shadow daily URA provider limit

```text
id              5
started_at      2026-07-30 00:42:16.685002+00
job_name        daily_ura_job
run_kind        scheduled_legacy
shadow_epoch_id null
status          ERROR
message         Alpha Vantage free API rate/quota response
```

Classification:

- occurred before the recovered Shadow epoch,
- provider explicitly returned rate/quota guidance,
- historical provider-limit observation,
- not a current P0 blocker.

### 2.2 Shadow daily URA isolated provider-response failure

```text
id              477
started_at      2026-08-07 23:40:00.196029+00
TRT             2026-08-08 02:40:00.196029
job_name        daily_ura_job
run_kind        scheduled_legacy
shadow_epoch_id 1
status          ERROR
message         Alpha Vantage günlük seri bulunamadı.
```

Adjacent scheduled runs:

```text
2026-08-06 02:40 TRT  OK  data_quality 85.40
2026-08-07 02:40 TRT  OK  data_quality 87.71
2026-08-08 02:40 TRT  ERROR
2026-08-09 02:40 TRT  OK  data_quality 87.77
2026-08-10 02:40 TRT  OK  data_quality 87.77
2026-08-11 02:40 TRT  OK  data_quality 88.07
```

The next successful run produced the missing market close as:

```text
as_of        2026-08-07
direction    USD→URA
status       WAIT
data_quality 87.77
```

Therefore the event did not create a permanent market-data gap. It recovered without intervention on the next scheduled run.

The collector already had request pacing and one controlled retry for Alpha Vantage's explicit `1 request per second` response at the time of the event. The 08 August job message is generated when the returned JSON does not contain `Time Series (Daily)` after the known provider error fields have been checked.

The historical raw response body was not retained in `job_runs.details`, so the exact provider payload can no longer be proven. The correct classification is:

**isolated unexpected Alpha Vantage response shape; exact historical payload unavailable; automatic next-run recovery confirmed.**

It must not be relabeled as a rate-limit event without evidence.

No additional retry/backoff behavior is introduced from this single event.

### 2.3 Shadow SEC ERROR

```text
id              1642
started_at      2026-08-29 03:35:15.183358+00
job_name        sec_event_job
run_kind        scheduled_legacy
shadow_epoch_id 1
status          ERROR
message         couldn't get a connection after 10.00 sec
```

Classification:

- not a separate SEC provider failure,
- belongs to the historical PostgreSQL connection-pool timeout family,
- follow-up is GitHub Issue #2 production observation debt.

The normal high volume of `sec_event_job DEGRADED` rows is different. Those rows primarily express limited exact US SEC ticker coverage of the URA top holdings and are not scheduler crashes.

## 3. P0 remediation decision

Current evidence does **not** justify:

```text
increase max_size
increase checkout timeout
add generic DB retry
serialize scheduler jobs
change Alpha Vantage retry behavior from one isolated unknown payload
change model thresholds or factor weights
change K1/K2, reversal, reset or sizing
change SHADOW -> LIVE
turn Realtime Execution ON
```

Long DB holds observed during the connection-pool RCA remain a separate optimization topic. They were not established as the primary historical timeout mechanism.

## 4. P0 closure result

```text
Connection pool RCA       CLOSED for development / production observation OPEN
Pre-Shadow URA ERROR      CLASSIFIED / NON-BLOCKING
Shadow URA ERROR          CLASSIFIED / RECOVERED / NON-BLOCKING
Shadow SEC ERROR          CONNECTION-POOL FAMILY / ISSUE #2
Task 4 runtime telemetry  DEPLOYED AND EVIDENCE COLLECTED
Model version             1.2.0 unchanged
Mode                      SHADOW unchanged
Realtime Execution        OFF unchanged
```

## 5. Next roadmap phase

The next development phase is:

**P1 — Validation parity / point-in-time evidence**

Order:

1. implement true rolling/expanding walk-forward validation,
2. ensure repeated scheduler evaluations of the same market `as_of` do not become fake independent market days,
3. validate strict FRED vintage / point-in-time availability,
4. measure production vs replay factor/state/action gaps,
5. measure K1/K2/reversal state-machine parity without changing released behavior,
6. continue accumulating or sourcing trustworthy URA PIT history.

P1 is evidence work. It does not authorize automatic threshold, factor-weight or state-machine changes.
