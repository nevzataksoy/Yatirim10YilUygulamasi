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

## Production rollout status

Build gate: **PASS**

Startup preflight: **PASS**

Production installation: **OPEN**

Next perform a controlled service stop and explicitly verify no stale/orphan `InvestmentEngine.exe --service` process remains before running the approved telemetry-enabled installer.

After installation verify:

1. installed executable SHA256 matches `020F46B8823ADCED3B9C935059D9037800321C3C23A513926E99173C96EE5E2D`,
2. `_internal`, `settings`, and `rosalock` are preserved,
3. Windows Service returns to `RUNNING / exit 0`,
4. a process-local `connection-pool-telemetry-<PID>.jsonl` file is created by the new service,
5. telemetry records are local-only and do not change pool sizing, timeout, retry, scheduler or model semantics.
