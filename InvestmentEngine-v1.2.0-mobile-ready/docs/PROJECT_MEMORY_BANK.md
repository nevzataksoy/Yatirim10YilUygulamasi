# BTC / ETH / URA 10 Yıllık Yatırım — Proje Memory Bank

Son güncelleme: 31 Temmuz 2026

Bu belge yeni ChatGPT/Codex oturumlarının proje amacını, kesinleşmiş kararları ve iki repo arasındaki sorumluluk sınırını dosya taramasına başlamadan anlaması için hazırlanmıştır. Ayrıntılı teknik belgelerin yerine geçmez; doğru belgeye yönlendiren kalıcı proje bağlamıdır.

## 1. Proje amacı

- Başlangıç tarihi **25.07.2026**, hedef süre **120 ay / 10 yıl**.
- Takip edilen varlıklar: spot **BTC**, **ETH** ve **URA**; nakit bacakları **USD** ve **TRY**.
- Kullanıcı her ay gerçek alım ve sermaye hareketlerini manuel kaydeder.
- Python Investment Engine portföyden bağımsız BTC/ETH ve URA/USD dönüşüm kararları üretir.
- Quasar uygulaması gerçek portföy defterini, maliyetleri, kâr/zararı, işlemleri, raporları ve motor görünümünü yönetir.
- Otomatik emir gönderimi yoktur. Sinyal karar desteğidir; işlemi kullanıcı yapar ve Quasar'a kaydeder.

## 2. Kesinleşmiş kullanıcı ve portföy modeli

- Sistem **tek kullanıcıya** yöneliktir; çoklu kullanıcı/SaaS kapsamı terk edilmiştir.
- Aynı Supabase Auth kullanıcısı altında **birden çok portföy hesabı** bulunabilir.
- Amaç kullanıcının kendisi, eşi ve çocuğu adına ayrı işlem defterleri tutabilmesidir.
- Portföylerin varlık evreni ve yatırım planı ortaktır; `investment_account_settings` oluşturulmaz.
- Dashboard, Portföy, İşlemler, Raporlar ve tüm işlem girişleri seçili portföy hesabına göre çalışır.
- Sinyaller, piyasa snapshot'ları, model validation ve engine health portföyden bağımsızdır.
- Seçili portföy kimliği Pinia persistence üzerinden SecureLS/AES ile localStorage'da saklanır. Bu, cihaz cache korumasıdır; native keychain değildir.

## 3. Sistem sınırları

| Katman                   | Sorumluluk                                                                                  | Bilinçli olarak yapmadığı                                   |
| ------------------------ | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Python Investment Engine | Piyasa/makro/veri toplama, feature/factor, karar, validation, scheduler, health ve Telegram | Portföy bakiyesi veya seçili portföy okumaz; emir göndermez |
| Supabase/PostgreSQL      | Auth, RLS, portföy hesapları ve işlemleri; read-only motor snapshot yüzeyi                  | Frontend'e service-role veya sağlayıcı secret'ı vermez      |
| Quasar/Pinia             | Veri girişleri, hesap seçimi, ledger, dashboard, rapor ve motor görünümü                    | Model ağırlığı/eşiği değiştirmez; Telegram token yönetmez   |

Repo haritası:

- Frontend: `nevzataksoy/tr.rosayazilim.yatirimdashboard`
- Engine ve veritabanı sözleşmesi: `nevzataksoy/Yatirim10YilUygulamasi`

## 4. Telegram kararı

- Tek Telegram botu ve tek Chat ID kullanılır.
- Bot API Key ve Chat ID yalnız Windows'taki Python ayar penceresinden girilir ve Python yerel güvenli ayar mekanizmasında tutulur.
- Quasar'daki kullanıcı/portföy ayarları Python Telegram yapılandırmasına bağlanmaz.
- Bildirim portföy hesabına değil, global varlık sinyali olayına aittir.
- Shadow modunda normal action Telegram bildirimi gönderilmez; LIVE geçişi ayrı manuel onay gerektirir.

## 5. Portföy veri sözleşmesi

- `public.investment_accounts`: bir Auth kullanıcısının portföy çalışma alanları.
- `public.portfolio_transactions`: her satır `account_id` taşır.
- `public.user_investment_settings`: kullanıcı seviyesinde ortak yatırım planı.
- `public.portfolio_positions`: etkin revizyonlardan hesaplanan hesap bazlı miktarlar.
- İşlemler append-only'dir. Düzeltme ve iptal yeni revizyon satırıyla yapılır.
- Kullanıcı kontrollü sıfırlama yalnız seçili hesabın işlemlerini `reset_portfolio_transaction_history` RPC'siyle siler.
- Profil, diğer hesaplar, yatırım ayarları, piyasa/model/sinyal/health verileri sıfırlamada korunur.

