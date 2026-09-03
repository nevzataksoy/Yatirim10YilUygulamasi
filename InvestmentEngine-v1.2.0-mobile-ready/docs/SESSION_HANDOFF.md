# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 04 Eylül 2026  
Amaç: Yeni sohbetin son aktif durumu konuşma geçmişini yeniden keşfetmeden devralması.

Kalıcı bağlam `PROJECT_MEMORY_BANK.md`, normatif motor gerçeği `SIGNAL_ENGINE_DECISION_CONTRACT.md`, Shadow adımları `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`, gerçek checkpoint sonuçları `SHADOW_CHECKPOINT_LOG.md` içindedir.

## 1. Aktif repo/branch

Ana repo:

```text
nevzataksoy/Yatirim10YilUygulamasi
```

Aktif Python geliştirme branch'i:

```text
agent/portfolio-audit-reset
```

04.09.2026 Oturum 8 başlangıcında GitHub remote üzerinde doğrulanan HEAD:

```text
01a341260168dc573f2986362a98a2353e83e164 — Görev 7 adımları tamamlandı.
```

Repo default branch'i `master` olsa da güncel Shadow/Python çalışması `agent/portfolio-audit-reset` branch'indedir. Yeni oturum yazmadan önce remote HEAD ve değiştirilecek dosya SHA'sı yeniden doğrulanır.

Bu çalışma ortamında doğrudan `git clone/pull` sırasında `github.com` DNS çözümlemesi başarısız olabildiği için yerel worktree temizliği kanıtlanmadan `git status clean` iddiası yapılmaz. Böyle bir durumda bağlı GitHub üzerinden remote ref, commit ve blob SHA'ları doğrulanır ve yazma işlemleri yalnız güncel remote HEAD üzerine force kullanmadan yapılır.

## 2. Status disiplini

### RELEASED

- Deployed model `1.2.0`.
- Mode `SHADOW`.
- Realtime Execution `OFF`.
- Minimum quality/edge/confidence `80/70/70`; strong edge/confidence `80/80`.
- `direction` emir değildir.
- `ACTION` tek başına yeni kademe değildir; `action_event=true` gerekir.
- K1/K2/reversal/reset/action-size davranışı `SIGNAL_ENGINE_DECISION_CONTRACT.md` ile sabittir.
- Python portföy bakiyesi okumaz ve otomatik exchange order göndermez.
- LIVE yalnız bildirim/order-book gözlem katmanıdır; `READY` otomatik LIVE değildir.
- Released `SHADOW_READINESS` kriterleri 03.09.2026 validation çalışmasında ilk kez topluca `READY` üretmiştir.

### APPROVED

- `READY` yalnız manuel graduation review kapısıdır; otomatik mode değişimi yoktur.
- Model davranışını değiştirmeyen v1.2.x observability/hardening çalışmaları yapılabilir.
- Explicit Shadow Epoch, run-kind provenance, scheduler expected/actual accounting ve diagnostic bucket yaklaşımı onaylı davranış-korumalı hardening yönüdür.
- Görev 7 sonrası FRED current/revision tekilleştirme ve retention araştırması davranışı değiştirmeyen veri yaşam döngüsü çalışması olarak sürdürülebilir.

### PROPOSED

Aşağıdaki model davranışı önerileri hâlâ onaylanmış değildir:

1. Kademeler arasında minimum 5 karar seansı.
2. Reversal için iki ardışık qualified karşı-yön kapanışı.
3. Production/replay için tek versioned state machine.
4. `max_regime_pct` UI yönetimi ve yeni sizing formülü.
5. Reset sonrası same-direction K1 davranışının değiştirilmesi.
6. Threshold/factor-weight değişiklikleri.

Bunlar açık kullanıcı onayı + yeni model version + test + deploy + yeni Shadow Epoch olmadan uygulanmaz. Mevcut Shadow kanıtı yeni model semantiğine otomatik taşınmaz.

### OPEN

- `SHADOW -> LIVE` graduation kararı.
- Görev 4 observability hardening'in gerçek Windows/Supabase deployment kanıtı, eğer henüz prod Shadow binary'de doğrulanmadıysa.
- Son 30 gündeki gerçek scheduler ERROR kayıtlarının kök neden analizi.
- Gerçek rolling/expanding walk-forward validation.
- Strict FRED-vintage point-in-time katmanı.
- Production/replay state-parity gap analizi.
- URA full PIT replay için yeterli gerçek holdings/breadth/event tarihçesi.
- FRED current/revision retention/dedup çözümünün seçimi ve kontrollü migration/backfill planı.

