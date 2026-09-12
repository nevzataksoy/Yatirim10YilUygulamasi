# Post-Shadow P2.7 — Data Lifecycle Observability Production Deployment

Tarih: 10 Eylül 2026  
Model version: `1.2.0`  
Mode: `SHADOW`  
Shadow readiness: `READY`  
Realtime execution: `OFF`  
LIVE: `NO-GO`  
Durum: `DEPLOYED / RUNTIME VERIFIED / P2.7 CLOSEABLE`

## 1. Kapsam

P2.7 ile P2.4 macro retention ve P2.6 `system.job_runs` evidence-aware retention kontratları mevcut scheduler mimarisine observability-first biçimde entegre edildi.

Kabul edilen sınır değişmedi:

- yeni scheduler veya queue yok,
- mevcut `monthly_audit_job` entegrasyon noktası,
- macro recurring DELETE yok,
- `system.job_runs` 90 günlük full-fidelity + evidence-aware classifier izlenir,
- candidate yoksa `NO_OP`,
- candidate bulunsa bile DELETE yetkisi yok,
- otomatik `VACUUM FULL` yok,
- scheduler cadence değişmedi,
- threshold/weights/K1/K2/reset/sizing değişmedi.

## 2. Kaynak ve test kanıtı

Implementation commit:

```text
6007c8ec4007c20c248037836f34104a18796fd6
P2.7 bounded lifecycle observability entegrasyonunu ekle
```

Pre-deploy production verification commit:

```text
9db200b3b853d97ed4077045fd9e5df61da927ba
P2.7 production read-only lifecycle doğrulamasını ekle
```

Pre-deploy evidence commit:

```text
0bcb00aeb275757c6d7635e9dba5fe974e6bc465
P2.7 pre-deploy production doğrulamasını kaydet
```

Local verification:

```text
tests/test_data_lifecycle_observability.py   4/4 PASS
full pytest suite                            91/91 PASS
release_check.py                             OK
```

Production READ-ONLY classifier sonucu:

```text
production_query_contract_complete       true
macro.p2_3_regression_free               true
macro.consecutive_same_value_rows           0
job_runs.rows_older_than_full_fidelity      0
job_runs.compaction_candidate_rows          0
maintenance_action                       NO_OP
mutation_performed                       false
delete_authorized                        false
```

## 3. Windows build ve installer

Güncel OneDir build başarıyla üretildi:

```text
EXE
SHA256 F72ACCA4E1355FAF8675F2B2D3F23741329015AF6F00A1E885DDD6544D05B65F

Installer
SHA256 D3AB0648776FC586B3CB2CE6F7FD992DE5DC9911E03F46BFC1DB90FDF7C6FB90
```

Build zinciri:

```text
pytest                 91 passed
release_check.py       OK
PyInstaller OneDir     PASS
Inno Setup             PASS
```

## 4. Pre-deploy production snapshot

Deployment öncesi Windows Service:

```text
Name       RosaInvestmentEngine
State      Running
StartMode  Auto
PathName   "C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe" --service
```

Eski production EXE:

```text
SHA256 B426B6D452B0AAA8773747DE693B4EF8F9DB7E12412DA19ADCA5A16E290E1012
```

Korunması gereken generated runtime dosyaları:

```text
settings SHA256
9B399425AA664EE5ECC94553259DCAF8261EB4FF1490E5E4768DAAFA8463C88B

rosalock SHA256
5B3D7A5AA99739516DAD7D816BFB7CBEC695FCD924502EE038B383099F216D9A
```

## 5. Production deployment sonucu

Installer upgrade sonucu:

```text
INSTALLER EXIT CODE   0
```

Post-deploy service:

```text
Name       RosaInvestmentEngine
State      Running
StartMode  Auto
PathName   "C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe" --service
ProcessId  9732
_internal  present
```

Post-deploy production EXE SHA256:

```text
F72ACCA4E1355FAF8675F2B2D3F23741329015AF6F00A1E885DDD6544D05B65F
```

Bu değer build artifact SHA256 ile birebir aynıdır.

Generated runtime dosyaları deployment boyunca korunmuştur:

