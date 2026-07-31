# BTC / ETH / URA 10 Yıllık Yatırım — Proje Memory Bank

Son güncelleme: 01 Ağustos 2026

Bu belge `BTC_ETH_URA_10YIL` projesinin kalıcı bağlamıdır. Yeni ChatGPT/Codex oturumları projenin amacı, Python Investment Engine'in hangi aşamalardan geçtiği, hangi fikirlerin denenip neden değiştirildiği, bugün hangi kararların bağlayıcı olduğu, Shadow görev takviminin hangi aşamada bulunduğu ve Quasar uygulamasının güncel ürün sınırlarını buradan öğrenir.

Bu belge tek başına normatif sinyal sözleşmesi değildir. Dönüşüm motorunun gerçek kod davranışı için `SIGNAL_ENGINE_DECISION_CONTRACT.md`, son aktif çalışma için `SESSION_HANDOFF.md`, Shadow kontrolleri için `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md` ve `SHADOW_CHECKPOINT_LOG.md` birlikte okunur.

## 1. Proje amacı ve yatırım çerçevesi

- Gerçek yatırım başlangıcı: **25.07.2026**.
- Plan süresi: **120 ay / 10 yıl**, hedef bitiş **25.07.2036**.
- Yatırım varlıkları: spot **BTC**, **ETH**, **URA**.
- Nakit bacakları: **USD** ve **TRY**. İlk sürümde USDT ayrı varlık olarak modellenmez.
- Kullanıcı aylık sermaye girişini, alımı, satışı, dönüşümü ve sermaye çıkışını kendisi yapar ve Quasar'a kaydeder.
- Python motoru otomatik alım/satım emri vermez; global piyasa kararı ve karar desteği üretir.
- Aylık DCA ana disiplin olmaya devam eder; gerçek bütçe, fiyat, miktar ve dağılım her ay farklı olabilir.
- Dönüşüm motorunun amacı sık işlem üretmek değil, BTC↔ETH ve USD↔URA göreli rejim değişimlerini ölçülebilir ve audit edilebilir biçimde değerlendirmektir.

## 2. Bağlayıcı kaynak sırası

Bir konuda kaynaklar çelişirse yeni oturum aşağıdaki sırayı izler ve çelişkiyi kullanıcıya açıkça bildirir:

1. Gerçek yayımlanmış kod, migration ve runtime çıktısı.
2. `SIGNAL_ENGINE_DECISION_CONTRACT.md` içindeki `RELEASED` maddeler.
3. Kullanıcının kesinleştirdiği `APPROVED` ürün/mimari kararları.
4. Bu memory bank.
5. `SESSION_HANDOFF.md` içindeki aktif çalışma bilgisi.
6. `PROPOSED` ve `OPEN` maddeler.

Durum etiketleri:

- `RELEASED`: yayımlanmış kod/veritabanı davranışı.
- `APPROVED`: kullanıcı tarafından kesinleştirilmiş karar; kodu ayrıca doğrulanır.
- `PROPOSED`: öneri; kullanıcı onayı olmadan uygulanmaz.
- `OPEN`: kanıt veya karar bekler.

## 3. İki repo ve sorumluluk sınırı

| Katman               | Repo / teknoloji                                                          | Sorumluluk                                                                                                                                       | Bilinçli sınır                                                     |
| -------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Investment Engine    | `nevzataksoy/Yatirim10YilUygulamasi`, Python / Windows Service            | Piyasa, FX, makro, derivatives, URA holdings/breadth ve event toplama; feature/factor/regime/decision; scheduler, validation, health ve Telegram | Portföy bakiyesi/seçili hesap okumaz; otomatik emir göndermez      |
| Veri ve güvenlik     | Supabase / PostgreSQL                                                     | Auth, RLS, portföy ledger'ı, motor tabloları, public read-only snapshot'lar                                                                      | Frontend'e DB password, service-role veya provider secret verilmez |
| Kullanıcı uygulaması | `nevzataksoy/tr.rosayazilim.yatirimdashboard`, Quasar / Pinia / Capacitor | Login, çoklu portföy hesabı, işlem girişi, append-only düzeltme, maliyet/KZ, raporlar ve motor görünümü                                          | Model eşiği/ağırlığı değiştirmez; Telegram secret yönetmez         |

