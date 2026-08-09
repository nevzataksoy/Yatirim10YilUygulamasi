# Investment Engine — Shadow Görev Takvimi

**Takvim başlangıcı:** 31.07.2026 00:23 — Türkiye (Europe/Istanbul)  
**Shadow başlangıcı:** 30.07.2026 akşamı  
**İlk 30 günlük değerlendirme hedefi:** 29.08.2026  
**Motor modu:** `SHADOW`  
**Realtime Execution:** `OFF`

> Amaç: Motoru mümkün olduğunca müdahalesiz çalıştırmak; belirli kontrol günlerinde sonuçları toplamak ve bu sonuçlara göre Python/model geliştirmesine devam etmek.

---

## 0. Bu 30 gün boyunca değiştirilmeyecekler

Aşağıdaki değerleri test sonuçlarına bakmadan değiştirme:

```text
Mode                  = SHADOW
Realtime Execution    = OFF
Min Data Quality      = 80
Min Edge              = 70
Min Confidence        = 70
Strong Edge           = 80
Strong Confidence     = 80
```

Normal durumda servisi durdurma ve `--once crypto`, `--once ura`, `--once hourly` çalıştırma.

Manuel `--once` komutları yalnızca bir scheduler işi gerçekten başarısız olduğunda ve hata analizi için ayrıca karar verdiğimizde kullanılacak.

---

# Görev 1 — 31.07.2026 Cuma, 07:00 TRT - PASS
## İlk otomatik günlük döngünün kontrolü

Bu saate kadar servis kendi scheduler'ı ile URA, hourly/macro ve crypto işlerinin en az bir bölümünü çalıştırmış olmalı.

### 1.1 Servis

```bat
cd /d "C:\Program Files\Rosa\InvestmentEngine"
InvestmentEngineCLI.cmd --service-status
```

Beklenen:

```text
STATE : 4 RUNNING
```

### 1.2 Son job kayıtları

```sql
select
    job_name,
    started_at,
    finished_at,
    status,
    message,
    details
from system.job_runs
order by started_at desc
limit 30;
```

### 1.3 Son kararlar

```sql
select
    id,
    system,
    as_of,
    direction,
    edge_score,
    confidence,
    data_quality,
    status,
    model_version,
    created_at
from model.decisions
where model_version like '1.2.%'
order by created_at desc
limit 20;
```

### 1.4 Health

```sql
select
    component,
    status,
    message,
    checked_at,
    details
from public.engine_health_snapshot
order by component;
```

### Bana gönder

1. `--service-status` çıktısı  
2. Son 30 `job_runs` sonucu  
3. Son kararlar  
4. `engine_health_snapshot`

**Bu kontrolde servisi durdurma.**

---

# Görev 2 — 31.07.2026 Cuma, 17:15 TRT - PASS
## TCMB/FX otomatik iş kontrolü

Cuma 16:30 planlanan FX işinden sonra:

```sql
select *
from public.market_snapshot
where symbol = 'USD/TRY';
```

```sql
select *
from public.engine_health_snapshot
where component = 'FX';
```

```sql
select
    job_name,
    started_at,
    finished_at,
    status,
    message,
    details
from system.job_runs
where job_name = 'daily_fx_job'
order by started_at desc
limit 5;
```

### Bana gönder

Bu üç sorgunun sonuçlarını gönder. Hata yoksa başka işlem yapma.

---

# Görev 3 — 01.08.2026 Cumartesi, 09:30 TRT - PASS
## Weekly + Monthly Audit scheduler testi

Cumartesi 08:00 `weekly_job`, ayın 1'i 09:00 `monthly_audit_job` çalışmış olmalı.

### 3.1 Job kontrolü

```sql
select job_name, started_at, finished_at, status, message, details from system.job_runs
where job_name in ('weekly_job', 'monthly_audit_job') order by started_at desc limit 10;
```

### 3.2 Validation snapshot

