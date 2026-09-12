# Post-Shadow P2.3 — macro.observations Safe Dedup Dry-Run Closure

## Status

- P2.3 safe dedup dry-run: **CLOSED / VERIFIED**
- Production DELETE: **NOT PERFORMED**
- Runtime persistence prevention: **OPEN**
- Production cleanup execution: **OPEN**
- Model semantics: **UNCHANGED**
- LIVE: **NO-GO**

## Scope

Bu adım `macro.observations` tablosunda P2.1/P2.2 ile doğrulanan current-view tekrarlarının güvenli biçimde ayıklanıp ayıklanamayacağını yalnız READ-ONLY dry-run ile ölçer.

Accepted P2.2 contract:

1. Production `FredCollector.fetch_series()` current-view FRED endpoint kullanır.
2. `realtime_start/realtime_end` current-view query real-time tarihini de taşıdığı için tek başına ekonomik revision kimliği değildir.
3. Revision lineage, `(series_id, observation_date)` içinde `realtime_start,id` sırasındaki **value transition zinciri** olarak korunmalıdır.
4. `A -> B -> A` gibi value reversion'lar gerçek lineage parçasıdır ve korunmalıdır.
5. Yalnız previous row ile aynı value taşıyan ardışık current-view refetch row'ları dedup adayıdır.

## Production evidence

Dry-run checked_at:

- `2026-09-10T00:19:29.992445+00:00`

Global sonuç:

| Metric | Result |
|---|---:|
| total_rows | 295,123 |
| observation_date_groups | 11,809 |
| retained_rows | 20,433 |
| candidate_delete_rows | 274,690 |
| candidate_delete_pct | 93.0764% |
| revision_groups | 1,505 |
| revision_groups_with_value_reversion | 57 |
| groups_without_retained_row | 0 |
| group_latest_value_mismatches | 0 |
| series_latest_value_date_mismatches | 0 |
| decision_refs_checked | 672 |
| decision_refs_present_before | 672 |
| decision_refs_preserved_after | 672 |
| decision_refs_lost_by_candidate_cleanup | 0 |
| safe_dedup_contract_complete | true |

## Series results

| series_id | total_rows | retained_rows | candidate_delete_rows | revision_groups |
|---|---:|---:|---:|---:|
| DFII10 | 45,983 | 1,465 | 44,518 | 0 |
| DGS10 | 45,980 | 1,465 | 44,515 | 0 |
| DGS2 | 44,545 | 1,465 | 43,080 | 0 |
| DTWEXBGS | 11,483 | 1,465 | 10,018 | 1 |
| NASDAQCOM | 41,826 | 1,470 | 40,356 | 0 |
| SP500 | 47,603 | 1,470 | 46,133 | 0 |
| STLFSI4 | 12,000 | 10,129 | 1,871 | 1,504 |
| VIXCLS | 45,703 | 1,504 | 44,199 | 0 |

## Revision lineage safety

Revision groups:

- version rows: 12,004
- retained transition rows: 10,129
- candidate duplicate rows inside revision groups: 1,875
- groups with value reversion: 57
- maximum versions in a group: 8
- maximum retained transitions in a group: 7

Bu sonuç `distinct value` bazlı tekilleştirmenin güvenli olmadığını doğrular. Aynı value daha sonraki bir revision zincirinde tekrar ortaya çıkabilir. Bu nedenle retention kuralı global distinct value değil, ardışık value transition'dır.

Örnek korunması gereken zincir:

```text
A -> A -> B -> B -> A
KEEP  DROP KEEP DROP KEEP
```

## Decision parity

Tüm persisted model `1.2.0` macro referansları kontrol edildi:

- checked: 672
- before cleanup present: 672
- after candidate cleanup preserved: 672
- lost: 0

Bu dry-run kapsamında candidate setin mevcut persisted decision series/date/value replay kanıtını kaybetmediği doğrulandı.

## Latest-value parity

Dry-run retained set sonrasında:

- hiçbir `(series_id, observation_date)` grubunun latest value'su değişmiyor,
- hiçbir serinin latest observation date/value'su değişmiyor.

Not: aynı value korunurken retained row'un `realtime_start` değeri daha eski olabilir. P2.2 kontratına göre current-view `realtime_start` tek başına ekonomik revision identity değildir; scoring semantiğinde esas olan observation date/value'dur. Future persistence tasarımında first-seen / last-seen metadata ayrıca ele alınmalıdır.

## Candidate age distribution

- total candidates: 274,690
- fetched older than 7d: 218,190
- fetched older than 30d: 63,484
- observation older than 1y: 230,026
- observation older than 3y: 134,922
- observation older than 5y: 39,870
- observation older than 10y: 1,182

Bu dağılım cleanup'ın yalnız yaş tabanlı retention ile çözülmemesi gerektiğini gösterir. Yeni veya eski olmasına bakılmaksızın value-transition lineage korunmalıdır.

## Accepted implementation contract for next substep

P2.3 implementation şu kurallara uymalıdır:

1. Production cleanup, dry-run ile aynı deterministic classifier'ı kullanmalı: `(series_id, observation_date)` içinde `realtime_start,id` sırası; first row + every value transition retained.
2. `A -> B -> A` reversion korunmalı.
3. DELETE öncesinde decision reference parity ve latest value/date parity tekrar doğrulanmalı.
4. Cleanup bounded/transactional olmalı; başarısızlıkta rollback mümkün olmalı.
5. Future current-view persistence aynı value yeniden geldiğinde yeni logical version üretmemeli.
6. Existing row'un historical first-seen `fetched_at` değeri tekrar tekrar mutation'a uğramamalı.
7. Gerekirse `last_seen_at` gibi ayrı metadata first-seen semantiğini bozmadan tutulmalı.
8. Deterministic readers aynı observation date içinde explicit version ordering kullanmalı; implicit physical row order kullanılmamalı.
9. Strict ALFRED/PIT validation yolu production current-view storage'dan ayrı kalmalı.
10. Threshold, weight, factor formula, K1/K2, reset, sizing, scheduler cadence veya LIVE/SHADOW semantiği değişmemeli.

## Closure classification

```text
P2.3 safe dedup dry-run              VERIFIED / CLOSED
Safe candidate rows                  274690 / 93.0764%
Retained rows                        20433
Value-reversion groups               57 / PRESERVED
Decision refs lost                   0
Group latest mismatches              0
Series latest mismatches             0
Safe dedup contract                  true
Production cleanup                   OPEN
Future duplicate prevention          OPEN
Model semantics                      UNCHANGED
LIVE                                 NO-GO
```
