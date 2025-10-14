# Sistema de Control de Asistencia NFC

## Descripción
Sistema completo de control de asistencia con tecnología NFC para múltiples ubicaciones. Incluye sincronización en tiempo real, reportes automáticos y almacenamiento en la nube.

## Características

### ✅ Funcionalidades Principales
- **Control de asistencia con NFC**: Registro instantáneo de entradas y salidas
- **Múltiples ubicaciones**: Tepanecos, Lerdo, Destino (ampliable)
- **Validación de horarios**: 10 minutos de tolerancia configurable
- **Sistema de colores**:
  - 🟢 Verde: A tiempo
  - 🟡 Amarillo: Retardo
  - 🔴 Rojo: Falta o salida temprana
- **Sincronización automática**: Funciona offline y sincroniza cuando hay internet
- **Reportes automáticos**: Exportación a Excel y PDF
- **Pantalla pública**: Visualización en tiempo real de registros
- **Administración segura**: Acceso protegido por contraseña

### 🎯 Validaciones de Asistencia
- **Entrada**: Tolerancia de 10 minutos
- **Salida**: Control de salidas tempranas
- **Faltas**: Detección automática de ausencias
- **Expedientes**: Generación automática por empleado

### 📊 Reportes
- Diarios y mensuales
- Individuales por empleado
- Exportación automática a carpetas organizadas
- Formatos Excel y PDF

## Instalación

### 1. Requisitos del Sistema
- Windows 10/11
- Python 3.8 o superior
- PostgreSQL 12 o superior
- Lector NFC compatible

### 2. Configurar PostgreSQL
```sql
-- Crear base de datos
CREATE DATABASE asistencia_nfc;

-- Ejecutar script de esquema
\i database/schema.sql
```

### 3. Instalar Dependencias
```bash
cd sistema_asistencia_nfc
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno
Editar el archivo `.env`:
```
# Base de datos PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=asistencia_nfc
DB_USER=postgres
DB_PASSWORD=tu_password

# AWS (opcional para sincronización en la nube)
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_REGION=us-east-1
AWS_BUCKET_NAME=asistencia-nfc-bucket

