# Post-Shadow P2.1 — `macro.observations` Production Baseline

Tarih: 10 Eylül 2026  
Model version: `1.2.0`  
Mode: `SHADOW`  
LIVE: `NO-GO`  
Durum: `CLOSED / BASELINE VERIFIED`

## 1. Amaç

Bu adımın amacı `macro.observations` tablosundaki büyümenin gerçek nedenini production üzerinde read-only kanıtla sınıflandırmaktı.

Özellikle şu olasılıklar ayrıştırıldı:

1. aynı `(series_id, observation_date)` için farklı `realtime_start` ile oluşan logical version çoğalması,
2. gerçek FRED value revision geçmişi,
3. aynı current-view değerin tekrar tekrar yeni version olarak saklanması,
4. mevcut `ON CONFLICT ... DO UPDATE` davranışının PostgreSQL MVCC/update churn etkisi,
5. mevcut decision ve replay tüketicilerinin multi-version tarihlerden etkilenme kapsamı.

Bu adım hiçbir production satırını değiştirmedi veya silmedi.

Kullanılan read-only doğrulama:

```text
verification/verify_macro_observations_p2_1_baseline.sql
```

Kontrol zamanı:

```text
2026-09-10T00:07:39.193606+00:00
```

---

## 2. Production tablo hacmi

Baseline:

```text
total_rows                         295123
configured / present series        8 / 8
unique series+observation groups   11809
min observation_date              1997-10-31
max observation_date              2026-09-08
min fetched_at                     2026-07-30T12:11:13.533446+00:00
max fetched_at                     2026-09-09T21:15:35.943516+00:00
```

Physical size:

```text
heap                               25 MB
indexes                            30 MB
total                              55 MB
```

Tablonun production fetch geçmişi yalnız yaklaşık Temmuz sonu / Ağustos başından beri oluşmasına rağmen 295 bin logical row'a ulaşmış olması, mevcut current-view persistence davranışının 10 yıllık hedef için bounded olmadığını gösterir.

---

## 3. Logical version sınıflandırması

Production classification:

```text
ACTUAL VALUE REVISION
  observation-date groups          1505
  rows                             12004

IDENTICAL CURRENT-VIEW REFETCH VERSION
  observation-date groups          10280
  rows                             283095
  conservative redundant rows      272815

SINGLE OBSERVATION
  observation-date groups          24
  rows                             24
```

Conservative identical-refetch oranı:

```text
272815 / 295123 = 92.44%
```

Yani mevcut tablodaki satırların en az yaklaşık `%92.44`'ü, aynı observation date için aynı value korunmasına rağmen farklı `realtime_start` ile tekrar saklanan current-view version adaylarıdır.

Bu sayı yalnız tamamen aynı-value kalan date group'larını redundant sayar. İçinde gerçek revision bulunan bir group'ta aynı value'nun tekrarlandığı ara fetch'ler varsa bu baseline onları redundant saymamıştır. Bu nedenle `%92.44` alt sınır niteliğindedir; P2.3 safe-dedup adımında revision transition'ları korunarak daha ayrıntılı ölçüm yapılacaktır.

---

## 4. Seri bazında sonuç

### DFII10

```text
rows                              45983
observation dates                  1465
multi-version dates                1462
actual revision dates                 0
identical refetch dates            1462
max versions/date                    32
conservative redundant rows       44518
```

### DGS10

```text
rows                              45980
observation dates                  1465
multi-version dates                1463
actual revision dates                 0
identical refetch dates            1463
max versions/date                    32
conservative redundant rows       44515
```

### DGS2

```text
rows                              44545
observation dates                  1465
multi-version dates                1463
actual revision dates                 0
identical refetch dates            1463
max versions/date                    31
conservative redundant rows       43080
```

### DTWEXBGS

```text
rows                              11483
observation dates                  1464
multi-version dates                1454
actual revision dates                 1
identical refetch dates            1453
max versions/date                     8
conservative redundant rows       10014
```

### NASDAQCOM

```text
rows                              41826
observation dates                  1470
multi-version dates                1468
actual revision dates                 0
identical refetch dates            1468
max versions/date                    29
conservative redundant rows       40356
```

### SP500

```text
rows                              47603
observation dates                  1470
multi-version dates                1469
actual revision dates                 0
identical refetch dates            1469
max versions/date                    33
conservative redundant rows       46133
```

### STLFSI4

```text
rows                              12000
observation dates                  1506
multi-version dates                1504
actual revision dates              1504
identical-only refetch dates          0
max versions/date                     8
conservative redundant rows           0
```

### VIXCLS

```text
rows                              45703
observation dates                  1504
multi-version dates                1502
actual revision dates                 0
identical refetch dates            1502
max versions/date                    31
conservative redundant rows       44199
```

Ana ayrım çok nettir:

```text
DFII10/DGS10/DGS2/NASDAQCOM/SP500/VIXCLS
  -> observed production history içinde multi-version çoğalması neredeyse tamamen identical current-view refetch

DTWEXBGS
  -> çoğunluk identical refetch + en az 1 gerçek revision date

STLFSI4
  -> gerçek revision geçmişi yoğun; kör `(series_id, observation_date)` dedup yapılamaz
```

Bu sonuç önceki strict ALFRED/PIT çalışmasındaki gerçek STLFSI4 revision kanıtıyla tutarlıdır.

---

## 5. PostgreSQL update / MVCC churn

`pg_stat_user_tables` baseline:

```text
stats_reset                       2026-07-15T13:16:47.376507+00:00
n_live_tup                        295123
n_dead_tup                         42387
n_tup_ins                         328162
n_tup_upd                        1689283
n_tup_hot_upd                     229634
n_tup_del                              0
autovacuum_count                     64
last_autovacuum                   2026-09-08T09:15:36.562891+00:00
last_autoanalyze                  2026-09-09T21:15:21.133497+00:00
```

