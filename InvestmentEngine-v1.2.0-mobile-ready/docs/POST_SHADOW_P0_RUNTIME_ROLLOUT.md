# Post-Shadow P0 — Runtime / Observability Rollout

Date opened: 04 September 2026  
Model version: `1.2.0`  
Required mode throughout rollout: `SHADOW`  
Realtime Execution: `OFF`

## Purpose

Close the OPEN Task 4 runtime-deployment gap without changing released signal semantics.

This rollout deploys the already-approved behavior-preserving observability layer only:

- migration `0010_shadow_observability.sql`,
- explicit Shadow epoch provenance,
- `system.job_runs.run_kind` / `shadow_epoch_id`,
- scheduler root/dependency/maintenance provenance,
- `--shadow-observability` CLI runtime verification.

It does **not** change thresholds, factor weights, K1/K2, reversal, reset, sizing, SHADOW/LIVE mode, or Realtime Execution.

## Baseline observed on 04.09.2026

### Supabase BLOCK A

```text
shadow_epochs_table_ok       false
job_runs_run_kind_ok         false
job_runs_shadow_epoch_id_ok  false
provenance_function_ok       false
provenance_trigger_ok        false
```

Conclusion: migration `0010` is not deployed in the production Supabase database.

### Windows Service

```text
SERVICE_NAME: RosaInvestmentEngine
STATE: RUNNING
WIN32_EXIT_CODE: 0
SERVICE_EXIT_CODE: 0
```

Conclusion: the existing deployed service is healthy before rollout.

### Installed CLI/runtime

```text
InvestmentEngineCLI.cmd --shadow-observability
<no output>
```

The branch runtime explicitly parses `--shadow-observability` and emits a result line plus JSON. Therefore the installed `InvestmentEngine.exe` predates the observability runtime.

Baseline classification:

```text
Migration 0010       NOT DEPLOYED
Observability binary NOT DEPLOYED
Existing service     RUNNING / healthy baseline
Model semantics      v1.2.0 RELEASED / unchanged
Mode                 SHADOW
Realtime Execution   OFF
```

## Rollout gates

### Gate A — Apply migration 0010 only

1. Pull the latest `agent/portfolio-audit-reset` branch.
2. Stop the Windows service:

```bat
InvestmentEngineCLI.cmd --stop-service
InvestmentEngineCLI.cmd --service-status
```

Do not continue unless the service is confirmed stopped.

3. In Supabase SQL Editor execute the current repository file:

```text
migrations/0010_shadow_observability.sql
```

The migration is transactional (`begin` / `commit`). Do not edit it in the SQL editor before execution.

4. Run `verification/verify_shadow_observability_0010.sql` BLOCK A again.

Expected result:

```text
shadow_epochs_table_ok       true
job_runs_run_kind_ok         true
job_runs_shadow_epoch_id_ok  true
provenance_function_ok       true
provenance_trigger_ok        true
```

5. If any value is false or migration execution reports an error, STOP. Do not install/restart a new runtime yet. Preserve and return the exact SQL error/output.

6. If all values are true, run verification BLOCK B-D and preserve the complete results. Do not infer PASS until they are reviewed.

### Gate B — Build and deploy branch runtime

Gate B starts only after Gate A has been reviewed as successful.

The repository `build.bat` performs compile, tests, release check, PyInstaller build and, when Inno Setup 6 is present, creates:

```text
installer/InvestmentEngineSetup-1.2.0.exe
```

The installer upgrade path stops the service, preserves generated `settings` and `rosalock`, copies the new EXE/CLI/migrations/docs, reinstalls the Windows service and starts it when configured.

Before Gate B deployment, record the Gate A verification result in the repository.

### Gate C — Runtime provenance verification

After the new runtime is installed and the service is RUNNING:

```bat
InvestmentEngineCLI.cmd --service-status
InvestmentEngineCLI.cmd --shadow-observability
```

Then rerun SQL verification BLOCK B-D after at least one newly generated scheduled job row exists under the new runtime.

Required checks include:

- active recovered v1.2.0 Shadow epoch exists,
- historical scheduler rows are explicitly classified (`scheduled_legacy`, `maintenance`, `dependency`, etc.),
- new scheduler-root rows are `scheduled`,
- nested jobs are not counted as independent scheduler fires,
- manual/test rows stay excluded from scheduled-root accounting,
- prior real scheduler ERROR rows remain visible,
- `SHADOW_OBSERVABILITY` is generated without replacing the released `SHADOW_READINESS` contract,
- mode remains SHADOW and Realtime Execution remains OFF.

## Rollout stop conditions

Stop the rollout and preserve evidence if any of the following occurs:

- migration transaction fails,
- migration objects are only partially visible after execution,
- service cannot stop/start cleanly,
- build/tests/release check fail,
- installer loses existing settings/rosalock,
- `--shadow-observability` returns ERROR,
- new scheduler rows lack expected provenance,
- any released model semantics or execution-mode setting changes unexpectedly.

No threshold, weight, K1/K2, reversal, reset, sizing or LIVE change is authorized by this rollout.