Google Sheets ve Apps Script production mimarisinden çıkarılmıştır.

## 4. İlk fikirden güncel mimariye geçiş

### 4.1 Google Sheets dönemi

İlk çalışma, 2020–2026 örnek DCA hesabı ve ETH/BTC oranına bağlı `%50` dönüşüm senaryoları üzerinden başladı. Sonra BTC, ETH ve URA için manuel alım, satış/çıkış, maliyet, USD/TRY ve dashboard sekmeleri tasarlandı.

Bu yaklaşım prototip ve ihtiyaç keşfi için yararlı oldu; ancak 10 yıllık veri bütünlüğü, kullanıcı oturumu, audit, mobil kullanım, scheduler ve güvenli secret yönetimi için yeterli değildi.

### 4.2 Kesinleşen mimari dönüşüm

- Google Sheets production akışından çıkarıldı.
- Supabase PostgreSQL ana veri katmanı oldu.
- Python Engine Windows Server 2019 üzerinde 7/24 servis olarak konumlandı.
- Quasar + Capacitor mobil/SPA istemci olarak seçildi.
- E-posta yerine Telegram bildirimi seçildi.
- Sinyal yalnız 36 aylık ETH/BTC percentile kuralından çıkarılıp çoklu factor/regime/quality/risk modeline dönüştürüldü.

## 5. Python Investment Engine sürüm kilometre taşları

### v1.0.0 — ilk çalışan prototip

- Windows Engine, Supabase, Telegram ve ilk snapshot akışı kuruldu.
- BTC/ETH/URA veri toplama ve karar fikri ilk kez uçtan uca çalıştı.
- Bu sürüm production güvenilirliği ve model doğrulaması açısından başlangıç seviyesindeydi.

### v1.1.1 — mobile-ready ve gerçek smoke-test düzeltmeleri

- Google Sheets production zincirinden çıkarıldı; Quasar + Supabase hedefi kesinleşti.
- Tek PyInstaller EXE, Windows Service, Inno Setup, güvenli settings/rosalock akışı kuruldu.
- Settings dosyası DPAPI `LocalMachine`, atomik yazım ve Program Files ACL yaklaşımıyla tasarlandı.
- Numeric feature alanına yanlışlıkla yazılan `as_of` tarihi düzeltildi.
- Alpha Vantage pacing/retry eklendi.
- Deribit timeout davranışı ve inverse perpetual OI birimi düzeltildi.
- Windowed EXE için CLI çıktısı görünür hale getirildi.

### v1.1.2 — freshness ve provider sürekliliği

- FRED verisinin yanlış sıralama nedeniyle eski observation'ı güncel sayması düzeltildi.
- Makro quality observation-date freshness'e bağlandı.
- Deribit başarısız olduğunda BTC ve ETH birlikte, atomik olarak OKX fallback'e geçer hale geldi; provider karışımı yasaklandı.

### v1.1.3 — veri semantiği, URA ve realtime hardening

- Eksik URA factor'larına verilen sahte `quality=50` kaldırıldı; veri yoksa `quality=0` oldu.
- `score=0` directional agreement içinde pozitif oy olmaktan çıkarıldı.
- Resmî Global X URA full-holdings, holdings/flow proxy ve coverage-aware breadth eklendi.
- SEC EDGAR filing monitörü eklendi; semantic classifier olmadığı için bullish/bearish yön uydurulmadı.
- Gerçek `ACTION` üretmeden Coinbase realtime smoke testi eklendi.
- Decision provenance, weekly bakım ve 5/20/60 seans realized-performance audit eklendi.

### v1.1.4 — dependency ve coverage hardening

