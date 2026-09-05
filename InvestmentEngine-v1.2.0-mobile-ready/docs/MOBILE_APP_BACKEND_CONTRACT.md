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
Uygulama tek Auth kullanıcısı altında birden çok hesap açılmasını destekler; kullanıcının
kendisi, eşi veya çocuğu için tuttuğu işlem defterleri `account_id` ile ayrılır. Quasar'da
seçili hesap tüm portföy çalışma alanını belirler ve SecureLS/Pinia cache içinde saklanır.

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

İşlem kayıtları authenticated mobil istemci için append-only'dir. Düzeltme veya
iptal, eski satırı değiştirmek/silmek yerine `metadata.supersedes_transaction_id`
ile önceki kayda bağlanan yeni bir revizyon satırı ekler. İptal revizyonunda ayrıca
`metadata.cancelled_at` ve `metadata.cancellation_reason` bulunur.

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
Eski revizyonlar ve append-only iptal işaretleri bakiyeye dahil edilmez.

### `public.user_investment_settings`

Aylık bütçe, plan başlangıç tarihi, BTC/ETH/URA hedef oranları, BTC↔ETH ve
URA↔USD dönüşüm oranları, DCA günü ve Telegram tercihidir. Yüzde kolonları
veritabanında `0..1` oranı olarak saklanır; Quasar kullanıcıya `0..100` gösterir.
Bu ayarlar kullanıcı seviyesindedir; aynı kullanıcının birden çok portföy hesabı
olursa hesapların tamamında ortak uygulanır. Python karar motoru bu tabloyu okumaz.

Python kararları, Telegram bildirimi ve motor health verileri portföy hesabından
bağımsızdır. Python bot anahtarı ve Chat ID yalnız Windows Engine ayarlarından gelir;
Quasar seçili hesap veya bildirim tercihi Python'a fan-out yapılandırması göndermez.

### `public.reset_portfolio_transaction_history(uuid, text)`

Oturum sahibinin yalnız kendisine ait aktif bir yatırım hesabındaki bütün işlem ve
revizyon satırlarını kalıcı olarak temizleyen kontrollü RPC'dir. Genel `DELETE`
yetkisi kapalı kalır. RPC profil, yatırım ayarları, piyasa/model verileri, kararlar,
sinyal durumu ve engine health kayıtlarını değiştirmez.

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

`portfolio_transactions` için authenticated rol yalnız `SELECT` ve `INSERT`
yapabilir. `UPDATE`/`DELETE` politikaları ve yetkileri yoktur. Yatırım hesabı
silme de audit satırlarının cascade ile kaybolmaması için kapalıdır; hesap
`is_active=false` ile pasifleştirilir. Bilinçli test verisi temizliği yalnız hesap
sahipliğini ve tam onay ifadesini sunucu tarafında doğrulayan
`reset_portfolio_transaction_history` RPC'si üzerinden yapılabilir.

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
