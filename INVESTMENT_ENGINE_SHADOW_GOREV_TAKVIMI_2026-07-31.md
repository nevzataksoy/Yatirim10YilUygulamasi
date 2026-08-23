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
# Sonuç Çıktısı:
```bat
C:\Program Files\Rosa\InvestmentEngine>InvestmentEngineCLI.cmd --service-status
2026-08-19T17:34:30.112405+00:00 SERVICE_NAME: RosaInvestmentEngine
        TYPE               : 10  WIN32_OWN_PROCESS
        STATE              : 4  RUNNING
                                (STOPPABLE, NOT_PAUSABLE, IGNORES_SHUTDOWN)
        WIN32_EXIT_CODE    : 0  (0x0)
        SERVICE_EXIT_CODE  : 0  (0x0)
        CHECKPOINT         : 0x0
        WAIT_HINT          : 0x0

C:\Program Files\Rosa\InvestmentEngine>InvestmentEngineCLI.cmd --test-realtime --realtime-seconds 20
2026-08-19T17:35:04.807564+00:00 Coinbase realtime smoke test başlatılıyor (20 sn)...
2026-08-19T17:35:27.688022+00:00 realtime_test: OK — run=f3578e65-0313-4a79-a79d-c635eec6334e snapshots=8 products=BTC-USD,ETH-USD

C:\Program Files\Rosa\InvestmentEngine>InvestmentEngineCLI.cmd --validate-model
2026-08-19T17:35:51.731140+00:00 Model validation başlatılıyor...
2026-08-19T17:37:37.779476+00:00 model_validation: OK — core=OK observations=1401 shadow=NOT_READY
```

### Sonra

Görev 4'teki şu sorguları tekrar çalıştır:

- 4.4 — 7 günlük job özeti
# 4.4 - 7 Görev isteği
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
# Sonuç Çıktısı
```json
[{"job_name":"daily_crypto_job","status":"OK","run_count": 7},{"job_name":"daily_fx_job","status":"OK","run_count": 5},{"job_name":"daily_ura_job","status":"OK","run_count": 7},{"job_name":"hourly_job","status":"ERROR","run_count": 2},{"job_name":"hourly_job","status":"OK","run_count": 166},{"job_name":"macro_job","status":"OK","run_count": 29},{"job_name":"model_validation_job","status":"OK","run_count": 1},{"job_name":"realtime_test","status":"OK","run_count": 1},{"job_name":"sec_event_job","status":"DEGRADED","run_count": 169},{"job_name":"weekly_job","status":"OK","run_count": 1} ]
```
- 4.5 — 7 günlük hatalar
# 4.5 — 7 Görev isteği
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
# Sonuç Çıktısı
```json
[{"job_name":"sec_event_job","started_at":"2026-08-19 17:35:05.129931+00","finished_at":"2026-08-19 17:35:27.198213+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"hourly_job","started_at":"2026-08-19 17:05:02.299558+00","finished_at":"2026-08-19 17:05:50.025816+00","status":"ERROR","message":"couldn't get a connection after 10.00 sec","details": {  "provider_mode":"auto"}},{"job_name":"sec_event_job","started_at":"2026-08-19 16:35:00.00221+00","finished_at":"2026-08-19 16:35:11.002573+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 15:35:00.012348+00","finished_at":"2026-08-19 15:35:12.558066+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 14:35:00.010165+00","finished_at":"2026-08-19 14:35:13.273852+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 13:35:00.026435+00","finished_at":"2026-08-19 13:35:11.217727+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 12:35:00.014828+00","finished_at":"2026-08-19 12:35:11.462221+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 11:35:00.010324+00","finished_at":"2026-08-19 11:35:11.368802+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 10:35:00.196335+00","finished_at":"2026-08-19 10:35:13.955444+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 09:35:00.007988+00","finished_at":"2026-08-19 09:35:11.787344+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 08:35:00.001797+00","finished_at":"2026-08-19 08:35:11.271113+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 07:35:00.011265+00","finished_at":"2026-08-19 07:35:15.447221+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 06:35:00.135939+00","finished_at":"2026-08-19 06:35:12.926234+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 05:35:00.004289+00","finished_at":"2026-08-19 05:35:11.318579+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 04:35:00.005627+00","finished_at":"2026-08-19 04:35:11.390713+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 03:35:00.12349+00","finished_at":"2026-08-19 03:35:12.739493+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 02:35:00.015715+00","finished_at":"2026-08-19 02:35:12.178877+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 01:35:00.018301+00","finished_at":"2026-08-19 01:35:12.724732+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-19 00:35:00.057872+00","finished_at":"2026-08-19 00:35:12.461902+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%","details": {  "quality": 20.29,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2029,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 23:35:00.00929+00","finished_at":"2026-08-18 23:35:11.403653+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 22:35:00.102232+00","finished_at":"2026-08-18 22:35:17.55456+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 21:35:00.840928+00","finished_at":"2026-08-18 21:35:20.966636+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 10,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 20:35:00.279339+00","finished_at":"2026-08-18 20:35:14.443969+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 19:35:01.394725+00","finished_at":"2026-08-18 19:35:19.675684+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 18:35:02.275886+00","finished_at":"2026-08-18 18:35:27.269483+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 17:35:10.686192+00","finished_at":"2026-08-18 17:35:54.950955+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 16:35:01.420295+00","finished_at":"2026-08-18 16:35:18.086101+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 15:35:00.520156+00","finished_at":"2026-08-18 15:35:15.020188+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 14:35:00.145334+00","finished_at":"2026-08-18 14:35:25.148561+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 13:35:00.124093+00","finished_at":"2026-08-18 13:35:11.069577+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 12:35:00.010359+00","finished_at":"2026-08-18 12:35:10.477867+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 11:35:00.156735+00","finished_at":"2026-08-18 11:35:12.287222+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 10:35:00.164343+00","finished_at":"2026-08-18 10:35:13.844462+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 09:35:00.013472+00","finished_at":"2026-08-18 09:35:09.760045+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 08:35:00.005961+00","finished_at":"2026-08-18 08:35:10.197642+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 07:35:00.006734+00","finished_at":"2026-08-18 07:35:10.454757+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 06:35:00.005814+00","finished_at":"2026-08-18 06:35:10.164621+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 05:35:00.079355+00","finished_at":"2026-08-18 05:35:17.210583+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 04:35:00.031871+00","finished_at":"2026-08-18 04:35:10.97987+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 03:35:00.029362+00","finished_at":"2026-08-18 03:35:11.588197+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 02:35:01.685179+00","finished_at":"2026-08-18 02:35:39.452613+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 01:35:00.887652+00","finished_at":"2026-08-18 01:35:23.930085+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-18 00:35:00.162517+00","finished_at":"2026-08-18 00:35:12.626707+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 23:35:03.014462+00","finished_at":"2026-08-17 23:35:48.779512+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 22:35:06.978313+00","finished_at":"2026-08-17 22:35:45.410408+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 21:35:03.003077+00","finished_at":"2026-08-17 21:36:37.234774+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 20:35:00.189797+00","finished_at":"2026-08-17 20:35:23.870557+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 19:35:03.403379+00","finished_at":"2026-08-17 19:35:41.362046+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 18:35:03.39503+00","finished_at":"2026-08-17 18:35:43.712107+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 17:35:00.755839+00","finished_at":"2026-08-17 17:35:18.709212+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 16:35:00.043241+00","finished_at":"2026-08-17 16:35:10.882367+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 15:35:00.011479+00","finished_at":"2026-08-17 15:35:12.439008+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 14:35:00.75096+00","finished_at":"2026-08-17 14:35:33.673248+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 13:35:00.279395+00","finished_at":"2026-08-17 13:35:17.221489+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 12:35:00.027468+00","finished_at":"2026-08-17 12:35:10.264864+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 11:35:00.032392+00","finished_at":"2026-08-17 11:35:10.88576+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 10:35:00.127559+00","finished_at":"2026-08-17 10:35:10.193556+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 09:35:00.004159+00","finished_at":"2026-08-17 09:35:11.349238+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 08:35:00.00384+00","finished_at":"2026-08-17 08:35:10.419694+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 07:35:00.005543+00","finished_at":"2026-08-17 07:35:14.376015+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 06:35:00.256673+00","finished_at":"2026-08-17 06:35:28.232018+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 05:35:00.188931+00","finished_at":"2026-08-17 05:35:14.108605+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 04:35:00.065215+00","finished_at":"2026-08-17 04:35:10.97045+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 03:35:00.176901+00","finished_at":"2026-08-17 03:35:12.09771+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 02:35:00.091763+00","finished_at":"2026-08-17 02:35:11.682899+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 01:35:01.764157+00","finished_at":"2026-08-17 01:35:15.358597+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-17 00:35:00.76718+00","finished_at":"2026-08-17 00:35:16.444477+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 23:35:00.122511+00","finished_at":"2026-08-16 23:35:25.024636+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 22:35:00.35643+00","finished_at":"2026-08-16 22:35:35.627221+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 21:35:00.006447+00","finished_at":"2026-08-16 21:35:11.600048+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 20:35:00.012221+00","finished_at":"2026-08-16 20:35:09.459721+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 19:35:00.043662+00","finished_at":"2026-08-16 19:35:11.90499+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 18:35:00.083102+00","finished_at":"2026-08-16 18:35:11.867022+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 17:35:00.120748+00","finished_at":"2026-08-16 17:35:13.15473+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 16:35:00.195442+00","finished_at":"2026-08-16 16:35:13.303219+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 15:35:00.177127+00","finished_at":"2026-08-16 15:35:15.692695+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 14:35:00.372726+00","finished_at":"2026-08-16 14:35:14.231859+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 13:35:00.586067+00","finished_at":"2026-08-16 13:35:15.15208+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 12:35:00.085503+00","finished_at":"2026-08-16 12:35:13.419172+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 11:35:00.082567+00","finished_at":"2026-08-16 11:35:10.602042+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 10:35:00.002215+00","finished_at":"2026-08-16 10:35:10.781815+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 09:35:00.006444+00","finished_at":"2026-08-16 09:35:11.094939+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 08:35:00.086242+00","finished_at":"2026-08-16 08:35:11.866706+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 07:35:00.10676+00","finished_at":"2026-08-16 07:35:10.706368+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 06:35:00.133374+00","finished_at":"2026-08-16 06:35:13.638192+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 05:35:00.062982+00","finished_at":"2026-08-16 05:35:11.65424+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 04:35:00.049164+00","finished_at":"2026-08-16 04:35:12.79026+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 03:35:00.102962+00","finished_at":"2026-08-16 03:35:13.403448+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 02:35:00.721545+00","finished_at":"2026-08-16 02:35:17.387998+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 01:35:00.126996+00","finished_at":"2026-08-16 01:35:19.513013+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-16 00:35:00.311254+00","finished_at":"2026-08-16 00:35:13.927874+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-15 23:35:00.188562+00","finished_at":"2026-08-15 23:35:15.098285+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-15 22:35:02.646016+00","finished_at":"2026-08-15 22:35:23.598915+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-15 21:35:00.130333+00","finished_at":"2026-08-15 21:35:12.532522+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-15 20:35:00.217023+00","finished_at":"2026-08-15 20:35:16.230591+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-15 19:35:01.054413+00","finished_at":"2026-08-15 19:35:17.136975+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-15 18:35:00.128942+00","finished_at":"2026-08-15 18:35:16.759545+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-15 17:35:00.109079+00","finished_at":"2026-08-15 17:35:15.041175+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-15 16:35:00.193541+00","finished_at":"2026-08-15 16:35:14.007128+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}},{"job_name":"sec_event_job","started_at":"2026-08-15 15:35:00.175677+00","finished_at":"2026-08-15 15:35:14.175209+00","status":"DEGRADED","message":"SEC filings kontrol edildi: 5 entity, 9 recent filing, fund weight coverage 20.7%","details": {  "quality": 20.69,  "scope_cap": 70,  "filings_seen": 9,  "matched_tickers": [ "OKLO", "UEC", "XE", "LEU", "SMR"  ],  "entities_checked": 5,  "unmatched_tickers": [ "CCO CN", "U-U CN", "NXE CN", "KAP LI", "EFR CN", "PDN AU", "DML CN", "SSW SJ", "047040 KS", "034020 KS"  ],  "matched_fund_weight": 0.2069,  "considered_top_n_weight": 0.7539}} ]
```
- 4.6 — Shadow Readiness
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
# Sonuç Çıktısı
```json
[{"status":"NOT_READY","stats": {  "job_count": 386,"performance": [],"ura_actions": 0,"ura_watches": 0,"calendar_days": 21,"crypto_actions": 0,"crypto_watches": 0,"job_success_rate": 0.9948186528497409,"last_decision_at":"2026-08-19T02:20:17.786050+00:00","first_decision_at":"2026-07-30T19:53:25.049772+00:00","ura_breadth_dates": 13,"ura_decision_days": 14,"ura_holdings_dates": 13,"ura_median_quality": 87.71,"crypto_decision_days": 21,"crypto_median_quality": 90.95,"realtime_test_age_days": 0.0014587801157407408},"waiting_reasons": [  "Shadow gözlem süresi 21/30 gün.","ETH/BTC karar günü 21/25.","URA/USD karar günü 14/20.","URA breadth history 13/20 gün."],"blockers": [],"generated_at":"2026-08-19 17:37:34.221296+00"} ]
```
- 4.7 — Karar istatistiği
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
# Sonuç Çıktısı
```json
[{"system":"ETH/BTC","decision_days": 21,"median_quality":"90.95","min_quality":"90.08","max_quality":"91.20"},{"system":"URA/USD","decision_days": 14,"median_quality":"87.71","min_quality":"70.40","max_quality":"88.07"} ]
```
- 4.8 — URA holdings
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
# Sonuç Çıktısı
```json
[{"holding_date":"2026-08-17","constituents": 57,"weight_coverage":"1.0002"},{"holding_date":"2026-08-14","constituents": 57,"weight_coverage":"0.9982"},{"holding_date":"2026-08-13","constituents": 58,"weight_coverage":"0.9996"},{"holding_date":"2026-08-12","constituents": 58,"weight_coverage":"0.9992"},{"holding_date":"2026-08-11","constituents": 58,"weight_coverage":"0.9991"},{"holding_date":"2026-08-10","constituents": 58,"weight_coverage":"0.9993"},{"holding_date":"2026-08-07","constituents": 58,"weight_coverage":"0.9987"},{"holding_date":"2026-08-05","constituents": 58,"weight_coverage":"0.9985"},{"holding_date":"2026-08-04","constituents": 58,"weight_coverage":"0.9991"},{"holding_date":"2026-08-03","constituents": 58,"weight_coverage":"0.9965"},{"holding_date":"2026-07-31","constituents": 58,"weight_coverage":"0.9942"},{"holding_date":"2026-07-30","constituents": 53,"weight_coverage":"0.9988"},{"holding_date":"2026-07-29","constituents": 53,"weight_coverage":"0.9983"} ]
```
- 4.9 — Realtime test
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
# Sonuç Çıktısı
```json
[{"test_run_id":"f3578e65-0313-4a79-a79d-c635eec6334e","first_snapshot":"2026-08-19 17:35:09.998891+00","last_snapshot":"2026-08-19 17:35:25.552551+00","snapshots": 8,"products": 2,"max_trade_gap": 0} ]
```

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
# Sonuç Çıktısı
```json
[{"system":"ETH/BTC","status":"WAIT","decisions": 21},{"system":"URA/USD","status":"NO_ACTION_DATA","decisions": 2},{"system":"URA/USD","status":"WAIT","decisions": 18} ]
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
# Görev 5 Sonuç Çıktısı

## Görev 5 sonucu: PASS — stabilite ve veri kalitesi kabul edilebilir

Görev 5 kapsamında 14 günlük Shadow/stabilite kontrolü 19.08.2026 tarihinde tamamlandı.

### Servis

`RosaInvestmentEngine` servisi çalışır durumda:

- STATE: `4 RUNNING`
- WIN32_EXIT_CODE: `0`
- SERVICE_EXIT_CODE: `0`

### Realtime

Coinbase realtime smoke test:

- Sonuç: `OK`
- Test süresi: 20 saniye
- Snapshot: `8`
- Product: `BTC-USD`, `ETH-USD`
- `max_trade_gap`: `0`

Realtime tarafında test sırasında trade gap problemi görülmedi.

### Validation

Model validation sonucu:

- Core: `OK`
- Observations: `1401`
- Shadow: `NOT_READY`

`NOT_READY` mevcut durumda bir blocker değildir. Shadow/history süre kriterleri henüz tamamlanmadığı için beklenen durumdur.

### Scheduler

Son 7 günlük job özeti:

- `daily_crypto_job`: 7 OK
- `daily_fx_job`: 5 OK
- `daily_ura_job`: 7 OK
- `hourly_job`: 166 OK / 2 ERROR
- `macro_job`: 29 OK
- `model_validation_job`: 1 OK
- `realtime_test`: 1 OK
- `sec_event_job`: 169 DEGRADED
- `weekly_job`: 1 OK

İki `hourly_job` ERROR gerçek scheduler hatasıdır:

```text
couldn't get a connection after 10.00 sec
```
Bu kayıtlar development/manual artığı olarak değerlendirilmemelidir. 7 günlük saatlik scheduler beklentisi 168 çalışmadır ve sonuç 166 OK + 2 ERROR = 168 şeklindedir.

sec_event_job DEGRADED kayıtları ise servis crash'i değildir. Son ölçümde SEC doğrudan ticker eşleşmesi yaklaşık %20.29 URA ağırlığını kapsamaktadır. Bu nedenle mevcut veri-kapsama semantiği altında DEGRADED beklenen bir kalite sonucudur.

Shadow Readiness

Güncel readiness:

Status: NOT_READY
Shadow calendar: 21/30
ETH/BTC decision days: 21/25
URA/USD decision days: 14/20
URA breadth dates: 13/20
URA holdings dates: 13
ETH/BTC median quality: 90.95
URA/USD median quality: 87.71
Job success rate: %99.48
Realtime test age: yaklaşık 0 gün
Blockers: []

Dolayısıyla mevcut sonuçlar Shadow'ın başarısız olduğunu göstermiyor. Bekleyen kriterler esas olarak gözlem/history süresidir.

Karar dağılımı

ETH/BTC:

WAIT: 21

URA/USD:

WAIT: 18
NO_ACTION_DATA: 2

Bu checkpoint'te ACTION üretimi görülmemiştir. Mevcut decision dağılımı motorun veri/karar kapılarının beklenen şekilde çalıştığına işaret etmektedir.

Kalite değerlendirmesi

ETH/BTC:

Median: 90.95
Min: 90.08
Max: 91.20

URA/USD:

Median: 87.71
Min: 70.40
Max: 88.07

URA median quality 80 eşiğinin üzerindedir. Bu nedenle Görev 6 karar ağacındaki URA median quality >= 80 dalı geçerlidir.

Görev 5 kararı

PASS

Görev 5 sonucunda:

Servis çalışıyor.
Realtime smoke test başarılı.
trade_gap_count = 0.
Core validation başarılı.
ETH/BTC quality güçlü.
URA quality kabul edilebilir seviyede.
Readiness blocker bulunmuyor.
Shadow süresi henüz tamamlanmadığı için NOT_READY beklenen durum.
2 gerçek hourly_job connection-pool hatası OPEN izleme konusu olarak korunmalı.
SEC DEGRADED durumu veri-kapsama problemi olarak izlenmeli.
Python revizyon borcu

Görev takvimi tamamlanana kadar model/runtime davranışını değiştirecek Python revizyonları uygulanmayacaktır.

Özellikle threshold, factor weight, K1/K2, reversal, reset, action-size veya Shadow/Realtime çalışma mantığını değiştiren revizyonlar PROPOSED/OPEN borç olarak tutulacaktır.

Davranış değiştirmeyen observability, diagnostic, test ve raporlama geliştirmeleri ise kontrollü şekilde devam edebilir.

Görev 6 için mevcut karar ağacına göre:

URA median quality = 87.71 >= 80

olduğu için Shadow gözlemi değiştirilmeden devam edilmelidir.

RELEASED: Mevcut model davranışı, threshold'lar, factor weight'ler, K1/K2, reversal, reset, action-size, SHADOW modu ve Realtime Execution OFF korunuyor.

APPROVED: Davranış değiştirmeyen observability/hardening çalışmaları.

PROPOSED: Model davranışına ilişkin gelecekteki iyileştirmeler uygulanmadı.

OPEN: 2 hourly connection-pool hatasının kök neden analizi ve Shadow history/readiness kriterlerinin tamamlanması.
Bu içeriği doğruladım; mevcut Görev 5 ölçümleriyle tutarlı. Mevcut dosyada placeholder'ın hemen ardından Görev 6 başlıyor. 

# Görev 6 — 20.08.2026 Perşembe, 10:30 TRT
## URA için kritik 20 günlük ara değerlendirme

Bu checkpoint'in ana konusu URA'dır.

### 6.1 Validation

```bat
InvestmentEngineCLI.cmd --validate-model
```
Sonuç Çıktısı:
```bat
C:\Program Files\Rosa\InvestmentEngine>InvestmentEngineCLI.cmd --service-status
2026-08-23T18:35:19.247676+00:00 SERVICE_NAME: RosaInvestmentEngine
        TYPE               : 10  WIN32_OWN_PROCESS
        STATE              : 4  RUNNING
                                (STOPPABLE, NOT_PAUSABLE, IGNORES_SHUTDOWN)
        WIN32_EXIT_CODE    : 0  (0x0)
        SERVICE_EXIT_CODE  : 0  (0x0)
        CHECKPOINT         : 0x0
        WAIT_HINT          : 0x0

