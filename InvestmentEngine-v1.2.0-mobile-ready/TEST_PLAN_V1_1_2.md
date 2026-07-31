# Smoke Test — Investment Engine v1.1.2

Başlangıç: `shadow`, Realtime Execution kapalı.

## 1. Upgrade migration

Supabase SQL Editor'da `0005_v1_1_2_macro_derivatives.sql` çalıştırın.

Development/shadow ortamında eski FRED kayıtlarını temizleyin:

```sql
truncate table macro.observations;
```

## 2. Servisi durdurun

```bat
cd /d "C:\Program Files\Rosa\InvestmentEngine"
InvestmentEngine.exe --stop-service
```

Windowed EXE parent console'a bağlanamazsa sonuç MessageBox olarak görünebilir; işlem yine çalışır.

## 3. Macro

```bat
InvestmentEngine.exe --once macro
```

Kontrol:

```sql
select distinct on (series_id)
  series_id, observation_date, value, fetched_at
from macro.observations
order by series_id, observation_date desc;
```

```sql
select * from public.engine_health_snapshot where component='MACRO';
```

Beklenti: 1981/1995/2009 gibi tarih yok. Health details içinde `quality`, `observation_dates`, `stale_or_missing` vardır.

## 4. Derivatives

```bat
InvestmentEngine.exe --once hourly
```

Kontrol:

```sql
select observed_at, venue, underlying, instrument_name,
       open_interest, funding_8h, mark_price, index_price, basis_pct
from market.derivatives_snapshots
order by observed_at desc
limit 10;
```

```sql
select * from public.engine_health_snapshot where component='DERIVATIVES';
```

Mevcut ağda beklenen provider `okx`, `fallback_used=true`. Son tur BTC ve ETH venue değerleri aynı olmalıdır.

## 5. Crypto decision

```bat
InvestmentEngine.exe --once crypto
```

Kontrol:

```sql
select as_of, factor_code, score, quality, weight, weighted_score, details
from model.factor_scores
where system='ETH/BTC'
order by as_of desc, factor_code;
```

`derivatives.quality` artık 0 olmamalı ve details.provider aynı venue göstermelidir. `macro.details.observation_dates` güncel olmalıdır.

```sql
select * from model.decisions
where system='ETH/BTC'
order by created_at desc
limit 3;
```

Karar ACTION olmak zorunda değildir; amaç veri kalitesi ve hesap zincirini doğrulamaktır.

## 6. URA

Günlük ücretsiz Alpha Vantage kotasını gereksiz tüketmemek için test bir kez yapılır:

```bat
InvestmentEngine.exe --once ura
```

## 7. Servisi başlatın

```bat
InvestmentEngine.exe --start-service
```

`public.engine_health_snapshot` ve `system.job_runs` izlenir. LIVE'a geçilmez.
