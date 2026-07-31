# BTC / ETH / URA 10 Yıllık Yatırım — Proje Memory Bank

Son güncelleme: 31 Temmuz 2026

Bu belge BTC_ETH_URA_10YIL projesinin kalıcı bağlamıdır. Yeni ChatGPT/Codex oturumları projenin amacını, v1.2.0'ın neden oluştuğunu, kesinleşmiş kararları, doğrulanmış görevleri ve iki repo arasındaki sınırı buradan öğrenir.

Bu belge tek başına sinyal motorunun normatif ayrıntısı değildir. Dönüşüm karar mantığında mutlaka `SIGNAL_ENGINE_DECISION_CONTRACT.md`, aktif çalışma durumunda `SESSION_HANDOFF.md` birlikte okunur.

## 1. Proje amacı ve yatırım çerçevesi

- Gerçek yatırım başlangıcı: **25.07.2026**.
- Plan süresi: **120 ay / 10 yıl**, hedef bitiş **25.07.2036**.
- Varlıklar: spot **BTC**, **ETH**, **URA**; nakit bacakları **USD** ve **TRY**.
- Kullanıcı aylık gerçek sermaye girişini, alımları, satışları, dönüşümleri ve çıkışları manuel kaydeder.
- Başlangıç DCA fikri aylık tek alım ve BTC/ETH/URA dağılımıdır; gerçek işlem, bütçe ve miktar her ay farklı olabilir.
- Dönüşüm motorunun amacı her gün işlem üretmek değil; göreli trend/rejim değişiminde BTC↔ETH ve USD↔URA için kanıtlanabilir karar desteği üretmektir.
- Otomatik emir yoktur. Python karar/sinyal üretir; kullanıcı işlemi yapar ve Quasar'a kaydeder.

## 2. İki repo ve sorumluluk sınırı

| Katman               | Repo / teknoloji                                                      | Sorumluluk                                                                                                                         | Bilinçli sınır                                                   |
| -------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Investment Engine    | `nevzataksoy/Yatirim10YilUygulamasi`, Python/Windows Service          | Piyasa, FX, makro, holdings, derivatives ve event toplama; feature/factor/regime/decision; validation, scheduler, health, Telegram | Portföy bakiyesi/seçili hesap okumaz; emir göndermez             |
| Veri ve güvenlik     | Supabase/PostgreSQL                                                   | Auth, RLS, portföy ledger'ı, motor tabloları ve read-only public snapshot'lar                                                      | Frontend'e DB password, service-role veya provider secret vermez |
| Kullanıcı uygulaması | `nevzataksoy/tr.rosayazilim.yatirimdashboard`, Quasar/Pinia/Capacitor | Login, hesap seçimi, veri girişleri, ledger, maliyet, kâr/zarar, raporlar ve motor görünümü                                        | Model ağırlığı/eşiği değiştirmez; Telegram secret yönetmez       |

Google Sheets ve Apps Script production mimarisinden çıkarılmıştır.

## 3. v1.2.0 nasıl ortaya çıktı?

v1.2.0 bir kerede tasarlanmış nihai sinyal modeli değildir. Gerçek Windows/Supabase testlerinde bulunan sorunların aşamalı olarak kapatılmasıyla oluşmuştur.

### v1.0.0 — prototip

- İlk Windows Engine, Supabase, Telegram ve Google Sheets snapshot prototipi.
- BTC/ETH/URA veri toplama ve karar fikri ilk kez çalışır hale getirildi.

### v1.1.1 — mobile-ready ve ilk smoke düzeltmeleri

- Google Sheets production akışından çıkarıldı; Quasar + Supabase hedefi kesinleşti.
- Tek PyInstaller EXE, Windows Service, güvenli settings/rosalock ve installer akışı kuruldu.
- `as_of` tarihinin numeric feature kolonuna yazılması düzeltildi.
- Alpha Vantage pacing/retry eklendi.
- Deribit timeout degrade davranışı ve inverse perpetual OI birimi düzeltildi.
- CLI çıktısı Windows windowed EXE için görünür hale getirildi.

