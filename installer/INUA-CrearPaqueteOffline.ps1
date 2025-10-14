# Crea un paquete ZIP offline del proyecto actual para llevarlo en USB
# Uso: ./INUA-CrearPaqueteOffline.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Split-Path -Parent $root
$outDir = Join-Path $proj 'dist'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$zipPath = Join-Path $outDir ('INUA_PaqueteOffline_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.zip')

Write-Host "Creando paquete offline: $zipPath" -ForegroundColor Cyan

$exclude = @('.git', 'dist', '__pycache__', '.venv', 'fotos_empleados', 'reportes', 'database\local.db')

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Add-ToZip($sourcePath, $entryPath) {
  $mode = [System.IO.Compression.ZipArchiveMode]::Update
  if (-not (Test-Path $zipPath)) {
    [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create).Dispose()
  }
  $zip = [System.IO.Compression.ZipFile]::Open($zipPath, $mode)
  try {
    if (Test-Path $sourcePath -PathType Container) {
      Get-ChildItem -Path $sourcePath -Recurse -Force | ForEach-Object {
        $rel = $_.FullName.Substring($proj.Length).TrimStart('\\')
        foreach ($ex in $exclude) { if ($rel -like "$ex*") { $rel = $null; break } }
        if ($rel) {
          if (-not $_.PSIsContainer) {
            $dest = $rel
            $dir = Split-Path $dest -Parent
            $null = $zip.CreateEntryFromFile($_.FullName, $dest)
          }
        }
      }
    }
  } finally { $zip.Dispose() }
}

Add-ToZip $proj '.'

Write-Host "Paquete creado." -ForegroundColor Green
Write-Host "Incluye en el USB este ZIP y el instalador online opcional: installer\\INUA-Instalar.ps1" -ForegroundColor Yellow