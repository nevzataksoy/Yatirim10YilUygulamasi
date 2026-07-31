$Root = Split-Path -Parent $PSScriptRoot
$svc = Get-Service -Name RosaInvestmentEngine -ErrorAction SilentlyContinue
if (!$svc) { Write-Error "RosaInvestmentEngine servisi bulunamadı"; exit 2 }
$svc | Format-List Name,Status,StartType
$Candidates = @(
  (Join-Path $Root "dist\logs\investment-engine.log"),
  "C:\Program Files\Rosa\InvestmentEngine\logs\investment-engine.log"
)
foreach ($log in $Candidates) {
  if (Test-Path $log) {
    Write-Host "Log: $log"
    Get-Content $log -Tail 40
    break
  }
}
