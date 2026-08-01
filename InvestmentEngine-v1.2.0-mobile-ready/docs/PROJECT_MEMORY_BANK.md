# BTC / ETH / URA 10 Yıllık Yatırım — Proje Memory Bank

Son güncelleme: 01 Ağustos 2026

Bu belge `BTC_ETH_URA_10YIL` projesinin kalıcı bağlamıdır. Projenin neden var olduğunu, Google Sheets fikrinden Python + Supabase + Quasar mimarisine neden geçildiğini, Investment Engine v1.2.0'a hangi gerçek smoke-test sorunları üzerinden gelindiğini, bugün hangi davranışın yayımlanmış olduğunu ve Shadow görevlerinden sonra hangi geliştirme kapılarının açılacağını anlatır.

Normatif motor davranışı için `SIGNAL_ENGINE_DECISION_CONTRACT.md`, son aktif çalışma için `SESSION_HANDOFF.md`, operasyon kanıtı için görev takvimi ve `SHADOW_CHECKPOINT_LOG.md` birlikte okunur.

## 1. Proje amacı

- Gerçek yatırım başlangıcı: **25.07.2026**.
- Süre: **120 ay / 10 yıl**; hedef bitiş **25.07.2036**.
- Spot yatırım varlıkları: **BTC, ETH, URA**.
- Nakit bacakları: **TRY ve USD**. İlk ürün sürümünde USDT ayrı varlık değildir.
- Aylık sermaye ayırma ve DCA ana disiplindir. Sinyal motoru, aylık yatırım yapılıp yapılmayacağına karar veren bir robot değildir.
- Kullanıcı gerçek sermaye girişini, alımı, satışı, dönüşümü ve sermaye çıkışını Quasar'da kendisi kaydeder.
- Python motorunun görevi, iki global göreli sistemi ölçmektir:
  - `ETH/BTC`: BTC ile ETH arasında göreli güç ve rejim değişimi.
  - `URA/USD`: USD nakit ile URA arasında göreli rejim değişimi.
- Motor sık işlem üretmek için değil; veri kalitesi, yön avantajı, güven, geç kalma, olay vetosu ve risk koşulları birlikte yeterliyse ölçülebilir bir kademe olayı üretmek için vardır.
- Otomatik borsa emri yoktur. LIVE modu bile yalnız bildirim ve isteğe bağlı execution/order-book gözlemi üretir.

## 2. Katmanların sorumluluk sınırı

| Katman                   | Sorumluluk                                                                                                                                              | Yapmadığı şey                                                      |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Python Investment Engine | Piyasa/FX/makro/derivatives/URA holdings-breadth/event verisi; feature, regime, factor, decision, signal state, validation, health, scheduler, Telegram | Kullanıcının portföy bakiyesini okumaz; işlem emri göndermez       |
| Supabase PostgreSQL      | Auth, RLS, portföy ledger'ı, motor audit tabloları, global public snapshot'lar                                                                          | Frontend'e service-role, DB password veya provider secret açmaz    |
| Quasar / Capacitor       | Login, çoklu portföy hesabı, manuel işlem girişi, append-only düzeltme/iptal, maliyet/KZ, raporlama, motor görünümü                                     | Factor weight/threshold/mode değiştirmez; Telegram secret yönetmez |

Sinyaller globaldir; Dashboard/Portföy/İşlemler/Raporlar ise seçili `account_id` bazlıdır.

## 3. İlk fikirden kalıcı mimariye geçiş

### 3.1 Google Sheets keşif dönemi

Başlangıçta 2020–2026 örnek DCA hesabı, her ayın 25'inde BTC/ETH alımı ve ETH/BTC oranına göre toplam varlığın `%50`siyle dönüşüm senaryosu incelendi. Sonra URA, USD/TRY, maliyet, alım/satım/dönüşüm ve dashboard sekmeleri eklendi.

Bu dönem ürün ihtiyacını ortaya çıkardı; ancak 10 yıllık audit, kullanıcı oturumu, çoklu hesap, güvenli secret, scheduler, provider fallback, model provenance, mobile kullanım ve append-only işlem geçmişi için Sheets yeterli değildi.

### 3.2 Kesin mimari dönüşüm