```sql
select validation_type, system, model_version, status, start_date, end_date, metrics, details, generated_at from public.model_validation_snapshot order by validation_type, system;
```

### 3.3 Validation run geçmişi
```sql
select id, validation_type, system, model_version, status, started_at, finished_at, observations, signals from model.validation_runs order by id desc limit 20;
```

### Bana gönder

Bu üç sonucu gönder.

Bu aşamada `SHADOW_READINESS = NOT_READY` olması normaldir.

---

# Görev 4 — 07.08.2026 Cuma, 10:30 TRT
## 7 günlük ilk Shadow kontrolü

Bu kontrol ilk gerçek güvenilirlik checkpoint'idir.

### 4.1 Servis

```bat
InvestmentEngineCLI.cmd --service-status
```

### 4.2 Realtime smoke testini yenile

Bu test ACTION üretmez ve Realtime Execution'ı açmaz.

```bat
InvestmentEngineCLI.cmd --test-realtime --realtime-seconds 20
```

### 4.3 Validation

```bat
InvestmentEngineCLI.cmd --validate-model
```

Validation'ın bitmesini bekle.

### 4.4 Son 7 günlük job özeti

```sql
select
    job_name,
    status,
    count(*) as run_count
from system.job_runs
where started_at >= now() - interval '7 days'
group by job_name, status
order by job_name, status;
```

### 4.5 Son 7 günlük hatalar

```sql
select
    job_name,
    started_at,
    finished_at,
    status,
    message,
    details
from system.job_runs
where started_at >= now() - interval '7 days'
  and status <> 'OK'
order by started_at desc;
```

### 4.6 Readiness

```sql
select
    status,
    metrics->'stats' as stats,
    metrics->'waiting_reasons' as waiting_reasons,
    metrics->'blockers' as blockers,
    generated_at
from public.model_validation_snapshot
where validation_type = 'SHADOW_READINESS'
  and system = 'ALL';
```

### 4.7 Karar istatistiği

```sql
select
    system,
    count(distinct as_of) as decision_days,
    round(
        (percentile_cont(0.5) within group (order by data_quality))::numeric,
        2
    ) as median_quality,
    round(min(data_quality)::numeric, 2) as min_quality,
    round(max(data_quality)::numeric, 2) as max_quality
from model.decisions
where model_version like '1.2.%'
group by system
order by system;
```

### 4.8 Holdings birikimi

```sql
select
    holding_date,
    count(*) as constituents,
    round(sum(weight)::numeric, 4) as weight_coverage
from fundamentals.ura_holdings
group by holding_date
order by holding_date desc;
```

### 4.9 Realtime test sonucu

```sql
select
    test_run_id,
    min(observed_at) as first_snapshot,
    max(observed_at) as last_snapshot,
    count(*) as snapshots,
    count(distinct product) as products,
    max(trade_gap_count) as max_trade_gap
from market.execution_snapshots
where is_test = true
  and observed_at >= now() - interval '30 minutes'
group by test_run_id
order by max(observed_at) desc
limit 3;
```

### Bana gönder

Görev 4'teki bütün çıktıları gönder.

### Bu checkpoint sonrası Python tarafında

Sonuçlara göre:

- Shadow Epoch / readiness ölçümünü temizleyeceğiz.
- Edge dağılımı ve Edge bucket diagnostics geliştirmesini değerlendireceğiz.
- Eski development job hatalarının readiness'e etkisini ayıracağız.
- Threshold'ları **henüz değiştirmeyeceğiz**.

---

