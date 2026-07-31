# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 01 Ağustos 2026  
Amaç: Yeni sohbetin son aktif durumu konuşma geçmişini yeniden keşfetmeden devralması.

Kalıcı bağlam `PROJECT_MEMORY_BANK.md`, normatif motor gerçeği `SIGNAL_ENGINE_DECISION_CONTRACT.md`, Shadow adımları görev takvimi, sonuçlar `SHADOW_CHECKPOINT_LOG.md` içindedir.

## 1. Aktif repo/branch'ler

| Repo | Aktif geliştirme branch'i | Durum |
| --- | --- | --- |
| `nevzataksoy/Yatirim10YilUygulamasi` | `agent/portfolio-audit-reset` | Draft PR #1 açık |
| `nevzataksoy/tr.rosayazilim.yatirimdashboard` | `feature/initial-investment-dashboard` | Draft PR #1 açık |

HEAD değerleri bu belge güncellendikçe değişir. Yeni oturum her zaman remote HEAD ve değiştireceği dosyanın güncel SHA'sını yeniden doğrular.

## 2. Bu oturumda yapılan bağlam düzeltmesi

İki repodaki başlangıç/memory/contract/handoff belgeleri, gerçek v1.2.0 kodu ve tarihsel hotfix belgeleriyle yeniden karşılaştırıldı.

Düzeltilen ana noktalar:

1. Önceki memory bank mobile-ready kapsamını yanlış biçimde v1.1.1'e topluyordu. Doğru sıra:
   - v1.1.0 mobile-ready temel paket,
   - v1.1.1 gerçek Windows/Supabase smoke-test hotfix'i.
2. `PIT_CORE_REPLAY` kod/DB etiketi strict FRED-vintage PIT değildir. Ürün yorumu historical as-of directional-core replay olarak düzeltildi.
3. v1.2.0 calibration gerçek expanding/multi-fold walk-forward değil, tek `%70 train / %30 holdout` keşif raporudur.
4. Replay'in production quality/confidence/event kapıları ve persistent K1/K2 state machine'iyle parity sağlamadığı açıklaştırıldı.
5. Runtime factor weights kaynağının `config/defaults.json` olduğu; `model.factor_weights` tablosunun v1.2.0 runtime tarafından okunmadığı kaydedildi.
6. Shadow kriterleri migration ile `model.parameters`a seed edilse de v1.2.0 readiness kodunun hard-coded defaults kullandığı kaydedildi.
7. Aylık DCA ile dönüşüm motoru ayrıldı: motor DCA'yı durduran veya otomatik portföy yöneten bir robot değildir.
8. `direction`, `ACTION`, `action_event`, `recommended_size` ve `action_size` kavramları birbirinden ayrıldı.
9. Ham veri → feature → regime → factor → edge/confidence → veto/risk → status → K1/K2 → Supabase tablo zinciri formülleriyle belgelendi.
10. Görev 4–7 sonrasındaki observability, strict PIT, gerçek walk-forward ve manual graduation kilometre taşları netleştirildi.

Bu tur yalnız dokümantasyon düzeltmesidir. Python model/app kodu, Quasar uygulama kodu, migration, threshold veya factor weight değiştirilmedi. Bu dokümantasyon turu için yeni build/test çalıştırıldığı iddia edilmez.

## 3. Python Engine — güncel doğrulanmış operasyon durumu

- Deployed model: **v1.2.0**.
- Windows Service: `RosaInvestmentEngine`, Automatic / Local System.
- Son kullanıcı kanıtı: `STATE : 4 RUNNING`, exit code `0`.
- Mode: `SHADOW`.
- Realtime Execution: `OFF`.
- Crypto history: Coinbase, 2500 ortak gün, `OK`.
- Validation: 1381 historical as-of directional-core observation, core `OK`.
- Configured edge `70` için replay signal sayısı `0`; düşük aday eşiklerde signal count sınırlı.
- Calibration exploratory; hiçbir threshold/weight uygulanmadı.
- URA full replay yeterli PIT history olmadığı için `NOT_READY`.

## 4. Shadow checkpoint'leri

### Görev 1 — `PASS`

- Scheduler hourly, macro, SEC, daily URA ve daily crypto işlerini otomatik çalıştırdı.
- ETH/BTC: `BTC→ETH`, edge `35.640`, confidence `46.250`, quality `90.450`, `WAIT`.
- URA/USD: `URA→USD`, edge `33.990`, confidence `36.170`, quality `70.400`, `NO_ACTION_DATA`.
- Deribit timeout → atomik OKX fallback; derivatives job `OK`.
- Macro quality `97.5`.
- SEC coverage `%14.04`, `DEGRADED`; job çökmemiştir.

### Görev 2 — `PASS`

- 31.07.2026 16:30 TRT TCMB işi zamanında çalıştı.
- Data date `31.07.2026`, USD/TRY `47.4305`.
- FX health/job/snapshot zinciri tutarlı.

### Görev 3 — `PENDING`

**01.08.2026 09:30 TRT weekly + monthly audit** çıktısı henüz bu oturumda paylaşılmadı. İstenen kanıt:

