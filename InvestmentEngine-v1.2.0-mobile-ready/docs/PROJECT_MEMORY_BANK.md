# BTC / ETH / URA 10 Yıllık Yatırım — Proje Memory Bank

Son güncelleme: 08 Eylül 2026

Bu belge `BTC_ETH_URA_10YIL` projesinin kalıcı bağlamıdır. Projenin neden var olduğunu, Python + Supabase + Quasar mimarisinin sınırlarını, yayımlanmış v1.2.0 davranışını, tamamlanan Shadow/Post-Shadow kanıtlarını ve hâlâ açık araştırma alanlarını özetler.

Normatif motor davranışı için `SIGNAL_ENGINE_DECISION_CONTRACT.md`, son aktif çalışma için `SESSION_HANDOFF.md`, operasyon kanıtı için görev takvimi ve `SHADOW_CHECKPOINT_LOG.md`, ayrıntılı Post-Shadow kanıtı için ilgili `POST_SHADOW_*.md` belgeleri birlikte okunur.

## 1. Proje amacı

- Gerçek yatırım başlangıcı: **25.07.2026**.
- Süre: **120 ay / 10 yıl**; hedef bitiş **25.07.2036**.
- Spot yatırım varlıkları: **BTC, ETH, URA**.
- Nakit bacakları: **TRY ve USD**. İlk ürün sürümünde USDT ayrı varlık değildir.
- Aylık sermaye ayırma ve DCA ana disiplindir. Sinyal motoru aylık yatırım yapılıp yapılmayacağına karar veren bir robot değildir.
- Kullanıcı gerçek sermaye girişini, alımı, satışı, dönüşümü ve sermaye çıkışını Quasar'da kendisi kaydeder.
- Python motoru yalnız iki global göreli sistemi ölçer:
  - `ETH/BTC`: BTC ile ETH arasında göreli güç ve rejim değişimi.
  - `URA/USD`: USD nakit ile URA arasında göreli rejim değişimi.
- Motor sık işlem üretmek için değil; veri kalitesi, yön avantajı, güven, olay vetosu ve risk koşulları birlikte yeterliyse ölçülebilir kademe olayı üretmek için vardır.
- Otomatik borsa emri yoktur. LIVE modu bile bildirim ve isteğe bağlı execution/order-book gözlemidir.

## 2. Katmanların sorumluluk sınırı

| Katman | Sorumluluk | Yapmadığı şey |
| --- | --- | --- |
| Python Investment Engine | Piyasa/FX/makro/derivatives/URA holdings-breadth-event verisi; feature, regime, factor, decision, signal state, validation, health, scheduler | Kullanıcının portföy bakiyesini okumaz; işlem emri göndermez |
| Supabase PostgreSQL | Auth, RLS, portföy ledger'ı, motor audit tabloları, global public snapshot'lar | Frontend'e service-role, DB password veya provider secret açmaz |
| Quasar / Capacitor | Login, çoklu portföy hesabı, manuel işlem girişi, append-only düzeltme/iptal, maliyet/KZ, raporlama, motor görünümü | Factor weight/threshold/mode değiştirmez; Telegram secret yönetmez |

Sinyaller globaldir; Dashboard/Portföy/İşlemler/Raporlar seçili `account_id` bazlıdır.

## 3. Mimari dönüşüm

İlk keşif Google Sheets + Apps Script ile aylık BTC/ETH DCA ve ETH/BTC dönüşüm senaryoları üzerinden başladı. URA, USD/TRY, maliyet ve dashboard ihtiyaçları eklendikçe 10 yıllık audit, kullanıcı oturumu, çoklu hesap, güvenli secret, scheduler, provider fallback, model provenance, mobile kullanım ve append-only işlem geçmişi için Sheets yetersiz kaldı.

Kesin mimari:

- Google Sheets/Apps Script production zincirinden çıkarıldı.
- Supabase PostgreSQL ana veri/audit katmanı oldu.
- Python Engine Windows üzerinde 7/24 Windows Service olarak konumlandı.
- Quasar + Pinia + Supabase + Capacitor kullanıcı uygulaması oldu.
- Basit oran kuralı çoklu factor + regime + quality + veto + risk + persistent state modeline dönüştü.

## 4. Sürüm tarihçesi

### v1.0.0

İlk uçtan uca Python/Supabase prototipi. Production smoke test ve validation katmanı olgun değildi.

### v1.1.0

