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
status           OK
```

This confirms the new runtime can set and persist provenance GUCs and attach the active Shadow epoch.

## Post-deploy scheduled-root provenance verification

A later production query, collected at 04 September 2026 15:42 Europe/Istanbul, contains repeated scheduler-root rows written by the deployed OneDir runtime.

Representative `hourly_job` rows:

```text
id     job_name     run_kind    status  shadow_epoch_id  root_job_name
1974   hourly_job   scheduled   OK      1                hourly_job
1976   hourly_job   scheduled   OK      1                hourly_job
1978   hourly_job   scheduled   OK      1                hourly_job
1980   hourly_job   scheduled   OK      1                hourly_job
1982   hourly_job   scheduled   OK      1                hourly_job
1984   hourly_job   scheduled   OK      1                hourly_job
1987   hourly_job   scheduled   OK      1                hourly_job
1989   hourly_job   scheduled   OK      1                hourly_job
1991   hourly_job   scheduled   OK      1                hourly_job
```

The same runtime provenance is visible for other scheduler roots:

```text
sec_event_job   run_kind=scheduled   root_job_name=sec_event_job   shadow_epoch_id=1
macro_job       run_kind=scheduled   root_job_name=macro_job       shadow_epoch_id=1
```

`sec_event_job` remains `DEGRADED` because current direct SEC ticker coverage is about 19.4% of fund weight; this is preserved diagnostic evidence and is not a packaging/runtime failure.

These rows prove that after deployment:

- new scheduler roots are classified as `scheduled`, not `scheduled_legacy`,
- `root_job_name` matches the scheduler root,
- the active Shadow epoch is attached as `shadow_epoch_id=1`,
- repeated `hourly_job` runs complete `OK`,
- scheduler provenance remains stable across multiple hours and job types.

## Gate B conclusion

All Gate B acceptance criteria are now satisfied:

- OneDir build / tests / release-check / installer compile: PASS
- cold startup latency comfortably below SCM timeout: PASS
- installed EXE fingerprint matches approved artefact: PASS
- `_internal`, `settings`, and `rosalock` present: PASS
- installer service start without 1053 / 7009: PASS
- Windows Service `RUNNING`, exit code 0: PASS
- manual `--shadow-observability` full report, exit code 0: PASS
- SHADOW_OBSERVABILITY persistence separate from SHADOW_READINESS: PASS
- manual runtime provenance + active Shadow epoch attachment: PASS
- scheduled-root runtime provenance + active Shadow epoch attachment: PASS
- mode remains `SHADOW`: PASS
- Realtime Execution remains `OFF`: PASS

**Gate B — PASS / CLOSED**

The OneFile-to-OneDir packaging remediation is complete. No system-wide `ServicesPipeTimeout` change was required.

## Next P0 step

Connection-pool root-cause analysis is now **OPEN**.

Historical `couldn't get a connection after 10.00 sec` errors must be investigated with runtime evidence before any pool-size change. Instrument and correlate connection checkout wait, connection hold duration, pool occupancy/saturation, root job/run kind, overlap, nested connection usage, long transactions/provider calls, and database/network latency. Do not blindly increase `max_size=6` and do not change released model semantics as part of this RCA.