# Configuración del sistema
TOLERANCIA_ENTRADA=10
ADMIN_PASSWORD=admin123
```

## Guía rápida: dejarlo listo en la nube (Windows)

1) Abrir una consola PowerShell en la carpeta `sistema_asistencia_nfc` y ejecutar el configurador:

```
./Configure-Cloud.ps1 -DbHost 127.0.0.1 -DbPort 5432 -DbName asistencia_nfc -DbUser postgres -DbPassword "TU_PASSWORD" -UbicacionPrincipal "Tepanecos" -AwsAccessKey "" -AwsSecretKey "" -AwsRegion "us-east-1" -AwsBucket "asistencia-nfc-bucket"
```

- Esto crea/actualiza `.env`, instala dependencias en `.venv`, verifica PostgreSQL y aplica `database/schema.sql` si faltan tablas, y crea el acceso directo `ASISTENCIA.lnk` en el Escritorio.
- Si no usarás AWS S3, deja `-AwsAccessKey` y `-AwsSecretKey` vacíos; la app funcionará con PostgreSQL en la nube y sincronización local→nube.

2) Verifica el archivo `config/readers.json` para mapear lectores por sitio (opcional):

```
{
   "sites": {
      "Tepanecos": { "readerName": "ACS ACR122 0" },
      "Lerdo":     { "readerName": "ACS ACR122 1" }
   }
}
```

3) Ejecutar la app:

- Doble clic en el acceso directo `ASISTENCIA` del Escritorio, o
- Desde consola:

```
.\.venv\Scripts\python.exe main.py
```

4) Administración y sincronización

- Atajo: Ctrl+Alt+A para abrir administración.
- Usuarios iniciales se crean automáticamente desde `.env` (RONALD, admin, SANDRA, RH; contraseña por defecto 1515060055). Cambia las contraseñas desde la administración.
- La app sincroniza cada 60s: si hay internet escribe directo en PostgreSQL; si no, guarda local y sube cuando vuelve la conexión.
- Si configuraste AWS, también sube snapshots JSON y permite backup manual.

## Uso del Sistema

### Ejecutar el Sistema
```bash
python main.py
```

### Pantalla Principal (Pública)
- Muestra fecha y hora en tiempo real
- Última persona registrada con foto
- Lista de todos los registros del día
- Solo para visualización pública

### Acceso a Administración
- **Combinación de teclas**: `Ctrl + Alt + A`
- **Contraseña por defecto**: `admin123`

### Administración de Empleados
1. Agregar empleado:
   - Nombre completo
   - Cargo y rol
   - Horarios de entrada y salida
   - Fotografía
   - Asignar tarjeta NFC

2. Gestionar horarios:
   - Horario estándar: 09:00 - 18:00
   - Tolerancia: 10 minutos
   - Personalizable por empleado

### Registro de Asistencia
1. **Entrada**: Presentar tarjeta NFC al lector
2. **Salida**: Presentar tarjeta nuevamente
3. **Estados automáticos**:
   - A tiempo (verde)
   - Retardo (amarillo)
   - Salida temprana (rojo)

## Estructura de Archivos

```
sistema_asistencia_nfc/
├── main.py                 # Archivo principal
├── requirements.txt        # Dependencias
├── .env                   # Configuración
├── src/
│   ├── database_manager.py # Gestión de base de datos
│   ├── main_screen.py      # Pantalla principal
│   ├── admin_interface.py  # Interfaz de administración
│   ├── nfc_handler.py      # Manejo de NFC
│   ├── report_generator.py # Generación de reportes
│   └── cloud_sync.py       # Sincronización en la nube
├── database/
│   ├── schema.sql          # Esquema de base de datos
│   └── local.db           # Base de datos local (SQLite)
├── fotos_empleados/        # Fotografías de empleados
├── reportes/              # Reportes generales
├── asistencia_empleados/  # Reportes individuales
└── config/               # Archivos de configuración
```

## Características Técnicas

### Base de Datos
- **Principal**: PostgreSQL (en línea)
- **Local**: SQLite (modo offline)
- **Sincronización**: Automática cada 60 segundos

### Sincronización en la Nube
- **Almacenamiento**: AWS S3
- **Backup automático**: Domingos a las 23:00
- **Sincronización**: Tiempo real cuando hay internet

### Reportes Automáticos
- **Diarios**: Generación manual
- **Mensuales**: Automático el día 1 de cada mes
- **Ubicación**: Carpetas organizadas por empleado
- **Formatos**: Excel (.xlsx) y PDF

### Sistema de Colores
```
Verde (A_TIEMPO):
- Entrada: Dentro de horario + 10 min tolerancia
- Salida: A la hora o después

Amarillo (RETARDO):
- Entrada: Después de 10 min de tolerancia

Rojo (TEMPRANO/FALTA):
- Salida: Antes de la hora programada
- Falta: Sin registro de entrada
```

## Solución de Problemas

### Error de Conexión a PostgreSQL
1. Verificar que PostgreSQL esté ejecutándose
2. Comprobar credenciales en `.env`
3. El sistema funcionará en modo offline con SQLite

### Error de NFC
1. Verificar que el lector esté conectado
2. Para pruebas, usar la función de simulación manual
3. Verificar drivers del dispositivo NFC

### Sincronización AWS
1. Verificar credenciales de AWS en `.env`
2. Comprobar permisos del bucket S3
3. El sistema funciona sin AWS (solo local)

### Reportes no se Generan
1. Verificar permisos de escritura en carpetas
2. Comprobar instalación de pandas y reportlab
3. Verificar datos en base de datos

## Ubicaciones Configuradas

### Ubicación Principal: **Tepanecos**
- Estado: Activa
- Lector NFC: Operativo

### Ubicación Secundaria: **Lerdo**
- Estado: Activa  
- Lector NFC: Operativo

### Ubicación Futura: **Destino**
- Estado: Inactiva (preparada para activación)
- Se activará automáticamente cuando esté lista

## Mantenimiento

### Tareas Automáticas
- **Verificación de asistencias**: Cada hora
- **Reportes mensuales**: Día 1 de cada mes, 08:00
- **Backup en la nube**: Domingos, 23:00
- **Sincronización**: Cada 60 segundos

### Backup Manual
```python
# Desde la aplicación
cloud_sync.manual_sync()
cloud_sync.backup_to_s3()
```

### Exportar Reportes
```python
# Reporte diario
report_generator.generate_daily_report()