## 3. Shadow görev takvimi özeti

### Görev 1 — PASS

- Scheduler ilk otomatik işleri çalıştırdı.
- ETH/BTC quality yaklaşık `%90`, WAIT.
- URA/USD ilk quality `%70,40`, NO_ACTION_DATA.

### Görev 2 — PASS

- TCMB FX scheduler işi başarılı.
- FX health/job `OK`.

### Görev 3 — PASS

- Weekly ve Monthly Audit scheduler çalıştı.
- Core replay çalıştı.
- Threshold/weight değişmedi.
- Erken history nedeniyle `SHADOW_READINESS=NOT_READY` beklenen sonuçtu.

### Görev 4 — PASS

- Servis `RUNNING`.
- Realtime test `OK`, 8 snapshot, `max_trade_gap=0`.
- Core validation `OK`.
- Readiness blocker yoktu; yalnız gözlem/history süresi eksikti.
- Üç `hourly_job` connection-pool ERROR gerçek scheduled hata olarak teşhis edildi.
- Raw macro/SEC sayılarındaki `+1` weekly child maintenance çağrılarından geliyordu.
- Davranış değiştirmeyen observability hardening branch üzerinde hazırlandı.

### Görev 5 — PASS

19.08.2026 checkpoint'i:

```text
Service: RUNNING
Realtime: OK / 8 snapshot / max_trade_gap=0
Core: OK / 1401 observations
Shadow: NOT_READY
Calendar: 21/30
ETH/BTC days: 21/25
URA days: 14/20
URA breadth: 13/20
ETH/BTC median quality: 90.95
URA median quality: 87.71
Job success: %99.48
Blockers: []
```

İki gerçek hourly connection-pool hatası izleme borcu olarak korundu; threshold/model semantiği değiştirilmedi.

### Görev 6 — PASS

23.08.2026 checkpoint'i:

```text
Service: RUNNING
Core: OK / 1405 observations
Shadow: NOT_READY
Calendar: 25/30
ETH/BTC days: 25/25
URA days: 17/20
URA breadth: 17/20
URA holdings: 17
ETH/BTC median quality: 90.83
URA median quality: 87.71
Job success: %99.74
Blockers: []
```

URA median quality `>=80` olduğu için görev karar ağacına göre Shadow değiştirilmeden devam etti.

### Görev 7 — CHECKPOINT PASS / LIVE OPEN

Görev 7 çıktıları kullanıcı tarafından 03.09.2026 tarihinde tamamlandı ve repo commitine işlendi.

Servis/realtime/validation:

```text
Service: RUNNING, exit code 0
Realtime: OK, 8 snapshot, BTC-USD + ETH-USD, max_trade_gap=0
Validation: core=OK, observations=1416
SHADOW_READINESS: READY
```

Released readiness ölçümleri:

```text
Shadow calendar days: 36              >= 30
ETH/BTC decision days: 35             >= 25
URA/USD decision days: 25             >= 20
ETH/BTC median quality: 90.83         >= 80
URA/USD median quality: 87.71         >= 80
URA holdings dates: 24                >= 2
URA breadth dates: 24                 >= 20
Recent job success: 99.2126%          >= 98%
Realtime test age: ~0.0017 days       <= 7 days
waiting_reasons: []
blockers: []
```

Bu nedenle released readiness classifier açısından Görev 7 checkpoint'i `PASS` ve `READY`dir.

Ancak `READY`, LIVE'a geçiş kararı değildir. Görev 7 manual graduation review sonucu mevcut kanıtla:

```text
Checkpoint: PASS
Readiness gate: READY
LIVE graduation: OPEN / NO-GO for now
Mode: SHADOW korunur
Realtime Execution: OFF korunur
```

## 4. Görev 7'de LIVE'ı açık bırakma gerekçesi

### 4.1 Shadow döneminde action davranışı hiç egzersiz edilmedi

Karar özeti:

