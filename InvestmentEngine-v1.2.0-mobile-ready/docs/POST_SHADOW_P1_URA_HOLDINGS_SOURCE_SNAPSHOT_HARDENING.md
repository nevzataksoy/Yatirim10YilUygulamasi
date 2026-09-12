# Post-Shadow P1 — URA Holdings Immutable Source Snapshot Hardening

Tarih: 09–10 Eylül 2026  
Model version: `1.2.0`  
Mode: `SHADOW`  
LIVE: `NO-GO`  
Durum: `CLOSED`

## 1. Araştırma sonucu

`fundamentals.ura_holdings` production scoring için tarih+ticker canonical tablosudur. Mevcut primary key `(holding_date,ticker)` olduğu için aynı dated Global X CSV yeniden çekildiğinde aynı ticker satırı overwrite edilir ve `fetched_at` yenilenir. Ham CSV body veya content hash ayrı bir immutable source kaydı olarak tutulmaz.

Production read-only baseline:

```text
URA decisions                                      42
positive-quality fundamentals decisions            40
complete persisted factor inputs                   40 / 40
holding dates in canonical table                   26
holding dates with multiple current fetch times     0
holding dates with multiple source URLs             0
mixed current fetch-generation dates                0
post-decision canonical rewrites                    16 decisions
```

İkinci forensic karşılaştırmada persisted decision fundamentals girdileri bugünkü canonical tabloyla yeniden hesaplandı:

```text
constituent mismatch decisions              0
weight coverage mismatch decisions          0
current market-value mismatch decisions     0
previous market-value mismatch decisions    0
flow-proxy mismatch decisions               0
```

Doğru sınıflandırma:

```text
Decision-level fundamentals replay          VERIFIED
Historical aggregate value drift            NO EVIDENCE
Mixed canonical snapshot                    NONE OBSERVED
Evaluation-time exact source identity       NOT RECONSTRUCTIBLE
Exact raw CSV replay                        NOT RECONSTRUCTIBLE
```

Yani immutable snapshot gereksiniminin gerekçesi mevcut production verisinde değer drift'i bulunması değildir. Gereksinim strict source/replay audit içindir: ileride issuer aynı dated CSV'yi düzeltir veya yeniden yayımlarsa geçmiş decision'ın gördüğü exact HTTP response bytes kanıtlanabilmelidir.

## 2. Dar hardening tasarımı

Mevcut scoring akışı korunur:

```text
Global X HTTP response
  -> immutable raw snapshot
  -> fundamentals.ura_holdings canonical day
  -> get_ura_holdings_summary()
  -> score_ura_holdings_fundamentals()
  -> model.decisions factors.fundamentals.details
```

Yeni ikinci bir scoring tablosu, queue veya ayrı karar motoru eklenmez.

### 2.1 Immutable raw fetch tablosu

Migration `0014_ura_holdings_source_snapshots.sql` şu tabloyu ekler:

```text
fundamentals.ura_holdings_snapshots
```

Her gerçek fetch ayrı satırdır ve şunları saklar:

- `holding_date`,
- `source_url`,
- source fetch zamanı `fetched_at`,
- exact HTTP response bytes `raw_csv`,
- `raw_csv` SHA-256 değeri `content_sha256`,
- parse edilen constituent adedi.

`content_sha256` UNIQUE değildir. Aynı bytes iki farklı zamanda gerçekten fetch edilmişse iki farklı source event olarak iki farklı `id/fetched_at` ile tutulur.

### 2.2 Canonical gün replacement

Issuer dosyası complete dated holdings snapshot olduğundan aynı transaction içinde:

```text
INSERT immutable raw snapshot
DELETE canonical rows WHERE holding_date = fetched holding_date
INSERT complete parsed constituent set
COMMIT
```

uygulanır.

Böylece aynı dated CSV'nin ileride düzeltilmesi halinde artık yeni CSV'de olmayan bir ticker'ın eski canonical satır olarak kalması engellenir. Raw insert veya canonical replacement'ın herhangi bir bölümü hata verirse transaction'ın tamamı rollback olur.

### 2.3 Decision provenance