- Daily crypto job stale/missing derivatives için karar öncesi best-effort refresh yapar hale geldi.
- SEC quality entity sayısı yerine eşleşen fon ağırlığı coverage'ına bağlandı ve scope cap uygulandı.
- CLI wrapper log replay sorunları düzeltildi.

### v1.2.0 — model validation ve Shadow milestone

- Model version provenance eklendi.
- ETH/BTC için leakage-resistant directional-core replay eklendi.
- Train/holdout exploratory edge-threshold raporu eklendi; otomatik apply açıkça yasaklandı.
- Shadow Readiness ve public validation snapshot yüzeyi eklendi.
- URA full point-in-time replay, yeterli holdings/breadth/event history oluşana kadar bilinçli `NOT_READY` bırakıldı.
- Monthly audit realized sonuçlar, validation ve readiness'i birlikte günceller hale geldi.

**Nihai yorum:** v1.2.0 daha fazla sinyal üretmek için değil; veri semantiği düzeltilmiş motoru versioned, ölçülebilir, audit edilebilir ve production-benzeri Shadow ortamında değerlendirilebilir hale getirmek için oluşturuldu.

**Güncel yayımlanmış/deploy edilmiş model sürümü v1.2.0'dır.** v1.2.1/v1.3 ancak kod, test, build, deployment ve gerekiyorsa yeni Shadow Epoch ile ayrıca doğrulanır; plan veya klasör adı tek başına release sayılmaz.

## 6. Denenen yaklaşım ve kesinleşen sonuçlar

| Konu                 | Denenen/ilk yaklaşım                       | Kesinleşen sonuç                                                             |
| -------------------- | ------------------------------------------ | ---------------------------------------------------------------------------- |
| Kullanıcı uygulaması | Google Sheets + Apps Script                | Quasar + Supabase; Sheets production dışı                                    |
| Sinyal               | 36 aylık ratio/percentile odaklı tek kural | Çoklu factor + regime + quality + veto + risk + persistent state             |
| Crypto fiyat         | Binance dahil alternatifler                | Coinbase günlük spot ana kaynak; güvenilir fallback yaklaşımı                |
| Derivatives          | Deribit tek başına                         | Deribit erişilemezse atomik OKX fallback                                     |
| Eksik veri           | Nötr/sahte quality                         | `quality=0`; kaynak yokken score/quality uydurulmaz                          |
| Model ayarı          | Backtest sonucuna göre otomatik threshold  | Validation yalnız raporlar; threshold/weight/mode otomatik değişmez          |
| Bildirim             | E-posta                                    | Tek Telegram botu + tek Chat ID; secret yalnız Python ayarlarında            |
| Execution            | LIVE/realtime kavramlarının karışması      | LIVE karar/bildirim modu; Realtime Execution ayrı; otomatik emir yok         |
| Portföy              | Tek defter                                 | Tek Auth kullanıcısı altında çoklu portföy hesabı                            |
| İşlem düzeltme       | Eski kaydı update/delete                   | Append-only revision/cancellation; rapor yalnız etkin son revizyonu kullanır |
| Nakit                | USDT dahil etme fikri                      | İlk sürümde yalnız TRY/USD; USDT eklenmez                                    |
| Muhasebe             | Ekran para birimine göre hesap             | İç ledger USD normalize; display asset yalnız sunum                          |

## 7. Güncel Python deployment gerçeği

- Sunucu: Windows Server 2019, 7/24.
- Servis: `RosaInvestmentEngine`, Automatic, Local System.
- Güncel doğrulanmış durum: `STATE : 4 RUNNING`, exit code `0`.
- Engine Mode: `SHADOW`.
- Realtime Execution: `OFF`.
- Supabase bağlantısı ve private/public snapshot zinciri çalışır durumda.
- Crypto history backfill: Coinbase üzerinden **2500 ortak gün**, başarılı.
- Model validation: **1381 observation**, core `OK`, Shadow `NOT_READY`.
- İlk calibration raporunda production eşiği `70` için sinyal yoktur; düşük eşik adaylarında sinyal sayısı sınırlıdır. Sonuç `LIMITED_SIGNAL_COUNT`/exploratory'dir ve hiçbir threshold değişikliği yapılmamıştır.
- URA full PIT replay yeterli tarihçe olmadığı için `NOT_READY` kalabilir.