```text
ETH/BTC WAIT: 35 karar / 35 gün
URA/USD WAIT: 33 karar / 24 gün
URA/USD NO_ACTION_DATA: 2 karar / 1 gün
Crypto ACTION/WATCH: 0/0
URA ACTION/WATCH: 0/0
performance: []
```

Dolayısıyla mevcut 36 günlük epoch veri kalitesi ve scheduler güvenilirliğini ölçüyor, fakat gerçek ACTION, K1/K2, reversal ve mature realized-performance davranışını kanıtlamıyor.

### 4.2 ETH/BTC historical core replay threshold kanıtı üretmedi

`PIT_CORE_REPLAY`:

```text
Status: OK
Period: 2022-10-18 .. 2026-09-02
Observations: 1416
Median replay data quality: 75
Configured edge threshold: 70
Signals @ 5/20/60 sessions: 0 / 0 / 0
Calibration: LIMITED_SIGNAL_COUNT
best_candidate: null
auto_apply: false
```

65/70/75/80 aday eşiklerinde train ve holdout sinyali yoktur. 60 eşiğinde yalnız 1 train sinyali, 55 ve 50 eşiklerinde de çok az örnek vardır. Bu çıktı threshold düşürme gerekçesi değildir.

Ayrıca replay derivatives/event için trustworthy historical PIT içermediğinden directional core validation'dır; production ACTION parity değildir.

### 4.3 URA full PIT hâlâ hazır değil

`PIT_FULL_REPLAY / URA/USD`:

```text
Status: NOT_READY
holdings_dates: 24
breadth_dates: 24
reason: holdings/breadth/event tarihçesi full PIT replay için yetersiz
```

URA tarafında production-quality historical validation kanıtı oluşmadan LIVE graduation tamamlanmış sayılmaz.

### 4.4 Scheduler başarı oranı gate'i geçiyor, fakat gerçek ERROR borcu var

Son 30 günlük raw özet:

```text
daily_crypto_job: 29 OK
daily_fx_job: 22 OK
daily_ura_job: 29 OK / 1 ERROR
hourly_job: 713 OK / 5 ERROR
macro_job: 123 OK
model_validation_job: 4 OK
monthly_audit_job: 1 OK
realtime_test: 3 OK
sec_event_job: 721 DEGRADED / 1 ERROR
weekly_job: 4 OK
```

Released readiness job success oranı `%99.21` ile `%98` kapısını geçmektedir. Buna rağmen gerçek ERROR kayıtları silinmez veya development artığı sayılmaz. Görülen hourly hata örneği:

```text
couldn't get a connection after 10.00 sec
```

`daily_ura_job` ve `sec_event_job` için tekil ERROR kayıtlarının kesin kök nedeni ayrıca incelenecektir.

SEC `DEGRADED` kayıtlarının büyük çoğunluğu crash değildir; doğrudan çözümlenen US SEC ticker'larının URA fund-weight kapsamı yaklaşık `%19–20` seviyesinde olduğu için mevcut quality semantiğiyle degraded görünür. Bu durum coverage borcudur, threshold değiştirme gerekçesi değildir.

## 5. Görev takvimi sonrası Python teknik borç planı

Görev 7 ile 30 günlük görev takvimi operasyonel olarak tamamlandı. Görev takvimi boyunca ertelenen runtime/model revizyonları bu checkpoint commitinde uygulanmaz; önce kanıt ve kök neden çalışmaları ayrılır.

### P0 — Runtime güvenilirliği, model semantiğine dokunmadan

1. 5 `hourly_job` connection-pool ERROR kaydının ortak kök nedenini çıkar.
2. Tek `daily_ura_job ERROR` ve tek `sec_event_job ERROR` kaydını ayrı incele.
3. Connection-pool kullanım süresi, saturation, timeout ve call-site provenance görünürlüğünü artır.
4. Gerekliyse idempotent safe-retry/backoff tasarla; karar semantiği veya scheduler cadence'i sessizce değiştirme.
5. Task 4 observability migration/binary runtime'da doğrulanmadıysa önce `0010` + `--shadow-observability` rollout kanıtını kapat.

### P1 — Validation parity ve PIT kanıtı