Mobile-ready temel paket:

- Supabase/Quasar hedefi kesinleşti,
- PyInstaller OneDir/tek EXE + Windows Service + Inno Setup,
- DPAPI LocalMachine encrypted settings,
- `rosalock` PBKDF2 doğrulayıcısı,
- scheduler/health/public snapshot temeli.

### v1.1.1

Gerçek smoke-test hotfix'leri:

- `as_of` metadata'nın numeric feature kolonuna yazılma hatası,
- Alpha Vantage pacing/retry,
- Deribit timeout fail-safe,
- inverse perpetual OI normalization,
- windowed EXE CLI görünürlüğü.

### v1.1.2

Freshness/provider hardening:

- FRED son observation'ları doğru yönde çekildi,
- quality observation yaşına bağlandı,
- BTC/ETH derivatives provider karışımı yasaklandı,
- Deribit başarısızlığında atomik OKX fallback.

### v1.1.3

URA/realtime veri semantiği:

- sahte q50 placeholder kaldırıldı,
- q0 eksik veri semantiği,
- Global X holdings + flow proxy,
- constituent breadth,
- SEC EDGAR monitor,
- Coinbase realtime smoke,
- decision provenance/performance audit.

### v1.1.4

Dependency/coverage hardening:

- derivatives preflight,
- SEC quality fund-weight coverage'a bağlandı,
- CLI wrapper görünürlüğü düzeltildi.

### v1.2.0

Doğrulanabilir Shadow milestone:

- `model_version` provenance,
- Coinbase 2500 günlük history,
- historical as-of directional-core replay,
- calibration/validation raporu,
- `model.validation_runs` ve public validation snapshot,
- Shadow Readiness,
- manuel LIVE graduation kapısı,
- monthly audit.

v1.2.0 daha fazla sinyal üretmek için çıkarılmadı; davranışın ölçülebilir ve audit edilebilir olması için çıkarıldı.

## 5. v1.2.0 terminoloji ve değişmez motor sınırları

DB/code validation type `PIT_CORE_REPLAY` adını kullanır; fakat released replay strict FRED-vintage PIT değildir.

- Fiyat geçmişi ilgili tarihe kadar kesilir.
- Makroda `observation_date <= as_of` seçilir.
- Historical FRED revision/vintage production DB'de birebir saklanmaz.
- Derivatives/event historical PIT coverage sınırlıdır.
- Production quality/confidence/event kapıları ve persistent state replay'de birebir değildir.

Doğru ürün yorumu: **historical as-of directional-core replay**.

Değişmez davranış:

- `direction`, signed edge yönüdür; emir değildir.
- `WAIT`/`NO_ACTION_DATA` yönü dönüşüm önerisi değildir.
- `ACTION` günlük model koşuludur; yeni kademe için ayrıca `action_event=true` gerekir.
- Python `action_size` global model yüzdesidir; kullanıcı portföy adedi değildir.
- `max_regime_pct=%50` Python state tavanıdır; Quasar gerçek portföy limiti değildir.
- Realtime Execution emir göndermez.
- Validation/calibration hiçbir ayarı otomatik değiştirmez.
- Eksik veri q0'dır; quality yükseltmek için sentetik history/score eklenmez.

Released parametreler:

```text
minimum data quality 80
edge threshold       70
confidence threshold 70
strong edge          80
strong confidence    80
WATCH edge           55
reset edge           45
reset days           5
base tranche         25%
max regime           50%
```

Factor weights, K1/K2, reversal, reset ve sizing semantiği model-version değişikliği olmadan değiştirilmez.

## 6. Karar zinciri

```text
Raw data
→ freshness/source quality
→ technical/features
→ regime
→ factor scores + factor quality
→ regime weights
→ quality-adjusted signed edge
→ edge + data quality + directional agreement
→ confidence / uncertainty
→ event veto + late-entry
→ volatility risk / recommended size
→ decision status
→ persistent K1/K2 signal state
→ private audit + public snapshots
→ SHADOW kayıt veya LIVE bildirim/order-book gözlemi
```

## 7. Veri ve tablo haritası

Ham/girdi:

- `market.daily_prices`
- `market.derivatives_snapshots`
- `macro.observations`
- `fundamentals.ura_holdings`
- `fundamentals.ura_breadth`
- `events.events`
- `market.execution_snapshots`

Model/audit:

