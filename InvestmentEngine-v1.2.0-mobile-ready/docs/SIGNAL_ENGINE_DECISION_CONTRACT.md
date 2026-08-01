# Dönüşüm Sinyali Motoru Karar Sözleşmesi

Son güncelleme: 01 Ağustos 2026  
Kapsam: Rosa Investment Engine **v1.2.0**, `ETH/BTC` ve `URA/USD`

Bu belge yayımlanmış motorun matematiksel ve işlevsel gerçeğini açıklar. Amaç yeni oturumların “kodda var”, “ürün kararı olarak kesin”, “önerilmiş” ve “henüz kanıt bekliyor” kavramlarını birbirine karıştırmasını önlemektir.

## 1. Durum etiketleri

- `RELEASED`: v1.2.0 kodunda veya uygulanan veritabanı sözleşmesinde mevcut davranış.
- `APPROVED`: kullanıcı tarafından kesinleştirilmiş ürün/mimari kararı; kodu ayrıca doğrulanır.
- `PROPOSED`: önerilmiş fakat kullanıcı tarafından bağlayıcı biçimde onaylanmamış hedef.
- `OPEN`: kanıt, ürün kararı veya teknik parity bekleyen konu.

`PROPOSED` veya `OPEN` madde kullanıcı onayı olmadan kodlanamaz. Model davranışı değişiyorsa model version, test, deployment ve yeni Shadow Epoch birlikte ele alınır.

## 2. Değişmez ürün sınırları

| Kural                            | Durum                 | Açıklama                                                                                                                            |
| -------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Otomatik borsa emri yok          | `APPROVED + RELEASED` | LIVE bile yalnız yeni action event bildirimi ve isteğe bağlı order-book gözlemi üretir.                                             |
| Motor portföyden bağımsız        | `APPROVED + RELEASED` | Python seçili Quasar hesabını, adet/bakiyeyi veya kullanıcı işlemlerini okumaz.                                                     |
| Gerçek işlem kullanıcı onaylı    | `APPROVED`            | Alım/satım/dönüşüm Quasar'da seçili hesapta manuel ve append-only kaydedilir.                                                       |
| Model oranı tavsiyedir           | `APPROVED`            | `action_size` gerçek işlem oranını zorlamaz; kullanıcı Telegram/Quasar bilgisini değerlendirip oranı veya miktarı kendisi belirler. |
| Sinyal bağı tek yönlüdür         | `APPROVED`            | Quasar isteğe bağlı `decision_id` kaydeder; Python portföy işlemini geri okuyup sinyali değiştirmez.                                |
| Aylık DCA ana disiplin           | `APPROVED`            | Sinyal motoru aylık sermaye ayırmayı otomatik durdurmaz veya zorunlu dağılım vermez.                                                |
| READY otomatik LIVE değildir     | `APPROVED + RELEASED` | READY yalnız manuel production review kapısıdır.                                                                                    |
| Eksik veri uydurulmaz            | `APPROVED + RELEASED` | Kaynak/history yoksa factor quality `0`; sahte nötr kalite verilmez.                                                                |
| Validation parametre değiştirmez | `APPROVED + RELEASED` | Threshold, weight ve mode yalnız raporla değişmez.                                                                                  |
| Tek Telegram hedefi              | `APPROVED + RELEASED` | Python tek bot/Chat ID kullanır; hesap bazlı fan-out yoktur.                                                                        |

## 3. Sistemler ve yön semantiği

### 3.1 ETH/BTC

Motor BTC ve ETH'nin USD fiyatlarından:

```text
ETH/BTC ratio = ETH-USD close / BTC-USD close
```

üretir.

- `signed_edge > 0` → yön etiketi `BTC→ETH`
- `signed_edge < 0` → yön etiketi `ETH→BTC`

Bu etiket göreli avantaj yönüdür. `WAIT`, `WATCH`, `NO_ACTION_DATA` veya blocker ile gelen yön işlem talimatı değildir.

### 3.2 URA/USD

- `signed_edge > 0` → `USD→URA`
- `signed_edge < 0` → `URA→USD`

`fundamentals` adı fiziksel uranyum arz-talep modeli değildir. v1.2.0'da resmî Global X URA holdings verisinden türetilen price-adjusted AUM flow proxy'sidir.

### 3.3 Sıfır signed edge

Kod `signed_edge >= 0` olduğunda pozitif yön etiketini seçebilir. `edge=0` action eşiğini geçemeyeceğinden bu etiket tek başına aksiyon değildir.

## 4. Runtime karar zinciri — `RELEASED`

```text
Ham veri
→ freshness/source quality
→ features
→ macro + market/trend regime
→ factor scores ve factor quality
→ rejime göre factor weights
→ quality-adjusted signed edge
→ edge, data quality, directional agreement
→ confidence / uncertainty
→ event veto + late-entry gate
→ volatility risk / recommended size
→ decision status
→ persistent signal state (K1/K2)
→ model/public tablolar
→ SHADOW kayıt veya LIVE bildirim/order-book gözlemi
```

### Günlük ETH/BTC işi

