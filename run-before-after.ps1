param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$InputFolder,

    [string]$OutputFolder = "",
    [int]$Size = 2048,
    [int]$Quality = 92,
    [int]$Similarity = 14
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path $InputFolder)) {
    Write-Error "Input folder not found: $InputFolder"
}

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..."
    python -m venv (Join-Path $Root ".venv")
    & $venvPython -m pip install -q -r (Join-Path $Root "requirements.txt")
}

$argsList = @("-m", "before_after", (Resolve-Path $InputFolder).Path)
if ($OutputFolder) {
    if (-not (Test-Path $OutputFolder)) {
        New-Item -ItemType Directory -Force -Path $OutputFolder | Out-Null
    }
    $argsList += @("-o", (Resolve-Path $OutputFolder).Path)
}
$argsList += @("--size", "$Size", "--quality", "$Quality", "--similarity", "$Similarity")

Push-Location $Root
try {
    & $venvPython @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
