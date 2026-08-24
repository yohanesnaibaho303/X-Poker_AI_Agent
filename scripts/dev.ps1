[CmdletBinding()]
param(
    [switch]$SkipChecks
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    & (Join-Path $PSScriptRoot "bootstrap.ps1")
}
if (-not $SkipChecks) {
    & (Join-Path $PSScriptRoot "check.ps1")
}

Push-Location $projectRoot
try {
    & $python -m uvicorn xpoker_agent.api:app --host 127.0.0.1 --port 8765
} finally {
    Pop-Location
}
