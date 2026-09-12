# Post-Shadow P1 — FRED Point-in-Time Baseline

**Evidence date:** 2026-09-07 (Europe/Istanbul)  
**Model:** 1.2.0  
**Mode:** SHADOW  
**Realtime execution:** OFF  
**Scope:** Existing `macro.observations` contents and strict historical FRED/ALFRED replay feasibility. No production model behavior changed.

## Decision

**Local strict FRED PIT from the current table: NOT AVAILABLE**  
**Current macro history: fetch-day/FRED-current snapshots, not ALFRED validity intervals**  
**Historical value revisions: PRESENT**  
**Production threshold/weights/state: UNCHANGED**  
**Next action:** build a verification-only ALFRED real-time-history replay before any migration/backfill decision.

## Baseline query

The read-only diagnostic `verification/verify_fred_pit_baseline.sql` was executed against the configured Supabase database.

Configured series:

- `DGS2`
- `DGS10`
- `DFII10`
- `VIXCLS`
- `STLFSI4`
- `DTWEXBGS`
- `NASDAQCOM`
- `SP500`

## What the current table contains

Every configured series showed:

- `interval_realtime_rows = 0`
- `open_ended_realtime_rows = 0`
- `same_day_realtime_rows = rows`

This means the persisted `realtime_start` / `realtime_end` pairs behave as request-day FRED-current snapshots rather than historical ALFRED validity intervals.

The table does contain many repeated rows for the same observation date because the collector has been run on multiple request dates. For example:

- `DFII10`: 43,108 rows / 1,463 observation dates / up to 30 rows per observation date
- `DGS10`: 43,105 rows / 1,463 observation dates / up to 30 rows per observation date
- `DGS2`: 41,670 rows / 1,463 observation dates / up to 29 rows per observation date
- `NASDAQCOM`: 40,383 rows / 1,469 observation dates / up to 28 rows per observation date
- `SP500`: 44,719 rows / 1,469 observation dates / up to 31 rows per observation date
- `VIXCLS`: 42,753 rows / 1,501 observation dates / up to 29 rows per observation date

These repeated request-day rows are useful as operational collection history but are not sufficient to reconstruct what was actually public on arbitrary historical dates before collection started.

## Proven revisions

Historical value revisions are not theoretical in this dataset.

### STLFSI4

- 1,503 observation dates have multiple distinct values.
- Maximum distinct values for one observation date: 6.
- Example `2026-07-24`: six different values were observed across request dates.
- Example `2026-08-14`: three different values were observed.

### DTWEXBGS

- At least one observation date has a confirmed value revision.
- Example `2026-08-03`: values `119.6951` and `120.7739` were observed on different request dates.

Therefore an `observation_date`-only replay can silently use a revision that was not available at the historical decision date.

## Strict PIT cutoff coverage

The baseline tested these cutoffs:

- `2022-10-18`
- `2023-10-17`
- `2024-10-11`
- `2025-10-06`
- `2026-07-03`
- `2026-09-07`

For every cutoff:

```text
configured_series = 8
available_series  = 0
missing_series    = all 8 configured series
```

No tested historical cutoff can be reconstructed locally using a validity-interval rule because the current table has no rows whose `realtime_start` / `realtime_end` interval contains those cutoffs.

## Latest-observation ambiguity

Most series currently have more than one row for the latest `observation_date`, because the same value was fetched on multiple request dates. At the measured baseline the latest duplicate rows had the same value, so no current factor-value divergence was observed there.

However, production query ordering currently uses only `observation_date desc`; it does not tie-break multiple revisions by a historical validity rule. The confirmed `STLFSI4` / `DTWEXBGS` revisions prove that this is not safe to reinterpret as strict PIT.

## Interpretation

The current `macro.observations` table serves two different concepts that must not be conflated:

1. **Operational FRED-current snapshots** collected repeatedly since late July 2026.
2. A schema shape capable of storing `realtime_start`, but without the complete historical ALFRED real-time intervals needed for older replay dates.

The current table must therefore not be deduplicated to only `(series_id, observation_date)` and must not be presented as a strict vintage store.

## Next P1 step

Before changing production collection or applying a migration:

1. Fetch FRED/ALFRED observations using the historical real-time period needed by replay.
2. Preserve each observation's historical `realtime_start` / `realtime_end` interval in memory for verification.
3. At each replay `as_of`, select only observations whose real-time validity includes that `as_of` and whose `observation_date <= as_of`.
4. Re-run ETH/BTC directional-core replay and expanding walk-forward with this strict macro selector.
5. Compare current-history replay vs strict-vintage replay for edge, regime, signal eligibility and fold evidence.
6. Only after the comparison decide whether a dedicated ALFRED backfill table/migration is justified.

## 2026-09-07 gerçek veri doğrulama denemeleri — güncel durum

### İlk deneme

İlk gerçek doğrulama koşusunda:

- FRED PIT odaklı testler: `5 passed`
- tüm Python testleri: `59 passed`
- release check: `OK`

Gerçek FRED isteği `HTTP 400 Bad Request` ile durdu. İlk istek 2022–2026 replay ihtiyacı için gereksiz biçimde 1776–9999 arasındaki bütün real-time geçmişi istiyordu. Bu doğrulama isteği replay dönemine daraltıldı. Ayrıca hata mesajlarında API anahtarının URL üzerinden görünmesi engellendi.

### İkinci deneme

Daraltılmış istek sonrasında:

- FRED PIT odaklı testler: `6 passed`
- tüm Python testleri: `60 passed`
- release check: `OK`

Bu kez ilk yedi yapılandırılmış seri tarihsel FRED/ALFRED çağrısından geçti; çalışma son seri `SP500` üzerinde durdu. FRED'in kendi hata cevabı şunu açıkça bildirdi:

```text
The series does not exist in ALFRED but may exist in FRED.
```

Bu nedenle ikinci denemedeki hata artık genel FRED erişim veya tarih-aralığı hatası değildir. `SP500` FRED'de kullanılabilir olsa da ALFRED tarafında doğrulanabilir tarihsel sürüm geçmişi bulunmayan bir kaynak boşluğudur.

Strict geçmiş doğrulamanın amacı geçmişte kanıtlanamayan bugünkü veriyi geçmişe taşımamak olduğundan `SP500` için FRED-current değeri strict replay'e yedek olarak sokulmayacaktır.

Verification-only kod buna göre güncellendi:

- ALFRED'de bulunmayan seri ayrı bir kaynak durumu olarak sınıflandırılır,
- doğrulama tamamen durmaz; o seri tarihsel olarak kanıtlanamayan/eksik veri sayılır,
- tüm yapılandırılmış seriler için kapsama ayrıca raporlanır,
- ALFRED'de bulunan seriler için ayrı kapsama raporu üretilir,
- `current -> comparable current` karşılaştırması ALFRED kaynak boşluğunun etkisini ölçer,
- `comparable current -> strict vintage` karşılaştırması yalnız ALFRED'de bulunan serilerde tarihsel revision/zamanlama etkisini ölçer,
- `current -> strict` karşılaştırması toplam farkı gösterir.

Bu ayrım gereklidir; aksi halde gelecekte görülen bir karar farkının `SP500` tarihsel arşiv eksikliğinden mi yoksa diğer FRED serilerinin geçmişte farklı yayımlanmış olmasından mı kaynaklandığı anlaşılamaz.

Güncel durum:

```text
Strict FRED seçme mantığı              TESTED
Daraltılmış gerçek FRED çağrısı         ÇALIŞIYOR — ilk 7 seri geçti
SP500 ALFRED geçmişi                    YOK / SOURCE GAP
Kaynak boşluğu işleme kodu              TESTED IN CODE, REAL RETEST REQUIRED
Current-vs-strict gerçek karşılaştırma  NOT YET PRODUCED
Model / threshold / LIVE                UNCHANGED
```

Bir sonraki adım aynı read-only verification komutunu tekrar çalıştırmak ve `SP500` kaynak boşluğu işlenirken kalan ALFRED serileriyle gerçek karşılaştırma çıktısının oluştuğunu doğrulamaktır.

## Invariants retained

- Model Version `1.2.0`
- Mode `SHADOW`
- Realtime Execution `OFF`
- production FRED collector unchanged at this baseline step
- production macro query unchanged at this baseline step
- edge/confidence/data-quality thresholds unchanged
- factor weights unchanged
- K1/K2/reversal/reset/sizing unchanged
- no automatic parameter application
- no SHADOW -> LIVE activation
