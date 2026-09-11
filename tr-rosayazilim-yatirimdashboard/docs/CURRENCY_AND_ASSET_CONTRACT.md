# Para Birimi ve Varlık Sözleşmesi

Status: **APPROVED / IMPLEMENTATION IN PROGRESS**  
Tarih: **11 Eylül 2026**

## Amaç

Quasar portföy tarafında işlem para birimi, tarihsel maliyet ve güncel görüntüleme para birimi kavramlarını birbirinden ayırmak; USD'yi zorunlu ana muhasebe para birimi gibi kullanmadan işlem anındaki gerçek varlık/miktar bilgisini korumak.

Bu sözleşme Python Investment Engine model davranışını değiştirmez.

## Varlık sınıfları

### Yatırım varlıkları

- BTC
- ETH
- URA

### Settlement / ödeme varlıkları

- USD
- TRY
- USDT
- USDC

Settlement varlıkları:

- `CASH_IN` hedefi,
- `CASH_OUT` kaynağı,
- `BUY` kaynağı,
- `SELL/EXIT` hedefi,
- `CONVERSION` kaynağı veya hedefi

olarak kullanılabilir.

## Display Currency

Güncel UI değerlemesinde desteklenen görüntüleme birimleri:

- USD
- TRY
- EUR
- BTC
- ETH
- USDT
- USDC

USDT/USD ve USDC/USD için önce provider quote'u kullanılır. Provider geçici olarak yoksa yalnız UI/display değerinin sıfıra düşmemesi için 1 USD peg fallback uygulanabilir. Bu fallback transaction verisine veya maliyet bazına yazılmaz.

## Tarihsel işlem sözleşmesi

Bir transaction'da aşağıdaki kavramlar farklı anlam taşır:

- `source_asset` / `target_asset`: gerçek işlem bacakları,
- `source_quantity` / `target_quantity`: gerçek hesap miktarları,
- `price_currency`: işlemin girildiği settlement para birimi,
- `usd_try`: işlem anındaki USD/TRY,
- `gross_usd`, `fee_usd`, `net_usd`: işlem anında üretilmiş USD eşdeğerleri.

USD eşdeğerleri audit ve ortak karşılaştırma için korunur. Bunların saklanması USD'nin ana muhasebe para birimi olduğu anlamına gelmez.

## Güncel değerleme ile tarihsel değer ayrımı

Güncel portföy değeri current market/display quote ile hesaplanabilir.

Tarihsel işlem tutarı, sermaye girişi/çıkışı ve maliyet bilgisi current FX ile yeniden yazılmaz. Bir sonraki implementation aşaması ledger'da bu ayrımı USD ve TRY tarihsel basis olarak açık biçimde uygulayacaktır.

## Python servis sınırı

Bu çalışma kapsamında aşağıdaki service-owned yüzeylerin şeması veya yazma sözleşmesi değiştirilmez:

- `public.market_snapshot`
- `public.decision_snapshot`
- `public.decision_history`
- `public.engine_health_snapshot`
- `market.*`
- `macro.*`
- `model.*`
- `system.job_runs`

`0016_portfolio_stablecoin_assets.sql` yalnız Quasar'ın append-only portföy tablosundaki `price_currency` check constraint'ini `USDT/USDC` kabul edecek şekilde genişletir.

## Uygulama sırası

1. Display quote ve asset taxonomy.
2. DB `price_currency` contract genişletmesi.
3. USDT/USDC transaction form akışları.
4. Historical/current formatter ayrımı.
5. Dual historical basis (USD + TRY) ledger revizyonu.
6. Transactions / Reports / Portfolio / Dashboard uyarlaması.
7. Regression ve gerçek Supabase doğrulaması.
