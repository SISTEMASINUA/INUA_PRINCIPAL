# Ejecuta la app con Python 3.11 (lector real). Uso: ./Run-App-311.ps1 [-Admin]
param(
    [switch]$Admin
)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py311 = Join-Path $root '..\.venv311\Scripts\python.exe'
$pyvenv = Join-Path $root '..\.venv\Scripts\python.exe'
$appDir = $root

if (!(Test-Path $py311) -and !(Test-Path $pyvenv)) { throw "No se encontró Python en $py311 ni $pyvenv" }
if (Test-Path $py311) { $py = $py311 } else { $py = $pyvenv }

Push-Location $appDir
try {
    if ($Admin) { & $py '.\main.py' '--admin' } else { & $py '.\main.py' }
}
finally {
    Pop-Location
}
