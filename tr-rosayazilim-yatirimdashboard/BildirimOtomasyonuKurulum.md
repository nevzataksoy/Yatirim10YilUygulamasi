# Bildirim Otomasyonu Kurulum Rehberi

Bu belge `Bildirim Yönetimi > Otomasyonlar` ekranından günlük portföy özeti ve sinyal bildirimi oluşturmayı, her form alanının hangi DB tablosu/kolonuna yazıldığını ve backend'in bu kaydı nasıl kullandığını açıklar.

Ön koşul: `BildirimModulKurulumu.md` içindeki Firebase/Capacitor/Supabase temel kurulumu yapılmış olmalıdır.

---

## 1. Otomasyon ekranına giriş

Quasar uygulamasında gerçek Supabase hesabınla login ol.

```text
Sağ üst profil menüsü
→ Bildirim Yönetimi
→ Otomasyonlar
```

Burada `public.notification_templates` tablosundaki kendi şablonların listelenir.

Her satırda:

- şablon adı,
- tetikleyici,
- saat/timezone,
- display para birimi,
- aktif/pasif toggle,
- düzenle,
- sil

bulunur.

---

## 2. Günlük 09:00 portföy bildirimi oluşturma

`Otomasyon Şablonu` butonuna bas.

Örnek hedef:

> Her sabah 09:00'da Ana Portföy hesabımın güncel değerini uygulamada seçtiğim para biriminde telefona gönder.

Formu şu şekilde doldur:

### Şablon Adı

Örnek:

```text
Ana Portföy Sabah Özeti
```

DB:

```text
public.notification_templates.name
```

Bu yalnız kullanıcıya görünen addır.

### Tetikleyici

Seç:

```text
Günlük Portföy Özeti
```

DB:

```text
notification_templates.event_type = 'PORTFOLIO_DAILY'
```

Bu seçim yapılınca portföy hesabı, saat, display currency, timezone ve gün alanları görünür.

### Portföy Hesabı

`AppPopupSelect` içerisinden örneğin:

```text
Ana Portföy
```

seç.

DB:

```text
notification_templates.account_id
→ public.investment_accounts.id
```

Backend değerleme sırasında yalnız bu hesabın efektif ledger bakiyelerini kullanır.

### Gönderim Saati

Gir:

```text
09:00
```

DB:

```text
notification_templates.schedule_time = '09:00'
```

Bu telefon local timer'ı değildir. Windows Server'daki notification dispatcher, template timezone'ına göre zamanı geldiğinde outbox oluşturur.

### Timezone

Türkiye için:

```text
Europe/Istanbul
```

DB:

```text
notification_templates.timezone
```

Saat 09:00'un hangi coğrafi saat dilimine göre değerlendirileceğini belirler.

### Gösterim Para Birimi

Seçenek Quasar `DISPLAY_ASSETS` listesine göre gelir. Örnek:

```text
TRY
```

veya:

```text
USD
```

Diğer desteklenen yatırım varlıkları UI display listesinde varsa seçilebilir.

DB:

```text
notification_templates.display_currency
```

Bu alan portföydeki gerçek varlıkları değiştirmez; yalnız bildirimdeki değerleme birimini belirler.

### Çalışacağı Günler

Örneğin her gün:

```text
Pzt Sal Çar Per Cum Cmt Paz
```

DB:

```text
notification_templates.days_of_week = [1,2,3,4,5,6,7]
```

ISO mantığı:

```text
1 = Pazartesi
2 = Salı
3 = Çarşamba
4 = Perşembe
5 = Cuma
6 = Cumartesi
7 = Pazar
```

Sadece hafta içi istiyorsan `[1,2,3,4,5]` seç.

### Bildirim Başlığı

Öneri:

```text
Günlük Portföy Özeti
```

DB:

```text
notification_templates.title_template
```

İstersen placeholder kullanabilirsin:

```text
{{account_name}} Günlük Özeti
```

### Bildirim Metni

Öneri:

```text
{{account_name}} portföy değeri: {{portfolio_value}} {{display_currency}}
```

DB:

```text
notification_templates.body_template
```

Günlük portföy template'inde kullanılabilen temel placeholder'lar:

```text
{{portfolio_value}}
{{display_currency}}
{{account_name}}
{{route}}
```

`route` backend tarafından `/portfolio` olarak gönderilebilir; RightDrawer mesajına tıklandığında Quasar ilgili sayfaya geçebilir.

### Şablon aktif

Açık bırak:

```text
enabled = true
```

DB:

```text
notification_templates.enabled
```

Şablonu silmeden geçici olarak durdurmak istiyorsan listede toggle'ı kapatman yeterlidir.

---

## 3. Günlük değer hangi verilerden hesaplanır?

