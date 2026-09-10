# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 11 Eylül 2026  
Amaç: Yeni sohbetin güncel proje durumunu konuşma geçmişini yeniden keşfetmeden devralması.

Kalıcı bağlam `PROJECT_MEMORY_BANK.md`, normatif motor gerçeği `SIGNAL_ENGINE_DECISION_CONTRACT.md`, Shadow adımları `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`, checkpoint kanıtları `SHADOW_CHECKPOINT_LOG.md`, Post-Shadow kanıtları ise ilgili `POST_SHADOW_*.md` belgelerindedir.

Kod ile eski belge çelişirse güncel branch'teki yayımlanmış kod, migration, test ve gerçek runtime/Supabase kanıtı önceliklidir.

## 1. Aktif repo / branch

```text
Repo   nevzataksoy/Yatirim10YilUygulamasi
Branch agent/portfolio-audit-reset
```

Repo default branch'i `master` olsa da güncel Python/Shadow geliştirme gerçeği `agent/portfolio-audit-reset` branch'indedir.

Kullanıcının yerel repo yolu:

```text
D:\wamp64\www\Yatirim10YilUygulamasi
```

11 Eylül 2026 Oturum15 başlangıcında kullanıcı tarafından verilen kontrol sonucu:

```text
LOCAL_HEAD   aadefba
REMOTE_HEAD  aadefba
BRANCH       agent/portfolio-audit-reset
STATUS       clean
```

Bu yalnız kontrol anındaki yerel durumu kanıtlar. Yeni sohbet yine remote HEAD'i ve kullanıcı local worktree durumunu yeniden doğrulamalıdır.

Her mantıksal değişiklik ayrı commit edilir ve aynı branch'e push edilir. Yeni commit mesajları Türkçe yazılır. Raw telemetry/log/generated verification çıktıları sırf kanıt olsun diye commit edilmez.

## 2. Değişmez released model durumu

```text
Model Version        1.2.0
Mode                 SHADOW
Realtime Execution   OFF
SHADOW_READINESS     READY
LIVE                  NO-GO
```

Released ayarlar:

```text
minimum data quality 80
edge threshold       70
confidence threshold 70
strong edge          80
strong confidence    80
WATCH edge           55
reset edge           45
reset days           5
base tranche         25%
max regime           50%
```

Factor weights, K1/K2, reversal, reset, sizing, scheduler cadence, SHADOW/LIVE mode ve model version kullanıcı açıkça onaylamadan değiştirilmez.

`READY` otomatik LIVE değildir. `direction` emir değildir. `ACTION` tek başına yeni kademe değildir; yeni kademe için ayrıca `action_event=true` gerekir. Python kullanıcı portföy bakiyesine göre karar vermez ve otomatik exchange order göndermez.

Model davranışı değişecekse ayrı kullanıcı onayı + model version kararı + test + gerekiyorsa migration + deploy + yeni Shadow Epoch birlikte değerlendirilir.

## 3. Shadow görev takvimi ve readiness — CLOSED / VERIFIED

30 günlük Shadow görev takvimi tamamlandı. Released model `READY` durumuna ulaştı; LIVE açılmadı.

Shadow Readiness job provenance contamination başlığı ayrıca kapatıldı.

Eski `Repository.shadow_readiness_stats()` geniş job row sayımından dolayı `manual`, `test`, `backfill`, `dependency` ve `maintenance` kayıtlarıyla readiness oranını kirletebiliyordu.

Uygulanan dar düzeltme:

```text
active Shadow Epoch
+ scheduler contract expected fires
+ aynı shadow_epoch_id
+ run_kind in ('scheduled','scheduled_legacy')
+ success statuses OK/DEGRADED/SKIPPED
```

7 günlük RCA penceresi:

```text
expected fires       384
captured/completed   378
missing                6
duplicate extra        0
off-cadence            0
job success rate       0.984375
job success percent   98.4375%
released minimum       0.98
```

İlgili commitler:

```text
81f1c09  Shadow Readiness scheduler provenance hesabını düzelt
aadefba  Shadow Readiness provenance regresyon testini ekle
```

Son regression:

```text
targeted tests   5 passed
full pytest      94 passed
release check    OK
```

Son Supabase `SHADOW_READINESS` snapshot:

```text
model_version        1.2.0
status               READY
engine_mode          shadow
job_count            384
job_success_rate     0.984375
job_success_percent  98.437500
blockers             []
calendar_days        43
crypto_decision_days 42
ura_decision_days    28
```

