# Post-Shadow P1 — ETH/BTC Expanding Walk-Forward Validation

**Evidence date:** 2026-09-07 (Europe/Istanbul)  
**Model:** 1.2.0  
**Mode:** SHADOW  
**Realtime execution:** OFF  
**Scope:** ETH/BTC directional core replay only; production model parameters are unchanged.

## Decision

**P1 walk-forward implementation: VERIFIED / CLOSED AS IMPLEMENTATION STEP**  
**Validation evidence: LIMITED / SIGNAL-STARVED**  
**Threshold change: NOT SUPPORTED**  
**SHADOW -> LIVE: NO-GO remains unchanged**

The expanding-window implementation is functioning on real Supabase history, but the directional core does not produce enough threshold-qualified historical signals to justify threshold calibration or LIVE promotion.

## Final verification — 2026-09-07

The user pulled remote commit `04bc2c4` into the Windows worktree and verified a clean status before running the final regression.

Final test evidence:

- focused walk-forward tests: `7 passed`
- full test suite: `54 passed`
- release check: `OK`
- both verification commands completed as dry-run
- `persistence.persisted = false` in both final outputs

Final default expanding-window output:

- observations: `1420`
- folds: `12`
- main evidence status: `LIMITED_TRAIN_SIGNAL_COUNT`
- underlying selection status: `LIMITED_SIGNAL_COUNT`
- configured edge=70 holdout signals: `0`
- selected candidate folds: `0`
- selected candidate holdout signals: `0`
- selected candidate OOS summary: `0` signals
- persistence: `false`

Final sensitivity output with validation-only `--min-train-signals 1`:

- observations: `1420`
- folds: `12`
- main evidence status: `LIMITED_OOS_SIGNAL_COUNT`
- underlying selection status: `OK`
- configured edge=70 holdout signals: `0`
- selected candidate folds: `11`
- selected candidate holdout signals: `4`
- folds with selected-candidate OOS signals: `2`
- aggregate OOS hit rate: `25%`
- aggregate average signed return: `-0.03821323744433411` (about `-3.82%`)
- persistence: `false`

This final run confirms that the evidence-status hardening behaves as intended on live project data: candidate selection can technically succeed in the sensitivity run while the primary validation status correctly remains limited because the OOS evidence count is too small.

## Expanding-window configuration

- method: `EXPANDING_WINDOW`
- minimum train sessions: `365`
- holdout sessions: `90`
- fold step: `90`
- primary horizon: `20` sessions
- configured production edge threshold: `70`
- default minimum train signals for candidate eligibility: `8`
- folds: `12`

The configured edge threshold generated no out-of-sample signal in the expanding holdout folds.

## Threshold train-signal diagnostics

The detailed threshold-ranking diagnostic was captured one observation earlier, at `1419` replay observations. Maximum and final expanding-train signal counts were:

| Edge | Max train signals | Final train signals | Folds meeting >=8 train signals |
|---:|---:|---:|---:|
| 50 | 5 | 5 | 0 |
| 55 | 4 | 4 | 0 |
| 60 | 1 | 1 | 0 |
| 65 | 0 | 0 | 0 |
| 70 | 0 | 0 | 0 |
| 75 | 0 | 0 | 0 |
| 80 | 0 | 0 | 0 |

No tested threshold in `(50, 55, 60, 65, 70, 75, 80)` reached the validation-only minimum of 8 train signals in that diagnostic. The final 1420-observation regression was used to verify status semantics and aggregate evidence; the ranking table above is retained as the exact earlier diagnostic rather than silently rewriting it.

## Sensitivity interpretation

A separate dry-run deliberately relaxed only the **validation candidate eligibility floor** from 8 to 1. This did not change any production threshold, model parameter, signal-state rule, K1/K2 rule, sizing rule, engine mode, or execution setting.

Earlier fold-level diagnostics showed:

- fold 1: no candidate
- folds 2-5: edge `50` selected from only 1-2 train signals
- folds 6-12: edge `60` selected from only 1 train signal
- fold 3: 1 OOS signal, hit rate `0%`, average signed return about `-7.98%`
- fold 5: 3 OOS signals, hit rate about `33.33%`, average signed return about `-2.43%`

The final 1420-observation run preserved the aggregate outcome at 4 selected-candidate OOS signals, 25% hit rate and about -3.82% average signed return.

This sensitivity result does **not** support lowering the production edge threshold. It shows that when candidate eligibility is reduced to one historical train signal, sparse candidates can be selected but their observed OOS evidence is both too small and unfavorable.

## Status semantics hardening

The first sensitivity command had returned `status=OK` because the core helper treated any selected candidate with at least one OOS signal as OK. That label was too broad for a validation gate.

The verification layer was hardened without changing the production model:

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

1. The expanding walk-forward machinery is working and boundary-safe.
2. The ETH/BTC historical directional core is signal-starved at the released edge threshold and across the tested lower threshold grid.
3. Lowering edge eligibility to create more historical candidates is not justified by the observed OOS sensitivity results.
4. No released factor weight, quality threshold, edge threshold, confidence threshold, K1/K2 rule, reset/reversal rule, sizing rule, SHADOW mode, or realtime execution setting should be changed from this evidence.
5. The walk-forward implementation step is complete; the next P1 work is validation parity / point-in-time fidelity: strict FRED vintage PIT followed by production-vs-replay gap analysis.

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
