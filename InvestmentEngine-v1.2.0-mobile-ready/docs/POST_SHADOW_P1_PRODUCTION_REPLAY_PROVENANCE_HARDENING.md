# Post-Shadow P1 — Production/Replay Evaluation-Time Provenance Hardening

Date: 2026-09-08
Model version: 1.2.0
Mode: SHADOW
LIVE: NO-GO unchanged

## Scope

This note records the production/replay provenance baseline and the narrow audit-only hardening applied after the same-market-date signal-state idempotency substage was closed.

It does **not** close full production/replay parity. It does not change factor weights, thresholds, confidence gates, K1/K2, reversal, reset-day semantics, sizing, scheduler cadence, execution behavior, engine mode or model version.

## Production provenance baseline

Read-only query:

- `verification/verify_production_replay_provenance_reconstructibility.sql`

Production baseline contained 39 ETH/BTC and 38 URA/USD model-version 1.2.0 decisions.

### ETH/BTC

All 39/39 decisions contained:

- `decision_evaluated_at`,
- embedded signal-state payload,
- core technical factor calculation inputs,
- macro values,
- macro observation dates,
- macro freshness-quality map,
- crypto flow input,
- derivatives scoring inputs,
- paired BTC/ETH derivatives observed timestamps.

This means the persisted decision audit surface is strong for ETH/BTC, subject to the broader distinction between persisted scoring inputs and independently versioned raw-source history.

### URA/USD

All 38/38 decisions contained:

- `decision_evaluated_at`,
- embedded signal-state payload,
- core technical inputs,
- macro values / observation dates / freshness qualities.

Directional fundamentals had positive quality in 36 rows, and all 36/36 preserved the calculation fields required by the existing holdings/flow factor.

However, before hardening:

```text
positive-quality breadth rows              36
rows with breadth numeric scoring inputs    0
rows with breadth compute timestamp          0
URA decisions                               38
rows with exact event-set identity           0
rows with event-health timestamp              0
rows with holdings fetch-time identity        0
```

The important interpretation is that persisted factor score/quality can be audited even when the exact raw source snapshot cannot be reconstructed. Those are different guarantees.

## Same-market-date evaluation drift

URA/USD had:

```text
repeated market dates                          7
repeated decision rows                        19
rows with factor-payload peer difference      17
rows with regime peer difference               0
```

Therefore 17/19 repeated rows had at least one different factor payload while market `as_of` remained unchanged. The scheduler repeat is not a duplicate by definition; later evaluation can see a different information set.

This is why replay parity must distinguish:

1. market `as_of`,
2. actual decision evaluation time,
3. source-specific observation/fetch/compute timestamps,
4. exact source records eligible at that evaluation time.

## Narrow audit-only hardening

`app/engines/ura.py` was changed without altering scoring formulas.

### Breadth

`score_ura_breadth()` now persists in factor details:

- `breadth_date`,
- breadth row `created_at`,
- `pct_above_20dma`,
- `pct_above_50dma`,
- `pct_above_200dma`,
- `pct_positive_day`,
- `new_20d_high_pct`,
- existing breadth metadata/details.

Null numeric values remain valid when a component has not accumulated enough history. The audit requirement is to preserve the exact keys/values that scoring saw, including nulls.

Raw table columns are authoritative if an identically named key ever appears inside the row's generic `details` JSON.

### Event

`score_event_monitor()` now persists:

- `health_checked_at`,
- `health_status`,
- evaluated `recent_events` count,
- exact `event_refs` array,
- existing monitored/directional event semantics.

Each event ref contains the fields used to identify/audit the event set and scoring context:

- source,
- entity,
- asset,
- event type,
- URL,
- occurred-at timestamp,
- severity,
- surprise,
- credibility.

An empty `event_refs=[]` is valid when the runtime actually saw no events in the evaluated window; preserving the empty array is still materially different from not recording the event-set identity at all.

### Holdings limitation deliberately not hidden

`fundamentals.ura_holdings` currently upserts `(holding_date,ticker)` rows and refreshes `fetched_at`. It does not version every raw fetch of the same holdings date as a separate immutable snapshot.

Therefore adding a single holdings `fetched_at` into decision JSON would not by itself make historical raw holdings snapshots replayable. The existing directional fundamentals calculation inputs remain auditable, but raw holdings snapshot versioning is a separate data-lifecycle limitation and is not falsely classified as solved here.

## Regression verification

Focused tests:

```text
python -m pytest -q tests\test_ura_provenance_audit.py
3 passed
```

Full suite:

```text
python -m pytest -q
68 passed
```

Release check:

```text
python .\scripts\release_check.py
Release check: OK
```

Focused tests verify:

1. breadth audit metadata carries the exact numeric inputs and compute timestamp without changing the existing breadth score/quality result,
2. a quiet event set carries health timestamp/status and exact event refs without inventing directional edge,
3. directional event weighting remains unchanged after audit metadata is added.

## Windows build acceptance

