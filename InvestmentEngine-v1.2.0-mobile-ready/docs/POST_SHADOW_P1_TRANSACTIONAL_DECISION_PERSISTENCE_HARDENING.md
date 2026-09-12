# Post-Shadow P1 — Transactional Decision Persistence Hardening

Tarih: 08 Eylül 2026  
Model version: `1.2.0`  
Mode: `SHADOW`  
LIVE: `NO-GO`

## 1. Araştırma kapanışı

İncelenen eski persistence sırası:

```text
get_signal_state()
apply_signal_state()
upsert_signal_state()     -> ayrı connection / ayrı commit
insert_decision()         -> ayrı connection / ayrı commit
publish_decision_history()-> ayrı connection / ayrı commit
publish_decision_snapshot()-> ayrı connection / ayrı commit
```

Kod seviyesinde state'in decision'dan önce kalıcılaşabildiği atomiklik boşluğu **VERIFIED (Doğrulandı)**.

Production kanıt taramasında ise bu boşluğun gerçekleştiğini gösteren kayıt bulunmadı. Son read-only current-state doğrulamasında iki sistem de latest persisted decision ile tam tutarlı çıktı:

```text
ETH/BTC fully_consistent    true
URA/USD fully_consistent    true
orphan_state_candidates     []
```

Sonuç:

```text
Code-level atomicity gap       VERIFIED
Production occurrence          NO EVIDENCE
Current persistent consistency VERIFIED
Production incident            NO
RCA evidence stage             CLOSED
```

Bu kapanış, historical bir incident bulunmadığını söyler; kod riskinin var olmadığını söylemez.

## 2. Proaktif hardening kararı

Riskin severity'si özellikle K1/K2, reversal ve reset state'inde yüksektir:

- state commit başarılı olup decision insert başarısız olursa K1/K2 state'i decision kaydı olmadan tüketilebilir,
- retry yeni bir karar objesi üretse bile kalıcı state ilerlemiş olduğundan önceki `action_event` yeniden oluşmayabilir,
- reset counter veya reversal state'i decision audit kaydı olmadan ilerleyebilir,
- private decision commit olup public history/snapshot yazımı başarısız kalırsa mobil/audit yüzeyi parçalı kalabilir.

Bu nedenle incident kanıtı beklenmeden persistence hardening uygulanır.

## 3. Yeni transaction boundary

Yeni atomik paket yalnız persistent decision outcome katmanını kapsar:

```text
ONE CONNECTION / ONE TRANSACTION

ensure model.signal_state row
SELECT model.signal_state ... FOR UPDATE
apply_signal_state(... locked current state ...)
UPDATE model.signal_state
INSERT model.decisions
  -> migration 0013 AFTER INSERT trigger
     -> last_evaluated_as_of sync
INSERT public.decision_history
UPSERT public.decision_snapshot
COMMIT
```

Bu zincirde herhangi bir hata oluşursa:

```text
ROLLBACK
```

ve dört persistent outcome bileşeninin hiçbiri kısmi olarak kalıcılaşmaz.

Network/API fetch, features, regimes, factor_scores, health/job logging, Telegram ve execution worker bu transaction'a alınmaz. Böylece DB row lock ve pool connection gereksiz yere uzun tutulmaz.

## 4. Concurrency davranışı

Scheduler aynı job için `max_instances=1` kullansa da çalışan service ile ayrı `--once crypto/ura` process'i çakışabilir.

Bu nedenle transaction, state machine'i çalıştırmadan önce aynı `system` satırını `FOR UPDATE` ile kilitler. İlk-ever state için satır önce:

```sql
insert into model.signal_state(system)
values (...)
on conflict(system) do nothing;
```

ile garanti edilir.

Sonuç:

- aynı sistem için paralel persistence state transition'ları sıraya girer,
- ikinci işlem ilk işlemin committed state'ini görür,
- `ETH/BTC` ve `URA/USD` farklı primary-key satırları olduğu için global bir mutex oluşturulmaz.

## 5. Karar mekanizmasına etkisi

