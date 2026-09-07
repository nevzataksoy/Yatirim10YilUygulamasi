# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 07 Eylül 2026  
Amaç: Yeni sohbetin güncel proje durumunu konuşma geçmişini yeniden keşfetmeden devralması.

Kalıcı bağlam `PROJECT_MEMORY_BANK.md`, normatif motor gerçeği `SIGNAL_ENGINE_DECISION_CONTRACT.md`, Shadow adımları root `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`, checkpoint kanıtları `SHADOW_CHECKPOINT_LOG.md`, Post-Shadow P0/P1 kanıtları ise ilgili `POST_SHADOW_*.md` belgelerindedir.

## 1. Aktif repo / branch

```text
Repo   nevzataksoy/Yatirim10YilUygulamasi
Branch agent/portfolio-audit-reset
```

Repo default branch'i `master` olsa da güncel Python/Shadow geliştirme gerçeği `agent/portfolio-audit-reset` branch'indedir.

Bu çalışma ortamında kullanıcının Windows worktree'sine doğrudan erişim yoktur. Yerel repo:

```text
D:\wamp64\www\Yatirim10YilUygulamasi
```

Asistan yerel `git status clean` iddiası yapmaz. Remote gerçeklik GitHub branch ref/commit/blob SHA ile, yerel durum ise kullanıcının verdiği `git rev-parse` / `git status` çıktısıyla doğrulanır.

Her mantıksal değişiklik ayrı commit edilir ve hemen push edilir. Kullanıcıya short SHA, full SHA ve commit mesajı bildirilir. Raw telemetry/log/generated verification dosyaları commit edilmez.

## 2. Anlatım ve proje hakimiyeti kuralı

Bu proje için zorunlu iletişim biçimi `CHATGPT_PROJECT_START_HERE.md` içinde sabittir:

- mümkün olduğunca sade Türkçe kullan,
- yabancı teknik terim gerekiyorsa önce Türkçe anlamını açıkla,
- her teknik adımda **hangi sorunu çözdüğümüzü** anlat,
- kontrolün **neden yapıldığını** belirt,
- sonucun **hangi proje aşamasını etkilediğini** açıkla,
- sonucun **hangi kararı henüz değiştirmediğini** özellikle söyle,
- kullanıcıya yalnız komut değil, projenin neden o komutu çalıştırdığını da aktar.

Bu yaklaşım yeni oturumlarda da vazgeçilmezdir.

## 3. Değişmez released durum

```text
Model Version        1.2.0
Mode                 SHADOW
Realtime Execution   OFF
SHADOW_READINESS     READY
LIVE Graduation      OPEN / NO-GO
```

Released ayarlar değişmemiştir:

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

`direction` emir değildir. `ACTION` tek başına yeni kademe değildir; `action_event=true` gerekir. Python portföy bakiyesi okumaz, otomatik exchange order göndermez ve readiness sonucundan otomatik LIVE'a geçmez.

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

Shadow epoch boyunca gerçek ACTION/WATCH davranışı egzersiz edilmedi:

```text
ETH/BTC WAIT              35 / 35 gün
URA/USD WAIT              33 karar / 24 gün
URA/USD NO_ACTION_DATA    2 karar / 1 gün
Crypto ACTION/WATCH       0 / 0
URA ACTION/WATCH          0 / 0
performance               []
```

Historical replay yönsel doğrulama sağlar fakat production ACTION/state davranışını birebir doğrulamaz. `edge=70` için yeterli sinyal kanıtı yoktur. Bu durum threshold düşürme gerekçesi değildir.

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

## 7. P1 — Walk-forward validation durumu

Expanding walk-forward altyapısı teknik olarak doğrulanmıştır.

Son doğrulanmış ana sonuç:

```text
observations                  1420
folds                         12
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

`selection_status=OK`, tek başına yeterli model kanıtı anlamına gelmez. P1 ortak kanıt sınıflandırması:

```text
LIMITED_TRAIN_SIGNAL_COUNT
LIMITED_OOS_SIGNAL_COUNT
EVIDENCE_AVAILABLE
```

## 8. P1 — FRED strict tarihsel doğrulama durumu

İlgili belgeler:

- `docs/POST_SHADOW_P1_FRED_PIT_BASELINE.md`
- `docs/POST_SHADOW_P1_FRED_STRICT_PIT_COMPARISON.md`

### 8.1 Mevcut Supabase FRED tablosu

Baseline kanıtı:

- `macro.observations` strict ALFRED validity history değildir,
- tekrar tekrar alınmış FRED-current/fetch-day snapshot'larıdır,
- historical cutoff testlerinde local strict PIT coverage yoktur,
- gerçek value revision kanıtlanmıştır,
- özellikle `STLFSI4` çok sayıda revision taşır,
- `DTWEXBGS` için de revision örneği vardır.

Bu nedenle `(series_id, observation_date)` bazında kör dedup yapılmaz ve mevcut tablo strict PIT store diye yorumlanmaz.

### 8.2 Verification-only ALFRED yolu

Production collector davranışı değiştirilmeden ayrı doğrulama yolu kuruldu:

- FRED historical real-time verisi memory içinde çekilir,
- historical `realtime_start/realtime_end` dönemine göre o gün gerçekten yayımlanmış değer seçilir,
- DB'ye yazılmaz,
- threshold/weight/state/mode değiştirilmez.

İlk geniş API isteği 400 verdi; tarih aralığı replay dönemine daraltıldı. API key'in hata URL'sinde görünmesini engelleyen güvenli hata raporu eklendi.

`SP500` FRED'de vardır fakat FRED API cevabına göre ALFRED historical history'si yoktur. Strict replay'de bugünkü değer geçmişe uydurulmaz; kaynak boşluğu sayılır.

### 8.3 Son gerçek veri koşusu

Kullanıcı koşusu:

```text
FRED PIT focused tests       9 passed
Full Python tests            63 passed
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

Eksik 23 günün tamamı `2022-10-18..2022-11-09` ve yalnız `STLFSI4` eksiktir.

Resmî ALFRED kaydı `STLFSI4` serisinin ilk yayımlanma tarihini `2022-11-10` olarak gösterir. Bu collector hatası değildir. Önceki `STLFSI3` serisi sessizce ikame edilmez; böyle bir ikame model/data-source değişikliği sayılır.

### 8.4 Temiz 1397 günlük FRED tarihsel farkı

ALFRED-available 7 serinin de bulunduğu tam-kapsama günlerinde:

```text
common dates                         1397
mean abs edge delta                  0.5222834646
max abs edge delta                   14.27
regime change dates                  19
direction-sign change dates          5
edge=70 qualification change dates   0
```

Örnek büyük farklar:

```text
2025-04-04   30.75 -> 16.48   RISK_OFF -> NEUTRAL
2025-04-05   30.96 -> 16.82   RISK_OFF -> NEUTRAL
2025-04-06   34.07 -> 20.28   RISK_OFF -> NEUTRAL
2025-04-07   36.06 -> 22.69   RISK_OFF -> NEUTRAL
2025-04-21   20.12 -> 31.83   NEUTRAL  -> RISK_OFF
2023-03-22   38.38 -> 45.58   NEUTRAL  -> RISK_ON_TREND
```

Ana yorum:

- FRED revision/yayın-zamanı farkı motorun iç edge ve rejim yorumunu bazı günlerde gerçekten değiştirir.
- Ancak tam kapsamalı 1397 günün hiçbirinde released `edge=70` uygunluğu değişmez.
- Dolayısıyla mevcut edge=70 sinyal kıtlığı FRED revision etkisiyle açıklanamamaktadır.
- Bu sonuç threshold düşürme veya LIVE gerekçesi değildir.

### 8.5 FRED walk-forward sınıflandırması — RETEST REQUIRED

Son kullanıcı koşusunda eski ham helper alanı:

```text
current status       LIMITED_SIGNAL_COUNT / edge70=0
comparable status    LIMITED_SIGNAL_COUNT / edge70=0
strict status        OK / edge70=0
```

Buradaki strict `OK` yeterli kanıt anlamına gelmiyordu; yalnız aday seçimi çalışabiliyordu.

FRED doğrulama komutu artık ana walk-forward ile aynı evidence classifier'ı kullanacak şekilde güncellendi ve ayrıca 1397 günlük clean walk-forward üretecek.

