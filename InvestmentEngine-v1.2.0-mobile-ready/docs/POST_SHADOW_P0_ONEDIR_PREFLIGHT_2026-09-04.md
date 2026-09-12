# Post-Shadow P0 — OneDir Windows Runtime Preflight

Date: 04 September 2026
Model version: `1.2.0`
Mode: `SHADOW`
Realtime Execution: `OFF`

## Purpose

Record the behavior-preserving Windows packaging preflight performed after replacing the PyInstaller OneFile service build with OneDir in response to confirmed SCM startup timeout error 1053 / Event 7009.

No signal thresholds, factor weights, K1/K2, reversal, reset, sizing, direction, ACTION semantics, mode or Realtime Execution behavior are changed by this packaging remediation.

## Build baseline

Source branch / build baseline:

```text
agent/portfolio-audit-reset
3388fcc
```

Build validation:

```text
pytest                       38 passed in 2.87s
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

## Artifact fingerprints

Rebuilt OneDir main executable:

```text
SHA256 CBBAA56B5315535520BFB4BC1342FA9E4077C64929F5F40031428646B0B1C09B
```

Rebuilt installer:

```text
SHA256 B9F44962E8A4C5AAA8AC95FC8BDD98BFE4C07A52F3690F55D07AA8EE7F3D0C14
```

Runtime dependency tree check:

```text
Test-Path dist\InvestmentEngine\_internal
True
```

## Startup latency preflight

The rebuilt OneDir executable was launched three times with the harmless `--service-status` path while the production service remained stopped:

```text
Run 1   5.183 s   exit 0
Run 2   1.034 s   exit 0
Run 3   1.021 s   exit 0
```

For comparison, the failed OneFile rollout measured:

```text
Run 1  62.741 s   exit 0
Run 2  20.879 s   exit 0
Run 3  18.019 s   exit 0
```

Windows SCM had previously timed out at 30,000 ms. The remediated cold OneDir launch is therefore comfortably inside the SCM connection window and the two subsequent launches are approximately one second.

**OneDir startup preflight: PASS**

## Production rollout gate

The rebuilt installer is now approved for the next controlled runtime validation step, subject to the following safeguards:

1. Production service remains stopped before launching the installer.
2. Existing `settings` and `rosalock` are backed up and must remain preserved.
3. Install exactly the installer fingerprinted above.
4. After installation, installed `InvestmentEngine.exe` must match the rebuilt executable SHA256 above.
5. Installed `{app}\_internal` must exist.
6. Installer service-start must complete without SCM error 1053 / Event 7009.
7. Service status must be `RUNNING` with exit code 0.
8. `--shadow-observability` must remain non-empty with exit code 0.
9. Supabase persistence/provenance verification remains required before Gate B is fully complete.

No system-wide `ServicesPipeTimeout` registry change is required or approved by this remediation.
