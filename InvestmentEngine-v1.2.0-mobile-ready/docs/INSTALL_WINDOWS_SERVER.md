# Windows Kurulum ve Upgrade — Investment Engine v1.2.0

## Build

Developer bilgisayarda Yönetici CMD ile:

```bat
build.bat
```

Başarılı build sonrası `installer\InvestmentEngineSetup-1.2.0.exe` oluşur.

## v1.1.3 → v1.2.0

Yeni migration yoktur; 0001–0006 yeterlidir. Setup dosyasını mevcut kurulumun üzerine çalıştırın. Aynı AppId upgrade davranışı sağlar; `settings` ve `rosalock` korunur.

Kurulum dizini:

```text
C:\Program Files\Rosa\InvestmentEngine\
├─ InvestmentEngine.exe
├─ InvestmentEngineCLI.cmd
├─ InvestmentEngineCLI.ps1
├─ settings
├─ rosalock
├─ logs\
└─ runtime\
```

## CLI

Ana binary hâlâ tek `InvestmentEngine.exe` dosyasıdır. `InvestmentEngineCLI.cmd` PowerShell wrapper üzerinden GUI-subsystem EXE'yi bekler ve komut boyunca `logs\investment-engine-cli.log` dosyasına eklenen yeni satırları işlem bittiğinde terminale basar.

```bat
InvestmentEngineCLI.cmd --service-status
InvestmentEngineCLI.cmd --stop-service
InvestmentEngineCLI.cmd --once hourly
InvestmentEngineCLI.cmd --once macro
InvestmentEngineCLI.cmd --once crypto
InvestmentEngineCLI.cmd --once ura
InvestmentEngineCLI.cmd --once events
InvestmentEngineCLI.cmd --test-realtime --realtime-seconds 20
InvestmentEngineCLI.cmd --start-service
```

## Crypto dependency preflight

`daily_crypto_job`, son 3 saat içinde aynı provider'dan tam BTC+ETH derivatives pair yoksa best-effort `hourly_job` refresh çağırır. Böylece servis restartı veya kaçırılmış hourly run nedeniyle eski derivatives verisinin fark edilmeden kullanılması engellenir. Refresh başarısız olursa derivatives factor quality=0 kalır ve data-quality gate aksiyonu bloklayabilir.

## SEC event quality

SEC monitor quality artık kontrol edilen entity sayısına göre verilmez. Exact SEC eşleşen URA holdings'lerinin gerçek fon ağırlığı coverage'ı kullanılır. SEC yalnızca resmi filing kaynağı olduğu için quality 70 ile cap edilir.
