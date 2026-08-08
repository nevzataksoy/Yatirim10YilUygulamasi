# Bildirim Modülü Kurulumu

Bu belge `tr-rosayazilim-yatirimdashboard` Quasar/Capacitor uygulamasına eklenen bildirim altyapısının **Firebase Cloud Messaging (FCM) + Supabase + Python Investment Engine** ile nasıl devreye alınacağını anlatır.

## 1. Mimari ve güvenlik sınırı

Bildirim modülü üç katmandan oluşur:

1. **Quasar/Capacitor**: kullanıcı arayüzü, cihaz kaydı, bildirim izinleri, RightDrawer bildirim kutusu, Firebase proje metadata ayarları, otomasyon şablonları ve log ekranları.
2. **Supabase**: cihaz, şablon, outbox, uygulama içi mesaj ve gönderim loglarını saklar.
3. **Python Investment Engine**: FCM mesajını gerçek cihaza gönderen güvenilir backend'dir.

Firebase **service account JSON / private key kesinlikle Quasar projesine, APK içine, Supabase kullanıcı tablolarına veya GitHub reposuna konulmaz**. Mobil uygulama yalnız `firebase_project_id`, `sender_id`, Android package adı ve gerekirse PWA VAPID public key gibi secret olmayan bilgileri yönetir.

Sunucu private key'i Windows Server'da örneğin şu dizinde tutulabilir:

```text
C:\ProgramData\Rosa\InvestmentEngine\secrets\firebase-service-account.json
```

Python servisine şu environment variable'lardan biri verilmelidir:

```text
FIREBASE_SERVICE_ACCOUNT_PATH=C:\ProgramData\Rosa\InvestmentEngine\secrets\firebase-service-account.json
```

veya Google standardı:

```text
GOOGLE_APPLICATION_CREDENTIALS=C:\ProgramData\Rosa\InvestmentEngine\secrets\firebase-service-account.json
```

## 2. Firebase Console projesi oluşturma

Firebase Console'a gir:

1. **Create a project / Proje ekle** seç.
2. Proje adı örneği: `Rosa Yatirim Dashboard`.
3. Google Analytics bu modül için zorunlu değildir; ihtiyacına göre açabilirsin.
4. Proje oluşturulduktan sonra **Project settings / Proje ayarları** ekranına gir.

Not etmen gereken secret olmayan değerler:

- **Project ID** → Quasar `Bildirim Yönetimi > Firebase > Firebase Project ID` tr-rosayazilim-yatirimdash
- **Project number / Sender ID** → Quasar `Sender ID / Project Number` 730014337064

## 3. Android uygulamasını Firebase'e ekleme

Firebase Console:

1. Project settings > General.
2. **Your apps** bölümünden Android ikonunu seç.
3. Android package name alanına **tam olarak** şunu yaz:

```text
tr.rosayazilim.yatirimdashboard
```

4. App nickname isteğe bağlıdır: `Yatirim Dashboard Android`.
5. SHA-1/SHA-256 ilk temel FCM kurulumu için zorunlu değildir. İleride Google Sign-In/App Check kullanırsan eklenebilir.
6. Uygulamayı kaydet.
7. Firebase'in ürettiği `google-services.json` dosyasını indir.

Dosyayı **repo dışında veya güvenli yerel çalışma kopyasında** şu konuma yerleştir:

```text
tr-rosayazilim-yatirimdashboard/
└─ src-capacitor/
   └─ android/
      └─ app/
         └─ google-services.json
```

Repo `.gitignore` dosyası bu dosyanın yanlışlıkla commit edilmesini engelleyecek şekilde güncellenmiştir.

> `google-services.json` service-account private key değildir; yine de environment-specific olduğu için repoda tutulmaması tercih edilmiştir.

## 4. Firebase Cloud Messaging'in açık olduğunu doğrulama

Firebase Console > Project settings > Cloud Messaging bölümüne gir.

Kontrol et:

- Firebase Cloud Messaging API aktif olmalı.
- Project ID / Project Number doğru olmalı.
- Android uygulama package adı `tr.rosayazilim.yatirimdashboard` olmalı.

