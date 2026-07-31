# Veri Kaynakları — v1.1.3

| Kaynak | Rol | Auth | Not |
|---|---|---|---|
| Coinbase Exchange | BTC/USD, ETH/USD günlük OHLCV + realtime execution observation | public | spot primary; realtime `level2_batch + matches` |
| Bitstamp | BTC/ETH spot fallback | public | BTC ve ETH birlikte provider değiştirir |
| Alpha Vantage | URA daily/weekly/monthly OHLCV | API key | pacing uygulanır |
| FRED | makro seriler | API key | latest-first + observation-date freshness |
| Deribit | derivatives primary candidate | public | AUTO modunda önce denenir |
| OKX | derivatives fallback | public | BTC/ETH USDT-SWAP OI/funding/mark/index |
| Global X | URA official full holdings CSV | public | fund sayfasından güncel dated CSV otomatik keşfedilir |
| SEC EDGAR | URA constituent filing monitor | public + declared User-Agent | exact ticker→CIK eşlemesi; severity uydurulmaz |
| TCMB | USD/TRY ForexSelling | public | günlük FX snapshot |

## Derivatives provider bütünlüğü

Aynı factor turunda BTC ve ETH aynı venue'dan gelmelidir. `auto`: tam Deribit çifti başarısızsa tam OKX çiftine geçer. Provider değişimi historical OI değişimi gibi yorumlanmamalıdır.

## Global X holdings kapsamı

Resmi holdings snapshot'ları `fundamentals.ura_holdings` tablosuna tarih bazlı saklanır. CSV'deki boş ticker cash/currency satırları constituent breadth'e dahil edilmez.

Bu veri URA ETF kompozisyonu ve price-adjusted AUM-flow proxy üretir; uranium spot/term fiyatı veya fiziksel arz-talep verisi değildir.

## SEC kapsamı

Global X ticker'ları örneğin `CCO CN` gibi exchange suffix içerebilir. v1.1.3 kesin olmayan cross-listing alias tahmini yapmaz; yalnız SEC ticker map'te exact eşleşen ticker'lar otomatik izlenir. Coverage health/details içinde görünür.

## Realtime

Realtime raw mesajları saklanmaz; yalnız türetilmiş execution metric snapshot'ları saklanır. Smoke test satırları `is_test=true` ile production action gözlemlerinden ayrılır.

Coinbase `matches` kanalı mesaj kaybı yaşayabildiğinden realtime worker trade_id sürekliliğini izler; tespit edilen eksik trade sayısı `trade_gap_count` olarak saklanır. Bu değer >0 ise trade imbalance metriği gözlemsel kabul edilmeli, tam tape olarak yorumlanmamalıdır.
