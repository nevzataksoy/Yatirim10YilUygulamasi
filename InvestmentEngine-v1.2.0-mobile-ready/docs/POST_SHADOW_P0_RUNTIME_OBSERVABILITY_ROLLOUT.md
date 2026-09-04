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

The migration verification demonstrated the intended historical behavior:

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
scheduled_legacy daily_ura_job            OK          7
scheduled_legacy weekly_job              OK          1
scheduled_legacy monthly_audit_job       OK          1
```

Recent historical rows also received `shadow_epoch_id=1`. Historical rows naturally have no runtime `root_job_name` GUC because they predate deployment of the new binary; this is expected and is why they are classified as `scheduled_legacy` rather than pretending exact runtime provenance.

**Gate A historical classification result: PASS**

## Gate B — Windows build and binary rollout

Status: **PASS / CLOSED**

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

These hashes are retained only as evidence for the failed OneFile rollout and must not be treated as final service artefacts.

### Gate B2 — Initial OneFile installer/runtime result

The exact initial installer was executed. Installed binary integrity, settings/rosalock compatibility, migration compatibility, DB connectivity and manual observability CLI runtime all verified successfully, but Windows Service startup failed with SCM error `1053`.

System Event Log evidence:

```text
Event 7045 — service installed successfully
Event 7009 — timeout waiting for service connection after 30000 ms
Event 7000 — service failed to start because it did not respond in time
```

No new application log entry was reached before the timeout. The same installed EXE nevertheless completed `--shadow-observability` successfully with exit code 0.

### Gate B3 — OneFile startup latency confirmation

The installed OneFile EXE was measured three times using harmless `--service-status` launches while the service remained stopped:

```text
Run 1: 62.741 s, exit 0
Run 2: 20.879 s, exit 0
Run 3: 18.019 s, exit 0
```

The first cold process launch exceeded the SCM 30,000 ms connection timeout.

**Root cause: CONFIRMED — PyInstaller OneFile bootstrap/extraction startup latency is incompatible with the Windows Service SCM startup window on this deployment host.**

No system-wide `ServicesPipeTimeout` registry change was approved or required.

### Gate B4 — Behavior-preserving packaging remediation

The release packaging was changed without changing model/runtime semantics:

- `build.bat`: `--onefile` -> `--onedir`
- `scripts/build_exe.ps1`: `--onefile` -> `--onedir`
- PyInstaller `--contents-directory "_internal"`
- UPX disabled with `--noupx`
- main EXE remains `C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe`
- dependencies install under `{app}\_internal`
- service binPath remains `"...\InvestmentEngine.exe" --service`
- `settings`, `rosalock`, logs/runtime paths remain unchanged
- Inno Setup recursively packages the `_internal` tree
- release-check rejects either Windows build path if `--onefile` is reintroduced
- packaging contract tests are now source-controlled

### Gate B5 — OneDir rebuild and startup preflight

Rebuild validation:

```text
Python compile control       PASS
pytest                       38 passed in 2.87s
release_check                OK
PyInstaller OneDir COLLECT   PASS
Inno Setup 6.4.0 compile     PASS
```

Final approved OneDir fingerprints:

```text
InvestmentEngine.exe
SHA256 CBBAA56B5315535520BFB4BC1342FA9E4077C64929F5F40031428646B0B1C09B

InvestmentEngineSetup-1.2.0.exe
SHA256 B9F44962E8A4C5AAA8AC95FC8BDD98BFE4C07A52F3690F55D07AA8EE7F3D0C14
```

OneDir startup timings:

```text
Run 1: 5.183 s, exit 0
Run 2: 1.034 s, exit 0
Run 3: 1.021 s, exit 0
```

**OneDir startup preflight: PASS**

### Gate B6 — Production OneDir deployment

The first upgrade attempt encountered a separate file-lock issue before service startup:

```text
DeleteFile failed; code 5
Access denied
```

SCM reported `STOPPED / PID 0`, but an orphaned old OneFile `InvestmentEngine.exe --service` process remained alive and held the executable open. Its ACL was normal and the file was not read-only. The stale process was terminated and a reversible rename test returned `LOCK_TEST_OK`.

The same approved installer was rerun and completed successfully.

Post-install verification:

```text
Installed EXE SHA256:
CBBAA56B5315535520BFB4BC1342FA9E4077C64929F5F40031428646B0B1C09B