- Google Sheets ve Apps Script production zincirinden çıkarıldı.
- Supabase PostgreSQL ana veri/audit katmanı oldu.
- Python Engine Windows Server 2019 üzerinde 7/24 Windows Service olarak konumlandı.
- Quasar + Pinia + Supabase + Capacitor kullanıcı uygulaması olarak seçildi.
- E-posta yerine Telegram bildirimi seçildi.
- Basit 36 aylık oran kuralı, çoklu factor + regime + quality + veto + risk + persistent state modeline dönüştü.

## 4. Sürüm tarihçesi: v1.2.0'a neden ve nasıl gelindi?

### v1.0.0 — ilk uçtan uca prototip

Windows üzerinde veri toplama, Supabase'e yazma, ilk BTC/ETH ve URA karar zinciri, ayar ekranı ve Telegram fikri bir araya getirildi. Bu sürüm mimari prototipti; production smoke test, provider dayanıklılığı ve validation katmanı henüz olgun değildi.

### v1.1.0 — mobile-ready temel paket

Önceki memory bank bu adımı atlayıp mobile-ready kapsamını v1.1.1'e yazıyordu. Doğru sıra şudur:

- Google Sheets production akışından çıkarıldı.
- Supabase mobile backend ve Quasar hedefi kesinleşti.
- Tek PyInstaller `InvestmentEngine.exe`, Windows Service ve Inno Setup kurulumu kuruldu.
- `settings` DPAPI `LocalMachine` ile şifrelendi; `rosalock` salted PBKDF2 doğrulayıcısı ve atomik dosya yazımı kullanıldı.
- Local SQLite spool, scheduler, health ve mobile public snapshot yüzeyleri oluşturuldu.

Bu sürüm “tasarımın mobile-ready temeli”ydi; gerçek Windows/Supabase smoke testi sonraki hataları görünür yaptı.

### v1.1.1 — gerçek smoke-test hotfix'i

v1.1.0'ın ilk gerçek testlerinde dört önemli sorun bulundu:

1. `as_of=2026-07-29` metadata değeri yanlışlıkla `model.features.value` numeric kolonuna yazılmaya çalışıyor, zincir `features → regimes → factor_scores → decisions` başlamadan kırılıyordu.
2. Alpha Vantage'ın daily/weekly/monthly URA çağrıları free-plan burst limitine çarpabiliyordu; pacing ve sınırlı retry eklendi.
3. Deribit bağlantı timeout'u motor hatası gibi davranmamalıydı; fail-safe health ve eksik derivatives için `quality=0` davranışı eklendi.
4. Deribit inverse perpetual OI tekrar fiyatla çarpılarak yanlış normalize ediliyordu; USD OI semantiği düzeltildi.
5. Windowed tek EXE CLI çıktısını konsola taşımıyordu; service-status ve `--once` görünür hale getirildi.

Bu sürümün amacı yeni sinyal mantığı değil, çalışan pipeline'ın gerçek ortamda kırılmasını önlemekti.

### v1.1.2 — freshness ve provider sürekliliği

v1.1.1 smoke testinde FRED'in `sort_order=asc` ve sınırlı kayıtla çağrılması nedeniyle DGS/VIX gibi serilerin 1981/1995/2009 verilerinde kaldığı görüldü. API çağrısı başarılı olduğu için eski veri yanlışlıkla kaliteli sayılabiliyordu.

- FRED son observation'ları descending aldı, DB'ye kronolojik yazdı.
- Quality API başarısına değil `observation_date` yaşına bağlandı.
- Günlük ve haftalık serilere ayrı freshness bantları verildi.
- Kullanıcı ağında Deribit erişilemediği için `auto` modda BTC veya ETH'den biri başarısızsa iki varlık birlikte OKX'e geçirildi.
- BTC ve ETH derivatives verisinin farklı provider'lardan karıştırılması yasaklandı.

### v1.1.3 — veri semantiği ve URA/realtime hardening

Core pipeline çalışsa da modelin bazı boşlukları sahte güven üretiyordu:

- URA `fundamentals/breadth/event` placeholder'larında `score=0, quality=50` kaldırıldı; kaynak/history yoksa `quality=0` oldu.
- `score=0`, directional agreement içinde pozitif oy sayılmaktan çıkarıldı.
- Resmî Global X URA full-holdings CSV keşfi ve saklama eklendi.
- İki holdings snapshot'ından sonra hesaplanabilen price-adjusted AUM flow proxy eklendi. Bu fiziksel uranyum arz-talep modeli değildir.
- Holdings constituent fiyatlarından zamanla biriken breadth katmanı eklendi; geçmiş sentetik olarak doldurulmadı.
- SEC EDGAR filing monitörü eklendi. Semantic classifier olmadığı için filing'lere sahte bullish/bearish severity verilmedi; yön `0` kaldı.
- Gerçek ACTION gerekmeden Coinbase websocket/order-book smoke testi eklendi.
- Decision provenance, weekly gerçek bakım ve 5/20/60 seans realized-performance audit eklendi.

URA quality'nin ilk gün düşmesi hata değil, sahte q50'nin kaldırılmasının doğru sonucuydu.

### v1.1.4 — dependency preflight ve coverage hardening

- Daily crypto kararı öncesi BTC+ETH derivatives çifti eksik veya 3 saatten eskiyse bir kez best-effort hourly refresh eklendi.
- Refresh başarısız olsa bile motor uydurma derivatives üretmez; q0 ve normal quality gate ile fail-safe kalır.
- SEC quality, kontrol edilen entity sayısına göre yapay `60+5*n` yerine exact eşleşen URA fon ağırlığına bağlandı.
- SEC yalnız tek event kaynağı olduğu için quality `70` ile sınırlandı.
- CLI wrapper'ın yeni log satırlarını terminale geri basma davranışı düzeltildi.

### v1.2.0 — doğrulanabilir Shadow milestone

v1.2.0 daha fazla sinyal üretmek için çıkarılmadı. Önceki sürümlerde veri semantiği ve operasyon güvenliği düzeltildikten sonra motorun nasıl ölçüleceği sorusuna cevap verdi:

- `model_version` provenance eklendi; eski kararlar `legacy-pre-1.2.0`, yeniler `1.2.0` olarak ayrıldı.
- Coinbase üzerinden 2500 ortak günlük BTC/ETH history backfill eklendi.
- ETH/BTC için historical as-of directional-core replay eklendi.
- Aday edge eşikleri için tek kronolojik `%70 train / %30 holdout` keşif raporu eklendi.
- Sonuçların settings/weight/threshold'a otomatik uygulanması açıkça yasaklandı.
- `model.validation_runs` ve authenticated `public.model_validation_snapshot` eklendi.
- Shadow Readiness kriterleri ve manuel LIVE review kapısı eklendi.
- URA full replay, holdings/breadth/event point-in-time geçmişi yeterli olmadığı için bilinçli `NOT_READY` bırakıldı.
- Monthly audit, realized performance + validation + readiness'i birlikte raporlar; parametre değiştirmez.

### v1.2.0 terminoloji düzeltmesi

DB/code validation type hâlâ `PIT_CORE_REPLAY` adını kullanır. Ancak bu sonuç strict PIT değildir:

- Fiyat geçmişi yalnız ilgili tarihe kadar kesilir.
- Makroda `observation_date <= as_of` seçilir.
- FRED revision/vintage (`realtime_start/realtime_end`) geçmişi birebir replay edilmez.
- Derivatives ve event geçmişte güvenilir PIT history olmadığı için q0 ile dışarıda kalır.
- Production quality/confidence/event kapıları ve persistent K1/K2 state machine replay'de birebir çalışmaz.

Bu nedenle doğru ürün adı/yorumu: **historical as-of directional-core replay**. Strict macro-vintage PIT ve production parity sonraki hardening işidir.

## 5. Sinyal motorunun değişmez sınırları

- `direction`, signed edge yönüdür; emir değildir.
- `WAIT` veya `NO_ACTION_DATA` satırındaki yön kullanıcıya dönüşüm önerisi sayılmaz.
- `ACTION`, günlük model koşuludur; yeni Telegram/kademe olayı için `action_event=true` gerekir.
- Python `action_size`, global model kademe yüzdesidir; kullanıcı bakiyesinden çevrilecek adet değildir.
- v1.2.0'daki `max_regime_pct=%50`, Python'un kendi global öneri state'inin kümülatif tavanıdır; gerçek portföyün `%50`si için bağlayıcı Quasar limiti değildir.
- Quasar'ın kayıtlı dönüşüm yüzdeleri ve `%25/%50/%75/%100` butonları hesaplama yardımcılarıdır; Python yüzdesiyle `min(...)` uygulanmaz ve gerçek işlem oranını zorlamaz.
- Realtime Execution order-book gözlemidir; emir göndermez.
- Validation ve calibration hiçbir parametreyi otomatik değiştirmez.
- Eksik veri q0'dır; quality yükselsin diye sentetik history/score eklenmez.