1. Coinbase BTC-USD ve ETH-USD günlük history alınır.
2. Son kapanış tarihleri eşit değilse karar üretilmez.
3. `market.daily_prices` ve `public.market_snapshot` güncellenir.
4. ETH/BTC features üretilip `model.features`a yazılır.
5. As-of makro observation'ları alınır; macro score ve quality hesaplanır.
6. Regime oluşturulup `model.regimes`a yazılır.
7. Derivatives pair 3 saatten eski/eksikse best-effort refresh yapılır.
8. Factor'lar hesaplanır ve `model.factor_scores`a yazılır.
9. Decision üretilir; persistent state uygulanır.
10. Private decision, public snapshot/history, health ve job audit yazılır.

### Günlük URA/USD işi

1. Alpha Vantage daily/weekly/monthly URA fiyatları alınır.
2. Global X dated holdings best-effort yenilenir.
3. Holdings geçmişinden flow proxy; constituent geçmişinden breadth üretilir.
4. SEC monitor health/event metadata alınır.
5. Technical, macro, fundamentals, breadth ve event factor'ları hesaplanır.
6. Aynı decision/state/audit zinciri çalışır.

## 5. Teknik feature çekirdeği — `RELEASED`

Her iki sistemde:

- EMA 10 ve EMA 21
- Bull/bear EMA cross age
- EMA21 beş günlük yüzde eğimi
- MACD 12/26/9, signal, histogram; ETH/BTC için cross age
- RSI 14
- Bollinger 20/2 `%B` ve band width
- 36 aylık percentile rank
- 52 haftalık z-score
- realized volatility 20 ve 60 dönem
- ATR yüzde girdileri
- hacim/relative-volume girdileri

ETH/BTC ayrıca BTC ve ETH notional relative volume ölçer. URA doğrudan ETF fiyat/hacim feature'larını kullanır.

### 5.1 Canlı kararın gerçek veri pencereleri — `RELEASED`

`regime_reset_days=5`, feature geçmişini beş günle sınırlamaz. Reset sayacı yalnız
`model.signal_state` içindeki aktif K1/K2 hafızasını temizleme eşiğidir. Canlı karar
her çalıştırmada aşağıdaki birbirinden farklı pencereleri yeniden hesaplar:

| Girdi / gösterge       | ETH/BTC canlı pencere                                                                                                                                  | URA/USD canlı pencere                                                                                                                   | Karardaki rolü                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Ham günlük fiyat       | Her günlük işte yaklaşık son `1300` takvim günü istenir; en az `1100` ortak BTC/ETH günü zorunludur                                                    | Kod `outputsize` sabitlemez; provider'ın döndürdüğü günlük seri kullanılır ve en az `60` bar zorunludur                                 | Bütün günlük teknik göstergelerin kaynak serisi                                         |
| Uzun dönem değer       | Son `36` tamamlanmış ay percentile + yaklaşık son `52` haftalık örnek z-score                                                                          | Son `36` aylık kapanış percentile + son `52` haftalık kapanış z-score                                                                   | `value` factor ve late-entry kontrolü                                                   |
| EMA / MACD / RSI       | EMA `10/21`, MACD `12/26/9`, RSI `14`; hesap eldeki günlük serinin tamamında yürür, eski gözlemlerin etkisi üstel olarak azalır                        | Aynı                                                                                                                                    | `trend`, `momentum`, yön ve late-entry                                                  |
| Trend eğimi / cross    | EMA21'in son `5` günlük değişimi; EMA/MACD cross en fazla `30` bar geriye aranır; late-entry için izin verilen cross yaşı `5` gündür                   | Aynı                                                                                                                                    | Rejim/trend ekseni ve geç kalma kapısı                                                  |
| Bollinger / volatilite | Bollinger `20`; realized volatility `20/60`                                                                                                            | Aynı                                                                                                                                    | Late-entry, market regime ve sizing/risk                                                |
| ATR                    | BTC ve ETH için son `80` günlük girdi üzerinde EMA tabanlı ATR `14`                                                                                    | Günlük seride EMA tabanlı ATR `14`                                                                                                      | Feature/audit; directional edge ağırlık listesinde doğrudan factor değildir             |
| Hacim / flow           | Son `20` ortak günde BTC ve ETH USD-notional relative volume                                                                                           | Son `20` günlük URA relative volume feature'ı                                                                                           | ETH/BTC `flow`; URA'da mevcut directional weight listesinde ayrı `flow` factor'u yoktur |
| Derivatives            | Aynı venue'dan en fazla `3` saat yaşında son BTC+ETH snapshot çifti                                                                                    | Kullanılmaz                                                                                                                             | ETH/BTC `derivatives` factor                                                            |
| Makro                  | Her sekiz seri için `as_of` tarihindeki son observation; score VIX, STLFSI4 ve DFII10'un son değerlerinden gelir                                       | Aynı                                                                                                                                    | `macro` factor ve market regime                                                         |
| Makro freshness        | Günlük serilerde `4/8/14`, haftalık STLFSI4'te `10/17/24` günlük yaş bantları                                                                          | Aynı                                                                                                                                    | Sekiz serinin ortalama data quality değeri                                              |
| Event / haber          | Bağlı directional crypto event/sentiment provider yoktur; factor `score=0, quality=0`. Yalnız varsa son `48` saatte severity `<=-80` event veto aranır | SEC job son `14` günlük filing'leri toplar; factor son `168` saati, veto son `72` saati kullanır; semantic severity yoksa yön `0` kalır | Veto ve event factor                                                                    |
| URA holdings           | Kullanılmaz                                                                                                                                            | Son iki farklı holdings tarihi; karşılaştırma aralığı `7/14/31` gün, snapshot freshness `3/7/14` gün bantlarıyla kalite düşer           | `fundamentals` flow proxy                                                               |
| URA breadth            | Kullanılmaz                                                                                                                                            | Constituent geçmişinde `2/20/50/200` observation; sorgu üst sınırı `220`                                                                | `breadth` factor                                                                        |

