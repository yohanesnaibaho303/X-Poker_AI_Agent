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
    $env:TEMP = Join-Path $projectRoot ".test-tmp"
    $env:TMP = $env:TEMP
    & $python -m ruff check .
    if ($LASTEXITCODE -ne 0) {
        throw "Ruff failed with exit code $LASTEXITCODE."
    }
    & $python -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "Pytest failed with exit code $LASTEXITCODE."
    }
    & npm --prefix (Join-Path $projectRoot "apps\monitor") run check
    if ($LASTEXITCODE -ne 0) {
        throw "Dashboard checks failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
