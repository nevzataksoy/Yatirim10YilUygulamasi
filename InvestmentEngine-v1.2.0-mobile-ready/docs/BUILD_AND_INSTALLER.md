# Build ve Installer — Investment Engine v1.2.0

## `build.bat`

Yönetici olarak çalıştırıldığında:

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

`scripts/release_check.py` aşağıdaki packaging sözleşmesini zorunlu tutar:

- `--onedir`
- `--contents-directory "_internal"`
- `--noupx`
- `dist\InvestmentEngine\InvestmentEngine.exe`
- installer'da `_internal` ağacının kopyalanması
- `--onefile` kullanımının yasak olması

Bu kontrol, SCM startup timeout riskinin yanlışlıkla yeniden release'e girmesini engeller.

## Windows-only doğrulama

Container/Linux üzerinde unit/static test yapılabilir; gerçek DPAPI LocalMachine, Windows Service SCM, PyInstaller Windows runtime, Inno Setup ve public WebSocket smoke test Windows makinede doğrulanmalıdır.

OneDir değişikliğinden sonraki kabul testi:

1. `build.bat` PASS
2. `release_check: OK`
3. installer compile PASS
4. kurulu EXE SHA256 build artefactı ile eşleşmeli
5. `settings` / `rosalock` korunmalı
6. `InvestmentEngineCLI.cmd --service-status` startup süresi 30 saniyenin belirgin altında olmalı
7. installer service start aşaması 1053/7009 vermemeli
8. service `RUNNING`, exit code 0 olmalı
9. `--shadow-observability` exit code 0 olmalı