## 6. Bugünkü karar zinciri

```text
Raw data
→ freshness ve source quality
→ technical/features
→ market/trend regime
→ factor scores ve factor quality
→ rejime göre ağırlık
→ quality-adjusted signed edge
→ edge + data quality + directional agreement
→ confidence / uncertainty
→ event veto + late-entry
→ volatility risk / recommended size
→ decision status
→ persistent K1/K2 state
→ private audit + public snapshots
→ SHADOW kayıt veya LIVE bildirim/order-book gözlemi
```

Ayrıntılı formüller ve tablo sözleşmesi `SIGNAL_ENGINE_DECISION_CONTRACT.md` içindedir.

## 7. Veri ve tablo haritası

### Ham/girdi tabloları

- `market.daily_prices`: BTC, ETH ve URA OHLCV geçmişi.
- `market.derivatives_snapshots`: aynı provider'dan BTC/ETH OI, funding, basis, bid/ask.
- `macro.observations`: FRED observation ve realtime alanları.
- `fundamentals.ura_holdings`: Global X dated holdings.
- `fundamentals.ura_breadth`: constituent breadth geçmişi ve quality.
- `events.events`: SEC/event metadata; severity/surprise yalnız kanıt varsa yönlüdür.
- `market.execution_snapshots`: test veya action sonrası order-book gözlemleri; işlem emri değildir.

### Model/audit tabloları

- `model.features`: tarih/sistem/feature/value/quality.
- `model.regimes`: primary regime, sabit gösterim olasılıkları ve market/trend axes.
- `model.factor_scores`: factor score, quality, kullanılan weight ve weighted score.
- `model.decisions`: yön, edge, confidence, quality, risk, status ve action alanları.
- `model.signal_state`: K1/K2 persistent aktif yön/stage/cumulative/reset state.
- `model.performance`: mature kararların 5/20/60 seans sonuçları.
- `model.validation_runs`: validation geçmişi.
- `system.job_runs`: scheduler/manuel job audit'i.

### Public Quasar yüzeyi

- `public.market_snapshot`
- `public.decision_snapshot`
- `public.decision_history`
- `public.engine_health_snapshot`
- `public.model_validation_snapshot`

### Kaynak otoritesi uyarısı

- v1.2.0 runtime factor ağırlıkları `config/defaults.json`dan okunur. `model.factor_weights` tablosunun varlığı runtime'ın onu okuduğu anlamına gelmez.
- Migration 0007 Shadow kriterlerini `model.parameters`a seed eder; fakat v1.2.0 readiness sınıflandırıcısı DB'den bu değerleri çekmez, kod varsayımlarını kullanır.
- Bu iki tutarsızlık dokümantasyonla gizlenmez; sonraki observability/config-authority hardening için `OPEN`dır.

## 8. Güncel deployment ve doğrulanmış durum

- Windows Server 2019, 7/24.
- Service: `RosaInvestmentEngine`, Automatic, Local System.
- Son doğrulama: `STATE : 4 RUNNING`, exit code `0`.
- Mode: `SHADOW`.
- Realtime Execution: `OFF`.
- Crypto history: Coinbase, 2500 ortak gün, `OK`.
- Validation: 1381 replay observation; core `OK`; configured edge 70'te sinyal yok.
- Calibration: düşük eşiklerde bile sınırlı signal count; exploratory; hiçbir ayar uygulanmadı.
- URA full replay: `NOT_READY`.

Scheduler — Europe/Istanbul:

```text
xx:05                         hourly derivatives
00:15 / 06:15 / 12:15 / 18:15 macro
xx:35                         SEC event
02:40                         daily URA
05:20                         daily crypto
16:30 Mon–Fri                 TCMB FX
08:00 Saturday                weekly maintenance
09:00 month day 1             monthly audit
```

## 9. Shadow görev takvimi

