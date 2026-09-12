# Post-Shadow Araştırma Görev Borcu — Options Open Interest / Max Pain

Durum: **OPEN / RESEARCH ONLY**  
Tarih: 12 Eylül 2026  
Kapsam: BTC, ETH ve URA sinyal motorunda options open interest (OI), option positioning ve max pain verisinin kullanılabilirliğinin araştırılması.

## 1. Amaç

Bu görev borcu herhangi bir released model davranışını değiştirmez. Amaç aşağıdaki soruları kanıta dayalı biçimde cevaplayan teknik/istatistiksel bir araştırma raporu üretmektir:

1. Options open interest ve max pain verisi motor için gerçekten ek bilgi taşıyor mu?
2. BTC/ETH rotasyon sistemi ile URA/USD sistemi için aynı veri aynı şekilde mi kullanılmalı?
3. Bu veri yön, dip/tavan, support/resistance benzeri seviye ve expiry pinning değerlendirmelerine hangi ölçüde katkı sağlayabilir?
4. Max pain bağımsız fiyat hedefi olarak mı, yoksa yalnız positioning/expiry-context metriği olarak mı ele alınmalı?
5. Mevcut derivatives factor içine alt-bileşen olarak mı eklenmeli, ayrı factor mı olmalı?
6. Kullanılması halinde ağırlığı ne olmalı ve hangi piyasa rejimlerinde aktif olmalı?
7. Hangi veri kalitesi, likidite, expiry distance ve freshness şartlarında skor üretmesine izin verilmeli?
8. Veri sağlayıcı kesintilerinde fallback semantiği ne olmalı?
9. Historical point-in-time (PIT) veri olmadan geriye dönük doğrulama yapılabilir mi; yapılamıyorsa forward-only evidence nasıl toplanmalı?
10. Mevcut LIVE NO-GO durumunda bu çalışma model geliştirme borcu mu, yoksa yalnız research/observability borcu mu kalmalı?

## 2. Mevcut sistem gerçeği

### 2.1 BTC/ETH derivatives altyapısı zaten var

Mevcut `market.derivatives_snapshots` tablosu aşağıdaki alanları zaten saklar:

- perpetual open_interest
- funding_8h
- current_funding
- basis_pct
- option_open_interest
- option_volume_24h
- option_mark_iv_mean

`DeribitCollector` BTC ve ETH için option chain book summary verisini toplar ve toplam option OI, 24h option volume ve ortalama mark IV üretir.

Ancak güncel `score_derivatives()` option alanlarını **kullanmamaktadır**. Mevcut derivatives skoru esas olarak:

- ETH-BTC funding farkı,
- ETH-BTC basis farkı,
- ETH/BTC perpetual OI USD ratio,
- crowding penalty

ile oluşur.

Dolayısıyla seçenek piyasası verisi tamamen yeni bir veri ailesi değildir; bir kısmı halihazırda ingest edilmekte fakat scoring'de kullanılmamaktadır.

### 2.2 Max pain şu anda toplanmıyor

Mevcut Deribit collector aggregate option OI/volume/mean IV toplar. Max pain hesaplamak için ise en azından expiry + strike + call/put + OI seviyesinde chain snapshot gerekir.

Aggregate `option_open_interest` tek başına max pain hesaplamak için yeterli değildir.

### 2.3 Provider farkı

- Deribit yolu option özetleri sağlayabilir.
- OKX fallback collector şu anda option alanlarını `None` bırakır ve yalnız swap/perpetual veri üretir.

Bu nedenle options skorunun provider-independent gibi davranması doğru değildir. Research sırasında option data availability ayrıca quality/freshness bileşeni olarak ele alınmalıdır.

### 2.4 Released factor ağırlıkları

ETH/BTC sisteminde mevcut `derivatives` factor weight rejime göre yaklaşık `%18-%23` aralığındadır.

Bu araştırma hiçbir released factor weight'i otomatik değiştirmeyecektir.

URA/USD sisteminde ayrı `derivatives` factor yoktur. URA options verisi kullanılacaksa yeni bir positioning/options factor gerekip gerekmediği ayrıca kanıtlanmalıdır.

## 3. Ön hipotezler

Bunlar araştırma sonucu değildir; test edilecek hipotezlerdir.

### H1 — Option OI seviyesi değil, değişimi ve dağılımı daha değerlidir

