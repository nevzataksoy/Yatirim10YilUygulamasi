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

Status: **IN PROGRESS — OBSERVABILITY CLI PASS / SERVICE PACKAGING REMEDIATION READY FOR REBUILD**

Do not treat source-level observability as complete production runtime truth until the Windows Service sub-gate passes.

### Gate B1 — Initial Windows build evidence

The first observability rollout build passed source/test/release validation:

```text
Python compile control       PASS
pytest                       38 passed in 19.24s
release_check                OK
PyInstaller EXE build        PASS
Inno Setup 6.4.0 compile     PASS
```

Initial build environment:

```text
OS                            Windows 10 10.0.19045
Python                        3.14.0
PyInstaller                   6.21.0
Inno Setup                    6.4.0
```

Initial OneFile artifacts:

```text
dist\InvestmentEngine.exe
SHA256 E81C8B8840492A055279348E107F59C7C6C64D7EF65CA8143A01C4A634C78892

installer\InvestmentEngineSetup-1.2.0.exe
SHA256 73DFC9B081E7C82ED998D1AA094F3011A458F2697AA3ADB2FA6B0600DA36C176
```

These hashes are retained only as evidence for the failed OneFile rollout and must not be treated as the final service artefacts after the OneDir remediation rebuild.

### Gate B2 — Controlled installer/runtime rollout of initial OneFile build

Status: **PARTIAL PASS — INSTALLED BINARY + CLI PASS / SERVICE START FAILED**

The exact initial installer was executed. Post-install evidence:

```text
Installed EXE SHA256:
E81C8B8840492A055279348E107F59C7C6C64D7EF65CA8143A01C4A634C78892

settings preserved: true
rosalock preserved: true
```

The Windows Service registration was correct:

```text
SERVICE_NAME: RosaInvestmentEngine
START_TYPE: AUTO_START
BINARY_PATH_NAME: "C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe" --service
SERVICE_START_NAME: LocalSystem
```

However installer service startup failed with Windows SCM error `1053`.

System Event Log evidence:

```text
Event 7045 — service installed successfully
Event 7009 — timeout waiting for service connection after 30000 ms
Event 7000 — service failed to start because it did not respond in time
```

The application log contained no new startup/failure entry from this failed service attempt; its latest line was the intentional pre-upgrade scheduler shutdown. Therefore the failed service process had not reached the normal `SvcDoRun()` logging path before SCM timed out.

At the same time the exact installed EXE successfully ran the new observability CLI path:

```text
InvestmentEngineCLI.cmd --shadow-observability
EXIT_CODE=0
```

The command loaded preserved settings, connected to Supabase, read the recovered Shadow epoch, calculated scheduler diagnostics and returned/persisted a full observability result. Therefore:

- installed binary integrity verified,
- settings/rosalock compatibility verified,
- migration 0010 compatibility verified,
- DB connectivity verified,
- observability CLI runtime verified,
- service failure isolated to packaged Windows Service startup/bootstrap.

Observed `SHADOW_OBSERVABILITY` status from the manual CLI run was `BLOCKED`, with `377/385` expected scheduler rows captured and `374/385` completed. This is diagnostic evidence and does not change mode, thresholds or released signal semantics.

### Gate B3 — OneFile startup latency confirmation

The installed OneFile EXE was measured three times using the harmless `--service-status` CLI path while the service remained stopped:

```text
Run 1: 62.741 s, exit 0
Run 2: 20.879 s, exit 0
Run 3: 18.019 s, exit 0
```

The first cold process launch exceeded the SCM connection timeout by more than 30 seconds. This directly explains the observed Event 7009 / service error 1053 during installer startup.

Combined evidence:

1. SCM waits 30,000 ms and times out.
2. First OneFile process startup takes 62.741 s.
3. No application log entry is reached before timeout.
4. Once startup finishes, the same binary performs CLI/DB/observability work successfully.

**Root cause: CONFIRMED — PyInstaller OneFile bootstrap/extraction startup latency is incompatible with the Windows Service SCM startup window on this deployment host.**

Do not change the system-wide `ServicesPipeTimeout` registry value as the primary fix.

### Gate B4 — Approved behavior-preserving packaging remediation

The release packaging has been changed without changing model/runtime semantics:

- `build.bat`: `--onefile` -> `--onedir`
- `scripts/build_exe.ps1`: `--onefile` -> `--onedir`
- PyInstaller `--contents-directory "_internal"`
- UPX disabled with `--noupx` to prioritize startup reliability
- main EXE remains `C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe`
- PyInstaller dependencies are installed under `{app}\_internal`
- service binPath remains `"...\InvestmentEngine.exe" --service`
- `settings`, `rosalock`, logs/runtime paths remain unchanged
- Inno Setup recursively packages the `_internal` runtime tree
- release-check rejects either Windows build path if `--onefile` is reintroduced

Status: **SOURCE REMEDIATION COMPLETE / WINDOWS REBUILD AND RUNTIME VALIDATION OPEN**

### Gate B final acceptance criteria

- rebuilt OneDir Windows artefacts pass compile/pytest/release-check/installer compile,
- fresh OneDir `--service-status` startup is comfortably below 30 seconds,
- installed EXE fingerprint equals rebuilt artefact fingerprint,
- settings/rosalock remain preserved,
- installer service-start step completes without 1053/7009,
- Windows Service becomes `RUNNING`, exit code `0`,
- `--shadow-observability` remains non-empty and exit code `0`,
- a `SHADOW_OBSERVABILITY` validation record/snapshot is persisted,
- new scheduler root rows classify as `scheduled`,
- child/dependency rows classify as `maintenance` / `dependency` as applicable,
- active `shadow_epoch_id=1` is attached to new rows,
- existing released `SHADOW_READINESS` semantics are not overwritten,
- mode remains `SHADOW`,
- Realtime Execution remains `OFF`.

## Gate C — Post-rollout reliability investigation

Status: **BLOCKED BY WINDOWS SERVICE ONEDIR RUNTIME VALIDATION**

After Gate B passes, the next P0 task is connection-pool root-cause analysis. Pool sizing must not be changed merely because historical errors exist. First collect runtime evidence for checkout wait, connection hold duration, saturation and job provenance; then decide whether the cause is pool capacity, nested connection usage, long transactions, network/database latency or another source.