- Görev 1 — ilk otomatik günlük döngü: `PASS`.
- Görev 2 — TCMB/FX: `PASS`.
- Görev 3 — 01.08.2026 09:30 TRT weekly + monthly audit: `PENDING`; kullanıcı çıktısı paylaşılmadan PASS sayılmaz.
- Görev 4 — 07.08.2026: 7 günlük güvenilirlik.
- Görev 5 — 14.08.2026: 14 günlük stabilite.
- Görev 6 — 20.08.2026: URA quality/history değerlendirmesi.
- Görev 7 — 29.08.2026: 30 günlük Shadow Graduation Review.

Görev 1 sonucu, motorun gece boyunca veri topladığını, Deribit timeout'ta atomik OKX fallback kullandığını, ETH/BTC için `WAIT`, URA için q70.4 nedeniyle `NO_ACTION_DATA` ürettiğini ve çökmeyip scheduler'a devam ettiğini kanıtladı. Görev 2 TCMB data date/rate, market snapshot, health ve job audit uyumunu doğruladı.

## 10. Görevlerden sonraki kilometre taşları

### Görev 1–3: operasyon gerçeği

Yalnız scheduler, provider, freshness, snapshot, health ve job-audit sapmaları düzeltilir. Factor/weight/threshold/K1/K2 davranışı değiştirilmez.

### Görev 4 sonrası: v1.2.x davranış değiştirmeyen hardening

- Açık `shadow_epoch_id` / `shadow_started_at`.
- `scheduled/manual/backfill/development` run-kind ayrımı.
- Beklenen/gerçekleşen scheduler run sayıları.
- `OK rate` ve `completed rate` ayrımı.
- Edge/confidence/quality/status/direction bucket diagnostics.
- Mevcut v1.2.0 K1/K2/reversal/reset davranışını değiştirmeden karakterize eden unit testler.
- Runtime config authority'nin JSON/DB ayrımını görünür hale getirme.

### Görev 5–6 sonrası: validation kanıtını güçlendirme

- Gerçek expanding/rolling walk-forward tasarımı.
- Strict macro vintage PIT (`realtime_start/realtime_end`) desteği.
- Production ve replay arasındaki kapı/state farklarının raporu.
- URA fundamentals/breadth/event quality katkılarını ayrı ayrı inceleme.
- Sentetik quality/history eklemeden kaynak/freshness/history iyileştirmesi.

### Görev 7: manuel graduation review

Birlikte değerlendirilir:

- scheduler güvenilirliği,
- Shadow edge/confidence/quality/status dağılımı,
- K1/K2 olayları,
- realtime smoke güncelliği,
- historical as-of replay,
- walk-forward,
- monthly realized performance,
- URA history/coverage.

`READY` görülse bile otomatik LIVE yoktur. Kanıt zayıfsa Shadow devam eder. Factor, weight, threshold, K1/K2, reversal, cooldown veya action-size otoritesi değişecekse yeni model version ve yeni Shadow Epoch gerekir; mevcut 30 günlük kanıt otomatik devredilmez.

### Görev takvimi sonrası: veri yaşam döngüsü ve FRED tekilleştirme araştırması

Veri büyümesini ölçme ve güvenli bir FRED tekilleştirme politikası seçme yönü
`APPROVED`dır. Buna karşılık `(series_id, observation_date)` başına tek current kayıt,
ayrı revision tablosu veya başka bir şema **henüz onaylanmış çözüm değildir**;
adayların gerçek FRED akışı ve geçmiş veriyle karşılaştırılması `OPEN`dır. Mevcut
v1.2.0 Supabase tablolarında yaşa göre çalışan otomatik retention/cleanup yoktur ve
Görev 3 dahil Shadow kanıtı toplanırken veri yazma davranışı değiştirilmez.

Görev 7 sonrasında Python tarafında iki bağlı çalışma ele alınacaktır:

1. Sinyal penceresinden çıkan ham ve operasyonel veriler için tablo bazlı yaşam
   döngüsü araştırılacak. Portföy ledger'ı, karar/sinyal bağı, fiyat geçmişi,
   validation/performance ve gerekli PIT/revision kanıtı kalıcı korunacak; yalnız
   tekrar eden veya özetlendikten sonra ham ayrıntısı atıl hale gelen derivatives,
   execution-test ve scheduler/job verileri temizlik adayı olacaktır.
2. FRED ingest davranışı önce ölçülecek, sonra tekilleştirme politikası seçilecektir.
   Doğrudan `UNIQUE (series_id, observation_date)` eklenmeyecek; bu yaklaşımın güncel
   değer, gerçek revision, strict PIT/replay ve audit üzerindeki etkisi kanıtlanmadan
   current/revision şeması production kararı sayılmayacaktır.