Salt toplam OI tek başına yön vermeyebilir. Daha anlamlı adaylar:

- call OI / put OI oranı,
- call OI change / put OI change,
- expiry bazında OI concentration,
- spot'a yakın OI yoğunluğu,
- üst taraftaki dominant call wall,
- alt taraftaki dominant put wall,
- spot-to-wall normalized distance,
- near-expiry OI concentration,
- OI change ile spot return birlikte değerlendirmesi.

### H2 — Max pain doğrudan fiyat hedefi olmamalıdır

Max pain, mevcut OI dağılımından türetilen mekanik bir expiry payout minimization seviyesidir. Tek başına:

- dip,
- tavan,
- support,
- resistance,
- kesin yön

olarak kabul edilmemelidir.

En olası yararlı rolü:

- expiry yaklaşırken positioning reference,
- pinning/magnet riski,
- spot ile max-pain mesafesinin normalize edilmesi,
- price move'un OI concentration yönüne doğru mu yoksa ondan uzağa mı olduğunu sınıflandırma,
- geç giriş / crowding / short-horizon risk context

olabilir.

### H3 — Expiry distance kritik olmalıdır

Max pain ve strike OI yoğunluğu etkisi tüm vadelerde eşit varsayılmamalıdır.

Araştırılması gereken DTE bucket'ları:

- 0-2 gün,
- 3-7 gün,
- 8-14 gün,
- 15-30 gün,
- 30+ gün.

Max pain'in candidate etkisinin özellikle 0-7 DTE aralığında test edilmesi gerekir.

### H4 — BTC/ETH için relative options positioning daha değerlidir

ETH/BTC sistemi mutlak BTC veya mutlak ETH yönü değil, relatif üstünlük üretir. Bu nedenle aday features:

- ETH/BTC option OI growth ratio,
- ETH/BTC call-put OI imbalance farkı,
- ETH/BTC near-expiry OI concentration farkı,
- ETH ve BTC'nin spot-to-max-pain normalized distance farkı,
- ETH/BTC IV skew farkı,
- ETH/BTC option volume/OI turnover farkı

şeklinde relatif kurulmalıdır.

### H5 — URA için liquidity gate zorunludur

URA ETF options zinciri teknik olarak bulunabilir olsa da BTC/ETH crypto options kadar derin olmayabilir. URA positioning factor üretilmeden önce:

- minimum toplam OI,
- minimum option volume,
- minimum strike count,
- minimum expiry count,
- spread/quote quality,
- stale-chain kontrolü

şartları tanımlanmalıdır.

## 4. Araştırılacak feature adayları

### 4.1 OI positioning

- `option_call_oi_total`
- `option_put_oi_total`
- `option_put_call_oi_ratio`
- `option_call_oi_change_1d`
- `option_put_oi_change_1d`
- `option_total_oi_change_1d`
- `option_oi_turnover = volume / OI`
- `option_front_expiry_oi_share`
- `option_near_spot_oi_share`

### 4.2 Strike concentration / walls

- dominant call OI strike
- dominant put OI strike
- call wall distance %
- put wall distance %
- wall asymmetry
- OI-weighted strike center
- OI concentration / entropy

### 4.3 Max pain

Her expiry için ayrı hesaplanmalı:

- max pain strike
- spot to max pain distance %
- distance / ATR
- distance / implied move
- max-pain shift 1d / 3d
- expiry DTE
- expiry OI weight

Expiry'leri tek bir "global max pain" sayısına kör biçimde birleştirmemek tercih edilir.

### 4.4 IV / skew tamamlayıcıları

Mevcut `option_mark_iv_mean` fazla kaba olabilir. Araştırma raporu mümkünse şu adayları da değerlendirmelidir:

- ATM IV,
- 25d put IV - 25d call IV skew,
- short-dated vs longer-dated IV term structure,
- realized vol / implied vol spread,
- ETH-BTC IV/skew differential.

## 5. Yön / dip / tavan katkısı nasıl değerlendirilmeli?

### Yön

OI verisi tek başına yön göstergesi sayılmamalıdır. Directional candidate ancak şu kombinasyonlarla test edilmelidir:

- OI change + price change,
- put/call imbalance + IV skew,
- wall asymmetry + trend/momentum,
- relative BTC/ETH positioning.

