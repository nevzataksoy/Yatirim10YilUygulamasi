# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 08 Eylül 2026  
Amaç: Yeni sohbetin güncel proje durumunu konuşma geçmişini yeniden keşfetmeden devralması.

Kalıcı bağlam `PROJECT_MEMORY_BANK.md`, normatif motor gerçeği `SIGNAL_ENGINE_DECISION_CONTRACT.md`, Shadow adımları root `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`, checkpoint kanıtları `SHADOW_CHECKPOINT_LOG.md`, Post-Shadow kanıtları ise ilgili `POST_SHADOW_*.md` belgelerindedir.

## 1. Aktif repo / branch

```text
Repo   nevzataksoy/Yatirim10YilUygulamasi
Branch agent/portfolio-audit-reset
```

Repo default branch'i `master` olsa da güncel Python/Shadow geliştirme gerçeği `agent/portfolio-audit-reset` branch'indedir.

Kullanıcının yerel repo yolu:

```text
D:\wamp64\www\Yatirim10YilUygulamasi
```

Asistan kullanıcının Windows worktree'sine doğrudan erişemediği için yerel `git status clean` iddiası yapmaz. Remote gerçeklik GitHub branch/commit/blob SHA ile, yerel durum kullanıcının verdiği `git rev-parse` / `git status` çıktısıyla doğrulanır.

Her mantıksal değişiklik ayrı commit edilir ve hemen push edilir. Kullanıcıya short SHA, full SHA ve commit mesajı bildirilir. Raw telemetry/log/generated verification çıktıları commit edilmez.

## 2. Zorunlu anlatım ve PowerShell sunum kuralı

Bu proje için iletişim yalnız komut/kod vermekten ibaret değildir. Her teknik adımda mümkün olduğunca sade Türkçe ile:

- hangi sorunun çözüldüğü,
- kontrolün neden yapıldığı,
- sonucun hangi aşama veya durumu etkilediği,
- hangi kararı henüz değiştirmediği,
- bir sonraki adımın neden gerekli olduğu

anlatılır.

PowerShell komutları kullanıcıya doğrudan kopyala-yapıştır güvenli biçimde verilir. Birbirine bağlı komutlar mümkünse tek blokta ve açık `;` ayırıcılarıyla yazılır. `$LASTEXITCODE` gibi geçici değerler ilgili komuttan hemen sonra yakalanır. `PS ...>` veya `>>` promptları komut bloğuna karıştırılmaz. Bu kural `CHATGPT_PROJECT_START_HERE.md` içinde bağlayıcıdır.

## 3. Değişmez released durum

```text
Model Version        1.2.0
Mode                 SHADOW
Realtime Execution   OFF
SHADOW_READINESS     READY
LIVE Graduation      OPEN / NO-GO
```

Released ayarlar:

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

Factor weights, K1/K2, reversal/reset/sizing davranışı değişmemiştir.

`direction` emir değildir. `ACTION` tek başına yeni kademe değildir; yeni kademe davranışı için ayrıca `action_event=true` gerekir. Python kullanıcı portföy bakiyesine göre karar vermez, otomatik exchange order göndermez ve readiness sonucundan otomatik LIVE'a geçmez.

Bu released davranışlarda değişiklik ancak ayrı kullanıcı onayı + yeni model version + test + deploy + yeni Shadow Epoch ile yapılabilir.

## 4. Shadow görev takvimi sonucu

Görev 1–6: `PASS`.

Görev 7:

```text
Checkpoint              PASS
30 günlük görev takvimi TAMAMLANDI
SHADOW_READINESS        READY
LIVE                    AÇILMADI
Mode                    SHADOW
Realtime Execution      OFF
```

Readiness kanıtı:

```text
Shadow calendar days       36
ETH/BTC decision days      35
URA/USD decision days      25
ETH/BTC median quality     90.83
URA/USD median quality     87.71
URA holdings dates         24
URA breadth dates          24
Recent job success         99.2126%
Realtime test              OK / 8 snapshots / max_trade_gap=0
waiting_reasons            []
blockers                   []
```

## 5. LIVE neden hâlâ NO-GO

Shadow epoch boyunca gerçek ACTION/WATCH davranışı yeterince egzersiz edilmedi:

```text
ETH/BTC WAIT              35 / 35 gün
URA/USD WAIT              33 karar / 24 gün
URA/USD NO_ACTION_DATA    2 karar / 1 gün
Crypto ACTION/WATCH       0 / 0
URA ACTION/WATCH          0 / 0
performance               []
```

Historical replay yönsel doğrulama sağlar fakat production ACTION/state davranışını birebir doğrulamaz. `edge=70` için yeterli bağımsız sinyal kanıtı yoktur. Bu durum threshold düşürme gerekçesi değildir.

URA full exact PIT/replay de ham holdings/breadth/event source snapshot geçmişi açısından hâlâ tam değildir.

## 6. Post-Shadow P0 — KAPANDI

```text
P0 Development Reliability   CLOSED / NON-BLOCKING
```

Detaylar:

- `docs/POST_SHADOW_P0_CONNECTION_POOL_RCA.md`
- `docs/POST_SHADOW_P0_RUNTIME_RELIABILITY_CLOSURE.md`

Özet:

- historical 10s pool timeout development ortamında doğrudan yeniden üretilemedi,
- pool lifecycle/replacement davranışı çalışıyor,
- yeni instrumented checkout timeout görülmedi,
- `max_size=6`, `timeout=10s` değiştirilmedi,
- generic DB retry eklenmedi,
- scheduler serialize edilmedi,
- historical production gözlem borcu GitHub Issue #2'de açık kaldı.

Scheduler ERROR RCA:

- ID 5: pre-Shadow Alpha Vantage free API quota — non-blocking.
- ID 477: isolated unexpected Alpha Vantage response shape, sonraki run otomatik toparlandı — non-blocking.
- ID 1642: SEC job içindeki 10s DB pool timeout, Issue #2 ailesi.
- SEC `DEGRADED` kayıtlarının çoğu crash değil, yaklaşık %19–20 fund-weight coverage semantiğidir.

## 7. P1 — Walk-forward doğrulaması

Expanding walk-forward altyapısı teknik olarak doğrulanmış ve implementation adımı kapatılmıştır.

Ana sonuç:

```text
observations                   1420
folds                          12
configured edge=70 OOS signal 0
```

Daha düşük keşif eşikleriyle yapılan hassasiyet koşusunda yalnız 4 OOS sinyal görülmüş, hit rate %25 ve ortalama signed return yaklaşık `-0.0382` olmuştur.

Doğru yorum:

```text
Walk-forward implementation  VERIFIED / CLOSED as implementation
Evidence                     LIMITED / SIGNAL-STARVED
Threshold change             NOT SUPPORTED
LIVE                         NO-GO
```

P1 ortak kanıt sınıflandırması:

```text
LIMITED_TRAIN_SIGNAL_COUNT
LIMITED_OOS_SIGNAL_COUNT
EVIDENCE_AVAILABLE
```

`selection_status=OK` yalnız aday seçim mekanizmasının çalışabildiğini gösterir; tek başına yeterli model kanıtı değildir.

## 8. P1 — FRED strict tarihsel doğrulama — KAPANDI

İlgili belgeler:

- `docs/POST_SHADOW_P1_FRED_PIT_BASELINE.md`
- `docs/POST_SHADOW_P1_FRED_STRICT_PIT_COMPARISON.md`

### 8.1 Baseline sonucu

Mevcut `macro.observations` tablosu strict ALFRED validity history değildir. Tekrar tekrar alınmış FRED-current/fetch-day snapshot'larıdır. Historical cutoff testlerinde local strict PIT coverage yoktur.

Gerçek value revision kanıtlanmıştır:

- `STLFSI4` çok sayıda revision taşır,
- `DTWEXBGS` için de revision örneği vardır.

Bu nedenle `(series_id, observation_date)` bazında kör dedup yapılmaz ve mevcut tablo strict PIT store diye yorumlanmaz.

### 8.2 Verification-only ALFRED yolu

Production collector davranışı değiştirilmeden ayrı doğrulama yolu kurulmuştur:

- FRED tarihsel real-time verisi memory içinde çekilir,
- historical `realtime_start/realtime_end` dönemine göre o tarihte gerçekten yayımlanmış değer seçilir,
- DB'ye yazılmaz,
- threshold/weight/state/mode değiştirilmez.

