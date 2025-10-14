# Lanzador por sitio con selección de lector (por índice o nombre)
param(
  [ValidateSet('Tepanecos','Lerdo','DESTINO')]
  [string]$Site = 'Tepanecos',
  [int]$ReaderIndex = 1,
  [string]$ReaderName
)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py311 = Join-Path $root '..\.venv311\Scripts\python.exe'
$pyvenv = Join-Path $root '..\.venv\Scripts\python.exe'
$appDir = $root
if (!(Test-Path $py311) -and !(Test-Path $pyvenv)) { throw "No se encontró Python en $py311 ni $pyvenv" }
if (Test-Path $py311) { $py = $py311 } else { $py = $pyvenv }

# Variables de entorno para el proceso
$env:UBICACION_PRINCIPAL = $Site
if ($ReaderName) {
  $env:NFC_READER_NAME = $ReaderName
  Remove-Item Env:NFC_READER_INDEX -ErrorAction SilentlyContinue
} else {
  $env:NFC_READER_INDEX = [string]$ReaderIndex
  Remove-Item Env:NFC_READER_NAME -ErrorAction SilentlyContinue
}

Push-Location $appDir
try {
  & $py '.\main.py'
}
finally {
  Pop-Location
}