Backend `public.notification_portfolio_value(account_id, display_currency)` fonksiyonunu çağırır.

Portföy adedi kaynağı:

```text
public.portfolio_positions
```

Bu view append-only ledger'dan yalnız efektif, iptal edilmemiş ve superseded olmayan işlemleri toplar.

Dolayısıyla:

- OPENING,
- BUY,
- SELL,
- CONVERSION,
- CASH_IN,
- CASH_OUT

hareketleri güncel bakiyeyi oluşturur.

Başlangıç kaydını revize ettiğinde eski OPENING audit için durur fakat efektif portföye yalnız yeni revision girer.

### BTC / ETH / URA değerleme

Güncel market snapshot'lar kullanılır:

```text
public.market_snapshot
```

Örnek:

```text
BTC/USD
ETH/USD
URA/USD
USD/TRY
```

USD değer örneği:

```text
BTC quantity × BTC/USD
+ ETH quantity × ETH/USD
+ URA quantity × URA/USD
+ USD balance
+ TRY balance / USDTRY
```

TRY bildiriminde USD toplamı güncel `USD/TRY` ile çevrilir.

Bu değerleme maliyet bazı/kâr hesabı değildir; bildirim anındaki **güncel yaklaşık portföy piyasa değeri**dir.

---

## 4. Otomasyon zamanı geldiğinde DB akışı

Örneğin template 09:00 Europe/Istanbul:

```text
notification_templates
        ↓
enqueue_due_portfolio_notifications(now())
        ↓
notification_outbox (PENDING)
        ↓
Python NotificationDispatcher
        ↓
notification_messages
        ↓
FCM → notification_devices
        ↓
notification_logs
```

Aynı template aynı gün/scheduled slot için tekrar tekrar outbox üretmemelidir; migration dedupe anahtarıyla bunu sınırlar.

---

## 5. Otomasyonu başlatma / durdurma

Otomasyonlar listesinde şablonun sağındaki toggle:

```text
Açık  → notification_templates.enabled = true
Kapalı → notification_templates.enabled = false
```

Kapalı template yeni outbox üretmez.

Geçmiş mesaj/log kayıtları silinmez.

---

## 6. Sinyal oluştu bildirimi oluşturma

`Otomasyon Şablonu` butonuna bas.

### Şablon Adı

Örnek:

```text
Yatırım Motoru Sinyalleri
```

### Tetikleyici

Seç:

```text
Yeni Sinyal Oluştu
```

DB:

```text
notification_templates.event_type = 'SIGNAL_CREATED'
```

Bu tipte günlük saat alanı kullanılmaz. Olay engine karar kaydıyla tetiklenir.

### Bildirim Başlığı

Örnek:

```text
Yeni Yatırım Sinyali
```

veya:

```text
{{system}} Sinyali
```

### Bildirim Metni

Öneri:

```text
{{system}} için {{direction}} sinyali oluştu. Edge {{edge}}, güven {{confidence}}, veri kalitesi {{data_quality}}.
```

Kullanılabilir placeholder'lar:

```text
{{system}}
{{direction}}
{{edge}}
{{confidence}}
{{data_quality}}
{{decision_id}}
{{route}}
```

DB trigger `public.decision_history` satırını izler. Yalnız:

```text
action_event = true
```

olan yeni karar için `SIGNAL_CREATED` outbox üretir.

Bu önemlidir: her günlük WAIT/HOLD değerlendirmesini push yapmayız; gerçek model aksiyon olayı oluştuğunda göndeririz.

---

## 7. Telegram ile ilişkisi

FCM bildirimi Telegram'ın yerine geçmez.

Mevcut sözleşme:

```text
Telegram bildirimi
→ Python ayar dosyası / engine_mode kuralları

Quasar FCM bildirimi
→ notification_templates + notification_devices

RightDrawer
→ notification_messages
```

Aynı sinyal için Telegram ve mobil uygulama bildirimi birlikte kullanılabilir.

FCM başarısız olsa bile Telegram motor davranışı bundan etkilenmez.

---

## 8. Cihaz seçimi nasıl yapılır?

Şu an template kullanıcı seviyesindedir ve aktif/izinli tüm cihazlara gönderilir.

Aktif cihaz sorgusu mantığı:

```text
notification_devices.user_id = template.user_id
is_active = true
permission_status = 'GRANTED'
push_target is not null
```

Belirli bir telefona geçici olarak bildirim istemiyorsan:

```text
Bildirim Yönetimi
→ Cihazlar
→ ilgili cihaz toggle kapat
```

Bu cihaz kaydını silmez.

---

## 9. Firebase provider açık/kapalı

`Bildirim Yönetimi > Firebase`:

```text
FCM bildirimlerini etkinleştir
```

alanı:

```text
public.push_provider_settings.enabled
```

kolonuna karşılık gelir.

Provider kapalıysa:

- otomasyon şablonları DB'de kalabilir,
- RightDrawer mesajı oluşturulabilir,
- fiziksel FCM gönderimi SKIPPED olur.

Bu sayede otomasyonları silmeden push kanalını global olarak durdurabilirsin.

---

## 10. Bildirim loglarını okuma

Uygulama:

```text
Bildirim Yönetimi
→ Loglar
```

DB:

```text
public.notification_logs
```

Başlıca kolonlar:

- `user_id`: kullanıcı
- `message_id`: oluşturulan uygulama içi mesaj
- `template_id`: kaynak otomasyon
- `device_id`: hedef cihaz
- `provider`: FCM
- `status`: SENT / FAILED / SKIPPED vb.
- `provider_message_id`: Firebase'in döndürdüğü message ID
- `error_message`: hata
- `created_at`: deneme zamanı

Push gelmiyorsa ilk bakılacak alan `error_message`dır.

---

## 11. RightDrawer bildirim kutusu

Header'daki zil ikonuna bas:

```text
RightDrawer → Bildirimler
```

Kaynak:

```text
public.notification_messages
```

Alanlar:

- `title`
- `body`
- `event_type`
- `payload`
- `created_at`
- `read_at`

Okunmayan adet header zilinde badge olarak görünür.

Mesaja basıldığında:

- `read_at` güncellenir,
- payload içindeki `route` varsa ilgili Quasar sayfasına gidilir.

Örnek route:

```text
/portfolio
/signals
```

---

## 12. Örnek: her gün 09:00 TRY portföy özeti

Form:

```text
Şablon Adı:            Sabah TRY Portföy Özeti
Tetikleyici:            Günlük Portföy Özeti
Portföy Hesabı:         Ana Portföy
Gönderim Saati:         09:00
Timezone:               Europe/Istanbul
Gösterim Para Birimi:   TRY
Günler:                 Pzt-Sal-Çar-Per-Cum-Cmt-Paz
Başlık:                 {{account_name}} Günlük Özeti
Metin:                  Güncel değer: {{portfolio_value}} {{display_currency}}
Şablon aktif:           Açık
```

DB karşılığı özet:

```text
notification_templates.name                = 'Sabah TRY Portföy Özeti'
notification_templates.event_type          = 'PORTFOLIO_DAILY'
notification_templates.account_id          = <Ana Portföy UUID>
notification_templates.schedule_time       = '09:00'
notification_templates.timezone            = 'Europe/Istanbul'
notification_templates.display_currency    = 'TRY'
notification_templates.days_of_week        = [1,2,3,4,5,6,7]
notification_templates.enabled             = true
```

---

## 13. Örnek: yalnız hafta içi USD özeti

```text
Şablon Adı:            Hafta İçi USD Özet
Tetikleyici:            Günlük Portföy Özeti
Saat:                   09:00
Timezone:               Europe/Istanbul
Display Currency:       USD
Günler:                 1,2,3,4,5
```

Cumartesi/Pazar outbox oluşmaz.

---

## 14. Örnek: sinyal bildirimi

```text
Şablon Adı:  Motor Sinyal Push
Tetikleyici: Yeni Sinyal Oluştu
Başlık:      {{system}} yeni sinyal
Metin:       {{direction}} · Edge {{edge}} · Güven {{confidence}} · Quality {{data_quality}}
Aktif:       Evet
```

Beklenen payload örneği:

```json
{
  "event_type": "SIGNAL_CREATED",
  "system": "ETH/BTC",
  "direction": "BTC→ETH",
  "edge": 82.4,
  "confidence": 84.1,
  "data_quality": 91.0,
  "decision_id": 123,
  "route": "/signals"
}
```

Değerler örnektir; gerçek değerler o karar kaydından gelir.

---

## 15. Manuel SQL doğrulamaları

### Şablonlar

```sql
select
  id,
  name,
  event_type,
  enabled,
  account_id,
  schedule_time,
  timezone,
  display_currency,
  days_of_week
from public.notification_templates
order by created_at desc;
```

### Cihazlar

```sql
select
  device_name,
  platform,
  permission_status,
  is_active,
  target_kind,
  last_seen_at
from public.notification_devices
order by last_seen_at desc;
```

Token değerini operasyon ekranlarında gereksiz yere paylaşma/loglama.

### Outbox

Service-role/admin incelemesinde:

```sql
select
  id,
  event_type,
  status,
  available_at,
  attempts,
  last_error,
  created_at
from public.notification_outbox
order by created_at desc
limit 100;
```

### Uygulama içi mesajlar