`score_ura_holdings_fundamentals()` formülü değiştirilmez. Score/quality üretildikten sonra audit-only metadata olarak:

```text
factors.fundamentals.details.source_snapshots.current
factors.fundamentals.details.source_snapshots.previous
```

eklenir.

Her mevcut snapshot referansı:

```text
id
holding_date
source_url
fetched_at
content_sha256
constituent_count
raw_size_bytes
```

alanlarını taşır. Böylece decision -> raw snapshot -> exact bytes -> SHA256 doğrulama zinciri kurulabilir.

## 3. Üretici akışları

Raw snapshot persistence mevcut iki gerçek Global X fetch noktasına bağlanır:

1. `daily_ura_job`
2. `weekly_job`

Bu akışların scheduler sıklığı değiştirilmez. `daily_ura_job` içindeki holdings best-effort semantiği de korunur; issuer fetch/persistence başarısız olursa fiyat/teknik akışın çalışabilmesi davranışı devam eder.

## 4. Model davranışına etkisi

Değişmeyenler:

```text
factor formulas
factor weights
edge/confidence thresholds
WAIT/WATCH/ACTION classification
K1/K2
reversal/reset
recommended/action sizing
max regime
scheduler cadence
model version
SHADOW/LIVE mode
```

Değişen yalnız source-level persistence/audit garantisidir.

## 5. Test kontratı

Yeni focused testler şunları doğrular:

1. collector exact raw bytes + fetch time bilgisini snapshot'a taşır,
2. raw snapshot + canonical replacement tek connection/transaction kullanır,
3. aynı bytes tekrar fetch edilirse yeni snapshot id fakat aynı SHA-256 oluşur,
4. aynı date yeni complete set eski ticker'ı canonical tabloda bırakmaz,
5. canonical failure raw snapshot dahil bütün transaction'ı rollback eder,
6. current/previous source snapshot refs doğru immutable satırları gösterir.

Gerçek Windows geliştirme/runtime makinesinde regression sonucu:

```text
compileall                         PASS / exit 0
focused URA tests                  9 passed
full pytest                        80 passed
release_check.py                   OK
```

## 6. Deployment sırası ve gerçekleşen kanıt

Uygulanan sıra:

```text
1. code regression doğrulaması                         VERIFIED
2. migration 0014 production Supabase                 VERIFIED
3. Windows OneDir + installer build                   VERIFIED
4. mevcut RosaInvestmentEngine service upgrade        VERIFIED
5. doğal daily_ura_job                                VERIFIED
6. read-only forward verification                    VERIFIED
```

Görev takvimi kuralına uyuldu; doğrulama için manuel `--once ura` kullanılmadı.

### 6.1 Production schema

Migration `0014_ura_holdings_source_snapshots.sql` production Supabase'e uygulandı.

Read-only schema verification:

```text
table_exists                                      true
initial row_count                                 0 / EXPECTED
idx_ura_holdings_snapshots_date_fetch             present
idx_ura_holdings_snapshots_sha256                 present
ura_holdings_snapshots_pkey                       present
constituent_count > 0 CHECK                       present
content_sha256 lowercase 64-hex CHECK             present
raw_csv octet_length > 0 CHECK                    present
```

Initial `row_count=0` bilinçlidir. Pre-0014 exact HTTP bytes elde olmadığı için historical fetch'ler için sahte raw snapshot backfill yapılmadı.

### 6.2 Windows build ve binary identity

Build regression içinde full suite tekrar `80 passed`, release check `OK` verdi; PyInstaller OneDir ve Inno Setup build tamamlandı.

```text
EXE SHA256
07B9A1E9095CE63CC0033A118673A115B8987E622080ED2F4B601FBFDFF4E506

Installer SHA256
04A292DBD79FC4547301DB941D39ACDFB36A90B97C1C2EAE6CCC1DFA48623C05
```

Upgrade öncesi installed EXE eski runtime hash'ini taşıyordu:

```text
73185707D2259D11640251A0B5EE34886919FC18C8E9EC5BC0E2A1C54ABD7C58
```

Upgrade sonrasında installed EXE hash'i yeni build ile birebir eşleşti:

```text
07B9A1E9095CE63CC0033A118673A115B8987E622080ED2F4B601FBFDFF4E506
```

Service doğrulaması:

```text
SERVICE_NAME          RosaInvestmentEngine
STATE                 RUNNING
StartType             Automatic
WIN32_EXIT_CODE       0
SERVICE_EXIT_CODE     0
settings              preserved
rosalock              preserved
```

### 6.3 Post-deploy baseline

Deploy sonrasında, ilk hardened doğal job'dan önce baseline:

```text
checked_at                     2026-09-09T14:41:17.457838+00:00
latest daily_ura_job id        2240
latest job started_at          2026-09-08T23:40:00.012425+00:00
latest URA decision id         88
latest decision as_of          2026-09-08
immutable raw snapshot count   0
```

Bu, job `2240` ve decision `88`'in yeni runtime deploy edilmeden önceki eski runtime kanıtı olduğunu sabitler.

### 6.4 İlk doğal hardened URA koşusu

10 Eylül 2026 02:40 Europe/Istanbul doğal scheduler koşusu:

```text
daily_ura_job id               2295
started_at                     2026-09-09T23:40:00.008914+00:00
finished_at                    2026-09-09T23:40:49.156817+00:00
status                         OK

raw snapshot count             1
snapshot id                    1
holding_date                   2026-09-08
source_url                     https://assets.globalxetfs.com/funds/holdings/ura_full-holdings_20260908.csv
fetched_at                     2026-09-09T23:40:10.689742+00:00
content_sha256                 58ba159a7636a0e2360af1a88abf2cf6364de0d538f072995c715b5de7100f40
raw_size_bytes                 5473
constituent_count              57

new URA decision id            90
as_of                          2026-09-09
status                         WAIT
created_at                     2026-09-09T23:40:46.158861+00:00
```

Bu koşu için manuel job üretilmedi; kanıt natural scheduler akışına aittir.

### 6.5 Exact decision -> raw source forward verification

`verification/verify_ura_holdings_source_snapshot_forward.sql` decision `90` üzerinde çalıştırıldı.

Current snapshot sonucu:

```text
ref_present                    true
snapshot_id                    1
holding_date                   2026-09-08
raw_size_bytes                 5473
ref_id_matches                 true
ref_date_matches               true
ref_sha_matches                true
raw_sha_valid                  true
raw_present                    true
```

`raw_sha_valid=true`, DB'de saklanan exact `raw_csv` bytes üzerinden yeniden hesaplanan SHA-256'nın persisted `content_sha256` ile birebir aynı olduğunu kanıtlar.

Previous snapshot referansı `null`/absent geldi. Bu beklenir ve kontrat tarafından kabul edilir; previous holding date pre-0014 döneme aittir ve o dönemin exact raw HTTP bytes'ı retroaktif olarak reconstruct edilemez.

Final query sonucu:

```text
latest_decision.id             90
decision_evaluated_at          2026-09-09T23:40:45.586742+00:00
forward_contract_complete      true
```

## 7. Final sınıflandırma

```text
Historical source-value mutation        NO EVIDENCE
Historical aggregate value drift         NO EVIDENCE
Mixed canonical snapshot                 NONE OBSERVED
Decision-level fundamentals replay       VERIFIED / 40 of 40
Pre-0014 exact source identity            NOT RECONSTRUCTIBLE
Pre-0014 exact raw CSV replay             NOT RECONSTRUCTIBLE
Migration 0014                            VERIFIED
Windows build/deploy                      VERIFIED
Natural hardened runtime                  VERIFIED
Immutable raw source persistence          VERIFIED
Decision -> raw snapshot provenance       VERIFIED
Exact raw-byte SHA verification           VERIFIED
Forward contract                          VERIFIED / true
Model semantics changed                   NO
URA immutable source snapshot P1          CLOSED
LIVE                                      NO-GO
```

URA P1 kapanışı model davranışı veya threshold değişikliği değildir. `1.2.0` SHADOW modeli aynı karar semantiğiyle çalışmaya devam eder; yalnız future source/replay audit zinciri artık exact immutable issuer bytes'a kadar doğrulanabilir.
