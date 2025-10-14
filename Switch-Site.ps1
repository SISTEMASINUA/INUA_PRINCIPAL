# Cambia rápidamente el sitio (UBICACION_PRINCIPAL) y el archivo config/readers.json
# Uso: ./Switch-Site.ps1 -Site Tepanecos|Lerdo|DESTINO
param(
  [Parameter(Mandatory=$true)][ValidateSet('Tepanecos','Lerdo','DESTINO')][string]$Site
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Ok($m){ Write-Host "[OK]   $m" -ForegroundColor Green }
function Write-Info($m){ Write-Host "[INFO] $m" -ForegroundColor Cyan }

# Actualizar .env
$envPath = Join-Path $root '.env'
if (-not (Test-Path $envPath)) {
  Copy-Item (Join-Path $root '.env.example') $envPath -Force
}
$content = Get-Content $envPath -Raw
if ($content -match 'UBICACION_PRINCIPAL=') {
  $content = [regex]::Replace($content, 'UBICACION_PRINCIPAL=.*', "UBICACION_PRINCIPAL=$Site")
} else {
  $content += "`nUBICACION_PRINCIPAL=$Site`n"
}
Set-Content -Path $envPath -Value $content -Encoding UTF8
Write-Ok "UBICACION_PRINCIPAL actualizado a $Site en .env"

# Copiar readers de plantilla
$tpl = Join-Path $root "config\readers.$($Site.ToLower()).json"
if (-not (Test-Path $tpl)) {
  $tpl = Join-Path $root 'config\readers.json'
}
Copy-Item $tpl (Join-Path $root 'config\readers.json') -Force
Write-Ok "config/readers.json actualizado para $Site"

Write-Info "Reinicia la aplicación para aplicar los cambios."