_internal   true
settings    true
rosalock    true

SERVICE_NAME: RosaInvestmentEngine
STATE: 4 RUNNING
WIN32_EXIT_CODE: 0
SERVICE_EXIT_CODE: 0
```

Recent SCM events for the successful OneDir install contained no new 7009/7000 timeout. The application log shows APScheduler startup and successful notification-dispatcher execution without startup traceback.

Manual observability runtime verification:

```text
InvestmentEngineCLI.cmd --shadow-observability
status: BLOCKED
EXIT_CODE=0
```

The diagnostic BLOCKED result is due to the seven-day scheduler success gate and does not indicate deployment failure.

Persistence separation verified:

```text
SHADOW_OBSERVABILITY snapshot   BLOCKED
SHADOW_READINESS snapshot       READY
```

Manual runtime provenance verified:

```text
job_name         shadow_observability
run_kind         manual
root_job_name    shadow_observability
shadow_epoch_id  1
status           OK
```

### Gate B7 — Scheduled-root provenance verification

A later production query collected at 04 September 2026 15:42 Europe/Istanbul showed repeated post-deploy scheduler roots with exact runtime provenance.

Representative examples:

```text
hourly_job      run_kind=scheduled  root_job_name=hourly_job      shadow_epoch_id=1  status=OK
macro_job       run_kind=scheduled  root_job_name=macro_job       shadow_epoch_id=1  status=OK
sec_event_job   run_kind=scheduled  root_job_name=sec_event_job   shadow_epoch_id=1  status=DEGRADED
```

Multiple hourly rows from ids 1974 through 1991 repeatedly completed `OK` with matching root provenance and epoch attachment. SEC rows remained `DEGRADED` with approximately 19.4% direct fund-weight ticker coverage; that diagnostic state is preserved intentionally and is not a Windows runtime failure.

### Gate B final acceptance criteria

- rebuilt OneDir Windows artefacts pass compile/pytest/release-check/installer compile: **PASS**
- OneDir startup comfortably below SCM timeout: **PASS**
- installed EXE fingerprint equals rebuilt artefact fingerprint: **PASS**
- settings/rosalock preserved and `_internal` present: **PASS**
- installer service start completes without 1053/7009: **PASS**
- Windows Service `RUNNING`, exit code 0: **PASS**
- `--shadow-observability` non-empty, exit code 0: **PASS**
- `SHADOW_OBSERVABILITY` validation record/snapshot persisted: **PASS**
- `SHADOW_READINESS` remains a separate released snapshot: **PASS**
- manual runtime provenance and active epoch attachment: **PASS**
- new scheduler roots classify as `scheduled`: **PASS**
- matching `root_job_name` on scheduler roots: **PASS**
- active `shadow_epoch_id=1` on new runtime rows: **PASS**
- mode remains `SHADOW`: **PASS**
- Realtime Execution remains `OFF`: **PASS**

**Gate B — PASS / CLOSED**

## Gate C — Post-rollout connection-pool root-cause analysis

Status: **OPEN**

The next P0 task is the historical database connection-pool failure RCA, including errors such as:

```text
couldn't get a connection after 10.00 sec
```

Do not increase `max_size=6` merely because these errors exist. First collect runtime evidence for:

- connection checkout wait duration,
- connection hold duration,
- pool occupancy / saturation at checkout and release,
- job/root-job/run-kind provenance,
- overlapping scheduler jobs,
- nested connection usage,
- transaction duration,
- provider/network calls while holding a DB connection,
- database/network latency and timeout correlation.

Only after measurement should the RCA decide whether the cause is true pool capacity, nested connection acquisition, long transactions, external-provider work inside DB scopes, database/network latency, or another source.

No signal thresholds, factor weights, K1/K2/reversal/reset/sizing behavior, model version, SHADOW mode or Realtime Execution state may be changed as part of this RCA without separate explicit approval.
