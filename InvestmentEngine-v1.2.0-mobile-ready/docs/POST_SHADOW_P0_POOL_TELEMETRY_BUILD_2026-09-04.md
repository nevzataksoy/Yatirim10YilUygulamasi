# Post-Shadow P0 — Connection Pool Telemetry Build

Date: 04 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Purpose

Record the Windows build and controlled rollout evidence for behavior-preserving connection-pool RCA telemetry instrumentation.

This work does not change pool sizing, pool timeout, retry policy, scheduler serialization, signal thresholds, factor weights, K1/K2, reversal, reset, sizing, mode, or Realtime Execution.

## Initial telemetry build

Source baseline before the first telemetry build:

```text
agent/portfolio-audit-reset
ae4a2cb
```

Validation:

```text
Python compile control       PASS
pytest                       44 passed in 7.84s
release_check                OK
PyInstaller OneDir COLLECT   PASS
Inno Setup 6.4.0 compile     PASS
```

Initial telemetry artefacts:

```text
EXE SHA256
020F46B8823ADCED3B9C935059D9037800321C3C23A513926E99173C96EE5E2D

Installer SHA256
ECD41D8045E5A6E5E35A245F57EA78AB70DAD2EA8141BB6CE768012F9B5D9B7D
```

Initial startup preflight:

```text
Run 1   7.047 s   exit 0
Run 2   1.013 s   exit 0
Run 3   1.014 s   exit 0
```

All runs reported the production Windows Service as `RUNNING` with service exit code 0.

## Initial controlled production installation

Before installation:

```text
SERVICE_NAME: RosaInvestmentEngine
STATE: 1 STOPPED
PID: 0
```

No `InvestmentEngine.exe` process remained after the controlled stop, so the prior orphan-OneFile file-lock condition was not present.

The installer fingerprint was rechecked immediately before installation and matched the approved artefact. Installation completed successfully.

Post-install verification:

```text
Installed EXE SHA256
020F46B8823ADCED3B9C935059D9037800321C3C23A513926E99173C96EE5E2D

_internal   True
settings    True
rosalock    True

SERVICE_NAME: RosaInvestmentEngine
STATE: 4 RUNNING
WIN32_EXIT_CODE: 0
SERVICE_EXIT_CODE: 0
ProcessId: 11496
PathName: "C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe" --service
```

**Initial telemetry production installation: PASS**

## Initial production telemetry evidence

The service created:

```text
C:\Program Files\Rosa\InvestmentEngine\logs\connection-pool-telemetry-11496.jsonl
```

The first checkout after startup recorded:

```text
wait_ms             1519.237
pool_size before    1
pool_available      0
requests_queued     1
pool_size after     2
connections_num     2
connections_ms      1486
requests_errors     0
returns_bad         0
connections_errors  0
connections_lost    0
```

A following sample showed both connections available again. A later `notification_dispatcher` checkout waited only `0.049 ms` with no connection-health errors.

This does not demonstrate pool-capacity exhaustion. It shows that a request can queue while the pool creates/warms an additional connection, and that connection creation took roughly 1.5 seconds on this startup. Historical 10-second checkout failures therefore remain compatible with connection-establishment / database-network health problems and must not be attributed to `max_size=6` without further evidence.

The first frozen-runtime records exposed an instrumentation-only issue: `callsite` was emitted as `unknown`. Root-job/run-kind attribution remained intact, but repository-method attribution was insufficient for long-duration RCA.

## Frozen-runtime callsite fix

The callsite parser was updated to recognize PyInstaller frozen `co_filename` forms such as `app/database/repository.py`, not only absolute paths containing `/app/`. A dedicated regression test was added.

Relevant source commits:

```text
f357cf4  Fix frozen runtime pool telemetry callsites
96304da  Test frozen runtime telemetry callsite parsing
```

The generated installer directory was then added to `.gitignore` and the previously tracked setup EXE removed from the Git index so future builds no longer dirty the repository:

```text
54bf458  Yeni build çalıştırıldı
cefbf25  Ignore generated installer artifacts
```

The installer remains present locally after `git rm --cached`; only Git tracking was removed.

## Callsite-fix Windows rebuild

Validation:

```text
Python compile control       PASS
pytest                       45 passed in 7.64s
release_check                OK
PyInstaller OneDir COLLECT   PASS
Inno Setup 6.4.0 compile     PASS
_internal                    True
```

Callsite-fix artefacts:

```text
EXE SHA256
86506CA2429A08760A93FAE5DF00461CF44A0C926A1E5184F940D4E16B69AC27

Installer SHA256
A18CA1F9562299B255F2F29257D8EC4CE1E6BC0D81F57D85A8B47564FCBF8498
```

## Callsite-fix startup preflight

The rebuilt executable was launched three times with the harmless `--service-status` command while production remained running:

```text
Run 1   7.477 s   exit 0
Run 2   2.013 s   exit 0
Run 3   1.009 s   exit 0
```

All three runs reported:

```text
SERVICE_NAME: RosaInvestmentEngine
STATE: 4 RUNNING
WIN32_EXIT_CODE: 0
SERVICE_EXIT_CODE: 0
```

Cold startup remains comfortably below the Windows SCM timeout and the callsite-only telemetry fix did not regress OneDir startup behavior.

**Callsite-fix build: PASS**

**Callsite-fix startup preflight: PASS**

## Current rollout status

Initial telemetry production installation: **PASS**

Initial local telemetry creation: **PASS**

Callsite-fix build: **PASS**

Callsite-fix startup preflight: **PASS**

Callsite-fix production installation: **OPEN**

Next step: controlled service stop, stale-process verification, installer hash verification, upgrade with the callsite-fix installer, and confirmation that the new service telemetry contains concrete callsites such as repository or notification-dispatcher methods instead of `unknown`.

No pool sizing, timeout, retry, scheduler, model, SHADOW-mode or Realtime Execution behavior has been changed.
