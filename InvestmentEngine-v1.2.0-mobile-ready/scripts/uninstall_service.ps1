$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $Root "dist\InvestmentEngine.exe"
if (Test-Path $Exe) {
  Start-Process -FilePath $Exe -ArgumentList "--stop-service" -Wait | Out-Null
  Start-Process -FilePath $Exe -ArgumentList "--uninstall-service" -Wait | Out-Null
}
Write-Host "Service kaldırıldı. settings ve rosalock otomatik silinmedi."
