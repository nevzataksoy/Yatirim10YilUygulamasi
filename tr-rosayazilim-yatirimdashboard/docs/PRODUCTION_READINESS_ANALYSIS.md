# Production Hazırlık ve Çoklu Portföy Etki Analizi

Tarih: 31.07.2026

## Sonuç

Quasar uygulaması tasarım, veri girişleri ve çoklu portföy çalışma alanı açısından
gerçek Supabase kullanıcı testine hazırdır. Python reposundaki
`0008_portfolio_audit_hardening.sql` ve `0009_portfolio_self_service_reset.sql`
migration'ları 31.07.2026 tarihinde Supabase SQL Editor'da başarıyla uygulanmıştır.
Migration'lar Python engine'in veri topladığı `market.*`, `macro.*`, `model.*`,
karar/snapshot ve health yazma yollarını değiştirmez.

Çoklu kullanıcı hedefinden vazgeçilmiştir. Tek Supabase Auth kullanıcısı altında
birden çok portföy hesabı açma, listeleme ve aktif çalışma alanını seçme arayüzü
aktiftir. Piyasa sinyalleri ve Telegram bildirimi portföyden bağımsız, varlık sistemi
odaklı kalacaktır.

## Tamamlanan entegrasyon düzeltmeleri

### Yatırım ayarları sözleşmesi

- Frontend artık veritabanında bulunmayan `id` ve `account_id` alanlarını göndermez.
- Kayıt `user_id` primary key'i üzerinden upsert edilir.
- Kullanıcıya yüzde olarak gösterilen hedef/dönüşüm oranları veritabanına `0..1`
  oranı olarak yazılır; okurken tekrar `0..100` yüzde gösterimine çevrilir.
- `start_date`, `btc_eth_conversion_pct` ve `ura_usd_conversion_pct` kolonları
  ileri migration ile sözleşmeye eklenmiştir.
- Dönüşüm oranı kolonları zorlayıcı portföy limiti değildir; kullanıcıya miktarı
  hızlı hesaplatan varsayılan/yardımcı oranlardır.
- `dca_day` ve `telegram_notifications` alanları Ayarlar sayfasında yönetilebilir.

### Append-only işlem bütünlüğü

- Düzenleme eski satırı değiştirmez; yeni revizyon ekler.
- İptal artık `DELETE` değildir. Nedeni zorunlu yeni bir iptal revizyonu eklenir.
- İptal veya revizyon sonraki işlemlerin bakiyesini bozarsa Quasar işlemi reddeder.
- `portfolio_positions` yalnız revizyon zincirinin güncel ve iptal edilmemiş
  satırlarını toplar.
- Authenticated rolün işlem `UPDATE`/`DELETE` ve yatırım hesabı `DELETE` yetkileri
  kaldırılmıştır.
- Aynı işleme iki ayrı doğrudan revizyon bağlanmasını engelleyen unique index ve
  kullanıcı/hesap sınırını doğrulayan insert trigger eklenmiştir.

### Profil yönetimi ve buton standardı

- `/profile` sayfası ad, ikinci ad, soyad, e-posta ve şifre güncellemesini destekler.
- Profil tablosu ile Supabase Auth metadata birlikte güncellenir.
- E-posta değişikliği Supabase'in doğrulama politikasına tabidir.
- Demo profil değişiklikleri yalnız cihazdaki demo state'inde kalır.
- Popup aksiyonları footer alanına taşınmış; Vazgeç, Geri Dön, Temizle, İptal ve
  birincil kayıt/onay aksiyonları push stiliyle belirginleştirilmiştir.

## Demo modu ve Supabase ilişkisi

Demo hesabın transaction, hesap, piyasa ve kullanıcı verileri SecureLS/Pinia içinde
yerel tutulur. `demo-user` ve `demo-main-account` gerçek UUID değildir ve Supabase'e
gönderilmez. Bu nedenle demo ekran revizyonları tek başına veritabanı migration'ı
gerektirmez.

Bu turdaki DB ihtiyacı demo modundan değil, gerçek kullanıcı akışındaki üç sözleşme
ihtiyacından doğmuştur:

1. Ayar kolonlarının frontend ile eşleşmesi.
2. Revizyonların bakiye görünümünde tek kez sayılması.
3. Append-only yetkilerinin RLS/grant düzeyinde uygulanması.

## Çoklu portföy hesabı değerlendirmesi