`SP500` FRED'de vardır fakat ALFRED historical history'si yoktur. Strict replay'de bugünkü SP500 geçmişe uydurulmaz; kaynak boşluğu kabul edilir.

### 8.3 Son gerçek ortam doğrulaması

```text
FRED PIT focused tests       10 passed
Full Python tests            64 passed
Release check                OK
verification stderr          empty
```

ALFRED durumu:

```text
configured series            8
ALFRED-available             7
ALFRED-unavailable           SP500
replay days                  1420
7-seri complete days         1397
complete ratio               %98.3803
first complete date          2022-11-10
last complete date           2026-09-06
excluded incomplete dates    23
```

Eksik 23 günün tamamı `2022-10-18..2022-11-09` ve yalnız `STLFSI4` eksiktir. Resmî ALFRED kaydına göre `STLFSI4` ilk kez `2022-11-10` tarihinde yayımlanmıştır.

### 8.4 Temiz 1397 günlük tarihsel fark

```text
common dates                         1397
mean abs edge delta                  0.5222834646
max abs edge delta                   14.27
regime change dates                  19
direction-sign change dates          5
edge=70 qualification change dates   0
```

Ana yorum:

- FRED revision/yayın-zamanı farkı motorun iç edge ve rejim yorumunu bazı günlerde gerçekten değiştirir.
- Ancak tam kapsamalı 1397 günün hiçbirinde released `edge=70` uygunluğu değişmez.
- Dolayısıyla mevcut edge=70 sinyal kıtlığı FRED revision etkisiyle açıklanamamaktadır.

### 8.5 Son walk-forward sınıflandırması

```text
current_walk_forward
  evidence_status          LIMITED_TRAIN_SIGNAL_COUNT
  edge70_signals           0
  selected_candidate_folds 0
  selected_oos_signals     0

comparable_current_walk_forward
  evidence_status          LIMITED_TRAIN_SIGNAL_COUNT
  edge70_signals           0
  selected_candidate_folds 0
  selected_oos_signals     0

strict_walk_forward
  evidence_status          LIMITED_OOS_SIGNAL_COUNT
  edge70_signals           0
  selected_candidate_folds 7
  selected_oos_signals     1

comparable_complete_coverage_walk_forward
  evidence_status          LIMITED_TRAIN_SIGNAL_COUNT
  observations             1397
  edge70_signals           0
  selected_candidate_folds 0
  selected_oos_signals     0

strict_complete_coverage_walk_forward
  evidence_status          LIMITED_OOS_SIGNAL_COUNT
  observations             1397
  edge70_signals           0
  selected_candidate_folds 7
  selected_oos_signals     0
```

Karar için esas alınan satır tam kapsamalı `strict_complete_coverage_walk_forward` sonucudur.

Sonuç:

```text
Verification implementation     VERIFIED
Real ALFRED fetch               VERIFIED
Source-gap handling             VERIFIED
Complete-coverage separation    VERIFIED
Evidence classification         VERIFIED IN REAL ENVIRONMENT
FRED strict-PIT sub-stage       CLOSED
Threshold/model change          NONE
LIVE impact                     NONE / NO-GO unchanged
```

FRED current/revision/dedup/retention veri yaşam döngüsü ayrı P2 başlığıdır.

## 9. P1 — Production vs replay parity

### 9.1 Same-market-date signal-state idempotency — KAPANDI

İlgili belge:

- `docs/POST_SHADOW_P1_PRODUCTION_REPLAY_STATE_IDEMPOTENCY.md`

Production baseline:

```text
ETH/BTC decisions              39
ETH/BTC unique market dates    39
ETH/BTC repeated market dates  0
URA/USD decisions              38
URA/USD unique market dates    26
URA/USD repeated market dates  7
max decisions / one URA date   3
```

Aynı `as_of` tekrarlarında production geçmişinde:

```text
same_asof_state_moves             []
same_asof_reset_advances          []
same_asof_multiple_action_events  []
```

Production geçmişinde state corruption görülmedi; fakat aktif rejim/reset dalı doğal production ACTION geçmişinde egzersiz edilmemişti.