### v1.1.2 — freshness ve provider sürekliliği

- FRED'in eski tarihleri latest veri sanmasına yol açan sıralama düzeltildi.
- Makro quality artık observation-date freshness'e bağlandı.
- Deribit erişimi başarısızsa aynı BTC+ETH çifti için atomik OKX fallback eklendi; provider karışımı yasaklandı.

### v1.1.3 — data semantics, URA ve realtime hardening

- Eksik URA factor'larına verilen sahte `quality=50` kaldırıldı; eksik veri `quality=0` oldu.
- `score=0` directional agreement içinde pozitif oy olmaktan çıkarıldı.
- Resmî Global X URA full-holdings, holdings/flow proxy ve coverage-aware breadth eklendi.
- SEC filing monitörü eklendi; semantic classifier olmadığı için filing yönü uydurulmadı.
- Gerçek ACTION üretmeden Coinbase realtime smoke testi eklendi.
- Decision provenance, weekly bakım ve 5/20/60 seans monthly realized audit eklendi.

### v1.1.4 — dependency ve coverage hardening

- Crypto job stale/missing derivatives için karar öncesi best-effort refresh yapar hale geldi.
- SEC quality entity sayısı yerine eşleşen fon ağırlığı coverage'ına bağlandı ve cap uygulandı.
- CLI wrapper log replay düzeltildi.

### v1.2.0 — model validation milestone

- Model version provenance eklendi.
- ETH/BTC leakage-resistant directional-core PIT replay eklendi.
- Train/holdout exploratory edge-threshold raporu eklendi; otomatik apply yasaklandı.
- Shadow Readiness ve public validation snapshot yüzeyi eklendi.
- URA full PIT replay, gerçek point-in-time history birikene kadar bilinçli `NOT_READY` bırakıldı.
- Monthly audit realized sonuçlarla birlikte validation/readiness çalıştırır hale geldi.

**Sonuç:** v1.2.0'ın ana amacı daha fazla `ACTION` üretmek değil; veri semantiği düzeltilmiş motorun üretim-benzeri Shadow ortamında ölçülebilir, audit edilebilir ve versioned hale gelmesidir.

## 4. Kesinleşmiş kullanıcı ve portföy modeli

- Sistem **tek kullanıcıya** yöneliktir; çoklu kullanıcı/SaaS hedefi terk edilmiştir.
- Aynı Supabase Auth kullanıcısı altında **birden çok portföy hesabı** bulunabilir.
- Amaç kullanıcının kendisi, eşi ve çocuğu için ayrı işlem defterleri tutabilmesidir.
- Portföylerin strateji ayarları kullanıcı seviyesinde ortaktır; `investment_account_settings` şu aşamada oluşturulmaz.
- Dashboard, Portföy, İşlemler, Raporlar ve tüm işlem girişleri seçili hesaba göre çalışır.
- Sinyaller, market snapshot, model validation ve engine health portföyden bağımsızdır.
- Seçili hesap Pinia persistence + SecureLS/AES ile localStorage'da tutulur. Bu cihaz cache korumasıdır; native keychain değildir.
- Display para birimi de yerelde korunur; muhasebe/ledger gerçeğini değiştirmez.

## 5. Portföy veri ve audit sözleşmesi

- `public.investment_accounts`: kullanıcının portföy çalışma alanları.
- `public.portfolio_transactions`: her satır zorunlu `account_id` taşır.
- `public.user_investment_settings`: kullanıcı seviyesinde ortak plan ve dönüşüm limitleri.
- `public.portfolio_positions`: etkin revizyon zincirlerinden hesaplanan hesap bazlı miktarlar.
- İşlemler append-only'dir; eski satır düzenlenmez/silinmez.
- Düzeltme ve iptal yeni revizyon satırıyla yapılır; rapor yalnız etkin son revizyonu kullanır.
- Kullanıcı kontrollü sıfırlama yalnız seçili hesabın işlem/revizyon satırlarını `reset_portfolio_transaction_history` RPC'siyle siler.
- Profil, diğer hesaplar, ayarlar ve motor verileri sıfırlamada korunur.