### Mevcut hazır temel

| Katman                              | Mevcut durum                                           | Sonuç                                    |
| ----------------------------------- | ------------------------------------------------------ | ---------------------------------------- |
| `investment_accounts`               | Bir kullanıcıya birden çok hesap satırı izinli         | Çoklu hesap için uygun                   |
| `portfolio_transactions.account_id` | Her işlem zorunlu olarak bir hesaba bağlı              | Hesap bakiyesi ayrıştırılabilir          |
| RLS                                 | `user_id = auth.uid()` ve hesap sahipliği kontrolü var | Kullanıcılar birbirinin verisini göremez |
| Quasar store                        | Hesap oluşturma, seçme ve SecureLS persistence aktif   | Seçili hesap uygulama çalışma alanıdır   |
| Ayarlar                             | Şu an kullanıcı başına tek satır                       | Hesap bazlı hedef gerekiyorsa yetersiz   |
| Sinyaller                           | Sistem bazlı global `ETH/BTC`, `URA/USD` kararı        | Hesaptan bağımsız karar motoru           |

### Yatırım ayarlarının kapsamı

1. Ortak strateji, çoklu hesap: Kullanıcının bütün portföy hesapları aynı hedef
   oranlarını kullanır. Mevcut `user_investment_settings` değişmeden kalır. Global
   sinyal modelimizle en uyumlu ve önerilen seçim budur.

2. Hesap bazlı strateji: Her hesabın bütçe, DCA günü, hedef ve dönüşüm hesaplama
   varsayımları farklı olur. Bunun için `investment_account_settings` tablosu gerekir.
   Bu tablo Python'un piyasa sinyalini değiştirmez; yalnız kullanıcı isterse global
   sinyal oranını seçili hesap bakiyesinde önizlemeye yarar. Python'un
   bu tabloyu okuyarak hesap başına tutar üretmesi istenirse repository, karar
   yayınlama sözleşmesi ve testler ayrıca değiştirilmelidir. Bugünkü motorda böyle
   bir okuma yoktur.

Bu proje için karar ortak stratejili çoklu portföydür. Hesap bazlı ayar tablosu
şimdilik eklenmemelidir. Kullanıcı başına bir varsayılan hesap kuralı ve hesap
adlarında mevcut `unique(user_id, name)` kuralı korunmalı; hesap silmek yerine
`is_active=false` kullanılmalıdır.

## Python sinyalleri ve Telegram'a etkisi

Python engine bugün portföy hesabı veya kullanıcı için ayrı sinyal üretmez. `model.decisions`,
`decision_snapshot` ve `decision_history` piyasa/sistem bazlı global karar üretir.
Bu yaklaşım çoklu portföyde de çalışır: aynı piyasa sinyali tüm hesaplar tarafından
okunabilir.

Kişiselleştirme gereken nokta sinyal üretimi değil, sinyalin uygulanma önerisidir.
Python `action_size`, risk ve confidence ile küçülebilen K1/K2 model kademesidir;
sabit `%50` sinyal değildir. Gerçek çevrilecek miktar seçili hesabın BTC/ETH/URA
veya USD bakiyesine göre Quasar tarafından hesaplanabilir, fakat mevcut
`ConversionForm` bunu otomatik uygulamaz; kullanıcı gerçek işlem miktarını seçer.

Mevcut Telegram yapılandırması tek bot token/chat id ile servis seviyesindedir.
Tek kullanıcı ve varlık odaklı tek bildirim kararı korunduğu için fan-out,
abonelik tablosu veya kullanıcı/portföy eşlemesi gerekmez. Telegram mesajındaki
`action_size` global model kademe önerisidir; portföyde çevrilecek gerçek adet
Quasar'da seçili hesabın güncel bakiyesi üzerinden hesaplanmalıdır. Python
`user_investment_settings` tablosunu okumaz ve Quasar dönüşüm oranıyla
`action_size` değerini bugün otomatik uygulayan released sözleşme yoktur.
Onaylanan hedef, Quasar'ın kararı `decision_id` ile isteğe bağlı bağlaması,
`action_size` değerini yalnız düzenlenebilir başlangıç oranı olarak doldurması ve
gerçek oranı kullanıcıya bırakmasıdır. `min(model önerisi, kullanıcı limiti)` veya
hard limit uygulanmaz. Sinyal ID'si elle yazdırılmaz; seçim `AppPopupSelect` ile
yapılır. Bu nedenle çoklu portföy sinyal üretimi için Python değişikliği gerekmez;
frontend entegrasyonu Auth/connection yaşam döngüsünden sonra ele alınır.

