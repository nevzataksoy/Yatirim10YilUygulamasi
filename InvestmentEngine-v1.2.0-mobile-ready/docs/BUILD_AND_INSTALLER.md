# Build ve Installer — Investment Engine v1.2.0

## `build.bat`

Build zinciri **normal (non-elevated) PowerShell / Komut İstemi** altında çalıştırılır. `build.bat` artık kendisini `RunAs` ile yeniden başlatmaz. Administrator tokenı algılarsa PyInstaller çalışmadan önce açık hata ile durur.

Bu ayrım bilinçlidir: PyInstaller build işleminin elevated çalışması gerekmez ve PyInstaller 7.0 yönünde bu kullanım engellenmektedir. Build-time yetkisi ile üretilen EXE/installer'ın runtime UAC gereksinimi birbirinden ayrı sözleşmelerdir.

Normal terminalde akış:

```text
.venv oluştur / kullan
→ pip build requirements
→ compileall
→ pytest
→ scripts/release_check.py
→ PyInstaller --onedir --contents-directory _internal --noupx --windowed --uac-admin
→ dist\InvestmentEngine\InvestmentEngine.exe
→ dist\InvestmentEngine\_internal\...
→ Inno Setup 6 varsa setup compile
```

Beklenen installer:

```text
installer\InvestmentEngineSetup-1.2.0.exe
```

Tek ana uygulama binary'si yine `InvestmentEngine.exe`'dir. `InvestmentEngineCLI.cmd` ikinci bir engine değildir; aynı GUI-subsystem EXE'yi terminalde blocking çalıştıran wrapper'dır.

### Build-time ve runtime elevation ayrımı

`build.bat` / PyInstaller / Inno Setup compiler normal kullanıcı tokenı ile çalışır.

PyInstaller'daki `--uac-admin` ise build sürecini yükseltmez; üretilen `InvestmentEngine.exe` için runtime UAC manifestini korur. Bu seçenek şimdilik gereklidir çünkü mevcut mimaride `settings`, `rosalock`, `logs` ve `runtime` kurulum dizini altında bulunur ve güvenlik sınırı LocalSystem + Administrators ACL sözleşmesine dayanır.

Inno Setup içindeki:

```text
PrivilegesRequired=admin
```

compiler'ı değil, oluşturulan installer'ın çalıştırılma anını yükseltir. Installer Program Files'a yazar, Windows Service'i durdurur/kurar/başlatır ve bu nedenle runtime'da Administrator yetkisi istemeye devam eder.

Özet sözleşme:

```text
BUILD
normal kullanıcı terminali
  → pytest / release_check
  → PyInstaller
  → ISCC compile

RUNTIME / INSTALL
InvestmentEngine.exe        → --uac-admin manifesti korunur
InvestmentEngineSetup.exe   → PrivilegesRequired=admin
Windows Service yönetimi    → elevated installer / admin runtime
```

## Neden OneDir?

04 Eylül 2026 kontrollü observability rollout sırasında eski `--onefile` build ile Windows Service başlangıcı SCM'nin 30 saniyelik başlangıç penceresini aştı.

Aynı kurulu EXE üzerinde ölçülen zararsız `--service-status` process başlangıç süreleri:

```text
run 1: 62.741 s
run 2: 20.879 s
run 3: 18.019 s
```

İlk service start denemesinde Windows System log:

```text
Event 7009: 30000 ms service connection timeout
Event 7000: service failed to start
```

Aynı EXE'nin `--shadow-observability` CLI akışı ise başarıyla çalışıp exit code 0 verdi. Ayrıca yeni service start denemesinden uygulama loguna hiç satır düşmedi. Bu kanıt problem alanını engine/DB/settings katmanından önceki packaged-runtime bootstrap aşamasına daralttı.

Bu nedenle Windows Service release'i artık OneDir olarak paketlenir. Bağımlılıklar installer tarafından önceden `{app}\_internal` altına açılır; servis başlangıcında büyük bir one-file arşivinin temp dizine tekrar çıkarılması gerekmez.

