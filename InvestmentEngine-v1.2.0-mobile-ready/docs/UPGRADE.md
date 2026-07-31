# Upgrade — v1.2.0

## v1.1.4 -> v1.2.0

1. Developer bilgisayarda `build.bat` çalıştırın.
2. Supabase SQL Editor'da yalnız `migrations/0007_v1_2_model_validation.sql` çalıştırın.
3. `InvestmentEngineSetup-1.2.0.exe` ile mevcut kurulumun üzerine upgrade yapın.
4. `settings` ve `rosalock` korunur.
5. `InvestmentEngineCLI.cmd --service-status` ile CLI çıktısını doğrulayın.
6. `InvestmentEngineCLI.cmd --validate-model` çalıştırın.
7. `public.model_validation_snapshot` ve `model.validation_runs` tablolarını doğrulayın.

`engine_mode` Shadow kalmalıdır. `SHADOW_READINESS=READY` olmadan LIVE'a geçmeyin.
