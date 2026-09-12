# Investment Engine — Shadow Checkpoint Sonuç Günlüğü

Son güncelleme: 07 Ağustos 2026  
Model ailesi: `1.2.x`  
Deployed model: `1.2.0`  
Mode: `SHADOW`  
Realtime Execution: `OFF`

Bu belge görev takvimindeki sonuçları kümülatif taşır. Bir görev ancak kullanıcı gerçek çıktıları paylaştıktan ve scheduler/provider/freshness/snapshot/health/job-audit tutarlılığı incelendikten sonra `PASS` sayılır.

## Görev 1 — 31.07.2026, ilk otomatik günlük döngü

**Sonuç: PASS**

### Servis

```text
SERVICE_NAME: RosaInvestmentEngine
STATE: 4 RUNNING
WIN32_EXIT_CODE: 0
SERVICE_EXIT_CODE: 0
```

### Scheduler kanıtı

- Hourly derivatives: otomatik çalıştı.
- Macro: otomatik çalıştı.
- SEC event: otomatik çalıştı.
- Daily URA: 02:40 TRT, otomatik çalıştı.
- Daily crypto: 05:20 TRT, otomatik çalıştı.

PostgreSQL kayıtları UTC, scheduler logları Europe/Istanbul (`+03`) gösterir. Örneğin `05:20 TRT = 02:20 UTC`; bu saat kayması değildir.

### Son kararlar

```text
ETH/BTC
as_of:        2026-07-30
direction:    BTC→ETH
edge:         35.640
confidence:   46.250
data_quality: 90.450
status:       WAIT
model:        1.2.0

URA/USD
as_of:        2026-07-30
direction:    URA→USD
edge:         33.990
confidence:   36.170
data_quality: 70.400
status:       NO_ACTION_DATA
model:        1.2.0
```

### Provider ve health yorumu

- Deribit bağlantısı tekrar eden connect timeout verdi.
- Aynı BTC+ETH çifti atomik biçimde OKX fallback ile alındı.
- `DERIVATIVES=OK`, `fallback_used=true`; sistem etkilenmeden devam etti.
- Macro quality `97.5`; stale/missing yok, `DTWEXBGS` degraded.
- SEC event job scheduler açısından tamamlandı; fund-weight coverage `%14.04` olduğu için `DEGRADED`.
- URA job teknik olarak `OK`; karar `NO_ACTION_DATA`. Job sağlığı ile karar yeterliliği birbirine karıştırılmaz.

### Karar

- Servis SHADOW çalışmaya devam eder.
- Realtime Execution açılmaz.
- Threshold/weight/mode değiştirilmez.
- Deribit kaldırılmaz; fallback gözlemlenir.
- SEC coverage yapay olarak yükseltilmez.
- Manuel daily job tekrarı yapılmaz.

## Görev 2 — 31.07.2026, TCMB/FX otomatik işi

**Sonuç: PASS**

```text
Planlanan zaman: 31.07.2026 16:30 TRT
Gerçek başlangıç: 31.07.2026 13:30 UTC
TCMB data date: 31.07.2026
USD/TRY: 47.4305
Health: FX=OK
Job: OK
Süre: yaklaşık 2.48 saniye
```

`market_snapshot`, `engine_health_snapshot` ve `system.job_runs` tutarlı bulundu. FX sonucu tek başına directional model değişikliği gerekçesi değildir.

## Görev 3 — 01.08.2026 09:30 TRT

**Sonuç: PASS**

### Scheduler

- `weekly_job` 08:00 TRT'de başladı, 08:01:15 civarında `OK` tamamlandı.
- `monthly_audit_job` 09:00 TRT'de başladı, 09:01:16 civarında `OK` tamamlandı.
- PostgreSQL UTC kayıtları sırasıyla `05:00` ve `06:00` olup TRT loglarıyla uyumludur.
- Servis görevlerden önce ve sonra `RUNNING`; exit code `0`dır.
- İlgili loglarda `ERROR`, `WARNING`, traceback veya scheduler misfire görülmedi.

### Weekly sonucu

- Holdings tarihi `2026-07-31`, holdings sayısı `58`.
- Breadth quality `%19,195`. Bu scheduler hatası değildir; yalnız üç breadth günü bulunduğu için 20/50/200 günlük bileşenler henüz oluşmamıştır.

### Monthly audit ve readiness

- ETH/BTC historical as-of directional-core replay `OK`.
- Observation sayısı `1383`; dönem `2022-10-18 – 2026-07-31`.
- Configured edge `70` sinyali `0`; calibration `LIMITED_SIGNAL_COUNT`, `best_candidate=null`.
- Mature `ACTION/WATCH` olmadığı için performance değerlendirmesi `0`; bu normaldir.
- Weight veya threshold değişmedi.
- Readiness `NOT_READY`: Shadow `3/30`, ETH/BTC karar günü `3/25`, URA/USD `2/20`, URA breadth `3/20`, URA median quality `%70,4`, recent job success `%97,115`.
- ETH/BTC median quality `%90,45`, realtime test yaşı `1,49` gün ve holdings günü kriterleri geçmiştir.

