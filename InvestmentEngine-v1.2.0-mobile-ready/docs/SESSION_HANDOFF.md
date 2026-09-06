# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 06 Eylül 2026  
Amaç: Yeni sohbetin güncel proje durumunu konuşma geçmişini yeniden keşfetmeden devralması.

Kalıcı bağlam `PROJECT_MEMORY_BANK.md`, normatif motor gerçeği `SIGNAL_ENGINE_DECISION_CONTRACT.md`, Shadow adımları root `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`, checkpoint kanıtları `SHADOW_CHECKPOINT_LOG.md`, Post-Shadow P0 kanıtları ise `POST_SHADOW_P0_CONNECTION_POOL_RCA.md` ve `POST_SHADOW_P0_RUNTIME_RELIABILITY_CLOSURE.md` içindedir.

## 1. Aktif repo / branch

Ana repo:

```text
nevzataksoy/Yatirim10YilUygulamasi
```

Aktif Python geliştirme branch'i:

```text
agent/portfolio-audit-reset
```

06.09.2026 P0 kapanışı sırasında remote branch üzerinde ardışık olarak oluşturulan güncel commitler:

```text
7b697425a45510a5b6dcbb6bfeb99dbb9f3764f3 — Close development connection pool RCA
0a5a3520a89f3285e88b908a31c512778eec19d0 — Record Post-Shadow P0 runtime reliability closure
```

Bu handoff commit'i branch'i ayrıca ileri taşır. Yeni oturum yazmadan önce remote HEAD ve değiştirilecek dosya blob SHA'sı yeniden doğrulanır.

Repo default branch'i `master` olsa da güncel Shadow/Python çalışması `agent/portfolio-audit-reset` branch'indedir.

Bu çalışma ortamında doğrudan Windows `D:\wamp64\www\Yatirim10YilUygulamasi` worktree'sine erişim yoktur ve geçmiş oturumda shell üzerinden GitHub DNS çözümlemesi başarısız olmuştur. Bu yüzden yerel `git status clean` iddiası yapılmaz. Remote gerçeklik bağlı GitHub üzerinden branch ref, commit ve blob SHA ile doğrulanır. Kullanıcı kendi Windows worktree'sinde gerektiğinde `git pull --ff-only` çalıştırır.

## 2. Değişmez released durum

```text
Model Version        1.2.0
Mode                 SHADOW
Realtime Execution   OFF
SHADOW_READINESS     READY
LIVE Graduation      OPEN / NO-GO for now
```

Released eşikler ve state davranışı değişmemiştir:

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

`direction` emir değildir. `ACTION` tek başına yeni kademe değildir; `action_event=true` gerekir. K1/K2/reversal/reset/sizing davranışı `SIGNAL_ENGINE_DECISION_CONTRACT.md` ile sabittir.

Python portföy bakiyesi okumaz, otomatik exchange order göndermez ve readiness sonucundan otomatik LIVE'a geçmez.

## 3. Shadow görev takvimi sonucu

Görev 1–6: `PASS`.

Görev 7:

```text
Checkpoint              PASS
30 günlük görev takvimi TAMAMLANDI
SHADOW_READINESS        READY
LIVE                    AÇILMADI
Mode                    SHADOW
Realtime Execution      OFF
```

Görev 7 readiness kanıtı:

```text
Shadow calendar days: 36              >= 30
ETH/BTC decision days: 35             >= 25
URA/USD decision days: 25             >= 20
ETH/BTC median quality: 90.83         >= 80
URA/USD median quality: 87.71         >= 80
URA holdings dates: 24                >= 2
URA breadth dates: 24                 >= 20
Recent job success: 99.2126%          >= 98%
Realtime test: OK / 8 snapshots / max_trade_gap=0
waiting_reasons: []
blockers: []
```

Readiness classifier geçti ancak LIVE için kanıt yeterli kabul edilmedi.

## 4. LIVE neden hâlâ NO-GO

Shadow epoch boyunca gerçek ACTION/WATCH davranışı egzersiz edilmedi:

```text
ETH/BTC WAIT: 35 karar / 35 gün
URA/USD WAIT: 33 karar / 24 gün
URA/USD NO_ACTION_DATA: 2 karar / 1 gün
Crypto ACTION/WATCH: 0/0
URA ACTION/WATCH: 0/0
performance: []
```

