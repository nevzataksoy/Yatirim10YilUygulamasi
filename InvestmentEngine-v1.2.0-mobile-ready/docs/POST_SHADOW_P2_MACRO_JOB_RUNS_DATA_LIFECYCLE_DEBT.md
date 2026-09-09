# Post-Shadow P2 — Macro Observations ve Job Runs Veri Yaşam Döngüsü Görev Borcu

Tarih: 09 Eylül 2026  
Durum: `OPEN (Açık)`  
Model version: `1.2.0`  
Mode: `SHADOW`  
LIVE: `NO-GO`

## 1. Amaç ve kapsam

Bu görev borcu iki büyüyen production tablosunun veri yaşam döngüsünü kanıtla yönetmek içindir:

1. `macro.observations`
2. `system.job_runs`

Amaç tabloyu yalnız küçültmek değildir. Önce hangi satırların karar, validation, readiness ve operasyonel RCA tarafından gerçekten kullanıldığını ayırmak; sonra güvenli dedup/retention politikasını uygulamaktır.

Bu başlık FRED strict-PIT/ALFRED doğrulamasından ayrıdır. Strict-PIT verification sub-stage daha önce kapanmıştır. Buradaki konu released production collector'ın current-view verisini nasıl sakladığı ve production telemetry geçmişinin ne kadar tutulması gerektiğidir.

Bu görev threshold, factor weight, K1/K2, reset, sizing, scheduler cadence veya SHADOW/LIVE davranışını otomatik değiştirmez.

---

## 2. `macro.observations` — mevcut üretici akışları

### 2.1 Production collector

`FredCollector.fetch_series(series_id, limit=1500)` FRED current real-time view'dan her seri için en fazla son 1500 observation'ı çeker.

Production path strict ALFRED history çekmez. `fetch_realtime_history()` yalnız verification/PIT çalışmaları içindir ve DB'ye yazmaz.

### 2.2 Scheduler üretimi

`macro_job` scheduler contract'ta günde dört kez çalışır:

```text
00:15
06:15
12:15
18:15
Europe/Istanbul
```

Her çalışmada configured FRED serilerinin tamamı için:

```text
fetch_series(series_id)
 -> upsert_macro(...)
```

akışı çalışır.

Ayrıca `weekly_job` kendi içinde tekrar `macro_job()` çağırır. Bu nedenle Cumartesi haftalık bakım akışı normal dört günlük macro schedule'ına ilave bir macro fetch/persistence çalıştırabilir.

### 2.3 Mevcut persistence anahtarı

`macro.observations` schema:

```text
id
series_id
observation_date
value
realtime_start
realtime_end
fetched_at
UNIQUE(series_id, observation_date, realtime_start)
```

Repository persistence:

```sql
on conflict(series_id,observation_date,realtime_start) do update set
  value=excluded.value,
  realtime_end=excluded.realtime_end,
  fetched_at=now()
```

Bu yapı aynı `(series_id, observation_date, realtime_start)` satırını tekrar üretmez; ancak `realtime_start` farklıysa aynı observation date/value için ayrı satır tutulabilir.

FRED current-view çağrılarının farklı fetch günlerinde aynı observation için farklı `realtime_start` üretip üretmediği production DB üzerinde nicelleştirilmeden bu satırlar "mükerrer" diye silinmez.

---

## 3. `macro.observations` — mevcut tüketici akışları

### 3.1 Güncel karar akışı

`get_latest_macro_observations(series_ids, as_of)` her seri için:

```sql
where observation_date <= as_of
order by observation_date desc
limit 1
```

kullanır.

Bu sonuç:

- `daily_crypto_job` -> `score_macro()` -> ETH/BTC decision,
- `daily_ura_job` -> `score_macro()` -> URA/USD decision,
- `macro_job` health/freshness hesabı

için kullanılır.

Önemli görev borcu: sorgu aynı `observation_date` için birden çok row varsa `realtime_start`, `fetched_at` veya `id` ile explicit tie-break yapmaz. Production duplicate/version yapısı ölçüldükten sonra deterministic selection kontratı belirlenmelidir.

### 3.2 Historical validation/replay