Başarılı normal run davranışında aşağıdakiler değiştirilmez:

```text
factor scores
weights
edge/confidence thresholds
WAIT/WATCH/ACTION classification
K1/K2 kuralları
reversal kuralları
reset thresholds / reset_days
recommended_size / action_size formülü
max_regime_pct
scheduler cadence
model_version
SHADOW/LIVE mode
```

Değişen yalnız persistence garantisidir:

```text
Önce: state ayrı başına commit olabilir.
Sonra: state + decision + history + snapshot birlikte commit olur veya birlikte rollback olur.
```

`0013_signal_state_market_date_idempotency.sql` yeniden uygulanmaz ve değiştirilmez. Trigger aynı transaction içinde çalıştığı için decision transaction rollback olursa marker güncellemesi de rollback olur.

## 6. Kapsam dışı kalan artık riskler

Bu hardening aşağıdaki ayrı problemleri otomatik çözmez:

1. **Ambiguous commit outcome:** PostgreSQL commit etmiş fakat bağlantı COMMIT cevabı dönmeden kopmuş olabilir. Bu durum gelecekte evaluation-level idempotency anahtarı gerektirebilir. `(system, as_of)` unique yapılmaz; repeated same-as-of evaluations production'da meşrudur.
2. **Older as_of arriving later:** eski market tarihine ait bir evaluation daha yeni `as_of` sonrasında persistence'a ulaşabilir. Bu davranışı reject/skip etmek model semantiği kararıdır ve bu hardening içinde değiştirilmez.
3. **External side effects:** Telegram veya execution worker PostgreSQL transaction'ına katılamaz. Bunlar yalnız DB commit başarıyla döndükten sonra başlatılır. Tam exactly-once external delivery gerekirse ayrı transactional-outbox tasarımı gerekir.
4. **Raw source snapshot/versioning:** `fundamentals.ura_holdings` immutable raw fetch history konusu bu görevden bağımsız ve OPEN kalır.

## 7. Test kontratı ve gerçek ortam doğrulaması

Yeni focused testler şu failure-injection senaryolarını kapsar:

- success path: tek connection, tek commit, `FOR UPDATE` lock,
- decision insert failure -> full rollback,
- public decision_history failure -> full rollback,
- public decision_snapshot failure -> full rollback,
- failed K1 state'i tüketmez; fresh retry tekrar K1 üretebilir,
- failed reset transition önceki committed state'i korur.

08 Eylül 2026 tarihinde development/production Shadow host'unda kullanıcı tarafından çalıştırılan gerçek doğrulama sonucu:

```text
local HEAD                         d88d997
compileall                         PASS / exit 0
focused transactional+state tests 9 passed / exit 0
full Python tests                 74 passed / exit 0
release check                     OK / exit 0
```

Final toplu exit özeti:

```text
COMPILE=0 FOCUSED=0 FULL=0 RELEASE=0
```

Bu sonuç code/test acceptance için yeterlidir. Test koşusu yeni migration gerektirmez ve model parametrelerini değiştirmez.

## 8. Kapanış sınıflandırması

Araştırma kapanışı:

```text
Historical production incident       NO EVIDENCE
Current state inconsistency           NONE OBSERVED
RCA evidence stage                    CLOSED
```

Hardening code/test kapanışı:

```text
Atomic decision persistence           VERIFIED
Failure rollback                      VERIFIED
Same-system state serialization       VERIFIED
Focused regression                    VERIFIED / 9 passed
Full regression                       VERIFIED / 74 passed
Release check                         VERIFIED / OK
Model semantics changed               NO
Migration required                    NO
Transactional hardening substage      CLOSED
LIVE                                  NO-GO
```

## 9. Runtime deploy ve ileri yönlü doğrulama — KAPANDI

08 Eylül 2026 tarihinde `build.bat` ile branch HEAD `750ad69` üzerinden OneDir runtime ve Inno Setup installer başarıyla üretildi. Transactional kod commit'i bu build zincirinde `d88d997` olarak bulunur; `750ad69` yalnız doğrulama belgesini güncelleyen sonraki documentation commit'idir.

