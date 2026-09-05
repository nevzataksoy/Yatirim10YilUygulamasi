# Shadow Task 4 — Reliability Findings and Observability Hardening

Date: 07 August 2026  
Model version: `1.2.0`  
Engine mode: `SHADOW`  
Realtime Execution: `OFF`

## Status discipline

- **RELEASED:** Existing v1.2.0 decision semantics, thresholds, weights, K1/K2, reversal, reset and action-size behavior. These are unchanged by this work.
- **APPROVED:** Behavior-preserving Shadow observability hardening may proceed after Task 4.
- **PROPOSED:** None of the signal-model proposals are promoted by this change.
- **OPEN:** Migration `0010` and the new observability command still require deployment against the real Supabase/Windows Service environment before they are treated as runtime evidence.

## Task 4 findings

User checkpoint evidence shows:

- Windows Service `RUNNING`, exit codes `0`.
- Coinbase realtime smoke test `OK`: 8 snapshots, BTC-USD + ETH-USD, max trade gap `0`.
- Model validation `OK`: ETH/BTC core `OK`, 1389 observations, Shadow `NOT_READY`.
- Readiness blockers are empty. Waiting reasons are only observation/history accumulation.
- ETH/BTC: 9 decision days, median quality `90.83`.
- URA/USD: 6 decision days, median quality `87.48`.
- URA holdings: 6 dates, roughly 99.4%–99.9% weight coverage.

### Scheduler accounting conclusion

The seven-day `hourly_job` counts are:

```text
165 OK + 3 ERROR = 168 total
```

That is exactly the expected `7 x 24` scheduled hourly fires. Therefore the three connection-pool errors are real scheduled failures and must not be relabeled as development noise.

The same period contains:

```text
macro_job:     29 rows
sec_event_job: 169 rows
```

The scheduler contract expects `28` macro and `168` SEC root fires. The extra `+1/+1` comes from `weekly_job`, which invokes `macro_job` and `sec_event_job` as child maintenance work. Counting every job row as an independent scheduler fire inflates the denominator.

SEC `DEGRADED` is also not a crashed scheduler run. It reflects the released SEC monitor quality rule: only five directly resolvable US tickers cover about 20%–21% of the considered URA fund weight. The current readiness implementation intentionally treats `OK`, `DEGRADED` and `SKIPPED` as completed/successful runs; strict `OK` rate was not separately visible.

## Hardening implemented on the development branch

The branch adds a behavior-preserving observability layer:

1. `model.shadow_epochs` records an explicit Shadow epoch. Migration `0010` recovers the current v1.2.0 epoch from the first real v1.2.0 decision instead of inventing a date.
2. `system.job_runs.run_kind` distinguishes `scheduled`, `scheduled_legacy`, `manual`, `test`, `backfill`, `dependency`, `maintenance`, `development` and `legacy`.
3. A DB trigger attaches the active `shadow_epoch_id` and run provenance to new job rows.
4. Scheduler and CLI root executions carry provenance through `ContextVar` + PostgreSQL local GUCs. Nested weekly/dependency jobs are therefore not mistaken for scheduler root fires.
5. Scheduler cadence is centralized in `app/schedule_contract.py`; the same contract is used for runtime scheduling and expected-run accounting.
6. New `--shadow-observability` command computes expected vs actual scheduled runs, capture/completed/OK rates and per-job breakdown.
7. The command reuses the released Shadow readiness criteria unchanged, but replaces the ambiguous recent-job denominator with expected scheduled root fires.
8. Edge, confidence, data-quality, status and direction distributions are added as diagnostics only. No threshold is recalibrated or auto-applied.
9. The diagnostic is published as `SHADOW_OBSERVABILITY`; it does **not** silently overwrite the released `SHADOW_READINESS` snapshot during rollout.

## Task 4 schedule-contract proof

For the seven-day interval ending approximately at the Task 4 validation time, the shared schedule contract calculates:

```text
hourly_job          168
macro_job            28
sec_event_job       168
daily_crypto_job      7
daily_ura_job         7
daily_fx_job          5
weekly_job            1
monthly_audit_job     1
-----------------------
expected root runs  385
```

Pure unit tests assert this exact distribution and verify run-context restoration.

If the three hourly errors are the only failed root fires and all expected roots were captured, the corrected completed/success rate remains above the released 98% gate. The purpose of the hardening is therefore not to manufacture a PASS; it is to make the denominator and provenance auditable.

## Runtime rollout gate

Before treating this branch implementation as runtime truth:

1. Build/test the Python package in the normal Windows release environment.
2. Apply migration `0010_shadow_observability.sql` once to Supabase.
3. Deploy/restart the same SHADOW service; do not enable Realtime Execution and do not switch to LIVE.
4. Run:

```bat
InvestmentEngineCLI.cmd --shadow-observability
```

5. Compare `SHADOW_OBSERVABILITY` with the existing `SHADOW_READINESS` snapshot and Task 4 raw SQL counts.
6. Confirm historical nested weekly rows were classified as `maintenance`, manual validation/realtime rows are excluded from scheduler accounting, and the three hourly errors remain scheduled failures.

Only after this runtime verification should the official readiness path itself be considered for replacement. No model-version change or new Shadow epoch is required for this observability-only hardening.
