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

## Remaining Gate B verification

Before Gate B is fully closed, still verify:

1. Recent Service Control Manager events contain no new 7009 / 7000 startup timeout for the successful OneDir install.
2. `InvestmentEngineCLI.cmd --shadow-observability` returns a full report with exit code 0.
3. Supabase runtime persistence keeps `SHADOW_OBSERVABILITY` separate from released `SHADOW_READINESS`.
4. New scheduler root runs use `run_kind='scheduled'` and carry matching `root_job_name` runtime provenance.
5. New runtime rows attach the active Shadow epoch where applicable.
6. Mode remains `SHADOW` and Realtime Execution remains `OFF`.

Connection-pool RCA remains blocked until these final runtime/provenance checks complete.