#### Doğrulanmış başlangıç bulgusu — nihai karar değildir

`macro_job` günde `00:15`, `06:15`, `12:15` ve `18:15` olmak üzere dört kez çalışır;
sekiz serinin her biri için son `1500` observation yeniden alınır. Bu, tur başına
yaklaşık `12.000`, günde yaklaşık `48.000` gelen observation ve bulk upsert denemesi
demektir.
Collector `realtime_start/realtime_end` göndermediği için FRED bunları kendi “today”
değerine varsayar. Aynı `realtime_start` dönen turlar mevcut
`(series_id, observation_date, realtime_start)` constraint'ine çarparak yeni mantıksal
satır üretmez; fakat `value`, `realtime_end` ve `fetched_at` tekrar update edildiğinden
WAL/dead-tuple, I/O ve job süresi etkisi ayrıca ölçülmelidir. FRED'in “today” için
kullandığı saat dilimi belgede açık değildir; TRT'deki dört tur provider tarih
sınırını aşarsa aynı TRT gününde bile farklı `realtime_start` ve yeni satır oluşabilir.
Bu nedenle analiz yerel takvim gününe değil, her response içindeki gerçek
`realtime_start/realtime_end` değerine dayanacaktır.

29–30.07.2026 örneğinde `14.513` satırın `4.343`ü aynı seri/tarih/değerin yalnız yeni
`realtime_start` altında tekrarıdır; karşılaştırılabilen ortak satırlarda gerçek değer
değişimi `0`dır. Bu iki günlük örnek çoğalma riskini kanıtlar, fakat bütün serilerin
revision karakterini veya uzun vadede doğru şemayı tek başına kanıtlamaz.

FRED'in resmî sözleşmesinde varsayılan real-time period bugündür; bu, “geçmiş hakkında
bugün bilinen bilgi” görünümüdür. `fred/series/vintagedates` ise yalnız yeni değer
yayınlanan veya seri değerleri gerçekten revize edilen tarihleri döndürür. Araştırma
bu iki semantiği günlük polling alanlarıyla karıştırmayacaktır:

- <https://fred.stlouisfed.org/docs/api/fred/realtime_period.html>
- <https://fred.stlouisfed.org/docs/api/fred/series_observations.html>
- <https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html>

#### Zorunlu araştırma ve geçmiş-veri backtest kapısı

Herhangi bir migration/dedup öncesinde şu sıra tamamlanacaktır:

1. Sekiz serinin her biri için frekans, yayın takvimi, gerçek revision/vintage
   davranışı ve FRED parametreleri belgelenecek. Dört TRT turunun döndürdüğü provider
   real-time tarihleri kaydedilecek; aynı `realtime_start` içi upsert'ler ile değişen
   `realtime_start` kaynaklı yeni satırlar ayrı ölçülecek.
2. Mevcut DB'de `series_id + observation_date + value`, `realtime_start`,
   `realtime_end`, `fetched_at` ve `system.job_runs` birlikte analiz edilecek.
   `received/inserted/unchanged/revised/skipped`, satır/indeks büyümesi,
   WAL/dead-tuple ve job süresi için ölçülebilir baseline oluşturulacak.
3. En az şu adaylar karşılaştırılacak:
   - mevcut `(series_id, observation_date, realtime_start)` yapısı,
   - yalnız current değer saklayan `(series_id, observation_date)` yapısı,
   - current + sıralı append-only change-point/revision yapısı,
   - FRED/ALFRED resmî vintage tarihleriyle beslenen PIT yapısı,
   - seri bazında farklı revision riskine izin veren hibrit yapı.
4. Geçmiş veri replay/backtest'inde aynı `as_of` tarihleri için latest değer, macro
   score/quality, regime, ETH/BTC ve URA/USD karar çıktıları karşılaştırılacak. Revision
   günleri, hafta sonu/tatil, yeni observation, eksik `.` değer, A→B→A geçişi ve geç
   gelen düzeltmeler özellikle test edilecek. Look-ahead bias oluşmaması ve replay'in
   deterministik kalması zorunludur.
