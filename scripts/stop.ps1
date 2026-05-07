<#
.SYNOPSIS
    Stops pi-Bot. Tries a graceful close first; falls back to a forceful kill
    after TimeoutSeconds.

.NOTES
    Windows has no real SIGTERM. We try ``taskkill /PID`` (no /F), which sends
    WM_CLOSE and works for processes with a window. Console-only Python
    processes will refuse and need ``Stop-Process -Force``. With the bot's
    periodic saver running every 60s by default, a forceful stop loses at
    most that much state — see PI_BOT_SAVE_INTERVAL.
#>
[CmdletBinding()]
param(
    [string]$PidFile,
    [int]$TimeoutSeconds = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $PidFile) { $PidFile = Join-Path $ProjectRoot '.run\pi-bot.pid' }

if (-not (Test-Path $PidFile)) {
    Write-Host "no pidfile at $PidFile — is pi-Bot running?"
    exit 1
}

$processId = (Get-Content $PidFile -Raw).Trim()
if (-not $processId) {
    Write-Host "pidfile is empty; removing"
    Remove-Item $PidFile -Force
    exit 1
}

if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
    Write-Host "process $processId is not running; removing stale pidfile"
    Remove-Item $PidFile -Force
    exit 0
}

Write-Host ("stopping pi-Bot (pid {0}, waiting up to {1}s)..." -f $processId, $TimeoutSeconds)

# Try a graceful close first. /T propagates to child processes.
& taskkill /PID $processId /T 2>&1 | Out-Null

# Wait for the process to exit on its own.
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
        Remove-Item $PidFile -Force
        Write-Host "pi-Bot stopped cleanly"
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

Write-Warning ("process did not stop within {0}s; force-killing (state up to last periodic save is preserved)" -f $TimeoutSeconds)
Stop-Process -Id $processId -Force
Remove-Item $PidFile -Force
exit 0