Kapanış:

```text
Shadow Readiness provenance contamination   CLOSED / VERIFIED
threshold/model semantics change             NONE
LIVE                                         NO-GO
```

## 4. Post-Shadow P0 reliability — CLOSED / NON-BLOCKING

İlgili belgeler:

- `docs/POST_SHADOW_P0_CONNECTION_POOL_RCA.md`
- `docs/POST_SHADOW_P0_RUNTIME_RELIABILITY_CLOSURE.md`

Özet:

- historical 10s pool timeout development ortamında doğrudan yeniden üretilemedi,
- pool lifecycle/replacement davranışı çalışıyor,
- yeni instrumented checkout timeout görülmedi,
- `max_size=6`, `timeout=10s` değiştirilmedi,
- generic DB retry eklenmedi,
- scheduler serialize edilmedi,
- historical production observation borcu GitHub Issue #2'de kaldı.

Bu başlık model davranışı tuning işi değildir.

## 5. P1 walk-forward ve FRED strict historical validation

### 5.1 Expanding walk-forward implementation — CLOSED / evidence LIMITED

Expanding walk-forward altyapısı teknik olarak doğrulandı.

Ana sonuç:

```text
configured edge=70 OOS signal   0
signal evidence                 LIMITED / SIGNAL-STARVED
threshold change                NOT SUPPORTED
LIVE                            NO-GO
```

Daha düşük keşif eşiklerinde bulunan sınırlı OOS sinyaller released edge=70 threshold'unu düşürmeyi desteklememektedir.

Sinyal kıtlığı threshold veya factor-weight değişikliği için otomatik gerekçe değildir.

### 5.2 FRED strict historical validation — CLOSED / VERIFIED

Verification-only ALFRED yolu gerçek FRED historical real-time verisini kullanır ve production collector davranışını değiştirmez.

Doğrulanan ana sonuç:

```text
configured series             8
ALFRED-available              7
ALFRED-unavailable            SP500
complete-coverage days        1397
complete ratio                98.3803%
edge=70 qualification changes 0
```

FRED revision/yayın-zamanı farkı edge ve rejim yorumunu bazı tarihlerde değiştirebilse de released `edge=70` qualification kıtlığını açıklamamaktadır.

## 6. Production/replay persistence hardening

### 6.1 Same-market-date signal-state idempotency — CLOSED / VERIFIED

Migration:

```text
0013_signal_state_market_date_idempotency.sql
```

`model.signal_state.last_evaluated_as_of` eklenmiştir ve trigger ile latest decision market date'e senkron tutulur.

Güncel production doğrulaması:

```text
ETH/BTC
last_evaluated_as_of = 2026-09-09
latest_decision_as_of = 2026-09-09
MATCH

URA/USD
last_evaluated_as_of = 2026-09-09
latest_decision_as_of = 2026-09-09
MATCH
```

Aynı `as_of` tekrarında reset counter ikinci kez ilerlemez. Threshold, K1/K2, reversal, sizing, scheduler cadence ve mode semantiği değişmemiştir.

### 6.2 Evaluation-time provenance hardening — CLOSED / VERIFIED

URA karar payload'ına audit-only olarak breadth numeric scoring inputs, breadth timestamp/date, exact `event_refs`, event health timestamp/status ve evaluated event count eklenmiştir.

Historical pre-hardening satırlar geriye dönük uydurulmamıştır.

Bu hardening scoring formülü veya model davranışı değiştirmez.

### 6.3 Transactional decision persistence — CLOSED / VERIFIED

Güncel runtime `app/database/decision_persistence.py` içindeki `persist_decision_outcome()` akışını kullanır.

Akış:

```text
signal_state row
→ FOR UPDATE lock
→ state transition
→ model.signal_state UPDATE
→ model.decisions INSERT
→ public.decision_history INSERT
→ public.decision_snapshot UPSERT
→ tek COMMIT
```

Herhangi bir persistence hatasında transaction bütünü rollback olur. Telegram/execution side-effect'leri yalnız transaction başarıyla tamamlandıktan sonra başlar.

Regression kapsamı:

```text
decision failure rollback
history failure rollback
snapshot failure rollback
failed K1 retry
failed reset transition
```

Production DB bütünlük sonucu:

```text
DECISION_WITHOUT_HISTORY    0 / PASS
DECISION_HISTORY_MISMATCH   0 / PASS
LATEST_SNAPSHOT ETH/BTC     PASS
LATEST_SNAPSHOT URA/USD     PASS
```