5. Aynı backtest her aday için mantıksal satır sayısı, günlük write/upsert hacmi,
   tahmini 10 yıllık kapasite, API/job süresi ve rollback maliyetini de raporlayacak.
   Sinyal sonucu kadar uzun vadeli işletim maliyeti de karar ölçütüdür.
6. Son karar yalnız bu rapordan sonra verilecektir. Dört günlük çekimin tek bir
   değişmeyen observation üretmesi idempotent olmalı; gerçek revision kaybolmamalı;
   latest ve PIT okuyucularının hangi katmanı kullandığı açık olmalı; mevcut veriye
   uygulanacak işlem önce dry-run ve geri alınabilir backfill ile doğrulanmalıdır.

Pure watermark/yalnız son observation tarihinden devam etmek de önceden doğru kabul
edilmez; eski tarihli revision'ları kaçırabilir. Resmî `vintagedates`/`output_type=3`,
değişen-response hash'i, kayan backfill penceresi ve current + event seçenekleri bu
sebeple ölçülecek adaylardır. `unique(series_id, observation_date, value)` de tek
başına yeterli değildir; A→B→A sırasındaki son A olayını ilk A ile çakıştırabilir.

Mevcut polling ile görülen bir değişimin zamanı yalnız “motorun farklı değeri ilk
gördüğü an”dır; resmî yayın/vintage zamanı olduğu iddia edilmez. Uygulanmış `0001`
migration'ı değiştirilmeyecek; araştırma bir çözüm seçerse yeni numaralı migration,
transaction/idempotency testleri ve kontrollü backfill/dedup kullanılacaktır.

## 11. Quasar kilometre taşları

1. `docs/DEMO_TEST_SCENARIO_100K_TRY.md` içindeki manuel finans regression'ını tamamla.
2. Dashboard/Portföy/İşlemler/Raporlar toplamlarını ekran görüntüsü ve beklenen matematikle doğrula.
3. Gerçek Supabase bağlantı sağlık testi, Auth/RLS yaşam döngüsü ve web callback kodu tamamlandı; gerçek proje ve native Capacitor deep-link testiyle doğrula.
4. Çoklu hesap, append-only revision/cancellation ve reset RPC davranışını gerçek Supabase üzerinde doğrula.
5. Auth/connection yaşam döngüsünden sonra Signal→Conversion bağını tek yönlü kur: dönüşüm formunda global karar `AppPopupSelect` ile seçilsin, `decision_id` otomatik kaydedilsin, sinyalin `action_size` değeri başlangıç oranı olarak getirilebilsin ve kullanıcı bu oranı serbestçe değiştirebilsin.
6. Capacitor aşamasında session/refresh secret'ı native secure storage'a taşı.

### Quasar Auth/connection revizyonu — kod tamamlandı, runtime kanıtı `OPEN`

- Project URL/publishable key gerçek `/auth/v1/health` isteğiyle test edilir;
  `service_role/sb_secret_` istemciye kaydedilmez.
- Aktif oturum `getUser()` ile sunucudan doğrulanır; `profiles`,
  `investment_accounts` ve `market_snapshot` authenticated RLS okumaları sınanır.
- Bağlantı imzası değiştiğinde eski auth subscription, auto-refresh ve realtime
  kanalları dispose edilir; eski oturum/account cache temizlenip yeni proje için
  yeniden giriş istenir.
- `INITIAL_SESSION`, `SIGNED_IN`, `TOKEN_REFRESHED`, `USER_UPDATED`,
  `PASSWORD_RECOVERY` ve `SIGNED_OUT` tek store yaşam döngüsünde ele alınır.
- PKCE, e-posta doğrulama ve şifre kurtarma için `/auth/callback` recovery ekranı;
  hash SPA yönlendirmesi ve Capacitor `appUrlOpen`/cold-launch adaptörü eklendi.
- Network, timeout, invalid key/credentials, email-not-confirmed, expired session ve
  RLS reddi kullanıcıya ayrıştırılmış hata olarak gösterilir.

Otomatik service testleri, Prettier/ESLint ve SPA build geçmiştir. Gerçek Supabase
URL/key/Auth e-postası bu çalışma ortamında bulunmadığından gerçek proje üzerinde
health + login + RLS + recovery e-posta zinciri henüz `OPEN` runtime doğrulamasıdır.
Capacitor native mode/plugin/custom-scheme üretildiğinde cold/warm deep-link ayrıca
cihazda test edilmelidir. Bu kanıttan sonra çoklu hesap/reset RPC ve `100.000 TRY`
regression tamamlanır; ardından Signal→Conversion frontend bağına geçilir.

