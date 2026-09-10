# Post-Shadow P2.3 — macro.observations Implementation Validation

## Status

- Runtime duplicate prevention implementation: **VERIFIED / DEVELOPMENT**
- Deterministic latest-read contract: **VERIFIED / DEVELOPMENT**
- Deterministic macro history projection: **VERIFIED / DEVELOPMENT**
- Migration 0015 contract tests: **VERIFIED / DEVELOPMENT**
- Production runtime deployment: **OPEN**
- Production migration 0015 execution: **OPEN**
- Post-migration verification: **OPEN**
- Model semantics: **UNCHANGED**
- LIVE: **NO-GO**

## Implementation commits

1. `37963aec794f173c7ac6c3df3a03e1afb8b693b6` — `Macro veri akışında mükerrer sürüm üretimini engelle`
2. `0a62eb06dfdc915010f9175b2f2bf2f51adedf1b` — `Macro observations transition dedup migrationını ekle`

## Runtime contract

`Repository.upsert_macro()` artık current-view FRED verisini şu kontratla kalıcılaştırır:

1. `(series_id, observation_date)` için deterministic latest retained transition okunur.
2. Gelen value mevcut latest value ile aynıysa INSERT yapılmaz.
3. Aynı-value refetch mevcut satırı UPDATE etmez ve `fetched_at` değerini ileri taşımaz.
4. Value değişmişse yeni immutable transition row eklenir.
5. Aynı series writer'ları transaction advisory lock ile serialize edilir.
6. Runtime migration 0015 öncesi legacy unique constraint ile de çalışabilmek için generic `ON CONFLICT DO NOTHING` kullanır.

Bu davranış current-view `realtime_start/realtime_end` tarihinin değişmesini tek başına ekonomik revision olarak kabul etmez.

## Deterministic read contract

`get_latest_macro_observations()` explicit version sırası kullanır:

```text
observation_date DESC
realtime_start DESC
fetched_at DESC
id DESC
```

`get_macro_history()` her `(series_id, observation_date)` için aynı explicit version ordering ile yalnız latest current-view row döndürür. Böylece historical replay aynı observation date için implicit physical row order veya mükerrer current-view refetch satırlarına bağlı kalmaz.

## Migration 0015 contract

`0015_macro_observations_transition_dedup.sql`:

1. validated P2.3 classifier ile first row + every value transition'ı korur,
2. yalnız consecutive same-value current-view refetch row'larını siler,
3. `A -> B -> A` value reversion zincirini korur,
4. legacy `UNIQUE(series_id, observation_date, realtime_start)` constraint'ini kaldırır,
5. deterministic version index'ini ekler,
6. cleanup sonrası consecutive same-value row kalırsa exception ile transaction'ı rollback eder.

Migration production'a henüz uygulanmamıştır.

## Development validation evidence

Kullanıcı local repo:

- HEAD: `0a62eb0`
- focused tests:
  - `tests/test_macro_observations_persistence.py`
  - `tests/test_macro_observations_migration_contract.py`
  - result: **7 passed in 3.08s**
- full regression:
  - result: **87 passed in 8.88s**

Classification:

```text
Focused macro tests                  7/7 PASS
Full regression                      87/87 PASS
Runtime duplicate prevention         VERIFIED / DEVELOPMENT
Deterministic macro reads            VERIFIED / DEVELOPMENT
0015 migration contract              VERIFIED / DEVELOPMENT
Production runtime deploy            OPEN
Production 0015 migration            OPEN
Post-migration forward verification  OPEN
Model semantics                      UNCHANGED
LIVE                                 NO-GO
```

## Deployment order

Production güvenliği için sıra:

1. hardened runtime build + installer oluştur,
2. artifact SHA-256 al,
3. yeni runtime'ı deploy et ve Windows Service/binari identity doğrula,
4. ardından migration 0015'i production DB'ye uygula,
5. `verification/verify_macro_observations_p2_3_post_migration.sql` çalıştır,
6. natural macro scheduler koşusundan sonra aynı-value refetch'in yeni row üretmediğini forward verify et,
7. ancak bu kanıtlardan sonra P2.3 production implementation CLOSED yapılabilir.

Migration runtime'dan önce uygulanmamalıdır; hardened runtime her iki schema ile uyumludur ve güvenli geçiş sırası runtime-first olarak belirlenmiştir.
