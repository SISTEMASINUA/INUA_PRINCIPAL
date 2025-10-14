# Crea una tarea programada que actualiza el sistema diariamente desde GitHub
# Uso: ./Install-AutoUpdateTask.ps1 -RepoUrl "https://github.com/<owner>/<repo>.git" -Branch "main" -Hour 6 -Minute 30
param(
  [Parameter(Mandatory=$true)][string]$RepoUrl,
  [string]$Branch = "main",
  [int]$Hour = 6,
  [int]$Minute = 30
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = "AsistenciaNFC-AutoUpdate"

# Acción: ejecutar PowerShell que invoca Update-From-GitHub.ps1
$ps = (Get-Command powershell.exe).Source
$script = "-NoProfile -ExecutionPolicy Bypass -File `"$root\Update-From-GitHub.ps1`" -RepoUrl `"$RepoUrl`" -Branch `"$Branch`""
$action = New-ScheduledTaskAction -Execute $ps -Argument $script
$runAt = (Get-Date).Date.AddHours($Hour).AddMinutes($Minute)
$trigger = New-ScheduledTaskTrigger -Daily -At $runAt

# Registrar/actualizar tarea
try {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
} catch {}
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description "Actualiza AsistenciaNFC desde GitHub" -RunLevel Highest | Out-Null
Write-Host ("Tarea programada creada: {0} a las {1}:{2:00}" -f $taskName, $Hour, $Minute) -ForegroundColor Green