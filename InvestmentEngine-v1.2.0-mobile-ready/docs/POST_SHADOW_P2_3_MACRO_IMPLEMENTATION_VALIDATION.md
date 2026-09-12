# Post-Shadow P2.3 — macro.observations Implementation Validation

## Status

- Runtime duplicate prevention implementation: **VERIFIED**
- Deterministic latest-read contract: **VERIFIED**
- Deterministic macro history projection: **VERIFIED**
- Migration 0015 contract tests: **VERIFIED**
- Hardened runtime build: **VERIFIED**
- Installer build: **VERIFIED**
- Artifact SHA-256 identity: **VERIFIED**
- Production runtime deployment: **VERIFIED**
- Production migration 0015 execution: **VERIFIED**
- Post-migration verification: **VERIFIED**
- Natural macro duplicate-prevention forward verification: **VERIFIED**
- P2.3 production implementation: **CLOSED**
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

- implementation HEAD: `0a62eb0`
- focused tests:
  - `tests/test_macro_observations_persistence.py`
  - `tests/test_macro_observations_migration_contract.py`
  - result: **7 passed in 3.08s**
- full regression:
  - result: **87 passed in 8.88s**

## Build and artifact validation evidence

`build.bat` çıktısı:

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

Build warnings observed but non-blocking for this artifact because build completed and required PyQt5 SIP binary was packaged:

- PyInstaller admin-mode deprecation warning
- `Hidden import "sip" not found!`

## Production runtime deployment evidence

Post-install doğrulama:

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

Binary identity exact match olduğu için hardened runtime production deployment **VERIFIED** kabul edilir.

## Production migration 0015 evidence

Migration `0015_macro_observations_transition_dedup.sql` production Supabase üzerinde başarıyla çalıştırıldı.

Post-migration check time:

- `2026-09-10T00:55:41.210674+00:00`

Evidence:

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

Bu sonuç dry-run ile öngörülen retained transition setini production'da birebir doğrulamıştır.

## Natural scheduler forward verification evidence

`verification/verify_macro_observations_p2_3_forward.sql` doğal scheduler koşusundan sonra çalıştırıldı.

Forward check:

- checked_at: `2026-09-10T04:48:51.925231+00:00`
- baseline boundary: `2026-09-10T00:55:41.210674+00:00`
- latest natural `macro_job` id: `2304`
- run_kind: `scheduled`
- status: `OK`
- message: `FRED serileri güncel (quality 97.5)`
- started_at: `2026-09-10T03:15:00.006946+00:00` = `10.09.2026 06:15 TRT`
- finished_at: `2026-09-10T03:15:25.572946+00:00`

Forward result:

| Metric | Result |
|---|---:|
| baseline_total_rows | 20,433 |
| total_rows | 20,434 |
| total_row_delta | +1 |
| post_boundary new_rows | 1 |
| post_boundary new_observation_rows | 1 |
| post_boundary value_transition_rows | 0 |
| post_boundary duplicate_same_value_rows | 0 |
| consecutive_same_value_rows | 0 |
| decision_refs_checked | 680 |
| decision_refs_preserved | 680 |
| decision_refs_lost | 0 |
| legacy_unique_constraint_present | false |
| version_index_present | true |
| forward_contract_complete | true |

`+1` row gerçek yeni observation'dır. Hardened writer doğal macro akışında same-value current-view refetch üretmemiştir. Decision reference parity korunmuş ve cleanup sonrası schema kontratı bozulmamıştır.

## Final classification

```text
P2.3 safe dedup dry-run                  VERIFIED / CLOSED
Runtime duplicate prevention            VERIFIED / DEPLOYED
Deterministic macro reads                VERIFIED / DEPLOYED
Migration 0015                           VERIFIED / APPLIED
Production retained rows after cleanup   20433
Natural scheduled macro_job              VERIFIED / id 2304
Legitimate post-boundary new rows         1
Post-boundary same-value duplicates       0
Global consecutive same-value rows        0
Decision refs preserved                  680/680
Decision refs lost                        0
Forward contract                         true
P2.3 production implementation           CLOSED
Model semantics                          UNCHANGED
LIVE                                     NO-GO
```

## Next scope

P2.3 kapanmıştır. Sonraki ayrı iş **P2.4 macro retention policy + maintenance**'tır ve Oturum12 içinde başlatılmamıştır.

P2.4, P2.3 dedup problemini yeniden çözmeye çalışmamalıdır. Legitimate value-transition/revision lineage ve decision/replay evidence korunmalı; blind age-based delete uygulanmamalıdır. Fiziksel alan geri kazanımı veya `VACUUM FULL` gibi agresif bakım işlemleri ayrıca değerlendirilmelidir. Autonomous maintenance için mevcut `monthly_audit_job`, bounded batch, dry-run/count mode, summary logging ve güvenli transaction boundary tercih edilmelidir.
