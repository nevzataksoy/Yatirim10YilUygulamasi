# v1.2.0 Smoke / Validation Test Plan

## 1. Upgrade

Mevcut v1.1.4 kurulumu üzerinde installer çalıştırılır. `settings` ve `rosalock` korunur.

Supabase'te yalnız yeni migration çalıştırılır:

```text
0007_v1_2_model_validation.sql
```

## 2. CLI wrapper

```bat
InvestmentEngineCLI.cmd --service-status
```

CMD içinde `RUNNING` çıktısı görülmeli. Dosyanın kendisi `@echo off\n...` şeklinde literal `\n` basmamalıdır.

## 3. Crypto dependency preflight

Servis durdurulduktan sonra ayrıca `--once hourly` çağırmadan:

```bat
InvestmentEngineCLI.cmd --once crypto
```

`derivatives quality > 0` ve provider `okx`/`deribit` olmalıdır; freshness yoksa crypto job kendi preflight refresh'ini yapar.

## 4. Historical crypto backfill

Validation öncesi bir kez:

```bat
InvestmentEngineCLI.cmd --backfill-crypto --history-days 2500
```

Beklenen `common_days` en az istenen pencerenin yaklaşık %85'i olmalıdır.

## 5. Model validation

```bat
InvestmentEngineCLI.cmd --validate-model
```

Ardından:

```sql
select validation_type, system, model_version, status,
       start_date, end_date, metrics, details, generated_at
from public.model_validation_snapshot
order by validation_type, system;
```

Beklenen ilk development ortamında:

- `PIT_CORE_REPLAY / ETH/BTC`: veri history yeterliyse `OK`; değilse `INSUFFICIENT_HISTORY`.
- `PIT_FULL_REPLAY / URA/USD`: başlangıçta `NOT_READY`.
- `SHADOW_READINESS / ALL`: başlangıçta `NOT_READY`.

## 6. Validation audit geçmişi

```sql
select id, validation_type, system, model_version, status,
       started_at, finished_at, observations, signals
from model.validation_runs
order by id desc
limit 20;
```

## 7. Model version

Yeni bir crypto kararı üret:

```bat
InvestmentEngineCLI.cmd --once crypto
```

Kontrol:

```sql
select id, system, as_of, status, model_version, created_at
from model.decisions
order by id desc
limit 10;
```

Yeni karar `1.2.0`, eski kararlar `legacy-pre-1.2.0` görünmelidir.

## 8. Monthly audit

```bat
InvestmentEngineCLI.cmd --once monthly
```

`MODEL_AUDIT` health kaydı içinde realized performance + validation bulunmalıdır. Hiç mature ACTION/WATCH yoksa performans observation sayısının 0 olması normaldir.

## 9. LIVE gate

`SHADOW_READINESS=READY` görülmeden `engine_mode=live` yapılmaz. READY olduğunda da mode otomatik değişmez; manuel production review gerekir.