Dolayısıyla nihai signed edge yalnız kısa vadeli değildir: `36 ay`, `52 hafta`,
`60 gün`, `20 gün`, kısa momentum, son türev snapshot'ı ve son makro observation'ı
rejime göre birlikte ağırlıklandırılır. Bununla birlikte gösterilen
`market_regime/trend_regime` etiketi daha dar bir sınıflandırmadır: son makro score,
EMA21'in `5` günlük eğimi ve `rv20/rv60` oranından üretilir. Bu etiket tek başına
uzun dönem klasik boğa/ayı sınıflandırması olarak sunulmamalıdır.

URA günlük history uzunluğunun provider yanıtına bırakılmış olması bir
observability/reproducibility açığıdır; görev takvimi sırasında davranış
değiştirilmez, fakat sonraki hardening incelemesinde gerçek bar sayısı provenance'a
yazılmalı ve gerekli pencere açıkça versionlanmalıdır.

## 6. Factor kümeleri ve runtime ağırlık kaynağı

| Sistem  | Directional factor'lar                                                    |
| ------- | ------------------------------------------------------------------------- |
| ETH/BTC | `value`, `trend`, `momentum`, `derivatives`, `flow`, `macro`, `event`     |
| URA/USD | `value`, `trend`, `momentum`, `macro`, `fundamentals`, `breadth`, `event` |

`volatility` factor score'u üretilebilir fakat directional weighted edge listesinde değildir; risk/sizing katmanında kullanılır.

### Kritik kaynak otoritesi

v1.2.0 `DecisionEngine`, factor ağırlıklarını **`config/defaults.json`** dosyasından okur. `model.factor_weights` tablosu şemada vardır fakat yayımlanmış runtime bu tabloyu okumaz. DB tablosunun varlığı onu aktif configuration source yapmaz.

Rejim bazlı ağırlık setleri:

- `RISK_ON_TREND`
- `MEAN_REVERSION`
- `RISK_OFF`
- `NEUTRAL`

## 7. Factor skorları — `RELEASED`

Tüm skorlar `[-100, 100]` aralığına kırpılır.

### 7.1 Value

```text
value_score = (0.5 - percentile_36m) × 160
            + (-zscore_52w) × 20
```

Düşük percentile/z-score pozitif göreli değer, yüksek seviye negatif göreli değer üretir.

### 7.2 Trend

```text
ema_gap_pct = (EMA10 / EMA21 - 1) × 100
trend_score = ema_gap_pct × 350 + ema21_slope_5d × 12
```

### 7.3 Momentum

```text
rsi_score  = (RSI14 - 50) × 2.3
scale      = max(abs(ratio_or_price) × 0.001, 1e-8)
macd_score = clamp(MACD_hist / scale, -50, 50)
momentum   = rsi_score + macd_score
```

### 7.4 ETH/BTC flow

```text
btc_rvol = son BTC USD-notional hacmi / 20 günlük ortalama
eth_rvol = son ETH USD-notional hacmi / 20 günlük ortalama
relative_rvol = eth_rvol / btc_rvol
flow_score = ln(relative_rvol) × 40
```

Yayımlanmış factor quality `80`dir.

### 7.5 ETH/BTC derivatives

BTC ve ETH snapshot'ı yoksa veya venue farklıysa:

```text
score = 0
quality = 0
```

Aynı provider pair bulunduğunda:

```text
funding_diff_bps = (ETH funding_8h - BTC funding_8h) × 10000
basis_diff_pct   = ETH basis_pct - BTC basis_pct
oi_ratio         = ETH OI_USD / BTC OI_USD
crowd_penalty    = max(0, funding_diff_bps - 1.5) × 20
score            = basis_diff_pct × 20
                 + ln(oi_ratio) × 8
                 - crowd_penalty
quality          = 90
```

Deribit inverse perpetual OI zaten USD amount units; OKX `oiUsd` kullanır. BTC ve ETH farklı venue'dan karıştırılmaz.

### 7.6 Macro

Macro score yönü bugün üç bileşenden gelir:

```text
VIX contribution      = clamp((22 - VIXCLS) × 2, -40, 40)
Stress contribution   = clamp(-STLFSI4 × 20, -30, 30)
Real-rate contribution= clamp((1.5 - DFII10) × 8, -20, 20)
macro_score            = toplam
```

Macro quality ise sekiz beklenen serinin freshness quality ortalamasıdır:

```text
DGS2, DGS10, DFII10, VIXCLS,
STLFSI4, DTWEXBGS, NASDAQCOM, SP500
```

API isteğinin başarılı olması tek başına quality=100 değildir. Observation yaşı freshness bantlarına göre puanlanır.

### 7.7 URA fundamentals

İlk holdings snapshot yalnız kaynağın erişilebilir olduğunu kanıtlar:

```text
score = 0
quality = 0
```

