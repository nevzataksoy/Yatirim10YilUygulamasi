param([Parameter(Mandatory=$true)][string]$ConnectionString)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Get-ChildItem "$Root\migrations\*.sql" | Sort-Object Name | ForEach-Object {
  Write-Host "Applying $($_.Name)"
  & psql $ConnectionString -v ON_ERROR_STOP=1 -f $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "Migration failed: $($_.Name)" }
}
