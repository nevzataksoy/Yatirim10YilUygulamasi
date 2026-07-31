# Model ve Scheduler — Investment Engine v1.1.3

## Karar zinciri

```text
Raw Data
→ Freshness / Data Quality
→ Features
→ Market Regime + Trend Regime
→ Factors
→ Quality-adjusted Edge
→ Confidence / Uncertainty
→ Late Entry + Event Veto
→ Risk Sizing
→ Decision
→ Signal State (K1/K2)
→ Supabase snapshots
→ isteğe bağlı Telegram / Realtime execution observation
```

Eksik veri **0 skor + 0 kalite** olarak ele alınır. `score=0` tek başına “nötr veri” anlamına gelmez; yalnız gerçekten izlenen ama yön üretmeyen kaynakta quality > 0 olabilir. `score=0` directional agreement hesabında + veya - oy sayılmaz.

## Scheduler

| Job | Zaman (Europe/Istanbul) | İş |
|---|---|---|
| `hourly_job` | her saat `:05` | Deribit→OKX same-provider BTC/ETH derivatives |
| `macro_job` | 00/06/12/18:15 | FRED refresh + freshness quality |
| `sec_event_job` | her saat `:35` | URA holdings içindeki güvenli SEC ticker eşleşmelerinin filing kontrolü |
| `daily_crypto_job` | 05:20 | BTC/ETH spot, features, regime, factors, decision |
| `daily_ura_job` | 02:40 | Alpha Vantage URA + Global X holdings/breadth + SEC event quality + decision |
| `daily_fx_job` | Pzt–Cum 16:30 | TCMB USD/TRY |
| `weekly_job` | Cumartesi 08:00 | Macro + holdings + breadth + SEC veri bakımı |
| `monthly_audit_job` | ayın 1'i 09:00 | mature kararların 5/20/60 session realized performansı |

`monthly_audit_job` factor weight'lerini otomatik değiştirmez. Model kalibrasyonu ancak ayrı doğrulama/backtest sonrası manuel release ile yapılmalıdır.

## Çalışma modları

### `shadow`
Tam gerçek veri/karar zinciri çalışır ve DB'ye yazar. Normal action Telegram bildirimi gönderilmez. İlk kurulum ve model gözlemi için önerilen moddur.

### `live`
Shadow işlerinin yanında yeni staged action Telegram bildirimi ve live hata bildirimi etkinleşir. Realtime Execution açıksa actionable event sonrası execution worker da çalışır. **Otomatik emir yoktur.**

### `maintenance`
Yeni BTC/ETH ve URA günlük kararları atlanır. Veri/health/bakım job'ları çalışabilir. Tüm motoru durdurmak için Windows Service durdurulur.

## Realtime Execution

Normal worker yalnız şu durumda devreye girer:

```text
decision.status = ACTION
AND action_event = true
AND realtime_execution_enabled = true
```

Coinbase Exchange public WebSocket üzerinden BTC-USD ve ETH-USD için:

- spread bps
- top-N bid/ask USD depth
- order-book imbalance (OBI)
- microprice
- interval order-flow imbalance (OFI)
- executed-trade imbalance
- trade notional
- trade-ID gap count (matches channel bütünlük göstergesi)

üretilir. Raw order book ve raw trades DB'ye kaydedilmez.

`--test-realtime` ise Realtime checkbox kapalı olsa da çalışır; gerçek decision/action/signal-state oluşturmaz ve satırları `is_test=true`, `test_run_id=<uuid>` ile kaydeder.

## URA veri kalitesi birikimi

Global X full holdings ilk kez çekildiğinde kaynak ulaşılabilirliği kanıtlanır ancak holdings/flow yönü için en az iki farklı tarih gerekir; ilk snapshot'ta `fundamentals quality=0` beklenir.

Breadth kalite kapsamı gerçek geçmiş biriktikçe artar:

```text
2 snapshot    → 1 günlük pozitiflik ölçümü başlayabilir
20 snapshot   → 20DMA + 20D high ölçümleri
50 snapshot   → 50DMA
200 snapshot  → 200DMA
```

Böylece ilk gün sahte `%50 quality` verilmez. URA kararı başlangıçta `NO_ACTION_DATA` görebilir; bu güvenlik davranışıdır.

`fundamentals` adı altında v1.1.3'te kullanılan veri, **Global X holdings/price-adjusted AUM flow proxy**'sidir. Uranium spot/supply-demand datası değildir.

## Event semantics

- ETH/BTC: haber/event provider bağlı değil → `score=0, quality=0`.
- URA: SEC monitor çalışmadı/coverage yok → `quality=0`.
- SEC monitor entity'leri gerçekten kontrol etti ve filing yok → `score=0`, quality > 0; bu “kontrol edildi, yönlü olay yok” anlamına gelir.
- SEC filing bulunduğunda v1.1.3 filing'i event olarak saklar fakat semantik classifier olmadığı için otomatik severity uydurmaz.

## Regime eksenleri

`primary_regime` geriye uyumluluk ve factor-weight seçimi için korunur. `model.regimes.details` ayrıca:

```text
market_regime = RISK_ON | RISK_OFF | NEUTRAL
trend_regime  = STRONG_UPTREND | STRONG_DOWNTREND | FLAT | TRANSITION
```

saklar. Böylece örneğin makro `RISK_ON` iken URA `STRONG_DOWNTREND` olabilir; bu çelişki değildir.

## Decision provenance

`model.decisions.rationale.provenance` içinde en az:

- `market_data_date`
- `decision_evaluated_at`
- `price_provider`
- derivatives provider ve BTC/ETH `observed_at`
- macro observation dates

saklanır. Böylece kapanış tarihi ile kararın üretildiği gerçek zaman birbirine karışmaz.

## Varsayılan eşikler

```text
Min Data Quality       80
Min Edge               70
Min Confidence         70
Strong Edge            80
Strong Confidence      80
Regime Reset Edge      45
Regime Reset Days       5
Base Tranche           %25
Max Regime             %50
```

Volatilite directional vote vermez; risk/size katmanını etkiler.

## v1.2.0 validation

- Monthly audit: realized 5/20/60-session performance + model validation.
- `--validate-model`: manuel PIT core replay ve Shadow readiness.
- `--backfill-crypto --history-days 2500`: validation için one-time daha derin BTC/ETH history.
- Validation hiçbir weight/threshold/mode değerini otomatik değiştirmez.