1. `weekly_job` ve `monthly_audit_job` son kayıtları.
2. `public.model_validation_snapshot`.
3. Son `model.validation_runs` kayıtları.

Sonuç görülmeden PASS yazılmaz. `SHADOW_READINESS=NOT_READY` bu aşamada normaldir.

## 5. Released motor gerçeği

- Minimum quality/edge/confidence `80/70/70`; strong `80/80`.
- Yön label'i emir değildir.
- `ACTION` günlük model status'udur; yeni kademe için `action_event=true` gerekir.
- K1 ilk qualified ACTION'da oluşabilir.
- K2 aynı yön + farklı `as_of` + edge/confidence `80/80` ister.
- K2 için 5-session şartı yoktur.
- Qualified karşı-yön ACTION rejimi hemen çevirebilir.
- Beş zayıf karar aktif state'i resetleyebilir.
- Cumulative regime cap `%50`dir.
- Python portföy bakiyesi okumaz ve otomatik emir göndermez.
- LIVE yalnız bildirim/order-book gözlemidir.

## 6. Onay bekleyen model önerileri

Aşağıdakiler `PROPOSED/OPEN` kalır:

1. Kademeler arasında en az 5 karar seansı.
2. Reversal için iki ardışık qualified karşı-yön kapanışı.
3. Production ve replay için tek versioned state machine.
4. Python action size ile Quasar kullanıcı limitinde kalan payın `min(...)` sözleşmesi.

Bunlar kullanıcı kararı, yeni model version, test ve yeni Shadow Epoch olmadan uygulanmaz.

## 7. Görevlerden sonra Python yol haritası

### Görev 4 sonrası — davranış değiştirmeyen v1.2.x

- explicit Shadow Epoch,
- run-kind ayrımı,
- expected/actual scheduler run,
- OK/completed rate,
- edge/confidence/quality/status bucket diagnostics,
- mevcut K1/K2/reversal/reset davranışını karakterize eden unit testler,
- JSON/DB runtime configuration authority görünürlüğü.

### Görev 5–6 sonrası

- gerçek expanding/rolling walk-forward,
- strict FRED-vintage PIT,
- production/replay gap/parity raporu,
- URA fundamentals/breadth/event quality decomposition.

### Görev 7

Scheduler, Shadow dağılımları, realtime, historical replay, walk-forward, monthly realized ve URA history birlikte manuel review edilir. READY otomatik LIVE değildir. Model semantiği değişirse yeni version ve yeni Shadow Epoch gerekir.

## 8. Quasar — güncel ürün durumu

- Tek Auth kullanıcısı altında çoklu portföy hesabı.
- Global seçili hesap ve account-scoped ledger.
- Seçili hesap/display asset SecureLS/Pinia persistence.
- Dashboard, Portföy, İşlemler, Raporlar ve girişler seçili hesap bazlı.
- Sinyal/market/validation/health global.
- `AppPopupSelect.vue` select standardı.
- Append-only transaction revision/cancellation ve kronolojik bakiye replay kontrolü.
- Kontrollü seçili-portföy reset RPC'si.
- İşlem formlarında önce/işlem/sonra bakiye bağlamı.
- Login ve Settings bağlantı alanlarında yerel ayar şifresi; açık parola saklanmaz.
- Supabase migration `0008` ve `0009` uygulanmış olarak belgelenmiştir; yeni migration `0010+` olmalıdır.

## 9. Quasar'da kullanıcı doğrulaması bekleyen işler

1. `docs/DEMO_TEST_SCENARIO_100K_TRY.md` içindeki 12 işlemi sırayla uygula.
2. İlk bakiye/hesap sapmasında zinciri durdurup ekran görüntüsü paylaş.
3. Sonunda Dashboard, Portföy, İşlem Geçmişi ve Raporlar toplamlarını beklenen matematikle karşılaştır.
4. Draft PR test tamamlanmadan merge edilmez.
5. Sonraki production-readiness işi Auth/connection lifecycle'dır.
6. Signal→Conversion yönlendirmesi, action-size/user-limit semantiği kesinleşmeden otomatik yüzde önermemelidir.

## 10. Yeni oturumun ilk eylemi

1. Zorunlu dört belgeyi tamamen oku.
2. Python işi ise görev takvimi ve checkpoint logunu oku.
3. `RELEASED/APPROVED/PROPOSED/OPEN` ayrımını doğrula.
4. İki remote branch'in güncel HEAD'ini yeniden kontrol et.
5. Kullanıcının son push'ını okumadan dosya değiştirme.
6. Runtime iddiası için gerçek kod veya kullanıcı çıktısı göster.
7. Proje durumu değişirse bu handoff'u; kalıcı karar değişirse memory/contract'ı iki repoda senkron güncelle.

## 11. Güvenlik sınırı

API key, parola, Telegram token/Chat ID, DB password veya service-role secret hiçbir bağlam belgesine yazılmaz. Otomatik emir, otomatik LIVE ve validation sonucundan otomatik threshold/weight değişikliği yoktur.