Eski “Server key” yaklaşımını kullanmıyoruz. Python backend Firebase Admin SDK ve service-account/ADC kullanır.

## 5. Firebase service account oluşturma

Firebase Console > Project settings > **Service accounts**:

1. `Firebase Admin SDK` bölümünü aç.
2. `Generate new private key` seç.
3. JSON dosyasını indir.
4. Dosyayı GitHub'a, Quasar klasörüne veya APK kaynaklarına kopyalama.
5. Windows Server'da yalnız servis hesabının okuyabileceği bir dizine taşı.
6. Yukarıdaki `FIREBASE_SERVICE_ACCOUNT_PATH` veya `GOOGLE_APPLICATION_CREDENTIALS` değişkenini tanımla.

Windows PowerShell örneği (makine seviyesinde; yolu kendi sunucuna göre değiştir):

```powershell
[Environment]::SetEnvironmentVariable(
  'FIREBASE_SERVICE_ACCOUNT_PATH',
  'C:\ProgramData\Rosa\InvestmentEngine\secrets\firebase-service-account.json',
  'Machine'
)
```

Servisin yeni environment variable'ı görmesi için ileride yeni backend deploy edildiğinde servis restart edilir.

## 6. Supabase migration 0011

Bu modülün DB yapısı:

```text
InvestmentEngine-v1.2.0-mobile-ready/
└─ migrations/
   └─ 0011_portfolio_institutions_notifications.sql
```

Aynı migration `supabase-migrations` altında da mirror olarak bulunur.

Supabase Dashboard > SQL Editor > New query aç, `0011_portfolio_institutions_notifications.sql` içeriğini yapıştırıp çalıştır.

### 0011 şimdi uygulanabilir mi?

Evet. `0011` yalnız public portföy/kurum/bildirim yüzeyini genişletir. Çalışan eski Python v1.2 servisinin veri topladığı `market.*`, `macro.*`, `model.*` ve `system.job_runs` scheduler sözleşmesini değiştirmez.

Bu yüzden mevcut 30 günlük Shadow servisinin durdurulması gerekmez.

### 0010 ile karıştırma

`0010_shadow_observability.sql` ayrı konudur. Onu mevcut eski EXE çalışırken uygulamıyoruz; 30 günlük Shadow döneminden sonra yeni Python build/deploy ile birlikte kontrollü olarak uygulayacağız.

Özet:

```text
Şimdi:     0011 uygulanabilir
Şimdi:     Eski v1.2 Shadow servisi çalışmaya devam eder
Bekle:     0010
Bekle:     Yeni Python EXE deploy/restart
```

## 7. 0011 ile oluşan bildirim tabloları

- `public.push_provider_settings`: Quasar'dan girilen secret olmayan Firebase proje bilgileri.
- `public.notification_devices`: kullanıcının kayıtlı mobil cihazları ve push target bilgileri.
- `public.notification_templates`: günlük portföy/sinyal otomasyonları.
- `public.notification_outbox`: backend'in göndereceği kuyruk. Mobil istemci bu tabloyu yönetmez.
- `public.notification_messages`: RightDrawer uygulama içi bildirim kutusu.
- `public.notification_logs`: FCM teslim denemeleri ve hataları.

Ayrıca:

- `public.enqueue_due_portfolio_notifications(...)`
- `public.notification_portfolio_value(...)`

fonksiyonları günlük otomasyon için kullanılır.

## 8. Quasar bağımlılıklarını kurma

Repo güncellendikten sonra:

```powershell
cd tr-rosayazilim-yatirimdashboard
yarn install
```

Yeni temel Capacitor bağımlılıkları:

```text
@capacitor/app
@capacitor/core
@capacitor/device
@capacitor/push-notifications
```

Sonra Capacitor native projeyi eşitle:

```powershell
npx cap sync android
```

veya Quasar build akışını kullan:

```powershell
yarn build:android
```

`yarn.lock` bu geliştirme ortamında internet olmadığı için yeniden üretilmemiştir. Kendi geliştirme PC'nde `yarn install` çalıştırdığında lockfile güncellenecektir; sonucu test edip ayrıca commit etmen önerilir.

