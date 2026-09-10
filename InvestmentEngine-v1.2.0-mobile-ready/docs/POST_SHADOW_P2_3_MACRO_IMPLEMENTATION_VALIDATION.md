# Post-Shadow P2.3 — macro.observations Implementation Validation

## Status

- Runtime duplicate prevention implementation: **VERIFIED / DEVELOPMENT**
- Deterministic latest-read contract: **VERIFIED / DEVELOPMENT**
- Deterministic macro history projection: **VERIFIED / DEVELOPMENT**
- Migration 0015 contract tests: **VERIFIED / DEVELOPMENT**
- Hardened runtime build: **VERIFIED**
- Installer build: **VERIFIED**
- Artifact SHA-256 identity: **VERIFIED**
- Production runtime deployment: **VERIFIED**
- Production migration 0015 execution: **VERIFIED**
- Post-migration verification: **VERIFIED**
- Natural macro duplicate-prevention forward verification: **OPEN**
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

Migration production'a runtime-first sıra korunarak uygulanmıştır.

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
Production runtime deploy            VERIFIED
Production 0015 migration            VERIFIED
Post-migration verification          VERIFIED
Natural forward verification         OPEN
Model semantics                      UNCHANGED
LIVE                                 NO-GO
```

## Build and artifact validation evidence

Kullanıcı local repo build öncesinde `d979a6e` HEAD'e fast-forward edildi. `build.bat` çıktısı:

- Python compile kontrolü: **PASS**
- full regression during build: **87 passed in 2.85s**
- release structure check: **Release check: OK**
- PyInstaller one-dir runtime build: **SUCCESS**
- Inno Setup installer compile: **SUCCESS**
- final marker: **BUILD TAMAMLANDI**

Generated artifacts:

```text
Runtime EXE
Path   dist/InvestmentEngine/InvestmentEngine.exe
Size   13,386,018 bytes
SHA256 B426B6D452B0AAA8773747DE693B4EF8F9DB7E12412DA19ADCA5A16E290E1012

Installer
Path   installer/InvestmentEngineSetup-1.2.0.exe
Size   54,582,223 bytes
SHA256 AB87DE9D32F8C874908B94FBF6DCDBEF72D579E1A370A66794C1BD6BE43593AF
```

Build warnings observed but non-blocking for this artifact because the build completed successfully and required PyQt5 SIP binary was packaged:

- PyInstaller admin-mode deprecation warning
- `Hidden import "sip" not found!`

These warnings remain maintenance observations, not P2.3 blockers unless runtime evidence shows failure.

## Production runtime deployment evidence

Hardened installer production makinede çalıştırıldı. Post-install doğrulama:

```text
Expected EXE SHA256
B426B6D452B0AAA8773747DE693B4EF8F9DB7E12412DA19ADCA5A16E290E1012

Installed EXE SHA256
B426B6D452B0AAA8773747DE693B4EF8F9DB7E12412DA19ADCA5A16E290E1012

settings exists    True
rosalock exists    True
Service            RosaInvestmentEngine
State              RUNNING
StartType          Automatic
WIN32_EXIT_CODE    0
SERVICE_EXIT_CODE  0
```

Binary identity exact match olduğu için hardened runtime production deployment **VERIFIED** kabul edilir. Generated `settings` ve `rosalock` korunmuştur; Windows Service çalışır durumdadır.

## Production migration 0015 evidence

Migration `0015_macro_observations_transition_dedup.sql` production Supabase üzerinde başarıyla çalıştırıldı:

```text
Success. No rows returned
```

Hemen ardından `verification/verify_macro_observations_p2_3_post_migration.sql` çalıştırıldı.

Check time:

- `2026-09-10T00:55:41.210674+00:00`

Post-migration evidence:

| Metric | Result |
|---|---:|
| total_rows | 20,433 |
| observation_date_groups | 11,809 |
| revision_groups | 1,505 |
| value_reversion_groups | 57 |
| consecutive_same_value_rows | 0 |
| decision_refs_checked | 672 |
| decision_refs_preserved | 672 |
| decision_refs_lost | 0 |
| legacy_unique_constraint_present | false |
| version_index_present | true |
| safe_cleanup_complete | true |

Bu sonuç dry-run ile öngörülen retained transition setini production'da birebir doğrulamıştır. Persisted decision reference parity korunmuş, ardışık same-value current-view tekrarları tamamen kaldırılmış, legacy unique constraint kaldırılmış ve deterministic version index etkinleştirilmiştir.

Production cleanup/schema classification:

```text
Production migration 0015             VERIFIED
Production retained rows               20433
Consecutive same-value rows             0
Decision refs preserved                 672/672
Decision refs lost                      0
Legacy unique constraint                REMOVED
Deterministic version index             PRESENT
Safe cleanup contract                   true
Natural duplicate-prevention proof      OPEN
Model semantics                         UNCHANGED
LIVE                                    NO-GO
```

## Remaining forward verification

P2.3 production implementation'ın kapanması için yalnız hardened writer'ın doğal scheduler koşusunda yeni same-value duplicate üretmediğinin kanıtı kalmıştır.

Migration sonrası doğrulama sınırı:

- `2026-09-10T00:55:41.210674+00:00`

Bir sonraki doğal `macro_job` sonrasında forward verification şunları kanıtlamalıdır:

1. `macro_job` bu sınırdan sonra doğal scheduled run olarak tamamlanmış olmalı.
2. Yeni yazılan hiçbir row, kendi `(series_id, observation_date)` transition zincirinde previous value ile aynı olmamalı.
3. Global `consecutive_same_value_rows` tekrar `0` kalmalı.
4. Decision reference parity kaybolmamalı.
5. Legacy unique constraint geri gelmemeli ve deterministic version index mevcut kalmalı.
6. Legitimate new observation veya value revision satırları kabul edilir; beklenen kontrat `total_rows hiç artmasın` değildir.

Bu forward evidence alınana kadar P2.3 production implementation **OPEN** kalır.

## Deployment order

Production güvenliği için sıra:

1. hardened runtime build + installer oluştur — **DONE**,
2. artifact SHA-256 al — **DONE**,
3. yeni runtime'ı deploy et ve Windows Service/binari identity doğrula — **DONE**,
4. migration 0015'i production DB'ye uygula — **DONE**,
5. `verification/verify_macro_observations_p2_3_post_migration.sql` çalıştır — **DONE / VERIFIED**,
6. natural macro scheduler koşusundan sonra same-value refetch'in yeni row üretmediğini forward verify et — **NEXT**,
7. ancak bu kanıtlardan sonra P2.3 production implementation CLOSED yapılabilir.

Migration runtime'dan önce uygulanmamıştır; runtime-first deployment sırası korunmuştur.
