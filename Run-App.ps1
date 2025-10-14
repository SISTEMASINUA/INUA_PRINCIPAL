# Ejecuta la app en modo normal (pantalla pública)
param(
    [switch]$Admin
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root '..\..\.venv\Scripts\python.exe'
$appDir = $root

if (!(Test-Path $venvPython)) {
    Write-Error "No se encontró el intérprete del venv: $venvPython"
    exit 1
}

Push-Location $appDir
try {
    if ($Admin) {
        & $venvPython '.\main.py' '--admin'
    } else {
        & $venvPython '.\main.py'
    }
}
finally {
    Pop-Location
}
