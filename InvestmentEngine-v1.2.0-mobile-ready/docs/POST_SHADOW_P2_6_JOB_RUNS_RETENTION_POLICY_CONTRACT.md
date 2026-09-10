# Post-Shadow P2.6 — `system.job_runs` Evidence-Aware Retention Policy Contract

Tarih: 10 Eylül 2026  
Kontrol zamanı: `2026-09-10T13:53:28.945838+00:00`  
Model version: `1.2.0`  
Mode: `SHADOW`  
Shadow readiness: `READY`  
LIVE: `NO-GO`  
Durum: `CLOSED / POLICY CONTRACT VERIFIED / NO CURRENT DELETE`

## 1. Amaç

P2.6, P2.5 production baseline sonrasında `system.job_runs` için kör yaş bazlı DELETE yerine evidence-aware retention/compaction kontratı tanımlar.

Canonical verification:

- `verification/verify_job_runs_p2_6_retention_policy_dry_run.sql`

Bu adımda production mutation yapılmadı:

- `DELETE`: yok
- `UPDATE`: yok
- `INSERT`: yok
- migration / DDL: yok
- `VACUUM FULL`: yok
- scheduler değişikliği: yok
- model threshold/weight/K1/K2/reset/sizing değişikliği: yok

Temel ayrım:

```text
COMPACTION_CANDIDATE != DELETE AUTHORIZED
```

P2.6 bir adaylık kontratı kurar. Production mutation zorunluluğu doğurmaz.

---

## 2. Production dry-run sonucu

Safety checks:

```text
groups_checked                                      73
groups_missing_anchor                                0
classifier_safety_complete                        true
every_group_retains_daily_anchor                  true
sim30_daily_anchors_never_candidate               true
sim30_incident_rows_never_candidate               true
sim30_milestone_jobs_never_candidate              true
sim30_provenance_gaps_never_candidate             true
sim30_non_scheduler_rows_never_candidate          true
sim30_status_message_boundaries_never_candidate   true
proposed_policy_never_touches_current_readiness   true
```

Sonuç: classifier, koruma sınıflarının hiçbirini 30 günlük agresif simülasyonda bile candidate setine sızdırmamıştır.

---

## 3. Scenario evidence

### 30 günlük simülasyon

30 günlük cutoff yalnız güvenlik stres testi olarak çalıştırıldı; production politikası değildir.

```text
rows older than cutoff             675
compaction candidates              511
protected rows                     164
candidate OK                       270
candidate DEGRADED                 241
candidate scheduled                 0
candidate scheduled_legacy         511
candidate payload bytes        230,365
```

Korunan 164 satırın nedeni:

```text
PROTECT_DAILY_FIRST_LAST_ANCHOR          89
PROTECT_STATUS_MESSAGE_BOUNDARY          42
PROTECT_PROVENANCE_GAP                   13
PROTECT_NON_SCHEDULER_EVIDENCE           12
PROTECT_INCIDENT_OR_UNKNOWN_STATUS        7
PROTECT_MILESTONE_JOB                     1
```

Bu sonuç iki noktayı doğrular:

1. Aynı gün içindeki tekrarlı routine telemetry gerçekten ayrıştırılabilir.
2. DEGRADED satırlar OK ile kör biçimde aynı sınıfa atılmaz; yalnız aynı status/message segmentinin iç tekrarı candidate olabilir, boundary ve günlük kanıt anchorları korunur.

### 60 / 90 / 180 günlük senaryolar

Production dataset henüz bu yaşlara ulaşmadığından candidate yoktur:

```text
60d   rows older=0   candidate=0
90d   rows older=0   candidate=0
180d  rows older=0   candidate=0
```

Bu nedenle bugün gerçek production DELETE/compaction uygulanamaz ve uygulanmamalıdır.

---

## 4. Accepted evidence-aware policy

### 4.1 Full-fidelity window

```text
FULL_FIDELITY_WINDOW = 90 DAYS
```

Son 90 gündeki tüm `system.job_runs` satırları tam fidelity ile korunur.

Bu pencere current readiness'in 7 günlük bağımlılığından belirgin şekilde büyüktür ve incident/RCA incelemesi için ilave güvenlik marjı sağlar.

### 4.2 Her yaşta korunan evidence sınıfları

Aşağıdakiler basit retention adayı değildir:

- `ERROR` ve unknown/other status,
- `manual`, `test`, `backfill`, `development`,
- `maintenance`, `dependency`, `legacy`,
- `shadow_epoch_id IS NULL` provenance boşlukları,
- release/audit/milestone job'ları,
- status veya message değişim sınırları,
- Europe/Istanbul operasyon gününde her `job_name + run_kind + status + root_job_name` grubunun ilk ve son satırı.