İkinci farklı tarih oluşunca:

```text
score = flow_proxy_pct × 12
quality = holdings_weight_coverage
          × comparison_window_quality
          × snapshot_freshness_quality
```

Bu factor “Global X URA holdings price-adjusted AUM flow proxy”dir; uranium spot fundamentals değildir.

### 7.8 URA breadth

Mümkün bileşenler:

- `% above 20 DMA`
- `% above 50 DMA`
- `% above 200 DMA`
- `% positive day`
- `% new 20-day high`

History coverage ve freshness yoksa q0. Score, mevcut bileşenlerin nötr tabandan ölçeklenmiş ortalamasıdır.

### 7.9 Event

ETH/BTC event provider bağlı değildir:

```text
score = 0
quality = 0
```

URA SEC monitor quality:

```text
quality = min(70, exact SEC ticker ile eşleşen URA fon ağırlığı yüzdesi)
```

Semantic severity bulunmadığında “monitor çalıştı ve sessiz” durumu `score=0, quality>0` olabilir. Filing var diye yön uydurulmaz.

## 8. Regime sınıflandırması — `RELEASED`

```text
trend_strength = min(100, abs(ema21_slope_5d) × 25)
vol_ratio      = rv20 / rv60
```

Market axis:

```text
macro_score < -35 veya vol_ratio > 1.6 → RISK_OFF
macro_score >= -10                       → RISK_ON
diğer                                   → NEUTRAL
```

Trend axis:

```text
trend_strength > 35 → STRONG_UPTREND / STRONG_DOWNTREND
trend_strength < 15 → FLAT
diğer               → TRANSITION
```

Primary weight regime:

```text
market RISK_OFF                         → RISK_OFF
trend_strength > 35 ve macro >= -10    → RISK_ON_TREND
trend_strength < 15 ve vol_ratio < 1.15→ MEAN_REVERSION
diğer                                  → NEUTRAL
```

`model.regimes.probabilities` öğrenilmiş/kalibre edilmiş probability değildir. Primary rejime `0.7`, diğerlerinin her birine `0.1` yazan sabit gösterim dağılımıdır.

## 9. Edge, quality ve confidence matematiği — `RELEASED`

Her configured directional factor için:

```text
quality_weight = factor_weight × factor_quality / 100
```

Yalnız `quality > 0` factor edge numerator/denominator'a girer:

```text
signed_edge = Σ(factor_score × quality_weight)
              / Σ(quality_weight)
edge        = abs(signed_edge)
```

Toplam data quality, eksik factor'ları gizlememek için bütün configured weight paydasını korur:

```text
data_quality = Σ(factor_quality × factor_weight)
               / Σ(all configured factor weights)
```

Directional agreement yalnız non-zero factor score işaretlerinden hesaplanır:

```text
agreement = abs(Σ(sign(nonzero score)))
            / nonzero_directional_factor_count × 100
```

```text
confidence  = clamp(edge × 0.65
                  + data_quality × 0.20
                  + agreement × 0.15, 0, 100)
uncertainty = 100 - confidence
```

`score=0` directional oy değildir. Ancak `score=0, quality>0`, gerçekten izlenen fakat yön üretmeyen kaynağın data-quality katkısı olabilir.

## 10. Varsayılan eşikler — `RELEASED`

```text
Minimum Data Quality = 80
Minimum Edge         = 70
Minimum Confidence   = 70
Strong Edge          = 80
Strong Confidence    = 80
WATCH Edge           = 55
Regime Reset Edge    = 45
Regime Reset Days    = 5
Base Tranche         = 25%
Max Regime           = 50%
```

31.07.2026–29.08.2026 Shadow süresinde checkpoint çıktısına bakıp bu değerler değiştirilmez.

## 11. Karar status önceliği — `RELEASED`

Sıra bağlayıcıdır:

1. `data_quality < 80` → `NO_ACTION_DATA`
2. event veto → `BLOCKED_EVENT`
3. late-entry ve `edge >= 70` → `BLOCKED_LATE`
4. `edge >= 70` ve `confidence >= 70` → `ACTION`
5. `edge >= 55` → `WATCH`
6. diğer → `WAIT`

Yüksek edge, quality/veto/late-entry kapılarını atlayamaz.

## 12. Late-entry kuralları — `RELEASED`

İlgili yön için aşağıdakilerden biri late-entry sebebidir:

- EMA cross age `> 5` veya cross bulunamaması
- Pozitif yön: `RSI >= 68`
- Negatif yön: `RSI <= 32`
- Pozitif yön: Bollinger `%B > 0.85`
- Negatif yön: Bollinger `%B < 0.15`
- Pozitif yön: 36 aylık percentile `> 0.45`
- Negatif yön: 36 aylık percentile `< 0.55`

Late-entry, status'u yalnız edge action eşiğine ulaştığında `BLOCKED_LATE` yapar. Düşük edge yine WATCH/WAIT olabilir.

## 13. Risk ve recommended size — `RELEASED`

```text
vol_ratio         = rv20 / rv60
risk              = clamp(50 + (vol_ratio - 1) × 50, 0, 100)
confidence_factor = clamp(confidence / 90, 0.40, 1.00)
vol_factor        = clamp(1 / max(vol_ratio, 0.70), 0.35, 1.00)
recommended_size  = min(max_regime_pct,
                        base_tranche_pct × confidence_factor × vol_factor)
```

