# Post-Shadow P2.4 — `macro.observations` Retention / Maintenance Production Baseline

Tarih: 10 Eylül 2026  
Kontrol zamanı: `2026-09-10T13:01:38.823941+00:00`  
Model version: `1.2.0`  
Mode: `SHADOW`  
Shadow readiness: `READY`  
LIVE: `NO-GO`  
Durum: `READ-ONLY BASELINE VERIFIED / RETENTION DELETE NOT JUSTIFIED`

## 1. Amaç

Bu adım P2.3 ile temizlenip hardened writer ile korumaya alınan `macro.observations` tablosunda artık gerçekten bir retention/delete ihtiyacı olup olmadığını production üzerinde read-only kanıtla ölçer.

Bu baseline hiçbir production satırını değiştirmedi veya silmedi. Şunlar yapılmadı:

- `DELETE`
- `UPDATE`
- `INSERT`
- DDL / migration
- `VACUUM FULL`
- scheduler değişikliği
- model threshold/weight/K1/K2/reset/sizing değişikliği

Kullanılan sorgu:

```text
verification/verify_macro_observations_p2_4_retention_baseline.sql
```

Baseline'ın temel güvenlik ilkesi:

```text
consumer tarafından doğrudan seçilmiyor
!=
safe-to-delete
```

Çünkü legitimate revision/value-transition lineage, future validation coverage ve source/revision audit ayrı koruma nedenleridir.

---

## 2. P2.3 lineage kontratı production'da korunuyor

Production sonucu:

```text
retained_rows                         20,435
observation_date_groups               11,811
base_observation_rows                 11,811
legitimate_value_transition_rows       8,624
same_value_repeat_rows                     0
rows_missing_fetched_at                    0
rows_missing_realtime_start                0
p2_3_same_value_contract_intact         true
```

Sonuç:

- P2.3 sonrası duplicate same-value sınıfı tekrar oluşmamış.
- Mevcut 20,435 satır artık aynı-value refetch şişkinliği değildir.
- 8,624 satır gerçek value-transition lineage parçasıdır.
- Bu nedenle P2.4, P2.3 duplicate cleanup'ını tekrar etmeye çalışmamalıdır.

---

## 3. Seri bazında retained history

| Series | Rows | Observation dates | Revision groups | Value transitions | Reversions | Oldest observation |
|---|---:|---:|---:|---:|---:|---|
| DFII10 | 1,465 | 1,465 | 0 | 0 | 0 | 2020-10-28 |
| DGS10 | 1,465 | 1,465 | 0 | 0 | 0 | 2020-10-28 |
| DGS2 | 1,465 | 1,465 | 0 | 0 | 0 | 2020-10-28 |
| DTWEXBGS | 1,465 | 1,464 | 1 | 1 | 0 | 2020-10-26 |
| NASDAQCOM | 1,471 | 1,471 | 0 | 0 | 0 | 2020-10-29 |
| SP500 | 1,471 | 1,471 | 0 | 0 | 0 | 2020-10-29 |
| STLFSI4 | 10,129 | 1,506 | 1,504 | 8,623 | 57 | 1997-10-31 |
| VIXCLS | 1,504 | 1,504 | 0 | 0 | 0 | 2020-10-28 |

Ana sonuç:

```text
STLFSI4 retained history
=
gerçek revision/value-transition lineage'in baskın kaynağı
```

STLFSI4 tek başına 8,623 transition row ve 57 value-reversion group taşır.

---

## 4. Yaş tek başına retention kriteri olamaz

Observation-age dağılımında özellikle STLFSI4:

```text
0-90d       65 rows      / 52 transitions
91d-1y     254 rows      / 215 transitions
1-3y       676 rows      / 572 transitions
3-5y       699 rows      / 594 transitions
5-10y    1,763 rows      / 1,503 transitions
>10y      6,672 rows      / 5,687 transitions
```

Kritik sonuç:

```text
>10 yıllık satırların 5,687 adedi legitimate value transition'dır.
```

Dolayısıyla aşağıdaki politikalar production evidence ile reddedilir:

```text
observation_date < now()-10y -> DELETE
observation_date < now()-5y  -> DELETE
consumer seçmiyor            -> DELETE
```

Eski observation tarihi, semantik olarak gereksiz row anlamına gelmez.

---

## 5. Released decision evidence

Model `1.2.0` persisted decision macro references:

```text
refs_checked                        680
refs_preserved                      680
refs_lost                             0
distinct_protected_rows             192
refs_with_multiple_matching_rows      0
```

Her configured series için 85 persisted reference vardır.

En eski decision observation dates yaklaşık:

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

Decision evidence eksiksizdir; ancak retention yalnız bu kısa pencereye indirgenemez.

---

## 6. Current model replay dependency

Current deterministic replay kontratı:

```text
BTC/ETH common sessions
-> first evaluation at session 1120
-> each evaluation date için latest macro row <= evaluation date
```

Production baseline:

```text
common_price_sessions                2,542
first_common_price_date         2019-09-25
last_common_price_date          2026-09-09
replay_evaluation_dates               1,423
first_replay_evaluation_date    2022-10-18
distinct_replay_rows                  7,048
unresolved_series_evaluations             0
```

Seri bazında current replay'in kullandığı distinct macro rows:

| Series | Distinct rows selected | First selected observation | Last selected observation |
|---|---:|---|---|
| DFII10 | 972 | 2022-10-18 | 2026-09-08 |
| DGS10 | 972 | 2022-10-18 | 2026-09-08 |
| DGS2 | 972 | 2022-10-18 | 2026-09-08 |
| DTWEXBGS | 972 | 2022-10-18 | 2026-09-04 |
| NASDAQCOM | 976 | 2022-10-18 | 2026-09-09 |
| SP500 | 976 | 2022-10-18 | 2026-09-09 |
| STLFSI4 | 204 | 2022-10-14 | 2026-09-04 |
| VIXCLS | 1,004 | 2022-10-18 | 2026-09-08 |

Recorded PIT core replay runs:

```text
runs                              8
earliest recorded replay start   2022-10-18
latest recorded replay end        2026-09-02
```

Current replay consumer direct dependency önemli bir protection setidir; fakat tek retention kriteri değildir.

---

## 7. Consumer-reference classification

Production classification:

```text
total_retained_rows                    20,435
directly_referenced_rows                7,054
consumer_unreferenced_rows             13,381
unreferenced_base_rows                  4,961
unreferenced_value_transition_rows      8,420
unreferenced_same_value_repeat_rows         0
unreferenced_observation_older_than_1y 13,119
unreferenced_observation_older_than_3y 12,547
unreferenced_observation_older_than_5y  9,958
unreferenced_observation_older_than_10y 6,672
```

Bu tablo P2.4'ün en önemli sonucudur.

13,381 consumer-unreferenced row'un 8,420'si genuine value-transition lineage parçasıdır.

Dolayısıyla:

```text
consumer_unreferenced_rows
```

bir DELETE candidate set değildir.

Bu sınıf yalnız observability/classification amacıyla kullanılabilir.

---

## 8. Strict FRED/ALFRED audit sınırı

Production `macro.observations` store şu semantiğe sahiptir:

```text
FRED current-view value-transition history after P2.3
```

`realtime_start/realtime_end` tek başına ekonomik revision identity değildir.

Strict historical PIT doğrulaması ise ayrı, DB-write-free yol üzerinden yapılır:

```text
FredCollector.fetch_realtime_history()
-> explicit FRED/ALFRED real-time period
-> verification only
-> production macro table'a write yok
```

Bu ayrım şu retention sonucunu doğurur:

- current production store strict ALFRED archive değildir,
- fakat production'da gerçekten gözlenmiş current-view value transitions audit/revision lineage kanıtıdır,
- bu lineage yalnız current replay bugün doğrudan seçmiyor diye silinmemelidir.

---

## 9. Physical maintenance baseline

Table statistics:

```text
n_live_tup               20,435
n_dead_tup                    0
n_tup_ins               328,164
n_tup_upd             1,689,283
n_tup_del               274,690
autovacuum_count             65
autoanalyze_count           122
last_autovacuum    2026-09-10T00:54:26.559278+00:00
last_autoanalyze   2026-09-10T00:54:26.645969+00:00
n_ins_since_vacuum             2
n_mod_since_analyze             2
```

Relation sizes:

```text
heap       25 MB
indexes    32 MB
total      57 MB
```

Indexes:

```text
idx_macro_series_date                 ~3.8 MB
idx_macro_series_observation_version   14 MB
observations_pkey                      14 MB
```

Schema contract:

```text
legacy unique constraint         absent
deterministic version index      present
```

### Physical interpretation

