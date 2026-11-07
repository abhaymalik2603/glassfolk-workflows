param(
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..."
    python -m venv (Join-Path $Root ".venv")
    & $venvPython -m pip install -q -r (Join-Path $Root "requirements.txt")
}

Push-Location $Root
try {
    Write-Host "Starting web tool at http://127.0.0.1:$Port"
    & $venvPython -m uvicorn before_after.web.app:app --host 127.0.0.1 --port $Port --reload
}
finally {
    Pop-Location
}