Recent job success hedefinin altında kalan üç eski kayıt Görev 3 weekly/monthly işleri değildir. Görev 4'te son yedi günlük başarısız iş sorgusuyla kökleri ayrılır.

## Görev 4 — 07.08.2026, 7 günlük ilk Shadow kontrolü

**Sonuç: PASS**

### Servis ve realtime

- `RosaInvestmentEngine` `RUNNING`; Windows ve service exit code `0`.
- Coinbase realtime smoke test `OK`.
- Test run: `36185c91-7358-43f7-97f0-e2bc5720211e`.
- 8 snapshot, 2 ürün (`BTC-USD`, `ETH-USD`), `max_trade_gap=0`.
- Realtime Execution açılmadı ve test ACTION üretmedi.

### Validation ve readiness

- Model validation `OK`.
- ETH/BTC core replay `OK`, `1389` observation.
- `SHADOW_READINESS=NOT_READY`.
- `blockers=[]`; yani quality/job/realtime kaynaklı graduation blocker yoktur.
- Waiting yalnız history birikimidir:
  - Shadow `9/30` gün,
  - ETH/BTC `9/25` karar günü,
  - URA/USD `6/20` karar günü,
  - URA breadth `6/20` gün.

### Karar kalitesi

```text
ETH/BTC: 9 decision days, median 90.83, min 90.08, max 91.20
URA/USD: 6 decision days, median 87.48, min 70.40, max 87.85
```

URA median quality artık 80 üstündedir; tek düşük ilk gün kaydı medianı graduation blocker seviyesine çekmemektedir. Threshold/weight değiştirilmedi.

### Holdings

- 6 ayrı holdings tarihi oluştu.
- Son snapshot'larda 58 constituent vardır.
- Weight coverage yaklaşık `0.9942–0.9991`; holdings zinciri sağlıklıdır.

### 7 günlük scheduler sonucu

Raw job özeti:

```text
daily_crypto_job      OK          7
daily_fx_job          OK          5
daily_ura_job         OK          7
hourly_job            ERROR       3
hourly_job            OK        165
macro_job             OK         29
model_validation_job  OK          1
monthly_audit_job     OK          1
realtime_test         OK          1
sec_event_job         DEGRADED   169
weekly_job             OK          1
```

Kritik teşhis:

- `hourly_job = 165 OK + 3 ERROR = 168`. Bu tam `7 x 24` planlı scheduler run'ıdır. Üç hata gerçek scheduled connection-pool hatasıdır; development artığı diye silinmez veya yeniden etiketlenmez.
- `macro_job=29` iken scheduler contract 28 root run bekler. Ek kayıt `weekly_job` içindeki maintenance çağrısıdır.
- `sec_event_job=169` iken scheduler contract 168 root run bekler. Ek kayıt yine `weekly_job` içindeki maintenance çağrısıdır.
- `model_validation_job` ve `realtime_test` manuel/test işidir; scheduler reliability paydasına root scheduled run gibi girmemelidir.
- SEC `DEGRADED`, job crash'i değildir. Doğrudan eşleşebilen beş SEC ticker'ı URA'nın yaklaşık `%20–21` fund weight'ini kapsadığı için released quality semantiğiyle degraded kalmaktadır.

Görev 4 penceresi için gerçek scheduler contract root beklentisi:

```text
hourly 168 + macro 28 + SEC 168 + crypto 7 + URA 7 + FX 5 + weekly 1 + monthly 1 = 385
```

Bu bulgu readiness sonucunu yapay biçimde PASS yapmak için değil, expected/actual ve scheduled/manual/dependency/maintenance ayrımını denetlenebilir hale getirmek için kullanılacaktır.

### Görev 4 sonrası hardening durumu

- **RELEASED:** v1.2.0 threshold, factor weight, K1/K2, reversal, reset, action-size ve mode semantiği aynıdır.
- **APPROVED:** davranış değiştirmeyen Shadow observability hardening.
- **PROPOSED:** model davranışı önerilerinin hiçbiri bu checkpoint ile onaylanmadı.
- **OPEN:** migration `0010`, yeni run-kind/Shadow Epoch provenance ve `--shadow-observability` komutunun gerçek Windows/Supabase ortamında deploy + runtime doğrulaması.

Detaylı tasarım ve rollout: `docs/SHADOW_TASK4_HARDENING.md`.

## Sonraki checkpoint'ler

- 14.08.2026 10:30 — Görev 5, 14 günlük stabilite.
- 20.08.2026 10:30 — Görev 6, URA quality değerlendirmesi.
- 29.08.2026 10:30 — Görev 7, Shadow Graduation Review.

## Genel kural

Bir hata görünürse takvim tarihi beklenmez; job ve health çıktısı paylaşılır. Aynı job art arda manuel çalıştırılmaz. Özellikle kota/burst sorunlarında tekrarlar teşhisi bozabilir.