Kod RCA'sında `reset_counter` aynı market `as_of` tekrarında yeniden artabilecek latent risk olarak doğrulandı. Scheduler tekrarları körlemesine engellenmedi; çünkü aynı `as_of` farklı evaluation zamanlarında farklı macro/fundamentals/breadth/event girdileri görebilir.

Uygulanan hardening:

- `model.signal_state.last_evaluated_as_of` eklendi,
- `reset_counter` yalnız yeni market `as_of` geldiğinde +1 ilerler,
- aynı `as_of` tekrarında ikinci kez artmaz,
- aynı gün aktif yön edge'i reset eşiği üzerine geri çıkarsa sayaç yine 0'a dönebilir,
- K1/K2, reversal, sizing, thresholds, scheduler cadence ve SHADOW/LIVE semantiği değişmedi.

Migration:

- `migrations/0013_signal_state_market_date_idempotency.sql`
- `supabase-migrations/0013_signal_state_market_date_idempotency.sql`

Doğrulama:

```text
focused signal-state tests  3 passed
full Python tests           65 passed
release check               OK
```

Production migration sonrası read-only DB doğrulaması:

```text
column_present                           true
trigger.present                          true
trigger.enabled                          true
signal_state_rows                        2
rows_with_last_evaluated_as_of           2
rows_matching_latest_decision_as_of      2
rows_not_matching_latest_decision_as_of  0
```

Doğrulama anındaki marker eşleşmeleri:

```text
ETH/BTC latest decision 83  as_of=2026-09-06  marker=2026-09-06
URA/USD latest decision 82  as_of=2026-09-04  marker=2026-09-04
```

Kapanış:

```text
Historical production corruption observed  NO
Repeated same-as-of evaluations             CONFIRMED
Latent reset idempotency risk                CONFIRMED
Hardening                                    VERIFIED
Migration                                    VERIFIED
Same-as-of state idempotency substage        CLOSED
```

### 9.2 Evaluation-time provenance hardening — KAPANDI

İlgili belge:

- `docs/POST_SHADOW_P1_PRODUCTION_REPLAY_PROVENANCE_HARDENING.md`

Production reconstructibility baseline:

```text
ETH/BTC historical decisions                       39
ETH/BTC persisted audit coverage                   strong / 39 of 39
URA/USD historical decisions                       38
URA directional fundamentals complete              36 of 36 positive-quality rows
URA positive-quality breadth rows                   36
historical breadth rows with numeric inputs         0 of 36
historical rows with exact event-set identity       0 of 38
historical rows with breadth/event timestamps       0 of 38
```

Aynı market `as_of` tekrarlarında URA faktör payload'ının gerçekten değişebildiği de doğrulandı:

```text
repeated market dates                    7
repeated decision rows                  19
factor-payload peer difference rows     17 / 19
regime peer difference rows              0
```

Bu nedenle repeated decision history deduplicate edilmez.

Dar audit-only hardening ile yeni URA decision payload'ına şunlar eklendi:

- breadth numeric scoring inputs,
- `breadth_date`,
- breadth row `created_at`,
- exact `event_refs` array,
- `health_checked_at`,
- `health_status`,
- evaluated event count.

Scoring formülü, factor weight, threshold, confidence, K1/K2, reset, sizing, scheduler, mode ve model version değişmedi.

Regression:

```text
focused provenance tests  3 passed
full Python tests          68 passed
release check              OK
```

Windows build/deploy kabulü:

```text
PyInstaller OneDir                       PASS
Inno Setup                               PASS
build EXE SHA256                         91300423EA360C11E923C1AC74F437581BAAEF0DC23CFBA3458B60FB8A29890A
installed EXE SHA256                     same / PASS
service                                  RUNNING / Auto
CLI service-status                       RUNNING / exit 0
settings preservation                    PASS
rosalock preservation                    PASS
post-deploy manual URA runs              2 x OK / exit 0
```

Forward read-only verification sonucu:

```text
latest decision id                       85
system                                   URA/USD
model_version                            1.2.0
as_of                                    2026-09-04
created_at                               2026-09-07T22:30:02.725709+00:00
decision_evaluated_at                    2026-09-07T22:30:00.362158+00:00
status                                   WAIT
direction                                USD→URA
action_event                             false
edge_score                               1.03
confidence                               23.77
data_quality                             90.51
hardened_audit_payload_complete          true
```

