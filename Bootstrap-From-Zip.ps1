# Descarga y despliega el sistema desde el ZIP de GitHub sin requerir Git.
# Uso:
#   ./Bootstrap-From-Zip.ps1 -InstallPath "C:\AsistenciaNFC" -RepoZipUrl "https://github.com/SISTEMASINUA/INUA_PRINCIPAL/archive/refs/heads/main.zip"
param(
  [string]$InstallPath = "C:\AsistenciaNFC",
  [string]$RepoZipUrl = "https://github.com/SISTEMASINUA/INUA_PRINCIPAL/archive/refs/heads/main.zip"
)

$ErrorActionPreference = 'Stop'
function Write-Info($m){ Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Ok($m){ Write-Host "[OK]   $m" -ForegroundColor Green }
function Write-Warn($m){ Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err($m){ Write-Host "[ERR]  $m" -ForegroundColor Red }

try {
  # Forzar TLS 1.2
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {}

Write-Info "Instalando en: $InstallPath"
New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null

$tmp = Join-Path $env:TEMP ("inua_zip_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
$zip = Join-Path $tmp 'repo.zip'

Write-Info "Descargando ZIP: $RepoZipUrl"
Invoke-WebRequest -Uri $RepoZipUrl -OutFile $zip

Write-Info "Extrayendo ZIP..."
Expand-Archive -Path $zip -DestinationPath $tmp -Force

# Detectar carpeta raíz del zip (GitHub agrega sufijo -main)
$rootExtract = Get-ChildItem $tmp | Where-Object { $_.PSIsContainer -and $_.Name -match 'INUA_PRINCIPAL' } | Select-Object -First 1
if (-not $rootExtract) { throw "No se encontró la carpeta del repo extraído." }

# Preservar locales
$keep = @('.env','config/readers.json','database/local.db','fotos_empleados','asistencia_empleados','reportes')
$backup = Join-Path $env:TEMP ("inua_backup_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($k in $keep) {
  $src = Join-Path $InstallPath $k
  if (Test-Path $src) {
    $dst = Join-Path $backup $k
    New-Item -ItemType Directory -Path (Split-Path $dst -Parent) -Force | Out-Null
    Copy-Item $src $dst -Recurse -Force
  }
}

Write-Info "Copiando archivos al destino..."
Get-ChildItem $rootExtract.FullName -Force | ForEach-Object {
  if ($_.Name -notin @('.git')) {
    Copy-Item $_.FullName (Join-Path $InstallPath $_.Name) -Recurse -Force
  }
}

# Restaurar preservados
foreach ($k in $keep) {
  $dst = Join-Path $InstallPath $k
  $src = Join-Path $backup $k
  if (Test-Path $src) {
    New-Item -ItemType Directory -Path (Split-Path $dst -Parent) -Force | Out-Null
    Copy-Item $src $dst -Recurse -Force
  }
}

Write-Ok "Código desplegado desde ZIP"

# Posinstalación: configurar entorno y accesos
$cfg = Join-Path $InstallPath 'Configure-Cloud.ps1'
if (Test-Path $cfg) {
  Write-Info "Ejecutando Configure-Cloud.ps1"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $cfg
}

$link = Join-Path $InstallPath 'Create-Desktop-Shortcuts.ps1'
if (Test-Path $link) {
  Write-Info "Creando acceso directo"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $link
}

Write-Ok "Bootstrap finalizado. Puedes abrir el acceso directo 'ASISTENCIA' en el escritorio."