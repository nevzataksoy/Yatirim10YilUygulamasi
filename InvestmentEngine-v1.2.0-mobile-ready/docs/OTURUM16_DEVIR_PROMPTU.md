# BTC_ETH_URA_10YIL — Oturum16 Devir Promptu

Bu belge Oturum15 kapanışından sonra yeni sohbet oturumunun projeyi güvenli ve eksiksiz devralması için hazırlanmıştır.

## 1. Repo ve aktif çalışma branch'i

```text
Repo   https://github.com/nevzataksoy/Yatirim10YilUygulamasi.git
Branch agent/portfolio-audit-reset
Yerel repo yolu D:\wamp64\www\Yatirim10YilUygulamasi
```

Repo default branch'i `master` olsa da güncel Python/Shadow geliştirme gerçeği `agent/portfolio-audit-reset` branch'indedir.

Oturum16 hiçbir local veya remote durumu varsaymamalıdır. İlk olarak remote HEAD'i kontrol etmeli, kullanıcıdan gelen local çıktı ile karşılaştırmalı ve yalnız gerçek kanıta dayanmalıdır.

## 2. Oturum16'nın ilk yapacağı işlem

İlk olarak kullanıcıya aşağıdaki kopyala-yapıştır güvenli PowerShell kontrolünü ver:

```powershell
cd D:\wamp64\www\Yatirim10YilUygulamasi; git fetch origin; Write-Host "LOCAL_HEAD=$(git rev-parse --short HEAD)"; Write-Host "REMOTE_HEAD=$(git rev-parse --short origin/agent/portfolio-audit-reset)"; Write-Host "BRANCH=$(git branch --show-current)"; Write-Host "=== STATUS ==="; git status --short
```

Local clean ve aynı branch'teyse gerekirse:

```powershell
cd D:\wamp64\www\Yatirim10YilUygulamasi; git pull --ff-only
```

Local worktree hakkında kullanıcı çıktısı olmadan tahmin yürütme.

## 3. Bağlamı devralmak için tamamen okunacak dosyalar

Güncel `agent/portfolio-audit-reset` branch'inden şu dosyaları tamamen oku:

1. `CHATGPT_PROJECT_START_HERE.md`
2. `InvestmentEngine-v1.2.0-mobile-ready/docs/PROJECT_MEMORY_BANK.md`
3. `InvestmentEngine-v1.2.0-mobile-ready/docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `InvestmentEngine-v1.2.0-mobile-ready/docs/SESSION_HANDOFF.md`
5. `InvestmentEngine-v1.2.0-mobile-ready/docs/OTURUM16_DEVIR_PROMPTU.md`
6. `InvestmentEngine-v1.2.0-mobile-ready/docs/INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`
7. `InvestmentEngine-v1.2.0-mobile-ready/docs/SHADOW_CHECKPOINT_LOG.md`
8. İlgili `InvestmentEngine-v1.2.0-mobile-ready/docs/POST_SHADOW_*.md` kanıt belgeleri
9. Yapılacak iş hangi alanı etkiliyorsa gerçek kod, migration ve test dosyaları

Kod ile eski belge çelişirse güncel branch'teki yayımlanmış kod, migration, test ve gerçek runtime/Supabase kanıtı önceliklidir.

## 4. Oturum15 kapanışında nerede kaldık

Released (yayımlanmış) model durumu değişmedi:

```text
Model Version             1.2.0
Mode                      SHADOW (gölge çalışma)
Realtime Execution        OFF (gerçek zamanlı icra kapalı)
SHADOW_READINESS          READY (hazır)
LIVE                      NO-GO (canlıya geçiş onaysız/uygun değil)
```

Released (yayımlanmış) ayarlar:

```text
minimum data quality      80
edge threshold            70
confidence threshold      70
strong edge               80
strong confidence         80
WATCH edge                55
reset edge                45
reset days                5
base tranche              25%
max regime                50%
```

Factor weights (faktör ağırlıkları), K1/K2, reversal (tersine dönüş), reset (sıfırlama), sizing (pozisyon boyutlama), scheduler cadence (görev zamanlama sıklığı), SHADOW/LIVE mode ve model version kullanıcı açıkça onaylamadan değiştirilmez.

`READY (hazır)` otomatik `LIVE (canlı)` değildir. `direction (yön)` emir değildir. `ACTION (aksiyon)` tek başına yeni kademe değildir; yeni kademe için ayrıca `action_event=true` gerekir.

## 5. Oturum15'te kapanan ana başlıklar

Aşağıdaki sınıflandırmalar günceldir:

```text
Shadow Readiness provenance contamination
CLOSED / VERIFIED (kapalı / doğrulandı)

