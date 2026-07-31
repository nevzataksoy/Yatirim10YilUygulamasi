# Model Validation ve Shadow -> LIVE Gate — v1.2.0

## Amaç

v1.2.0, model parametrelerini geçmiş veriye bakıp otomatik değiştirmez. İki ayrı doğrulama katmanı kullanır:

1. **PIT Core Replay (ETH/BTC):** Geçmişte o tarihte mevcut olabilecek fiyat + makro verileriyle value/trend/momentum/flow/macro çekirdeğini tekrar oynatır.
2. **Shadow Readiness:** Gerçek Shadow kararlarının, job başarılarının, veri kalitesinin, realtime testinin ve URA history birikiminin production gözlem kriterlerini karşılayıp karşılamadığını ölçer.

Bu iki katmandan hiçbiri `engine_mode=live` yapmaz. LIVE kararı manueldir.

## Neden full historical production backtest değil?

Derivatives, crypto event/sentiment, Global X holdings/breadth ve SEC/event kapsamının güvenilir point-in-time tarihçesi henüz yeterli değildir. Bugünkü veriyi geçmişe taşıyarak backtest yapmak look-ahead bias üretir.

Bu nedenle ETH/BTC replay içinde historical olarak güvenilir olmayan:

- derivatives,
- event/sentiment

faktörlerinin quality değeri `0` kabul edilir. Replay yalnız directional core'u sınar.

URA/USD full PIT replay ise yeterli holdings/breadth/event history birikene kadar `NOT_READY` olarak raporlanır.

## CLI

```bat
InvestmentEngineCLI.cmd --validate-model
```

Beklenen çıktı örneği:

```text
Model validation başlatılıyor...
model_validation: OK — core=OK observations=... shadow=NOT_READY candidate_edge=...
```

`candidate_edge` yalnız exploratory calibration sonucudur. Ayarlara otomatik yazılmaz.

## Supabase tabloları

### model.validation_runs

Her validation çalışmasının audit geçmişidir.

### public.model_validation_snapshot

Mobil/dashboard tarafının okuyabileceği son validation sonucudur.

Örnek:

```sql
select *
from public.model_validation_snapshot
order by validation_type, system;
```

## Shadow readiness varsayılan kriterleri

- Minimum Shadow süresi: **30 takvim günü**
- ETH/BTC farklı karar günü: **25**
- URA/USD farklı karar günü: **20**
- Median Data Quality: **>= 80**
- Son 7 günlük job başarı oranı: **>= %98**
- Başarılı realtime smoke test yaşı: **<= 7 gün**
- URA holdings snapshot: **>= 2 farklı gün**
- URA breadth history: **>= 20 gün**

Sonuçlar:

- `NOT_READY`: Gözlem/history henüz yeterli değil.
- `BLOCKED`: Yeterli gözlem süresine rağmen quality/health/realtime kriterlerinden biri başarısız.
- `READY`: Gate kriterleri geçildi. Bu yalnız manuel LIVE değerlendirmesine izin verir.

## Calibration yaklaşımı

ETH/BTC core replay edge threshold'larını train/holdout ayrımıyla karşılaştırır. Holdout sonucu model parametresini otomatik değiştirmek için kullanılmaz; yalnız adayları raporlar.

Minimum sinyal sayısı yetersizse sonuç `LIMITED_SIGNAL_COUNT` olur. Bu bir hata değildir; modelin az sayıda güçlü sinyal ürettiğini gösterebilir.

## Monthly audit

`monthly_audit_job` artık:

1. Mature `ACTION/WATCH` kararlarının 5/20/60 session performansını günceller.
2. Model validation çalıştırır.
3. Shadow readiness'i günceller.
4. Ağırlıkları ve threshold'ları **değiştirmez**.

## Model version provenance

v1.2.0 sonrası yeni kararlar:

- `model.decisions.model_version`
- `public.decision_snapshot.model_version`
- `public.decision_history.model_version`

alanlarında model sürümünü taşır. Eski kararlar migration sırasında `legacy-pre-1.2.0` olarak işaretlenir.

## History backfill

Günlük production crypto job yaklaşık 1300 günlük rolling history toplar. Bu, 36 aylık warm-up sonrasında PIT replay için sınırlı değerlendirme penceresi bırakabilir. Daha anlamlı validation öncesi bir kez:

```bat
InvestmentEngineCLI.cmd --backfill-crypto --history-days 2500
```

çalıştırılır. Backfill mevcut satırları `upsert` eder; duplicate üretmez. Ardından `--validate-model` tekrar çalıştırılır.

Replay değerlendirme noktası 365'in altındaysa `PIT_CORE_REPLAY` sonucu `LIMITED_HISTORY` olur; bu hata değil, daha derin history gerektiğini gösterir.
