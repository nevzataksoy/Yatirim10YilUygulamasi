# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 01 Ağustos 2026 00:44 TRT  
Amaç: Yeni sohbetin son aktif durumu konuşma geçmişini yeniden keşfetmeden devralması.

Kalıcı kararlar `PROJECT_MEMORY_BANK.md`, normatif motor davranışı `SIGNAL_ENGINE_DECISION_CONTRACT.md`, Shadow adımları `INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`, sonuç geçmişi `SHADOW_CHECKPOINT_LOG.md` içindedir.

## 1. Son doğrulanan repo durumu

| Repo | Aktif branch | Bu handoff öncesi doğrulanan HEAD | PR |
| --- | --- | --- | --- |
| `nevzataksoy/Yatirim10YilUygulamasi` | `agent/portfolio-audit-reset` | `0a4a40c` | Draft PR #1 |
| `nevzataksoy/tr.rosayazilim.yatirimdashboard` | `feature/initial-investment-dashboard` | `1ab1018` | Draft PR #1 |

Bu dosya güncellenince branch HEAD değişir. Yeni oturum her zaman remote branch'i yeniden okuyup güncel HEAD'i doğrular; bu tabloda yazan SHA'yı körlemesine kullanmaz.

## 2. Python Engine — güncel operasyon durumu

- Yayımlanmış/deploy edilmiş model: **v1.2.0**.
- Windows Service: `RosaInvestmentEngine`, Automatic / Local System.
- Son doğrulama: `STATE : 4 RUNNING`, exit code `0`.
- Mode: `SHADOW`.
- Realtime Execution: `OFF`.
- Crypto history backfill: Coinbase, 2500 ortak gün, `OK`.
- Validation: 1381 observation, directional core `OK`, Shadow `NOT_READY`.
- Calibration exploratory ve limited-signal; hiçbir threshold otomatik uygulanmadı.
- URA full PIT history yeterli olmadığı için `NOT_READY` olabilir.

## 3. Doğrulanmış Shadow checkpoint'leri

### Görev 1 — ilk otomatik günlük döngü: `PASS`

- Servis gece boyunca çalışmaya devam etti.
- Scheduler hourly, macro, SEC, daily URA ve daily crypto işlerini otomatik çalıştırdı.
- ETH/BTC: `BTC→ETH`, edge `35.640`, confidence `46.250`, quality `90.450`, `WAIT`.
- URA/USD: `URA→USD`, edge `33.990`, confidence `36.170`, quality `70.400`, `NO_ACTION_DATA`.
- Deribit timeout → OKX fallback; derivatives job `OK`.
- Macro quality `97.5`.
- SEC coverage `%14.04` → `DEGRADED`, fakat scheduler/job çökmemiştir.
- Karar: servis SHADOW kalır; threshold/weight/mode değişmez; job'lar manuel tekrarlanmaz.

### Görev 2 — TCMB/FX: `PASS`

- 31.07.2026 16:30 TRT planı doğru çalıştı.
- Data date `31.07.2026`, USD/TRY `47.4305`.
- `FX=OK`, job `OK`, süre yaklaşık `2.48 s`.
- Snapshot, health ve job audit tutarlı.

### Sıradaki checkpoint

**Görev 3 — 01.08.2026 09:30 TRT**

Kullanıcı şu üç çıktıyı paylaşmalıdır:

1. `weekly_job` ve `monthly_audit_job` son kayıtları.
2. `public.model_validation_snapshot`.
3. Son `model.validation_runs` kayıtları.

`SHADOW_READINESS=NOT_READY` bu aşamada normaldir. Sonuç paylaşılmadan görev başarılı sayılmaz.

## 4. Görev 4 sonrasında planlanan davranış değiştirmeyen Python hardening

- Açık `shadow_epoch_id` / `shadow_started_at`.
- `scheduled/manual/backfill/development` run-kind ayrımı.
- Beklenen ve gerçekleşen scheduler run sayısı.
- `OK rate` ile `completed rate` ayrımı.
- Edge/confidence/quality/status/direction bucket diagnostics.
- Mevcut v1.2.0 K1/K2 davranışını karakterize eden unit testler.

Bunlar v1.2.x observability/readiness hardening olabilir; threshold, factor yönü veya K1/K2 semantiği sessizce değiştirilemez.

## 5. Model davranışında açık kararlar

Released gerçek:

