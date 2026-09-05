# Investment Engine — Shadow Görev Takvimi

**Takvim başlangıcı:** 31.07.2026 00:23 TRT  
**Shadow başlangıcı:** 30.07.2026 akşamı  
**İlk 30 günlük değerlendirme:** 29.08.2026  
**Motor modu:** `SHADOW`  
**Realtime Execution:** `OFF`

Amaç motoru mümkün olduğunca müdahalesiz çalıştırmak, belirli tarihlerde operasyonel/veri/model kanıtı toplamak ve Python geliştirmesini bu kanıt sınıflarına göre sürdürmektir.

## 1. 30 gün boyunca değiştirilmeyecekler

```text
Mode                  = SHADOW
Realtime Execution    = OFF
Min Data Quality      = 80
Min Edge              = 70
Min Confidence        = 70
Strong Edge           = 80
Strong Confidence     = 80
```

Normal durumda servis durdurulmaz ve `--once crypto/ura/hourly` çalıştırılmaz. Manuel job yalnız gerçek scheduler hatası analizinde ayrıca kararlaştırılır.

## 2. Görevler

### Görev 1 — 31.07.2026 07:00 TRT

İlk otomatik günlük döngü: service status, son 30 job, son v1.2 kararları ve engine health.

**Sonuç:** `PASS`. Ayrıntı `SHADOW_CHECKPOINT_LOG.md`.

### Görev 2 — 31.07.2026 17:15 TRT

TCMB/FX: `USD/TRY` market snapshot, `FX` health ve son `daily_fx_job` kayıtları.

**Sonuç:** `PASS`. Ayrıntı `SHADOW_CHECKPOINT_LOG.md`.

### Görev 3 — 01.08.2026 09:30 TRT

Weekly + Monthly Audit scheduler testi.

```sql
select job_name, started_at, finished_at, status, message, details
from system.job_runs
where job_name in ('weekly_job', 'monthly_audit_job')
order by started_at desc
limit 10;
```

```sql
select validation_type, system, model_version, status,
       start_date, end_date, metrics, details, generated_at
from public.model_validation_snapshot
order by validation_type, system;
```

```sql
select id, validation_type, system, model_version, status,
       started_at, finished_at, observations, signals
from model.validation_runs
order by id desc
limit 20;
```

`SHADOW_READINESS=NOT_READY` normaldir.

**Sonuç:** `PASS`. Weekly job 08:00 TRT, monthly audit 09:00 TRT'de başlayıp `OK`
tamamlandı. Ayrıntı `SHADOW_CHECKPOINT_LOG.md`.

### Görev 4 — 07.08.2026 10:30 TRT

7 günlük ilk gerçek güvenilirlik checkpoint'i.

1. Service status.
2. `--test-realtime --realtime-seconds 20`.
3. `--validate-model`.
4. Son 7 gün job/status sayıları ve hatalar.
5. Shadow readiness stats/waiting reasons/blockers.
6. Sistem bazlı decision days ve median/min/max quality.
7. URA holdings tarih/coverage birikimi.
8. Son realtime test snapshot özeti.

Bu görevden sonra davranış değiştirmeden Shadow Epoch, run-kind, expected/actual runs, OK/completed rate ve edge/status diagnostics değerlendirilebilir. Threshold değiştirilmez.

### Görev 5 — 14.08.2026 10:30 TRT

14 günlük stabilite.

Görev 4 kontrolleri tekrarlanır; ayrıca sistem/status karar sayıları çıkarılır. BTC/ETH quality, URA quality trendi, scheduler tekrar eden hataları, realtime trade gap ve WAIT/NO_ACTION_DATA dağılımı incelenir.

### Görev 6 — 20.08.2026 10:30 TRT

URA 20 günlük ara değerlendirmesi.

- Validation ve readiness.
- Bütün v1.2 URA kararları.
- Son URA factor score/quality/weight/details.
- Holdings history gün sayısı.
- Son 7 gün hata özeti.

Karar ağacı:

- URA median quality `>=80`: Shadow değiştirilmeden devam.
- `70–79`: fundamentals/breadth/event katkıları ayrı analiz.
- `<70`: provider/freshness/history regresyonu aranır.

### Görev 7 — 29.08.2026 10:30 TRT

30 günlük Shadow Graduation Review.

- Service, realtime smoke, validation.
- Readiness criteria/stats/blockers.
- 30 günlük job özeti ve hatalar.
- Sistem/status karar sayıları, median quality/edge/confidence.
- Validation snapshot'ları.
- URA holdings günleri.
- Realtime test özeti.

Hedefler:

```text
Shadow calendar days       >= 30
ETH/BTC decision days      >= 25
URA/USD decision days      >= 20
ETH/BTC median quality     >= 80
URA/USD median quality     >= 80
URA holdings dates         >= 2
URA breadth dates          >= 20
Recent job success         >= 98%
Realtime smoke age         <= 7 gün
```

Hepsi geçse bile `SHADOW -> LIVE` otomatik yapılmaz. PIT, walk-forward, monthly realized ve Shadow sonuçları manuel production review'da birlikte değerlendirilir.

## 3. Hata halinde

Takvim tarihi beklenmeden şu iki sorgu paylaşılır:

```sql
select job_name, started_at, finished_at, status, message, details
from system.job_runs
where status <> 'OK'
order by started_at desc
limit 20;
```

```sql
select component, status, message, checked_at, details
from public.engine_health_snapshot
order by component;
```

Aynı job art arda manuel çalıştırılmaz.

## 4. Sonuç paylaşım formatı

```text
CHECKPOINT:
Tarih/Saat:
Service:
Engine Version:

1. Job/Realtime:
2. Readiness:
3. Decisions/Quality:
4. Health/Errors:
```

## 5. Paralel Python geliştirme planı

```text
31 Temmuz – 7 Ağustos
    Shadow Epoch
    Edge diagnostics
    readiness hardening

7 – 14 Ağustos
    Edge / Confidence / Quality bucket analizi
    walk-forward validation

14 – 20 Ağustos
    strict macro point-in-time / vintage
    historical replay hardening

20 – 29 Ağustos
    Shadow – validation karşılaştırması
    URA quality analizi
    release hardening

29 Ağustos
    Shadow Graduation Review
```

Bu tarihler geliştirme için bekleme süresi değildir; sunucu veri toplarken davranış değiştirmeyen hardening paralel yapılabilir.
