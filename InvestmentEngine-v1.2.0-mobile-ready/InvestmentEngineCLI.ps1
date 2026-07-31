param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$EngineArgs
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'InvestmentEngine.exe'
$log = Join-Path $root 'logs\investment-engine-cli.log'

$before = 0
if (Test-Path $log) {
    $before = @(Get-Content -LiteralPath $log -Encoding UTF8).Count
}

$process = Start-Process -FilePath $exe -ArgumentList $EngineArgs -Wait -PassThru

if (Test-Path $log) {
    Get-Content -LiteralPath $log -Encoding UTF8 | Select-Object -Skip $before
}
exit $process.ExitCode
