param(
    [string]$LogDir = "C:\Program Files\Rosa\InvestmentEngine\logs",
    [int]$Top = 20
)

$ErrorActionPreference = 'Stop'

$files = Get-ChildItem -LiteralPath $LogDir -Filter 'connection-pool-telemetry-*.jsonl*' -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime

if (-not $files) {
    Write-Host "Pool telemetry dosyası bulunamadı: $LogDir"
    exit 2
}

Write-Host "=== FILES ==="
$files | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

$rows = foreach ($file in $files) {
    Get-Content -LiteralPath $file.FullName -Encoding UTF8 | ForEach-Object {
        if ([string]::IsNullOrWhiteSpace($_)) { return }
        try {
            $row = $_ | ConvertFrom-Json
            $row | Add-Member -NotePropertyName source_file -NotePropertyValue $file.Name -Force
            $row
        }
        catch {
            Write-Warning "JSON satırı okunamadı: $($file.Name)"
        }
    }
}

if (-not $rows) {
    Write-Host "Telemetry satırı bulunamadı."
    exit 3
}

Write-Host "`n=== EVENT COUNTS ==="
$rows |
    Group-Object event |
    Sort-Object Count -Descending |
    Select-Object Name, Count |
    Format-Table -AutoSize

Write-Host "`n=== CHECKOUT TIMEOUTS ==="
$rows |
    Where-Object event -eq 'checkout_timeout' |
    Sort-Object ts -Descending |
    Select-Object -First $Top ts, root_job_name, run_kind, callsite, thread, wait_ms, error,
        @{N='pool_size';E={$_.stats_timeout.pool_size}},
        @{N='available';E={$_.stats_timeout.pool_available}},
        @{N='waiting';E={$_.stats_timeout.requests_waiting}},
        @{N='req_errors';E={$_.stats_timeout.requests_errors}},
        @{N='conn_errors';E={$_.stats_timeout.connections_errors}},
        @{N='conn_lost';E={$_.stats_timeout.connections_lost}},
        source_file |
    Format-Table -AutoSize

Write-Host "`n=== SLOW/PRESSURED CHECKOUTS ==="
$rows |
    Where-Object event -eq 'checkout_pressure' |
    Sort-Object {[double]$_.wait_ms} -Descending |
    Select-Object -First $Top ts, root_job_name, run_kind, callsite, thread, wait_ms,
        @{N='pool_size';E={$_.stats_acquired.pool_size}},
        @{N='available';E={$_.stats_acquired.pool_available}},
        @{N='waiting';E={$_.stats_acquired.requests_waiting}},
        source_file |
    Format-Table -AutoSize

Write-Host "`n=== SLOW CONNECTION HOLDS ==="
$rows |
    Where-Object event -eq 'hold_slow' |
    Sort-Object {[double]$_.hold_ms} -Descending |
    Select-Object -First $Top ts, root_job_name, run_kind, callsite, thread, wait_ms, hold_ms,
        @{N='pool_size';E={$_.stats_after.pool_size}},
        @{N='available';E={$_.stats_after.pool_available}},
        @{N='waiting';E={$_.stats_after.requests_waiting}},
        source_file |
    Format-Table -AutoSize

Write-Host "`n=== POOL COUNTER DELTAS ==="
$rows |
    Where-Object event -eq 'counter_delta' |
    Sort-Object ts -Descending |
    Select-Object -First $Top ts, root_job_name, run_kind, callsite, thread,
        @{N='queued_delta';E={$_.deltas.requests_queued}},
        @{N='request_error_delta';E={$_.deltas.requests_errors}},
        @{N='returns_bad_delta';E={$_.deltas.returns_bad}},
        @{N='conn_error_delta';E={$_.deltas.connections_errors}},
        @{N='conn_lost_delta';E={$_.deltas.connections_lost}},
        @{N='pool_size';E={$_.stats.pool_size}},
        @{N='available';E={$_.stats.pool_available}},
        source_file |
    Format-Table -AutoSize

Write-Host "`n=== LATEST PERIODIC SAMPLES ==="
$rows |
    Where-Object event -eq 'sample' |
    Sort-Object ts -Descending |
    Select-Object -First $Top ts, root_job_name, run_kind, callsite, thread, wait_ms, hold_ms,
        @{N='pool_size';E={$_.stats.pool_size}},
        @{N='available';E={$_.stats.pool_available}},
        @{N='waiting';E={$_.stats.requests_waiting}},
        @{N='queued';E={$_.stats.requests_queued}},
        @{N='request_errors';E={$_.stats.requests_errors}},
        @{N='returns_bad';E={$_.stats.returns_bad}},
        @{N='conn_errors';E={$_.stats.connections_errors}},
        @{N='conn_lost';E={$_.stats.connections_lost}},
        source_file |
    Format-Table -AutoSize