The hardened branch was pulled on the Windows build host and rebuilt with the released OneDir packaging flow.

Observed build acceptance:

```text
full Python tests       68 passed
release check           OK
PyInstaller OneDir      PASS
Inno Setup 6.4.0        PASS
installer               InvestmentEngineSetup-1.2.0.exe
```

Build artefact reference:

```text
file    dist\InvestmentEngine\InvestmentEngine.exe
SHA256  91300423EA360C11E923C1AC74F437581BAAEF0DC23CFBA3458B60FB8A29890A
```

Installer reference:

```text
file    installer\InvestmentEngineSetup-1.2.0.exe
SHA256  7F49A2670F1A7BECB8BAE1055A87C4548F035DE0360ACF24B9B3EEFC035C5B7C
```

This SHA256 is the deployment identity for the provenance-hardened `1.2.0` runtime. Because the semantic model version remains intentionally `1.2.0`, production upgrade acceptance must compare the installed EXE hash against this artefact rather than relying only on the version string.

## Production runtime deployment acceptance

The development workstation is also the Windows host running the production Shadow service, so the freshly built installer was executed directly in place; no cross-host file transfer was required.

Pre-upgrade baseline:

```text
service                         RosaInvestmentEngine
state                           RUNNING
start mode                      Auto
service path                    C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe --service
old installed EXE SHA256        5DA8383A5B0B1F8710168B247ED9CC2BBA0C1DC440A607B3F275F59678B1253D
settings SHA256                 9B399425AA664EE5ECC94553259DCAF8261EB4FF1490E5E4768DAAFA8463C88B
rosalock SHA256                 5B3D7A5AA99739516DAD7D816BFB7CBEC695FCD924502EE038B383099F216D9A
```

Post-upgrade acceptance:

```text
service                         RUNNING
start mode                      Auto
installed EXE SHA256            91300423EA360C11E923C1AC74F437581BAAEF0DC23CFBA3458B60FB8A29890A
build artefact hash match       PASS
settings SHA256                 9B399425AA664EE5ECC94553259DCAF8261EB4FF1490E5E4768DAAFA8463C88B
settings preservation           PASS
rosalock SHA256                 5B3D7A5AA99739516DAD7D816BFB7CBEC695FCD924502EE038B383099F216D9A
rosalock preservation           PASS
CLI service-status              RUNNING
CLI exit code                   0
```

This proves the running Windows service was upgraded to the exact hardened OneDir build while preserving the configured settings/lock files.

## Forward URA job execution

After deployment, the installed runtime was exercised twice with:

```text
InvestmentEngineCLI.cmd --once ura
```

Both runs returned:

```text
daily_ura_job: OK
exit code: 0
```

In the released code path, `daily_ura_job` logs `OK` only after `_persist_decision(...)` completes. Therefore the deployed runtime completed the normal URA decision persistence path. The exact latest decision id/timestamps and the new audit payload fields are still verified separately by the read-only forward SQL below; this job result alone is not used to claim those JSON fields are correct.

## Implementation classification

```text
Baseline provenance diagnostic          VERIFIED IN PRODUCTION
ETH/BTC persisted audit coverage        STRONG / 39 of 39
URA technical+macro audit coverage      COMPLETE / 38 of 38
URA directional fundamentals inputs     COMPLETE / 36 of 36 positive-quality rows
URA historical breadth raw inputs       MISSING BEFORE HARDENING
URA historical exact event-set identity MISSING BEFORE HARDENING
Audit-only code hardening                VERIFIED BY TESTS
Full Python suite                        68 PASS
Release check                            OK
Windows OneDir build                     PASS
Installer compile                        PASS
Build EXE SHA256                         91300423EA360C11E923C1AC74F437581BAAEF0DC23CFBA3458B60FB8A29890A
Production runtime deployment           VERIFIED
Installed/build EXE identity             VERIFIED
settings/rosalock preservation           VERIFIED
Post-deploy URA job execution            VERIFIED / 2 manual runs
Forward production decision payload      PENDING READ-ONLY SQL
Full production/replay parity            OPEN
LIVE                                     NO-GO
```

## Forward production verification

A read-only forward verification query is provided:

- `verification/verify_production_replay_ura_provenance_forward.sql`

It must be run only after the hardened runtime has actually been deployed and at least one new URA/USD decision has been created by that runtime. Those preconditions are now satisfied by the deployment/hash acceptance and successful post-deploy URA persistence path above.

The acceptance field is:

```text
checks.hardened_audit_payload_complete = true
```

A passing forward check proves that newly created URA decisions carry the intended breadth/event audit metadata. It does not retroactively repair old decisions and does not create immutable raw holdings history.

## Remaining parity work

After a successful forward production check, the next research decision is whether full replay needs new immutable source-snapshot storage for URA holdings/events or whether persisted decision-input snapshots are sufficient for the intended validation contract.

That decision must be evidence-driven and separate from model tuning. No threshold/weight/model/LIVE change follows automatically from this hardening.