Telegram yapılandırmasının Quasar'dan okunmaması bilinçli mimari karardır. Bot API
Key ve Chat ID Python ayar penceresinden girilir; Python bildirimi yerel `settings`
ve `engine_mode == live` koşuluyla yönetir. Tek kullanıcı ve tek Telegram hedefi
nedeniyle portföy veya Quasar ayarıyla entegrasyon eklenmeyecektir.

## Deneme portföy verisini sıfırlama

Authenticated kullanıcı için kontrollü olarak uygulanmıştır. Genel `DELETE` yetkisi
kapalı kalır. Ayarlar sayfasındaki tehlikeli bölge iki aşamalı onaydan sonra
`reset_portfolio_transaction_history` RPC'sini çağırır. RPC:

- `auth.uid()` ile oturumu doğrular,
- hesabın oturum sahibine ait ve aktif olduğunu doğrular,
- tam `PORTFÖYÜ SIFIRLA` ifadesini sunucu tarafında denetler,
- yalnız seçili hesabın `portfolio_transactions` satırlarını siler,
- silinen satır sayısını istemciye döndürür.

Profil, yatırım ayarları, diğer portföy hesapları, `market.*`, `macro.*`, `model.*`,
karar/sinyal geçmişi, Telegram ve engine health verileri korunur. Demo modunda aynı
işlem yalnız cihazdaki seçili demo hesabının SecureLS/Pinia satırlarını temizler.

## 10 yıllık raporlama sürdürülebilirliği

Tek hesapta aylık alım, birkaç dönüşüm/satış ve revizyonla 10 yılda beklenen satır
sayısı yüzler veya düşük binler düzeyindedir. Mevcut Decimal tabanlı kronolojik replay
bu hacimde yeterlidir. Kullanıcı izolasyonu RLS ile, hesap/tarih erişimi de mevcut
`(account_id, transaction_at desc)` index'i ile desteklenmektedir.

Yine de mevcut Quasar sync bütün kullanıcının bütün işlem satırlarını indirip maliyet
bazını tarayıcıda baştan hesaplar. Tek kullanıcı/az hesap için kabul edilebilir;
hesap ve kullanıcı sayısı büyürse şu sıra izlenmelidir:

1. Geçmiş ekranına cursor pagination eklemek.
2. Sync sorgusunu seçili `account_id` ile sınırlamak.
3. Sunucuda doğrulanmış hesap özeti/RPC üretmek; ham ledger'ı audit kaynağı olarak
   korumak.
4. Aylık kapanış snapshot'larıyla rapor trendlerini hızlandırmak; gerektiğinde son
   snapshot sonrası işlemleri replay etmek.
5. Snapshot ile ham ledger sonucunu düzenli uzlaştırma testiyle karşılaştırmak.

Maliyet bazı sıra bağımlı olduğu için yalnız basit `SUM` görünümü kâr/ortalama maliyet
raporları için yeterli değildir. Ham append-only ledger doğruluk kaynağı olarak
korunmalı, snapshot/özetler yalnız hızlandırma katmanı olmalıdır.

## Bağlantı testi ve Auth yaşam döngüsü — kod tamamlandı, gerçek ortam kabulü açık

Signal→Conversion entegrasyonundan önce bu katman kod seviyesinde tamamlandı. Gerçek
Supabase health testi, authenticated RLS probe, client/listener dispose-re-init,
Auth event state yönetimi ve confirmation/recovery callback sayfası aktiftir.
`yarn test:acceptance` gerçek test kullanıcısıyla health/login/RLS/token refresh/local
sign-out zincirini secret basmadan çalıştırır.

Önceki kod incelemesindeki aşağıdaki açıklar giderildi:

1. Bağlantı ayarı yalnız URL ve key alanlarının boş olmadığını kontrol eder; gerçek
   Supabase Auth erişimi veya authenticated RLS sorgusu kaydetmeden önce test edilmez.
2. `resetSupabaseClient()` client referansını değiştirir fakat auth store'daki
   `listenerBound` ve `ready` durumunu sıfırlamaz. Eski subscription unsubscribe
   edilmez; yeni client listener'ı için sayfa yenilemeye bağımlı davranış oluşabilir.
