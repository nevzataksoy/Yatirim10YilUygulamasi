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

## 2. Zorunlu anlatım ve proje hakimiyeti kuralı

Bu proje için iletişim yalnız komut/kod vermekten ibaret değildir. Her teknik adımda mümkün olduğunca sade Türkçe ile:

- hangi sorunun çözüldüğü,
- kontrolün neden yapıldığı,
- sonucun hangi aşama veya durumu etkilediği,
- hangi kararı henüz değiştirmediği,
- bir sonraki adımın neden gerekli olduğu

anlatılır. Yabancı teknik terim gerekiyorsa önce Türkçe anlamı verilir. Bu yaklaşım `CHATGPT_PROJECT_START_HERE.md` içinde vazgeçilmez proje kuralıdır.

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

`direction` emir değildir. `ACTION` tek başına yeni kademe değildir; yeni kademe davranışı için `action_event=true` gerekir. Python kullanıcı portföy bakiyesine göre karar vermez, otomatik exchange order göndermez ve readiness sonucundan otomatik LIVE'a geçmez.

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

URA full PIT de henüz yeterli tarihsel holdings/breadth/event geçmişine sahip değildir.

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

`SP500` FRED'de vardır fakat FRED API cevabına göre ALFRED historical history'si yoktur. Strict replay'de bugünkü SP500 geçmişe uydurulmaz; kaynak boşluğu kabul edilir.

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

Eksik 23 günün tamamı `2022-10-18..2022-11-09` ve yalnız `STLFSI4` eksiktir. Resmî ALFRED kaydına göre `STLFSI4` ilk kez `2022-11-10` tarihinde yayımlanmıştır. Bu collector hatası değildir. Önceki `STLFSI3` sessizce ikame edilmez; bu model/data-source değişikliği sayılır.

### 8.4 Temiz 1397 günlük tarihsel fark

ALFRED geçmişi bulunan 7 serinin de mevcut olduğu günlerde:

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

Karar için esas alınan satır tam kapsamalı `strict_complete_coverage_walk_forward` sonucudur. Burada yayımlanmış edge70 için sinyal `0`, daha düşük keşif adaylarında bağımsız test sinyali de `0`dır.

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

FRED current/revision/dedup/retention veri yaşam döngüsü ise ayrı P2 başlığıdır; bu kapanış P2'yi kapatmaz.

## 9. P1 — Production vs replay parity

### 9.1 Same-market-date signal-state idempotency — KAPANDI

İlgili belge:

- `docs/POST_SHADOW_P1_PRODUCTION_REPLAY_STATE_IDEMPOTENCY.md`

Production read-only baseline ve tekrar-detail sorguları şunları kanıtladı:

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

Bu geçmişte state corruption görülmediğini gösterdi; fakat iki sistemde de `action_event=0` ve state pasif olduğu için aktif rejim reset dalı production geçmişinde egzersiz edilmemişti.

Kod RCA'sında `reset_counter` market-günü kuralı olmasına rağmen aynı market `as_of` tekrarında yeniden artabilen latent risk doğrulandı. URA tekrar-detail kanıtı aynı market gününün farklı evaluation zamanlarında güncellenmiş `macro`, `fundamentals`, `breadth` ve `event` girdileriyle tekrar değerlendirilebildiğini gösterdi; bu nedenle scheduler tekrarlarını körlemesine engellemek doğru çözüm değildi.

Uygulanan en küçük hardening:

- `model.signal_state.last_evaluated_as_of` eklendi,
- `reset_counter` yalnız yeni market `as_of` geldiğinde +1 ilerler,
- aynı `as_of` tekrarında ikinci kez artmaz,
- aynı gün aktif yön edge'i released `reset edge=45` üzerine geri çıkarsa sayaç yine 0'a dönebilir,
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
column_present                         true
trigger.present                        true
trigger.enabled                        true
signal_state_rows                      2
rows_with_last_evaluated_as_of         2
rows_matching_latest_decision_as_of    2
rows_not_matching_latest_decision_as_of 0
```

Doğrulama anındaki marker eşleşmeleri:

```text
ETH/BTC latest decision 83  as_of=2026-09-06  marker=2026-09-06
URA/USD latest decision 82  as_of=2026-09-04  marker=2026-09-04
```

Kapanış sınıflandırması:

```text
Historical production corruption observed  NO
Repeated same-as-of evaluations             CONFIRMED
Latent reset idempotency risk                CONFIRMED
Hardening                                    VERIFIED
Migration                                    VERIFIED
Same-as-of state idempotency substage        CLOSED
```

### 9.2 Aktif sıradaki alt aşama: evaluation-time provenance parity

Full production/replay parity **henüz kapanmadı**.

Artık ana soru şudur:

> Aynı market `as_of` tekrar değerlendirildiğinde production'ın o gerçek evaluation anında bildiği source snapshot'ları replay tarafından yeniden kurulabiliyor mu?

Market `as_of` tek başına production bilgi setini tanımlamıyor. En az şu zaman kavramları ayrılmalıdır:

1. market `as_of`,
2. gerçek decision evaluation zamanı,
3. source-specific observation/fetch zamanları,
4. o evaluation anında eligibility taşıyan macro/fundamentals/breadth/event/derivatives snapshot'ları.

Özellikle:

- production `daily_crypto_job` / `daily_ura_job` veri kesim semantiği,
- replay factor/quality/confidence/regime hesapları,
- `ACTION` ile `action_event=true` ayrımının replay'de korunması,
- derivatives/event historical coverage boşlukları,
- decision provenance içindeki gerçek timestamp coverage

ölçülmeden production state-machine'i taklit eden yeni geniş replay yazılmaz.

Bu aşama threshold düşürme veya model tuning gerekçesi değildir.

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

Windows hedefi 24/7 servis çalışmasıdır. Production kurulum/ayar dizinleri ve encrypted settings çözümlemesi verification komutlarında korunur.
