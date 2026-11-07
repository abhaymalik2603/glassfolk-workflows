param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$PhotoOne,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$PhotoTwo,

    [string]$Output = "before_after.jpg",
    [switch]$NoAuto,
    [int]$Size = 2048,
    [int]$Quality = 92
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    python -m venv (Join-Path $Root ".venv")
    & $venvPython -m pip install -q -r (Join-Path $Root "requirements.txt")
}

$argsList = @(
    "-m", "before_after",
    (Resolve-Path $PhotoOne).Path,
    (Resolve-Path $PhotoTwo).Path,
    "-o", (Join-Path (Get-Location) $Output),
    "--size", "$Size",
    "--quality", "$Quality"
)
if ($NoAuto) { $argsList += "--no-auto" }

Push-Location $Root
try {
    & $venvPython @argsList
}
finally {
    Pop-Location
}