## Görev 4 sonucu: PASS
## Görev 4 Sonuç Çıktısı:
```txt
Paylaştığın gerçek Görev 4 çıktılarında servis RUNNING, realtime smoke test OK, validation core OK, ETH/BTC median quality 90.83, URA median quality 87.48 ve readiness blockers=[]. NOT_READY olmasının nedeni şu anda hata değil, yalnızca Shadow/history süresinin dolmamış olması: Shadow 9/30, ETH/BTC 9/25, URA 6/20, breadth 6/20.

En önemli teşhis önceki tahminimizi düzeltti: üç hourly_job ERROR kaydı development artığı değil. Çünkü:

165 OK + 3 ERROR = 168
168 = 7 gün × 24 saat

Yani üçü de gerçek scheduler çalışması sırasında oluşmuş bağlantı havuzu hataları. Bunları readiness hesabından gizlemek yanlış olur.

Buna karşılık iki gerçek muhasebe problemi bulduk:

macro_job     raw = 29    scheduler root beklentisi = 28
sec_event_job raw = 169   scheduler root beklentisi = 168

Her ikisindeki +1, weekly_job içinden çağrılan child maintenance çalışması. Dolayısıyla mevcut system.job_runs tablosu scheduler root çalışmalarıyla nested/manual işleri birbirine karıştırıyordu. SEC tarafındaki DEGRADED kayıtları da crash değil; yaklaşık %20–21 URA ağırlığının doğrudan SEC ticker'larıyla kapsanabilmesinden kaynaklanan veri-kapsama kalitesi. Bu ayrımları yeni hardening dokümanında açıkça kaydettim.

Uyguladığım revizyon

Python tarafında model davranışına dokunmadan Görev 4 observability hardening geliştirmesini yaptım. Yeni yapı explicit Shadow Epoch, run-kind provenance, scheduler expected/actual karşılaştırması ve edge/confidence/quality/status diagnostiklerini getiriyor. Görev 4 için ortak scheduler sözleşmesi tam olarak şu 385 root çalışmayı hesaplıyor:

hourly_job          168
macro_job            28
sec_event_job       168
daily_crypto_job      7
daily_ura_job         7
daily_fx_job          5
weekly_job            1
monthly_audit_job     1
------------------------
TOTAL                385

Eklenen/değiştirilen ana parçalar tek bir çalışma kapsamında şunlar oldu:

app/run_context.py
app/schedule_contract.py
app/observability.py
app/database/db.py
app/scheduler.py
run.py
migrations/0010_shadow_observability.sql
supabase-migrations/0010_shadow_observability.sql
tests/test_shadow_observability.py
docs/SHADOW_TASK4_HARDENING.md
docs/SHADOW_CHECKPOINT_LOG.md
docs/SESSION_HANDOFF.md

Yeni CLI komutu:

InvestmentEngineCLI.cmd --shadow-observability

Ancak önemli güvenlik kararı olarak bu komut şimdilik sonucu ayrı SHADOW_OBSERVABILITY validation type'ına yazıyor. Mevcut released SHADOW_READINESS mekanizmasını sessizce değiştirmedim. Gerçek Windows/Supabase deployment testi tamamlanmadan yeni ölçümü resmi readiness gerçeği yapmayacağız. Bu sınır da dokümana işlendi.

RELEASED / APPROVED / PROPOSED / OPEN

RELEASED tarafında hiçbir model davranışı değişmedi: threshold'lar, factor weight'ler, K1/K2, reversal, 5 zayıf değerlendirme reseti, action-size, SHADOW modu ve Realtime Execution OFF aynen duruyor.

APPROVED kapsamda yalnız davranış değiştirmeyen Shadow observability hardening uygulandı.

PROPOSED konular — 5 seanslık kademe aralığı, iki kapanışlı reversal, reset sonrası K1 davranışının değiştirilmesi, yeni sizing gibi başlıklar — hâlâ öneri durumunda. Hiçbirini uygulamadım.

OPEN olan kısım ise yeni 0010 migration + build + gerçek Windows Service/Supabase runtime testi. Bu yapılmadan source kodundaki yeni hardening'i deployed gerçeklik olarak kabul etmiyoruz. Bu statü ayrımı repoya da işlendi.

GitHub durumu

Python aktif branch artık:

agent/portfolio-audit-reset
6e2ff610d9f908af96d67c87ebf8776492bd7b99
Shadow Task 4 observability hardening

Branch gerçekten bu committe ve bir önceki d37c6a4... commitinin doğrudan fast-forward çocuğu.

Python Draft PR #1 de yeni HEAD'i görüyor ve açıklamasını revizyona göre düzelttim. Önceden artık yanlış hale gelen “Python engine source değişmedi” ifadesini kaldırdım; model semantiğinin değişmediğini fakat observability source kodunun değiştiğini açıkça ayırdım. PR hâlâ draft.

Quasar aktif branch:

feature/initial-investment-dashboard
55e67acdd666ecfc4be3a551e174867269e8a414
Sync Shadow Task 4 handoff context

Burada uygulama koduna dokunmadım; yalnız SESSION_HANDOFF, SHADOW_CHECKPOINT_LOG ve yeni Task 4 hardening belgesini iki repo arasında senkronladım. Quasar PR açıklamasını da bu doküman senkronunu yansıtacak şekilde güncelledim; PR draft kalıyor.

Bir teknik sınırlamayı açık bırakıyorum: bu çalışma ortamından doğrudan git clone/pull sırasında github.com DNS çözümlemesi başarısız olduğu için gerçek bir yerel git worktree oluşturup git status ile “clean” doğrulaması yapamadım. Bunun yerine her iki remote branch HEAD'ini bağlı GitHub üzerinden işlem öncesinde tekrar kontrol ettim ve değişiklikleri yalnız doğruladığım HEAD'lerin üzerine force kullanmadan fast-forward olarak yazdım. Dolayısıyla remote branch durumu doğrulanmış durumda; yerel worktree için temiz olduğunu iddia etmiyorum.

Ayrıca saf Python schedule/run-context testleri geçti ve Task 4'ün 385 root-run hesabını doğruladı. GitHub tarafında bu commit için CI workflow bulunmuyor; tam Windows build, migration'ın gerçek Supabase'e uygulanması ve servis runtime testi OPEN durumda.

Bir sonraki mantıklı adım artık model threshold'larıyla oynamak değil; bu observability hardening'i test sunucu/gerçek Shadow ortamına kontrollü deploy edip --shadow-observability çıktısını almak. Bu çıktı geldiğinde üç hourly ERROR'ın scheduled kaldığını, weekly child macro/SEC'nin maintenance'a ayrıldığını ve manual/test kayıtlarının readiness scheduler paydasından çıktığını birlikte doğrularız. Ondan sonra Görev 5'e temiz bir ölçüm temeliyle devam ederiz.
```