- `model.features`
- `model.regimes`
- `model.factor_scores`
- `model.decisions`
- `model.signal_state`
- `model.performance`
- `model.validation_runs`
- `system.job_runs`

Public Quasar yüzeyi:

- `public.market_snapshot`
- `public.decision_snapshot`
- `public.decision_history`
- `public.engine_health_snapshot`
- `public.model_validation_snapshot`

Kaynak otoritesi uyarısı:

- v1.2.0 factor weights runtime'da `config/defaults.json`dan okunur; `model.factor_weights` tablosunun varlığı runtime'ın onu kullandığı anlamına gelmez.
- Shadow kriterlerinin bazı DB seed'leri olsa da released readiness kod otoritesi ayrıca kontrol edilmelidir.

## 8. Güncel Windows deployment

Bu projede development makinesi aynı zamanda çalışan Shadow service host'udur.

```text
Service                 RosaInvestmentEngine
State                   RUNNING
StartMode               Auto
Mode                    SHADOW
Realtime Execution      OFF
Model version           1.2.0
```

08.09.2026 provenance hardening build/deploy kabulü:

```text
full Python tests       68 passed
release check           OK
PyInstaller OneDir      PASS
Inno Setup              PASS
build EXE SHA256        91300423EA360C11E923C1AC74F437581BAAEF0DC23CFBA3458B60FB8A29890A
installed EXE SHA256    same / PASS
settings preservation   PASS
rosalock preservation   PASS
CLI service-status      RUNNING / exit 0
```

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

## 9. Shadow görev takvimi — TAMAMLANDI

Görev 1–7 tamamlandı.

```text
30 günlük görev takvimi  TAMAMLANDI
SHADOW_READINESS         READY
LIVE                     NO-GO / açılmadı
Mode                     SHADOW
Realtime Execution       OFF
```

Readiness kanıtının ana özeti:

```text
Shadow calendar days       36
ETH/BTC decision days      35
URA/USD decision days      25
ETH/BTC median quality     90.83
URA/USD median quality     87.71
URA holdings dates         24
URA breadth dates          24
Recent job success         99.2126%
Realtime test              OK
waiting_reasons            []
blockers                   []
```

READY otomatik LIVE değildir.

## 10. Post-Shadow P0 — CLOSED

Development/runtime reliability alt aşaması kapandı.

- 10s historical pool timeout development ortamında yeniden üretilemedi.
- Pool lifecycle/replacement doğrulandı.
- Generic DB retry veya scheduler serialization eklenmedi.
- Historical production gözlem borcu GitHub Issue #2'de tutuldu.
- SEC `DEGRADED` kayıtlarının çoğu crash değil fund-weight coverage semantiğidir.

Ayrıntı:

- `POST_SHADOW_P0_CONNECTION_POOL_RCA.md`
- `POST_SHADOW_P0_RUNTIME_RELIABILITY_CLOSURE.md`

## 11. Post-Shadow P1 — walk-forward ve FRED strict PIT doğrulaması

### Walk-forward

```text
observations                   1420
folds                          12
configured edge=70 OOS signal 0
```

Düşük keşif eşiklerinde sınırlı sinyal bulundu; kanıt sinyal-kıt kaldı.

```text
implementation  VERIFIED / CLOSED
threshold change NOT SUPPORTED
LIVE            NO-GO
```

### FRED/ALFRED strict verification

Production collector değiştirilmeden verification-only ALFRED yolu kuruldu.

```text
configured series            8
ALFRED available             7
ALFRED unavailable           SP500
replay days                  1420
complete days                1397
excluded incomplete days     23
mean abs edge delta          0.5222834646
max abs edge delta           14.27
regime changes               19
direction-sign changes       5
edge=70 qualification change 0
```

Tam kapsamalı strict walk-forward yine yeterli OOS sinyal üretmedi. FRED revision farkı bazı günlerde edge/rejimi değiştirir ama released edge=70 sinyal kıtlığını açıklamaz.

```text
FRED strict-PIT substage  CLOSED
threshold/model change    NONE
LIVE impact               NONE
```

Ayrıntı:

- `POST_SHADOW_P1_FRED_PIT_BASELINE.md`
- `POST_SHADOW_P1_FRED_STRICT_PIT_COMPARISON.md`

## 12. Post-Shadow P1 — same-market-date signal-state idempotency — CLOSED

