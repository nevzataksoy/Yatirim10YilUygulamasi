# Quasar Display Quote Architecture

Status: **APPROVED / IMPLEMENTED**  
Tarih: **23 Ağustos 2026**

## Amaç

Quasar/Capacitor uygulamasındaki görüntüleme para birimi ve güncel portföy değerlemesini Python Investment Engine'in günlük `market_snapshot` fiyatlarından ayırmak.

Bu katman yalnız UI/display değerlemesidir. Python sinyal motoru, backtest, historical cost basis, gerçekleşmiş K/Z, işlem tarihindeki FX ve audit kayıtları bu fiyatları kullanmaz.

## Canonical quote seti

Uygulama aşağıdaki beş canonical değeri tutar:

- `BTC_USD`
- `ETH_USD`
- `URA_USD`
- `USD_TRY`
- `EUR_USD`

Display seçenekleri:

- USD
- TRY
- EUR
- BTC
- ETH

Bütün portföy değeri önce USD'ye normalize edilir. Display dönüşümleri bu canonical quote setinden yapılır.

## Provider zinciri

### BTC/USD ve ETH/USD

1. Coinbase public Spot API
2. `market_snapshot`
3. cihazdaki son başarılı cache

### USD/TRY ve EUR/USD

1. Coinbase public Exchange Rates API
2. Yahoo Finance chart endpoint
3. Frankfurter v2, `providers=TCMB`
4. Fawaz Ahmed Currency API (jsDelivr, ardından Cloudflare fallback)
5. `market_snapshot` (`USD_TRY` için)
6. cihazdaki son başarılı cache

Frankfurter ve Fawaz günlük referans verisidir; canlı provider gibi etiketlenmez.

### URA/USD

1. Yahoo Finance chart endpoint
2. `market_snapshot`
3. cihazdaki son başarılı cache

Yahoo Finance resmi developer API sözleşmesi olmadığı için provider abstraction arkasındadır ve uzun vadede değiştirilebilir kabul edilir.

## Mobil HTTP davranışı

Production hedefi Quasar + Capacitor mobil uygulamasıdır.

- Native ortamda `CapacitorHttp.get()` doğrudan kullanılır.
- Global `fetch`/XHR patch'i açılmaz.
- Browser tarafı yalnız geliştirme kolaylığı için `fetch` fallback'ine sahiptir.
- API key veya provider secret APK'ya gömülmez.

## Store ve servis sorumlulukları

`displayQuotes` Pinia store:

- normalized quote state,
- source/quality/timestamp metadata,
- stale kontrolü,
- device cache hydrate/persist,
- display conversion.

Provider dosyaları:

- endpoint bilgisi,
- response parsing,
- provider metadata.

`displayQuoteService`:

- provider fallback sırası,
- pair bazında bağımsız hata toleransı.

`displayQuoteScheduler`:

- BTC/ETH için 30 saniye,
- FX/URA için 60 saniye,
- tekil in-flight guard,
- recursive `setTimeout`,
- 1/2/5/15 dakika backoff,
- foreground'da anlık yenileme,
- background'da polling durdurma ve cache persist.

## Fallback semantiği

Daha düşük `fallbackLevel` daha kaliteli kaynaktır. Live/current provider başarısız olduğunda son iyi değer anında sıfırlanmaz.

Stale eşikleri:

- BTC/ETH: 2 dakika
- URA/FX: 5 dakika

Canlı/current veri stale hale gelirse `market_snapshot` daha düşük kaliteli olsa bile geçici fallback olarak devreye girebilir. Provider geri geldiğinde daha kaliteli quote tekrar öncelik kazanır.

## Python sınırı

Bu değişiklik Python tarafının:

- scheduler cadence,
- `market.daily_prices`,
- `market_snapshot` üretimi,
- TCMB/Coinbase/Alpha Vantage/FRED provider akışı,
- factor/threshold,
- K1/K2,
- signal/decision,
- Shadow readiness

davranışını değiştirmez.

`market_snapshot` korunur ve yalnız display katmanında fallback kaynağı olarak okunur.
