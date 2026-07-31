# Dönüşüm Sinyali Motoru Karar Sözleşmesi

Son güncelleme: 31 Temmuz 2026  
Kapsam: Rosa Investment Engine v1.2.0, ETH/BTC ve URA/USD  
Amaç: Yeni oturumların mevcut kod davranışıyla hedeflenen sonraki davranışı birbirine karıştırmasını engellemek.

## 1. Durum etiketleri

Bu belgede her önemli kural aşağıdaki etiketlerden biriyle değerlendirilir:

- `RELEASED`: v1.2.0 kodunda ve/veya veritabanı sözleşmesinde uygulanmış davranış.
- `APPROVED`: Kullanıcı tarafından kesinleştirilmiş ürün/mimari kararı; kodu ayrıca doğrulanmalıdır.
- `PROPOSED`: Önceki analizde önerilmiş, fakat kullanıcı tarafından henüz bağlayıcı şekilde onaylanmamış hedef.
- `OPEN`: Kanıt veya ürün kararı bekleyen konu.

Bir `PROPOSED` ya da `OPEN` madde, yeni oturum tarafından sessizce uygulanamaz. Davranış değişecekse kullanıcı kararı, test, model version ve yeni Shadow Epoch birlikte ele alınır.

## 2. Değişmez ürün sınırları

| Kural                                   | Durum                   | Açıklama                                                                                                  |
| --------------------------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------- |
| Motor otomatik emir göndermez           | `APPROVED` + `RELEASED` | `live` modu dahi karar/bildirim ve isteğe bağlı execution observation üretir.                             |
| Sinyaller portföyden bağımsızdır        | `APPROVED` + `RELEASED` | Sistemler `ETH/BTC` ve `URA/USD` olarak global çalışır; Python portföy bakiyesi veya seçili hesap okumaz. |
| İşlem kullanıcı tarafından yapılır      | `APPROVED`              | Gerçek alım/satım/dönüşüm Quasar'da manuel ve append-only kaydedilir.                                     |
| Tek Telegram botu ve Chat ID            | `APPROVED` + `RELEASED` | Bildirim hesap bazlı fan-out yapmaz.                                                                      |
| Shadow'dan LIVE'a otomatik geçiş yok    | `APPROVED` + `RELEASED` | `READY` yalnız manuel production review kapısını açar.                                                    |
| Eksik veri uydurulmaz                   | `APPROVED` + `RELEASED` | Kaynak/history yoksa factor `quality=0`; sahte nötr kalite verilmez.                                      |
| Model parametreleri otomatik ayarlanmaz | `APPROVED` + `RELEASED` | Validation/calibration yalnız rapor üretir.                                                               |

## 3. Sistemler ve yön semantiği

### ETH/BTC

- Pozitif signed edge: `BTC→ETH`
- Negatif signed edge: `ETH→BTC`
- Amaç, toplam portföy performansında BTC ve ETH arasında göreli güç/rejim değişimini değerlendirmektir.

### URA/USD

- Pozitif signed edge: `USD→URA`
- Negatif signed edge: `URA→USD`
- `fundamentals` factor adı v1.2.0'da fiziksel uranyum arz-talep modeli değildir; Global X URA holdings/price-adjusted AUM flow proxy'sidir.

Signed edge sıfır olduğunda kod yön etiketini pozitif bacağa verir; fakat edge sıfır olduğu için bu tek başına `ACTION` üretemez.