## 9. Android sürüm bilgisi

Yeni kaynak kod:

```text
versionCode: 2
versionName: 1.1.0
```

olarak hazırlanmıştır. Böylece telefondaki önceki APK'nın üzerine güncelleme kurulabilir.

## 10. Android 13+ bildirim izni

Capacitor Push Notifications üzerinden uygulama kullanıcıdan açıkça izin ister. Uygulama açılır açılmaz otomatik permission popup göstermiyoruz.

Kullanıcı:

```text
Bildirim Yönetimi
→ Cihazlar/Firebase
→ Bu Cihazı Kaydet
```

dediğinde:

1. Android notification permission kontrol edilir.
2. Gerekirse sistem izin ekranı açılır.
3. FCM registration başlatılır.
4. Capacitor registration token alınır.
5. Device ID + token Supabase `notification_devices` tablosuna kaydedilir.

İzin reddedilirse cihaz `GRANTED` sayılmaz ve backend o cihaza push göndermez.

## 11. Uygulama kapalıyken bildirim

Bu modül local timer değildir. Günlük saat 09:00 otomasyonu telefondaki JavaScript timer'ına bağlı değildir.

```text
Windows Server Python Service
→ Supabase outbox
→ Firebase Cloud Messaging
→ Android işletim sistemi
→ Telefon
```

Bu nedenle uygulama foreground'da olmasa da FCM notification mesajı Android tarafından gösterilebilir. Telefonun internet erişimi, Android bildirim izni, üretici battery/network politikaları ve Firebase bağlantısı yine gereklidir.

Uygulama tekrar açıldığında RightDrawer `notification_messages` tablosundan geçmiş mesajları da gösterir.

## 12. Quasar Firebase ayar ekranı

Uygulamada:

```text
Profil menüsü
→ Bildirim Yönetimi
→ Firebase
```

Alanlar:

- **FCM bildirimlerini etkinleştir** → `push_provider_settings.enabled`
- **Firebase Project ID** → `firebase_project_id`
- **Sender ID / Project Number** → `sender_id`
- **Android Package Name** → `android_package_name`
- **Web VAPID Key** → yalnız gelecekte PWA web push kullanacaksan
- **Not** → operasyon notu

Private key alanı bilerek yoktur.

## 13. Cihaz kaydı

Firebase ayarları kaydedildikten sonra gerçek Android APK'da:

```text
Bildirim Yönetimi → Bu Cihazı Kaydet
```

butonuna bas.

Başarılı kayıt sonrası Cihazlar sekmesinde şunları görmelisin:

- cihaz adı/modeli
- Android/platform
- OS versiyonu
- uygulama versiyonu
- permission durumu
- son görülme
- aktif/pasif toggle

Bir cihazı pasif yaparsan kayıt silinmez; backend o cihaza push göndermez.

## 14. Python backend bildirim dispatcher'ı

Yeni Python kaynaklarında:

```text
app/notifications/fcm.py
app/notifications/dispatcher.py
```

bulunur.

Scheduler her dakika notification dispatcher'ı maintenance işi olarak çağırır. Bu job **Shadow `SCHEDULE_SPECS` içine dahil değildir**. Dolayısıyla notification availability veya Firebase hatası model readiness hesabını değiştirmez.

Dispatcher:

1. zamanı gelen günlük otomasyonları outbox'a ekler,
2. bekleyen outbox kayıtlarını claim eder,
3. RightDrawer için `notification_messages` kaydı oluşturur,
4. aktif cihazları bulur,
5. Firebase Admin SDK ile FCM gönderir,
6. cihaz bazlı `notification_logs` kaydı oluşturur.

Firebase kurulmamışsa veya migration yoksa bu bakım katmanı engine market/model job'larını durdurmaz.

## 15. Python yeni build

Backend deploy zamanı geldiğinde Windows geliştirme/build makinesinde:

```powershell
cd InvestmentEngine-v1.2.0-mobile-ready
.\build.bat
```

veya mevcut build prosedürünü kullan.

