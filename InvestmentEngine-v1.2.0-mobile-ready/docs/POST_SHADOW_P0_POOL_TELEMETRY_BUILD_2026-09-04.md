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

## Production rollout status

Build gate: **PASS**

Production installation: **OPEN**

Before installation, perform a harmless OneDir startup-latency preflight with `--service-status`. The existing production service may remain running for this preflight because the command only queries SCM state and does not open the application DB pool.

Do not install if the new artifact unexpectedly approaches or exceeds the SCM startup window.

After preflight passes, perform a controlled service stop / stale-process check / installer upgrade. Then verify that the new service creates local `connection-pool-telemetry-<PID>.jsonl` output without changing database/model behavior.