Production baseline URA/USD için aynı market `as_of` tarihinde tekrar değerlendirmeler olduğunu kanıtladı; bu tekrarlar körlemesine duplicate sayılmaz.

```text
ETH/BTC decisions              39
ETH/BTC repeated market dates  0
URA/USD decisions              38
URA/USD repeated market dates  7
max URA decisions/date         3
```

Historical production state corruption görülmedi. Ancak kod RCA'sında aktif rejimde aynı `as_of` tekrarının `reset_counter`ı tekrar artırabileceği latent risk doğrulandı.

Hardening:

- `model.signal_state.last_evaluated_as_of`,
- migration `0013_signal_state_market_date_idempotency.sql`,
- reset counter yalnız yeni market as_of'ta ilerler.

Doğrulama:

```text
focused tests                           3 passed
full tests                              65 passed
release check                           OK
state rows                              2
rows matching latest decision as_of     2
mismatches                              0
```

K1/K2, thresholds, scheduler ve LIVE semantiği değişmedi.

## 13. Post-Shadow P1 — URA evaluation-time provenance hardening — CLOSED

Ayrıntı:

- `POST_SHADOW_P1_PRODUCTION_REPLAY_PROVENANCE_HARDENING.md`
- `verification/verify_production_replay_provenance_reconstructibility.sql`
- `verification/verify_production_replay_ura_provenance_forward.sql`

Historical baseline:

```text
ETH/BTC decisions                           39
ETH/BTC persisted audit coverage            strong / 39 of 39
URA/USD decisions                           38
URA directional fundamentals complete       36/36 positive-quality rows
URA positive-quality breadth rows            36
breadth rows with numeric scoring inputs      0/36 before hardening
event rows with exact event-set identity      0/38 before hardening
```

Repeated URA market dates aynı evaluation input setini garanti etmiyordu:

```text
repeated decision rows                  19
factor-payload peer differences         17/19
regime peer differences                  0
```

Bu nedenle repeated decisions deduplicate edilmez.

Audit-only hardening yeni URA decision payload'ına şunları ekledi:

- breadth numeric scoring keys,
- `breadth_date`,
- breadth `created_at`,
- exact `event_refs`,
- event `health_checked_at`,
- event `health_status`,
- evaluated event count.

Regression:

```text
focused provenance tests  3 passed
full Python tests          68 passed
release check              OK
```

Production forward acceptance, decision `85`:

```text
system                             URA/USD
model_version                      1.2.0
as_of                              2026-09-04
created_at                         2026-09-07T22:30:02.725709+00:00
decision_evaluated_at              2026-09-07T22:30:00.362158+00:00
status                             WAIT
direction                          USD→URA
action_event                       false
edge_score                         1.03
confidence                         23.77
data_quality                       90.51
hardened_audit_payload_complete    true
```

Tüm required forward check'ler `true` çıktı. Breadth 50DMA/200DMA değerlerinin `null` olması history maturity durumudur; anahtarların korunması audit kontratıdır. Event `event_refs=[]` evaluated set'in gerçekten boş olduğunu gösterir.

Sınıflandırma:

```text
audit-only hardening               VERIFIED
runtime deployment                 VERIFIED
forward new-decision persistence   VERIFIED
URA provenance substage            CLOSED
historical old rows                NOT BACKFILLED
raw holdings immutable history     OPEN
full production/replay parity      OPEN
LIVE                               NO-GO
```

Bu kapanış threshold, factor weight, confidence, K1/K2, reset, sizing, scheduler cadence, model version veya SHADOW/LIVE davranışını değiştirmez.

## 14. P2 veri yaşam döngüsü — OPEN

FRED current/revision/dedup/retention ve uzun vadeli veri yaşam döngüsü ayrı araştırma başlığıdır.

Kesin kurallar:

- Doğrudan `(series_id, observation_date)` UNIQUE migration uygulanmaz.
- Uygulanmış migration geriye dönük değiştirilmez.
- Dedup/delete/backfill dry-run ve rollback planı olmadan çalıştırılmaz.
- Gerçek revision kaybolmamalı ve PIT/look-ahead semantiği bozulmamalıdır.

Mevcut collector aynı observation setlerini gün içinde tekrar upsert edebilir. FRED real-time/vintage semantiği ile local polling zamanı birbirine karıştırılmaz. Current-only, change-point/revision, ALFRED PIT ve hibrit adayları kapasite + replay doğruluğu birlikte ölçülmeden production kararı verilmez.