Transactional decision persistence
CLOSED / VERIFIED (kapalı / doğrulandı)

URA immutable raw source snapshot P1
CLOSED / VERIFIED (kapalı / doğrulandı)

P2.1-P2.7 macro/job-runs data lifecycle
CLOSED (kapalı)

Build-time forced elevation
CLOSED / VERIFIED (kapalı / doğrulandı)

Normal-user PyInstaller build
VERIFIED (doğrulandı)

Installer/service runtime deployment
VERIFIED (doğrulandı)

Model semantics change
NONE (yok)
```

## 6. Windows build/deploy hardening kapanış kanıtı

Oturum15'te build pipeline'daki gereksiz Administrator yükseltmesi kaldırıldı.

Dar değişiklik:

```text
build.bat auto-elevation / RunAs     REMOVED (kaldırıldı)
build.bat elevated-shell guard       ADDED (eklendi)
PyInstaller --uac-admin              PRESERVED (korundu)
Inno PrivilegesRequired=admin        PRESERVED (korundu)
OneDir / _internal / --noupx         PRESERVED (korundu)
service install/start semantics      UNCHANGED (değişmedi)
model/scheduler semantics            UNCHANGED (değişmedi)
```

İlgili commitler:

```text
def6f2d  Build sırasında zorunlu yönetici yükseltmesini kaldır
83a0555  Normal kullanıcı build sözleşmesini release guard ile koru
792e565  Build ve kurulum yetki ayrımını dokümante et
50ed43b  Build yetki hardening kapanış kanıtını kaydet
```

Normal-user build (normal kullanıcı derlemesi) gerçek Windows ortamında doğrulandı:

```text
POWERSHELL_ADMIN=False
full pytest                   94 passed
release check                 OK
PyInstaller                   6.21.0 / OneDir PASS
PyInstaller admin warning     NOT PRESENT
Inno Setup                    6.4.0 / compile PASS
BUILD_EXIT_CODE               0
```

Yeni build/deploy identity (kimliği):

```text
Built EXE SHA256
83F793BE56792FD18F750D0416DC73356BFAB65FCF691A69731ECFEBBDFAA2E7

Installer SHA256
FF188BD2B3A9F6144C39BF7B25F2202F66386F972B3140EECB6E5243C1B005DA

Installed EXE SHA256
83F793BE56792FD18F750D0416DC73356BFAB65FCF691A69731ECFEBBDFAA2E7

EXE_HASH_MATCH=True
```

Upgrade sırasında güvenlik/ayar dosyaları korundu:

```text
SETTINGS_PRE  = SETTINGS_POST
9B399425AA664EE5ECC94553259DCAF8261EB4FF1490E5E4768DAAFA8463C88B

