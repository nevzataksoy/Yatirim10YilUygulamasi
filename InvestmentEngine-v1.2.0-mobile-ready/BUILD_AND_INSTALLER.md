# Build ve Installer — Investment Engine v1.1.4

## `build.bat`

Yönetici olarak çalıştırıldığında:

```text
.venv oluştur / kullan
→ pip build requirements
→ compileall
→ pytest
→ scripts/release_check.py
→ PyInstaller --onefile --windowed --uac-admin
→ dist\InvestmentEngine.exe
→ Inno Setup 6 varsa setup compile
```

Beklenen installer:

```text
installer\InvestmentEngineSetup-1.1.4.exe
```

Tek ana binary vardır: `InvestmentEngine.exe`. `InvestmentEngineCLI.cmd` ikinci bir engine değildir; GUI-subsystem EXE'yi terminalde `start /wait` ile blocking çalıştıran küçük wrapper'dır.

## PyInstaller önemli modüller

Build hem `build.bat` hem `scripts\build_exe.ps1` tarafında WebSocket dahil gerekli hidden import/collect tanımlarını içerir:

```text
psycopg / psycopg_pool
apscheduler
tzdata
pywin32 service modülleri
cryptography
websocket-client
```

## Inno Setup

Installer:

- EXE'yi `{autopf}\Rosa\InvestmentEngine` altına kopyalar.
- `InvestmentEngineCLI.cmd`, migration ve docs dosyalarını kurar.
- upgrade'de çalışan `RosaInvestmentEngine` servisini durdurur.
- ilk kurulumda settings yoksa `--configure` açar.
- aynı EXE'yi `--install-service` ile service olarak kaydeder.
- settings/rosalock varsa servisi başlatır.
- settings ve rosalock release paketinde bulunmaz ve upgrade'de korunur.

## Windows-only doğrulama

Container/Linux üzerinde unit/static test yapılabilir; gerçek DPAPI LocalMachine, Windows Service SCM, PyInstaller Windows EXE, Inno Setup ve public WebSocket smoke test Windows makinede doğrulanmalıdır.


v1.1.4 installer ayrıca `InvestmentEngineCLI.ps1` dosyasını kurar; CMD wrapper bu script ile yeni CLI log satırlarını terminale replay eder.