31.07.2026 tarihinde aşağıdaki migration'lar Supabase SQL Editor'de başarıyla uygulanmıştır:

- `0008_portfolio_audit_hardening.sql`
- `0009_portfolio_self_service_reset.sql`

Yeni migration `0010` veya sonraki numarayla eklenir. Uygulanmış migration dosyaları geriye dönük değiştirilmez. `migrations/` ve `supabase-migrations/` kopyaları birebir eşleşmelidir.

## 6. Quasar'da doğrulanan ürün kararları

- Login/register/session Supabase Auth üzerinden çalışır.
- Portföy Hesaplarım sayfasından birden çok hesap oluşturulup seçilebilir.
- Right drawer profil alanında `AppPopupSelect` ile global çalışma hesabı seçilir.
- Bütün select akışlarında proje standardı `AppPopupSelect.vue` bileşenidir; tekli/çoklu seçim ve filtreleme ihtiyaçlarını desteklemelidir.
- İşlem düzenleme append-only revision dialog üzerinden yapılır; eski kayıt silinmez.
- `/signals` statü pill'i kart üst kenarına yapışmaması için üst boşlukla gösterilir.
- Dönüşüm formu gerçek borsa işlem miktarını manuel kaydeder; Python otomatik işlem yapmaz.

## 7. Telegram kararı

- Tek Telegram botu ve tek Chat ID kullanılır.
- Bot token ve Chat ID yalnız Python ayar penceresinden girilir; Quasar'a veya repo belgelerine yazılmaz.
- Bildirim global varlık sinyaline aittir; portföy hesabına ait değildir.
- Shadow modunda normal action Telegram bildirimi gönderilmez.
- LIVE ve Realtime Execution birbirinden ayrıdır; ikisi de otomatik emir yetkisi vermez.

## 8. Dönüşüm sinyali motorunun çekirdeği

Normatif ayrıntı: `SIGNAL_ENGINE_DECISION_CONTRACT.md`.

Kısa özet:

- Sistemler: `ETH/BTC` ve `URA/USD`.
- Faktörler value, trend, momentum, flow/derivatives/macro/event ve URA için holdings/breadth katmanlarından oluşur.
- EMA, MACD, RSI ve Bollinger yaklaşımı terk edilmemiş; factor/regime modelinin teknik çekirdeğine alınmıştır.
- Minimum quality/edge/confidence: `80/70/70`; strong: `80/80`.
- Status sırası: `NO_ACTION_DATA → BLOCKED_EVENT → BLOCKED_LATE → ACTION → WATCH → WAIT` koşullarına göre değerlendirilir.
- v1.2.0 K1/K2 en fazla `%50` cumulative rejim kullanır; her kademe risk nedeniyle `%25`ten küçük olabilir.
- Mevcut production ters-yön `ACTION` geldiğinde rejimi hemen çevirebilir; PIT replay aynı K1/K2 state machine'ini kullanmaz.

Son iki madde çözülmüş sayılmaz. Whipsaw/reversal/cooldown ve Python–Quasar yüzde otoritesi contract içinde `PROPOSED`/`OPEN` olarak açıkça ayrılmıştır.

## 9. Python action size ile Quasar yüzdesinin bugünkü durumu

- Python `action_size`, global model önerisidir; portföy miktarı değildir.
- Quasar kullanıcı ayarlarında BTC/ETH ve URA/USD dönüşüm oranı bulunur; Python bu tabloyu okumaz.
- Quasar dönüşüm formunda kullanıcı gerçek miktarı manuel seçer/kaydeder.
- Bugün bu iki yüzdeyi otomatik birleştiren uygulanmış sözleşme yoktur.

Önceki analizde önerilen fakat henüz bağlayıcı olmayan hedef:

```text
Python action_size = model önerisi
Quasar oranı       = kullanıcı maksimum rejim limiti
Uygulanacak öneri  = min(Python önerisi, kullanıcı limitinde kalan pay)
```

