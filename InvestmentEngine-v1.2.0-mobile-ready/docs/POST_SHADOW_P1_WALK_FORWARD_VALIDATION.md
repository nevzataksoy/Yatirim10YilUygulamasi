# Post-Shadow P1 — ETH/BTC Expanding Walk-Forward Validation

**Evidence date:** 2026-09-07 (Europe/Istanbul)  
**Model:** 1.2.0  
**Mode:** SHADOW  
**Realtime execution:** OFF  
**Scope:** ETH/BTC directional core replay only; production model parameters are unchanged.

## Decision

**P1 walk-forward implementation: VERIFIED**  
**Validation evidence: LIMITED / SIGNAL-STARVED**  
**Threshold change: NOT SUPPORTED**  
**SHADOW -> LIVE: NO-GO remains unchanged**

The expanding-window implementation is functioning on real Supabase history, but the directional core does not produce enough threshold-qualified historical signals to justify threshold calibration or LIVE promotion.

## Verification

Source checkout verification after implementation:

- focused P1 tests: `5 passed`
- full test suite: `52 passed`
- release check: `OK`
- configured OneDir settings were resolved from `C:\Program Files\Rosa\InvestmentEngine`
- verification was executed as dry-run; no validation row/snapshot was persisted

## Default expanding-window run

Configuration:

- observations: `1419`
- replay start: `2022-10-18`
- replay end: `2026-09-05`
- method: `EXPANDING_WINDOW`
- minimum train sessions: `365`
- holdout sessions: `90`
- fold step: `90`
- primary horizon: `20` sessions
- configured production edge threshold: `70`
- minimum train signals for candidate eligibility: `8`
- folds: `12`

Observed result:

- configured edge=70 holdout signals: `0`
- selected candidate folds: `0`
- selected candidate holdout signals: `0`
- original selection status: `LIMITED_SIGNAL_COUNT`

The configured edge threshold therefore generated no out-of-sample signal in any of the 12 expanding holdout folds.

## Threshold train-signal diagnostics

Maximum and final expanding-train signal counts:

| Edge | Max train signals | Final train signals | Folds meeting >=8 train signals |
|---:|---:|---:|---:|
| 50 | 5 | 5 | 0 |
| 55 | 4 | 4 | 0 |
| 60 | 1 | 1 | 0 |
| 65 | 0 | 0 | 0 |
| 70 | 0 | 0 | 0 |
| 75 | 0 | 0 | 0 |
| 80 | 0 | 0 | 0 |

No tested threshold in `(50, 55, 60, 65, 70, 75, 80)` reached the validation-only minimum of 8 train signals in any fold.

## Sensitivity run — min train signals = 1

A second dry-run deliberately relaxed only the **validation candidate eligibility floor** from 8 to 1. This did not change any production threshold, model parameter, signal-state rule, K1/K2 rule, sizing rule, engine mode, or execution setting.

Result:

- observations: `1419`
- folds: `12`
- configured edge=70 holdout signals: `0`
- selected candidate folds: `11`
- selected candidate holdout signals: `4`

Candidate pattern:

- fold 1: no candidate
- folds 2-5: edge `50` selected from only 1-2 train signals
- folds 6-12: edge `60` selected from only 1 train signal

Only two holdout folds produced any selected-candidate signal:

- fold 3: 1 signal, hit rate `0%`, average signed return about `-7.98%`
- fold 5: 3 signals, hit rate about `33.33%`, average signed return about `-2.43%`

Aggregate across the 4 selected-candidate OOS signals:

- hit rate: `25%`
- weighted average signed return: approximately `-3.82%`

This sensitivity result does **not** support lowering the production edge threshold. It shows that when candidate eligibility is reduced to one historical train signal, sparse candidates can be selected but their observed OOS evidence is both too small and unfavorable.

## Status semantics hardening

The first sensitivity command returned `status=OK` because the core helper treated any selected candidate with at least one OOS signal as OK. That label was too broad for a validation gate.

The verification layer was therefore hardened without changing the production model:

- `selection_status` preserves the underlying selection result
- main evidence status is now:
  - `LIMITED_TRAIN_SIGNAL_COUNT` when no train-eligible candidate exists
  - `LIMITED_OOS_SIGNAL_COUNT` when candidates exist but aggregate OOS count is below the validation evidence floor
  - `EVIDENCE_AVAILABLE` only when the OOS signal-count floor is met
- aggregate selected-candidate OOS hit rate and average signed return are reported separately
- `EVIDENCE_AVAILABLE` is not a performance PASS and does not auto-apply parameters

The verification-only OOS evidence floor defaults to 8 signals. It is not a model threshold and does not affect production decisions.

## Interpretation

Current evidence supports these conclusions:

1. The expanding walk-forward machinery itself is working and boundary-safe.
2. The ETH/BTC historical directional core is signal-starved at the released edge threshold and across the tested lower threshold grid.
3. Lowering edge eligibility to create more historical candidates is not justified by the observed OOS sensitivity results.
4. No released factor weight, quality threshold, edge threshold, confidence threshold, K1/K2 rule, reset/reversal rule, sizing rule, SHADOW mode, or realtime execution setting should be changed from this evidence.
5. The next P1 work should target validation parity / point-in-time fidelity rather than threshold tuning: strict FRED vintage PIT and production-vs-replay gap analysis are the next logical evidence tasks.

## Invariants retained

- Model Version `1.2.0`
- Mode `SHADOW`
- Realtime Execution `OFF`
- production edge threshold unchanged
- all factor weights unchanged
- all confidence/quality thresholds unchanged
- K1/K2 unchanged
- reversal/reset unchanged
- sizing unchanged
- no automatic parameter application
- no LIVE activation
