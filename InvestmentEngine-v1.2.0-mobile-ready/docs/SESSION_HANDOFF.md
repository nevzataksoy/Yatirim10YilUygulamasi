# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 07 Eylül 2026  
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

## 9. P1 — Aktif sıradaki aşama: production vs replay parity

FRED strict-PIT alt aşaması kapandı. P1'in aktif ana sorusu artık şudur:

> Geçmiş replay ile üretimde çalışan gerçek karar zinciri aynı bilgiyi gördüğünde aynı factor, quality/confidence kapısı, rejim, persistent state ve ACTION davranışını üretiyor mu?

Bu aşamanın amacı model ayarı değiştirmek değil, geçmiş doğrulamanın production davranışına ne kadar benzediğini ölçmektir.

Önce veri ve kod kabiliyeti çıkarılacak; doğrudan K1/K2 replay kodu yazılmayacaktır. Özellikle şu sorular doğrulanacaktır:

1. Üretim `daily_crypto_job` hangi veri kesim zamanını ve hangi factor'ları kullanıyor?
2. Replay aynı factor/quality/confidence/regime hesabını mı kullanıyor?
3. Aynı piyasa `as_of` tarihindeki tekrar scheduler koşuları nasıl saklanıyor ve state'i kaç kez ilerletiyor?
4. K1/K2, reversal ve reset state'i hangi tablolarda/alanlarda tutuluyor?
5. `ACTION` ile `action_event=true` ayrımını geçmiş kayıtlardan yeniden kurabiliyor muyuz?
6. Derivatives/event geçmişi eksik olduğunda production ile replay karşılaştırmasının sınırı nedir?
7. Market `as_of` ile kararın gerçek çalışma zamanı / o anda bilinen makro veri kesimi aynı kavram mı, ayrı mı tutulmalı?

Bu soruların cevabı alınmadan production state-machine'i taklit eden yeni replay yazılmaz.

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

## 13. Yeni oturum başlangıç sırası

Yeni oturumda:

1. bu `SESSION_HANDOFF.md` dosyasını oku,
2. `PROJECT_MEMORY_BANK.md` dosyasını oku,
3. `SIGNAL_ENGINE_DECISION_CONTRACT.md` dosyasını oku,
4. aktif branch HEAD'ini doğrula,
5. kullanıcı yerel HEAD/status verdiyse remote ile karşılaştır,
6. FRED strict-PIT'i yeniden keşfetme; alt aşama `CLOSED`,
7. aktif P1 konusu olarak production-vs-replay parity veri/kod gap analizinden devam et,
8. production davranışını değiştirmeden önce verification-only/read-only kanıt üret.

## 14. Son karar özeti

```text
Tasks 1-7 / Shadow calendar          PASS / COMPLETE
SHADOW_READINESS                     READY
LIVE                                 NO-GO
P0 runtime reliability development   CLOSED
P1 walk-forward implementation       CLOSED / evidence limited
P1 FRED strict-PIT                    CLOSED / evidence limited
P1 production-vs-replay parity       ACTIVE / NEXT
P2 FRED lifecycle                    OPEN
P3 model changes                     NOT AUTHORIZED
Model                                1.2.0 unchanged
Mode                                 SHADOW
Realtime execution                   OFF
```