3. Auth event türü yok sayılarak yalnız session uygulanır. `TOKEN_REFRESHED`,
   `USER_UPDATED`, `PASSWORD_RECOVERY`, `SIGNED_OUT` ve proje bağlantısı değişimi
   için açık state-transition/cleanup sözleşmesi yoktur.
4. Şifre sıfırlama e-postası gönderilir fakat `redirectTo`, recovery route/formu ve
   hash-router/Capacitor deep-link dönüşü uygulanmamıştır.
5. Başlangıç sync'leri `Promise.allSettled()` ile kullanıcıya görünmeden
   yutulabilir; geçersiz key, timeout, offline, RLS reddi ve süresi dolmuş refresh
   token hataları bağlantı/auth/veri-yetkisi olarak ayrıştırılmaz.
6. Otomatik Auth yaşam döngüsünü doğrulayan test paketi bulunmamaktadır.

Uygulanan sıra:

1. Yeniden kullanılabilir `testConnection` sonucu: Auth endpoint erişimi, latency ve
   açıklanabilir hata; girişten sonra authenticated RLS read smoke testi.
2. Supabase client manager: connection signature, subscription dispose, yeni client
   oluşturma ve auth store re-init tek atomik işlem.
3. Auth state machine: initial session, sign-in/register/confirmation, token refresh,
   user update, password recovery, sign-out ve dependent store/cache cleanup.
4. SPA hash callback ile Capacitor deep-link ayrımı; password-recovery ekranı ve
   expired/used link davranışı.
5. Unit/state testleri ve gerçek Supabase matrisi: reload, uygulamayı kapat/aç,
   offline→online, refresh token, connection change, sign-out ve RLS denial.
6. Otomatik 100.000 TRY, çoklu hesap izolasyonu, revision/cancellation, overdraft ve
   idempotency regression'ı tamamlandı. Gerçek Supabase/reset RPC ve ekran kabulü
   sonrasında Signal→Conversion'a geçilecek.

Bu revizyon database model davranışını değiştirmez. Publishable/anon key sınırı,
RLS ve tek kullanıcı altında çoklu portföy kararı korunur. Capacitor aşamasında
refresh/session secret'ı SecureLS'den native secure storage'a taşınacaktır.

Portföy insert akışı da sağlamlaştırıldı: istemci transaction UUID'si DB primary key
olarak korunur, retry aynı kaydı döndürür, farklı içerikli UUID tekrarı reddedilir;
store bakiye zincirini insert öncesi replay eder. OPENING satırları tek bulk SQL
statement ile atomik, CONVERSION ise tek ledger satırında iki bacaklıdır. Otomatik
testler `PASS`; gerçek Supabase credentials/e-posta/cihaz kanıtı `OPEN`dır.

## Gerçek Supabase testine geçiş sırası

1. Çalışan Python görevlerinin normal devam ettiğini doğrula.
2. Uygulanmış `0008` ve `0009` sözleşmelerinin bulunduğunu doğrula; migration'ları
   yeniden çalıştırma.
3. Yeni bir Auth test kullanıcısı oluştur ve otomatik profil/ana hesap/ayar satırını
   doğrula.
4. Quasar'da gerçek giriş yap; profil ve yatırım ayarlarını kaydet, ikinci bir
   portföy hesabı oluştur ve hesaplar arasında geçiş yap.
5. Başlangıç, sermaye, alım, dönüşüm, satış, revizyon ve iptal senaryosunu çalıştır.
6. Quasar ledger ile `public.portfolio_positions` sonucunu karşılaştır.
7. Performans testinden sonra Ayarlar > Tehlikeli Bölge üzerinden seçili test
   portföyünün işlem geçmişini temizle.

Çoklu hesap yönetim ekranı uygulanmıştır. Çoklu kullanıcı ve Telegram fan-out
kapsamdan çıkarılmıştır.

## Resmi Supabase referansları

- RLS, service-role ve performans: https://supabase.com/docs/guides/database/postgres/row-level-security
- Grants ve RLS katmanları: https://supabase.com/docs/guides/api/securing-your-api
- Yedekler ve point-in-time recovery: https://supabase.com/docs/guides/platform/backups
- Sorgu ve indeks optimizasyonu: https://supabase.com/docs/guides/database/query-optimization
- Veritabanı performans izleme: https://supabase.com/docs/guides/database/inspect
