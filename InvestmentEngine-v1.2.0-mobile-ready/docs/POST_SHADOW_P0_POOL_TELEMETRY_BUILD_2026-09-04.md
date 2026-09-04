# Post-Shadow P0 — Connection Pool Telemetry Build

Date: 04 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Purpose

Record the Windows build evidence for the behavior-preserving connection-pool RCA telemetry instrumentation.

This build does not change pool sizing, pool timeout, retry policy, scheduler serialization, signal thresholds, factor weights, K1/K2, reversal, reset, sizing, mode, or Realtime Execution.

## Source baseline

Branch:

```text
agent/portfolio-audit-reset
```

Source commit before build:

```text
ae4a2cb
```

Working tree was clean before the build.

## Build validation

```text
Python compile control       PASS
pytest                       44 passed in 7.84s
release_check                OK
PyInstaller OneDir COLLECT   PASS
Inno Setup 6.4.0 compile     PASS
```

Generated runtime layout:

```text
dist\InvestmentEngine\InvestmentEngine.exe
dist\InvestmentEngine\_internal\...
installer\InvestmentEngineSetup-1.2.0.exe
```

Runtime dependency tree check:

```text
Test-Path dist\InvestmentEngine\_internal
True
```

## Artifact fingerprints

Telemetry-enabled OneDir main executable:

```text
SHA256 020F46B8823ADCED3B9C935059D9037800321C3C23A513926E99173C96EE5E2D
```

Telemetry-enabled installer:

```text
SHA256 ECD41D8045E5A6E5E35A245F57EA78AB70DAD2EA8141BB6CE768012F9B5D9B7D
```

## Startup-latency preflight

The rebuilt telemetry-enabled OneDir executable was launched three times with the harmless `--service-status` command while the production Windows Service remained running.

Observed timings:

```text
Run 1   7.047 s   exit 0
Run 2   1.013 s   exit 0
Run 3   1.014 s   exit 0
```

All three runs reported:

```text
SERVICE_NAME: RosaInvestmentEngine
STATE: 4 RUNNING
WIN32_EXIT_CODE: 0
SERVICE_EXIT_CODE: 0
```

The cold launch remains comfortably below the Windows SCM startup window, and the telemetry instrumentation did not regress the OneDir startup remediation.

**Startup preflight: PASS**

## Controlled production installation

Before installation:

```text
SERVICE_NAME: RosaInvestmentEngine
STATE: 1 STOPPED
PID: 0
```

No `InvestmentEngine.exe` process remained after the controlled stop, so the prior orphan-OneFile file-lock condition was not present.

The approved installer fingerprint was rechecked immediately before installation:

```text
SHA256 ECD41D8045E5A6E5E35A245F57EA78AB70DAD2EA8141BB6CE768012F9B5D9B7D
```

The installer completed successfully.

Post-install executable fingerprint:

```text
SHA256 020F46B8823ADCED3B9C935059D9037800321C3C23A513926E99173C96EE5E2D
```

Runtime layout and preserved state:

```text
_internal   True
settings    True
rosalock    True
```

Windows Service after installation:

```text
SERVICE_NAME: RosaInvestmentEngine
STATE: 4 RUNNING
WIN32_EXIT_CODE: 0
SERVICE_EXIT_CODE: 0
ProcessId: 11496
PathName: "C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe" --service
```

**Telemetry production installation: PASS**

## Initial production telemetry evidence

The service created the expected process-local telemetry file:

```text
C:\Program Files\Rosa\InvestmentEngine\logs\connection-pool-telemetry-11496.jsonl
```

The first checkout after service startup recorded:

```text
wait_ms          1519.237
pool_size before 1
pool_available   0
requests_queued  1
pool_size after  2
connections_num  2
connections_ms   1486
requests_errors  0
returns_bad      0
connections_errors 0
connections_lost   0
```

The following sample showed both connections available again. A later `notification_dispatcher` DB checkout waited only `0.049 ms` with no connection-health errors.

This first sample does not demonstrate pool-capacity exhaustion. It shows that a request can queue while the pool creates/warms an additional connection, and that connection creation itself took roughly 1.5 seconds on this startup. Historical 10-second checkout failures therefore remain compatible with connection-establishment / database-network health problems and must not be attributed to `max_size=6` without further evidence.

The first frozen-runtime records also exposed an instrumentation-only issue: `callsite` was emitted as `unknown`. Root job and run-kind remained available, but repository-method attribution must be fixed before long-duration RCA collection. This does not affect engine/database behavior.

## Production rollout status

Build gate: **PASS**

Startup preflight: **PASS**

Production installation: **PASS**

Telemetry file creation: **PASS**

Callsite attribution: **FIX REQUIRED BEFORE LONG-DURATION COLLECTION**

No pool sizing, timeout, retry, scheduler or model behavior change has been made.
