# Oturum12 → Oturum13 Proje Devri

Tarih: 10 Eylül 2026

## 1. Proje

Proje: `BTC_ETH_URA_10YIL`
Repo: `https://github.com/nevzataksoy/Yatirim10YilUygulamasi.git`
Aktif branch: `agent/portfolio-audit-reset`

Yatırım ufku: `25.07.2026 – 25.07.2036`
Model version: `1.2.0`
Mode: `SHADOW`
Realtime execution: `OFF`
Shadow readiness: `READY`
LIVE: `NO-GO`

Sistemler: `ETH/BTC` ve `URA/USD`.
Quasar gerçek kullanıcı portföy ledger'ını tutar; Python global model kullanıcı holdings miktarına göre sizing yapmaz. Otomatik exchange order execution yoktur.

Released model parametreleri Oturum13'te değiştirilmemelidir:

- minimum data quality: 80
- edge threshold: 70
- confidence: 70
- strong edge/confidence: 80/80
- WATCH edge: 55
- reset edge: 45
- reset days: 5
- base tranche: 25%
- max regime: 50%

Post-Shadow validation bu parametreleri otomatik değiştiremez. Davranış değişikliği ancak açık kullanıcı onayı + yeni model version + tests + deploy + yeni Shadow Epoch ile ele alınabilir.

## 2. Oturum13 bağlamı devralmak için önce okunacak dosyalar

Önce remote branch güncelliğini doğrula ve aşağıdaki dosyaları published branch üzerinden incele:

1. `InvestmentEngine-v1.2.0-mobile-ready/docs/SESSION_HANDOFF_OTURUM12_TO_OTURUM13.md`
2. `InvestmentEngine-v1.2.0-mobile-ready/docs/POST_SHADOW_P2_MACRO_JOB_RUNS_DATA_LIFECYCLE_DEBT.md`
3. `InvestmentEngine-v1.2.0-mobile-ready/docs/POST_SHADOW_P2_1_MACRO_OBSERVATIONS_PRODUCTION_BASELINE.md`
4. `InvestmentEngine-v1.2.0-mobile-ready/docs/POST_SHADOW_P2_2_MACRO_DETERMINISTIC_READ_CONTRACT.md`
5. `InvestmentEngine-v1.2.0-mobile-ready/docs/POST_SHADOW_P2_3_MACRO_SAFE_DEDUP_DRY_RUN.md`
6. `InvestmentEngine-v1.2.0-mobile-ready/docs/POST_SHADOW_P2_3_MACRO_IMPLEMENTATION_VALIDATION.md`
7. `InvestmentEngine-v1.2.0-mobile-ready/migrations/0015_macro_observations_transition_dedup.sql`
8. `InvestmentEngine-v1.2.0-mobile-ready/app/database/repository.py`
9. `InvestmentEngine-v1.2.0-mobile-ready/verification/verify_macro_observations_p2_3_forward.sql`
10. `InvestmentEngine-v1.2.0-mobile-ready/app/engine.py` — özellikle `macro_job` ve `monthly_audit_job`.

Published code + gerçek runtime/DB evidence dokümanlarla çelişirse published code/runtime/DB evidence önceliklidir.

## 3. Nerede kaldık

Post-Shadow P1 URA immutable raw holdings source snapshot CLOSED.

Macro data-lifecycle akışında:

```text
P2.1  macro.observations production baseline         CLOSED
P2.2  deterministic read/version contract            CLOSED
P2.3  safe dedup + future duplicate prevention       CLOSED
P2.4  macro retention policy + maintenance           NEXT / OPEN
P2.5  system.job_runs production baseline            OPEN
P2.6  job_runs evidence-aware retention policy       OPEN
P2.7  autonomous bounded maintenance integration     OPEN
```

### P2.3 final production evidence

Eski production baseline:

- `295,123` macro rows
- `11,809` `(series_id, observation_date)` groups
- dominant same-value current-view refetch şişkinliği
- gerçek revisions mevcut, özellikle STLFSI4

Validated dry-run:

- retained: `20,433`
- candidate delete: `274,690` (~%93.08)
- revision groups: `1,505`
- value-reversion groups: `57`
- decision refs preserved: `672/672`
- decision refs lost: `0`

Runtime hardening production'a deploy edildi:

- aynı `(series,date)` için latest retained value aynıysa INSERT yok
- same-value refetch UPDATE yok, `fetched_at` mutation yok
- value değişirse immutable transition row
- same-series writers transaction advisory lock ile serialize
- latest/history reads deterministic

Migration `0015_macro_observations_transition_dedup.sql` production'a uygulandı:

- total retained rows: `20,433`
- consecutive same-value rows: `0`
- decision refs: `672/672`
- legacy UNIQUE `(series_id, observation_date, realtime_start)`: removed
- deterministic version index: present
- `safe_cleanup_complete=true`

Natural scheduler forward verification:

- macro job id: `2304`
- run kind: `scheduled`
- status: `OK`
- started: `2026-09-10T03:15:00.006946+00:00` = `10.09.2026 06:15 TRT`
- baseline rows: `20,433`
- final rows: `20,434`
- legitimate new observation rows: `1`
- same-value duplicate rows: `0`
- global consecutive same-value rows: `0`
- decision refs preserved: `680/680`
- decision refs lost: `0`
- `forward_contract_complete=true`

