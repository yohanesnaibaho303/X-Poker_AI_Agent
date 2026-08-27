[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Run .\scripts\bootstrap.ps1 first."
}

Push-Location $projectRoot
try {
    & (Join-Path $PSScriptRoot "check.ps1")
    & $python -m xpoker_agent.simulation | Out-Null
    & $python -c "from xpoker_agent.controller import SafetyGateInput, evaluate_safety_gates; result=evaluate_safety_gates(SafetyGateInput()); assert not result.passed and result.outcome == 'blocked'"
    Write-Output "Offline demo rehearsal passed; live control remains disabled."
} finally {
    Pop-Location
}
