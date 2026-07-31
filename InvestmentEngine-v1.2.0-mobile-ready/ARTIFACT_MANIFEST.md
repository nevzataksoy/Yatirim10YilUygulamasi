# Artifact Manifest — v1.2.0

Ana kaynak paketi:

```text
InvestmentEngine-v1.2.0-mobile-ready.zip
```

Supabase migration paketi:

```text
supabase-migrations-v1.2.0.zip
```

Upgrade migration:

```text
0007_v1_2_model_validation.sql
```

Başlıca doğrulama belgeleri:

```text
HOTFIX_1_2_0.md
UPGRADE.md
TEST_PLAN_V1_2_0.md
MODEL_VALIDATION_AND_SHADOW.md
RELEASE_VALIDATION.md
PRODUCTION_CHECKLIST.md
```

v1.2.0 kapsamı: gerçek satır sonlu CLI wrapper, model-version provenance, ETH/BTC point-in-time directional core replay, exploratory train/holdout threshold raporu, Shadow readiness gate, validation audit/snapshot ve one-time crypto history backfill.

Windows installer bu kaynak ağacındaki `build.bat` ile development Windows bilgisayarında üretilir; ZIP hazır Windows binary içermez.