`requirements.txt` artık `firebase-admin==7.5.0` içerir ve PyInstaller build script'i `firebase_admin` modüllerini toplar.

**30 günlük Shadow veri toplama sürerken sırf bildirim için mevcut servisi değiştirmek zorunda değilsin.** Quasar/0011 tarafını şimdi hazırlayabilir, Python backend göndericisini Shadow checkpoint sonrasında kontrollü deploy edebiliriz.

## 16. Signal bildirimleri

`decision_history` içine yalnız `action_event=true` olan yeni karar yazıldığında DB trigger `SIGNAL_CREATED` outbox kaydı üretir.

Bu Telegram'ın yerine geçmez:

```text
Telegram → mevcut Python kanalın
FCM       → mobil Quasar uygulaması
RightDrawer → uygulama içi geçmiş
```

üçü bağımsızdır.

Eski sinyallerin deploy sırasında topluca telefona yağmaması için dispatcher 6 saatten eski SIGNAL_CREATED outbox kayıtlarını göndermez/skip eder.

## 17. Test sırası

Önerilen test:

1. `0011` migration uygula.
2. Quasar repo'da `yarn install`.
3. `google-services.json` doğru dizine kopyala.
4. `npx cap sync android`.
5. APK build et ve kur.
6. Supabase gerçek kullanıcıyla login ol.
7. Bildirim Yönetimi > Firebase metadata gir ve kaydet.
8. Bu Cihazı Kaydet'e bas, Android iznini ver.
9. `notification_devices` satırını doğrula.
10. Günlük test otomasyonu için geçici olarak yakın bir saat seç.
11. Backend yeni sürüm deploy edildikten sonra outbox → message → log zincirini doğrula.
12. Telefon ekranı kapalı/uygulama background'da iken FCM teslimini test et.

## 18. Sorun giderme

### Cihaz kaydolmuyor

- APK native Capacitor build mi?
- `google-services.json` doğru app dizininde mi?
- package name birebir `tr.rosayazilim.yatirimdashboard` mı?
- Android notification permission GRANTED mı?
- `npx cap sync android` son Firebase/Capacitor değişikliğinden sonra çalıştırıldı mı?

### RightDrawer mesaj geliyor ama push gelmiyor

- Python yeni build deploy edildi mi?
- `FIREBASE_SERVICE_ACCOUNT_PATH` doğru mu?
- provider `enabled=true` mi?
- cihaz `is_active=true`, `permission_status=GRANTED` mı?
- `notification_logs.error_message` ne diyor?

### Push geliyor ama RightDrawer boş

- kullanıcı doğru Supabase Auth hesabında mı?
- `notification_messages` RLS altında ilgili user_id satırı var mı?
- uygulama sync/refresh yapıldı mı?

### Saat yanlış

Şablonda `timezone=Europe/Istanbul`, `schedule_time=09:00` kontrol et. Backend trigger UTC saatini doğrudan sabitlemez; template timezone'ına göre hesaplar.

## 19. iOS ileride eklenecekse

Bu tur Android odaklıdır. iOS için ayrıca:

- Firebase'e iOS app kaydı,
- APNs Authentication Key/Certificate,
- Xcode Push Notifications capability,
- Background Modes / Remote notifications,
- `GoogleService-Info.plist`

gerekecektir. Aynı Supabase cihaz/şablon/log modeli kullanılabilir.

## 20. Production kabul kriterleri

Bildirim modülünü production-ready kabul etmeden önce:

- Firebase private key APK/repo/Supabase user tables içinde olmamalı.
- 0011 migration başarılı olmalı.
- RLS test edilmeli.
- gerçek Android cihaz kaydı başarılı olmalı.
- foreground/background/uygulama kapalı FCM senaryoları test edilmeli.
- günlük otomasyon timezone doğrulaması yapılmalı.
- SIGNAL_CREATED yalnız gerçek `action_event=true` kararında tetiklenmeli.
- notification dispatcher hatası Investment Engine health/readiness'i etkilememeli.
- 0010 observability migration'ı ayrı rollout olarak kalmalı.
