# Instalador sencillo desde Internet (sin Git)
# Descarga y ejecuta el Bootstrap-From-Zip para desplegar en C:\AsistenciaNFC

$ErrorActionPreference = 'Stop'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$dest = 'C:\AsistenciaNFC'
$zipUrl = 'https://github.com/SISTEMASINUA/INUA_PRINCIPAL/archive/refs/heads/main.zip'
$bootstrapUrl = 'https://raw.githubusercontent.com/SISTEMASINUA/INUA_PRINCIPAL/main/Bootstrap-From-Zip.ps1'

Write-Host "Instalando en: $dest" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $dest -Force | Out-Null

$tmp = Join-Path $env:TEMP 'INUA_bootstrap.ps1'
Invoke-WebRequest -Uri $bootstrapUrl -OutFile $tmp
powershell -NoProfile -ExecutionPolicy Bypass -File $tmp -InstallPath $dest -RepoZipUrl $zipUrl

Write-Host "Instalación completada." -ForegroundColor Green
Write-Host "Abre el acceso directo 'ASISTENCIA' del escritorio y configura .env si no lo hiciste aún." -ForegroundColor Yellow