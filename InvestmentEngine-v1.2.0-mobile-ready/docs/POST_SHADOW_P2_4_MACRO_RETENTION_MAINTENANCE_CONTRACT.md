# Post-Shadow P2.4 — `macro.observations` Retention / Maintenance Closure Contract

Tarih: 10 Eylül 2026  
Model version: `1.2.0`  
Mode: `SHADOW`  
Shadow readiness: `READY`  
LIVE: `NO-GO`  
Durum: `CLOSED / RETENTION DELETE NOT JUSTIFIED`

## 1. Amaç

Bu belge P2.4 read-only production baseline sonucunu formal retention/maintenance kontratına dönüştürür.

P2.4 bir tablo küçültme hedefi değildir. Amaç, P2.3 sonrası retained `macro.observations` verisinin hangi bölümünün korunması gerektiğini, güvenle silinebilen bir row sınıfı bulunup bulunmadığını ve fiziksel maintenance ihtiyacını production evidence ile karara bağlamaktır.

Canonical baseline:

- `docs/POST_SHADOW_P2_4_MACRO_RETENTION_PRODUCTION_BASELINE.md`
- `verification/verify_macro_observations_p2_4_retention_baseline.sql`

Bu kapanış hiçbir production mutation gerektirmez.

---

## 2. Production evidence özeti

P2.4 baseline:

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

P2.3 same-value prevention kontratı production'da sağlamdır. Kalan 20,435 satır redundant refetch sınıfı değildir.

Özellikle `STLFSI4` gerçek revision lineage'ın baskın kaynağıdır ve 10 yıldan eski satırlarının büyük bölümü legitimate value transition'dır.

---

## 3. Accepted logical retention contract

Production evidence ile kabul edilen politika:

1. P2.3 sonrası retained tüm base observation satırları korunur.
2. Tüm legitimate value-transition ve value-reversion satırları korunur.
3. Same-value current-view refetch satırları writer seviyesinde persist edilmez; P2.4 bunları tekrar cleanup etmeye çalışmaz.
4. `observation_date` yaşına göre blind cutoff uygulanmaz.
5. Consumer tarafından bugün doğrudan seçilmeyen satırlar DELETE candidate kabul edilmez.
6. Released decision provenance/evidence korunur.
7. Current model validation/replay için gerekli historical coverage küçültülmez.
8. Production current-view transition lineage source/revision audit evidence olarak korunur.
9. Strict FRED/ALFRED PIT verification production-current store'dan ayrı, DB-write-free verification yolu olarak kalır.
10. Retention ancak gelecekte yeni production evidence güvenli bir logical row class kanıtlarsa yeniden açılır.

Formal sonuç:

```text
SAFE LOGICAL DELETE CLASS            NONE PROVEN
BLIND AGE CUTOFF                     REJECTED
CONSUMER-UNREFERENCED DELETE         REJECTED
VALUE-TRANSITION PRUNING             REJECTED
CURRENT BASE-ROW PRUNING             NOT JUSTIFIED
```

---

## 4. Accepted physical maintenance contract

P2.4 baseline sırasında:

```text
n_dead_tup             0
autovacuum             active / cleanup sonrası çalışmış
autoanalyze            active / cleanup sonrası çalışmış
n_ins_since_vacuum     2
n_mod_since_analyze    2
heap                    25 MB
indexes                 32 MB
total                   57 MB
```

PostgreSQL normal VACUUM/autovacuum silinmiş tuple alanını relation içinde yeniden kullanım için serbest bırakabilir; heap dosyasının işletim sistemi seviyesinde küçülmemesi tek başına bakım problemi değildir.

Kabul edilen fiziksel bakım kontratı:

```text
normal autovacuum/autoanalyze       SUFFICIENT CURRENTLY
manual VACUUM                       NOT PROVEN NECESSARY
VACUUM FULL                         NOT JUSTIFIED
periodic table/index growth check   REQUIRED AS OBSERVABILITY
```

`VACUUM FULL` ancak gelecekte ciddi physical bloat/disk pressure kanıtı ve operasyonel etki analizi oluşursa ayrı bir bakım kararı olarak değerlendirilebilir.

---

## 5. Autonomous maintenance sınırı

P2.4 sonucu macro tarafında bugün çalıştırılması gereken recurring DELETE işi üretmemiştir.

Bu nedenle P2.7'de sırf maintenance framework oluşturmak için macro DELETE eklenmez.

P2.7 açısından accepted yaklaşım:

- mevcut scheduler mimarisi korunur,
- yeni scheduler/queue katmanı eklenmez,
- macro için gerekiyorsa yalnız bounded/read-only growth ve physical-health observability eklenir,
- gelecekte kanıtlanmış bir maintenance aksiyonu doğarsa ilk entegrasyon noktası mevcut `monthly_audit_job` olarak değerlendirilir,
- mutation varsa bounded batch + explicit predicate/cutoff + dry-run/count + summary logging + açık transaction boundary gerekir,
- failure decision path'i bozmamalıdır,
- model parameterlerine dokunulmamalıdır.

Şu an için macro maintenance mutation:

```text
NONE
```

---

## 6. Model ve runtime sınırı

P2.4 retention kararı model tuning değildir.

```text
Threshold/weights/K1/K2/reset/sizing     UNCHANGED
Model version                            1.2.0
Mode                                     SHADOW
Shadow readiness                         READY
Realtime execution                       OFF
LIVE                                     NO-GO
```

Runtime writer/read contract P2.3 haliyle korunur. Migration veya deployment gerekmez.

---

## 7. P2.4 closure

Acceptance sonucu:

```text
Read-only production baseline            VERIFIED
P2.3 transition contract                 INTACT
Decision evidence                        PRESERVED
Replay coverage                          RESOLVED
Safe logical delete class                NONE PROVEN
Age-based retention                      REJECTED
Consumer-unreferenced retention          REJECTED
Physical dead-tuple pressure             NONE
Normal autovacuum                        SUFFICIENT CURRENTLY
VACUUM FULL                              NOT JUSTIFIED
Production mutation                      NONE
Scheduler change                         NONE
Model semantics                          UNCHANGED
P2.4                                     CLOSED
```

P2.4 yeniden ancak aşağıdakilerden biri yeni evidence ile ortaya çıkarsa açılır:

- writer kontratına rağmen yeni semantik redundant row sınıfı,
- anlamlı ve sürekli physical bloat/disk pressure,
- replay/decision/source-audit ihtiyaçlarını bozmadan güvenle sınıflandırılabilen yeni retention class,
- production scale nedeniyle mevcut autovacuum politikasının yetersiz olduğunun ölçülmesi.

Sonraki görev:

```text
P2.5 — system.job_runs production baseline
```