- Minimum quality/edge/confidence `80/70/70`, strong `80/80`.
- Persistent K1/K2 ve `%50` cumulative cap var.
- K2 farklı tarih + strong `80/80` ister; 5 seans şartı yok.
- Karşı yön qualified `ACTION` rejimi hemen çevirebilir.
- PIT replay production state machine'ini birebir kullanmaz.
- Python action size ve Quasar kullanıcı yüzdesi otomatik birleşmez.

Kullanıcı onayı bekleyen öneriler:

1. Kademeler arası en az 5 karar seansı.
2. Reversal için iki ardışık qualified kapanış.
3. Production ve replay için tek versioned state machine.
4. Python önerisi ile Quasar maksimum limitinin `min(...)` sözleşmesi.

## 6. Quasar — son tamamlanan durum

- Tek Supabase Auth kullanıcısı altında çoklu portföy hesabı.
- `/accounts` ve global seçili hesap akışı.
- Seçili hesap ve display asset SecureLS/Pinia persistence.
- Dashboard, Portföy, İşlemler, Raporlar ve girişler seçili hesap bazlı.
- Sinyaller/market/validation/health global.
- `AppPopupSelect.vue` proje genelinde select standardı; tekli/çoklu, arama/filtreleme ve responsive dialog destekli.
- İşlem düzenleme/iptal append-only revision; eski kayıt korunur.
- Revision sonrası tüm kronolojik bakiye zinciri replay edilir; sonraki işlemi bozan değişiklik reddedilir.
- Seçili portföy işlem geçmişi kontrollü reset RPC'siyle sıfırlanabilir.
- Alım/satış/dönüşüm/sermaye ekranlarında önce–işlem–sonra bakiye bağlamı bulunur.
- `/signals` karar status pill'i üst boşlukla hizalanmıştır.
- Prettier, ESLint ve Quasar SPA production build, Draft PR #1 açıklamasına göre geçti.

## 7. Quasar'da henüz kullanıcı doğrulaması bekleyen iş

- Son AppPopupSelect, multi-account, append-only revision ve reset değişikliklerinden sonra manuel finansal regression tamamlanmış sayılmıyor.
- `docs/DEMO_TEST_SCENARIO_100K_TRY.md` içindeki 12 işlem adım adım uygulanmalı.
- Her adımda önce/işlem/sonra bakiyesi kontrol edilmeli; ilk sapmada zincir durdurulup ekran görüntüsü paylaşılmalı.
- Sonunda Dashboard, Portföy, İşlem Geçmişi ve Raporlar ekran görüntüleriyle beklenen toplamlar karşılaştırılmalı.
- Draft PR testler tamamlanmadan merge edilmemeli.

## 8. Veritabanı/audit durumu

31.07.2026 tarihinde Supabase'e uygulanmış migration'lar:

- `0008_portfolio_audit_hardening.sql`
- `0009_portfolio_self_service_reset.sql`

Yeni migration `0010+` olmalıdır. Uygulanmış migration dosyaları geriye dönük değiştirilmez. Python reposundaki `migrations/` ve `supabase-migrations/` kopyaları birebir tutulur.

## 9. Dönüşümlü Git çalışma protokolü

1. Asistan kullanıcının mesajını okuduktan sonra aksiyon almadan önce remote branch'in güncel HEAD/dosyalarını yeniden okur.
2. Asistan değişiklikleri branch'e push eder.
3. Kullanıcı `git pull` yapar ve test eder.
4. Kullanıcı dosya üretmiş/değiştirmişse commit+push eder.
5. Asistan bir sonraki değişiklikten önce remote'u tekrar okur.
6. Eşzamanlı yazma yapılmaz.
7. Git hata/ayrışma çözümünde kullanıcıya bir seferde yalnız bir komut verilir.

## 10. Yeni oturumun ilk eylemi

1. `CHATGPT_PROJECT_START_HERE.md` ve zorunlu bağlam dosyalarını tamamen oku.
2. `RELEASED/APPROVED/PROPOSED/OPEN` ayrımını kısa biçimde kullanıcıya doğrula.
3. İki repo için aktif branch ve güncel HEAD'i remote'dan doğrula.
4. Kullanıcının son mesajında yeni Shadow çıktısı varsa checkpoint loguyla karşılaştır.
5. Quasar işi ise en son kullanıcı push'ını okumadan kod değiştirme.
6. Proje durumunu değiştirirsen oturum bitmeden bu handoff'u ve gerekiyorsa memory/contract'ı iki repoda senkron güncelle.

## 11. Secret ve güvenlik sınırı

API key, parola, Telegram token/Chat ID, Supabase service-role veya DB password hiçbir bağlam belgesine yazılmaz. Otomatik emir, otomatik LIVE ve otomatik threshold/weight değişikliği yoktur.