## 15. Production/replay tarafında sıradaki iki açık RCA

Bu konular ayrı ele alınmalıdır:

1. **Raw holdings/source snapshot versioning:** `fundamentals.ura_holdings` aynı `(holding_date,ticker)` satırını overwrite eder. Persisted decision-input snapshot'larının validation kontratı için yeterli olup olmadığı veya immutable raw source snapshot store gerekip gerekmediği araştırılacak.
2. **Transactional state-before-decision risk:** mevcut `_persist_decision` state'i decision insert'ten önce persist eder. State commit başarılı, decision insert başarısız senaryosunun retry etkisi analiz edilecek. Bunun production'da gerçekleştiğine dair DB kanıtı yoktur; production incident olarak sınıflandırılmaz.

İki konu da threshold/model tuning gerekçesi değildir.

## 16. Quasar kilometre taşları

- Otomatik `100.000 TRY` finans regression'ı hesap izolasyonu, revizyon/iptal ve idempotent retry ile PASS.
- Gerçek Supabase test hesabında ekran bazlı kabul, Auth/RLS/e-posta/deep-link akışı ve native secure-storage adımları kendi Quasar doğrulama planında sürer.
- Signal→Conversion bağı gelecekte tek yönlü ve isteğe bağlıdır: `decision_id` seçilebilir, `action_size` başlangıç oranı olabilir, kullanıcı gerçek oranı değiştirebilir.
- Python seçili hesabı veya gerçek portföy bakiyesini okumaz.

## 17. Hâlâ onaylanmamış model işleri

Aşağıdakiler `PROPOSED/OPEN` kalır:

- kademeler arasında minimum 5 karar seansı,
- reversal için iki ardışık qualified karşı-yön kapanışı,
- production/replay için tek versioned state machine,
- yeni `max_regime_pct` / sizing yaklaşımı,
- reset sonrası same-direction K1 değişikliği,
- threshold/factor-weight değişiklikleri.

Bunlardan biri seçilirse açık kullanıcı onayı + yeni model version + test + deploy + yeni Shadow Epoch gerekir.

## 18. Güvenlik, Git ve komut sunum protokolü

- Secret'lar repo veya memory bank'e yazılmaz.
- Uygulanmış migration geriye dönük değiştirilmez; yeni sıra numarası kullanılır.
- Her değişiklikten önce remote HEAD ve dosya SHA yeniden okunur.
- Asistan feature/agent branch'e push eder; kullanıcı pull/test eder.
- Kullanıcının yerel repo clean/current durumu yalnız verdiği `git` çıktısıyla doğrulanır.
- Draft PR'lar test döngüsü bitmeden merge edilmez.
- Proje durumu değiştiğinde `SESSION_HANDOFF.md`; kalıcı motor kararı değiştiğinde memory bank veya contract güncellenir.
- PowerShell'de birbirine bağlı komutlar doğrudan kopyala-yapıştır güvenli biçimde, mümkünse tek blok/tek satır ve açık `;` ayırıcılarıyla verilir.
- `$LASTEXITCODE` ilgili komuttan hemen sonra yakalanır.
- `PS ...>` / `>>` promptları kullanıcıya verilen komut bloğuna konmaz.

## 19. En kısa devir özeti

```text
Amaç: 25.07.2026–25.07.2036 BTC/ETH/URA yatırımını audit edilebilir biçimde izlemek.
DCA: aylık ana disiplin; sinyal motoru DCA'yı durdurmaz.
Python: v1.2.0; ETH/BTC + URA/USD; SHADOW; Realtime OFF; otomatik emir yok.
Shadow: Görev 1–7 tamamlandı; SHADOW_READINESS READY; LIVE NO-GO.
P0 reliability: CLOSED.
P1 walk-forward: implementation VERIFIED, evidence signal-starved, threshold change unsupported.
P1 FRED strict verification: CLOSED; edge70 qualification changes 0.
P1 same-as-of state idempotency: CLOSED; migration 0013 verified.
P1 URA provenance hardening: CLOSED; production decision 85 forward payload complete=true.
Historical old URA provenance: geriye dönük backfill yok.
Raw holdings immutable snapshot history: OPEN.
Transactional state-before-decision RCA: OPEN / no production incident evidence.
P2 FRED/data lifecycle: OPEN.
LIVE: NO-GO; hiçbir doğrulama sonucu threshold/weight/mode'u otomatik değiştirmez.
```