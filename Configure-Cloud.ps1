# Configura el sistema para usar PostgreSQL en la nube y sincronización S3
# - Crea/actualiza .env con credenciales
# - Instala dependencias en .venv
# - Prueba conexión a PostgreSQL y ejecuta schema.sql si faltan tablas
# - Crea atajo de escritorio

param(
    [string]$DbHost = "localhost",
    [int]$DbPort = 5432,
    [string]$DbName = "asistencia_nfc",
    [string]$DbUser = "postgres",
    [string]$DbPassword = "",
    [string]$UbicacionPrincipal = "Tepanecos",
    [string]$AwsAccessKey = "",
    [string]$AwsSecretKey = "",
    [string]$AwsRegion = "us-east-1",
    [string]$AwsBucket = "asistencia-nfc-bucket",
    [string]$DbSSLMode = ""
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg){ Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host "[ERR]  $msg" -ForegroundColor Red }

# 1) Generar .env
$envPath = Join-Path $root ".env"
$envContent = @()
$envContent += "DB_HOST=$DbHost"
$envContent += "DB_PORT=$DbPort"
$envContent += "DB_NAME=$DbName"
$envContent += "DB_USER=$DbUser"
$envContent += "DB_PASSWORD=$DbPassword"
$envContent += "DB_SSLMODE=$DbSSLMode"
$envContent += "UBICACION_PRINCIPAL=$UbicacionPrincipal"
$envContent += "AWS_ACCESS_KEY_ID=$AwsAccessKey"
$envContent += "AWS_SECRET_ACCESS_KEY=$AwsSecretKey"
$envContent += "AWS_REGION=$AwsRegion"
$envContent += "AWS_BUCKET_NAME=$AwsBucket"
$envContent += "ADMIN_USER=admin"
$envContent += "ADMIN_PASSWORD=1515060055"
$envContent += "ADMIN_USER_RONALD=RONALD"
$envContent += "ADMIN_PASS_RONALD=2200"
$envContent += "ADMIN_USER_ADMIN=admin"
$envContent += "ADMIN_PASS_ADMIN=1515060055"
$envContent += "ADMIN_USER_SANDRA=SANDRA"
$envContent += "ADMIN_PASS_SANDRA=1515060055"
$envContent += "ADMIN_USER_RH=RH"
$envContent += "ADMIN_PASS_RH=1515060055"
$envContent = ($envContent -join "`r`n") + "`r`n"
Set-Content -Path $envPath -Value $envContent -Encoding UTF8
Write-Ok ".env generado en $envPath"

# 2) Crear/activar .venv e instalar requirements
$venv = Join-Path $root "..\.venv\Scripts\python.exe"
if (!(Test-Path $venv)) {
    Write-Info "Creando entorno virtual .venv"
    python -m venv ..\.venv
}
& $venv -m pip install --upgrade pip
& $venv -m pip install -r requirements.txt
Write-Ok "Dependencias instaladas"

# 3) Probar conexión a PostgreSQL y aplicar schema si falta
$testPy = @"
import os, psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
host=os.getenv('DB_HOST');port=os.getenv('DB_PORT');name=os.getenv('DB_NAME');user=os.getenv('DB_USER');pwd=os.getenv('DB_PASSWORD')
conn = psycopg2.connect(host=host, port=port, dbname=name, user=user, password=pwd)
cur = conn.cursor()
cur.execute("SELECT 1")
print("OK_POSTGRES")
# Verificar tablas esenciales
cur.execute("""
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema='public' AND table_name IN ('empleados','ubicaciones','registros_asistencia','configuraciones')
""")
count = cur.fetchone()[0]
print("TABLES=", count)
conn.close()
"@
$tmp = Join-Path $env:TEMP "pg_test_$([guid]::NewGuid().ToString('N')).py"
Set-Content -Path $tmp -Value $testPy -Encoding UTF8
$env:DB_HOST=$DbHost; $env:DB_PORT=$DbPort; $env:DB_NAME=$DbName; $env:DB_USER=$DbUser; $env:DB_PASSWORD=$DbPassword
try {
    $out = & $venv $tmp
    if ($out -notmatch "OK_POSTGRES") { throw "No se pudo conectar a PostgreSQL" }
    Write-Ok "Conexión a PostgreSQL verificada"
} catch {
    Write-Err $_.Exception.Message
    throw
} finally { Remove-Item $tmp -ErrorAction Ignore }

# Si faltan tablas, aplicar schema.sql
try {
    $psql = & where.exe psql 2>$null | Select-Object -First 1
} catch { $psql = $null }
$schemaPath = Join-Path $root 'database/schema.sql'
if ($psql -and (Test-Path $schemaPath)) {
    Write-Info "Aplicando schema.sql si faltan tablas"
    & $psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -f $schemaPath
    Write-Ok "Esquema verificado/aplicado"
} else {
    Write-Warn "psql no encontrado; asegúrate de que la BD ya tenga el esquema (empleados, ubicaciones, registros_asistencia, configuraciones)"
}

# 4) Crear acceso directo
$createLinks = Join-Path $root 'Create-Desktop-Shortcuts.ps1'
if (Test-Path $createLinks) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $createLinks
}
Write-Ok "Configuración nube completa. Ejecuta run_app.bat o el acceso directo 'ASISTENCIA'"
