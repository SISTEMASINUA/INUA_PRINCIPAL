# Crea UN solo acceso directo en el Escritorio para lanzar la app
# Dentro de la app puedes abrir Administración y cambiar Sitio desde el menú

$ErrorActionPreference = 'Stop'

$root    = Split-Path -Parent $MyInvocation.MyCommand.Path 
$batPath = Join-Path $root 'run_app.bat'
$ps311   = Join-Path $root 'Run-App-311.ps1'
$assets  = Join-Path $root 'assets'
$icoPath = Join-Path $assets 'app_icon.ico'
$pngPath = Join-Path $assets 'app_icon.png'
$makeIco = Join-Path $root 'tools/make_icon.py'

# Escritorio del usuario actual
$desktop = [Environment]::GetFolderPath('Desktop')

# Asegurar que existe al menos un lanzador base
if (!(Test-Path $batPath) -and !(Test-Path $ps311)) {
    throw "No se encontraron los lanzadores base (run_app.bat o Run-App-311.ps1) en $root"
}

# Utilidad para crear shortcut
function New-Shortcut([string]$LinkPath, [string]$TargetPath, [string]$Arguments, [string]$WorkingDirectory, [string]$IconLocation) {
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($LinkPath)
    $shortcut.TargetPath = $TargetPath
    if ($Arguments) { $shortcut.Arguments = $Arguments }
    if ($WorkingDirectory) { $shortcut.WorkingDirectory = $WorkingDirectory }
    if ($IconLocation) { $shortcut.IconLocation = $IconLocation }
    $shortcut.Save()
}

# Icono: si hay assets/app_icon.png lo convertimos a .ico y lo usamos; si no, fallback a python.exe/cmd
$py311exe = Join-Path $root '..\.venv311\Scripts\python.exe'
if (Test-Path $pngPath) {
    try {
        if (!(Test-Path $icoPath)) {
            if (Test-Path $py311exe) {
                & $py311exe $makeIco | Out-Null
            } else {
                $pyvenv = Join-Path $root '..\.venv\Scripts\python.exe'
                if (Test-Path $pyvenv) { & $pyvenv $makeIco | Out-Null }
            }
        }
    } catch {}
}
$icon = if (Test-Path $icoPath) { $icoPath } elseif (Test-Path $py311exe) { $py311exe } else { "$env:SystemRoot\System32\cmd.exe" }

# Limpiar accesos directos antiguos (Admin y por sitio)
$oldLinks = @(
    'Asistencia NFC (Admin).lnk',
    'Asistencia NFC - Tepanecos.lnk',
    'Asistencia NFC - Lerdo.lnk',
    'Asistencia NFC - DESTINO.lnk'
)
foreach ($name in $oldLinks) {
    $p = Join-Path $desktop $name
    if (Test-Path $p) {
        try { Remove-Item $p -Force -ErrorAction Stop } catch {}
    }
}

# Crear único acceso directo (usa run_app.bat por compatibilidad doble clic)
$lnkPublic = Join-Path $desktop 'ASISTENCIA.lnk'
New-Shortcut -LinkPath $lnkPublic -TargetPath $batPath -Arguments '' -WorkingDirectory $root -IconLocation $icon

Write-Host "Acceso directo creado en: $desktop\ASISTENCIA.lnk" -ForegroundColor Green
