# Post-Shadow P2 — Macro Observations ve Job Runs Veri Yaşam Döngüsü Görev Borcu

Tarih: 09 Eylül 2026  
Son durum güncellemesi: 10 Eylül 2026  
Durum: `OPEN — P2.1/P2.2/P2.3 CLOSED; P2.4 NEXT`  
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

Migration `0015_macro_observations_transition_dedup.sql` production'a uygulanmıştır:

- retained rows: `20,433`
- consecutive same-value rows: `0`
- decision refs: `672/672` preserved
- legacy `UNIQUE(series_id, observation_date,realtime_start)`: removed
- deterministic version index: present
- `safe_cleanup_complete=true`

Natural scheduler forward verification da tamamlandı:

- natural `macro_job` id: `2304`
- run_kind: `scheduled`
- status: `OK`
- start: `2026-09-10T03:15:00.006946+00:00` = `10.09.2026 06:15 TRT`
- baseline rows: `20,433`
- post-run rows: `20,434`
- new legitimate observation: `1`
- post-boundary same-value duplicate: `0`
- global consecutive same-value rows: `0`
- decision refs: `680/680` preserved
- `forward_contract_complete=true`

Dolayısıyla hem mevcut şişkinlik temizlenmiş hem de aynı problemin normal production ingest ile yeniden üretilmesini engelleyen writer kontratı forward-verified olmuştur.

Canonical evidence:

- `docs/POST_SHADOW_P2_3_MACRO_SAFE_DEDUP_DRY_RUN.md`
- `docs/POST_SHADOW_P2_3_MACRO_IMPLEMENTATION_VALIDATION.md`
- `verification/verify_macro_observations_p2_3_forward.sql`

## 3. P2.4 — Macro retention policy + maintenance — NEXT / OPEN

P2.4 Oturum12 içinde **başlatılmamıştır**. Oturum13'ün ilk yeni görevidir.

P2.4'ün görevi P2.3 dedup problemini tekrar çözmek değildir. Aynı-value duplicate prevention artık production'da CLOSED'dur.

Retention tasarımı minimum şu kanıtları korumalıdır:

- legitimate value-transition/revision lineage,
- released decision payload'larının macro provenance/evidence ihtiyacı,
- historical validation/replay gereksinimleri,
- 10 yıllık yatırım/validation hedefi,
- strict source/revision audit gereksinimleri.

Bu nedenle:

- blind age-based delete uygulanmaz,
- `(series_id, observation_date)` bazında revision'ları ezen cleanup yapılmaz,
- `VACUUM FULL` gibi agresif ve tablo kilitleyen fiziksel bakım işlemleri ihtiyaç/etki analizi olmadan çalıştırılmaz,
- önce mevcut retained transition tarihçesinin yaş/consumer ihtiyacı read-only olarak ölçülür.

Bakımın otonomlaştırılması gerekirse ilk tercih yeni scheduler katmanı eklemek değil mevcut `monthly_audit_job` içine bounded data-lifecycle maintenance entegre etmektir.

Aday güvenlik kontratı:

```text
monthly_audit_job
  -> existing model audit/validation
  -> bounded data-lifecycle maintenance
```

Maintenance özellikleri:

- bounded batch,
- explicit cutoff,
- protected evidence predicate,
- dry-run/count mode,
- silinen/korunan row sayısı summary logging,
- açık transaction boundary,
- failure halinde decision path'i bozmama,
- model parameterlerine dokunmama.

## 4. system.job_runs açık görevleri

### P2.5 — Production baseline — OPEN

Ölçülecekler:

- total row / physical size,
- job_name + status dağılımı,
- günlük/aylık growth,
- oldest/latest timestamps,
- ERROR/DEGRADED/OK/SKIPPED dağılımı,
- manual/test/backfill oranı,
- 7/30/90 gün dışındaki row sayıları,
- details/message payload boyutları.

Released runtime son 7 günü readiness için yoğun kullanıyor olsa da daha eski `job_runs` kayıtları P0/RCA ve historical incident evidence olarak kullanılmıştır. Bu nedenle `7 günden eski her şeyi sil` kabul edilmez.

### P2.6 — Evidence-aware retention policy — OPEN

En az şu sınıflar ayrılmalıdır:

```text
ROUTINE SUCCESS TELEMETRY
ROUTINE DEGRADED TELEMETRY
ERROR / INCIDENT EVIDENCE
MANUAL / BACKFILL / TEST EVIDENCE
RELEASE / SHADOW MILESTONE EVIDENCE
```

### P2.7 — Autonomous bounded maintenance integration — OPEN

P2.4 ve P2.6 retention kontratları kanıtlandıktan sonra bounded maintenance mevcut scheduler mimarisine en az yeni katmanla entegre edilir.

## 5. Güncel görev sırası

```text
P1    URA immutable raw holdings source snapshot     CLOSED
P2.1  macro.observations production baseline         CLOSED
P2.2  macro deterministic read/version contract      CLOSED
P2.3  macro dedup + future duplicate prevention      CLOSED
P2.4  macro retention policy + maintenance           NEXT / OPEN
P2.5  job_runs production baseline                   OPEN
P2.6  job_runs evidence-aware retention policy       OPEN
P2.7  autonomous bounded maintenance integration     OPEN
```

## 6. Model/LIVE sınırı

Bu veri yaşam döngüsü çalışmaları model davranışı tuning işi değildir.

```text
Threshold/weights/K1/K2/reset/sizing     UNCHANGED
Model version                            1.2.0
Mode                                     SHADOW
Realtime execution                       OFF
LIVE                                     NO-GO
```