Kapanış:

```text
Transactional decision persistence   CLOSED / VERIFIED
Historical production incident       NO EVIDENCE
Model semantics changed              NO
LIVE                                 NO-GO
```

## 7. URA immutable raw holdings source snapshot — CLOSED / VERIFIED

Bu başlık artık OPEN değildir.

Kanonik belge:

```text
docs/POST_SHADOW_P1_URA_HOLDINGS_SOURCE_SNAPSHOT_HARDENING.md
```

Migration:

```text
0014_ura_holdings_source_snapshots.sql
```

`fundamentals.ura_holdings_snapshots` her gerçek Global X fetch event'ini immutable olarak saklar:

```text
id
holding_date
source_url
fetched_at
content_sha256
raw_csv
constituent_count
```

Aynı bytes yeniden fetch edilse bile ayrı gerçek fetch event'i olduğu için yeni snapshot ID alması bilinçlidir.

Raw snapshot insert + canonical `fundamentals.ura_holdings` replacement aynı transaction içindedir.

İlk doğal hardened scheduler kanıtı:

```text
daily_ura_job id     2295
started_at           2026-09-09T23:40:00Z
status               OK

snapshot id          1
holding_date         2026-09-08
constituent_count    57
raw_size_bytes       5473
```

Snapshot SHA256:

```text
58ba159a7636a0e2360af1a88abf2cf6364de0d538f072995c715b5de7100f40
```

Yeni doğal URA decision:

```text
decision_id  90
as_of        2026-09-09
status       WAIT
```

Decision provenance doğrulaması:

```text
referenced_snapshot_id     1
actual_snapshot_id         1
referenced_holding_date    2026-09-08
actual_holding_date        2026-09-08
referenced SHA256          MATCH
constituent_count          57 / 57
raw_size_bytes             5473 / 5473
provenance_match           PASS
```

Pre-0014 kararların exact raw HTTP bytes ref taşımaması beklenen tarihsel durumdur. Sahte backfill yapılmaz.

`previous_snapshot_id=NULL` mevcut P1 kapanışını engellemez; previous holding date pre-0014 dönemdedir ve exact HTTP bytes geriye dönük reconstruct edilemez.

Gelecekte ikinci farklı immutable holdings tarihi oluşunca current + previous snapshot bağının ikisini birlikte görmek ekstra forward evidence olacaktır; kapanış blocker'ı değildir.

Manuel `--once ura` ile doğal evidence taklit edilmez.

## 8. P2 macro/job-runs data lifecycle — CLOSED

P2.1–P2.7 tamamlandı.

Kanonik belge:

```text
docs/POST_SHADOW_P2_MACRO_JOB_RUNS_DATA_LIFECYCLE_DEBT.md
```

Kapanış commit'i:

```text
209b5b225ec2bc733512b771f6d7ead825afeaa3
P2.7 lifecycle görev borcunu kapat
```

Özet:

```text
P2.1  macro.observations production baseline         CLOSED
P2.2  macro deterministic read/version contract      CLOSED
P2.3  macro dedup + future duplicate prevention      CLOSED
P2.4  macro retention policy + maintenance           CLOSED
P2.5  job_runs production baseline                   CLOSED
P2.6  job_runs evidence-aware retention policy       CLOSED
P2.7  bounded lifecycle observability integration    CLOSED
P2     overall data lifecycle debt                    CLOSED
```

Migration `0015_macro_observations_transition_dedup.sql` uygulanmıştır.

P2.7 mevcut `monthly_audit_job` içinde observability-only çalışır:

```text
new scheduler/queue       NONE
macro recurring DELETE    NONE
job_runs DELETE           NOT AUTHORIZED
VACUUM FULL               NONE
mutation                  NONE
candidate yoksa           NO_OP
```

İlk doğal `monthly_audit_job` lifecycle observation'ı:

```text
1 Ekim 2026 09:00 Europe/Istanbul
```

beklenmektedir. Bu yalnız forward operational observation'dır; P2.7 kapanış blocker'ı değildir ve `--once monthly` ile taklit edilmemelidir.

## 9. Güncel Windows runtime / deploy identity

Son build ve development Windows makinesindeki upgrade deployment doğrulaması:

```text
Built EXE SHA256
FA945EDB69B57C0D9CE305430BFB1815CA74780065A91C9BCC8259C8642EF295

Installer SHA256
6C52BAAF9A2590AD14FEF72E68A11F87E29E71FA3354A84CA37125B05AB8129D

EXE_HASH_MATCH=True
```