ROSALOCK_PRE  = ROSALOCK_POST
5B3D7A5AA99739516DAD7D816BFB7CBEC695FCD924502EE038B383099F216D9A
```

Windows Service (Windows Hizmeti) durumu:

```text
Name       RosaInvestmentEngine
State      Running (çalışıyor)
StartMode  Auto (otomatik)
ProcessId  7352
WIN32_EXIT_CODE   0
SERVICE_EXIT_CODE 0
SERVICE_STATUS_EXIT_CODE 0
```

## 7. Realtime smoke test freshness olayı ve kesin RCA sonucu

Yeni deploy sonrası ilk model validation (model doğrulama) çıktısı:

```text
model_validation: OK
core=OK
observations=1423
shadow=BLOCKED
VALIDATION_EXIT_CODE=0
SERVICE_PID_UNCHANGED=True
```

Bu `BLOCKED (engellendi)` durumu build/deploy regression (gerileme) değildi.

Supabase RCA (kök neden analizi) sonucu tek blocker (engelleyici) şuydu:

```text
Realtime smoke test 7.2 günlük; maksimum 7 gün.
```

Aynı readiness (hazır olma) kaydında:

```text
calendar_days               43
crypto_decision_days        42
ura_decision_days           29
crypto_median_quality       90.83
ura_median_quality          87.74
job_count                   384
job_success_percent         99.739583
realtime_test_age_days      7.210820397870371
ura_holdings_dates          28
ura_breadth_dates           28
```

Önceki READY kaydı 6.98046 günlük realtime test yaşı taşıyordu. Yaklaşık 5 saat sonra 7 günlük freshness gate (tazelik kapısı) aşılınca yalnız bu nedenle BLOCKED oldu.

Kullanıcı daha sonra normal PowerShell'de şu gerçek runtime doğrulamasını yaptı:

```text
SERVICE_PID_BEFORE=7352
Coinbase realtime smoke test başlatılıyor (20 sn)...
Websocket connected
realtime_test: OK
run=42df8e40-790a-42da-9a9e-9ec6684e2794
snapshots=8
products=BTC-USD,ETH-USD
REALTIME_EXIT_CODE=0

Model validation başlatılıyor...
model_validation: OK — core=OK observations=1424 shadow=READY
VALIDATION_EXIT_CODE=0
SERVICE_PID_AFTER=7352
SERVICE_PID_UNCHANGED=True
```

Kesin sonuç:

```text
Build/deploy regression              NO (yok)
Realtime Coinbase pipeline           VERIFIED (doğrulandı)
Core model validation                OK (başarılı)
SHADOW_READINESS                     READY (hazır)
Service continuity                   VERIFIED (doğrulandı)
Service restart/crash                NONE (yok)
```

`--validate-model` komutunun exit code 0 üretmesi tek başına readiness PASS anlamına gelmez; CLI exception yoksa 0 döner. Readiness durumu ayrıca `shadow=...` alanından okunmalıdır.

Normal PowerShell kullanımı sorun değildir. Runtime EXE `--uac-admin` manifestini korur; build sürecinin normal kullanıcı olması ile runtime UAC (Kullanıcı Hesabı Denetimi) gereksinimi ayrı sözleşmelerdir.

## 8. LIVE neden hâlâ NO-GO

`SHADOW_READINESS=READY (hazır)` yalnız manuel production review (üretim incelemesi) kapısıdır.

LIVE hâlâ `NO-GO (canlıya geçiş yok)` çünkü:

- production ACTION/WATCH örneklemi yeterli değildir,
- bağımsız OOS (out-of-sample / örneklem dışı) signal evidence sınırlı/signal-starved durumdadır,
- historical replay production K1/K2/reset/reversal/event/data-quality zincirini birebir doğrulamaz,
- URA full PIT (point-in-time / zaman-noktası) replay için holdings/breadth/event geçmişi henüz yeterli değildir.

Bu durum threshold düşürmek, factor weights değiştirmek veya LIVE açmak için otomatik gerekçe değildir.

## 9. Forward observation (ileri yönlü gözlem) olarak kalanlar

Bunlar mevcut kapanışları yeniden OPEN yapmaz:

1. `1 Ekim 2026 09:00 Europe/Istanbul` ilk doğal `monthly_audit_job` lifecycle observation.
2. İleride ikinci post-0014 farklı URA holdings tarihi oluşunca current + previous immutable raw snapshot refs zincirinin birlikte görülmesi.
3. Historical connection-pool timeout ailesi için GitHub Issue #2 observation borcu.

Doğal scheduler evidence (zamanlayıcı kanıtı) manuel job ile taklit edilmez. Özellikle `--once monthly` veya `--once ura` bu kanıtlar için kullanılmaz.

## 10. Non-blocking warning (engelleyici olmayan uyarı) teknik borcu

Build sırasında iki warning gözlendi:

```text
pytest cache/temp cleanup      WinError 183 / WinError 5
PyInstaller hidden import      "sip" not found
```

Bunlar full tests, release check, PyInstaller build, installer compile veya runtime'ı düşürmedi.

Oturum16'da bunlara doğrudan patch yazma. Önce RCA-only (yalnız kök neden analizi) yap.

Önerilen sıra:

1. Önce `pytest cache/temp cleanup` uyarısının geçmiş elevated build kalıntısı/ownership (sahiplik) kaynaklı olup olmadığını doğrula. Kod değişikliği gerekmeyebilir.
2. Sonra `PyInstaller hidden import "sip" not found` uyarısının PyQt5/Python 3.14 packaging davranışında gerçek runtime riski oluşturup oluşturmadığını doğrula. Mevcut build ve runtime çalıştığı için yalnız warning'i susturmak amacıyla rastgele hidden-import ekleme.
3. Daha yüksek değerli açık bir teknik borç tespit edilirse warning hygiene (uyarı temizliği) yerine onu önceliklendir ve kullanıcıya gerekçeyi anlat.

İlk teknik adımın kod değişikliği değil, mevcut açık borçları ve bu iki warning'i kanıta dayalı önceliklendirmek olması tercih edilir.

## 11. Kod revizyon çalışma biçimi

Bağlayıcı yöntem:

```text
önce mevcut dosya ve mimariyi incele
→ veri akışını anla
→ gereksiz yeni layer (katman) / queue (kuyruk) / scheduler (zamanlayıcı) ekleme
→ mevcut veri akışını koru
→ değişiklikleri yalnız ilgili fonksiyonlarla sınırla
→ model semantiğini istemeden değiştirme
→ focused test (odaklı test)
→ full test (tam test)
→ release check (sürüm kontrolü)
→ gerekiyorsa gerçek runtime/Supabase doğrulaması
→ değişen/yeni dosyaları açıkça listele
```

Bir sorun kodda zaten çözülmüşse yeniden implement etme. Önce test/runtime evidence ile kapanıp kapanmadığını kontrol et.

`kodlandı`, `test edildi`, `production DB'de doğrulandı`, `runtime deploy edildi`, `ürün kararı olarak onaylandı` durumlarını birbirine karıştırma.

