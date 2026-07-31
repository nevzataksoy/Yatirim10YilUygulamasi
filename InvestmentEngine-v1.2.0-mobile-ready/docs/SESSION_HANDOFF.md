# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 31 Temmuz 2026  
Amaç: Yeni sohbetin son aktif durumu konuşma geçmişini yeniden keşfetmeden devralması.

Bu belge yalnız en güncel çalışma durumunu taşır. Kalıcı proje kararları `PROJECT_MEMORY_BANK.md`, sinyal motorunun normatif davranışı `SIGNAL_ENGINE_DECISION_CONTRACT.md` içindedir.

## 1. Aktif repo durumu

| Repo                              | Branch                                 | Bağlam setini oluşturan commit | Çalışma amacı                                                     |
| --------------------------------- | -------------------------------------- | ------------------------------ | ----------------------------------------------------------------- |
| `Yatirim10YilUygulamasi`          | `agent/portfolio-audit-reset`          | `d056531`                      | Python Engine, Supabase migration/sözleşmesi, ortak proje bağlamı |
| `tr.rosayazilim.yatirimdashboard` | `feature/initial-investment-dashboard` | `619441d`                      | Quasar tek kullanıcı–çoklu portföy uygulaması                     |

Bu SHA'lar memory/contract/start/handoff bağlam setinin ilk yayımlandığı commitlerdir.
Handoff senkronizasyonu nedeniyle branch HEAD daha yeni olabilir; yeni oturum güncel
HEAD'i her zaman `git log -1 --oneline` ile doğrular.

## 2. Son tamamlanan geliştirmeler

### Python / Supabase

- Append-only portföy revision zinciri hardening tamamlandı.
- Kullanıcı kontrollü seçili portföy işlem geçmişi sıfırlama RPC'si eklendi.
- `0008_portfolio_audit_hardening.sql` ve `0009_portfolio_self_service_reset.sql` 31.07.2026 tarihinde Supabase SQL Editor'de başarıyla uygulandı.
- Python motoru portföyden ve Telegram fan-out'tan bağımsız bırakıldı.

### Quasar

- Tek Auth hesabı altında çoklu portföy çalışma alanı eklendi.
- `/accounts` Portföy Hesaplarım sayfası ve yeni hesap oluşturma akışı eklendi.
- Profil/right drawer içine global `AppPopupSelect` hesap seçimi eklendi.
- Seçili hesap SecureLS/AES destekli Pinia persistence ile korunuyor.
- Dashboard, portföy, işlemler, raporlar ve girişler seçili `account_id` ile çalışıyor.
- Sinyaller hesabın dışında/global kalıyor.
- İşlem düzenleme ve iptal append-only revision akışında çalışıyor.
- Native `q-select` kullanımı bırakılarak proje formları `AppPopupSelect` standardına geçirildi.

## 3. Doğrulanmış görev

### Görev 2 — TCMB/FX scheduler: başarılı

```text
Planlanan: 31.07.2026 16:30 TRT
Başlangıç: 13:30:00 UTC
Data date: 31.07.2026
USD/TRY: 47.4305
Health: FX=OK
Job: OK
Süre: yaklaşık 2,48 saniye
```

`market_snapshot`, `engine_health_snapshot` ve `system.job_runs` uyumludur. Bu sonuç model threshold değişikliği gerektirmez.

## 4. Devam eden Shadow takvimi

- Görev 3: 01.08.2026 — weekly + monthly audit scheduler kontrolü.
- Görev 4: 07.08.2026 — 7 günlük ilk gerçek güvenilirlik checkpoint'i.
- Görev 5: 14.08.2026 — 14 günlük stabilite.
- Görev 6: 20.08.2026 — URA 20 günlük quality değerlendirmesi.
- Görev 7: 29.08.2026 — 30 günlük Shadow Graduation Review.

Sonucu paylaşılmamış görev başarılı varsayılmaz.

## 5. Sinyal motorunda son analiz sonucu

### Mevcut/released gerçek

- Eşikler: quality `80`, edge `70`, confidence `70`, strong `80/80`.
- K1/K2 persistent state ve `%50` cumulative cap mevcut.
- K2 farklı gün + strong `80/80` ister; 5 seans bekleme şartı mevcut değil.
- Karşı-yön qualified `ACTION`, production state'i hemen yeni K1'e çevirebilir.
- PIT replay 5 seans cooldown kullanır; fakat production K1/K2 state'ini ve bütün quality/confidence kapılarını birebir yürütmez.
- Python action size ile Quasar kullanıcı dönüşüm yüzdesi otomatik entegre değildir.

### Onay bekleyen öneri

1. K2 ve her yeni kademe arasında en az 5 karar seansı.
2. Ters yön için iki ardışık qualified close.
3. Production ve replay için tek versioned state machine.
4. Python `action_size` model önerisi; Quasar dönüşüm oranı maksimum kullanıcı limiti; uygulanacak öneri `min(...)`.

Bu dört madde kullanıcı tarafından açıkça onaylanmadan kodlanmaz veya released karar gibi belgelenmez.

## 6. Görev 4 sonrası davranış değiştirmeyen Python işi

- `shadow_epoch_id` veya `shadow_started_at` ile açık epoch.
- `scheduled/manual/backfill/development` run-kind ayrımı.
- Beklenen job sayısı ve gerçekleşen job sayısı karşılaştırması.
- `OK rate` ve `completed rate` ayrımı.
- Edge/confidence/quality/status/direction bucket diagnostics.
- Mevcut v1.2.0 K1/K2 davranışını karakterize eden unit testler.

Bu işler mevcut threshold veya yön davranışını değiştirmeden v1.2.x hardening olarak ele alınabilir.

## 7. Açık ürün/teknik kararlar

- Whipsaw koruması için önerilen reversal ve cooldown kuralları kabul edilecek mi?
- Quasar kullanıcı dönüşüm oranının semantiği “maksimum rejim limiti” olarak değiştirilecek mi?
- Bu kararlar kabul edilirse yeni model sürümü `1.3.0` mı olacak?
- Signal→Conversion UX, seçili hesaptaki kaynak bakiyeden önerilen miktarı nasıl gösterecek?

## 8. Yeni oturum için ilk eylem

Yeni sohbet doğrudan kod değiştirmeden önce:

1. `PROJECT_MEMORY_BANK.md` ve `SIGNAL_ENGINE_DECISION_CONTRACT.md` ayrımını özetlesin.
2. Bu handoff'taki repo branch/commit değerlerini `git status` ve `git log -1` ile doğrulasın.
3. Kullanıcı yeni Shadow çıktısı verdiyse ilgili görev sorgularıyla karşılaştırsın.
4. Sonucu operasyonel sapma, data-quality sapması veya model-karar kanıtı olarak sınıflandırsın.
5. Öneri ile released davranışı birbirine karıştırmadan ilerlesin.

## 9. Oturum kapanış kuralı

Proje durumunu değiştiren her sohbet bitmeden önce:

- tamamlanan işi,
- doğrulama sonuçlarını,
- yeni branch/commit'i,
- kesinleşen kararları,
- kalan açık işi ve sıradaki checkpoint'i

bu dosyaya işler. Kalıcı karar `PROJECT_MEMORY_BANK.md` veya `SIGNAL_ENGINE_DECISION_CONTRACT.md` içinde de güncellenir. Secret değerler yazılmaz.