UPX de service release'inde kapalıdır (`--noupx`). Amaç paket boyutundan ziyade deterministik ve hızlı startup'tır.

## Kurulum dizini sözleşmesi

Installer şu yapıyı kurar:

```text
C:\Program Files\Rosa\InvestmentEngine\
  InvestmentEngine.exe
  InvestmentEngineCLI.cmd
  InvestmentEngineCLI.ps1
  settings                 # generated, upgrade'de korunur
  rosalock                 # generated, upgrade'de korunur
  _internal\...           # PyInstaller OneDir bağımlılıkları
  logs\
  runtime\
  migrations\
  docs\
```

Bu değişiklik service/CLI yol sözleşmesini değiştirmez:

```text
"C:\Program Files\Rosa\InvestmentEngine\InvestmentEngine.exe" --service
```

`app.paths.application_dir()` frozen runtime'da EXE'nin bulunduğu dizini kullanmaya devam ettiği için `settings`, `rosalock`, `logs` ve `runtime` konumları aynı kalır. Bundled read-only kaynaklar OneDir `_internal` altında çözülür.

## PyInstaller önemli modüller

Build WebSocket dahil gerekli hidden import/collect tanımlarını içerir:

```text
psycopg / psycopg_pool
apscheduler
tzdata
firebase_admin
pywin32 service modülleri
cryptography
websocket-client
```

## Inno Setup

Installer:

- ana EXE'yi `{autopf}\Rosa\InvestmentEngine` altına kopyalar,
- `dist\InvestmentEngine\_internal` ağacını `{app}\_internal` altına kopyalar,
- `InvestmentEngineCLI.cmd`, `InvestmentEngineCLI.ps1`, migration ve docs dosyalarını kurar,
- upgrade'de çalışan `RosaInvestmentEngine` servisini durdurur,
- ilk kurulumda settings yoksa `--configure` açar,
- aynı ana EXE'yi `--install-service` ile service olarak kaydeder,
- settings/rosalock varsa servisi başlatır,
- settings ve rosalock release paketinde bulunmaz ve upgrade'de korunur.

## Release guard

`scripts/release_check.py` aşağıdaki packaging/build sözleşmesini zorunlu tutar:

- `--onedir`
- `--contents-directory "_internal"`
- `--noupx`
- `dist\InvestmentEngine\InvestmentEngine.exe`
- installer'da `_internal` ağacının kopyalanması
- `--onefile` kullanımının yasak olması
- `build.bat` içinde `-Verb RunAs` ile otomatik yükseltme bulunmaması
- `build.bat` içinde elevated terminali reddeden non-elevated build guard'ının bulunması

Bu kontroller hem SCM startup timeout riskinin hem de elevated PyInstaller build davranışının yanlışlıkla release zincirine geri dönmesini engeller.

## Windows-only doğrulama

Container/Linux üzerinde unit/static test yapılabilir; gerçek DPAPI LocalMachine, Windows Service SCM, PyInstaller Windows runtime, Inno Setup ve public WebSocket smoke test Windows makinede doğrulanmalıdır.

Build-time elevation hardening sonrası kabul testi:

1. Normal PowerShell / Komut İstemi altında `build.bat` PASS
2. `pytest` PASS
3. `release_check: OK`
4. PyInstaller çıktısında elevated/admin deprecation uyarısı bulunmamalı
5. installer compile PASS
6. kurulu EXE SHA256 build artefactı ile eşleşmeli
7. `settings` / `rosalock` korunmalı
8. `InvestmentEngineCLI.cmd --service-status` startup süresi 30 saniyenin belirgin altında olmalı
9. installer service start aşaması 1053/7009 vermemeli
10. service `RUNNING`, exit code 0 olmalı
11. `--shadow-observability` exit code 0 olmalı

Administrator terminalinde `build.bat` çalıştırılması ise başarı kriteri değildir; guard'ın PyInstaller başlamadan önce açık hata ile işlemi reddetmesi beklenen davranıştır.
