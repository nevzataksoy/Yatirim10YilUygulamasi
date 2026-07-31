# Açık Kalan Kapsam — v1.1.3 Sonrası

Bu dosya daha önce “sonraki turda ele alınacak” denilen konuların kaybolmaması için bilinçli açık kapsamı listeler. v1.1.3 bunları varmış gibi puanlamaz.

## 1. Uranium fiziksel fundamentals

**Durum:** Henüz production source yok.

v1.1.3 `fundamentals` factor slotunda Global X URA holdings/price-adjusted AUM-flow proxy kullanır. Bu ETF yatırımcı akışını temsil edebilir; uranium spot fiyatı, term contract fiyatı, utility contracting, mine production, inventory veya supply deficit değildir.

Sonraki aday kaynaklar ancak lisans/erişim ve point-in-time history uygunluğu doğrulandıktan sonra eklenmelidir. Kaynak yokken score/quality uydurulmaz.

## 2. Crypto event/news/on-chain/ETF-flow katmanı

**Durum:** `ETH/BTC event quality=0`.

Güvenilir point-in-time event/news sentiment veya doğrulanmış ETF/on-chain akış kaynağı seçilmeden model directional event oyu üretmez. Bir provider eklendiğinde aynı freshness/provenance kuralları uygulanmalıdır.

## 3. SEC filing semantic classification

**Durum:** Monitoring mevcut, direction sınıflandırması yok.

v1.1.3 SEC filing metadata'sını izleyebilir; ancak 8-K/10-Q gibi bir filing'in tek başına bullish/bearish olduğu varsayılmaz. İleride filing text parser + deterministic rule set veya versioned classifier eklenebilir. Audit için classifier version ve input provenance saklanmalıdır.

## 4. Full point-in-time model backtest / calibration

**Durum:** Monthly realized-performance audit mevcut; full historical replay yok.

`model.performance`, production/shadow kararlarının 5/20/60 session sonuçlarını ölçer. Bu, full historical point-in-time backtest değildir. Derivatives, macro, holdings, breadth ve event tarihçesi yeterli şekilde birikmeden geriye dönük full model backtest yapmak look-ahead/source-survivorship riski taşır.

Ağırlıklar otomatik değiştirilmez. Gelecekte calibration yapılırsa train/validation/test dönemleri ve model versioning zorunlu olmalıdır.

## 5. Realtime trade completeness

**Durum:** Execution observation mevcut; otomatik emir yok.

Coinbase `matches` trade stream'inde gap tespit edilirse `trade_gap_count` artar. v1.1.3 gap'i görünür kılar ancak REST ile eksik trade backfill yapmaz. Order-book Level2 metrikleri ayrı kalır. Trade imbalance, gap > 0 olduğunda tam tape olarak yorumlanmamalıdır.

## 6. Mobil Quasar + Capacitor

**Durum:** Supabase backend contract hazır; mobil uygulama bu release'in parçası değil.

Mobil istemci `public.*` authenticated/RLS yüzeyini kullanacak, DB/API secret'larını içermeyecektir. Engine smoke/shadow doğrulaması tamamlandıktan sonra ayrı geliştirme aşamasıdır.

## 7. Otomatik emir execution

**Durum:** Bilinçli olarak kapsam dışı.

`live` modu otomatik alım/satım emri göndermez. Realtime katmanı yalnız karar sonrası execution koşullarını gözlemlemek içindir. Broker/exchange order-routing ayrı güvenlik, idempotency, limit/permission ve risk projesi olarak ele alınmalıdır.

## v1.2.0 güncellemesi

- ETH/BTC için leakage-resistant **directional core PIT replay** ve exploratory threshold raporu eklendi.
- Full production model PIT backtest hâlâ tamamlanmış sayılmaz; derivatives/event tarihçesi yokken geçmiş ACTION simülasyonu yapılmaz.
- URA full PIT replay, holdings/breadth/event history birikene kadar `NOT_READY` kalır.
- Shadow readiness artık ölçülür ve LIVE için manuel gate oluşturur.