# Görev 5 — 14.08.2026 Cuma, 10:30 TRT
## 14 günlük stabilite kontrolü

### Önce

```bat
InvestmentEngineCLI.cmd --service-status
InvestmentEngineCLI.cmd --test-realtime --realtime-seconds 20
InvestmentEngineCLI.cmd --validate-model
```

### Sonra

Görev 4'teki şu sorguları tekrar çalıştır:

- 4.4 — 7 günlük job özeti
- 4.5 — 7 günlük hatalar
- 4.6 — Shadow Readiness
- 4.7 — Karar istatistiği
- 4.8 — URA holdings
- 4.9 — Realtime test

Ek olarak:

```sql
select
    system,
    status,
    count(*) as decisions
from model.decisions
where model_version like '1.2.%'
group by system, status
order by system, status;
```

### Bana gönder

Tüm sonuçları gönder.

### Özellikle bakacağımız konular

- BTC/ETH quality yaklaşık 80+ seviyesinde kalıyor mu?
- URA quality yükseliyor mu?
- Scheduler'da tekrarlayan hata var mı?
- Realtime testlerde `trade_gap_count` normal mi?
- Karar sayısı/WAIT/NO_ACTION_DATA dağılımı nasıl?

---

# Görev 6 — 20.08.2026 Perşembe, 10:30 TRT
## URA için kritik 20 günlük ara değerlendirme

