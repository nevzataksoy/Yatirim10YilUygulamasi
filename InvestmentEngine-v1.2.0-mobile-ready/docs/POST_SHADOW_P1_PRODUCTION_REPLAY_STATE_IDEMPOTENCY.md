# Post-Shadow P1 — Production/Replay Signal-State Idempotency Closure

Date: 2026-09-08
Model version: 1.2.0
Mode: SHADOW
LIVE: NO-GO unchanged

## Scope

This note closes only the persistent signal-state same-market-date idempotency finding inside the broader production-vs-replay parity work.

It does **not** close full production/replay parity, change model thresholds/weights, change K1/K2 or reversal semantics, change scheduler cadence, change sizing, or enable LIVE.

## Production baseline evidence

Read-only production diagnostics showed:

- ETH/BTC: 39 decision rows / 39 unique market dates / no repeated market dates.
- URA/USD: 38 decision rows / 26 unique market dates / 7 repeated market dates / up to 3 decisions for one market date.
- `same_asof_state_moves = []`.
- `same_asof_reset_advances = []`.
- `same_asof_multiple_action_events = []`.
- Production history contained no `action_event=true`; both current states were inactive.

Therefore no historical production corruption was observed. However, the active-regime reset branch had not been exercised in production, so absence of historical corruption did not prove the code path safe.

## Root cause / latent risk

`apply_signal_state()` previously incremented `reset_counter` for every non-ACTION evaluation while a regime was active. The counter represented market days, but production can evaluate the same market `as_of` more than once.

URA/USD repeated-market-date detail confirmed that repeated evaluations are real and can use different supporting snapshots. For example, the same URA market date could be re-evaluated on later scheduler runs after macro/fundamentals/breadth/event inputs changed.

Blocking all repeated evaluations would therefore discard potentially newer supporting evidence. The correct hardening target was the persistent state progression, not the scheduler history.

## Fix

`app/engines/signal_state.py` now treats `reset_counter` as a market-date counter:

- a new market `as_of` may advance the counter once,
- another evaluation of the same `as_of` does not advance it again,
- a later same-date evaluation may still clear the counter to zero if the active direction regains the released reset-edge condition,
- existing K1/K2/action-event/reversal/sizing behavior is otherwise unchanged.

`model.signal_state.last_evaluated_as_of` was added by migration `0013_signal_state_market_date_idempotency.sql`.

The migration:

- backfills the marker from each system's latest existing decision,
- installs `trg_signal_state_last_evaluated_as_of` after decision insert,
- uses a short migration-time write lock on `model.decisions` so no insert can fall between backfill and trigger installation,
- retains all repeated decision history.

## Regression verification

Focused test:

```text
python -m pytest -q tests\test_signal_state.py
3 passed
```

Full suite:

```text
python -m pytest -q
65 passed
```

Release check:

```text
python .\scripts\release_check.py
Release check: OK
```

Focused coverage verifies:

1. first evaluation of a new market date advances reset counter,
2. repeated evaluation of the same market date does not advance it again,
3. next distinct market date may advance it again,
4. same-date recovery above released reset edge can still clear the counter,
5. same-action-date second-stage action protection remains intact.

## Production migration verification

After applying migration 0013, the read-only verification query returned:

```text
column_present = true
trigger.present = true
trigger.enabled = true
trigger.function_name = sync_signal_state_last_evaluated_as_of
signal_state_rows = 2
rows_with_last_evaluated_as_of = 2
rows_matching_latest_decision_as_of = 2
rows_not_matching_latest_decision_as_of = 0
```

State rows at verification time:

```text
ETH/BTC
  latest_decision_id      83
  latest_decision_as_of   2026-09-06
  last_evaluated_as_of    2026-09-06
  active_direction        null
  stage                   0
  reset_counter           0

URA/USD
  latest_decision_id      82
  latest_decision_as_of   2026-09-04
  last_evaluated_as_of    2026-09-04
  active_direction        null
  stage                   0
  reset_counter           0
```

The database marker is therefore installed and aligned with the latest persisted decision for both systems.

## Closure classification

```text
Observed historical state corruption       NO
Repeated same-market-date evaluations       CONFIRMED
Latent reset-counter idempotency risk        CONFIRMED
Code hardening                               VERIFIED
Focused regression tests                     PASS
Full test suite                              PASS
Release check                                PASS
Migration applied                            VERIFIED BY READ-ONLY DB CHECK
State marker / latest decision alignment      2 / 2
Same-as-of signal-state idempotency substage  CLOSED
```

## Remaining production/replay parity work

Full production/replay parity remains open.

The next question is evaluation-time provenance: a market `as_of` is not sufficient by itself to identify the exact information set used in production. Repeated URA evaluations demonstrated that supporting factor inputs can change after the market close while the price-bar `as_of` remains unchanged.

Future parity work must therefore distinguish at least:

- market `as_of`,
- actual decision evaluation time,
- source-specific observation/fetch timestamps,
- which macro/fundamentals/breadth/event/derivatives snapshots were eligible at that evaluation time.

Historical derivatives/event availability remains an explicit replay limitation. No threshold/model/LIVE change is justified by this closure.