Aşağıdaki check'lerin tamamı `true` çıktı:

```text
has_decision_evaluated_at
has_embedded_signal_state
has_breadth_numeric_keys
has_breadth_created_at
has_breadth_date
has_event_refs_array
has_event_health_checked_at
has_event_health_status
has_event_count
fundamentals_directional_inputs_complete
has_macro_values
has_macro_observation_dates
has_macro_freshness_quality
```

Breadth içindeki 50DMA/200DMA değerlerinin `null` olması hata değildir; history henüz olgunlaşmamışken anahtarların ve gerçek null değerlerin korunması audit kontratının parçasıdır. Event tarafında `event_refs=[]` gerçek evaluated set'in boş olduğunu gösterir; historical pre-hardening satırlardaki alan yokluğuyla aynı şey değildir.

Kapanış sınıflandırması:

```text
Audit-only code hardening                 VERIFIED
Production runtime deployment             VERIFIED
Forward new-decision persistence           VERIFIED / decision 85
URA provenance hardening substage          CLOSED
Historical pre-hardening URA rows          NOT BACKFILLED
Raw holdings immutable snapshot history    OPEN
Full production/replay parity              OPEN
LIVE                                       NO-GO
```

### 9.3 Sıradaki açık production/replay araştırmaları

İki konu birbirinden ayrı tutulmalıdır:

1. **Raw source snapshot/versioning gereksinimi:** `fundamentals.ura_holdings` aynı `(holding_date,ticker)` satırını overwrite ettiği için aynı güne ait her raw fetch immutable snapshot olarak tutulmuyor. Persisted decision-input snapshot'larının validation kontratı için yeterli olup olmadığı veya ayrı immutable source-snapshot storage gerekip gerekmediği kanıtla kararlaştırılacak.
2. **Transactional state-before-decision risk analizi:** mevcut `_persist_decision` akışında signal state decision insert'ten önce commit edilir. Teorik olarak state commit başarılı olup decision insert başarısız olursa retry davranışı incelenmelidir. Bunun production'da gerçekleştiğine dair DB kanıtı yoktur; production incident olarak sınıflandırılmaz.

Bu iki açık konu threshold düşürme veya model tuning gerekçesi değildir.

## 10. P2 veri yaşam döngüsü — AÇIK

FRED current/revision/dedup/retention çözümü ayrı araştırma başlığıdır.

Doğrudan `(series_id, observation_date)` UNIQUE migration uygulanmaz. Uygulanmış `0001` migration geriye dönük değiştirilmez. Silme/dedup/backfill migration'ı dry-run ve açık kanıt olmadan çalıştırılmaz.

## 11. P3 model davranışı — yalnız ayrı onayla

Aşağıdakiler PROPOSED kalır:

1. kademeler arasında minimum 5 karar seansı,
2. reversal için iki ardışık qualified karşı-yön kapanışı,
3. production/replay için tek versioned state machine,
4. yeni `max_regime_pct` / sizing yaklaşımı,
5. reset sonrası same-direction K1 değişikliği,
6. threshold/factor-weight değişiklikleri.

Bunlardan biri seçilirse açık kullanıcı onayı + yeni model version + test + deploy + yeni Shadow Epoch gerekir. Mevcut v1.2.0 Shadow kanıtı yeni semantiğe otomatik taşınmaz.

## 12. Mimari süreklilik

Ana akış:

```text
External data
  -> Python Investment Engine
  -> Supabase/PostgreSQL
  -> Signal Engine
  -> public snapshot/API
  -> Quasar
  -> notification / user decision
```

Quasar aynı ana repo altında `tr-rosayazilim-yatirimdashboard` dizinindedir. Tek Auth kullanıcısı + çoklu portföy mimarisi korunur. Quasar gerçek kullanıcı ledger'ını taşır; Python global sistem değerlendirmesini yapar.

Windows hedefi 24/7 servis çalışmasıdır. Bu projede development makinesi aynı zamanda çalışan Shadow service host'udur. Production kurulum/ayar dizinleri ve encrypted settings çözümlemesi verification komutlarında korunur.
