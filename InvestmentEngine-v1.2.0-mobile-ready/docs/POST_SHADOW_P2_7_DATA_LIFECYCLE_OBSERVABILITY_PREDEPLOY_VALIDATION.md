# Post-Shadow P2.7 — Data Lifecycle Observability Pre-Deploy Validation

Tarih: 10 Eylül 2026  
Production read-only kontrol zamanı: `2026-09-10T14:31:50.679781+00:00`  
Model version: `1.2.0`  
Mode: `SHADOW`  
Shadow readiness: `READY`  
LIVE: `NO-GO`  
Durum: `IMPLEMENTED / TESTED / PRE-DEPLOY VERIFIED / DEPLOY NEXT`

## 1. Amaç

P2.7, P2.4 macro retention kontratı ile P2.6 `system.job_runs` evidence-aware retention kontratını mevcut scheduler mimarisine en küçük güvenli entegrasyonla taşımayı amaçlar.

Bu aşamada kabul edilen sınır observability-first'tür:

- yeni scheduler veya queue katmanı eklenmez,
- mevcut `monthly_audit_job` doğal entegrasyon noktasıdır,
- macro tarafında recurring DELETE yoktur,
- `job_runs` tarafında 90 günlük full-fidelity + evidence-aware classifier izlenir,
- candidate `0` ise bakım sonucu `NO_OP` olur,
- candidate bulunsa bile bu durum DELETE yetkisi vermez,
- `VACUUM FULL` otomatik maintenance değildir,
- scheduler cadence ve model semantics değişmez.

## 2. Implementasyon

Commit:

```text
6007c8ec4007c20c248037836f34104a18796fd6
P2.7 bounded lifecycle observability entegrasyonunu ekle
```

Değişiklikler:

```text
ADDED     app/database/data_lifecycle.py
MODIFIED  app/engine.py
ADDED     tests/test_data_lifecycle_observability.py
```

`app/database/data_lifecycle.py`:

- yalnız SELECT tabanlı lifecycle snapshot üretir,
- `macro.observations` için P2.3 same-value regression kontrolü yapar,
- macro ve `system.job_runs` physical size / dead tuple ölçer,
- `system.job_runs` için 90 günlük full-fidelity sınırını uygular,
- P2.6 evidence-aware candidate classifier'ını runtime observability'ye taşır,
- Europe/Istanbul operasyon günü kullanır,
- hiçbir mutation path içermez,
- `mutation_performed=false`,
- `delete_authorized=false` döndürür.

`app/engine.py`:

- mevcut `monthly_audit_job` cadence ve temel akışını korur,
- performance ve model validation sonrasında lifecycle snapshot alır,
- sonucu `details.data_lifecycle` altında audit evidence olarak yazar,
- lifecycle observability hatasını best-effort `DEGRADED` detail olarak taşır,
- lifecycle probe hatası mevcut model audit işini ERROR'a dönüştürmez,
- factor weights/thresholds değiştirilmez.

Scheduler tarafında değişiklik yapılmamıştır:

```text
app/scheduler.py          UNCHANGED
app/schedule_contract.py  UNCHANGED
```

## 3. Otomatik test sonucu

Local doğrulama:

```text
python -m pytest -q tests\test_data_lifecycle_observability.py
4 passed in 6.28s

python -m pytest -q
91 passed in 5.10s
```

Testlerin kilitlediği ana invariant'lar:

- lifecycle SQL içinde `DELETE FROM` yok,
- lifecycle SQL içinde `INSERT INTO` yok,
- lifecycle SQL içinde mutation `UPDATE` yok,
- lifecycle SQL içinde `VACUUM` yok,
- DB connection üzerinde commit gerektirmez,
- unsafe `<7 day` full-fidelity window reddedilir,
- candidate varsa yalnız `OBSERVE_CANDIDATES_ONLY` olur,
- candidate DELETE authorization değildir,
- lifecycle probe failure monthly audit'i ERROR'a çevirmeden `OBSERVABILITY_FAILED_NO_MUTATION` evidence üretir.

## 4. Production pre-deploy READ-ONLY verification

Canonical verification:

- `verification/verify_data_lifecycle_p2_7_production_readonly.sql`

Verification query commit:

```text
9db200b3b853d97ed4077045fd9e5df61da927ba
P2.7 production read-only lifecycle doğrulamasını ekle
```

Production sonucu:

```text
production_query_contract_complete       true
observability_only                        true
current_noop                              true
mutation_performed                        false
delete_authorized                         false
maintenance_action                       NO_OP
full_fidelity_days                        90
timezone                                  Europe/Istanbul
```

### 4.1 macro.observations

```text
rows                                      20,435
consecutive_same_value_rows                    0
p2_3_regression_free                       true
dead_tuples                                   0
total_bytes                           59,686,912
macro_delete_policy                   NONE_PROVEN
```

Yorum:

- P2.3 same-value refetch suppression production'da bozulmamıştır.
- P2.4 retained lineage için yeni safe logical delete class kanıtı oluşmamıştır.
- Physical pressure veya dead-tuple sorunu görünmemektedir.

### 4.2 system.job_runs

```text
rows                                       2,328
rows_last_7d                                 386
rows_older_than_full_fidelity                  0
compaction_candidate_rows                      0
compaction_candidate_payload_bytes             0
protected_rows_older_than_full_fidelity        0
old_incident_or_unknown_rows                   0
old_non_scheduler_evidence_rows                0
old_provenance_gap_rows                        0
old_milestone_rows                             0
old_status_message_boundary_rows               0
old_daily_anchor_rows                          0
dead_tuples                                    0
total_bytes                            4,120,576
```

Yorum:

- Production henüz 90 günlük full-fidelity pencerenin dışına taşmamıştır.
- Bu nedenle gerçek production candidate şu anda `0`dır.
- P2.7 runtime davranışının bugünkü doğru sonucu `NO_OP` olmalıdır.
- Candidate oluşsa bile accepted contract gereği otomatik DELETE yetkisi yoktur.

## 5. Pre-deploy sonucu

P2.7 implementasyonu kod/test/production-read-only contract seviyesinde doğrulanmıştır:

```text
IMPLEMENTATION                         PASS
TARGETED TESTS                        4/4 PASS
FULL TEST SUITE                       91/91 PASS
PRODUCTION READ-ONLY CONTRACT         PASS
MACRO P2.3 REGRESSION CHECK           PASS
CURRENT JOB_RUNS CANDIDATE            0
CURRENT MAINTENANCE ACTION            NO_OP
PRODUCTION MUTATION                   NONE
DELETE AUTHORIZED                     false
SCHEDULER CADENCE CHANGE              NONE
MODEL SEMANTICS CHANGE                NONE
```

## 6. Neden P2.7 henüz CLOSED değildir?

Bu aşamadaki production query doğrudan Supabase üzerinde aynı classifier kontratını doğrulamıştır; ancak `6007c8e` runtime değişikliği henüz production Windows service/EXE içine deploy edilmemiştir.

P2.7'nin `autonomous bounded maintenance integration` olarak CLOSED sayılması için en azından:

1. güncel runtime build/package doğrulanmalı,
2. production Windows service bu runtime ile güncellenmeli,
3. settings/secrets/service identity korunmalı,
4. service start/health doğrulanmalı,
5. runtime'ın lifecycle observability path'ini taşıdığı deployment evidence ile doğrulanmalıdır.

Aylık doğal scheduler çalışması bir sonraki ayın 1'inde oluşacağından, kapanışı yalnız bu uzak tarihe bağlamak zorunlu değildir. Ancak production runtime'a kodun gerçekten deploy edildiğine dair kanıt olmadan P2.7 kapatılmamalıdır.

## 7. Sonraki adım

```text
P2.7 DEPLOY / RUNTIME VERIFICATION
```

Deploy sırasında:

- migration gerekmez,
- schema değişikliği gerekmez,
- scheduler değişikliği gerekmez,
- DELETE gerekmez,
- `VACUUM FULL` gerekmez,
- model version değiştirilmez,
- threshold/weights/K1/K2/reset/sizing değiştirilmez,
- realtime execution açılmaz,
- LIVE `NO-GO` kalır.

Beklenen production davranışı candidate `0` olduğu sürece:

```text
data_lifecycle.maintenance_action = NO_OP
mutation_performed                = false
delete_authorized                 = false
```
