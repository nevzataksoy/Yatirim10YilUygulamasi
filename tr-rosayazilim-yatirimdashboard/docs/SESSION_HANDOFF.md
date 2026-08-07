# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 07 Ağustos 2026  
Amaç: Yeni sohbetin son aktif durumu konuşma geçmişini yeniden keşfetmeden devralması.

Kalıcı bağlam `PROJECT_MEMORY_BANK.md`, normatif motor gerçeği `SIGNAL_ENGINE_DECISION_CONTRACT.md`, Shadow adımları `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`, gerçek checkpoint sonuçları `SHADOW_CHECKPOINT_LOG.md` içindedir.

## 1. Aktif repo/branch'ler

| Repo | Aktif geliştirme branch'i | Durum |
| --- | --- | --- |
| `nevzataksoy/Yatirim10YilUygulamasi` | `agent/portfolio-audit-reset` | Draft PR #1 açık |
| `nevzataksoy/tr.rosayazilim.yatirimdashboard` | `feature/initial-investment-dashboard` | Draft PR #1 açık |

07.08.2026 Görev 4 incelemesine başlanırken doğrulanan remote HEAD'ler:

```text
Python: d37c6a441647ad9df6ae3f51ae19f2f10521cb58 — Revizyon Güncellemesi
Quasar: 68da3673395038c4190567525beabb4f61e51790 — Revizyon sonrası guncelleme commit
```

HEAD değerleri bu belge güncellendikçe değişebilir. Yeni oturum yazmadan önce remote HEAD'i ve değiştireceği dosyanın güncel SHA'sını yeniden doğrular.

## 2. Status disiplini

### RELEASED

- Deployed model `1.2.0`.
- Mode `SHADOW`.
- Realtime Execution `OFF`.
- Minimum quality/edge/confidence `80/70/70`; strong `80/80`.
- `direction` emir değildir.
- `ACTION` tek başına yeni kademe değildir; `action_event=true` gerekir.
- K1/K2/reversal/reset/action-size davranışı `SIGNAL_ENGINE_DECISION_CONTRACT.md` ile sabittir.
- Python portföy bakiyesi okumaz ve otomatik emir göndermez.
- LIVE yalnız bildirim/order-book gözlemidir; READY otomatik LIVE değildir.

### APPROVED

Görev 4 sonrası yalnız davranış değiştirmeyen v1.2.x observability hardening yapılabilir:

- explicit Shadow Epoch,
- scheduled/manual/test/backfill/dependency/maintenance run-kind provenance,
- expected/actual scheduler run accounting,
- completed rate ve strict OK rate'in ayrı görünmesi,
- edge/confidence/quality/status/direction bucket diagnostics.

### PROPOSED

Aşağıdaki model önerileri hâlâ onaylanmış değildir:

1. Kademeler arasında minimum 5 karar seansı.
2. Reversal için iki ardışık qualified karşı-yön kapanışı.
3. Production/replay için tek versioned state machine.
4. `max_regime_pct` UI yönetimi ve yeni sizing formülü.
5. Reset sonrası same-direction K1 davranışının değiştirilmesi.

Bunlar kullanıcı onayı + yeni model version + test + yeni Shadow Epoch olmadan uygulanmaz.

### OPEN

- Görev 4 observability hardening branch üzerinde hazırlanmıştır; gerçek Windows/Supabase deploy kanıtı henüz yoktur.
- Migration `0010_shadow_observability.sql` gerçek DB'ye uygulanmadan `model.shadow_epochs`, `run_kind` ve `shadow_epoch_id` runtime gerçeği değildir.
- Yeni `--shadow-observability` komutu deploy edilip gerçek çıktısı alınmadan official `SHADOW_READINESS` yolu değiştirilmez.
- Gerçek walk-forward, strict FRED-vintage PIT, production/replay parity ve FRED retention/dedup araştırması sonraki görev kapılarındadır.

## 3. Shadow checkpoint özeti

### Görev 1 — PASS

- Scheduler hourly/macro/SEC/daily URA/daily crypto çalıştı.
- ETH/BTC quality yaklaşık `%90,45`, WAIT.
- URA/USD ilk quality `%70,40`, NO_ACTION_DATA.
- Deribit timeout sonrası atomik OKX fallback başarılı.