# Reporte mensual  
report_generator.generate_monthly_report()

# Reporte de empleado específico
report_generator.generate_employee_report(empleado_id)
```

## Soporte y Contacto

Para soporte técnico o consultas sobre el sistema, consulte la documentación técnica o contacte al administrador del sistema.

---

**Sistema de Control de Asistencia NFC v1.0**  
*Desarrollado con Python • PostgreSQL • AWS*

## Despliegue multi-PC (2 lectores + 1 reservado + 4 PCs admin)

Sigue estos pasos en cada tipo de equipo:

1) Servidor PostgreSQL (una sola vez)
- Crear BD y aplicar `database/schema.sql` (o usa `Configure-Cloud.ps1` si tienes `psql`).
- Usuarios/roles y firewall listos para aceptar conexiones desde las PCs.
- Si el proveedor exige SSL, añade `DB_SSLMODE=require` en `.env`.
- Como las PCs están en diferentes redes, el servidor PostgreSQL debe ser público o accesible vía VPN; valida IPs permitidas y puertos abiertos.

2) PCs con lector NFC (dos equipos, “Tepanecos” y “Lerdo”)
- Clona/copía la carpeta `sistema_asistencia_nfc`.
- Ejecuta `Configure-Cloud.ps1` con `-UbicacionPrincipal "Tepanecos"` en la primera PC y `"Lerdo"` en la segunda.
- Ajusta `config/readers.json` para que cada sitio apunte al lector correcto (`readerName`/`readerIndex`).
- Abre la app con el acceso directo “ASISTENCIA”. La pantalla pública corre y el lector registra al instante.

3) PC reservada “DESTINO” (sin lector por ahora)
- Mismo procedimiento, deja `config/readers.json` con el sitio `DESTINO` configurado; cuando conectes el lector, funcionará.

4) PCs de administración (4 equipos)
- Mismo repositorio y `.env` apuntando al mismo PostgreSQL.
- Ejecuta la app y usa Ctrl+Alt+A para la administración. No necesitan lector; podrán gestionar empleados, usuarios y reportes.

5) Verificación rápida
- En cada PC con lector, la barra inferior debe mostrar el sitio y el lector activo (si aplica).
- Registros se ven en tiempo real en la lista diaria. Si se cae internet, guardan local y suben luego.

6) Empaquetado/atajos
- El script `Create-Desktop-Shortcuts.ps1` crea un único acceso directo “ASISTENCIA”.
- `run_app.bat` usa `.venv` automáticamente.
- Opcional: generar EXE con PyInstaller (ver sección siguiente).

## (Opcional) Generar EXE con PyInstaller

En PowerShell dentro de `sistema_asistencia_nfc`:

```
.\.venv\Scripts\pip install pyinstaller
.\.venv\Scripts\pyinstaller --noconsole --onefile --name AsistenciaNFC main.py
```

El ejecutable quedará en `dist/AsistenciaNFC.exe`. Aún necesitarás drivers del lector y, si usas SQLite local o fotos, asegurar rutas accesibles.

## Mantenerlo siempre actualizado desde GitHub

En cada PC (lectores y admins), puedes actualizar con:

```
powershell -NoProfile -ExecutionPolicy Bypass -File .\Update-From-GitHub.ps1 -RepoUrl "https://github.com/<owner>/<repo>.git" -Branch "main"
```

- Preserva `.env`, `config/readers.json`, bases locales y carpetas de reportes/fotos.
- Si ya es repo (tiene `.git`), hace `git pull`; si no, clona y copia.
- Reinstala dependencias si cambió `requirements.txt` y recrea el acceso directo.

Programar actualización automática diaria (recomendado):

```
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-AutoUpdateTask.ps1 -RepoUrl "https://github.com/<owner>/<repo>.git" -Branch "main" -Hour 6 -Minute 30
```

- Crea una tarea de Windows que ejecuta el update cada día a la hora indicada.