ETH/BTC historical core replay directional validation sağlıyor fakat production ACTION parity sağlamıyor. Configured edge threshold `70` ile yeterli signal count oluşmadı; bu durum threshold düşürme gerekçesi değildir.

URA full PIT hâlâ yeterli gerçek holdings/breadth/event history taşımıyor.

Bu nedenle `READY` operasyonel readiness anlamındadır; model davranışının production graduation için yeterince egzersiz edildiği anlamına gelmez.

## 5. Post-Shadow P0 — KAPANDI

06.09.2026 itibarıyla development tarafındaki P0 runtime reliability çalışması:

```text
P0 Development Reliability   CLOSED / NON-BLOCKING
```

### 5.1 Connection pool RCA

Detaylı belge:

```text
docs/POST_SHADOW_P0_CONNECTION_POOL_RCA.md
```

Final sınıflandırma:

```text
Development RCA          CLOSED / NON-BLOCKING
Historical 10s timeout   doğrudan yeniden üretilemedi
Production observation   OPEN — GitHub Issue #2
```

Doğrudan lifecycle telemetry şunları doğruladı:

- `connection_expired_on_return` olayları,
- connection age yaklaşık 57–60 dakika,
- replacement connection başarıyla oluşturuluyor,
- pressure sırasında pool headroom mevcut,
- yeni instrumented `checkout_timeout = 0`,
- bad/error/lost connection counter'ları kök nedeni desteklemiyor.

Development host kaynak baskısı connection establishment latency'yi artırabilen makul contributor, fakat historical timeout'un kanıtlanmış root cause'u değildir.

Ayrı bir yaklaşık `14.657s` DB hold gözlendi; düşük checkout wait nedeniyle historical timeout ile otomatik aynı problem sayılmaz.

No-change kararı:

```text
max_size = 6        değişmez
timeout = 10s       değişmez
generic DB retry    eklenmez
scheduler serialize edilmez
model davranışı     değişmez
```

### 5.2 Scheduler ERROR RCA

Detaylı kapanış belgesi:

```text
docs/POST_SHADOW_P0_RUNTIME_RELIABILITY_CLOSURE.md
```

Gerçek `system.job_runs` incelemesi:

#### ID 5 — daily_ura_job

```text
2026-07-30
shadow_epoch_id = null
Alpha Vantage explicit free API rate/quota response
```

Pre-Shadow historical provider-limit olayı; current P0 blocker değil.

#### ID 477 — daily_ura_job

```text
2026-08-08 02:40 TRT
shadow_epoch_id = 1
Alpha Vantage günlük seri bulunamadı.
```

Öncesinde iki OK, sonrasında ardışık OK scheduler çalışmaları var. Bir sonraki çalışma eksik piyasa kapanışını `as_of=2026-08-07`, `WAIT`, quality `87.77` ile üretmiştir.

Collector olay tarihinde zaten request pacing ve explicit `1 request per second` için tek kontrollü retry içeriyordu. Ham historical provider payload'ı saklanmadığından exact cevap kanıtlanamaz.

Doğru sınıflandırma:

```text
isolated unexpected Alpha Vantage response shape
exact historical payload unavailable
next scheduled run recovered automatically
NON-BLOCKING
```

Bu tek olaydan yeni retry/backoff davranışı türetilmez.

#### ID 1642 — sec_event_job

```text
2026-08-29
couldn't get a connection after 10.00 sec
```

Ayrı SEC provider problemi değildir. Historical connection-pool timeout ailesidir ve GitHub Issue #2 production observation debt kapsamındadır.

SEC'in yüzlerce `DEGRADED` kaydı bu ERROR'dan farklıdır; yaklaşık %19–20 exact US SEC ticker fund-weight coverage semantiğini gösterir ve crash değildir.

## 6. Aktif sonraki aşama — P1 Validation Parity / PIT

P0 artık roadmap blocker değildir.

Sıradaki geliştirme aşaması:

```text
P1 — Validation parity / point-in-time evidence
```

Önerilen sıra:

1. gerçek rolling/expanding walk-forward validation kur,
2. aynı piyasa `as_of` tarihindeki tekrar scheduler değerlendirmelerini bağımsız market day gibi sayma,
3. strict FRED vintage / realtime_start-realtime_end PIT erişimini doğrula,
4. production vs replay factor/state/action gap raporu üret,
5. K1/K2/reversal state-machine replay parity'sini released davranışı değiştirmeden ölç,
6. URA full PIT için trustworthy history biriktir veya doğrulanabilir gerçek PIT kaynak araştır.

