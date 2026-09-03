# Post-Shadow P0.1 — Runtime / Observability Rollout

Date: 04 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Purpose

This document records the controlled production rollout of Task 4 behavior-preserving Shadow observability hardening after the 30-day Shadow task calendar was completed.

No signal thresholds, factor weights, K1/K2, reversal, reset, sizing, direction, ACTION semantics or Realtime Execution behavior are changed by this rollout.

## Gate 0 — Baseline before rollout

Production Windows Service baseline:

```text
SERVICE_NAME: RosaInvestmentEngine
STATE: RUNNING
WIN32_EXIT_CODE: 0
SERVICE_EXIT_CODE: 0
```

Initial Supabase verification showed migration `0010_shadow_observability.sql` had not yet been applied:

```text
shadow_epochs_table_ok       false
job_runs_run_kind_ok         false
job_runs_shadow_epoch_id_ok  false
provenance_function_ok       false
provenance_trigger_ok        false
```

The installed production binary also did not emit any output for:

```bat
InvestmentEngineCLI.cmd --shadow-observability
```

The current branch source does implement this flag and emits an explicit `shadow_observability: ...` result. Therefore the installed Windows binary was confirmed to predate the Task 4 observability runtime hardening.

## Gate A — Migration 0010 rollout

The Windows Service was stopped before migration:

```text
STATE: STOPPED
```

Migration `0010_shadow_observability.sql` was applied successfully to the production Supabase database.

### Schema/object verification

Post-migration BLOCK A result:

```text
shadow_epochs_table_ok       true
job_runs_run_kind_ok         true
job_runs_shadow_epoch_id_ok  true
provenance_function_ok       true
provenance_trigger_ok        true
```

**Gate A schema result: PASS**

### Recovered Shadow epoch

Migration 0010 recovered the real v1.2.0 production Shadow epoch from existing decision evidence:

```text
id:            1
epoch_key:     shadow-1.2.0-initial
model_version: 1.2.0
started_at:    2026-07-30 19:53:25.049772+00
ended_at:      null
status:        ACTIVE
source:        model.decisions
recovered_by:  0010_shadow_observability
```

No synthetic epoch start date was introduced.

### Historical provenance classification

The last verification window demonstrated the intended migration behavior:

- weekly child `macro_job` -> `maintenance`
- weekly child `sec_event_job` -> `maintenance`
- manually invoked `model_validation_job` -> `manual`
- `realtime_test` -> `test`
- historical scheduler-root jobs -> `scheduled_legacy`
- real historical `hourly_job ERROR` records remain visible as scheduler failures
- historical SEC `DEGRADED` records remain visible and are not rewritten to OK

Representative counts from the supplied verification window:

```text
maintenance      macro_job              OK          1
maintenance      sec_event_job          DEGRADED    1
manual           model_validation_job   OK          1
test             realtime_test          OK          1
scheduled_legacy hourly_job              OK        164
scheduled_legacy hourly_job              ERROR       2
scheduled_legacy macro_job               OK         27
scheduled_legacy sec_event_job           DEGRADED   165
scheduled_legacy sec_event_job           ERROR       1
scheduled_legacy daily_crypto_job        OK          6
scheduled_legacy daily_fx_job            OK          5
scheduled_legacy daily_ura_job           OK          7
scheduled_legacy weekly_job              OK          1
scheduled_legacy monthly_audit_job       OK          1
```

Recent historical rows also received `shadow_epoch_id=1`. Historical rows naturally have no runtime `root_job_name` GUC because they predate deployment of the new binary; this is expected and is why they are classified as `scheduled_legacy` rather than pretending exact runtime provenance.

**Gate A historical classification result: PASS**

## Gate B — Windows build and binary rollout

Status: **IN PROGRESS — BUILD SUB-GATE PASS / INSTALLER ROLLOUT OPEN**

Do not treat source-level observability as production runtime truth until the installer/runtime sub-gate passes.

### Gate B1 — Windows build evidence

The latest `agent/portfolio-audit-reset` source was built in the normal Windows build environment while the production service remained stopped.

Build validation:

```text
Python compile control       PASS
pytest                       38 passed in 19.24s
release_check                OK
PyInstaller EXE build        PASS
Inno Setup 6.4.0 compile     PASS
```

Build environment observed in the supplied output:

```text
OS                            Windows 10 10.0.19045
Python                        3.14.0
PyInstaller                   6.21.0
Inno Setup                    6.4.0
```

Generated artifacts and SHA256 fingerprints:

```text
dist\InvestmentEngine.exe
SHA256 E81C8B8840492A055279348E107F59C7C6C64D7EF65CA8143A01C4A634C78892

installer\InvestmentEngineSetup-1.2.0.exe
SHA256 73DFC9B081E7C82ED998D1AA094F3011A458F2697AA3ADB2FA6B0600DA36C176
```

PyInstaller emitted non-fatal warnings while UPX attempted to compress already non-compressible binaries (`_uuid.pyd`, `python3.dll`) and also reported `Hidden import "sip" not found!`. The build continued to successful EXE creation and installer compilation. These warnings are not treated as runtime proof; Gate B2 must verify the actual installed CLI and Windows Service behavior.

**Gate B1 build result: PASS**

### Gate B2 — Controlled installer/runtime rollout

Status: **OPEN**

Required sequence:

1. Keep the production service stopped during the controlled upgrade.
2. Install exactly the generated `InvestmentEngineSetup-1.2.0.exe` identified above.
3. Existing `settings` and `rosalock` must remain preserved.
4. Confirm the service starts successfully.
5. Run:

```bat
InvestmentEngineCLI.cmd --service-status
InvestmentEngineCLI.cmd --shadow-observability
```

6. Re-run verification SQL BLOCK C/D after at least one new scheduled root run if practical, and confirm newly written scheduler rows use `run_kind='scheduled'` with runtime provenance rather than `scheduled_legacy`.

### Gate B acceptance criteria

- Windows Service: `RUNNING`, exit code `0`.
- `--shadow-observability` prints a non-empty explicit report.
- A `SHADOW_OBSERVABILITY` validation record/snapshot is persisted.
- New scheduler root rows are classified `scheduled`.
- Nested/dependency work is classified `maintenance` / `dependency` as applicable.
- Active `shadow_epoch_id=1` is attached to new rows.
- Existing released `SHADOW_READINESS` semantics are not silently overwritten.
- Mode remains `SHADOW`.
- Realtime Execution remains `OFF`.

## Gate C — Post-rollout reliability investigation

Status: **BLOCKED BY GATE B**

After Gate B passes, the next P0 task is connection-pool root-cause analysis. Pool sizing must not be changed merely because historical errors exist. First collect runtime evidence for checkout wait, connection hold duration, saturation and job provenance; then decide whether the cause is pool capacity, nested connection usage, long transactions, network/database latency or another source.
