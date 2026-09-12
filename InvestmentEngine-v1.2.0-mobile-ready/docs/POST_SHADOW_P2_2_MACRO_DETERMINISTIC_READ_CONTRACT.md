# Post-Shadow P2.2 — Macro Deterministic Read / Version Contract

Tarih: 10 Eylül 2026  
Model version: `1.2.0`  
Mode: `SHADOW`  
LIVE: `NO-GO`  
Durum: `CLOSED / CONTRACT VERIFIED WITH HISTORICAL LIMITATION`

## 1. Amaç

Bu adım `macro.observations` içindeki multi-version yapı için production karar ve historical replay okuma kontratını kanıtla belirlemek amacıyla yürütüldü.

P2.1 baseline şu iki problemi doğrulamıştı:

1. current-view FRED fetch'lerinin aynı value'yu farklı `realtime_start` günleriyle tekrar saklaması,
2. özellikle `STLFSI4` içinde gerçek value revision geçmişi bulunması.

P2.2 hiçbir production satırını değiştirmedi veya silmedi.

Kullanılan read-only doğrulama:

```text
verification/verify_macro_observations_p2_2_read_contract.sql
```

Kontrol zamanı:

```text
2026-09-10T00:13:47.471774+00:00
```

---

## 2. FRED current-view real-time alanlarının gerçek anlamı

Production collector `FredCollector.fetch_series()` FRED `fred/series/observations` endpoint'ine `realtime_start` ve `realtime_end` parametrelerini göndermez.

FRED resmi API kontratına göre bu iki parametre verilmezse varsayılan real-time period **today** olur.

Dolayısıyla production current-view çağrısında aynı observation/value her gün tekrar döndüğünde:

```text
realtime_start = fetch gününün FRED real-time tarihi
realtime_end   = fetch gününün FRED real-time tarihi
```

olabilir.

Bu nedenle `realtime_start` veya `realtime_end` değişimi tek başına ekonomik value revision kanıtı değildir. Aynı value korunurken yalnız current-view sorgu tarihi değişmiş olabilir.

Bu bulgu P2.1'deki identical current-view refetch sınıflandırmasını açıklamaktadır.

Kaynak:

```text
https://fred.stlouisfed.org/docs/api/fred/realtime_period.html
https://fred.stlouisfed.org/docs/api/fred/series_observations.html
```

---

## 3. Persisted decision reference sonucu

Released `1.2.0` persisted decision macro refs:

```text
total refs                                      672
multi-version refs                              663
actual revision refs                             83
refs with date + persisted value                672
persisted values absent from current table        0
```

Gerçek revision referanslarının tamamı `STLFSI4` üzerindedir.

```text
STLFSI4 total refs                               84
STLFSI4 multi-version refs                       83
STLFSI4 actual-revision refs                     83
```

---

## 4. Current latest geçmiş karar replay'i değildir

83 gerçek revision reference için:

```text
revision_refs_still_matching_current_latest       0
revision_refs_drifted_from_current_latest         83
```

Yani geçmiş kararın kullandığı persisted macro value bugün tablodaki en son revision value ile 83/83 durumda farklıdır.

Bu **beklenen revision davranışıdır**; veri kaybı kanıtı değildir.

Sonuç:

```text
Bugünkü current latest row
!=
geçmiş karar anındaki authoritative row
```

Dolayısıyla historical decision replay için bugünkü latest version kullanılamaz.

---

## 5. Evaluation-date candidate sonucu

Coarse day-level candidate:

```text
latest row where realtime_start <= decision_evaluated_at::date
```

sonucu:

```text
actual revision refs                             83
matches                                           77
mismatches                                         6
no day-level candidate                             0
```

6 mismatch gerçek model drift'i değildir.

Örnek pattern:

```text
decision evaluation       02:20 UTC civarı
same calendar-day FRED row realtime_start = o gün
ama row'un fetch zamanı    daha sonra (örn. 15:15 UTC)
```

Bu durumda yalnız `realtime_start <= evaluation DATE` filtresi, karar anında henüz DB'de bulunmayan aynı-gün future-intraday version'ı yanlışlıkla eligible sayar.

