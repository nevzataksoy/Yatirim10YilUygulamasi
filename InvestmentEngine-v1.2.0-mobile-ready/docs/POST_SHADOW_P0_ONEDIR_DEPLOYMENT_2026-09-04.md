# Post-Shadow P0 — OneDir Windows Production Deployment

Date: 04 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Purpose

Record the controlled production deployment of the behavior-preserving PyInstaller OneDir remediation for the Windows Service startup timeout observed during the Task 4 observability rollout.

No signal thresholds, factor weights, K1/K2, reversal, reset, sizing, direction, ACTION semantics, mode or Realtime Execution behavior are changed by this packaging remediation.

## Preflight baseline

Approved OneDir artefacts:

```text
InvestmentEngine.exe
SHA256 CBBAA56B5315535520BFB4BC1342FA9E4077C64929F5F40031428646B0B1C09B

InvestmentEngineSetup-1.2.0.exe
SHA256 B9F44962E8A4C5AAA8AC95FC8BDD98BFE4C07A52F3690F55D07AA8EE7F3D0C14
```

Pre-install startup timing:

```text
Run 1   5.183 s   exit 0
Run 2   1.034 s   exit 0
Run 3   1.021 s   exit 0
```

The production service was confirmed stopped before installation and `settings` / `rosalock` were backed up.

## Upgrade file-lock incident

The first OneDir installer attempt failed before service startup while replacing the existing executable:

```text
DeleteFile failed; code 5
Access denied
```

Diagnostics showed:

```text
SCM state: STOPPED
SCM PID:   0
```

but a stale process still existed:

```text
InvestmentEngine.exe --service
PID 13556
ExecutablePath C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe
```

The executable ACL was normal and the file was not read-only. Therefore the installer failure was caused by an orphaned old OneFile service process holding the executable open, not by OneDir package corruption or ACL misconfiguration.

The stale process was terminated explicitly. A reversible rename test then succeeded:

```text
LOCK_TEST_OK
```

This confirmed the executable file lock had been released.

## Successful OneDir installation

The installer was rerun after the stale process was cleared and completed successfully.

Post-install installed executable fingerprint:

```text
SHA256 CBBAA56B5315535520BFB4BC1342FA9E4077C64929F5F40031428646B0B1C09B
```

The installed executable exactly matches the approved rebuilt OneDir artefact.

Runtime layout / preserved state:

```text
C:\Program Files\Rosa\InvestmentEngine\_internal   True
C:\Program Files\Rosa\InvestmentEngine\settings    True
C:\Program Files\Rosa\InvestmentEngine\rosalock    True
```

Windows Service status after installation:

```text
SERVICE_NAME: RosaInvestmentEngine
STATE: 4 RUNNING
WIN32_EXIT_CODE: 0
SERVICE_EXIT_CODE: 0
CHECKPOINT: 0x0
WAIT_HINT: 0x0
```

**OneDir production install + service start: PASS**

## Post-deploy runtime verification

Recent Service Control Manager events for the successful OneDir installation contained only service installation Event 7045. No new Event 7009 or 7000 was observed.

The application log shows the new service successfully initialized APScheduler at 04:27:54 local time, registered the expected jobs, started the scheduler, and immediately executed the notification dispatcher successfully. No startup traceback was observed.

Manual runtime observability verification:

```text
InvestmentEngineCLI.cmd --shadow-observability
status: BLOCKED
EXIT_CODE=0
```

The BLOCKED state is readiness/diagnostic evidence only. The command produced a complete report, connected to the production database, evaluated the active Shadow epoch, and persisted observability output. No released model semantics were changed.

Supabase persistence verification confirms:

```text
SHADOW_OBSERVABILITY validation run id 26   status BLOCKED
SHADOW_OBSERVABILITY snapshot               status BLOCKED
SHADOW_READINESS snapshot                   status READY
```

Therefore SHADOW_OBSERVABILITY remains separate from the released SHADOW_READINESS result and does not overwrite it.

Runtime CLI provenance also verified:

```text
job_name         shadow_observability
run_kind         manual
root_job_name    shadow_observability
shadow_epoch_id  1
status            OK
```

This confirms the new runtime can set and persist provenance GUCs and attach the active Shadow epoch.

At the time BLOCK D was collected, the newly deployed service had not yet reached its first scheduled root execution after startup. The most recent scheduler rows were therefore still historical `scheduled_legacy` rows from before the OneDir deployment.

## Remaining Gate B verification

Before Gate B is fully closed, one runtime provenance check remains:

1. After the first post-deploy scheduled root run (expected `hourly_job` at 05:05 Europe/Istanbul), verify a new row with:

```text
job_name         hourly_job
run_kind         scheduled
root_job_name    hourly_job
shadow_epoch_id  1
```

2. Confirm that run completes with expected status and no new service-start error appears.

All other Gate B runtime/deployment acceptance criteria are PASS.

Connection-pool RCA remains blocked until this final scheduled-root provenance check completes.