31.07.2026 tarihinde `0008_portfolio_audit_hardening.sql` ve `0009_portfolio_self_service_reset.sql` Supabase SQL Editor'de başarıyla uygulanmıştır. Yeni bir migration oluşturulursa bu iki dosyadan sonra numaralandırılmalıdır; uygulanmış migration dosyaları geriye dönük değiştirilmemelidir.

## 6. Python Shadow görevlerinin amacı

Görev takvimi rastgele veri kontrolü değildir. Windows Server üzerindeki production-benzeri Shadow zincirinin aşağıdaki noktalarını gerçek zamanlarda kanıtlamak için oluşturulmuştur:

1. Scheduler'ın Europe/Istanbul saatlerinde doğru işi başlatması.
2. Sağlayıcıdan doğru tarihli verinin alınması ve freshness kurallarının çalışması.
3. Raw/normalized veri, public snapshot, health ve `system.job_runs` kayıtlarının birbiriyle tutarlı olması.
4. Geçici provider sorunu ile kalıcı kod/sözleşme hatasının ayrıştırılması.
5. Model kararları değerlendirilmeden önce veri kalitesi ve operasyonel güvenilirliğin kanıtlanması.

Doğrulanmış sonuç: **Görev 2 — TCMB/FX otomatik işi**, 31.07.2026 Cuma 16:30 TRT'de geçti. `daily_fx_job=OK`, `FX=OK`, veri tarihi `2026-07-31`, USD/TRY `47.4305`; job yaklaşık 2,48 saniyede tamamlandı.

Henüz paylaşılmamış görev sonuçları başarıyla geçmiş kabul edilmez; memory bank yalnız kanıtlanmış sonucu kaydeder.

## 7. Görevler tamamlandıktan sonraki Python revizyonu

Python'a çoklu portföy kodu eklenmeyecektir. Görev takvimi tamamlandığında şu release-gate uygulanır:

1. Tüm görev çıktıları scheduler, provider, freshness, snapshot, health, job audit ve model etkisi başlıklarıyla tek matriste sınıflandırılır.
2. Beklenen davranışlar kod değişikliğine dönüştürülmez; yalnız gerçek sapmalar düzeltilir.
3. Sapma varsa düzeltme önceliği: veri bütünlüğü → zamanlama/retry → health/observability → model girdisi → bildirim.
4. Düzeltmeler yeniden `--once`/smoke test, release check ve ilgili zamanlanmış iş ile doğrulanır.
5. `--validate-model` ve Shadow Readiness yeniden değerlendirilir. Model eşikleri/ağırlıkları otomatik değiştirilmez.
6. En az 30 günlük Shadow kriterleri `READY` olmadan ve manuel production review yapılmadan `engine_mode=live` seçilmez.
7. Hata düzeltmeleri v1.2.x; yeni veri kaynağı, model davranışı veya sözleşme değişikliği ayrı, versioned bir sonraki sürüm kapsamıdır.

Bu revizyonun muhtemel temas noktaları görev kanıtına bağlı olarak scheduler gözlemlenebilirliği, provider retry/fallback, freshness/data-quality açıklamaları ve validation raporudur. Portföy seçimi, portföy bakiyesi ve hesap bazlı Telegram fan-out Python kapsamı değildir.

## 8. Model güvenlik kararları

- Mevcut çalışma modu Shadow'dur; Realtime Execution kapalıdır.
- Shadow Readiness varsayılan olarak en az 30 takvim günü, karar günü sayıları, median quality, son 7 günlük job başarısı, realtime smoke yaşı ve URA history kriterlerini ölçer.
- ETH/BTC için PIT core replay vardır; güvenilir tarihçesi olmayan derivatives/event girdileri geçmişe taşınmaz.
- URA full PIT replay yeterli holdings/breadth/event geçmişi birikene kadar `NOT_READY` kalabilir.
- Eksik veri skor uydurularak tamamlanmaz; quality `0` olarak görünür tutulur.
- Otomatik threshold/weight kalibrasyonu ve otomatik LIVE geçişi yoktur.

## 9. Yeni oturum çalışma protokolü

1. Önce bu dosyayı tamamen oku.
2. Değişiklik yapılacak katmanın ayrıntılı sözleşme ve test belgesini incele.
3. `git status` ile kullanıcı değişikliklerini koru.
4. Veritabanı değişikliğinde Python reposundaki migration zinciri ve `MOBILE_APP_BACKEND_CONTRACT.md` ile Quasar store kullanımını birlikte güncelle.
5. Python değişikliğinde `MODEL_AND_SCHEDULE.md`, `MODEL_VALIDATION_AND_SHADOW.md` ve ilgili test planını kontrol et.
6. Kalıcı proje kararı, doğrulanmış görev sonucu veya mimari sınır değişirse bu memory bank'i aynı turda güncelle.
7. Secret değerleri, erişim anahtarları ve kişisel token'lar hiçbir zaman memory bank'e yazılmaz.