### Scheduler — Europe/Istanbul

```text
xx:05                  hourly derivatives
00:15/06:15/12:15/18:15 macro
xx:35                  SEC event
02:40                  daily URA
05:20                  daily crypto
16:30 Mon–Fri          TCMB FX
08:00 Saturday         weekly
09:00 month day 1      monthly audit
```

## 8. Shadow görev takvimi ve doğrulanmış sonuçlar

Canonical takvim: `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`.
Kümülatif sonuçlar: `SHADOW_CHECKPOINT_LOG.md`.

### Görev 1 — 31.07.2026 ilk otomatik günlük döngü: `PASS`

- Servis `RUNNING`.
- Hourly, macro, SEC event, daily URA ve daily crypto scheduler tarafından otomatik çalıştı.
- ETH/BTC: `BTC→ETH`, edge `35.640`, confidence `46.250`, quality `90.450`, status `WAIT`.
- URA/USD: `URA→USD`, edge `33.990`, confidence `36.170`, quality `70.400`, status `NO_ACTION_DATA`.
- Deribit bağlantısı timeout verdi; OKX fallback ile derivatives job `OK` kaldı.
- Macro quality `97.5`; stale/missing yok, `DTWEXBGS` degraded.
- SEC event coverage `%14.04` olduğu için `DEGRADED`; job çökmemiştir.
- Sonuç: motor veri topladı, yetersiz koşulda aksiyonu engelledi ve scheduler akışına devam etti. Threshold/weight/mode değişikliği gerekmez.

### Görev 2 — 31.07.2026 TCMB/FX: `PASS`

- Planlanan 16:30 TRT işi 13:30 UTC'de başladı.
- Data date `31.07.2026`, USD/TRY `47.4305`.
- `FX=OK`, job `OK`, süre yaklaşık `2.48` saniye.
- `market_snapshot`, `engine_health_snapshot` ve `system.job_runs` uyumlu.

### Sıradaki görevler

- Görev 3: **01.08.2026 09:30 TRT** — weekly + monthly audit scheduler kontrolü.
- Görev 4: **07.08.2026 10:30 TRT** — 7 günlük ilk güvenilirlik checkpoint'i.
- Görev 5: **14.08.2026 10:30 TRT** — 14 günlük stabilite.
- Görev 6: **20.08.2026 10:30 TRT** — URA 20 günlük quality değerlendirmesi.
- Görev 7: **29.08.2026 10:30 TRT** — 30 günlük Shadow Graduation Review.

Sonucu paylaşılmamış görev başarılı sayılmaz. Normal durumda servis durdurulmaz ve aynı job art arda manuel çalıştırılmaz.

## 9. Görevlerden Python revizyonuna geçiş kuralı

| Kanıt aşaması | İzin verilen revizyon                                                                                                                             | Yasak                                                 |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Görev 1–3     | Gerçek scheduler/provider/freshness/snapshot/health sapmasını düzeltmek                                                                           | Model threshold/weight değiştirmek                    |
| Görev 4       | Açık Shadow Epoch, run-kind ayrımı, expected/actual job sayısı, OK/completed rate, edge/status diagnostics, mevcut K1/K2 karakterizasyon testleri | Sinyal davranışını sessizce değiştirmek               |
| Görev 5–6     | ETH/BTC ve URA factor quality/freshness katkılarını ayrıştırmak, walk-forward ve strict PIT katmanını güçlendirmek                                | Quality yükselsin diye sentetik score/history eklemek |
| Görev 7       | PIT, walk-forward, monthly realized, Shadow dağılımları ve scheduler güvenilirliğini birlikte review etmek                                        | Otomatik LIVE geçişi                                  |

Model factor, weight, threshold, K1/K2, reversal, cooldown veya action-size otoritesi değişirse yeni model version ve yeni Shadow Epoch gerekir. Eski 30 günlük kanıt otomatik devredilmez.