Bu öneri kullanıcı tarafından ayrıca onaylanmadan kodlanmaz.

## 10. Shadow görevlerini neden oluşturduk?

Görevler yalnız “servis çalışıyor mu?” kontrolü değildir. Model davranışını değiştirmeden önce üç kanıt sınıfını ayırmak için oluşturuldu:

1. **Operasyonel kanıt:** Scheduler doğru saatte çalışıyor mu; provider, freshness, snapshot, health ve `system.job_runs` tutarlı mı?
2. **Veri/model girdisi kanıtı:** Quality zaman içinde beklenen şekilde birikiyor mu; eksik provider gerçek factor katkısını nasıl etkiliyor?
3. **Karar kanıtı:** PIT/walk-forward, Shadow karar dağılımları ve 5/20/60 seans gerçekleşen performans aynı hikâyeyi destekliyor mu?

### Görev–revizyon ilişkisi

| Aşama     | Rol                                   | Python'da yapılabilecekler                                                     |
| --------- | ------------------------------------- | ------------------------------------------------------------------------------ |
| Görev 1–3 | İlk scheduler/iş/snapshot doğrulaması | Gerçek operasyonel sapmayı düzelt; model eşiğine dokunma                       |
| Görev 4   | 7 günlük güvenilirlik                 | Shadow Epoch, run-kind ayrımı, edge/status diagnostics, readiness hardening    |
| Görev 5–6 | 14/20 günlük quality/stabilite        | ETH ve URA factor katkısı/freshness regresyon analizi; eşik değiştirme yok     |
| Görev 7   | 30 günlük graduation                  | PIT, walk-forward, monthly realized ve Shadow sonuçlarını birlikte değerlendir |

## 11. Doğrulanmış görev sonuçları

### Görev 2 — TCMB/FX otomatik işi: `BAŞARILI`

- Planlanan zaman: 31.07.2026 16:30 TRT.
- Gerçek başlangıç: 13:30:00 UTC = 16:30:00 TRT.
- TCMB veri tarihi: 31.07.2026.
- USD/TRY: `47.4305`.
- `FX=OK`, job `OK`, süre yaklaşık 2,48 saniye.
- `market_snapshot`, `engine_health_snapshot` ve `system.job_runs` tarih/kur değerleri birbiriyle uyumludur.

Görev 2 FX zincirini kanıtlar; USD/TRY dönüşüm yön motorunun doğrudan directional girdisi olmadığı için tek başına model değişikliği gerekçesi değildir.

Henüz kullanıcı tarafından sonuçları paylaşılmamış görevler başarılı kabul edilmez.

## 12. Görevlerden sonra planlanan Python revizyonu

### Görev 4 sonrasında — davranış değiştirmeyen v1.2.x adayları

- Açık Shadow Epoch başlangıcı.
- Manual/backfill/development run'larını scheduler readiness hesabından ayırma.
- Beklenen ve gerçekleşen job sayısını karşılaştırma.
- `OK rate` ile `completed rate` ayrımı.
- Edge, confidence, quality ve status bucket diagnostics.
- K1/K2 mevcut davranışını karakterize eden unit testler.

### Görev 5–6 sonrasında

- URA quality 70–79 ise fundamentals/breadth/event katkılarını ayrı inceleme.
- URA `<70` ise provider/freshness/history zincirinde regresyon arama.
- ETH/BTC quality düşüşünde spot/derivatives/macro/event freshness ayrımı.
- Quality yükselsin diye sentetik score veya sahte history eklememe.

### Görev 7 sonrasında

Birlikte incelenecek kanıtlar:

- ETH/BTC PIT directional-core replay.
- Train/holdout exploratory threshold karşılaştırması.
- 5/20/60 seans realized performance.
- Shadow edge/confidence/quality/status/direction dağılımları.
- K1/K2 action olayları ve rejim davranışı.
- Scheduler, provider ve data-quality güvenilirliği.

Model davranışı değişirse yeni model version ve yeni Shadow Epoch gerekir. v1.2.0'ın 30 günlük kanıtı değiştirilmiş modele otomatik devredilmez.