Windows Service:

```text
Name       RosaInvestmentEngine
State      Running
StartMode  Auto
ProcessId  6272
StartTime  10.09.2026 23:34:28 Europe/Istanbul
```

Kurulu runtime üzerinden model validation:

```text
model_validation: OK
core=OK
observations=1423
shadow=READY
VALIDATION_EXIT_CODE=0
SERVICE_PID_UNCHANGED=True
```

Bu deployment'da settings/rosalock korunmuştur.

Bu güncel runtime identity, eski P1/P2 deployment hash'lerinin yerine current deployed baseline olarak alınmalıdır.

## 10. LIVE neden hâlâ NO-GO

`SHADOW_READINESS=READY` yalnız manuel production review kapısıdır.

LIVE hâlâ NO-GO çünkü:

- production ACTION/WATCH örneklemi yeterli değildir,
- bağımsız OOS signal evidence sınırlı/signal-starved durumdadır,
- historical replay production K1/K2/reset/reversal/event/data-quality zincirini birebir doğrulamaz,
- URA full PIT replay için holdings/breadth/event point-in-time history henüz yeterli değildir.

Bu durum threshold düşürmek, factor weights değiştirmek veya LIVE açmak için otomatik gerekçe değildir.

## 11. Gelecekte yalnız forward observation olarak izlenecekler

Aşağıdakiler mevcut kapanışları yeniden OPEN yapmaz:

1. `1 Ekim 2026 09:00 Europe/Istanbul` ilk doğal `monthly_audit_job` lifecycle observation'ı.
2. İleride ikinci post-0014 farklı URA holdings tarihi oluşunca current + previous immutable raw snapshot refs zincirinin birlikte görülmesi.
3. Historical connection-pool timeout ailesi için GitHub Issue #2 observation borcu.

Doğal scheduler evidence'i manuel job ile taklit edilmez.

## 12. Sıradaki teknik çalışma — Windows build pipeline elevation RCA

İlk yeni bağımsız teknik çalışma, build pipeline'ın zorunlu Administrator elevation davranışını araştırmaktır.

Mevcut problem:

```text
build.bat
```

build'in tamamını Administrator seviyesine yükseltiyor. Son PyInstaller build sırasında elevated build davranışının deprecated olduğuna ve gelecekte PyInstaller 7 ile engellenebileceğine ilişkin uyarı görülmüştür.

Bu şu anda build'i bozmadı; EXE ve installer başarıyla üretildi ve deploy edildi. Ancak packaging reliability borcudur.

İlk aşamada kod değiştirme.

Önce tamamen incelenecek dosyalar:

```text
build.bat
installer/investmentengine_setup.iss
scripts/release_check.py
docs/BUILD_AND_INSTALLER.md
```

Araştırma soruları:

```text
1. PyInstaller build gerçekten Administrator gerektiriyor mu?
2. Inno Setup compile gerçekten Administrator gerektiriyor mu?
3. --uac-admin yalnız üretilen EXE manifest davranışı mı?
4. build.bat içindeki net session / auto-elevation kaldırılabilir mi?
5. Service install/upgrade elevation yalnız installer runtime aşamasında bırakılabilir mi?
6. Değişiklik OneDir startup, installer service davranışı, settings/rosalock veya release_check'i etkiler mi?
```

Hedef mimari:

```text
build process             mümkünse normal user
installer/service install gerektiğinde Administrator
```

Bu araştırma model semantics, threshold, weights, K1/K2, scheduler cadence, SHADOW/LIVE veya model version ile ilgili değildir.

## 13. Installer kullanım tercihi

Development deployment'larda kullanıcı installer penceresini görmek istiyor.

Yeni runtime gerçekten deploy edilecekse tercih edilen PowerShell:

```powershell
Start-Process "D:\wamp64\www\Yatirim10YilUygulamasi\InvestmentEngine-v1.2.0-mobile-ready\installer\InvestmentEngineSetup-1.2.0.exe" -Verb RunAs -Wait
```

Sessiz `/VERYSILENT` yöntemini varsayılan kullanma.

Read-only SQL, belge değişikliği veya yalnız analiz için installer çalıştırılmaz.

Deployment sonrası mümkünse doğrula:

```text
installer exit
service Running
StartMode Auto
service PID/start time
installed EXE SHA256 == built EXE SHA256
settings/rosalock preserved
```