Dolayısıyla:

```text
realtime_start DATE <= evaluation DATE
```

tek başına authoritative availability kontratı değildir.

---

## 6. Strict timestamp reconstruction sonucu

Candidate:

```text
fetched_at <= decision_evaluated_at
```

sonucu:

```text
revision refs matching strict timestamp          10
revision refs strict timestamp mismatch           0
revision refs without timestamp candidate        73
```

Reconstruct edilebilen 10/10 reference persisted decision value ile tam eşleşmektedir.

Bu production davranışı için güçlü kanıttır:

```text
Authoritative live semantics
=
karar anında gerçekten persistence katmanında mevcut olan en güncel current-view information
```

Ancak 73 reference için exact historical candidate bulunamamasının nedeni mevcut persistence davranışıdır:

```sql
on conflict(series_id, observation_date, realtime_start) do update set
  value=excluded.value,
  realtime_end=excluded.realtime_end,
  fetched_at=now()
```

Aynı logical key sonraki scheduled fetch'lerde tekrar geldiğinde `fetched_at` ileri taşınmıştır. Böylece ilk-görülme timestamp'i korunmamıştır.

Baseline:

```text
total rows                                      295123
fetched_at date > realtime_start                274822
fetched_at date = realtime_start                 20301
max observed lag                                     8 days
```

Sonuç:

```text
Pre-hardening exact intraday first-seen provenance
NOT RECONSTRUCTIBLE
```

Bu geçmiş kararların value/date payload'ını geçersiz yapmaz; persisted decision içinde value ve observation date korunmuştur.

---

## 7. Persisted decision payload replay kanıtı

Önemli sonuç:

```text
persisted_values_not_found_in_current_table       0
```

Yani 672 decision macro reference'ın persisted value'ları mevcut production macro history içinde hâlâ temsil edilmektedir.

Buna karşılık:

```text
refs_whose_persisted_value_exists_in_multiple_versions 595
```

aynı value current-view refetch nedeniyle birden fazla version row'da bulunabilir.

Bu nedenle decision audit için version row ID'ye değil yalnız `observation_date`'e güvenmek yeterli değildir; P2.3 sonrası future provenance kontratı first-seen/version identity'yi deterministic hale getirmelidir.

---

## 8. Earliest-version sonucu neden canonical kontrat değildir

P2.2 ölçümünde 83/83 actual-revision reference, evaluation date'e kadar görülen en erken version value ile de eşleşmiştir.

Bu gözlem production dataset'in bugünkü karar penceresinde şu nedenle oluşmaktadır:

- kararlar çoğunlukla o anda en yeni observation date'i kullanmıştır,
- daha sonraki revision'lar eski observation date üzerinde sonradan oluşmuştur,
- persisted karar doğal olarak o observation'ın ilk current-view değerini taşımıştır.

Bu nedenle:

```text
"always choose earliest version"
```

production live read contract olarak kabul edilmez.

Doğru live semantik:

```text
latest information actually available at evaluation time
```

olmalıdır.

---

## 9. `realtime_end` transition kriteri reddedildi

P2.2 ilk transition-lineage denemesi row'u şu durumlarda keep saydı:

- first row,
- value changed,
- `realtime_end` changed.

Sonuç:

```text
total rows                              295123
transition-lineage keep rows            295123
consecutive identical repeat rows            0
```

Revision groups:

```text
revision groups                           1505
version rows in revision groups          12004
transition keep rows                     12004
consecutive identical repeats                0
```

Bu sonuç P2.1 ile çelişmez.

FRED current-view real-time period default olarak today olduğu için `realtime_end` sorgu günüyle değişebilir. Bu alanın değişmesi value revision anlamına gelmez.

Dolayısıyla P2.3 safe-dedup transition kriterinde:

```text
realtime_start/end değişti -> mutlaka revision
```

kuralı kullanılmayacaktır.

Revision lineage'in temel semantik olayı `value` transition olacaktır.

A→B→A gibi geri dönüşler korunmalıdır; yalnız ardışık aynı-value current-view kopyaları dedup adayı olabilir.

---

## 10. Production live read contract