C:\Program Files\Rosa\InvestmentEngine>InvestmentEngineCLI.cmd --validate-model
2026-08-23T18:36:31.958387+00:00 Model validation başlatılıyor...
2026-08-23T18:38:06.987623+00:00 model_validation: OK — core=OK observations=1405 shadow=NOT_READY
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
Sonuç Çıktısı:
```json
[
  {
    "status": "NOT_READY",
    "stats": {
      "job_count": 387,
      "performance": [],
      "ura_actions": 0,
      "ura_watches": 0,
      "calendar_days": 25,
      "crypto_actions": 0,
      "crypto_watches": 0,
      "job_success_rate": 0.9974160206718347,
      "last_decision_at": "2026-08-23T02:20:38.499567+00:00",
      "first_decision_at": "2026-07-30T19:53:25.049772+00:00",
      "ura_breadth_dates": 17,
      "ura_decision_days": 17,
      "ura_holdings_dates": 17,
      "ura_median_quality": 87.71,
      "crypto_decision_days": 25,
      "crypto_median_quality": 90.83,
      "realtime_test_age_days": 4.043461111631944
    },
    "waiting_reasons": [
      "Shadow gözlem süresi 25/30 gün.",
      "URA/USD karar günü 17/20.",
      "URA breadth history 17/20 gün."
    ],
    "blockers": [],
    "generated_at": "2026-08-23 18:38:02.878362+00"
  }
]
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
Sonuç Çıktısı:
```json
[
  {
    "id": 8,
    "as_of": "2026-07-30",
    "direction": "URA→USD",
    "edge_score": "33.160",
    "confidence": "35.630",
    "data_quality": "70.400",
    "status": "NO_ACTION_DATA",
    "model_version": "1.2.0",
    "created_at": "2026-07-30 20:36:52.973542+00"
  },
  {
    "id": 9,
    "as_of": "2026-07-30",
    "direction": "URA→USD",
    "edge_score": "33.990",
    "confidence": "36.170",
    "data_quality": "70.400",
    "status": "NO_ACTION_DATA",
    "model_version": "1.2.0",
    "created_at": "2026-07-30 23:40:32.89814+00"
  },
  {
    "id": 11,
    "as_of": "2026-07-31",
    "direction": "URA→USD",
    "edge_score": "28.550",
    "confidence": "36.030",
    "data_quality": "87.380",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-07-31 23:40:35.194871+00"
  },
  {
    "id": 13,
    "as_of": "2026-07-31",
    "direction": "URA→USD",
    "edge_score": "22.630",
    "confidence": "32.220",
    "data_quality": "87.550",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-01 23:40:34.504318+00"
  },
  {
    "id": 15,
    "as_of": "2026-07-31",
    "direction": "URA→USD",
    "edge_score": "22.630",
    "confidence": "32.220",
    "data_quality": "87.550",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-02 23:41:11.024758+00"
  },
  {
    "id": 17,
    "as_of": "2026-08-03",
    "direction": "URA→USD",
    "edge_score": "21.740",
    "confidence": "31.700",
    "data_quality": "87.850",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-03 23:40:37.923982+00"
  },
  {
    "id": 19,
    "as_of": "2026-08-04",
    "direction": "URA→USD",
    "edge_score": "21.310",
    "confidence": "31.350",
    "data_quality": "87.480",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-04 23:40:29.982605+00"
  },
  {
    "id": 21,
    "as_of": "2026-08-05",
    "direction": "URA→USD",
    "edge_score": "0.760",
    "confidence": "22.570",
    "data_quality": "85.400",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-05 23:40:35.15733+00"
  },
  {
    "id": 23,
    "as_of": "2026-08-06",
    "direction": "URA→USD",
    "edge_score": "9.620",
    "confidence": "28.800",
    "data_quality": "87.710",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-06 23:41:17.090055+00"
  },
  {
    "id": 26,
    "as_of": "2026-08-07",
    "direction": "USD→URA",
    "edge_score": "31.100",
    "confidence": "42.770",
    "data_quality": "87.770",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-08 23:41:02.947613+00"
  },
  {
    "id": 28,
    "as_of": "2026-08-07",
    "direction": "USD→URA",
    "edge_score": "31.100",
    "confidence": "42.770",
    "data_quality": "87.770",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-09 23:40:36.563936+00"
  },
  {
    "id": 30,
    "as_of": "2026-08-10",
    "direction": "USD→URA",
    "edge_score": "30.880",
    "confidence": "42.680",
    "data_quality": "88.070",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-10 23:40:55.494296+00"
  },
  {
    "id": 32,
    "as_of": "2026-08-11",
    "direction": "USD→URA",
    "edge_score": "31.270",
    "confidence": "42.850",
    "data_quality": "87.630",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-11 23:40:39.635501+00"
  },
  {
    "id": 34,
    "as_of": "2026-08-12",
    "direction": "USD→URA",
    "edge_score": "31.350",
    "confidence": "42.930",
    "data_quality": "87.730",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-12 23:40:38.031027+00"
  },
  {
    "id": 36,
    "as_of": "2026-08-13",
    "direction": "USD→URA",
    "edge_score": "30.930",
    "confidence": "42.650",
    "data_quality": "87.750",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-13 23:40:32.326785+00"
  },
  {
    "id": 38,
    "as_of": "2026-08-14",
    "direction": "USD→URA",
    "edge_score": "29.800",
    "confidence": "41.920",
    "data_quality": "87.730",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-14 23:40:38.845644+00"
  },
  {
    "id": 40,
    "as_of": "2026-08-14",
    "direction": "USD→URA",
    "edge_score": "30.110",
    "confidence": "42.110",
    "data_quality": "87.710",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-15 23:40:39.576205+00"
  },
  {
    "id": 42,
    "as_of": "2026-08-14",
    "direction": "USD→URA",
    "edge_score": "30.110",
    "confidence": "42.110",
    "data_quality": "87.710",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-16 23:40:36.608204+00"
  },
  {
    "id": 44,
    "as_of": "2026-08-17",
    "direction": "USD→URA",
    "edge_score": "30.250",
    "confidence": "42.260",
    "data_quality": "88.010",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-17 23:41:11.633815+00"
  },
  {
    "id": 46,
    "as_of": "2026-08-18",
    "direction": "USD→URA",
    "edge_score": "28.010",
    "confidence": "40.720",
    "data_quality": "87.580",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-18 23:40:34.291015+00"
  },
  {
    "id": 48,
    "as_of": "2026-08-19",
    "direction": "USD→URA",
    "edge_score": "28.120",
    "confidence": "40.820",
    "data_quality": "87.710",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-19 23:40:58.910754+00"
  },
  {
    "id": 50,
    "as_of": "2026-08-20",
    "direction": "USD→URA",
    "edge_score": "24.940",
    "confidence": "38.750",
    "data_quality": "87.690",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-20 23:40:38.961071+00"
  },
  {
    "id": 52,
    "as_of": "2026-08-21",
    "direction": "USD→URA",
    "edge_score": "26.980",
    "confidence": "40.080",
    "data_quality": "87.720",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-21 23:40:32.209634+00"
  },
  {
    "id": 54,
    "as_of": "2026-08-21",
    "direction": "USD→URA",
    "edge_score": "26.670",
    "confidence": "39.880",
    "data_quality": "87.710",
    "status": "WAIT",
    "model_version": "1.2.0",
    "created_at": "2026-08-22 23:40:35.686101+00"
  }
]
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
Sonuç Çıktısı:
```json
[
  {
    "as_of": "2026-08-21",
    "factor_code": "breadth",
    "score": "48.097",
    "quality": "20.000",
    "weight": "0.100000",
    "weighted_score": "0.961931",
    "details": {
      "source": "Global X URA full holdings CSV market-price history",
      "history_max": 17,
      "history_min": 9,
      "breadth_date": "2026-08-21",
      "constituents": 57,
      "holding_date": "2026-08-21",
      "component_coverage": {
        "pct_above_20dma": 0,
        "pct_above_50dma": 0,
        "new_20d_high_pct": 0,
        "pct_above_200dma": 0,
        "pct_positive_day": 1
      }
    }
  },
  {
    "as_of": "2026-08-21",
    "factor_code": "event",
    "score": "0.000",
    "quality": "20.250",
    "weight": "0.050000",
    "weighted_score": "0.000000",
    "details": {
      "monitored": true,
      "recent_events": 1,
      "directional_events": 0
    }
  },
  {
    "as_of": "2026-08-21",
    "factor_code": "fundamentals",
    "score": "-5.927",
    "quality": "100.000",
    "weight": "0.150000",
    "weighted_score": "-0.888993",
    "details": {
      "note": "Bu uranium spot arz-talep verisi değildir; ETF holdings/flow proxy'sidir.",
      "proxy": "Global X URA holdings price-adjusted AUM flow",
      "constituents": 57,
      "current_date": "2026-08-21",
      "days_between": 1,
      "previous_date": "2026-08-20",
      "aum_change_pct": 4.592793791860128,
      "flow_proxy_pct": -0.4938850402566475,
      "reference_date": "2026-08-21",
      "weight_coverage": 1.0003,
      "price_return_pct": 5.0866788321167755,
      "snapshot_age_days": 0,
      "total_market_value": 6426742729.08,
      "previous_total_market_value": 6144536823.32
    }
  },
  {
    "as_of": "2026-08-21",
    "factor_code": "macro",
    "score": "21.750",
    "quality": "97.500",
    "weight": "0.120000",
    "weighted_score": "2.544750",
    "details": {
      "latest": {
        "DGS2": 4.19,
        "DGS10": 4.69,
        "SP500": 7674.37,
        "DFII10": 2.35,
        "VIXCLS": 16.01,
        "STLFSI4": -0.8285,
        "DTWEXBGS": 118.9028,
        "NASDAQCOM": 26180.45
      },
      "degraded": [
        "DTWEXBGS"
      ],
      "reference_date": "2026-08-21",
      "used_components": [
        "VIXCLS",
        "STLFSI4",
        "DFII10"
      ],
      "stale_or_missing": [],
      "freshness_quality": {
        "DGS2": 100,
        "DGS10": 100,
        "SP500": 100,
        "DFII10": 100,
        "VIXCLS": 100,
        "STLFSI4": 100,
        "DTWEXBGS": 80,
        "NASDAQCOM": 100
      },
      "observation_dates": {
        "DGS2": "2026-08-20",
        "DGS10": "2026-08-20",
        "SP500": "2026-08-21",
        "DFII10": "2026-08-20",
        "VIXCLS": "2026-08-20",
        "STLFSI4": "2026-08-14",
        "DTWEXBGS": "2026-08-14",
        "NASDAQCOM": "2026-08-21"
      }
    }
  },
  {
    "as_of": "2026-08-21",
    "factor_code": "momentum",
    "score": "29.163",
    "quality": "100.000",
    "weight": "0.170000",
    "weighted_score": "4.957685",
    "details": {
      "rsi": 59.866157696067795,
      "macd_hist": 0.29810472994918846
    }
  },
  {
    "as_of": "2026-08-21",
    "factor_code": "trend",
    "score": "100.000",
    "quality": "100.000",
    "weight": "0.230000",
    "weighted_score": "23.000000",
    "details": {
      "ema_gap_pct": 1.9708504063081111,
      "slope_5d_pct": 1.6544814296374888
    }
  },
  {
    "as_of": "2026-08-21",
    "factor_code": "value",
    "score": "-39.899",
    "quality": "100.000",
    "weight": "0.180000",
    "weighted_score": "-7.181790",
    "details": {
      "zscore": -0.4495027644925632,
      "percentile": 0.8055555555555556
    }
  },
  {
    "as_of": "2026-08-21",
    "factor_code": "volatility",
    "score": "68.643",
    "quality": "100.000",
    "weight": "0.000000",
    "weighted_score": "0.000000",
    "details": {
      "rv20": 0.45462386507016467,
      "rv60": 0.49763399012219584,
      "ratio": 0.913570765048686
    }
  }
]
```
### 6.5 Holdings history