### Dip / tavan

Max pain "dip" veya "tavan" değildir. Dominant put/call OI strikes potansiyel positioning/liquidity zones olarak incelenebilir ancak support/resistance etiketi yalnız forward evidence ile verilebilir.

Araştırma şu olayları ayrı ölçmelidir:

- spot wall'a yaklaşınca rejection oranı,
- wall kırılınca continuation oranı,
- max pain'e yaklaşma/uzaklaşma olasılığı,
- expiry günlerinde pinning oranı,
- expiry sonrası level etkisinin kaybolma hızı.

## 6. Ağırlık araştırma çerçevesi

### 6.1 Production için şimdiki karar

**Şimdilik ağırlık değişikliği YOK.**

Released `derivatives` factor zaten ETH/BTC edge içinde `%18-%23` ağırlığa sahiptir. Options verisi için doğrudan yeni `%X` production weight atanmayacaktır.

### 6.2 Research-only aday aralıklar

Evidence üretmek için başlangıç grid'i:

#### ETH/BTC — mevcut derivatives factor içi alt-bileşen

- perpetual funding/basis/OI: `%60-%80`
- options positioning/OI/skew: `%20-%40`
- max pain bileşeni: derivatives factor içinde en fazla `%5-%10`

Bu durumda max pain'in toplam edge üzerindeki teorik etkisi released derivatives weight'e göre yaklaşık `%0.9-%2.3` efektif bandı geçmemelidir.

Options positioning'in toplam edge üzerindeki efektif araştırma bandı yaklaşık `%3.6-%9.2` olabilir.

Bunlar production önerisi değil, sensitivity/backtest grid sınırlarıdır.

#### URA/USD — yeni positioning/options factor adayı

İlk araştırma grid'i toplam model ağırlığında `%0 / %2.5 / %5 / %7.5 / %10` olabilir.

`%0` baseline mutlaka korunmalıdır. URA options factor ancak OOS/PIT kanıtı baseline'a göre katkı gösterirse consideration aşamasına geçmelidir.

## 7. Veri mimarisi araştırma borcu

### 7.1 BTC/ETH

Max pain için aggregate snapshot yeterli değildir. Research tasarımı aşağıdaki seçenekleri karşılaştırmalıdır:

A. Raw chain snapshot tablosu
- provider
- observed_at
- underlying
- expiry
- strike
- option_type
- open_interest
- volume
- mark_iv
- mark_price
- bid/ask
- raw/provenance

B. Raw source bytes/json immutable snapshot + derived chain rows

PIT/replay açısından B seçeneği daha güçlüdür.

### 7.2 URA

URA için data source araştırması yapılmalıdır:

- Cboe delayed chain,
- lisans/API koşulları,
- ücretsiz/ücretli veri alternatifleri,
- historical PIT erişimi,
- rate limits,
- redistribution şartları,
- chain completeness.

Scraping'e dayalı kırılgan kaynak production source olarak kabul edilmemelidir.

## 8. Quality modeli

Options feature quality yalnız "API çalıştı" şeklinde olmamalıdır.

Candidate quality bileşenleri:

- freshness,
- chain completeness,
- expiry coverage,
- strike coverage,
- total OI,
- volume/OI turnover,
- bid/ask availability,
- provider provenance,
- stale OI publication timing,
- BTC/ETH aynı provider şartı.

Quality düşükse feature score neutral + low-quality olmalı; ağırlık otomatik normalize edilse bile data-quality gate etkisi açıkça audit edilmelidir.

## 9. Backtest / validation planı

Araştırma raporu en az üç baseline kıyaslamalıdır:

1. released model (options yok),
2. derivatives + options OI/skew, max pain yok,
3. derivatives + options OI/skew + max pain context.

Horizonlar:

- 1d,
- 3d,
- 5d,
- 10d,
- 20d,
- expiry close,
- expiry +1/+3 gün.

Ölçümler:

- direction hit rate,
- signed return,
- max adverse excursion,
- max favorable excursion,
- false reversal rate,
- WATCH→ACTION precision,
- late-entry reduction,
- signal count / signal starvation etkisi,
- regime bazlı katkı,
- provider bazlı stability.

Walk-forward / OOS kanıt olmadan factor-weight değişikliği önerilmemelidir.

## 10. Raporun cevaplaması gereken ek sorular