P2.2 sonrası accepted contract:

### 10.1 Current production decision

Current runtime için authoritative macro observation:

1. `observation_date <= market as_of` filtresinden en yeni observation date,
2. o observation date için **karar evaluation anında DB'de gerçekten mevcut en yeni current-view version**,
3. deterministic tie-break ile seçilmelidir.

Future hardened storage'da `fetched_at`/first-seen semantiği immutable hale getirildikten sonra exact availability timestamp'i korunmalıdır.

Current runtime zaten yalnız o ana kadar ingest edilmiş row'ları görebildiği için explicit deterministic tie-break gelecekte şu ailede olmalıdır:

```text
observation_date DESC
source/current-view version order DESC
immutable first-seen timestamp DESC
id DESC
```

Exact kolon kontratı P2.3 persistence hardening ile uygulanacaktır.

### 10.2 Historical current-view replay

Production current-view store strict ALFRED history değildir.

Pre-hardening `fetched_at` mutable olduğu için geçmiş intraday availability tam reconstruct edilemez.

Bu nedenle current production table'dan yapılan historical replay:

```text
STRICT PIT
```

olarak etiketlenemez.

Deterministic current-view replay gerekiyorsa yalnız açıkça tanımlanmış canonical/first-observed transition history kullanılmalıdır ve historical limitation raporda korunmalıdır.

### 10.3 Strict historical/PIT validation

Strict historical macro doğrulaması production-current store'dan yapılmaz.

Mevcut ayrı yol korunur:

```text
FredCollector.fetch_realtime_history()
-> ALFRED / explicit realtime period
-> DB-write-free strict PIT verification
```

Bu ayrım değişmez.

---

## 11. P2.2 kararları

```text
Production current-view version ambiguity       VERIFIED
Actual decision refs on revision dates          VERIFIED / 83
Current-latest historical drift                 VERIFIED / 83 of 83
Day-level availability candidate                INSUFFICIENT / 6 mismatch
Strict timestamp candidate                      VERIFIED where reconstructible / 10 of 10
Strict timestamp historical coverage            INCOMPLETE / 73 not reconstructible
Persisted decision values retained              VERIFIED / 672 of 672
FRED realtime_start/end default today           VERIFIED
realtime_end as revision-transition signal      REJECTED
Blind earliest-version live read                REJECTED
Live authoritative semantic                     latest actually available at evaluation time
Pre-hardening exact intraday provenance         NOT RECONSTRUCTIBLE
Strict ALFRED/PIT path                          REMAINS SEPARATE
Model thresholds/weights/state changed          NO
LIVE                                            NO-GO
```

P2.2 acceptance hedefi karşılanmıştır:

```text
P2.2 macro deterministic read/version contract
CLOSED / VERIFIED WITH HISTORICAL LIMITATION
```

---

## 12. Sonraki zorunlu adım — P2.3

P2.3 yalnız bu kontrata göre safe-dedup ve future duplicate prevention tasarlayacaktır.

Önce read-only dry-run ile:

1. her `(series_id, observation_date)` version zinciri `realtime_start, id` sırasına konacak,
2. ilk row korunacak,
3. `value` önceki retained/current transition value'dan farklıysa korunacak,
4. A→B→A gibi value geri dönüşleri ayrı transition olarak korunacak,
5. yalnız ardışık same-value current-view refetch row'ları delete candidate sayılacak,
6. bütün persisted decision `(series, observation_date, value)` referanslarının retained set içinde hâlâ bulunması doğrulanacak,
7. current latest value parity before/after candidate cleanup doğrulanacak,
8. replay/input parity için deterministic canonical contract test edilecek.

Dry-run parity kapanmadan production DELETE uygulanmaz.

Future ingest hardening ayrıca:

- aynı current-view value tekrarında yeni logical version üretmemeli,
- aynı unique key tekrarında yalnız `fetched_at=now()` churn üretmemeli,
- yeni value revision geldiğinde revision transition'ı korumalı,
- post-hardening first-seen timestamp'ini immutable tutmalı,
- strict ALFRED/PIT verification yoluna dokunmamalıdır.