Sonuç: **P2.3 VERIFIED / CLOSED**. Hem mevcut şişkinlik temizlendi hem de normal production ingest'in aynı şişkinliği yeniden üretmediği doğal scheduler ile doğrulandı.

## 4. Güncel production runtime/build kimliği

```text
Runtime EXE SHA256
B426B6D452B0AAA8773747DE693B4EF8F9DB7E12412DA19ADCA5A16E290E1012

Installer SHA256
AB87DE9D32F8C874908B94FBF6DCDBEF72D579E1A370A66794C1BD6BE43593AF
```

Installed EXE hash build EXE hash ile birebir eşleşti.
Windows Service `RosaInvestmentEngine` = Running / Automatic.
`settings` ve `rosalock` korunmuş durumda.

## 5. Oturum13'te ilk yapılacak iş

**P2.4 — macro retention policy + maintenance** ile başlanacak.

P2.4 Oturum12'de başlatılmadı. İlk adım production mutation değildir. Önce READ-ONLY baseline/consumer analysis yapılmalıdır.

İlk analiz minimum şu alanları ölçmeli/kanıtlamalıdır:

- P2.3 sonrası retained transition history'nin series bazında observation age dağılımı,
- legitimate revision/value-transition tarihçesinin yaş dağılımı,
- released decisions'ın hangi macro tarih/value kanıtlarına ihtiyaç duyduğu,
- walk-forward/model validation replay'in gerekli historical coverage sınırı,
- strict FRED/ALFRED source/revision audit gereksinimleri,
- table/index physical size ve cleanup sonrası dead tuple/vacuum durumu,
- hangi retained rows'un gerçekten korunması gerektiği ve hangi row sınıfının retention adayı olabileceği.

Henüz DELETE, retention cutoff, VACUUM FULL veya scheduler değişikliği uygulanmamalıdır.

P2.4 P2.3 duplicate problemini yeniden çözmeye çalışmamalıdır. Same-value refetch prevention zaten production'da CLOSED'dur.

Korunması gereken temel kontratlar:

- legitimate value-transition/revision lineage,
- decision/replay evidence,
- released model validation ihtiyacı,
- 10 yıllık proje ufku,
- strict source/revision audit.

Blind age-based delete yoktur. `UNIQUE(series_id, observation_date)` gibi revision ezen yaklaşım yoktur. `VACUUM FULL` gibi agresif/table-locking işlem etki analizi olmadan yapılmaz.

Maintenance otomasyonu gerekirse yeni scheduler katmanı eklemek yerine öncelikle mevcut `monthly_audit_job` içine aşağıdaki özelliklerle bounded maintenance düşünülmelidir:

- bounded batch
- explicit cutoff
- protected evidence predicate
- dry-run/count mode
- summary logging
- açık transaction boundary
- failure halinde decision path'i bozmama
- model parameterlerine dokunmama

## 6. Sonraki görev sırası

P2.4 tamamlandıktan sonra:

- P2.5 `system.job_runs` production baseline
- P2.6 evidence-aware `job_runs` retention
- P2.7 autonomous bounded maintenance integration

`system.job_runs` için eski kayıtların P0/RCA ve incident evidence değeri olduğu unutulmamalıdır; `7 günden eski her şeyi sil` uygulanamaz.

## 7. Çalışma ve Git disiplini

Kullanıcı çalışma biçimi:

- önce mevcut dosya/mimariyi incele,
- gereksiz yeni katman/kuyruk ekleme,
- mevcut veri akışını koru,
- değişiklikleri ilgili fonksiyonlarla sınırla,
- sonunda değişen/yeni dosyaları açık listele,
- bir seferde tek mantıksal alt adım ilerle.

GitHub write öncesi **her seferinde**:

1. remote `agent/portfolio-audit-reset` HEAD'i yeniden kontrol et,
2. değiştirilecek dosyayı yeniden fetch et ve güncel blob SHA'yı al,
3. sonra write yap.

Kullanıcı paralel push yapabilir; eski SHA üzerinden write yapılmamalıdır.

Her mantıksal değişiklik ayrı commit/push olmalıdır.
Commit mesajları Türkçe olmalıdır.
Her commit sonrası raporla:

- short SHA
- full SHA
- Türkçe commit mesajı
- MODIFIED/ADDED dosyalar

PowerShell'de birden fazla komut verilecekse tek satır ve explicit `;` kullan.

Kullanıcı local repo için `git pull`, `git status`, test vb. çıktı vermeden local repo'nun güncel/clean olduğunu iddia etme.

Natural scheduler evidence gereken yerde job'u manuel tetikleme.

## 8. Model sınırı

P2 veri yaşam döngüsü çalışmaları model tuning değildir.

```text
Threshold/weights/K1/K2/reset/sizing  UNCHANGED
Model version                         1.2.0
Mode                                  SHADOW
Realtime execution                    OFF
LIVE                                  NO-GO
```