Bu yeni raporlama kodu unit test ile korunmuştur fakat **gerçek FRED ortamında son kez yeniden çalıştırılmayı beklemektedir**. FRED P1 alt aşamasını `CLOSED` yapmadan önce bu retest alınmalıdır.

## 9. P1 sıradaki adımlar

FRED evidence-status retest tamamlandıktan sonra önerilen sıra:

1. FRED strict macro PIT alt aşamasını sonuçlandır.
2. Production vs replay factor/state/action gap raporu üret.
3. Aynı piyasa `as_of` tarihindeki scheduler tekrarlarını bağımsız market day saymama semantiğini netleştir.
4. K1/K2/reversal/reset persistent state davranışını replay ile karşılaştır.
5. Derivatives/event PIT açığını ayrıca sınıflandır.
6. URA full PIT için trustworthy history biriktir/araştır.

P1 evidence çalışmasıdır. Otomatik olarak threshold, factor weight, K1/K2, reversal/reset, sizing, model version, mode veya LIVE değiştirmez.

## 10. P2 veri yaşam döngüsü — AÇIK

FRED current/revision/dedup/retention çözümü P1 kanıtına bağlı olarak açık araştırma başlığıdır.

Doğrudan `(series_id, observation_date)` UNIQUE migration uygulanmaz. Önce strict PIT gereksinimi ve revision history semantiği tamamlanır.

Uygulanmış `0001` migration geriye dönük değiştirilmez. Silme/dedup/backfill migration'ı dry-run ve açık kanıt olmadan çalıştırılmaz.

## 11. P3 model davranışı — yalnız ayrı onayla

Aşağıdakiler PROPOSED kalır:

1. kademeler arasında minimum 5 karar seansı,
2. reversal için iki ardışık qualified karşı-yön kapanışı,
3. production/replay için tek versioned state machine,
4. yeni `max_regime_pct` / sizing yaklaşımı,
5. reset sonrası same-direction K1 değişikliği,
6. threshold/factor-weight değişiklikleri.

Bunlardan biri seçilirse açık kullanıcı onayı + yeni model version + test + deploy + yeni Shadow Epoch gerekir. Mevcut v1.2.0 Shadow kanıtı yeni semantiğe otomatik taşınmaz.

## 12. Quasar bağlamı

- Quasar aynı ana repo altında `tr-rosayazilim-yatirimdashboard` dizinindedir.
- Tek Auth kullanıcısı + çoklu portföy mimarisi korunur.
- Account-scoped ledger, append-only revision/cancellation, reset RPC ve connection/Auth hardening mevcut bağlamın parçasıdır.
- Signal/market/validation/health global; portföy işlemleri account scoped.
- Python önerisi hard limit değildir; kullanıcı nihai dönüşüm kararını verir.
- P0/P1 çalışması Quasar ürün davranışlarını otomatik değiştirmez.

## 13. Yeni oturum başlangıç protokolü

1. `CHATGPT_PROJECT_START_HERE.md` tamamen oku.
2. `docs/PROJECT_MEMORY_BANK.md`, `docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`, `docs/SESSION_HANDOFF.md` tamamen oku.
3. Python işi ise root görev takvimini ve ilgili P0/P1 belgelerini oku.
4. `RELEASED / APPROVED / PROPOSED / OPEN` ayrımını koru.
5. Remote `agent/portfolio-audit-reset` HEAD ve değiştirilecek blob SHA'yı yeniden doğrula.
6. Kullanıcının son push'ını okumadan yazma yapma.
7. Runtime iddiasını gerçek code/deployment/user output ile kanıtla.
8. Model davranışı değişiyorsa önce açık kullanıcı onayı + version/epoch etkisini belirt.
9. Her mantıksal repo değişikliğini ayrı commit yap ve hemen push et; short SHA, full SHA ve commit mesajını kullanıcıya bildir.
10. Raw telemetry/log/generated verification çıktılarını commit etme.

## 14. Güvenlik sınırı

API key, parola, Telegram token/Chat ID, DB password veya service-role secret bağlam belgelerine yazılmaz.

Otomatik exchange order, otomatik LIVE ve validation sonucundan otomatik threshold/weight değişikliği yoktur.