### Görev 2 — PASS

- TCMB FX işi 16:30 TRT'de çalıştı.
- USD/TRY `47.4305`, FX health/job `OK`.

### Görev 3 — PASS

- Weekly 08:00 TRT, Monthly Audit 09:00 TRT `OK`.
- Core replay `1383` observation.
- Threshold/weight değişmedi.
- `SHADOW_READINESS=NOT_READY`; erken history birikimi nedeniyle beklenen sonuç.

### Görev 4 — PASS

Kullanıcı 07.08.2026 tarihinde bütün 4.1–4.9 çıktıları paylaştı.

Servis/realtime/validation:

```text
Service: RUNNING, exit code 0
Realtime: OK, 8 snapshot, BTC-USD + ETH-USD, max_trade_gap=0
Core replay: OK, 1389 observation
Shadow: NOT_READY, blockers=[]
```

Readiness waiting reasons:

```text
Shadow 9/30 gün
ETH/BTC 9/25 karar günü
URA/USD 6/20 karar günü
URA breadth 6/20 gün
```

Decision quality:

```text
ETH/BTC median 90.83, min 90.08, max 91.20
URA/USD median 87.48, min 70.40, max 87.85
```

Holdings: 6 tarih, çoğu 58 constituent, weight coverage yaklaşık `%99,4–99,9`.

## 4. Görev 4 scheduler teşhisi

Raw son 7 gün sonucu:

```text
hourly_job: 165 OK + 3 ERROR = 168
macro_job: 29 OK
sec_event_job: 169 DEGRADED
crypto: 7 OK
URA: 7 OK
FX: 5 OK
weekly: 1 OK
monthly: 1 OK
model_validation: 1 OK
realtime_test: 1 OK
```

Kritik sonuçlar:

1. `hourly_job` toplamı tam `168 = 7 x 24`. Üç connection-pool hatası gerçek scheduled run hatasıdır; development kaydı diye gizlenmeyecek.
2. Scheduler contract macro için `28`, SEC için `168` root run bekler. Raw tablodaki `+1/+1`, `weekly_job` içindeki child maintenance çağrılarıdır.
3. `model_validation_job` manuel, `realtime_test` test run'ıdır; scheduler reliability paydasında root scheduled run gibi sayılmamalıdır.
4. SEC `DEGRADED` crash değildir; yalnız doğrudan çözümlenen US SEC ticker'larının URA ağırlık kapsamı yaklaşık `%20–21` olduğu için released quality semantiğiyle degraded kalmaktadır.
5. Görev 4 penceresi için shared schedule contract toplam `385` root run hesaplar:

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

## 5. Python branch'inde hazırlanan Task 4 hardening

Davranış değiştirmeyen dosyalar:

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

Temel davranış:

- Scheduler cadence tek `SCHEDULE_SPECS` sözleşmesine taşınır; mevcut saatler değişmez.
- Scheduler root işleri ContextVar ile `scheduled` olarak işaretlenir.
- CLI `--once` = manual, realtime = test, validation = manual, backfill = backfill provenance taşır.
- DB connection local PostgreSQL GUC üzerinden root job/run kind bilgisini migration trigger'ına verir.
- Migration ilk v1.2.0 gerçek karar zamanından `shadow-1.2.0-initial` epoch'unu recover eder.
- Historical weekly child macro/SEC `maintenance`, daily dependency işleri `dependency`, geri kalan scheduler adayları `scheduled_legacy` olarak ayrılır.
- `--shadow-observability` aynı released readiness kriterlerini kullanır ama recent-job paydasını beklenen root scheduler fire'ları ile kurar.
- `OK/DEGRADED/SKIPPED` released completed semantiği korunur; ayrıca strict `OK rate` görünür hale gelir.
- Edge/confidence/quality/status/direction dağılımları yalnız diagnostiktir.
- Çıktı `SHADOW_OBSERVABILITY` validation type'ına yazılır; official `SHADOW_READINESS` rollout sırasında sessizce ezilmez.

Pure test kanıtı:

```text
Task 4 7-day expected schedule: 385 root run
hourly 168 / macro 28 / SEC 168 / crypto 7 / URA 7 / FX 5 / weekly 1 / monthly 1
run-context restore test: PASS
```