## 12. Çıktı ve isimlendirme kuralı

Kullanıcının yeni kalıcı çalışma kuralı:

- Sonuç özetlerindeki sınıflandırma adlarının Türkçe karşılığını parantez içinde yaz.
- Teknik terimlerde anlamı bozmayacak şekilde Türkçe karşılığını parantez içinde ver.
- Kod identifier (tanımlayıcı), tablo/kolon/fonksiyon adı veya CLI flag gibi literal teknik isimleri değiştirme; gerekiyorsa yanına açıklama ekle.

Örnek:

```text
CLOSED / VERIFIED (kapalı / doğrulandı)
BLOCKED (engellendi)
READY (hazır)
RCA (kök neden analizi)
rollback (geri alma)
provenance (kaynak izi)
```

## 13. PowerShell çalışma kuralı

PowerShell komutları doğrudan kopyala-yapıştır güvenli biçimde verilir.

- Birbirine bağlı komutlar mümkünse tek satırda `;` ile ayrılır.
- `$LASTEXITCODE` ilgili komuttan hemen sonra yakalanır.
- `PS ...>` ve `>>` prompt metinleri code block içine yazılmaz.
- Migration, service stop/start, production job, installer veya data mutation komutu verilecekse etkisi önceden açıklanır.
- Development installer kullanıcı tarafından görünür çalıştırılmalıdır; varsayılan olarak `/VERYSILENT` kullanılmaz.

## 14. Commit/push çalışma kuralı

Her mantıksal değişiklik ayrı commit edilir.

Commit mesajları mutlaka Türkçe olur.

GitHub yazma işleminden hemen önce:

1. remote `agent/portfolio-audit-reset` HEAD'i yeniden oku,
2. değiştirilecek mevcut dosyanın güncel blob SHA'sını yeniden oku,
3. stale (bayat) SHA ile update yapma.

Yasaklar:

```text
force push                         YOK
master merge                       kullanıcı açıkça istemedikçe YOK
rebase/history rewrite             kullanıcı açıkça istemedikçe YOK
raw log/telemetry kanıtını commit  yalnız gerekli belge değilse YOK
```

Commit/push sonrasında mutlaka bildir:

```text
short SHA
full SHA
değişen dosyalar
yeni dosyalar
test/build/runtime doğrulama durumu
```

Sonra kullanıcıya local repo için `git pull --ff-only` komutu ver.

## 15. Her turun sonunda zorunlu proje bağlamı güncellemesi

Kullanıcının açık kuralı:

**Her tur sonunda proje bağlamını ve Git reposunu güncellemeyi unutma.**

Bunun anlamı:

- Turda kalıcı proje durumu, karar, kapanış, yeni RCA sonucu veya çalışma kuralı oluştuysa ilgili proje bağlamı belgesini güncelle.
- Uygun belge tercihen `docs/SESSION_HANDOFF.md`; oturum özel devir bilgisi gerekiyorsa ilgili oturum devir belgesi de güncellenebilir.
- Doküman değişikliğini Türkçe commit mesajıyla `agent/portfolio-audit-reset` branch'ine push et.
- Doküman-only değişikliklerde gereksiz test/build çalıştırma; bunun doküman-only olduğunu açıkça belirt.
- Remote write öncesi her zaman güncel HEAD/blob SHA kontrolü yap.
- Tur sonunda yeni remote SHA'yı kullanıcıya bildir ve local `git pull --ff-only` iste.

Bu kural yalnız anlamlı kalıcı proje bilgisi oluşan turlar için uygulanır; gereksiz/boş doküman churn (değişiklik gürültüsü) üretme.

## 16. Oturum16'da önerilen ilk çalışma sırası

Oturum16 başlangıcında:

1. Remote/local branch durumunu doğrula.
2. Bölüm 3'teki bağlam dosyalarını tamamen oku.
3. Güncel runtime baseline'ı şu kabul et, ancak yeni kanıtla çelişirse yeni kanıtı esas al:

```text
Installed EXE SHA256  83F793BE56792FD18F750D0416DC73356BFAB65FCF691A69731ECFEBBDFAA2E7
Service               Running / Auto / PID 7352
Realtime smoke test   OK
Core validation       OK
observations           1424
SHADOW_READINESS      READY
LIVE                  NO-GO
```

4. Açık teknik borçları yeniden sınıflandır; CLOSED başlıkları sebepsiz yeniden açma.
5. İlk teknik öneri olarak warning-hygiene RCA'yı değerlendir, ancak daha yüksek değerli açık görev varsa onu öne al.
6. Kullanıcı onayı olmadan released model semantics (yayımlanmış model semantiği) değiştirme.
7. Kod değişikliğine geçilecekse önce gerçek dosyaları ve testleri incele; dar değişiklik yap.
8. Tur sonunda proje bağlamını ve Git reposunu güncelle.

## 17. Oturum16'ya verilecek kısa görev tanımı

Yeni sohbetin amacı eski işleri yeniden yapmak değil; Oturum15'te kapanan Windows build/deploy hardening'i ve tekrar READY olan runtime baseline'ını devralıp, güncel açık borçları kanıta dayalı olarak önceliklendirmek ve bir sonraki geliştirme adımını seçmektir.

Özellikle:

```text
Build-time Administrator problemi     CLOSED / VERIFIED (kapalı / doğrulandı)
Realtime 7-day freshness blocker      RESOLVED (çözüldü)
SHADOW_READINESS                      READY (hazır)
LIVE                                  NO-GO (canlıya geçiş yok)
Model semantics                       UNCHANGED (değişmedi)
```

Bu durumdan devam et; kapanmış işleri tekrar implement etme.