### Signal→Conversion için kesin ürün sınırı

- Python seçili hesabı, bakiyeyi veya Quasar'da gerçekleşen oranı okumaz.
- Quasar sinyal kartları karar mekanizmasını zorlayan talimat değil, öngörü ve raporlama desteğidir.
- Bir dönüşüm sinyale bağlanabilir fakat bağ isteğe bağlıdır; aynı global `decision_id` birden fazla portföy işlemiyle ilişkilendirilebilir.
- Kullanıcıya ID yazdırılmaz. Sinyal listesi `AppPopupSelect` üzerinden seçilir.
- Sinyal seçildiğinde Python önerisi ön doldurulabilir; kullanıcı gerçek risk kararına göre oranı veya miktarı değiştirebilir.
- `btc_eth_conversion_pct` ve `ura_usd_conversion_pct` zorlayıcı üst sınır değil, Quasar hesaplama/varsayılan oran yardımcılarıdır.

## 12. Hâlâ onaylanmamış veya görev takvimi sonrasına bırakılmış model işleri

- Kademeler arasında en az 5 karar seansı.
- Karşı yöne geçiş için iki ardışık qualified kapanış.
- Production ve replay için tek versioned state machine.
- Python ayar penceresinde `max_regime_pct` alanının yönetilmesi ve gelecek action-size formülünün hangi sinyal gücü/kalitesi bileşenlerini kullanacağının kesinleştirilmesi.
- Beş zayıf değerlendirme sonrası resetin aynı `as_of` tekrarları ve örtüşen feature geçmişiyle davranışının incelenmesi. Mevcut kod reset sonrası yeniden aynı yön K1'e izin verir; önce ters rejim görülmesini zorunlu kılan ürün kuralı yoktur.

Reset eşiği veri penceresi değildir. Canlı ETH/BTC işi yaklaşık `1300` takvim
günlük fiyat serisi üzerinde 36 ay/52 hafta/60 gün/20 gün ve daha kısa teknik
pencereleri birlikte kullanır; derivatives son `3` saat, makro her serinin son
geçerli observation'ıdır. URA günlük history uzunluğu kodda sabitlenmemiştir;
provider yanıtı kullanılır, yalnız en az `60` günlük bar ile `52` haftalık ve `36`
aylık history zorunludur. `5→30` reset değişikliği bu verileri veya yön hesabını
uzatmaz; yalnız K1/K2 persistent state'ini daha uzun süre korur. Ayrıntılı pencere
haritası signal contract bölüm 5.1'dedir.

Bunlar mantıklı adaylardır fakat `APPROVED` veya `RELEASED` değildir.

## 13. Güvenlik ve Git protokolü

- Secret'lar repo veya memory bank'e yazılmaz.
- Uygulanmış migration geriye dönük değiştirilmez; yeni sıra numarası kullanılır.
- Her değişiklikten önce remote HEAD ve dosya SHA yeniden okunur.
- Asistan feature/agent branch'e push eder; kullanıcı pull/test eder.
- Draft PR'lar test döngüsü bitmeden merge edilmez.
- Proje durumu değiştiğinde `SESSION_HANDOFF.md`; kalıcı motor kararı değiştiğinde bu memory bank veya contract aynı turda güncellenir.

## 14. En kısa devir özeti

```text
Amaç: 25.07.2026–25.07.2036 BTC/ETH/URA yatırımını audit edilebilir biçimde izlemek.
DCA: aylık ana disiplin; sinyal motoru DCA'yı durdurmaz.
Python: v1.2.0, global ETH/BTC + URA/USD karar desteği, SHADOW, Realtime OFF, otomatik emir yok.
Quasar: seçili hesapta gerçek işlem ledger'ı ve raporlama.
Signal→Conversion: gelecekte tek yönlü ve isteğe bağlı decision_id bağı; öneri oranı düzenlenebilir, bağlayıcı limit yok.
Validation: historical as-of directional core; strict vintage PIT/production K1-K2 parity değil.
Görevler: 1 ve 2 PASS; Görev 3 kullanıcı kanıtı bekliyor.
Kural: test sonucu threshold/weight/mode/LIVE'ı otomatik değiştirmez.
```
