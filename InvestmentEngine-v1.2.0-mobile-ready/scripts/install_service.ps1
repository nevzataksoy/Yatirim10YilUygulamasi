$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $Root "dist\InvestmentEngine.exe"
if (!(Test-Path $Exe)) { throw "dist\InvestmentEngine.exe bulunamadı. Önce build.bat çalıştırın." }
if (!(Test-Path (Join-Path (Split-Path $Exe -Parent) "settings"))) {
  Write-Host "İlk ayarlar açılıyor..."
  $p = Start-Process -FilePath $Exe -ArgumentList "--configure" -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Ayar ekranı başarıyla tamamlanmadı. ExitCode=$($p.ExitCode)" }
}
$p = Start-Process -FilePath $Exe -ArgumentList "--install-service" -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "Service kurulumu başarısız. ExitCode=$($p.ExitCode)" }
if ((Test-Path (Join-Path (Split-Path $Exe -Parent) "settings")) -and (Test-Path (Join-Path (Split-Path $Exe -Parent) "rosalock"))) {
  $p = Start-Process -FilePath $Exe -ArgumentList "--start-service" -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Service başlatma başarısız. ExitCode=$($p.ExitCode)" }
}
Write-Host "RosaInvestmentEngine service kurulumu tamamlandı."