Decision status ACTION değilse runtime `recommended_size` değerini `0` yapar. Bir K1/K2 kademesi sabit %25 olmak zorunda değildir; confidence/volatility yüzünden daha küçük olabilir.

Bu yayımlanmış formül `data_quality` değerini doğrudan yüzdeye çevirmez. Kullanıcının “sinyal kalitesine/gücüne göre oran” hedefinin v1.2.0'daki somut karşılığı confidence ve volatiliteyle küçülen model kademesidir. Gelecek formülde hangi strength/quality bileşenlerinin kullanılacağı görev takvimi sonrasında ayrıca kararlaştırılır; bu sözleşme mevcut formülü sessizce değiştirmez.

## 14. Persistent K1/K2 state — v1.2.0 gerçeği

### `RELEASED`

- İlk qualified `ACTION`, aktif yön farklıysa karşı yön dahil yeni rejimi **hemen** başlatır.
- K1:

```text
action_size = min(recommended_size, base_tranche 25%, remaining regime cap)
```

- K2 yalnız:
  - aktif yön aynı,
  - stage `1`,
  - `as_of` son action tarihinden farklı,
  - edge `>=80`,
  - confidence `>=80`
    olduğunda oluşabilir.
- K2 için yayımlanmış kodda 5 karar seansı bekleme şartı yoktur.
- Aynı `as_of` tekrarında yeni kademe yoktur.
- Cumulative regime size `%50`yi aşmaz.
- Qualified karşı-yön ACTION mevcut rejimi beklemeden sıfırlar ve karşı yönde K1 başlatabilir.
- Aktif yön aynı ve edge `>=45` ise reset counter sıfırlanır.
- ACTION dışı/zayıf kararlar reset counter'ı artırır; `5` olduğunda aktif state temizlenir.
- Reset counter ayrı bir “son 5 gün verisi” penceresi taramaz; `apply_signal_state` çağrılarındaki ardışık zayıf karar değerlendirmelerini sayar. Kod farklı `as_of` şartı aramadığı için aynı tarihli manuel tekrarlar da sayacı etkileyebilir.
- Her günlük karar kendi uzun/kısa rolling feature geçmişini kullanır; reset sonrası yeni karar önceki turla büyük ölçüde örtüşen veri setine dayanabilir.
- State temizlendikten sonra yeni qualified ACTION aynı yöndeyse, arada ters rejim görülmeden yeniden K1 başlayabilir. Mevcut üründe “önce mutlaka ters yön görülmeli” kuralı yoktur.
- State `model.signal_state` tablosunda kalıcıdır; servis restart'ında korunur.

### Status ile action event farkı

```text
status=ACTION
```

günlük koşulun uygun olduğunu söyler. Telegram/yeni kademe için:

```text
action_event=true
```

gerekir. Aynı rejimde yeni kademe şartı oluşmadıysa ACTION satırı olabilir ama yeni event olmaz.

### Reset araştırması — `OPEN`, görev takvimi sonrası

Beş zayıf değerlendirme sonrası aynı yönün yeniden K1 olabilmesi tek başına hata kabul edilmez. İncelemede şu kanıtlar birlikte değerlendirilir:

- zayıf kararların farklı `as_of` günleri olup olmadığı,
- kararların kullandığı rolling feature geçmişinin ne kadar örtüştüğü,
- reset sonrası qualified kararın aynı verilerde gerçekten yeni güç kazanıp kazanmadığı,
- manuel tekrar/idempotency etkisi,
- aynı yönü yasaklamak yerine mevcut piyasa yönünün yeniden değerlendirilmesinin daha doğru olup olmadığı.

`regime_reset_days` değerini `5`ten `30`a çıkarmak factor, edge, confidence,
`market_regime` veya `trend_regime` hesabını değiştirmez. Yalnız persistent state'i
daha uzun süre aktif tutar. Bunun beklenen etkileri:

- aynı yönde yeni K1'in daha uzun süre engellenmesi,
- K1/K2 stage ve kümülatif model öneri tavanının daha uzun süre korunması,
- qualified karşı-yön `ACTION`ın yine beklemeden immediate reversal yapması,
- gerçek bir durulma ve yeniden güçlenme `5–29` değerlendirme içinde oluşursa yeni
  aynı-yön K1 fırsatının bastırılabilmesi,
- aynı `as_of` manuel tekrarlarının reset oluşturma riskinin azalması fakat
  idempotency sorununun çözülmemesi,
- aynı yön edge `>=45` oldukça counter her seferinde sıfırlandığı için `30` ardışık
  zayıf değerlendirmeye ulaşmanın pratikte çok zorlaşması.

Bu nedenle `30`, yönü daha doğru hesaplayan daha uzun veri analizi değildir; yalnız
rejim hafızasını daha yapışkan hale getirir. Veri pencerelerini uzatmak veya çoklu
zaman ufuklu boğa/ayı sınıflandırması eklemek ayrı bir model değişikliğidir.

Görev takvimi bitmeden reset, reversal, K1/K2 veya action-size davranışı değiştirilmez. Değişiklik gerekirse yeni model version ve yeni Shadow Epoch açılır.

## 15. Python action size ve Quasar manuel dönüşüm oranı

### Bugünkü gerçek — `RELEASED`