Bu checkpoint'in ana konusu URA'dır.

### 6.1 Validation

```bat
InvestmentEngineCLI.cmd --validate-model
```

### 6.2 Readiness

```sql
select
    status,
    metrics->'stats' as stats,
    metrics->'waiting_reasons' as waiting_reasons,
    metrics->'blockers' as blockers,
    generated_at
from public.model_validation_snapshot
where validation_type = 'SHADOW_READINESS'
  and system = 'ALL';
```

### 6.3 URA kararları

```sql
select
    id,
    as_of,
    direction,
    edge_score,
    confidence,
    data_quality,
    status,
    model_version,
    created_at
from model.decisions
where system = 'URA/USD'
  and model_version like '1.2.%'
order by as_of, created_at;
```

### 6.4 URA factor quality

```sql
select
    as_of,
    factor_code,
    score,
    quality,
    weight,
    weighted_score,
    details
from model.factor_scores
where system = 'URA/USD'
  and as_of = (
      select max(as_of)
      from model.factor_scores
      where system = 'URA/USD'
  )
order by factor_code;
```

### 6.5 Holdings history

```sql
select
    count(distinct holding_date) as holdings_days,
    min(holding_date) as first_date,
    max(holding_date) as last_date
from fundamentals.ura_holdings;
```

### 6.6 Son 7 gün hata özeti

```sql
select
    job_name,
    started_at,
    status,
    message,
    details
from system.job_runs
where started_at >= now() - interval '7 days'
  and status <> 'OK'
order by started_at desc;
```

### Bana gönder

Görev 6'nın bütün sonuçlarını gönder.

### Bu checkpoint'te karar ağacı

**URA median quality ≥ 80 ise:**  
Shadow gözlemini değiştirmeden devam ederiz.

**URA hâlâ 70–79 arasındaysa:**  
Sadece beklemeyiz; `fundamentals`, `breadth` ve `event` quality katkılarını ayrı ayrı analiz ederiz.

**URA < 70 ise:**  
Veri kaynağı / freshness / breadth üretim zincirinde regresyon ararız.

---

# Görev 7 — 29.08.2026 Cumartesi, 10:30 TRT
## 30 günlük Shadow Graduation Review

Bu ilk ciddi LIVE-readiness değerlendirmesidir.  
**READY çıkması LIVE'a otomatik geçeceğimiz anlamına gelmez.**

### 7.1 Servis

```bat
InvestmentEngineCLI.cmd --service-status
```

### 7.2 Realtime testini yenile

```bat
InvestmentEngineCLI.cmd --test-realtime --realtime-seconds 20
```

### 7.3 Validation

```bat
InvestmentEngineCLI.cmd --validate-model
```

### 7.4 Readiness

```sql
select
    status,
    metrics->'stats' as stats,
    metrics->'criteria' as criteria,
    metrics->'waiting_reasons' as waiting_reasons,
    metrics->'blockers' as blockers,
    generated_at
from public.model_validation_snapshot
where validation_type = 'SHADOW_READINESS'
  and system = 'ALL';
```

### 7.5 30 günlük job özeti

```sql
select
    job_name,
    status,
    count(*) as run_count
from system.job_runs
where started_at >= now() - interval '30 days'
group by job_name, status
order by job_name, status;
```

### 7.6 30 günlük hatalar

```sql
select
    job_name,
    started_at,
    finished_at,
    status,
    message,
    details
from system.job_runs
where started_at >= now() - interval '30 days'
  and status <> 'OK'
order by started_at desc;
```

### 7.7 Karar özeti

```sql
select
    system,
    status,
    count(*) as decision_count,
    count(distinct as_of) as decision_days,
    round(
        (percentile_cont(0.5) within group (order by data_quality))::numeric,
        2
    ) as median_quality,
    round(
        (percentile_cont(0.5) within group (order by edge_score))::numeric,
        2
    ) as median_edge,
    round(
        (percentile_cont(0.5) within group (order by confidence))::numeric,
        2
    ) as median_confidence
from model.decisions
where model_version like '1.2.%'
group by system, status
order by system, status;
```