## 4. v1.2.0 karar zinciri — `RELEASED`

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
→ Decision Status
→ Persistent Signal State (K1/K2)
→ Supabase snapshots/history
→ Shadow veya LIVE bildirim davranışı
```

### 4.1 Teknik girdiler

Her iki sistemin fiyat çekirdeğinde aşağıdaki göstergeler bulunur:

- EMA 10 ve EMA 21
- EMA cross age ve EMA21 beş günlük eğimi
- MACD 12/26/9 ve cross age
- RSI 14
- Bollinger 20/2, `%B` ve band genişliği
- 36 aylık percentile
- 52 haftalık z-score
- 20/60 dönem realized volatility
- hacim/relative-volume girdileri

ETH/BTC ayrıca BTC ve ETH günlük fiyat/hacimlerini oranlar, derivatives ve makro girdileri kullanır. URA/USD, URA fiyatlarına ek olarak Global X holdings/flow, coverage-aware breadth ve SEC event-monitor kalitesi kullanır.

### 4.2 Factor kümeleri

| Sistem  | Directional model factor'ları                                             |
| ------- | ------------------------------------------------------------------------- |
| ETH/BTC | `value`, `trend`, `momentum`, `derivatives`, `flow`, `macro`, `event`     |
| URA/USD | `value`, `trend`, `momentum`, `macro`, `fundamentals`, `breadth`, `event` |

Volatilite yön oyu değildir; risk ve büyüklük katmanını etkiler. Factor ağırlıkları `config/defaults.json` içinde `RISK_ON_TREND`, `MEAN_REVERSION`, `RISK_OFF`, `NEUTRAL` rejimlerine göre versioned kaynak olarak tutulur.

## 5. Skor matematiği — `RELEASED`

Her factor için:

```text
quality_weight = factor_weight × factor_quality / 100
signed_edge    = Σ(factor_score × quality_weight) / Σ(quality_weight)
edge           = abs(signed_edge)
data_quality   = Σ(factor_quality × factor_weight) / Σ(configured_factor_weight)
```

`quality <= 0` factor edge hesabına katılmaz. Ancak data quality paydası tüm yapılandırılmış ağırlıkları içerdiği için eksik factor toplam kaliteyi düşürür.

Directional agreement yalnız pozitif ve negatif factor skorlarından hesaplanır:

```text
agreement = abs(Σ(sign(score))) / directional_factor_count × 100
confidence = clamp(edge × 0.65 + data_quality × 0.20 + agreement × 0.15, 0, 100)
uncertainty = 100 - confidence
```

`score=0` directional oy sayılmaz. Gerçekten izlenen fakat yön üretmeyen bir kaynak `score=0, quality>0` olabilir; hiç izlenmeyen kaynak `score=0, quality=0` olmalıdır.

## 6. Varsayılan eşikler — `RELEASED`, Shadow süresince kilitli

```text
Minimum Data Quality = 80
Minimum Edge         = 70
Minimum Confidence   = 70
Strong Edge          = 80
Strong Confidence    = 80
Regime Reset Edge    = 45
Regime Reset Days    = 5
Base Tranche         = %25
Max Regime           = %50
WATCH Edge           = 55
```

31.07.2026–29.08.2026 Shadow gözleminde bu değerler checkpoint sonuçlarına bakılarak değiştirilmez.

## 7. Karar statüsü önceliği — `RELEASED`

Sıra bağlayıcıdır:

1. `data_quality < 80` → `NO_ACTION_DATA`
2. Event veto → `BLOCKED_EVENT`
3. Late entry ve `edge >= 70` → `BLOCKED_LATE`
4. `edge >= 70` ve `confidence >= 70` → `ACTION`
5. `edge >= 55` → `WATCH`
6. Diğer durumlar → `WAIT`

Event veto, late-entry ve quality kapıları geçilmeden edge tek başına aksiyon değildir.

## 8. Late-entry kuralları — `RELEASED`

Yön için aşağıdakilerden biri oluşursa late-entry işaretlenir:

- İlgili EMA cross age `> 5` gün veya cross bulunamaması
- Pozitif yön RSI `>= 68`
- Negatif yön RSI `<= 32`
- Pozitif yön Bollinger `%B > 0.85`
- Negatif yön Bollinger `%B < 0.15`
- Pozitif yön 36 aylık percentile `> %45`
- Negatif yön 36 aylık percentile `< %55`

Late-entry yalnız edge minimum action eşiğine ulaştığında `BLOCKED_LATE` statüsünü doğurur. Daha düşük edge, `WATCH` veya `WAIT` akışında kalabilir.

## 9. Risk ve önerilen büyüklük — `RELEASED`

```text
vol_ratio        = rv20 / rv60
risk             = clamp(50 + (vol_ratio - 1) × 50, 0, 100)
confidence_factor= clamp(confidence / 90, 0.40, 1.00)
vol_factor       = clamp(1 / max(vol_ratio, 0.70), 0.35, 1.00)
recommended_size = min(max_regime_pct, base_tranche_pct × confidence_factor × vol_factor)
```

Bu nedenle K1/K2'nin her biri sabit `%25` olmak zorunda değildir; `recommended_size` confidence ve volatilite nedeniyle daha küçük olabilir.

## 10. Persistent K1/K2 state — mevcut v1.2.0 gerçeği

### Uygulanmış davranış — `RELEASED`

- İlk uygun `ACTION`, aktif yön farklıysa yeni rejimi **hemen** başlatır ve K1 üretir.
- K1 büyüklüğü `min(recommended_size, %25, rejimde kalan pay)` değeridir.
- K2 yalnız aynı yönde, K1'den farklı bir `as_of` tarihinde, edge `>=80` ve confidence `>=80` ise üretilebilir.
- K2 için mevcut kodda beş karar seansı bekleme şartı yoktur.
- Aynı `as_of` tekrarında yeni kademe oluşmaz.
- Toplam rejim büyüklüğü `%50`yi aşmaz.
- Karşı yönde yeterli `ACTION` gelirse mevcut rejim beklemeden sıfırlanır ve karşı yönde K1 başlar.
- Aktif yön aynı ve edge `>=45` ise reset sayacı sıfırlanır.
- `ACTION` dışı/zayıf koşullar reset sayacını artırır; sayaç 5'e ulaştığında aktif rejim temizlenir.
- State `model.signal_state` tablosunda tutulur; servis yeniden başladığında korunur.

### Bilinen doğrulama açığı — `OPEN`

Production K1/K2 state machine'i, PIT replay sinyal seçicisi tarafından birebir kullanılmıyor. Bu nedenle v1.2.0 replay çıktısı gerçek K1/K2 olay sayısını, kademeler arası süreyi veya toplam dönüşüm yüzdesini doğrulamaz.

## 11. Python action size ve Quasar dönüşüm oranı

### Bugünkü teknik gerçek — `RELEASED`

- Python `action_size`, global piyasa kararı için modelin önerdiği rejim kademesidir; portföy adedi değildir.
- Python `public.user_investment_settings` tablosunu ve Quasar'daki `%50` dönüşüm ayarlarını okumaz.
- Quasar `btc_eth_conversion_pct` ve `ura_usd_conversion_pct` değerlerini kullanıcı seviyesinde tutar.
- Mevcut `ConversionForm` dönüşümü otomatik uygulamaz; kullanıcı mevcut bakiyeden `%25/%50/%75/%100` veya manuel miktar seçer.
- Dolayısıyla v1.2.0'da Python yüzdesi ile Quasar yüzdesinin otomatik çarpıldığı ya da `min(...)` ile uygulandığı bir entegrasyon yoktur.

### Hedef yorum — `PROPOSED`, henüz bağlayıcı değil

- Python `action_size`: modelin önerdiği gerçek kademe yüzdesi.
- Quasar dönüşüm oranı: kullanıcının bir rejimde izin verdiği maksimum toplam dönüşüm sınırı.
- Uygulanacak öneri: `min(Python action_size, kullanıcı limitinde kalan pay)`.
- Quasar gerçek çevrilecek adedi seçili hesabın güncel kaynak bakiyesinden hesaplar; işlem yine kullanıcı onayıyla kaydedilir.

Bu hedef kabul edilirse backend sözleşmesi, Quasar sinyal→dönüşüm akışı ve testleri aynı değişiklik setinde güncellenmelidir. Onay gelmeden mevcut `%50` ayarlarının anlamı sessizce değiştirilemez.

## 12. PIT replay ve calibration — `RELEASED`

### ETH/BTC directional core

- Yalnız geçmiş tarihte mevcut olabilecek fiyat ve makro verileri kullanır.
- Güvenilir point-in-time geçmişi olmadığı için derivatives ve event factor'ları `quality=0` ile dışarıda bırakılır.
- Bugünkü derivatives/event verisi geçmiş tarihe taşınmaz.
- Bu nedenle çıktı “historical production ACTION backtest” değil, directional core doğrulamasıdır.

### Replay sinyal seçimi

Mevcut seçici:

- edge threshold'u geçen,
- late-entry olmayan,
- yön işareti sıfır olmayan

noktaları seçer; sinyaller arasında varsayılan 5 seans cooldown uygular. Ancak production decision statüsündeki quality/confidence kapılarını ve persistent K1/K2 state'ini birebir çalıştırmaz.

### Exploratory calibration

- Aday edge eşikleri: `50, 55, 60, 65, 70, 75, 80`
- Train/holdout ayrımı: `%70 / %30`
- Birincil horizon: 20 seans
- Minimum uygunluk: train'de 8, holdout'ta 3 sinyal
- Sonuç yalnız aday raporudur; settings'e yazılmaz.

### URA/USD

Holdings, breadth ve event point-in-time geçmişi yeterli olmadıkça full replay `NOT_READY` kalır. Bugünkü holdings bileşenlerini geçmişe taşıyarak sonuç üretmek yasaktır.

## 13. Monthly realized-performance audit — `RELEASED`

- Gerçek Shadow/production `ACTION` ve `WATCH` kararlarını 5/20/60 trading-session horizonlarında değerlendirir.
- Direction-adjusted return, hit rate ve gözlem sayısını `model.performance` tablosuna yazar.
- Factor ağırlığı veya eşik değiştirmez.
- Bu audit, full PIT backtestin yerine geçmez; farklı bir kanıt katmanıdır.

## 14. Shadow Readiness — mevcut v1.2.0 sözleşmesi

### Eşikler — `RELEASED`

```text
Shadow calendar days       >= 30
ETH/BTC decision days      >= 25
URA/USD decision days      >= 20
Median data quality        >= 80
Recent job success         >= %98
Realtime smoke age         <= 7 gün
URA holdings dates         >= 2
URA breadth dates          >= 20
```

Sonuçlar:

- `NOT_READY`: süre/history birikmedi.
- `BLOCKED`: süre/history yeterli, fakat quality/health/realtime blocker var.
- `READY`: manuel LIVE değerlendirmesine izin verir; otomatik geçiş değildir.

### Bilinen readiness açıkları — `OPEN`

- Shadow süresi, aynı model version'daki ilk ve son karar arasından türetiliyor; açık bir `shadow_epoch_id`/`shadow_started_at` yok.
- Son 7 gün job hesabında `OK`, `DEGRADED` ve `SKIPPED` başarılı kabul ediliyor.
- Beklenen scheduler çalışma sayısı gerçekleşen sayıyla karşılaştırılmıyor.
- Development/manual/backfill çalışmaları ayrı epoch/run-kind ile dışlanmıyor.
- `OK rate` ile `completed rate` ayrıştırılmıyor.

Bu açıklar Görev 4 sonrası diagnostics/readiness hardening kapsamıdır; eşik değişikliği değildir.

## 15. Shadow görevlerinin model geliştirmesine etkisi

| Görev | Kanıt                                            | İzin verilen geliştirme                                                                    |
| ----- | ------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| 1–3   | Scheduler, provider, snapshot, health, job audit | Operasyonel sapmayı düzelt; model davranışını değiştirme.                                  |
| 4     | 7 günlük ilk güvenilirlik                        | Shadow Epoch, job sınıflandırması, edge/status diagnostics; eşikleri değiştirme.           |
| 5–6   | 14 günlük stabilite ve URA 20 günlük quality     | Factor katkılarını/freshness'i ayrıştır; kanıtsız score/quality ekleme.                    |
| 7     | 30 günlük graduation                             | PIT, walk-forward, monthly realized sonuçlar ve Shadow dağılımlarını birlikte değerlendir. |

Görev sonucu tek başına weight/threshold değişikliği yetkisi vermez.

## 16. v1.3 için önerilen parity/whipsaw hedefi — `PROPOSED`

Aşağıdaki hedef önceki oturum analizinin önerisidir; henüz v1.2.0 davranışı veya onaylanmış karar değildir:

1. Production ve replay aynı versioned state machine'i kullanır.
2. K1 ilk normal `ACTION` olayında oluşur.
3. K2 aynı yönde `80/80` koşuluna ek olarak önceki aksiyondan en az 5 karar seansı sonra oluşur.
4. Karşı yöne geçiş için en az iki ardışık kapanışta yeterli karşı-yön `ACTION` doğrulaması gerekir.
5. Her kademe arasında en az 5 karar seansı bulunur.
6. Aynı sistem/tarih/yön/kademe olayı idempotenttir; tekrar bildirilemez.
7. Toplam rejim ve kullanıcı limiti aşılmaz.
8. Servis restart, reversal, reset ve production/replay parity unit testlerle kanıtlanır.

Bu değişiklikler sinyal sıklığını ve zamanlamasını değiştireceği için basit hotfix değildir; kullanıcı onayından sonra yeni model version ve yeni Shadow Epoch gerektirir.

## 17. Zorunlu test matrisi — sonraki model davranış değişikliği için

- Quality `79.99 / 80.00`
- Edge `69.99 / 70.00`
- Confidence `69.99 / 70.00`
- Eksik factor `quality=0`
- Nötr factor'un directional oy sayılmaması
- Quality → event veto → late-entry → action önceliği
- K1, K2, küçük `recommended_size` ve `%50` cumulative cap
- Aynı gün tekrar aksiyon üretmeme
- Beş zayıf karar sonrası reset
- Karşı yön değişimi
- State'in servis restart sonrası korunması
- Production/replay parity
- Shadow epoch ve job-kind ayrımı
- Beklenen/gerçekleşen scheduler run hesabı

Mevcut repoda `scripts/release_check.py` marker/sözleşme kontrolleri yapar; bu state-machine sınırlarını kapsayan gerçek unit test paketi bulunmadığı için “release check geçti” ifadesi bu davranışların test edildiği anlamına gelmez.

## 18. Versioning ve değişiklik kapısı

- Veri/scheduler/observability hatası, model davranışını değiştirmiyorsa v1.2.x hotfix olabilir.
- Factor, ağırlık, eşik, K1/K2, reversal, cooldown, action-size otoritesi veya replay parity değişirse yeni model version gerekir.
- Yeni model version, eski Shadow kanıtını kendiliğinden devralmaz; yeni Shadow Epoch başlatılır.
- Contract, test planı, migration/provenance ihtiyacı ve Quasar yüzeyi aynı release içinde güncellenir.
- LIVE geçişi her durumda manuel production review gerektirir.

## 19. Kaynak gerçekleri

Bu sözleşme aşağıdaki repo kaynaklarıyla çapraz doğrulanmıştır:

- `app/engines/decision.py`
- `app/engines/signal_state.py`
- `app/engines/veto.py`
- `app/engines/risk.py`
- `app/backtest/validation.py`
- `app/database/repository.py`
- `config/defaults.json`
- `MODEL_AND_SCHEDULE.md`
- `MODEL_VALIDATION_AND_SHADOW.md`
- `TEST_PLAN_V1_2_0.md`
- `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`

Kod ile bu belge çelişirse yeni oturum önce çelişkiyi raporlar; kullanıcı kararı olmadan belgeyi veya kodu sessizce “doğru” kabul etmez.
