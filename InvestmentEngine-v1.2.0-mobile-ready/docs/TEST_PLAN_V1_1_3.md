# Smoke Test — Investment Engine v1.1.3

Başlangıç:

```text
Mode = shadow
Realtime Execution = OFF
Derivatives Provider = auto
```

Servisle manual job'ı aynı anda çalıştırmamak için önce:

```bat
InvestmentEngineCLI.cmd --stop-service
```

## 1. Migration

```sql
select column_name
from information_schema.columns
where table_schema='market' and table_name='execution_snapshots'
  and column_name in ('ofi','trade_imbalance','trade_notional_usd','trade_gap_count','sample_window_seconds','test_run_id','is_test')
order by column_name;
```

6 kolon beklenir.

## 2. URA + Global X

```bat
InvestmentEngineCLI.cmd --once ura
```

```sql
select holding_date,count(*) constituents,
       sum(weight) weight_coverage,
       sum(market_value) holding_market_value
from fundamentals.ura_holdings
group by holding_date
order by holding_date desc
limit 5;
```

```sql
select *
from public.engine_health_snapshot
where component in ('URA','URA_HOLDINGS','SEC_EVENTS')
order by component;
```

Factor kontrolü:

```sql
select as_of,factor_code,score,quality,weight,weighted_score,details
from model.factor_scores
where system='URA/USD'
order by as_of desc,factor_code;
```

İlk official holdings günü için fundamentals/breadth `quality=0` veya history coverage oranına bağlı düşük kalite normaldir. Kaynak yokken q50 görülmemelidir.

## 3. SEC event job

```bat
InvestmentEngineCLI.cmd --once events
```

```sql
select component,status,message,checked_at,details
from public.engine_health_snapshot
where component='SEC_EVENTS';
```

```sql
select source,entity,event_type,occurred_at,title,url,severity,credibility
from events.events
where asset='URA'
order by occurred_at desc
limit 30;
```

Filing bulunmasa bile health başarılı/coverage'lı olabilir. `severity=0` v1.1.3'te bilinçli davranıştır.

## 4. Crypto missing event semantics

```bat
InvestmentEngineCLI.cmd --once crypto
```

```sql
select factor_code,score,quality,weight,weighted_score,details
from model.factor_scores
where system='ETH/BTC'
  and as_of=(select max(as_of) from model.factor_scores where system='ETH/BTC')
order by factor_code;
```

`event score=0 quality=0` beklenir; derivatives ve macro gerçek quality ile devam eder.

## 5. Provenance

```sql
select id,as_of,created_at,rationale->'provenance' provenance
from model.decisions
order by created_at desc
limit 10;
```

Kapanış tarihi ve evaluate timestamp ayrı olmalıdır.

## 6. Realtime smoke test

Realtime checkbox'ı açmayın. Test bağımsızdır:

```bat
InvestmentEngineCLI.cmd --test-realtime --realtime-seconds 20
```

```sql
select test_run_id,observed_at,product,spread_bps,
       bid_depth_usd,ask_depth_usd,imbalance,microprice,
       ofi,trade_imbalance,trade_notional_usd,trade_gap_count,sample_window_seconds,is_test
from market.execution_snapshots
where is_test=true
order by observed_at desc
limit 30;
```

Aynı `test_run_id` altında BTC-USD ve ETH-USD beklenir.

```sql
select * from public.engine_health_snapshot where component='REALTIME_TEST';
```

## 7. Regime axes

```sql
select system,as_of,primary_regime,
       details->>'market_regime' market_regime,
       details->>'trend_regime' trend_regime,
       details
from model.regimes
order by created_at desc
limit 10;
```

## 8. Weekly

```bat
InvestmentEngineCLI.cmd --once weekly
```

```sql
select * from public.engine_health_snapshot where component='WEEKLY';
```

## 9. Monthly audit

```bat
InvestmentEngineCLI.cmd --once monthly
```

```sql
select system,horizon_days,count(*) observations,
       avg(case when hit then 1.0 else 0.0 end) hit_rate,
       avg(relative_return) avg_relative_return
from model.performance
group by system,horizon_days
order by system,horizon_days;
```

Henüz mature ACTION/WATCH yoksa tablo boş olabilir; job'ın `OK` olması yeterlidir.

## 10. Service restore

```bat
InvestmentEngineCLI.cmd --start-service
InvestmentEngineCLI.cmd --service-status
```

Realtime Execution OFF ve Shadow ile gözleme devam edin.