Milestone/audit sınıfında en az `monthly_audit_job` korunur. Gelecekte yeni release/shadow milestone job'ları eklenirse classifier listesi açıkça genişletilmelidir; sessizce routine telemetry sayılmamalıdır.

### 4.3 90 günden sonra aday olabilen tek sınıf

Yalnız aşağıdaki koşulların tamamını sağlayan satırlar `COMPACTION_CANDIDATE` olabilir:

```text
started_at < now() - 90 days
AND run_kind IN ('scheduled', 'scheduled_legacy')
AND status IN ('OK', 'DEGRADED', 'SKIPPED')
AND protected evidence class değil
AND daily first/last anchor değil
AND status/message boundary değil
```

Bu, yalnız eski intra-day routine repetition'ı hedefler.

### 4.4 DEGRADED semantiği

`DEGRADED` tümüyle silinebilir telemetry değildir.

Accepted rule:

- yeni/benzersiz DEGRADED durum geçişi korunur,
- message/status boundary korunur,
- günlük ilk/son DEGRADED anchor korunur,
- aynı gün ve aynı semantic segment içindeki tekrarlı DEGRADED satırlar ancak 90 gün sonrasında candidate olabilir.

Böylece `sec_event_job` gibi uzun süre aynı degradation sebebini saatlik tekrar eden job'larda RCA trendi korunurken gereksiz intra-day tekrarlar gelecekte compact edilebilir.

---

## 5. Current production decision

Bugünkü dataset için:

```text
90d compaction candidates        0
production DELETE authorized     false
production compaction required   false
storage pressure                 not proven
VACUUM FULL                      not justified
```

P2.5 physical baseline yaklaşık 4 MB relation ve `n_dead_tup=0` göstermiştir.

Dolayısıyla P2.6'nın kapanışı bir production cleanup operasyonu değildir; güvenli gelecek eligibility kontratıdır.

---

## 6. Ten-year growth context

Dry-run projection:

```text
recent rows/day                         55.07
recent payload bytes/day            24,467.4
10y rows without retention estimate   200,993
10y payload bytes estimate         89,306,010
```

Bu büyüme bugünden agresif cleanup gerektirecek seviyede değildir.

Accepted operational consequence:

- retention mutation takvimsel olarak sırf 90 gün doldu diye zorunlu çalıştırılmaz,
- P2.7 önce bounded observability kurabilir,
- 90 günden eski candidate oluştuğunda dahi mutation ancak aynı classifier güvenlik kontratıyla ve bounded batch davranışıyla yapılabilir,
- tablo boyutu/growth düşük kaldığı sürece no-op maintenance kabul edilebilir ve tercih edilir.

---

## 7. P2.7 entegrasyon sınırı

P2.7 yeni scheduler/queue katmanı oluşturmamalıdır.

Mevcut scheduler mimarisinde en küçük entegrasyon tercih edilir. İlk doğal aday mevcut `monthly_audit_job`dır.

Ancak P2.6 şu anda P2.7'ye zorunlu DELETE talimatı vermez.

P2.7 için kabul edilen sınır:

1. macro tarafında P2.4 gereği recurring DELETE yok,
2. job_runs tarafında 90 günlük full-fidelity + evidence-aware classifier kontratı var,
3. önce bounded growth/health observability,
4. candidate yoksa maintenance `NO-OP`,
5. candidate varsa bile batch sınırı ve safety invariant doğrulanmadan mutation yok,
6. `VACUUM FULL` otomatik maintenance değildir,
7. model semantiği ve scheduler cadence değişmez.

---

## 8. Final P2.6 contract

```text
FULL FIDELITY WINDOW                    90 DAYS
BLIND AGE DELETE                         REJECTED
ERROR / INCIDENT PRUNING                 REJECTED
NON-SCHEDULER EVIDENCE PRUNING           REJECTED
PROVENANCE GAP PRUNING                   REJECTED
MILESTONE PRUNING                        REJECTED
STATUS/MESSAGE BOUNDARY PRUNING          REJECTED
DAILY FIRST/LAST ANCHOR PRUNING          REJECTED
OLD INTRA-DAY ROUTINE REPETITION         ELIGIBLE AFTER 90D
CURRENT PRODUCTION CANDIDATES             0
CURRENT DELETE                            NONE
AUTOMATIC DELETE REQUIREMENT              NONE
P2.7                                      NEXT
```

P2.6 `CLOSED` kabul edilir.
