<#
.SYNOPSIS
    Reports SirrMizan status. Exit codes: 0 running, 1 stopped, 2 stale pidfile.
#>
[CmdletBinding()]
param(
    [string]$PidFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $PidFile) { $PidFile = Join-Path $ProjectRoot '.run\sirrmizan.pid' }

if (-not (Test-Path $PidFile)) {
    Write-Host "SirrMizan is not running"
    exit 1
}

$processId = (Get-Content $PidFile -Raw).Trim()
if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
    Write-Host "SirrMizan is running (pid $processId)"
    exit 0
}

Write-Host "SirrMizan is not running (stale pidfile: $PidFile)"
exit 2