Build kanıtı:

```text
full Python tests                  74 passed
release check                      OK
PyInstaller OneDir                 SUCCESS
Inno Setup                         SUCCESS
built EXE SHA256                   73185707D2259D11640251A0B5EE34886919FC18C8E9EC5BC0E2A1C54ABD7C58
installer SHA256                   D975EACB02EF477D799D305F98654FA678ABE0CAE5464AC4C9027AE1FB7316C9
```

Mevcut v1.2.0 kurulumunun üzerine upgrade yapıldı. Upgrade öncesi kurulu EXE hash'i farklıydı; upgrade sonrasında kurulu EXE hash'i build artefactıyla birebir eşleşti:

```text
pre-deploy installed EXE SHA256    91300423EA360C11E923C1AC74F437581BAAEF0DC23CFBA3458B60FB8A29890A
post-deploy installed EXE SHA256   73185707D2259D11640251A0B5EE34886919FC18C8E9EC5BC0E2A1C54ABD7C58
built EXE == installed EXE          TRUE
settings preserved                  TRUE
rosalock preserved                  TRUE
RosaInvestmentEngine                RUNNING
service StartType                    Automatic
CLI --service-status                 exit 0
```

Yeni servis process başlangıcı:

```text
ProcessId        18196
StartTimeLocal   2026-09-08 06:51:43 Europe/Istanbul
StartTimeUtc     2026-09-08 03:51:43Z
```

Deploy sonrasında ilk read-only DB kontrolünde mevcut satırlar tutarlıydı fakat henüz yeni servis process'i tarafından üretilmiş decision yoktu. Görev takvimi kuralına uygun olarak yalnız doğrulama amacıyla manuel `--once crypto/ura` çalıştırılmadı; doğal scheduler kararları beklendi.

09 Eylül 2026 tarihinde aynı servis process'i hâlâ çalışırken iki doğal scheduler kararı oluştu:

```text
ETH/BTC
  latest decision id      89
  decision_created_at     2026-09-09 02:21:22.609961Z
  as_of                   2026-09-08
  status                  WAIT
  service_start_utc       2026-09-08 03:51:43Z
  post-deploy decision    YES
  history_present         true
  history_matches         true
  snapshot_matches        true
  marker_matches          true
  signal_state matches    true
  fully_consistent        true

URA/USD
  latest decision id      88
  decision_created_at     2026-09-08 23:40:43.067080Z
  as_of                   2026-09-08
  status                  WAIT
  service_start_utc       2026-09-08 03:51:43Z
  post-deploy decision    YES
  history_present         true
  history_matches         true
  snapshot_matches        true
  marker_matches          true
  signal_state matches    true
  fully_consistent        true
```

Her iki yeni decision da servis başlangıcından sonradır. `model.signal_state.last_evaluated_as_of`, persistent state alanları, `model.decisions.rationale.signal_state`, `public.decision_history` ve `public.decision_snapshot` aynı decision outcome ile eşleşmektedir.

Final runtime sınıflandırması:

```text
Runtime binary deployment            VERIFIED
Built/installed binary identity      VERIFIED
Service runtime                      VERIFIED / RUNNING
Post-deploy ETH/BTC scheduler run    VERIFIED / decision 89
Post-deploy URA/USD scheduler run    VERIFIED / decision 88
State/decision/history/snapshot      VERIFIED / fully_consistent=true
Runtime forward verification         VERIFIED
Transactional persistence runtime    CLOSED
Model semantics changed              NO
LIVE                                 NO-GO
```

Dolayısıyla **RCA evidence**, **transactional hardening code/test**, **runtime binary deployment** ve **runtime forward verification** kapanmıştır. Transactional state-before-decision başlığı artık production/replay açık araştırma listesinde tutulmaz.

Bu belge full production/replay parity'yi kapatmaz. Raw holdings immutable source snapshot/versioning başlığı ayrı OPEN araştırma olarak kalır.
