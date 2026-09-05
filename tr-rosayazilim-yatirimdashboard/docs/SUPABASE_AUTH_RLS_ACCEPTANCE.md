# Gerçek Supabase Auth/RLS Kabul Kontrolü

Bu kontrol gerçek Supabase projesinde aşağıdaki zinciri salt-okuma ağırlıklı olarak doğrular:

- Auth health ve gecikme,
- test kullanıcısıyla parola girişi,
- sunucu üzerinden `getUser`,
- `profiles`, `investment_accounts`, `user_investment_settings`, `market_snapshot` ve
  `portfolio_positions` RLS okumaları,
- token yenileme,
- yerel sign-out sonrasında session temizliği.

## Güvenlik sınırı

Yalnız ayrı bir test kullanıcısı kullan. `service_role`, `sb_secret_*`, DB parolası veya
production kullanıcı parolasını kaynak koda ve `.env.example` dosyasına yazma. Script hiçbir
parolayı veya token'ı çıktıya basmaz ve portföy verisini değiştirmez.

## Çalıştırma

PowerShell oturumunda değerleri yalnız çalışan süreç için tanımla:

```powershell
$env:QCLI_SUPABASE_URL="https://PROJECT.supabase.co"
$env:QCLI_SUPABASE_PUBLISHABLE_KEY="PUBLISHABLE_OR_ANON_KEY"
$env:QCLI_ACCEPTANCE_EMAIL="test-user@example.com"
$env:QCLI_ACCEPTANCE_PASSWORD="TEST_USER_PASSWORD"
yarn test:acceptance
```

Başarılı çıktı `status: PASS`, `authenticatedRls: ok`, `tokenRefresh: PASS` ve
`localSignOut: PASS` alanlarını taşır.

## Ayrı manuel kabul kontrolleri

Bu script e-posta kutusuna veya fiziksel cihaza erişmez. Aşağıdakiler manuel kalır:

1. Yeni kullanıcı kaydı ve doğrulama e-postası callback'i.
2. Şifremi unuttum e-postası, recovery callback'i ve yeni parola belirleme.
3. Başka bir test kullanıcısının hesap/işlem satırlarına erişemediğinin iki kullanıcıyla negatif
   RLS testi.
4. Capacitor cold/warm custom-scheme deep-link testi.
5. Gerçek Supabase üzerinde çoklu hesap, reset RPC ve `100.000 TRY` ekran regresyonu.

Otomatik portföy matematiği regresyonu `yarn test` içinde çalışır; gerçek RLS ve e-posta zincirinin
yerine geçmez.