P1 evidence çalışmasıdır. Şunları otomatik olarak yetkilendirmez:

- threshold değişikliği,
- factor-weight değişikliği,
- K1/K2 değişikliği,
- reversal/reset değişikliği,
- sizing değişikliği,
- yeni model version,
- SHADOW -> LIVE.

## 7. Aynı `as_of` duplicate evaluation notu

URA scheduler kanıtında hafta sonu nedeniyle iki farklı scheduler run'ın aynı `as_of=2026-08-07` kararı ürettiği doğrulandı.

Bu production açısından doğal olabilir; ancak walk-forward/readiness/performance analizlerinde scheduler run count ile distinct market observation day birbirine karıştırılmamalıdır.

P1 tasarımında validation unit açıkça tanımlanmalıdır:

```text
market observation / distinct as_of
```

veya kullanılan başka bir unit ise bunun neden doğru olduğu testlerle kanıtlanmalıdır.

## 8. Veri yaşam döngüsü — P2 açık

FRED current/revision/dedup/retention çözümü hâlâ OPEN araştırma başlığıdır.

Doğrudan `(series_id, observation_date)` UNIQUE migration uygulanmaz. Önce strict PIT/backtest gereksinimi ve mevcut revision history ölçülür.

Uygulanmış `0001` migration geriye dönük değiştirilmez. Silme/dedup migration'ı dry-run/backfill kanıtı olmadan çalıştırılmaz.

## 9. Model davranışı — P3 yalnız ayrı onayla

Aşağıdakiler PROPOSED kalır:

1. kademeler arasında minimum 5 karar seansı,
2. reversal için iki ardışık qualified karşı-yön kapanışı,
3. production/replay için tek versioned state machine,
4. yeni `max_regime_pct` / sizing yaklaşımı,
5. reset sonrası same-direction K1 değişikliği,
6. threshold/factor-weight değişiklikleri.

Bunlardan biri seçilirse açık kullanıcı onayı + yeni model version + test + deploy + yeni Shadow Epoch gerekir. Mevcut v1.2.0 Shadow kanıtı yeni semantiğe otomatik taşınmaz.

## 10. Quasar bağlamı

- Quasar aynı ana repo altında `tr-rosayazilim-yatirimdashboard` dizinindedir.
- Tek Auth kullanıcısı + çoklu portföy mimarisi korunur.
- Account-scoped ledger, append-only revision/cancellation, reset RPC ve connection/Auth hardening mevcut bağlamın parçasıdır.
- Signal/market/validation/health global; portföy işlemleri account scoped.
- Python önerisi hard limit değildir; kullanıcı nihai dönüşüm kararını verir.
- P0/P1 çalışması Quasar'ın bu ürün davranışlarını otomatik değiştirmez.

## 11. Yeni oturum başlangıç protokolü

1. `CHATGPT_PROJECT_START_HERE.md` tamamen oku.
2. `docs/PROJECT_MEMORY_BANK.md`, `docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`, `docs/SESSION_HANDOFF.md` tamamen oku.
3. Python işi ise root görev takvimini ve ilgili P0/P1 belgelerini oku.
4. `RELEASED / APPROVED / PROPOSED / OPEN` ayrımını koru.
5. Remote `agent/portfolio-audit-reset` HEAD ve değiştirilecek blob SHA'yı yeniden doğrula.
6. Kullanıcının son push'ını okumadan yazma yapma.
7. Runtime iddiasını gerçek code/deployment/user output ile kanıtla.
8. Model davranışı değişiyorsa önce açık kullanıcı onayı + version/epoch etkisini belirt.
9. Her mantıksal repo değişikliğini ayrı commit yap ve hemen push et; short SHA, full SHA ve commit mesajını kullanıcıya bildir.
10. Raw telemetry/log dosyalarını commit etme.

## 12. Güvenlik sınırı

API key, parola, Telegram token/Chat ID, DB password veya service-role secret bağlam belgelerine yazılmaz.

Otomatik exchange order, otomatik LIVE ve validation sonucundan otomatik threshold/weight değişikliği yoktur.