- OI level mi, OI change mi daha faydalı?
- Put/call OI ratio direction için gerçekten faydalı mı, yoksa crowding contrarian göstergesi mi?
- Max pain yalnız expiry haftasında mı anlamlı?
- Nearest-expiry ile monthly expiry birbirinden ayrılmalı mı?
- Crypto 24/7 market ile US ETF options market-hours farkı nasıl normalize edilmeli?
- Weekend BTC/ETH fiyat hareketinde son option chain ne kadar stale kabul edilmeli?
- Option expiry UTC settlement zamanı engine market-date semantiğine nasıl bağlanmalı?
- BTC ve ETH option OI contract unit / USD notional normalize edilmeli mi?
- Deribit option chain ile OKX fallback arasındaki feature parity nasıl korunmalı?
- Options feature yoksa mevcut derivatives factor davranışı aynen kalmalı mı?
- Provider değişiminde score discontinuity oluşuyor mu?
- Max pain shift, spot hareketinden sonra mekanik olarak mı değişiyor; look-ahead/response leakage riski var mı?
- OI'nin settlement sonrası publication delay'i PIT backtest'te nasıl modellenmeli?
- Dealer gamma exposure hesaplanacaksa dealer long/short sign varsayımı ne kadar güvenilir?
- Gamma wall / zero-gamma gibi metrikler max pain'den daha faydalı olabilir mi?
- OI wall seviyeleri ATR/IV ile normalize edildiğinde daha stabil mi?
- URA option liquidity zayıf günlerde feature tamamen kapatılmalı mı?
- SEC/event günlerinde options flow ayrı risk context sağlayabilir mi?

## 11. Karar kapıları

### Gate A — Veri erişimi

- BTC/ETH strike-expiry chain güvenilir şekilde alınabiliyor mu?
- URA chain için yasal/stabil source var mı?
- Historical/PIT veri yeterli mi?

### Gate B — Feature validity

- Feature aynı snapshot'tan deterministik yeniden üretilebiliyor mu?
- Provider normalization testleri var mı?
- Missing/stale data semantics açık mı?

### Gate C — Evidence

- Baseline'a karşı OOS iyileşme var mı?
- Signal count aşırı artıyor veya azalıyor mu?
- Sonuç tek expiry/provider/regime'e bağımlı mı?

### Gate D — Model change

Yalnız Gate A/B/C geçerse:

- yeni factor mı,
- mevcut derivatives alt-score'u mu,
- ağırlık ne olmalı,
- model version bump gerekir mi,
- yeni Shadow Epoch gerekir mi

ayrı kullanıcı onayına sunulur.

## 12. Şimdiki karar

```text
Research debt                        OPEN
Released model change                NONE
factor_weights change                NONE
threshold change                     NONE
K1/K2/reset/reversal change          NONE
scheduler change                     NONE
SHADOW/LIVE mode change              NONE
model version change                 NONE
```

Ön değerlendirme:

- BTC/ETH options OI: **yüksek araştırma değeri**, mevcut derivatives factor'a doğal aday.
- BTC/ETH max pain: **düşük-orta bağımsız tahmin değeri**, expiry-context olarak araştırılmalı.
- URA options OI/max pain: **teknik olarak uygulanabilir**, ancak liquidity/source/PIT kalitesi kanıtlanmadan factor yapılmamalı.
- Dip/tavan tayini: **tek başına uygun değil**; wall/expiry context olarak test edilmeli.
- Production weight: **şimdilik 0 yeni ağırlık**.

## 13. Beklenen deliverable

Görev tamamlandığında ayrı bir araştırma raporu aşağıdakileri içermelidir:

1. kaynak ve lisans matrisi,
2. mevcut repo/schema gap analizi,
3. önerilen raw/PIT veri modeli,
4. feature formülleri,
5. quality/freshness kuralları,
6. BTC/ETH ve URA ayrı uygulama kararı,
7. backtest/walk-forward sonuçları,
8. max pain predictive value testi,
9. OI wall/direction/dip-tavan katkı testi,
10. sensitivity weight grid sonuçları,
11. GO / NO-GO / RESEARCH-FURTHER kararı,
12. production model değişecekse model-version + Shadow Epoch planı.

Bu rapor tamamlanmadan released model ağırlığı veya scoring formülü değiştirilmeyecektir.