- Python `action_size` global model kademesidir.
- Portföy adedi veya kullanıcının gerçek işlemi değildir.
- Python `public.user_investment_settings` veya seçili Quasar hesabını okumaz.
- Quasar kullanıcıya bakiye üzerinden yüzde butonları ve manuel miktar sunar.
- Python'un `max_regime_pct=%50` değeri yalnız global model önerilerinin aynı state içindeki kümülatif tavanıdır; gerçek portföyün bağlayıcı dönüşüm sınırı değildir.
- Python yüzdesi Quasar oranıyla çarpılmaz, `min(...)` ile sınırlandırılmaz veya otomatik uygulanmaz.
- `public.user_investment_settings.btc_eth_conversion_pct` ve `ura_usd_conversion_pct` bugün kullanıcıya ait varsayılan/hesaplama yüzdeleridir; hard limit değildir.

### Signal→Conversion hedefi — `APPROVED`, henüz uygulanmadı

- Python global sinyal, yön, güç/kalite bilgileri ve `action_size` önerisini yayımlar; Quasar veya portföy verisine bağımlı olmaz.
- Dönüşüm formunda sinyal bağı isteğe bağlıdır. Kullanıcı ID yazmaz; `AppPopupSelect` üzerinden uygun global karar listesinden seçim yapar.
- Seçim `portfolio_transactions.decision_id` alanına kaydedilir ve “hangi sinyale istinaden işlem yapıldı?” raporlamasını sağlar.
- Aynı global karar, farklı `account_id` işlemlerine bağlanabilir; bir portföyde işlem yapılması diğer portföyü veya Python sinyalini etkilemez.
- Sinyal seçildiğinde `action_size` başlangıç oranı olarak otomatik getirilebilir. Kullanıcı oranı/miktarı kendi riskine göre değiştirebilir; model yüzdesi hard-coded uygulanmaz.
- Quasar sinyal göstergeleri karar zorlayıcısı değildir; yalnız öngörü, hesaplama ve audit desteğidir.
- Gerçek adet seçili hesabın işlem anındaki kaynak bakiyesi üzerinden Quasar'da hesaplanır ve kullanıcı özeti/onayıyla kaydedilir.

### Görev takvimi sonrasına bırakılan sizing işi — `OPEN`

- `max_regime_pct` AppSettings içinde vardır fakat v1.2.0 ayar penceresinde düzenlenebilir alan değildir.
- Bu tavanın Python ayar penceresine eklenip eklenmeyeceği ve action-size formülünde sinyal gücü/kalitesinin tam olarak nasıl ölçekleneceği ayrıca kararlaştırılır.
- Bu değişiklik Quasar portföy limiti yaratmaz; model öneri otoritesini etkilediği için yeni model version/test/Shadow Epoch gerektirebilir.

## 16. Historical replay ve calibration — doğru yorum

### 16.1 Kod etiketi

DB ve kod validation type:

```text
PIT_CORE_REPLAY / ETH/BTC
```

### 16.2 Gerçek kapsam — `RELEASED`

- DB backfill varsayılan olarak `2500` takvim günlük BTC/ETH geçmişi ister.
- Replay ilk noktayı en az `1120` ortak günlük session prefix'i biriktikten sonra
  üretir; doğrulanmış son çalışmada bu yapı `1381` replay observation vermiştir.
- Her tarih için BTC/ETH fiyat prefix'i yalnız o tarihe kadar kesilir.
- Makroda `observation_date <= as_of` olan son satır seçilir.
- Historical derivatives/event factor q0 ile dışarıda bırakılır.
- Değer/trend/momentum/flow/macro directional core yeniden hesaplanır.

Replay selector'daki varsayılan `5-session cooldown`, production
`regime_reset_days=5` ile aynı mekanizma değildir. Replay production K1/K2,
reset/reversal state'ini çalıştırmaz; bu iki `5` değeri birbirinin kanıtı veya
eşdeğeri olarak yorumlanmamalıdır.

### 16.3 Strict PIT değildir — `OPEN`

- FRED revision/vintage history (`realtime_start/realtime_end`) gerçek yayın anına göre replay edilmez.
- Derivatives/event PIT history yoktur.
- Bu nedenle “production ACTION backtest” veya “strict PIT” denemez.
- Doğru yorum: **historical as-of directional-core replay**.

### 16.4 Replay selector production parity değildir

Mevcut selector:

- edge threshold'u geçer,
- late-entry değildir,
- signed direction sıfır değildir,
- varsayılan 5-session cooldown uygular.

Ancak production:

- data-quality kapısını,
- confidence kapısını,
- event veto sırasını,
- status önceliğini,
- persistent K1/K2/reversal/reset state'ini

birebir replay etmez.

### 16.5 Calibration gerçek walk-forward değildir

v1.2.0:

- aday threshold: `50,55,60,65,70,75,80`
- tek chronological split: `%70 train / %30 holdout`
- primary horizon: `20 seans`
- eligibility: train `>=8`, holdout `>=3` sinyal
- settings'e auto-apply yok

Bu, expanding/rolling çok-fold walk-forward değil; exploratory train/holdout raporudur.

### 16.6 URA replay

URA holdings, breadth ve event point-in-time history yeterli olmadan `PIT_FULL_REPLAY / URA/USD = NOT_READY` kalır. Bugünkü holdings'i geçmişe taşıyıp sahte sonuç üretmek yasaktır.