```text
settings SHA256
9B399425AA664EE5ECC94553259DCAF8261EB4FF1490E5E4768DAAFA8463C88B

rosalock SHA256
5B3D7A5AA99739516DAD7D816BFB7CBEC695FCD924502EE038B383099F216D9A
```

Pre/post hash eşleşmesi, upgrade sırasında settings/rosalock içeriğinin değişmediğini doğrular.

## 6. Doğal scheduler runtime kanıtı

Deployment sonrası yeni production service doğal scheduler kayıtları üretmiştir.

```text
id                 2333
started_at         2026-09-10 16:05:00.002761+00
finished_at        2026-09-10 16:05:10.280281+00
job_name           hourly_job
run_kind           scheduled
status             OK
shadow_epoch_id    1
root_job_name      hourly_job
```

```text
id                 2334
started_at         2026-09-10 16:35:00.006578+00
finished_at        2026-09-10 16:35:05.257952+00
job_name           sec_event_job
run_kind           scheduled
status             DEGRADED
shadow_epoch_id    1
root_job_name      sec_event_job
message            SEC filings kontrol edildi: 5 entity, 1 recent filing, fund weight coverage 20.0%
```

Bu iki kayıt birlikte şunları doğrular:

- yeni production EXE yalnız kopyalanmamış, service process olarak çalışmaktadır,
- scheduler doğal cadence ile iş almaktadır,
- job completion DB'ye yazılmaktadır,
- provenance trigger/runtime context `run_kind=scheduled` ve doğru `root_job_name` üretmektedir,
- aktif Shadow epoch bağlantısı korunmaktadır,
- `DEGRADED` sec-event sonucu mevcut operational semantics ile uyumludur ve deploy failure değildir.

Manuel `--once monthly` çalıştırılmamıştır. Böylece doğal scheduler evidence kirletilmemiştir.

## 7. monthly_audit_job doğal observation sınırı

P2.7 lifecycle snapshot `monthly_audit_job` içine entegredir. Bir sonraki doğal aylık scheduler çalışması 1 Ekim 2026 tarihinde oluşacaktır.

P2.7 kapanışı bu uzak tarihe bağlanmaz; çünkü aşağıdaki zincir ayrı ayrı doğrulanmıştır:

```text
source implementation       PASS
unit/integration tests      PASS
production read-only SQL    PASS
Windows build               PASS
installer deployment        PASS
artifact identity           PASS
settings/rosalock preserve  PASS
service Running/Auto        PASS
natural scheduler DB write  PASS
```

İlk doğal `monthly_audit_job` sonrasında `details.data_lifecycle` ayrıca operational forward observation olarak kontrol edilmelidir. Bu gelecekteki gözlem P2.7 implementation closure'ını yeniden açmaz; yalnız deployed monthly integration'ın ilk natural evidence kaydıdır.

## 8. P2.7 kapanış kararı

```text
IMPLEMENTATION                         PASS
TARGETED TESTS                         4/4 PASS
FULL TEST SUITE                        91/91 PASS
PRODUCTION READ-ONLY CONTRACT          PASS
WINDOWS BUILD                          PASS
INSTALLER DEPLOYMENT                   PASS
PRODUCTION EXE IDENTITY                PASS
SETTINGS/ROSALOCK PRESERVED            PASS
SERVICE RUNNING / AUTO                 PASS
NATURAL SCHEDULER RUNTIME              PASS
CURRENT MAINTENANCE ACTION             NO_OP
CURRENT PRODUCTION MUTATION            NONE
DELETE AUTHORIZED                      false
MODEL SEMANTICS CHANGE                 NONE
SCHEDULER CADENCE CHANGE               NONE
LIVE                                   NO-GO
```

Sonuç:

```text
P2.7 AUTONOMOUS BOUNDED MAINTENANCE INTEGRATION — CLOSED
```

Bu kapanış otomatik deletion/compaction yetkisi vermez. Gelecekte `compaction_candidate_rows > 0` oluşması halinde P2.6'daki unresolved `details`-only transition safety caveat ayrıca çözülmeden production DELETE yapılmamalıdır.
