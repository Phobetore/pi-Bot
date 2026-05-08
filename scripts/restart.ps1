<#
.SYNOPSIS
    Restarts SirrMizan. Tolerates a not-currently-running bot (start anyway).
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot '.run\sirrmizan.pid'

if (Test-Path $PidFile) {
    & "$PSScriptRoot\stop.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "stop.ps1 exited with $LASTEXITCODE; continuing with start anyway"
    }
}

& "$PSScriptRoot\start.ps1"
exit $LASTEXITCODE