Mevcut persistence davranışı:

```sql
on conflict(series_id, observation_date, realtime_start) do update set
  value=excluded.value,
  realtime_end=excluded.realtime_end,
  fetched_at=now()
```

aynı unique key aynı gün dört scheduled macro fetch sırasında tekrar geldiğinde, value değişmese bile `fetched_at` güncelleyerek UPDATE üretir.

Dolayısıyla production sorunu iki katmanlıdır:

```text
A. Logical row growth
   farklı realtime_start -> yeni persistent version

B. Physical update churn
   aynı realtime_start -> value değişmese de DO UPDATE / fetched_at=now()
```

Yaklaşık 295 bin live row'a karşı 1.69 milyon update ve 64 autovacuum, ikinci problemin de gerçek olduğunu doğrular.

---

## 6. Index davranışı

Baseline:

```text
idx_macro_series_date
  size                    ~3.8 MB
  idx_scan                 2034

observations_pkey
  size                    ~14 MB
  idx_scan                    0

(series_id, observation_date, realtime_start) UNIQUE
  size                    ~12 MB
  idx_scan              2017584
  idx_tup_read           6379927
  idx_tup_fetch          5920239
```

Composite UNIQUE index'in çok yüksek kullanımının ana nedenlerinden biri repeated upsert conflict kontrolüdür. Bu index şu aşamada kaldırılmaz; mevcut persistence contract onu kullanmaktadır.

---

## 7. Decision provenance etkisi

Released `1.2.0` decision payload'larındaki macro `observation_dates` ile current table date-group'ları eşleştirildi.

```text
valid decision macro refs                         672
resolved refs                                      672
refs pointing to multi-version date               663
refs pointing to identical-refetch date           580
refs pointing to actual-revision date               83
```

Oranlar:

```text
multi-version ref ratio            98.66%
identical-refetch ref ratio        86.31%
actual-revision ref ratio          12.35%
```

Identical-refetch date'lerde version seçimi value açısından sonucu değiştirmez; bütün row'lar aynı value'yu taşır.

Ancak 83 persisted decision reference gerçek revision date-group'una bağlanır. Mevcut query yalnız:

```sql
order by observation_date desc
limit 1
```

dediği için aynı observation date içindeki version için deterministic tie-break kontratı tanımlı değildir.

Bu nedenle P2.2 yalnız storage optimizasyonu değildir. Production selection ve validation replay için explicit deterministic version contract gereklidir.

---

## 8. Decision kullanım aralığı

Released `1.2.0` persisted decision'larda her configured macro series için 84 referans vardır.

En eski kullanılan observation dates yaklaşık:

```text
DFII10      2026-07-28
DGS10       2026-07-28
DGS2        2026-07-28
DTWEXBGS    2026-07-24
NASDAQCOM   2026-07-29
SP500       2026-07-29
STLFSI4     2026-07-24
VIXCLS      2026-07-28
```

En yeni references 2026-09-04 / 2026-09-08 bandındadır.

Bu, production decisions'ın bugüne kadar kısa bir observation window kullandığını gösterir; fakat retention bununla sınırlandırılamaz, çünkü model validation/replay daha uzun geçmiş ister.

---

## 9. Validation boundary

BTC/ETH ortak market history:

```text
first_common_price_date            2019-09-25
last_common_price_date             2026-09-08
common_price_days                  2541
```

Dolayısıyla yalnız bugünkü decision provenance penceresine bakıp eski macro observation'ları silmek doğru değildir. Current-view replay ve strict PIT verification ayrımı P2.2/P2.4 boyunca korunmalıdır.

---

## 10. P2.1 kararları

Production evidence artık şu sonuçları destekler:

```text
Logical macro row growth                 VERIFIED
Identical current-view refetch growth    VERIFIED / dominant
Conservative redundant rows              272815 / 92.44%
True FRED value revisions                VERIFIED
STLFSI4 revision history                 VERIFIED / extensive
Blind UNIQUE(series,date)                REJECTED
Blind one-row-per-date cleanup            REJECTED
Conflict UPDATE churn                    VERIFIED
Physical dead-tuple pressure             VERIFIED
Decision refs on multi-version dates     VERIFIED / 663 of 672
Decision refs on true revisions          VERIFIED / 83 of 672
Immediate DELETE                         NOT AUTHORIZED / NOT PERFORMED
Immediate retention cutoff               NOT YET DEFINED
Model semantics changed                  NO
LIVE                                     NO-GO
```

P2.1 acceptance hedefi karşılanmıştır:

```text
P2.1 macro.observations production baseline   CLOSED / VERIFIED
```

---

## 11. Sonraki zorunlu adım — P2.2

Silme, constraint değişikliği veya persistence hardening'den önce deterministic read/version contract kapanmalıdır.

P2.2 şu soruları production evidence ile cevaplayacaktır:

1. Persisted decisions gerçek revision date'lerinde evaluation anında mevcut hangi version'ı kullanmış?
2. `latest current-view version available at evaluation time` kuralı persisted decision values ile eşleşiyor mu?
3. Current production read için tie-break sırası ne olmalı?
4. Historical current-view replay için canonical version ne olmalı?
5. Strict ALFRED/PIT verification production-current store'dan nasıl kesin ayrılmalı?
6. Revision group'ları içinde tekrar eden identical value version'ları varsa gerçek value transitions kaybedilmeden nasıl ayıklanmalı?

P2.2 kapanmadan P2.3 dedup veya future duplicate-prevention migration'ı uygulanmaz.
