# Post-Shadow P2 — Macro Observations ve Job Runs Veri Yaşam Döngüsü Görev Borcu

Tarih: 09 Eylül 2026  
Son durum güncellemesi: 10 Eylül 2026  
Durum: `OPEN — P2.1/P2.2/P2.3/P2.4/P2.5 CLOSED; P2.6 NEXT`  
Model version: `1.2.0`  
Mode: `SHADOW`  
LIVE: `NO-GO`

## 1. Amaç ve kapsam

Bu görev borcu iki büyüyen production tablosunun veri yaşam döngüsünü kanıtla yönetmek içindir:

1. `macro.observations`
2. `system.job_runs`

Amaç yalnız tablo küçültmek değildir. Karar, validation, readiness ve operasyonel RCA için gereken kanıt korunurken semantik olarak gereksiz veri üretiminin engellenmesi ve güvenli retention/maintenance politikasının kurulmasıdır.

Bu başlık strict FRED/ALFRED PIT doğrulamasından ayrıdır. Threshold, factor weight, K1/K2, reset, sizing, scheduler cadence veya SHADOW/LIVE davranışını otomatik değiştirmez.

## 2. Tamamlanan macro.observations aşamaları

### P2.1 — Production baseline / duplicate sınıflandırması — CLOSED

Production baseline şu problemi doğruladı:

- toplam row: `295,123`
- `(series_id, observation_date)` grubu: `11,809`
- dominant problem: aynı value'nun farklı current-view fetch günlerinde tekrar kalıcılaştırılması
- gerçek FRED value revision geçmişi de mevcut; özellikle `STLFSI4` geniş revision lineage taşır
- conflict UPDATE churn de production'da doğrulandı

Blind `UNIQUE(series_id, observation_date)` yaklaşımı gerçek revision bilgisini kaybedeceği için reddedildi.

Canonical evidence:

- `docs/POST_SHADOW_P2_1_MACRO_OBSERVATIONS_PRODUCTION_BASELINE.md`

### P2.2 — Deterministic production/validation read contract — CLOSED

FRED current-view collector `realtime_start/realtime_end` parametrelerini göndermediğinden bu alanların gün değiştirmesi tek başına ekonomik value revision kabul edilmez.

Kontrat:

- historical karar için bugünkü current-latest row authoritative değildir,
- live karar için evaluation anında gerçekten mevcut latest current-view bilgi esastır,
- pre-hardening exact intraday first-seen provenance'ın önemli bölümü artık reconstruct edilemez,
- strict ALFRED/PIT doğrulaması ayrı doğrulama yolu olarak kalır,
- deterministic tie-break gerekir.

Canonical evidence:

- `docs/POST_SHADOW_P2_2_MACRO_DETERMINISTIC_READ_CONTRACT.md`

### P2.3 — Safe dedup + future duplicate prevention — CLOSED

Dry-run value-transition classifier production üzerinde doğrulandı:

- dry-run total: `295,123`
- retained transition rows: `20,433`
- candidate delete rows: `274,690`
- delete candidate oranı: yaklaşık `%93.08`
- revision groups: `1,505`
- value-reversion groups: `57`
- decision refs preserved: `672/672`
- decision refs lost: `0`
- `safe_dedup_contract_complete=true`

`A -> A -> B -> B -> A` örneğinde yalnız ardışık aynı-value tekrarları redundant kabul edilir; gerçek `A -> B -> A` reversion lineage korunur.

Runtime hardening:

- incoming value latest retained value ile aynıysa INSERT yok,
- same-value refetch UPDATE yapmaz ve `fetched_at`ı ileri taşımaz,
- value değişmişse yeni immutable transition row yazılır,
- same-series writer'lar transaction advisory lock ile serialize edilir,
- latest/history okumaları explicit deterministic ordering kullanır.

Migration `0015_macro_observations_transition_dedup.sql` production'a uygulanmıştır.

Natural scheduler forward verification:

- natural `macro_job` id: `2304`
- run_kind: `scheduled`
- status: `OK`
- baseline rows: `20,433`
- post-run rows: `20,434`
- new legitimate observation: `1`
- post-boundary same-value duplicate: `0`
- global consecutive same-value rows: `0`
- decision refs: `680/680` preserved
- `forward_contract_complete=true`

Canonical evidence:

- `docs/POST_SHADOW_P2_3_MACRO_SAFE_DEDUP_DRY_RUN.md`
- `docs/POST_SHADOW_P2_3_MACRO_IMPLEMENTATION_VALIDATION.md`
- `verification/verify_macro_observations_p2_3_forward.sql`

### P2.4 — Macro retention policy + maintenance — CLOSED

P2.4 production üzerinde read-only baseline ile yürütüldü. P2.3 sonrası retained setin yaş dağılımı, revision/value-transition lineage, released decision evidence, current replay dependency ve physical maintenance durumu ölçüldü.

Final production baseline:

```text
retained rows                         20,435
observation-date groups               11,811
base observation rows                 11,811
legitimate value-transition rows       8,624
same-value repeat rows                     0
released decision refs                680/680 preserved
current replay unresolved                  0
consumer-unreferenced rows            13,381
consumer-unreferenced transitions      8,420
>10y retained rows                     6,672
>10y transition rows                   5,687
n_dead_tup                                 0
relation total size                    57 MB
```

Accepted retention/maintenance kontratı:

```text
SAFE LOGICAL DELETE CLASS            NONE PROVEN
BLIND AGE CUTOFF                     REJECTED
CONSUMER-UNREFERENCED DELETE         REJECTED
VALUE-TRANSITION PRUNING             REJECTED
CURRENT BASE-ROW PRUNING             NOT JUSTIFIED
normal autovacuum/autoanalyze        SUFFICIENT CURRENTLY
manual VACUUM                        NOT PROVEN NECESSARY
VACUUM FULL                          NOT JUSTIFIED
production mutation                  NONE
scheduler change                     NONE
```

P2.4 sonucu macro tarafında recurring DELETE işi üretmemiştir. P2.7 sırf maintenance framework oluşturmak için macro cleanup eklememelidir. Gerekirse yalnız bounded/read-only growth ve physical-health observability mevcut scheduler mimarisinde değerlendirilir.

Canonical evidence:

- `verification/verify_macro_observations_p2_4_retention_baseline.sql`
- `docs/POST_SHADOW_P2_4_MACRO_RETENTION_PRODUCTION_BASELINE.md`
- `docs/POST_SHADOW_P2_4_MACRO_RETENTION_MAINTENANCE_CONTRACT.md`

## 3. system.job_runs aşamaları

### P2.5 — Production baseline — CLOSED

P2.5 production üzerinde yalnız READ-ONLY ölçüm ile tamamlandı.

Overall baseline:

```text
total rows                         2,327
oldest started_at                  2026-07-30T00:32:13.964357+00:00
latest started_at                  2026-09-10T13:35:00.015676+00:00
rows last 1d                          55
rows last 7d                         386
rows last 30d                      1,652
rows older than 30d                  675
rows older than 90d                    0
unfinished rows                        0
negative-duration rows                 0
relation total                     ~4 MB
n_dead_tup                             0
```

Status/evidence dağılımı:

```text
OK                               1,305
DEGRADED                         1,010
ERROR                               12
SKIPPED                              0
explicit manual/test/backfill       15
```

Hacmin baskın kaynakları:

```text
sec_event_job     1,007 rows / 1,004 DEGRADED
hourly_job        1,000 rows /   992 OK / 8 ERROR-or-other
macro_job           174 rows /   168 OK / 6 DEGRADED
```

Provenance:

```text
scheduled_legacy    1,941
scheduled             357
maintenance            12
manual                 10
test                    4
dependency              2
backfill                 1
unresolved legacy        0
```

Shadow evidence:

```text
shadow-1.2.0-initial / epoch 1     2,306 rows
pre-epoch / no shadow_epoch_id        21 rows
```

Current readiness contract son 7 günü kullanır, `realtime_test`i dışlar ve `OK/DEGRADED/SKIPPED` statülerini successful sayar. Baseline anında readiness seti `385/385` successful'dır. Bu nedenle `DEGRADED` operational evidence olmasıyla readiness başarısızlığı olması aynı şey değildir.

P2.5 sonucu:

```text
baseline_complete                 true
production mutation               none
retention delete authorized       false
VACUUM FULL authorized            false
blind 7/30/90 day delete          not justified
```

Canonical evidence:

- `verification/verify_job_runs_p2_5_production_baseline.sql`
- `docs/POST_SHADOW_P2_5_JOB_RUNS_PRODUCTION_BASELINE.md`

### P2.6 — Evidence-aware retention policy — NEXT / OPEN

P2.5 kanıtı, tek tip age-based retention'ın güvenli olmadığını gösterir. P2.6 en az şu sınıfları ayrı ele almalıdır:

```text
ROUTINE SUCCESS TELEMETRY
ROUTINE DEGRADED TELEMETRY
ERROR / INCIDENT EVIDENCE
MANUAL / BACKFILL / TEST EVIDENCE
RELEASE / SHADOW MILESTONE EVIDENCE
```

P2.6 minimum güvenlik sınırları:

- current 7-day readiness window kesin korunur,
- ERROR/incident evidence kör age cutoff ile silinmez,
- DEGRADED telemetry `OK` ile otomatik aynı sınıfa konmaz,
- manual/backfill/test evidence düşük hacimli yüksek değerli kanıt olarak ayrılır,
- pre-epoch/release/bootstrap history doğrudan routine telemetry kabul edilmez,
- `scheduled_legacy` provenance limitation retention gerekçesi değildir,
- deletion candidate set varsa önce read-only/dry-run ile ölçülür,
- herhangi bir DELETE/migration/scheduler change ancak evidence sonrası ayrıca onaylanır.

### P2.7 — Autonomous bounded maintenance integration — OPEN

P2.4 macro kontratı ve P2.6 job-runs kontratı birlikte değerlendirilerek mevcut scheduler mimarisine gerçekten gerekli en küçük maintenance/observability entegrasyonu yapılır.

P2.4 gereği macro tarafında bugün kanıtlanmış recurring DELETE yoktur. P2.7 macro için cleanup uydurmamalı; gerekirse yalnız bounded/read-only growth/physical-health observability eklemelidir.

## 4. Güncel görev sırası

```text
P1    URA immutable raw holdings source snapshot     CLOSED
P2.1  macro.observations production baseline         CLOSED
P2.2  macro deterministic read/version contract      CLOSED
P2.3  macro dedup + future duplicate prevention      CLOSED
P2.4  macro retention policy + maintenance           CLOSED
P2.5  job_runs production baseline                   CLOSED
P2.6  job_runs evidence-aware retention policy       NEXT / OPEN
P2.7  autonomous bounded maintenance integration     OPEN
```

## 5. Model/LIVE sınırı

Bu veri yaşam döngüsü çalışmaları model davranışı tuning işi değildir.

```text
Threshold/weights/K1/K2/reset/sizing     UNCHANGED
Model version                            1.2.0
Mode                                     SHADOW
Realtime execution                       OFF
LIVE                                     NO-GO
```