```sql
select
    count(distinct holding_date) as holdings_days,
    min(holding_date) as first_date,
    max(holding_date) as last_date
from fundamentals.ura_holdings;
```
Sonuç Çıktısı:
```json
[
  {
    "holdings_days": 17,
    "first_date": "2026-07-29",
    "last_date": "2026-08-21"
  }
]
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
Sonuç Çıktısı:
```json
[
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 18:35:01.963981+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 17:35:00.730135+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 16:35:00.090592+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 15:35:00.016528+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 14:35:00.01115+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 13:35:00.007362+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 12:35:00.028437+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 11:35:00.003611+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 10:35:00.005201+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 09:35:00.008318+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 08:35:00.006069+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 07:35:00.00852+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 06:35:00.009405+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 05:35:00.02479+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 04:35:00.013043+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 03:35:00.088864+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 02:35:00.134438+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 01:35:00.001754+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-23 00:35:00.169114+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 23:35:00.012687+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 22:35:01.029388+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 21:35:00.15609+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 20:35:00.033118+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 19:35:00.980992+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 18:35:00.117544+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 17:35:00.845603+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 16:35:00.007287+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 15:35:00.006396+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 14:35:00.008391+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 13:35:00.122335+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 12:35:00.13163+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 11:35:00.204416+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 10:35:00.027805+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 09:35:00.016129+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 08:35:00.005518+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 07:35:00.002728+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 06:35:00.006832+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 05:35:00.004731+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 05:01:16.965706+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.2%",
    "details": {
      "quality": 20.25,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "028260 KS",
        "BHP AU"
      ],
      "matched_fund_weight": 0.2025,
      "considered_top_n_weight": 0.76
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 04:35:00.00485+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.0%",
    "details": {
      "quality": 20.01,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2001,
      "considered_top_n_weight": 0.7508
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 03:35:00.01674+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.0%",
    "details": {
      "quality": 20.01,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2001,
      "considered_top_n_weight": 0.7508
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 02:35:00.156576+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.0%",
    "details": {
      "quality": 20.01,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2001,
      "considered_top_n_weight": 0.7508
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 01:35:00.108426+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.0%",
    "details": {
      "quality": 20.01,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2001,
      "considered_top_n_weight": 0.7508
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-22 00:35:00.248357+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 4 recent filing, fund weight coverage 20.0%",
    "details": {
      "quality": 20.01,
      "scope_cap": 70,
      "filings_seen": 4,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "LEU",
        "XE",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2001,
      "considered_top_n_weight": 0.7508
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 23:35:00.475531+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 22:35:00.673752+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 21:35:00.374947+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 20:35:01.175244+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 19:35:00.421068+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 18:35:05.719841+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 17:35:01.13054+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 16:35:21.640631+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 15:35:00.08891+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 14:35:00.096232+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 13:35:00.021016+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 12:35:00.277078+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 11:35:00.220529+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 10:35:00.156584+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 09:35:00.007858+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 08:35:00.024568+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 07:35:00.033296+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 06:35:00.099979+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 05:35:00.071234+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 04:35:12.725169+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 03:35:01.073473+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 02:35:29.891143+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 01:35:01.190187+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-21 00:35:00.018464+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 5 recent filing, fund weight coverage 20.5%",
    "details": {
      "quality": 20.47,
      "scope_cap": 70,
      "filings_seen": 5,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "000720 KS",
        "047040 KS"
      ],
      "matched_fund_weight": 0.2047,
      "considered_top_n_weight": 0.7569
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 23:35:00.267302+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 22:35:00.980108+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 21:35:00.196858+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 20:35:00.243356+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 19:35:01.081935+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 18:35:05.287968+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 17:35:00.180273+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 16:35:00.105333+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 15:35:00.124849+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 14:35:04.360703+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 13:35:00.001936+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 12:35:00.015997+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 11:35:00.606342+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 10:35:00.153956+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 09:35:00.022368+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 08:35:00.028566+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 07:35:00.009295+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 06:35:00.011846+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 05:35:00.015589+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 04:35:00.015364+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 03:35:00.081732+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 02:35:00.313781+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 01:35:00.306094+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-20 00:35:00.016972+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 7 recent filing, fund weight coverage 19.8%",
    "details": {
      "quality": 19.84,
      "scope_cap": 70,
      "filings_seen": 7,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "7011 JP",
        "047040 KS"
      ],
      "matched_fund_weight": 0.1984,
      "considered_top_n_weight": 0.7513
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-19 23:35:00.806037+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%",
    "details": {
      "quality": 20.29,
      "scope_cap": 70,
      "filings_seen": 10,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "047040 KS",
        "034020 KS"
      ],
      "matched_fund_weight": 0.2029,
      "considered_top_n_weight": 0.7539
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-19 22:35:00.389711+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%",
    "details": {
      "quality": 20.29,
      "scope_cap": 70,
      "filings_seen": 10,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "047040 KS",
        "034020 KS"
      ],
      "matched_fund_weight": 0.2029,
      "considered_top_n_weight": 0.7539
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-19 21:35:00.311611+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%",
    "details": {
      "quality": 20.29,
      "scope_cap": 70,
      "filings_seen": 10,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "047040 KS",
        "034020 KS"
      ],
      "matched_fund_weight": 0.2029,
      "considered_top_n_weight": 0.7539
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-19 20:35:00.241632+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%",
    "details": {
      "quality": 20.29,
      "scope_cap": 70,
      "filings_seen": 10,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "047040 KS",
        "034020 KS"
      ],
      "matched_fund_weight": 0.2029,
      "considered_top_n_weight": 0.7539
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-19 19:35:17.052433+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%",
    "details": {
      "quality": 20.29,
      "scope_cap": 70,
      "filings_seen": 10,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "047040 KS",
        "034020 KS"
      ],
      "matched_fund_weight": 0.2029,
      "considered_top_n_weight": 0.7539
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-19 18:35:00.177883+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%",
    "details": {
      "quality": 20.29,
      "scope_cap": 70,
      "filings_seen": 10,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "047040 KS",
        "034020 KS"
      ],
      "matched_fund_weight": 0.2029,
      "considered_top_n_weight": 0.7539
    }
  },
  {
    "job_name": "sec_event_job",
    "started_at": "2026-08-19 17:35:05.129931+00",
    "status": "DEGRADED",
    "message": "SEC filings kontrol edildi: 5 entity, 10 recent filing, fund weight coverage 20.3%",
    "details": {
      "quality": 20.29,
      "scope_cap": 70,
      "filings_seen": 10,
      "matched_tickers": [
        "OKLO",
        "UEC",
        "XE",
        "LEU",
        "SMR"
      ],
      "entities_checked": 5,
      "unmatched_tickers": [
        "CCO CN",
        "U-U CN",
        "NXE CN",
        "KAP LI",
        "EFR CN",
        "PDN AU",
        "DML CN",
        "SSW SJ",
        "047040 KS",
        "034020 KS"
      ],
      "matched_fund_weight": 0.2029,
      "considered_top_n_weight": 0.7539
    }
  },
  {
    "job_name": "hourly_job",
    "started_at": "2026-08-19 17:05:02.299558+00",
    "status": "ERROR",
    "message": "couldn't get a connection after 10.00 sec",
    "details": {
      "provider_mode": "auto"
    }
  }
]
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
