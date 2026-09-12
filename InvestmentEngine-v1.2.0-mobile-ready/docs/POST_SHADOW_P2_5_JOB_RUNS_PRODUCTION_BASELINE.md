# Post-Shadow P2.5 — `system.job_runs` Production Baseline

Tarih: 10 Eylül 2026  
Kontrol zamanı: `2026-09-10T13:42:47.229675+00:00`  
Model version: `1.2.0`  
Mode: `SHADOW`  
Shadow readiness: `READY`  
LIVE: `NO-GO`  
Durum: `CLOSED / READ-ONLY BASELINE VERIFIED`

## 1. Amaç

P2.5, `system.job_runs` için herhangi bir retention/delete politikası uygulamadan önce gerçek production hacmini, growth profilini, provenance kalitesini, readiness bağımlılığını, incident/RCA evidence sınıflarını ve fiziksel bakım durumunu ölçer.

Canonical verification:

- `verification/verify_job_runs_p2_5_production_baseline.sql`

Bu adımda production mutation yapılmadı. Aşağıdakiler uygulanmadı:

- `DELETE`
- `UPDATE`
- `INSERT`
- migration / DDL
- `VACUUM FULL`
- scheduler değişikliği
- model threshold/weight/K1/K2/reset/sizing değişikliği

Temel güvenlik ilkesi:

```text
old / routine / current-readiness tarafından doğrudan kullanılmıyor
!=
safe-to-delete
```

---

## 2. Overall production baseline

```text
total_rows                     2,327
oldest_started_at              2026-07-30T00:32:13.964357+00:00
latest_started_at              2026-09-10T13:35:00.015676+00:00
rows_last_1d                      55
rows_last_7d                     386
rows_last_30d                  1,652
rows_last_90d                  2,327
rows_older_than_7d             1,941
rows_older_than_30d              675
rows_older_than_90d                0
unfinished_rows                    0
invalid_negative_duration_rows     0
```

Payload:

```text
total_message_bytes              89,086
total_details_bytes             936,184
total_payload_bytes           1,025,270
avg_payload_bytes                 440.60
p95_payload_bytes                 533
max_payload_bytes               2,361
```

Job runtime:

```text
avg_duration_seconds             16.575
p50_duration_seconds             11.006
p95_duration_seconds             46.297
max_duration_seconds            157.433
```

Sonuç: tablo şu anda küçük ve operasyonel açıdan sağlıklı boyuttadır. Acil storage pressure kanıtı yoktur.

---

## 3. Status / evidence dağılımı

```text
OK          1,305
DEGRADED    1,010
ERROR          12
SKIPPED         0
```

Evidence sınıfları:

```text
ROUTINE_OK                 1,305
DEGRADED_EVIDENCE          1,010
ERROR_OR_OTHER_EVIDENCE       12
```

Kritik ayrım:

- `DEGRADED` production history hacminin büyük bölümünü oluşturur.
- `ERROR` sayısı azdır ama doğrudan incident/RCA evidence sınıfıdır.
- `SKIPPED` production baseline'da yoktur.
- status tek başına retention kararı vermek için yeterli değildir; job_name, run_kind, age ve release/shadow milestone bağlamı birlikte değerlendirilmelidir.

---

## 4. Job bazında ana kaynaklar

En yüksek hacimli iki job:

```text
sec_event_job    1,007 rows
hourly_job       1,000 rows
```

`sec_event_job`:

```text
OK             2
DEGRADED    1,004
ERROR          1
```

`hourly_job`:

```text
OK           992
DEGRADED       0
ERROR/other    8
```

Diğer önemli job'lar:

```text
macro_job                  174 rows / 168 OK / 6 DEGRADED
 daily_crypto_job           47 rows / 46 OK / 1 ERROR-or-other
 daily_ura_job              47 rows / 45 OK / 2 ERROR-or-other
 daily_fx_job               31 rows / 31 OK
 model_validation_job        6 rows / 6 OK
 weekly_job                  6 rows / 6 OK
 realtime_test               4 rows / 4 OK
 monthly_audit_job           2 rows / 2 OK
 shadow_observability        2 rows / 2 OK
 crypto_history_backfill     1 row  / 1 OK
```

`sec_event_job` DEGRADED kayıtları routine success telemetry ile aynı retention sınıfına otomatik olarak konamaz. Bunlar halen sağlık/RCA açıklama değerine sahip operational evidence'dır.

---

## 5. Yaş dağılımı

Production history henüz 90 günü doldurmamıştır:

```text
0-7d       386 rows
8-30d    1,266 rows
31-90d     675 rows
>90d         0 rows
```

Her age bucket içinde evidence karışıktır:

```text
0-7d:     213 OK / 173 DEGRADED / 0 ERROR-other
8-30d:    709 OK / 552 DEGRADED / 5 ERROR-other
31-90d:   383 OK / 285 DEGRADED / 7 ERROR-other
```

Bu nedenle `7 günden eski`, `30 günden eski` veya `90 günden eski` gibi kör cutoff'lar P2.5 kanıtı ile desteklenmez.

Özellikle 12 ERROR/other kaydının tamamı 7 günden eski, 7 adedi 30 günden eskidir. Yaşa dayalı cleanup incident evidence'ı doğrudan silebilir.

---

## 6. Growth profili

Production tipik olarak yaklaşık `54-58 row/day` üretmektedir. Son 1 gün baseline'da `55 row` vardır.