P2.3 cleanup 274,690 row silmiştir. PostgreSQL normal VACUUM/autovacuum heap dosyasını işletim sistemine küçültmek zorunda değildir; boş alanı relation içinde yeniden kullanım için hazırlar.

Production evidence:

```text
n_dead_tup = 0
autovacuum cleanup sonrası çalışmış
n_ins_since_vacuum = 2
n_mod_since_analyze = 2
```

Bu nedenle mevcut durumda dead-tuple baskısı yoktur.

`VACUUM FULL` relation'ı fiziksel olarak rewrite ederek disk alanı geri kazandırabilir; ancak tabloyu daha agresif kilitleyen/rewrite eden bir operasyondur. Mevcut relation yalnız 57 MB olduğu ve dead tuple baskısı bulunmadığı için operasyonel fayda/risk oranı bunu haklı çıkarmamaktadır.

Sonuç:

```text
VACUUM FULL              NOT JUSTIFIED
manual VACUUM required   NOT PROVEN
normal autovacuum        SUFFICIENT CURRENTLY
```

---

## 10. Retention candidate değerlendirmesi

P2.4 baseline'da güvenle silinebileceği kanıtlanmış logical row class aranmıştır.

Sonuç:

```text
SAME_VALUE_REPEAT                  0
LEGITIMATE VALUE TRANSITION    8,624
BASE OBSERVATION              11,811
```

P2.3 zaten semantik olarak redundant same-value row'ları temizlemiştir ve writer bunların tekrar üretimini engellemektedir.

Kalan satırlar için production evidence şu anda herhangi bir row class'ı güvenle DELETE etmeyi kanıtlamamaktadır.

Özellikle:

- old-age rows içinde gerçek transitions yoğun,
- consumer-unreferenced rows içinde gerçek transitions yoğun,
- replay'in doğrudan seçmediği eski base rows future validation/history coverage değerine sahip olabilir,
- strict source/revision audit lineage korunmalıdır,
- 10 yıllık proje ufku boyunca geçmiş validation coverage'ı küçültmek için gerekçe yoktur.

Bu nedenle accepted retention sonucu:

```text
SAFE LOGICAL DELETE CLASS            NONE PROVEN
BLIND AGE CUTOFF                     REJECTED
CONSUMER-UNREFERENCED DELETE         REJECTED
VALUE-TRANSITION PRUNING             REJECTED
CURRENT BASE-ROW PRUNING             NOT JUSTIFIED
```

---

## 11. P2.4 policy yönü

Mevcut production evidence ile en güvenli politika:

```text
1. P2.3 retained base observations korunur.
2. Tüm legitimate value transitions/reversions korunur.
3. Same-value refetch writer seviyesinde persist edilmez.
4. Age-based logical DELETE uygulanmaz.
5. Decision/replay evidence ayrıca protected kalır.
6. Strict ALFRED/PIT verification production-current store'dan ayrı tutulur.
7. Normal PostgreSQL autovacuum/autoanalyze fiziksel maintenance için şimdilik yeterlidir.
8. VACUUM FULL uygulanmaz.
9. Table/index growth düzenli olarak ölçülür; retention ancak yeni kanıt oluşursa yeniden değerlendirilir.
```

Bu politika storage'ın sınırsız duplicate refetch ile büyümesini P2.3 writer contract sayesinde zaten kesmiştir. P2.4'te ayrıca historical evidence silmek şu an gereksiz risk yaratır.

---

## 12. P2.4 baseline sonucu

```text
READ-ONLY baseline                    VERIFIED
P2.3 same-value contract              INTACT
retained rows                         20,435
legitimate transitions                 8,624
same-value repeats                         0
released decision refs                680/680 preserved
current replay unresolved             0
consumer-unreferenced rows            13,381
consumer-unreferenced transitions      8,420
>10y retained rows                     6,672
>10y transition rows                   5,687
n_dead_tup                                 0
relation total size                    57 MB
VACUUM FULL                            NOT JUSTIFIED
safe logical delete class              NONE PROVEN
production mutation                    NONE
model semantics                        UNCHANGED
LIVE                                   NO-GO
```

P2.4 read-only production baseline kabul hedefi karşılanmıştır.

P2.4'ün sonraki alt adımı, bu baseline üzerinden retention policy/maintenance kontratını açıkça kapatmak ve gerekiyorsa yalnız observability/bounded maintenance tasarımını tanımlamaktır. Production DELETE veya `VACUUM FULL` için bu baseline yetki üretmemektedir.
