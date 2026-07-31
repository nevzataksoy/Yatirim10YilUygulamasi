# Mobil Uygulama Backend Sözleşmesi

Planlanan istemci:

```text
Quasar + Capacitor
package id: tr.rosayazilim.yatirimdashboard
```

Bu dosya Python/Supabase tarafının mobil geliştirmeye hazır sözleşmesini tanımlar.

## İlk uygulama açılışı

Mobil uygulama yerel ayar ekranında yalnız:

- Supabase Project URL
- Supabase public/publishable key

ister.

Ardından Supabase Auth ile kullanıcı login/register akışı açılır.

**DB password, Telegram token, FRED/Alpha key veya service-role key mobil uygulamada bulunmaz.**

## Auth sonrası tablolar

### `public.profiles`
Kullanıcının isim alanları.

### `public.investment_accounts`
Kullanıcının portföy hesapları. Yeni Auth kullanıcısına otomatik `Ana Portföy` oluşturulur.

### `public.portfolio_transactions`
Tüm veri girişleri tek normalize transaction tablosunda tutulur.

Desteklenen tipler:

- `OPENING`
- `BUY`
- `SELL`
- `CONVERSION`
- `EXIT`
- `CASH_IN`
- `CASH_OUT`

Örnek BTC→ETH dönüşümü:

```json
{
  "transaction_type": "CONVERSION",
  "source_asset": "BTC",
  "target_asset": "ETH",
  "source_quantity": 0.01,
  "target_quantity": 0.31,
  "gross_usd": 680.00,
  "fee_usd": 0.68,
  "net_usd": 679.32
}
```

### `public.portfolio_positions`
Transaction legs üzerinden türetilmiş kullanıcı/account/asset miktar görünümü.

### `public.user_investment_settings`
Aylık bütçe, BTC/ETH/URA hedef oranları ve DCA günü.

### `public.decision_snapshot`
Windows Engine'in son BTC↔ETH / URA↔USD kararları. Authenticated read-only.

### `public.decision_history`
Engine tarafından üretilen karar geçmişi. Mobil uygulamada sinyal geçmişi/audit ekranı için authenticated read-only kullanılır. `portfolio_transactions.decision_id` ile gerçek dönüşüm işlemi ilgili karara bağlanabilir.

### `public.market_snapshot`
Engine referans fiyatları: BTC/USD, ETH/USD, ETH/BTC, URA/USD ve USD/TRY. Authenticated read-only.

### `public.engine_health_snapshot`
Engine sağlık bilgisi. Authenticated read-only.

## RLS

Kullanıcı portföy tablolarında yalnız kendi `user_id` verisine erişebilir. Client tarafından gönderilen `user_id` her insert/update'te `auth.uid()` ile doğrulanır.

## Mobilde önerilen veri akışı

```text
Supabase Auth
    ↓
Session
    ↓
investment_accounts
portfolio_transactions
user_investment_settings
    +
market_snapshot
decision_snapshot
decision_history
engine_health_snapshot
```

Bir sonraki aşamada Quasar projesi bu contract üzerine üretilebilir; Python engine tarafını değiştirmeden ilerlenmesi hedeflenmiştir.

## v1.2.0 model validation surface

Authenticated Quasar istemcisi `public.model_validation_snapshot` tablosunu yalnız `SELECT` için kullanabilir. Bu yüzey:

- `PIT_CORE_REPLAY / ETH/BTC`
- `PIT_FULL_REPLAY / URA/USD`
- `SHADOW_READINESS / ALL`

sonuçlarını, `model_version`, status ve metrics/details JSON alanlarıyla yayınlar. Mobil istemci bu tablodan model parametresi değiştiremez.