## 10. Sinyal motorunun bugünkü özeti

Normatif ayrıntı `SIGNAL_ENGINE_DECISION_CONTRACT.md` içindedir.

- Sistemler: `ETH/BTC`, `URA/USD`.
- Minimum: quality `80`, edge `70`, confidence `70`.
- Strong: edge/confidence `80/80`.
- Status önceliği: `NO_ACTION_DATA → BLOCKED_EVENT → BLOCKED_LATE → ACTION → WATCH → WAIT` koşullarıyla değerlendirilir.
- Volatilite yön oyu değil, risk/sizing girdisidir.
- K1/K2 persistent state ve maksimum `%50` cumulative rejim mevcut.
- K2 farklı gün + strong `80/80` ister; released kodda 5 karar seansı şartı yoktur.
- Karşı-yön qualified `ACTION` released production state'ini hemen yeni K1'e çevirebilir.
- PIT replay production K1/K2 state machine'ini birebir çalıştırmaz.

### Onaylanmamış öneriler

Aşağıdakiler `PROPOSED`/`OPEN` kalır:

1. K2 ve her yeni kademe arasında en az 5 karar seansı.
2. Ters yön için iki ardışık qualified kapanış.
3. Production ve replay için tek versioned state machine.
4. Python `action_size` model önerisi + Quasar maksimum kullanıcı limiti; uygulanacak öneri `min(...)`.

Kullanıcı açıkça onaylamadan kodlanmaz.

## 11. Quasar ürün ve veri sözleşmesi

- Paket/proje: `tr.rosayazilim.yatirimdashboard`.
- Vue 3 + Quasar, `<script setup>`, Pinia, Supabase ve SecureLS.
- Tek Auth kullanıcısı altında birden çok portföy hesabı bulunabilir.
- Dashboard, Portföy, İşlemler, Raporlar ve tüm girişler seçili `account_id` bazlıdır.
- Sinyaller, market, validation ve engine health globaldir; hesap bazlı değildir.
- Seçili hesap ve display asset SecureLS destekli persistence ile korunur.
- Bütün proje select standardı `AppPopupSelect.vue` bileşenidir; tekli/çoklu seçim, arama/filtreleme ve mobil/desktop popup düzenini destekler.
- İşlem düzeltme/iptal append-only revision satırıyla yapılır; eski kayıt korunur.
- Revision, sonraki bakiye zincirini bozuyorsa reddedilir.
- `0008_portfolio_audit_hardening.sql` ve `0009_portfolio_self_service_reset.sql` Supabase'e uygulanmıştır.
- Seçili portföy geçmişi kontrollü RPC ile sıfırlanabilir; profil, diğer hesaplar, ayarlar ve motor verileri korunur.
- Alım, satış, dönüşüm ve sermaye hareketlerinde önce/işlem/sonra bakiye bağlamı gösterilir.
- İç muhasebe USD normalize; display asset `USD/TRY/BTC/ETH` sunum katmanıdır.
- Supabase bağlantı ayarları hem Login hem `/settings` giriş noktasında yerel ayar şifresiyle korunur.
- İlk erişimde en az 6 karakterli ayar şifresi oluşturulur; bağlantı alanları her yeniden açıldığında şifre tekrar doğrulanır.
- Hatalı denemeler kalıcı kilit oluşturmaz; bağlantı penceresi kapanınca URL/key taslağı bellek state'inden temizlenir.

## 12. Portföy işlem semantiği

- `OPENING`: takibe başlanırken mevcut varlık/maliyet.
- `CASH_IN`: dış dünyadan yatırım hesabına yeni sermaye.
- `BUY`: mevcut TRY/USD nakitle BTC/ETH/URA alımı.
- `CONVERSION`: portföy içindeki varlıkların dönüşümü.
- `SELL`: yatırım varlığını TRY/USD portföy nakdine çevirme.
- `CASH_OUT`: portföy nakdini yatırım sisteminden dışarı çekme.