```sql
select id, event_type, title, body, read_at, created_at
from public.notification_messages
order by created_at desc
limit 100;
```

### Loglar

```sql
select status, provider, provider_message_id, error_message, created_at
from public.notification_logs
order by created_at desc
limit 100;
```

---

## 16. Portföy değerleme fonksiyonunu elle test etme

Supabase SQL Editor'da account UUID ve currency ile:

```sql
select public.notification_portfolio_value(
  '<INVESTMENT_ACCOUNT_UUID>'::uuid,
  'TRY'
);
```

Dönen JSON içerisinde toplam değer ve kullanılan snapshot bilgileri yer alır.

USD için:

```sql
select public.notification_portfolio_value(
  '<INVESTMENT_ACCOUNT_UUID>'::uuid,
  'USD'
);
```

Bu test FCM göndermez; yalnız değerleme fonksiyonunu doğrular.

---

## 17. Başlangıç portföyü düzeltmeleri otomasyonu etkiler mi?

Evet, doğru şekilde etkiler.

Yeni opening kuralı:

- aynı account+asset için ikinci bağımsız aktif OPENING oluşturma,
- mevcut OPENING'i transaction revision akışıyla düzelt,
- eksik bir asset hiç OPENING almamışsa sonradan ilk OPENING olarak ekle.

`portfolio_positions` yalnız efektif revision'ı kullandığı için ertesi bildirim güncel düzeltilmiş miktarı esas alır.

Tüm işlemleri baştan girmek istiyorsan kontrollü `PORTFÖYÜ SIFIRLA` RPC kullanılabilir. Bu normal düzeltme yöntemi değildir.

---

## 18. Banka / Borsa / Aracı Kurum verisi bildirimlerde kullanılabilir mi?

Yeni sözlük:

```text
public.financial_institutions
public.investment_account_institutions
portfolio_transactions.institution_id
```

sayesinde ileride notification template context'ine örneğin:

```text
{{institution_name}}
{{largest_institution}}
```

gibi placeholder'lar eklenebilir.

İlk sürüm günlük değer ve sinyal bildirimine odaklıdır; kurum dağılımı push'u sonraki raporlama geliştirmesidir.

---

## 19. Şablon değişikliği ne zaman etkili olur?

Şablonu kaydettiğin anda sonraki enqueue değerlendirmesinde yeni değerler kullanılır.

Örnek:

```text
09:00 → 10:30
```

değiştirirsen sonraki uygun slot 10:30 olur.

Daha önce SENT olan notification logları değiştirilmez.

---

## 20. Operasyon kuralları

Production kullanımda şu kuralları koru:

1. Firebase private key'i UI'ya girme.
2. Cihaz push token'ını kullanıcıya açık raporlarda gösterme.
3. Template'i test ederken 1 dakikada çok sayıda tekrarlı slot üretme.
4. Sinyal push'unu yalnız `action_event=true` mantığında tut.
5. Bildirim modülünü model threshold/weight/readiness koduyla bağlama.
6. Notification failure engine market/model job failure sayılmamalı.
7. Günlük portföy bildirimini “kesin banka değeri” değil, market snapshot tabanlı güncel karar-destek değeri olarak yorumla.
8. Telegram ve FCM kanallarını bağımsız tut.
9. Template kapatmayı kayıt silmek yerine tercih et; log geçmişi korunur.
10. 0010 Shadow observability rollout'unu bildirim modülünden ayrı yönet.

---

## 21. Kullanıma alma kontrol listesi

- [ ] `0011_portfolio_institutions_notifications.sql` uygulandı.
- [ ] Kurum sözlüğü ekranı çalışıyor.
- [ ] İşlem formlarında kurum AppPopupSelect ile seçilebiliyor.
- [ ] Firebase Android app package adı doğru.
- [ ] `google-services.json` doğru native app klasöründe.
- [ ] `yarn install` tamamlandı.
- [ ] `npx cap sync android` tamamlandı.
- [ ] APK yeni `versionCode` ile build edildi.
- [ ] Gerçek cihaz notification permission GRANTED.
- [ ] `notification_devices` satırı oluştu.
- [ ] Provider metadata kaydedildi.
- [ ] En az bir PORTFOLIO_DAILY template oluşturuldu.
- [ ] En az bir SIGNAL_CREATED template oluşturuldu.
- [ ] Python yeni FCM backend sürümü kontrollü deploy edildi.
- [ ] RightDrawer mesaj testi geçti.
- [ ] Foreground push testi geçti.
- [ ] Background/uygulama kapalı push testi geçti.
- [ ] Log ekranında SENT provider id görüldü.
- [ ] Bildirim hatası Shadow/model readiness sonucunu değiştirmedi.