## 17. Monthly realized audit — `RELEASED`

- Gerçek kaydedilmiş `ACTION` ve `WATCH` kararlarını 5/20/60 trading-session horizonlarında değerlendirir.
- Direction-adjusted return ve hit bilgisini `model.performance`a yazar.
- Full PIT backtest değildir.
- Weight/threshold/mode değiştirmez.

## 18. Shadow Readiness — `RELEASED`

Kriterler:

```text
Shadow calendar days       >= 30
ETH/BTC decision days      >= 25
URA/USD decision days      >= 20
Median data quality        >= 80
Recent job success         >= 98%
Realtime smoke age         <= 7 gün
URA holdings dates         >= 2
URA breadth dates          >= 20
```

- `NOT_READY`: süre/history birikmedi.
- `BLOCKED`: waiting tamamlandı fakat health/quality/realtime blocker var.
- `READY`: manuel LIVE review yapılabilir; otomatik geçiş değildir.

### Runtime config uyarısı

Migration 0007 bu kriterleri `model.parameters`a seed eder. Fakat v1.2.0 `classify_shadow_readiness()` bu tablodan okumaz; hard-coded defaults kullanır. DB kayıtları bugün runtime source of truth değildir. Bu `OPEN` observability/config-authority işidir.

### Bilinen readiness açıkları — `OPEN`

- Açık `shadow_epoch_id`/`shadow_started_at` yok.
- Manual/backfill/development run-kind ayrımı yok.
- Beklenen scheduler run sayısı gerçek run sayısıyla karşılaştırılmıyor.
- `OK`, `DEGRADED`, `SKIPPED` completed/healthy ayrımı yeterince açık değil.
- OK rate ve completed rate ayrıştırılmıyor.

## 19. Supabase tablo sözleşmesi

### Ham/girdi

- `market.daily_prices`
- `market.derivatives_snapshots`
- `market.execution_snapshots`
- `macro.observations`
- `fundamentals.ura_holdings`
- `fundamentals.ura_breadth`
- `events.events`

### Model/audit

- `model.features`
- `model.regimes`
- `model.factor_scores`
- `model.decisions`
- `model.signal_state`
- `model.performance`
- `model.validation_runs`
- `model.parameters`
- `model.factor_weights` — şemada mevcut, runtime weight source değil
- `system.job_runs`
- `system.data_sources`

### Public/read-only motor yüzeyi

- `public.market_snapshot`
- `public.decision_snapshot`
- `public.decision_history`
- `public.engine_health_snapshot`
- `public.model_validation_snapshot`

Quasar `public` snapshot'ları gösterir; private factor/model tablolarını değiştirmez.

### 19.1 Veri yaşam döngüsü ve FRED tekilleştirme sözleşmesi

#### Bugünkü durum — `RELEASED`

- Supabase motor tablolarında yaşa göre çalışan otomatik retention/cleanup görevi
  yoktur.
- K1/K2 reseti veri temizliği değildir; yalnız `model.signal_state` alanlarını
  sıfırlar.
- `macro_job` günde dört kez çalışır; sekiz serinin her biri için collector son
  `1500` observation'ı yeniden ister. Çağrı real-time period'i açıkça sabitlemez.
- `macro.observations` benzersizlik anahtarı `series_id`, `observation_date` ve
  `realtime_start` birleşimidir. FRED'in varsayılan `realtime_start` değeri sorgu
  günüyle ilerlediğinde aynı ekonomik değer ertesi gün yeni satır olur.
- 29–30.07.2026 gerçek örneğinde `14.513` satırın `4.343`ü aynı
  seri/tarih/değer tekrarıdır; karşılaştırılabilen ortak satırlarda gerçek değer
  değişikliği yoktur. Günlük `realtime_start` bu veri akışında revision kanıtı
  değildir.
- Mevcut latest/replay okumaları bu günlük kopyaları versioned revision kaynağı
  olarak deterministik biçimde seçen tam bir vintage-PIT sözleşmesi sağlamaz.

#### Görev takvimi sonrası hedef — `APPROVED`

1. Current katmanda `(series_id, observation_date)` başına tek değer bulunur. Aynı
   değer yeniden geldiyse yalnız son görülme/fetch metadata'sı ilerler.
2. Değer değiştiğinde önceki/yeni değer, sıralı revision numarası ve motorun değişimi
   ilk gördüğü zaman append-only change-point olarak yazılır. Current güncellemesi ve
   revision insert'i tek transaction içinde idempotent olmalıdır.
3. `unique(series_id, observation_date, value)` nihai çözüm değildir; A→B→A geçişinde
   son A olayını ilk A ile çakıştırır. Yalnız `unique(series_id, observation_date)`
   kullanıp geçmişi ezmek de yasaktır.
4. Latest/factor okuyucuları current katmanını deterministik okur. Historical PIT
   okuyucuları revision/vintage katmanını `known_at <= as_of` kuralıyla okur.
5. Günlük polling change-point'i resmî FRED vintage yayın zamanı sayılmaz. Strict
   vintage PIT için ayrı ALFRED/FRED vintage endpoint backfill'i ve provenance
   gerekir.