1. Tek 70/30 split yerine gerçek rolling/expanding walk-forward validation kur.
2. FRED macro için strict vintage/realtime_start-realtime_end point-in-time erişimini doğrula.
3. Production vs replay factor/state/action gap raporu üret.
4. K1/K2/reversal state machine replay parity'si model değişikliği yapmadan ölçülebilir hale getir.
5. URA full PIT için gerçek historical holdings/breadth/event coverage biriktir veya güvenilir kaynakla geriye dönük olarak doğrulanabilir gerçek PIT veri sağla; sentetik history üretme.

### P2 — Veri yaşam döngüsü / FRED hardening

1. FRED current-revision ve vintage kayıt modelini ölç.
2. `(series_id, observation_date)` current görünümü ile revision history'yi ayıran seçenekleri karşılaştır.
3. Retention matrix, storage büyümesi, idempotency ve backtest gereksinimlerini birlikte değerlendir.
4. Dry-run/backfill doğrulaması olmadan silme/dedup migration'ı çalıştırma.
5. Uygulanmış `0001` migration'ı geriye dönük değiştirme.

### P3 — Model davranışı değişiklikleri yalnız ayrı onayla

Aşağıdakiler bu teknik borç planında otomatik uygulama değildir:

- 5 karar seansı minimum kademe aralığı,
- iki qualified opposite close ile reversal,
- reset sonrası same-direction K1 davranışı,
- yeni sizing / `max_regime_pct`,
- threshold/factor-weight değişiklikleri.

Bunlardan biri seçilirse yeni model version, migration/provenance, test, deploy ve yeni Shadow Epoch gerekir.

## 6. Görev 4 observability hardening notu

Branch üzerinde hazırlanan davranış-korumalı yapı:

```text
app/run_context.py
app/schedule_contract.py
app/observability.py
app/database/db.py
app/scheduler.py
run.py
migrations/0010_shadow_observability.sql
supabase-migrations/0010_shadow_observability.sql
tests/test_shadow_observability.py
docs/SHADOW_TASK4_HARDENING.md
docs/SHADOW_CHECKPOINT_LOG.md
```

Shared Task 4 scheduler contract 7 günlük pencere için `385` root run hesaplar:

```text
hourly 168
macro 28
SEC 168
crypto 7
URA 7
FX 5
weekly 1
monthly 1
```

Gerçek Windows build/Supabase migration/runtime çıktısı kullanıcı tarafından ayrıca kanıtlanmadıysa source-level hardening deployed gerçeklik olarak işaretlenmez.

## 7. Quasar bağlamı

- Quasar aynı ana repo altında `tr-rosayazilim-yatirimdashboard` dizinindedir.
- Tek Auth kullanıcısı + çoklu portföy mimarisi korunur.
- Account-scoped ledger, append-only revision/cancellation, reset RPC ve connection/Auth hardening mevcut bağlamın parçasıdır.
- Signal/market/validation/health global; portföy işlemleri account scoped.
- Python önerisi hard limit değildir; kullanıcı nihai dönüşüm kararını verir.
- Görev 7 değerlendirmesi Quasar ürün davranışını değiştirmez.

## 8. Yeni oturumun ilk eylemi

1. `CHATGPT_PROJECT_START_HERE.md` tamamen oku.
2. `docs/PROJECT_MEMORY_BANK.md`, `docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`, `docs/SESSION_HANDOFF.md` tamamen oku.
3. Python işi ise root görev takvimini ve ilgili Shadow hardening/checkpoint belgelerini oku.
4. `RELEASED / APPROVED / PROPOSED / OPEN` ayrımını koru.
5. Remote `agent/portfolio-audit-reset` HEAD'ini ve değiştireceğin dosyanın blob SHA'sını yeniden doğrula.
6. Kullanıcının son push'ını okumadan dosya değiştirme.
7. Runtime iddiası için gerçek kod/deployment veya kullanıcı çıktısı göster.
8. Model davranışı değişiyorsa önce açık kullanıcı onayı ve yeni Shadow Epoch etkisini belirt.
9. Proje durumu değişirse handoff; kalıcı normatif karar değişirse memory/contract senkron güncellenir.

## 9. Güvenlik sınırı

API key, parola, Telegram token/Chat ID, DB password veya service-role secret hiçbir bağlam belgesine yazılmaz. Otomatik exchange order, otomatik LIVE ve validation sonucundan otomatik threshold/weight değişikliği yoktur.
