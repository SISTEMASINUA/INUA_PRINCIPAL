# Actualiza la carpeta del sistema desde GitHub preservando .env y config/readers.json
# Uso: ./Update-From-GitHub.ps1 -RepoUrl "https://github.com/<owner>/<repo>.git" [-Branch "main"]
param(
  [Parameter(Mandatory=$true)][string]$RepoUrl,
  [string]$Branch = "main"
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Write-Info($m){ Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Ok($m){ Write-Host "[OK]   $m" -ForegroundColor Green }
function Write-Warn($m){ Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err($m){ Write-Host "[ERR]  $m" -ForegroundColor Red }

# Requiere git
$git = (Get-Command git -ErrorAction SilentlyContinue)
if (-not $git) { throw "Git no está instalado o no está en PATH." }

# Preservar archivos locales
$keep = @('.env','config/readers.json','database/local.db','fotos_empleados','asistencia_empleados','reportes')
$backup = Join-Path $env:TEMP ("nfc_update_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($k in $keep) {
  $src = Join-Path $root $k
  if (Test-Path $src) {
    $dst = Join-Path $backup $k
    New-Item -ItemType Directory -Path (Split-Path $dst -Parent) -Force | Out-Null
    Copy-Item $src $dst -Recurse -Force
  }
}

# Estrategia: si es repo git, hacer pull; si no, clonar en temp y copiar
if (Test-Path (Join-Path $root '.git')) {
  Write-Info "Repositorio detectado, haciendo pull..."
  git fetch --all
  git reset --hard origin/$Branch
  git checkout $Branch
  git pull origin $Branch
} else {
  Write-Info "Clonando repositorio fresco..."
  $tmp = Join-Path $env:TEMP ("nfc_clone_" + [guid]::NewGuid().ToString('N'))
  git clone --branch $Branch --depth 1 $RepoUrl $tmp
  # Copiar contenido al root actual (excepto preservados ya respaldados)
  Get-ChildItem $tmp -Force | ForEach-Object {
    if ($_.Name -notin @('.git')) {
      Copy-Item $_.FullName $root -Recurse -Force
    }
  }
}

# Restaurar preservados
foreach ($k in $keep) {
  $dst = Join-Path $root $k
  $src = Join-Path $backup $k
  if (Test-Path $src) {
    New-Item -ItemType Directory -Path (Split-Path $dst -Parent) -Force | Out-Null
    Copy-Item $src $dst -Recurse -Force
  }
}
Write-Ok "Código actualizado desde GitHub y archivos locales preservados"

# Reinstalar deps si cambió requirements
if (Test-Path (Join-Path $root 'requirements.txt')) {
  $py = Join-Path $root '.\.venv\Scripts\python.exe'
  if (Test-Path $py) {
    & $py -m pip install -r requirements.txt
    Write-Ok "Dependencias verificadas"
  }
}

# Recrear acceso directo si se requiere
$short = Join-Path $root 'Create-Desktop-Shortcuts.ps1'
if (Test-Path $short) { & powershell -NoProfile -ExecutionPolicy Bypass -File $short }
Write-Ok "Update finalizado. Reinicia la app si estaba abierta."