Aylık gözlem:

```text
2026-07    88 rows  (partial month)
2026-08  1,710 rows
2026-09    529 rows  (10 Eylül baseline, partial month)
```

Payload büyümesi de düşük ve düzenlidir. Mevcut production ölçeğinde P2.6'nın amacı kısa vadeli disk kurtarmak değil, 10 yıllık proje ufkunda evidence-aware kontrollü büyüme politikası oluşturmaktır.

Bu dokümandaki growth verileri retention için otomatik DELETE yetkisi üretmez.

---

## 7. Provenance kalitesi

`0010_shadow_observability.sql` sonrasında `run_kind` ve `shadow_epoch_id` kontratı production'da mevcut ve trigger/index yapısı doğrulanmıştır.

Run kind dağılımı:

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

Önemli yorum:

- `scheduled_legacy` kayıtlar eski scheduler geçmişini kaybetmeden açıkça imperfect provenance olarak korur.
- yeni scheduler kayıtlarında `scheduled` provenance vardır.
- explicit manual/test/backfill kayıtları ayrı evidence sınıfı olarak ayırt edilebilir.
- unresolved `legacy` satır kalmamıştır.

`root_job_name` yalnız provenance trigger sonrasındaki doğal kayıtlar için yaygındır; eski satırlarda null olması beklenen historical limitation'dır ve retention gerekçesi değildir.

---

## 8. Shadow Epoch evidence

```text
shadow_epoch_id = 1 / shadow-1.2.0-initial    2,306 rows
shadow_epoch_id is null                          21 rows
```

Epoch dışındaki 21 satır ilk Shadow epoch başlangıcından önceki bootstrap/pre-epoch history'dir:

```text
17 OK
1 DEGRADED
3 ERROR/other
```

Bu 21 satır özellikle release/bootstrap/RCA provenance açısından otomatik silme adayı kabul edilmemelidir.

---

## 9. Current readiness contract

Released `shadow_readiness_stats()` şu job contract'ını kullanır:

```text
started_at >= now() - 7 days
job_name != realtime_test
successful status = OK / DEGRADED / SKIPPED
```

Baseline anında readiness window:

```text
jobs                              385
successful_by_current_contract    385
unsuccessful                        0
success_rate                      1.0
```

Run-kind dağılımı:

```text
scheduled           357
scheduled_legacy     21
manual                5
maintenance           2
```

Kritik yorum:

`DEGRADED` readiness kontratında successful sayılır. Dolayısıyla yüksek `sec_event_job` DEGRADED hacmi readiness başarısızlığı değildir; ancak operational evidence olarak retention tasarımında ayrı korunması gereken sınıftır.

P2.6 herhangi bir cleanup tasarlarsa current 7-day readiness dependency setini bozmayacak açık protection predicate gerektirir.

---

## 10. Explicit non-scheduler evidence

```text
manual     10
test        4
backfill    1
total      15
```

Bu kayıtlar düşük hacimli ama yüksek kanıt değerine sahiptir. Özellikle:

- manual model validation,
- realtime test,
- historical crypto backfill

kayıtları routine scheduler telemetry ile aynı retention sınıfında değerlendirilmemelidir.

---

## 11. Physical maintenance baseline

Relation:

```text
heap       3,072 kB
indexes      856 kB
total      4,024 kB
```

Table stats:

```text
n_live_tup             2,327
n_dead_tup                 0
n_tup_ins              2,327
n_tup_upd              3,907
n_tup_del                  0
autovacuum_count           2
autoanalyze_count         18
n_ins_since_vacuum       363
n_mod_since_analyze      116
```

Indexes mevcut ve kullanılıyor:

- `idx_job_runs_name_time`
- `idx_job_runs_kind_time`
- `idx_job_runs_epoch_name_time`
- primary key

Production evidence:

```text
n_dead_tup = 0
relation total = ~4 MB
VACUUM FULL = NOT AUTHORIZED / NOT JUSTIFIED
```

Acil physical maintenance ihtiyacı yoktur.

---

## 12. P2.5 sonucu

```text
READ-ONLY baseline                 VERIFIED
baseline_complete                  true
mutation_performed                 false
total rows                         2,327
relation total                     ~4 MB
rows > 90d                         0
OK                                 1,305
DEGRADED                           1,010
ERROR                                 12
explicit manual/test/backfill         15
unresolved legacy                     0
unfinished rows                       0
negative-duration rows                0
n_dead_tup                            0
current readiness window          385/385 successful
retention delete authorized        false
VACUUM FULL authorized             false
model semantics                    UNCHANGED
LIVE                               NO-GO
```

P2.5 acceptance hedefi karşılanmıştır ve bu aşama `CLOSED` kabul edilir.

Sonraki adım P2.6'dır: production evidence üzerinden `system.job_runs` için evidence-aware retention policy tasarlanacaktır. P2.6 minimum şu sınıfları ayırmalıdır:

```text
ROUTINE SUCCESS TELEMETRY
ROUTINE DEGRADED TELEMETRY
ERROR / INCIDENT EVIDENCE
MANUAL / BACKFILL / TEST EVIDENCE
RELEASE / SHADOW MILESTONE EVIDENCE
```

P2.6 tasarımı, `7/30/90 gün` gibi tek başına yaşa dayalı bir cutoff uygulamamalı ve P2.5 sonucu hiçbir production DELETE/migration/scheduler change yetkisi üretmemelidir.
