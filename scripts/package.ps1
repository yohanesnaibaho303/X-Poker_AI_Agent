[CmdletBinding()]
param(
    [string]$OutputDirectory = "release"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$output = Join-Path $projectRoot $OutputDirectory

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Run .\scripts\bootstrap.ps1 first."
}

Push-Location $projectRoot
try {
    & (Join-Path $PSScriptRoot "check.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Project checks failed with exit code $LASTEXITCODE."
    }
    New-Item -ItemType Directory -Force $output | Out-Null
    & $python -m pip wheel --disable-pip-version-check --no-deps --wheel-dir $output $projectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Wheel build failed with exit code $LASTEXITCODE."
    }
    Compress-Archive -Path (Join-Path $projectRoot "apps\monitor\dist\*") -DestinationPath (Join-Path $output "xpoker-monitor.zip") -Force
    & $python (Join-Path $PSScriptRoot "offline_readiness.py") --sessions 100 --output (Join-Path $output "offline-readiness.json")
    if ($LASTEXITCODE -ne 0) {
        throw "Offline readiness failed with exit code $LASTEXITCODE."
    }
    Copy-Item -LiteralPath (Join-Path $projectRoot "requirements.lock") -Destination $output -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "apps\monitor\package-lock.json") -Destination $output -Force
    Write-Output "Release artifacts created at $output"
} finally {
    Pop-Location
}
