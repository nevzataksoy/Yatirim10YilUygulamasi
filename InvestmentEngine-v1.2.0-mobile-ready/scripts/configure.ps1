$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $Root "dist\InvestmentEngine.exe"
if (Test-Path $Exe) {
  & $Exe --configure
} else {
  $Python = Join-Path $Root ".venv\Scripts\python.exe"
  if (!(Test-Path $Python)) { throw ".venv bulunamadı." }
  & $Python "$Root\run.py" --configure
}