## 13. Validation ve LIVE güvenlik kapısı

- Mevcut çalışma modu: `SHADOW`.
- Realtime Execution: `OFF`.
- ETH/BTC PIT yalnız güvenilir historical price+macro directional core'u sınar; derivatives/event geçmişe taşınmaz.
- URA full PIT, holdings/breadth/event history yeterli olana kadar `NOT_READY` olabilir.
- Monthly audit gerçek `ACTION/WATCH` kararlarının 5/20/60 seans sonucunu ölçer; full PIT değildir.
- Shadow Readiness minimum 30 gün, karar günleri, median quality, job başarısı, realtime smoke yaşı ve URA history kriterlerini ölçer.
- `READY`, LIVE değildir. LIVE yalnız manuel production review sonrası seçilir.

## 14. Bilinen teknik borç ve açık kararlar

### Uygulanmış fakat güçlendirilmesi gereken

- Production ve PIT replay aynı signal-state/K1/K2 state machine'ini kullanmıyor.
- Readiness'te açık epoch/run-kind ayrımı yok.
- Job success, `DEGRADED/SKIPPED` değerlerini successful sayıyor ve beklenen run sayısını ölçmüyor.
- Release check marker kontrolleri yapıyor; K1/K2 sınırlarını kapsayan gerçek unit test paketi yok.

### Kullanıcı kararı bekleyen

- K2 için en az 5 karar seansı bekleme.
- Ters yön için iki ardışık qualified close doğrulaması.
- Python `action_size` ile Quasar kullanıcı limitinin `min(...)` sözleşmesi.

Bu üç madde önceki oturumda önerildi; henüz onaylanmış/released davranış değildir.

## 15. Bilinçli açık kapsam

- Fiziksel uranium spot/term contract/mine supply-demand fundamentals kaynağı.
- Güvenilir point-in-time crypto event/news/on-chain/ETF-flow provider'ı.
- SEC filing semantic direction classifier.
- Derivatives/event dahil full historical production replay.
- URA için yeterli PIT holdings/breadth/event history.
- Realtime trade gap REST backfill.
- Otomatik broker/exchange order routing.

Kaynak yokken score/quality uydurulmaz.

## 16. Yeni oturum çalışma protokolü

1. Repo kökündeki `CHATGPT_PROJECT_START_HERE.md` dosyasını oku.
2. Bu memory bank'i tamamen oku.
3. `SIGNAL_ENGINE_DECISION_CONTRACT.md` ve `SESSION_HANDOFF.md` dosyalarını oku.
4. `git status`, aktif branch ve son commit'i doğrula; kullanıcı değişikliklerini koru.
5. Değiştirilecek katmanın eski teknik belgesini ve gerçek kodunu birlikte incele.
6. `RELEASED`, `APPROVED`, `PROPOSED`, `OPEN` ayrımını koru.
7. Model sonucundan otomatik threshold/weight/mode değişikliği yapma.
8. Kalıcı karar/sonuç değiştiyse memory bank veya contract'ı; aktif ilerleme değiştiyse handoff'u aynı turda güncelle.
9. Ortak belgelerin iki repodaki kopyalarını eşleştir.
10. Secret değerlerini hiçbir bağlam belgesine yazma.

## 17. Yeni sohbetlerin bilmesi gereken en kısa özet

```text
Amaç: 25.07.2026'dan başlayan 120 aylık BTC/ETH/URA yatırımını güvenli biçimde takip etmek.
Python: global, portföyden bağımsız ETH/BTC ve URA/USD karar motoru; otomatik emir yok.
Quasar: tek kullanıcı, çoklu portföy; gerçek işlemler ve raporlama seçili hesap bazlı.
Şu an: v1.2.0 SHADOW, Realtime OFF; 30 günlük görev takvimi devam ediyor.
Kural: Görevler kanıt toplar; eşik/ağırlık/LIVE otomatik değişmez.
Kritik açık: production/replay K1-K2 parity, reversal/cooldown ve Python–Quasar yüzde otoritesi henüz kesinleşmedi.
```
