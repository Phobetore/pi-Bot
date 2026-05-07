<#
.SYNOPSIS
    Starts pi-Bot in the background and writes its PID to a file.

.PARAMETER PidFile
    Where to write the PID. Defaults to .run\pi-bot.pid

.PARAMETER LogFile
    Where to send stdout (and stderr to LogFile.err). Defaults to logs\console.log

.PARAMETER Python
    Python interpreter to use. Defaults to .venv\Scripts\python.exe if present,
    otherwise the first python on PATH.
#>
[CmdletBinding()]
param(
    [string]$PidFile,
    [string]$LogFile,
    [string]$Python
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Move to the project root (this script lives in scripts/).
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $PidFile) { $PidFile = Join-Path $ProjectRoot '.run\pi-bot.pid' }
if (-not $LogFile) { $LogFile = Join-Path $ProjectRoot 'logs\console.log' }

# Create directories if needed.
$null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $PidFile)
$null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogFile)

# Bail out if a previous instance is already alive.
if (Test-Path $PidFile) {
    $existing = (Get-Content $PidFile -Raw -ErrorAction SilentlyContinue)
    if ($existing) {
        $existing = $existing.Trim()
        if ($existing -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)) {
            Write-Host "pi-Bot is already running (pid $existing)"
            exit 1
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# Pick the interpreter: explicit override > local venv > python on PATH.
if (-not $Python) {
    $venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) {
        $Python = $venvPython
    } else {
        $Python = 'python'
    }
}

$ErrLogFile = $LogFile + '.err'

# Start the bot detached, with stdout and stderr going to log files.
$proc = Start-Process `
    -FilePath $Python `
    -ArgumentList '-m', 'pi_bot' `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $ErrLogFile `
    -PassThru

# Persist the PID *before* sleeping so a fast crash still leaves a useful
# trace.
$proc.Id | Out-File -FilePath $PidFile -Encoding ascii -NoNewline

# Heartbeat check: did the process survive the first half-second?
Start-Sleep -Milliseconds 300
if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
    Write-Host "pi-Bot failed to start — see $LogFile and $ErrLogFile"
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "pi-Bot started (pid $($proc.Id), log: $LogFile)"
