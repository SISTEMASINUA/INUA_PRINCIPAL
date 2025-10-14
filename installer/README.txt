INUA - Instalación rápida (copiable a otras PCs)

Opción A - Instalador Online (recomendado):
  1) Copia este archivo a la otra PC: installer\INUA-Instalar.ps1
  2) En la PC destino, abre PowerShell y ejecuta:
     Set-ExecutionPolicy -Scope CurrentUser Bypass -Force
     cd C:\ruta\donde\copiaste
     powershell -NoProfile -ExecutionPolicy Bypass -File .\INUA-Instalar.ps1
  3) Sigue el asistente (Configure-Cloud), edita .env y luego usa Switch-Site.ps1 si aplica.

Opción B - Paquete Offline (sin internet):
  1) En esta PC, ejecuta: installer\INUA-CrearPaqueteOffline.ps1
  2) Lleva el ZIP generado en dist\ a la otra PC.
  3) Descomprime en C:\AsistenciaNFC y ejecuta:
     powershell -NoProfile -ExecutionPolicy Bypass -File .\Configure-Cloud.ps1
     (y luego .\Create-Desktop-Shortcuts.ps1)

Cambiar de sitio/lector rápidamente:
  C:\AsistenciaNFC> .\Switch-Site.ps1 -Site Tepanecos
  C:\AsistenciaNFC> .\Switch-Site.ps1 -Site Lerdo

Actualización diaria automática:
  (Ejecutar PowerShell como Administrador)
  C:\AsistenciaNFC> .\Install-AutoUpdateTask.ps1 -RepoUrl "https://github.com/SISTEMASINUA/INUA_PRINCIPAL.git" -Branch "main" -Hour 6 -Minute 30