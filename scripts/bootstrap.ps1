[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$bundledPython = "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$systemPython = Get-Command python -ErrorAction SilentlyContinue

if (Test-Path -LiteralPath $bundledPython) {
    $python = $bundledPython
} elseif ($systemPython) {
    $python = $systemPython.Source
} else {
    throw "Python 3.12 is required. Install it or run this project from Codex with its bundled runtime."
}

$version = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($version -ne "3.12") {
    throw "Python 3.12 is required; found $version at $python."
}

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python -m venv (Join-Path $projectRoot ".venv")
}

& $venvPython -m pip install --disable-pip-version-check -r (Join-Path $projectRoot "requirements.lock")
& $venvPython -m pip install --disable-pip-version-check --no-deps -e $projectRoot

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    throw "Node.js and npm are required for the monitoring dashboard."
}
& $npm.Source --prefix (Join-Path $projectRoot "apps\monitor") ci
if ($LASTEXITCODE -ne 0) {
    throw "Dashboard dependency installation failed with exit code $LASTEXITCODE."
}
Write-Output "Development environment is ready: $venvPython"