Bu test gerçek Windows build/Supabase integration testi değildir; runtime kanıtı `OPEN` kalır.

## 6. Deployment sınırı

Bu branch değişiklikleri source-level hardening'dir. Deployed sunucunun halen v1.2.0 eski binary'sini çalıştırdığı varsayılır; kullanıcı gerçek build/deploy çıktısı vermeden yeni observability runtime'da var kabul edilmez.

Rollout istendiğinde sıra:

1. Remote HEAD'i yeniden doğrula/pull et.
2. Windows release ortamında compile + pytest + release check + build çalıştır.
3. Migration `0010`u Supabase'e uygula.
4. Yeni EXE/setup'ı aynı `SHADOW` ve `Realtime Execution=OFF` ile deploy et.
5. Servisin `RUNNING` olduğunu doğrula.
6. Çalıştır:

```bat
InvestmentEngineCLI.cmd --shadow-observability
```

7. `SHADOW_OBSERVABILITY` ile raw Task 4 job sayıları ve existing `SHADOW_READINESS` sonucunu karşılaştır.
8. Üç hourly ERROR scheduled olarak kalmalı; weekly child macro/SEC maintenance olmalı; manual/test satırları scheduler paydasından çıkmalı.
9. Ancak bu runtime kanıtı geçerse official readiness entegrasyonu ayrıca değerlendirilebilir.

Bu rollout model version değiştirmez ve mevcut Shadow kanıtını sıfırlamaz; çünkü decision semantics değişmemektedir.

## 7. Quasar güncel durumu

- Aktif branch `feature/initial-investment-dashboard`.
- Tek Auth kullanıcısı + çoklu portföy.
- Account-scoped ledger, SecureLS/Pinia seçili hesap, append-only revision/cancellation, reset RPC, connection/Auth hardening mevcut.
- Signal/market/validation/health global; portföy işlemleri hesap scoped.
- Signal→Conversion seçim UX'i henüz OPEN; Python önerisi hard limit değildir.
- Supabase portföy migration `0008` ve `0009` uygulanmış olarak belgelenmiştir; yeni Python observability migration numarası `0010`dur.
- Bu Görev 4 turunda Quasar ürün davranışı değiştirilmemiştir; yalnız ortak handoff bağlamı senkron tutulabilir.

## 8. Sonraki görevler

### Görev 5 — 14.08.2026

14 günlük stabilite. Mevcut 4.4–4.9 sorgularına ek olarak, observability hardening deploy edilmişse `--shadow-observability` çıktısı da alınır. Deploy edilmemişse mevcut released komutlarla görev devam eder; hardening eksikliği Shadow motoru durdurma gerekçesi değildir.

### Görev 6 — 20.08.2026

URA 20 günlük quality/history değerlendirmesi.

### Görev 7 — 29.08.2026

30 günlük manual Shadow Graduation Review. READY otomatik LIVE değildir.

Görev 5–6 sonrasında gerçek walk-forward/strict PIT araştırması; Görev 7 sonrasında FRED tekilleştirme/retention karşılaştırması yapılır. Threshold değişikliği halen yasaktır.

## 9. Yeni oturumun ilk eylemi

1. `CHATGPT_PROJECT_START_HERE.md` tamamen oku.
2. `docs/PROJECT_MEMORY_BANK.md`, `docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`, `docs/SESSION_HANDOFF.md` tamamen oku.
3. Python işi ise görev takvimi, `docs/SHADOW_CHECKPOINT_LOG.md` ve `docs/SHADOW_TASK4_HARDENING.md` dosyalarını oku.
4. RELEASED/APPROVED/PROPOSED/OPEN ayrımını koru.
5. İki remote branch'in HEAD'ini yeniden doğrula.
6. Kullanıcının son push'ını okumadan dosya değiştirme.
7. Runtime iddiası için gerçek kod veya kullanıcı çıktısı göster.
8. Proje durumu değişirse handoff; kalıcı karar değişirse memory/contract iki repoda senkron güncellenir.

## 10. Güvenlik sınırı

API key, parola, Telegram token/Chat ID, DB password veya service-role secret hiçbir bağlam belgesine yazılmaz. Otomatik emir, otomatik LIVE ve validation sonucundan otomatik threshold/weight değişikliği yoktur.
