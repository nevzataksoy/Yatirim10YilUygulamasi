# Post-Shadow P1 — URA Holdings Immutable Source Snapshot Hardening

Tarih: 09 Eylül 2026  
Model version: `1.2.0`  
Mode: `SHADOW`  
LIVE: `NO-GO`

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

## 6. Deployment sırası

Bu değişiklik schema + runtime birlikte gerektirir. Güvenli sıra:

```text
1. code regression doğrulaması
2. migration 0014 production Supabase'e uygulanır
3. Windows OneDir/installer build
4. mevcut service upgrade
5. doğal daily_ura_job beklenir
6. read-only forward verification çalıştırılır
```

Görev takvimi kuralına göre sırf doğrulama için gereksiz manuel `--once ura` üretilmez.

Forward query:

```text
verification/verify_ura_holdings_source_snapshot_forward.sql
```

## 7. Mevcut sınıflandırma

Kod değişikliği hazırlandıktan sonraki acceptance hedefi:

```text
Historical source-value mutation        NO EVIDENCE
Decision-level fundamentals replay       VERIFIED / 40 of 40
Immutable raw snapshot requirement       REQUIRED / strict source audit
Model semantics changed                  NO
Migration                                REQUIRED / 0014
Runtime forward verification             OPEN until deploy + natural decision
LIVE                                     NO-GO
```

Historical pre-0014 fetch'ler retroaktif olarak exact raw bytes'a dönüştürülemez. Mevcut 40/40 decision-level fundamentals calculation inputs yine audit edilebilir; bu hardening yalnız future exact source identity açığını kapatır.