## 14. Kod revizyon çalışma biçimi

Bağlayıcı yöntem:

```text
önce mevcut dosya ve mimariyi incele
→ veri akışını anla
→ gereksiz yeni layer/queue/scheduler ekleme
→ mevcut veri akışını koru
→ değişiklikleri yalnız ilgili fonksiyonlarla sınırla
→ model semantiğini istemeden değiştirme
→ focused test
→ full test
→ release check
→ gerekiyorsa gerçek runtime/Supabase doğrulaması
→ değişen/yeni dosyaları açıkça listele
```

Bir sorun kodda zaten çözülmüşse yeniden implement etme. Önce test/runtime evidence ile kapanıp kapanmadığını kontrol et.

`kodlandı`, `test edildi`, `production DB'de doğrulandı`, `runtime deploy edildi`, `ürün kararı olarak onaylandı` durumlarını birbirine karıştırma.

## 15. PowerShell ve GitHub çalışma kuralı

PowerShell komutları doğrudan kopyala-yapıştır güvenli biçimde verilir. Birbirine bağlı komutlar mümkünse tek satırda `;` ile ayrılır. `$LASTEXITCODE` ilgili komuttan hemen sonra yakalanır. `PS ...>` ve `>>` prompt metinleri code block içine yazılmaz.

Migration, service stop/start, production job, installer veya data mutation komutu verilecekse etkisi önceden açıkça anlatılır.

GitHub için:

- yeni değişiklikten hemen önce remote branch ve dosyanın son hali yeniden okunur,
- stale blob SHA üzerinden yazılmaz,
- her mantıksal değişiklik ayrı commit edilir,
- tüm yeni commit mesajları Türkçe olur,
- force push yapılmaz,
- kullanıcı ayrıca istemedikçe master merge/rebase/history rewrite yapılmaz,
- commit/push sonrası short SHA, full SHA ve değişen/yeni dosyalar bildirilir,
- kullanıcıya `git pull --ff-only` komutu verilir.

## 16. Yeni sohbet başlangıç kuralı

Yeni sohbet önce remote `agent/portfolio-audit-reset` HEAD'ini doğrular ve şu kaynakları güncel branch'ten okur:

1. `CHATGPT_PROJECT_START_HERE.md`
2. `InvestmentEngine-v1.2.0-mobile-ready/docs/PROJECT_MEMORY_BANK.md`
3. `InvestmentEngine-v1.2.0-mobile-ready/docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `InvestmentEngine-v1.2.0-mobile-ready/docs/SESSION_HANDOFF.md`
5. `InvestmentEngine-v1.2.0-mobile-ready/docs/INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`
6. `InvestmentEngine-v1.2.0-mobile-ready/docs/SHADOW_CHECKPOINT_LOG.md`
7. ilgili `POST_SHADOW_*.md` kanıt belgeleri
8. değiştirilecek gerçek kod/migration/test dosyaları

Kullanıcının local worktree'si için yalnız kullanıcı çıktısına dayanılır.

Güvenli başlangıç kontrolü:

```powershell
cd D:\wamp64\www\Yatirim10YilUygulamasi; git fetch origin; Write-Host "LOCAL_HEAD=$(git rev-parse --short HEAD)"; Write-Host "REMOTE_HEAD=$(git rev-parse --short origin/agent/portfolio-audit-reset)"; Write-Host "BRANCH=$(git branch --show-current)"; Write-Host "=== STATUS ==="; git status --short
```

## 17. Oturum15 güncel kapanış noktası

Oturum15 başlangıcında remote/local branch senkronizasyonu doğrulandı ve `SESSION_HANDOFF.md` güncel runtime/DB/test kanıtlarıyla reconcile edildi.

Güncel özet:

```text
Model                                  1.2.0 / SHADOW
SHADOW_READINESS                       READY
LIVE                                   NO-GO
Shadow Readiness provenance            CLOSED / VERIFIED
Transactional decision persistence     CLOSED / VERIFIED
URA immutable raw source snapshot P1   CLOSED / VERIFIED
P2.1-P2.7 lifecycle                    CLOSED
Full pytest                            94 PASS
Release check                          OK
Installed runtime identity             VERIFIED
Next technical work                    build.bat Administrator/PyInstaller RCA
Model semantics change                 NONE
```

Bu handoff senkronizasyonu yalnız dokümantasyon değişikliğidir. Yeni build, installer, migration, production job veya model davranışı değişikliği gerektirmez.
