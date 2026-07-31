# Investment Engine v1.1.4 — CLI, Dependency Preflight ve SEC Coverage Hardening

## Düzeltilenler

1. `InvestmentEngineCLI.cmd` artık GUI-subsystem EXE'nin CLI loguna eklediği yeni satırları komut tamamlanınca terminale geri basar. Tek ana binary `InvestmentEngine.exe` olarak kalır.
2. `daily_crypto_job`, 3 saatten eski veya eksik BTC+ETH derivatives pair görürse karar öncesi bir kez `hourly_job` ile best-effort refresh dener. Refresh başarısızsa derivatives quality=0 kalır ve data-quality gate fail-safe davranır.
3. SEC event monitor quality artık entity sayısına göre `60+5*n` verilmez. Quality, exact SEC eşleşen URA holdings'lerinin gerçek fon ağırlığı coverage'ına bağlıdır ve SEC-only kaynak kapsamı nedeniyle 70 ile sınırlıdır.
4. SEC health details içine `matched_fund_weight`, `considered_top_n_weight`, `matched_tickers` ve `scope_cap` eklenmiştir.

## Migration

Yeni migration yoktur. v1.1.3 migration seti (0001–0006) yeterlidir.