`get_macro_history()` şu anda requested series için `macro.observations` satırlarının tamamını döndürür:

```sql
order by series_id, observation_date
```

`model_validation_job()` bunu `replay_ethbtc_core()` içine verir.

Replay tarafında `_prepare_macro_history()` satırları yalnız `observation_date` ile sıralar; `_macro_asof()` aynı tarihte son sırada kalan satırı seçer. Aynı observation date için birden fazla production-current version bulunuyorsa seçim explicit bir version kontratına bağlı değildir.

Bu nedenle `macro.observations` şişmesi yalnız storage problemi değildir; mükerrer/version semantiği deterministic replay davranışını da etkileyebilir.

---

## 4. `macro.observations` için P2 görev sırası

### P2.1 — Production baseline / duplicate sınıflandırması

İlk iş read-only SQL ile şunları ölçmektir:

- tablo toplam row ve physical size,
- series bazında row sayıları,
- `(series_id, observation_date)` başına version sayısı,
- aynı `(series_id, observation_date, value)` için kaç farklı `realtime_start` bulunduğu,
- aynı observation date içinde gerçekten farklı `value` taşıyan revision sayısı,
- exact/current duplicate adaylarının yaş dağılımı,
- latest-decision makro observation_date kapsamı,
- validation/replay'in gerçekten ihtiyaç duyduğu en eski tarih.

Classification en az şu ayrımı yapmalıdır:

```text
ACTUAL VALUE REVISION
IDENTICAL CURRENT-VIEW REFETCH VERSION
SINGLE OBSERVATION
UNRESOLVED
```

### P2.2 — Deterministic production/validation read contract

Silme veya UNIQUE migration'dan önce şu sorular kapanmalıdır:

- current decision için hangi version authoritative?
- released current-view collector için `realtime_start` semantiği korunmalı mı?
- historical validation current production table'dan hangi canonical row'u okumalı?
- strict ALFRED verification ile production-current storage kesin olarak nasıl ayrılmalı?

`(series_id, observation_date)` üzerine doğrudan UNIQUE eklenmez. Gerçek FRED revision kanıtı daha önce bulunduğu için kör dedup revision bilgisini silebilir.

### P2.3 — Safe dedup / future duplicate prevention

Baseline sonrası yalnız semantik olarak redundant olduğu kanıtlanan satırlar için:

- dry-run candidate query,
- korunacak canonical/version kuralı,
- migration öncesi/sonrası row count + replay parity kontrolü,
- future ingest'te aynı gereksiz version'ın yeniden oluşmasını engelleyen idempotent persistence kontratı

tasarlanır.

### P2.4 — Retention

Retention yalnız decision/validation açısından artık gerekli olmayan satırlara uygulanır.

Minimum koruma kontratı belirlenmeden gün sayısı seçilmez. Özellikle:

- 10 yıllık yatırım/validation hedefi,
- model replay ihtiyaçları,
- strict source/revision audit gereksinimi,
- released decision payload'ındaki macro provenance

birlikte değerlendirilir.

---

## 5. `system.job_runs` — mevcut üretici/tüketici akışı

### 5.1 Üretim

`Repository.log_job()` her job sonucu için yeni satır INSERT eder. Unique/idempotency anahtarı yoktur; bu tablo append-only telemetry gibi davranır.

Scheduler ve manuel/verification akışları zaman içinde çok sayıda `OK`, `DEGRADED`, `ERROR`, `SKIPPED` veya test run kaydı oluşturabilir.

### 5.2 Runtime tüketimi

Released runtime'ın sürekli kullandığı historical pencere sınırlıdır:

`shadow_readiness_stats()`:

- son **7 günlük** `job_runs` kayıtlarından success rate hesaplar,
- `realtime_test` için latest successful row'u bulur.

`get_latest_job_run(job_name)` de yalnız en yeni satırı ister.

Bununla birlikte eski `job_runs` kayıtları Post-Shadow/P0 RCA çalışmalarında gerçek historical kanıt olarak kullanılmıştır. Örneğin isolated scheduler failures ve pool-timeout incident ailesi eski run ID'lerinden doğrulanmıştır.