6. Her `macro_job`, seri bazında `received/inserted/unchanged/revised/skipped`
   sayılarını ve beklenen sekiz serideki eksikleri audit'e yazar. Bir serinin boş
   dönmesi diğer serilerin başarılı upsert'i içinde görünmez hale gelmez.
7. Sinyal penceresinden çıkmış olsa da portföy ledger'ı, `model.decisions`, bağlı
   `public.decision_history`, performance/validation, fiyat geçmişi ve gerekli
   macro/URA PIT kanıtı otomatik silinmez.
8. Tekrar eden ya da kalıcı günlük/aylık özeti üretildikten sonra ham ayrıntısı
   gereksizleşen derivatives, execution-test ve `system.job_runs` kayıtları tablo
   bazlı retention/aggregation adayıdır.
9. Cleanup işlemi Shadow gününü, K1/K2 state'ini, karar–işlem `decision_id` bağını,
   maliyet/KZ replay'ini veya kullanıcı portföyünü sıfırlamayacaktır.

Kesin current/revision tablo tasarımı, retention süreleri, günlük/aylık özet şeması,
batch boyutu, dry-run/ölçüm raporu ve rollback yaklaşımı `OPEN`dır. Görev 7 öncesinde
runtime yazma/silme davranışı değiştirilmez. Uygulama yeni numaralı migration,
repository transaction/idempotency testleri, mevcut kopyalarda
`lag(value)`/sıralı-geçiş dry-run'ı, kontrollü backfill/dedup ve kapasite
karşılaştırmasıyla yapılacaktır.

## 20. Shadow görevlerinden sonraki değişiklik kapısı

### Görev 1–3

Scheduler/provider/freshness/snapshot/health sapması düzeltilebilir. Model davranışı değiştirilmez.

### Görev 4 sonrası — v1.2.x hardening

- Shadow epoch
- run kind
- expected/actual run
- OK/completed rate
- decision bucket diagnostics
- mevcut K1/K2 davranışını karakterize eden unit testler
- runtime config source görünürlüğü

Bunlar davranışı değiştirmeden yapılırsa v1.2.x olabilir.

### Görev 5–6 sonrası

- gerçek expanding/rolling walk-forward
- strict FRED-vintage PIT
- production/replay gap report
- URA factor quality decomposition

### Görev 7 sonrası veri hardening

- FRED current/revision tekilleştirme ve kontrollü mevcut-veri dedup
- tablo bazlı retention/aggregation matrisi
- dry-run ile silinecek/korunacak satır ve kapasite raporu
- portföy/decision/PIT audit bütünlüğü ve idempotency testleri

### Model davranışı değişirse

Factor formülü/ağırlığı, threshold, status gate, K1/K2, reversal, cooldown, action-size otoritesi veya production/replay state parity değişirse:

1. kullanıcı onayı,
2. yeni model version,
3. migration/provenance ihtiyacı,
4. test matrisi,
5. yeni deployment,
6. yeni Shadow Epoch

gerekir. Eski Shadow kanıtı otomatik devredilmez.

## 21. v1.3 adayı — `PROPOSED`, uygulanmış değil

1. Production ve replay tek versioned state machine kullanır.
2. Her kademe arasında en az 5 karar seansı bulunur.
3. Reversal iki ardışık qualified karşı-yön kapanışı ister.
4. Event/state olayları idempotent olur.
5. Restart, reversal, reset ve parity unit testleri yazılır.
6. `max_regime_pct` ayar yüzeyi ve action-size strength/quality formülü kanıtla kesinleştirilir.
7. Reset sonrası aynı yön K1 davranışında farklı `as_of`, veri örtüşmesi ve idempotency karakterize edilir; zorunlu ters yön kuralı varsayılmaz.

Bu liste v1.2.0 gerçeği değildir.

## 22. Zorunlu test matrisi

- Quality `79.99 / 80.00`
- Edge `69.99 / 70.00`
- Confidence `69.99 / 70.00`
- q0 factor'un edge/data-quality etkisi
- score=0 factor'un agreement'a katılmaması
- quality → event → late-entry → action önceliği
- K1/K2, küçük recommended size ve Python model önerisi için `%50` cumulative cap
- aynı as_of tekrarının event üretmemesi
- 5 zayıf karar sonrası reset
- karşı yön immediate reversal karakterizasyonu
- restart sonrası state korunması
- replay/production farkı
- Shadow epoch ve job-kind
- expected/actual scheduler run

Mevcut `scripts/release_check.py` marker/sözleşme kontrolleridir; bu davranışların tamamını test eden unit-test paketi olduğu anlamına gelmez.

## 23. Kaynak gerçekleri

Bu sözleşme aşağıdaki yayımlanmış kaynaklarla uyumlu tutulur:

- `app/engine.py`
- `app/features/builders.py`
- `app/engines/factors.py`
- `app/engines/regime.py`
- `app/engines/decision.py`
- `app/engines/veto.py`
- `app/engines/risk.py`
- `app/engines/signal_state.py`
- `app/engines/ura.py`
- `app/backtest/validation.py`
- `config/defaults.json`
- `migrations/0001_schema.sql`
- `migrations/0003_mobile_api.sql`
- `migrations/0007_v1_2_model_validation.sql`

Kod ile belge çelişirse önce çelişki raporlanır; kullanıcı kararı olmadan kod veya belge sessizce doğru kabul edilmez.