### 7.8 Validation çıktıları

```sql
select
    validation_type,
    system,
    model_version,
    status,
    start_date,
    end_date,
    metrics,
    details,
    generated_at
from public.model_validation_snapshot
order by validation_type, system;
```

### 7.9 URA holdings

```sql
select
    count(distinct holding_date) as holdings_days,
    min(holding_date) as first_date,
    max(holding_date) as last_date
from fundamentals.ura_holdings;
```

### 7.10 Realtime test sonucu

```sql
select
    test_run_id,
    min(observed_at) as first_snapshot,
    max(observed_at) as last_snapshot,
    count(*) as snapshots,
    count(distinct product) as products,
    max(trade_gap_count) as max_trade_gap
from market.execution_snapshots
where is_test = true
  and observed_at >= now() - interval '30 minutes'
group by test_run_id
order by max(observed_at) desc
limit 3;
```

### Bana gönder

Görev 7'deki tüm sonuçları tek turda gönder.

---

# 30 günlük değerlendirmede hedefler

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

Bunların hepsi geçse bile:

```text
SHADOW -> LIVE
```

otomatik yapılmayacak.

Önce historical validation, walk-forward, strict point-in-time ve Shadow sonuçlarını birlikte değerlendireceğiz.

---

# Bir hata görürsen takvim tarihini bekleme

Aşağıdakilerden biri oluşursa aynı gün sonucu paylaş:

```text
Service STOPPED
Scheduler job ERROR
ENGINE ERROR
DB bağlantı hatası
Coinbase/OKX sürekli hata
FRED/TCMB freshness sorunu
URA holdings gelmemesi
Data Quality'nin ani çökmesi
Realtime smoke test FAIL
```

Önce şu sorguyu çalıştır:

```sql
select
    job_name,
    started_at,
    finished_at,
    status,
    message,
    details
from system.job_runs
where status <> 'OK'
order by started_at desc
limit 20;
```

ve:

```sql
select
    component,
    status,
    message,
    checked_at,
    details
from public.engine_health_snapshot
order by component;
```

Sonuçları paylaş.

**Hata gördüğünde aynı job'ı art arda tekrar çalıştırma.** Özellikle Alpha Vantage kota/burst sorunlarında tekrarlar teşhisi zorlaştırabilir.

---

# Sonuç paylaşım formatı

Her kontrol gününde mesajın başına şu formatı koy:

```text
CHECKPOINT:
Tarih/Saat:
Service:
Engine Version:
```

Ardından CMD ve SQL çıktılarını ekle.

Örnek:

```text
CHECKPOINT: 7 Gün
Tarih/Saat: 07.08.2026 10:30 TRT
Service: RUNNING
Engine Version: 1.2.x

1. Realtime:
...

2. Job Summary:
...

3. Readiness:
...

4. Decisions:
...
```

Bu formatla her turda önceki checkpoint ile değişimi daha kolay karşılaştırabiliriz.

---

# Python geliştirme planı ile bağlantısı

Shadow motor veri biriktirirken geliştirme paralel devam edecek:

```text
31 Temmuz - 7 Ağustos
    Shadow Epoch
    Edge diagnostics
    readiness hardening

7 - 14 Ağustos
    Edge / Confidence / Quality bucket analizleri
    walk-forward validation

14 - 20 Ağustos
    strict macro point-in-time / vintage katmanı
    historical replay hardening

20 - 29 Ağustos
    Shadow verisi ile validation karşılaştırması
    URA quality analizi
    release hardening

29 Ağustos
    30 günlük Shadow Graduation Review
```

Bu tarihler geliştirme için bekleme süresi değildir. Sunucu veri toplarken Python/model tarafı paralel geliştirilecektir.