`BUY`, `CONVERSION` ve `SELL` yeni sermaye değildir. Yatırım bütçesi yalnız `CASH_IN`, sermaye çıkışı yalnız `CASH_OUT` üzerinden raporlanır.

## 13. Güvenlik ve secret kuralları

- Supabase DB password, service-role key, FRED/Alpha Vantage key, Telegram token/Chat ID repo veya bağlam belgelerine yazılmaz.
- Quasar yalnız Project URL ve publishable/anon key kullanır.
- Ayar şifresinin açık değeri saklanmaz; rastgele salt ile `PBKDF2-SHA256` doğrulayıcısı türetilip SecureLS/AES içindeki localStorage kaydında tutulur.
- Yerel ayar şifresi cihaz içi yanlışlıkla erişimi azaltır; native keychain veya sunucu tarafı secret kasası değildir.
- Python settings/rosalock uygulama klasöründe şifreli/hashed ve atomik tutulur.
- SecureLS frontend cache korumasıdır; XSS veya native secure enclave yerine geçmez.
- Capacitor aşamasında refresh/session secret native secure storage'a taşınmalıdır.

## 14. Git ve oturumlar arası çalışma protokolü

Kullanıcının tercih ettiği dönüşümlü çalışma şekli:

1. Asistan her değişiklikten önce remote branch'in güncel dosyalarını/HEAD'ini yeniden okur; önceki konuşma varsayımıyla yazmaz.
2. Asistan değişikliği feature/agent branch'e push eder.
3. Kullanıcı `git pull` yapar, yerel testleri/manuel girişleri tamamlar.
4. Kullanıcının ürettiği dosya değişikliği varsa commit+push eder.
5. Asistan sonraki aksiyondan önce remote'u yeniden okur ve ancak sonra yeni commit/push yapar.
6. Aynı branch üzerinde eşzamanlı yazma yapılmaz.
7. Git ayrışması/çakışması olduğunda kullanıcıya bir seferde yalnız bir komut verilir; çıktı görüldükten sonra sonraki adıma geçilir.
8. Draft PR'lar test döngüsü tamamlanmadan merge edilmez.

## 15. Yeni oturum çalışma protokolü

1. Repo kökündeki `CHATGPT_PROJECT_START_HERE.md` dosyasını oku.
2. Bu memory bank'i tamamen oku.
3. `SIGNAL_ENGINE_DECISION_CONTRACT.md` ve `SESSION_HANDOFF.md` dosyalarını oku.
4. Python/Shadow işi varsa görev takvimi ve checkpoint logunu oku.
5. Aktif branch, son commit ve çalışma ağacını doğrula; kullanıcı değişikliklerinin üzerine yazma.
6. Değiştirilecek katmanın gerçek kodunu ve ilgili teknik belgeyi birlikte incele.
7. `RELEASED/APPROVED/PROPOSED/OPEN` ayrımını koru.
8. Test sonucundan otomatik threshold/weight/mode/LIVE değişikliği yapma.
9. Proje durumu değiştiyse handoff'u; kalıcı karar değiştiyse memory bank veya contract'ı aynı turda güncelle.
10. Ortak bağlam belgelerini iki repoda senkron tut.

## 16. En kısa devir özeti

```text
Amaç: 25.07.2026'dan başlayan 120 aylık BTC/ETH/URA yatırımını güvenli biçimde izlemek.
Python: v1.2.0, Windows Service, global/portföyden bağımsız karar motoru, SHADOW, Realtime OFF.
Quasar: tek kullanıcı, çoklu portföy, gerçek işlemler ve raporlama seçili hesap bazlı.
Doğrulama: Görev 1 ve Görev 2 PASS; sıradaki Görev 3, 01.08.2026 09:30 TRT.
Kural: Görevler kanıt toplar; threshold/weight/LIVE otomatik değişmez.
Kritik açık: production/replay K1-K2 parity, reversal/cooldown ve Python–Quasar yüzde otoritesi.
```