Bu nedenle "runtime son 7 günü kullanıyor, 7 günden eski her şeyi sil" yaklaşımı kabul edilmez.

---

## 6. `system.job_runs` için P2 görev sırası

### P2.5 — Production baseline ve evidence sınıflandırması

Read-only baseline ile:

- toplam row/physical size,
- job_name + status bazında sayılar,
- günlük/aylık growth,
- en eski/en yeni kayıt,
- ERROR/DEGRADED/OK/SKIPPED dağılımı,
- manuel/test/backfill run oranı,
- son 7/30/90 gün dışındaki row sayıları,
- details/message payload boyut dağılımı

ölçülür.

### P2.6 — Retention policy

Kayıtlar tek retention sınıfına alınmaz. Tasarım en az şu kategorileri ayırmalıdır:

```text
ROUTINE SUCCESS TELEMETRY
ROUTINE DEGRADED TELEMETRY
ERROR / INCIDENT EVIDENCE
MANUAL / BACKFILL / TEST EVIDENCE
RELEASE / SHADOW MILESTONE EVIDENCE
```

Routine telemetry için daha kısa retention mümkünken ERROR/incident ve önemli validation/deploy dönemleri daha uzun veya kalıcı tutulabilir.

Gerekirse eski telemetry silinmeden önce günlük/aylık aggregate tabloya özetlenebilir; bunun gerçekten gerekli olup olmadığı baseline sonrası belirlenir. Yeni katman yalnız kanıtla ihtiyaç varsa eklenir.

### P2.7 — Otonom maintenance

Ayrı ve gereksiz bir scheduler job eklemek ilk tercih değildir.

Mevcut akıştan kopmamak için aday tasarım:

```text
monthly_audit_job
  -> model audit/validation
  -> bounded data-lifecycle maintenance
```

veya kanıtlanan ihtiyaç daha sık ise mevcut `weekly_job` içinde sınırlı bakım adımıdır.

Nihai cadence, retention window ve batch boyutu production row-growth baseline'ı görülmeden seçilmez.

Maintenance şu güvenlik özelliklerine sahip olmalıdır:

- küçük bounded batch'ler,
- explicit cutoff,
- protected evidence predicate,
- dry-run/count mode,
- silinen row sayısı audit/log özeti,
- transaction sınırı,
- failure halinde model karar akışını bozmama,
- threshold/model parametrelerine dokunmama.

---

## 7. Görev borcu öncelik sırası

Mevcut Post-Shadow akışını bozmadan sıra:

```text
P1  URA immutable raw holdings source snapshot
    -> code/test
    -> migration
    -> deploy
    -> natural forward verification
    -> CLOSE

P2.1 macro.observations production baseline
P2.2 macro deterministic read/version contract
P2.3 macro safe dedup + future duplicate prevention
P2.4 macro retention policy + maintenance
P2.5 job_runs production baseline
P2.6 job_runs evidence-aware retention policy
P2.7 autonomous bounded maintenance integration
```

`macro.observations` daha önce açık bırakılmış FRED current/revision/dedup/retention P2 borcunun somutlaştırılmış devamıdır. `job_runs` retention ise bu belgeyle yeni ve açık bir P2 görev borcu olarak kaydedilmiştir.

---

## 8. Şu anda yapılmayanlar

Bu görev borcunun kaydı sırasında:

- production satırı silinmez,
- dedup migration uygulanmaz,
- retention günü belirlenmez,
- `macro.observations` constraint'i değiştirilmez,
- `job_runs` schema'sı değiştirilmez,
- yeni scheduler job eklenmez,
- threshold/weight/state/sizing değiştirilmez,
- LIVE açılmaz.

Önce production read-only baseline ve dry-run evidence gerekir.

Final mevcut durum:

```text
macro.observations duplicate semantics analysis   OPEN
macro deterministic consumer contract             OPEN
macro dedup / duplicate prevention                OPEN
macro retention                                   OPEN
job_runs retention baseline                       OPEN
job_runs evidence-aware cleanup                   OPEN
autonomous maintenance                            OPEN
model semantics changed                           NO
LIVE                                              NO-GO
```
