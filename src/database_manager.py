import sqlite3
import os
import json
from datetime import datetime, date
from dotenv import load_dotenv
import threading
import importlib
import hashlib
import binascii
import secrets

# Detectar psycopg2 dinámicamente para evitar errores en entornos sin PostgreSQL
try:
    spec = importlib.util.find_spec('psycopg2')
    if spec is not None:
        psycopg2 = importlib.import_module('psycopg2')  # type: ignore
        POSTGRESQL_AVAILABLE = True
    else:
        POSTGRESQL_AVAILABLE = False
        print("PostgreSQL no disponible - funcionando solo con SQLite")
except Exception:
    POSTGRESQL_AVAILABLE = False
    print("PostgreSQL no disponible - funcionando solo con SQLite")

# Cargar variables de entorno
load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.pg_connection = None
        self.sqlite_connection = None
        self.lock = threading.Lock()
        self.setup_local_db()
        # Parámetros de keepalive para conexiones estables en redes poco confiables
        self._pg_keepalive = dict(
            keepalives=1,
            keepalives_idle=30,      # segundos de inactividad antes de enviar keepalive
            keepalives_interval=10,  # intervalo entre keepalives
            keepalives_count=3       # reintentos antes de considerar caída
        )
        
    def connect_postgresql(self):
        """Establece conexión a PostgreSQL si no existe y retorna True si queda conectada."""
        if not POSTGRESQL_AVAILABLE:
            return False
        try:
            if self.pg_connection and getattr(self.pg_connection, 'closed', 1) == 0:
                return True
            # Soporte opcional de SSL y keepalive
            conn_kwargs = dict(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'asistencia_nfc'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', ''),
                **self._pg_keepalive,
            )
            sslmode = os.getenv('DB_SSLMODE')
            if sslmode:
                conn_kwargs['sslmode'] = sslmode
            self.pg_connection = psycopg2.connect(**conn_kwargs)
            # autocommit para operaciones simples y menor latencia
            try:
                self.pg_connection.autocommit = False
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"Error conectando a PostgreSQL: {e}")
            self.pg_connection = None
            return False

    def _get_pg_conn(self):
        """Obtiene una conexión activa a PostgreSQL, intentando reconectar si es necesario. Retorna None si no hay."""
        if not POSTGRESQL_AVAILABLE:
            return None
        try:
            if self.pg_connection is None or getattr(self.pg_connection, 'closed', 1) != 0:
                if not self.connect_postgresql():
                    return None
            # Ping ligero
            try:
                cur = self.pg_connection.cursor()
                cur.execute('SELECT 1')
                cur.fetchone()
            except Exception:
                # Intentar reconectar una vez
                if not self.connect_postgresql():
                    return None
            return self.pg_connection
        except Exception:
            return None
    
    def setup_local_db(self):
        """Configurar base de datos local SQLite para cuando no hay internet"""
        local_db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'local.db')
        os.makedirs(os.path.dirname(local_db_path), exist_ok=True)
        
        self.sqlite_connection = sqlite3.connect(local_db_path, check_same_thread=False)
        
        # Crear tablas locales
        cursor = self.sqlite_connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS empleados_local (
                id INTEGER PRIMARY KEY,
                nombre_completo TEXT NOT NULL,
                cargo TEXT NOT NULL,
                rol TEXT NOT NULL,
                nfc_uid TEXT UNIQUE,
                foto_path TEXT,
                hora_entrada TEXT NOT NULL DEFAULT '09:00:00',
                hora_salida TEXT NOT NULL DEFAULT '18:00:00',
                activo INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros_local (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empleado_id INTEGER,
                ubicacion_nombre TEXT,
                fecha TEXT NOT NULL,
                hora_registro TEXT NOT NULL,
                tipo_movimiento TEXT NOT NULL,
                estado TEXT NOT NULL,
                sincronizado INTEGER DEFAULT 0,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuraciones_local (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        ''')

        # Tabla de justificaciones locales (retardos/faltas/tempranos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS justificaciones_local (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empleado_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL, -- 'RETARDO' | 'FALTA' | 'TEMPRANO'
                motivo TEXT,
                evidencia_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de usuarios locales para autenticación multi-PC
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios_local (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'ADMIN',
                activo INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.sqlite_connection.commit()
        # Ejecutar migraciones idempotentes
        try:
            from migrations import apply_pending_migrations
            applied = apply_pending_migrations(self.sqlite_connection)
            if applied:
                print(f"Migraciones aplicadas: {', '.join(applied)}")
        except Exception as e:
            print(f"Aviso migraciones: {e}")
        # Bootstrap de usuario admin si no existe
        try:
            c = self.sqlite_connection.cursor()
            c.execute("SELECT COUNT(*) FROM usuarios_local WHERE role = 'ADMIN' AND activo = 1")
            has_admin = (c.fetchone() or [0])[0] > 0
            if not has_admin:
                admin_user = os.getenv('ADMIN_USER', 'admin').strip() or 'admin'
                admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123').strip() or 'admin123'
                self._create_local_user(admin_user, admin_pass, role='ADMIN', force=True)
                print(f"🔐 Usuario administrador inicial creado: {admin_user}")
            # Sembrado de cuentas ADMIN solicitadas por el usuario (solo una vez)
            try:
                c.execute("SELECT valor FROM configuraciones_local WHERE clave = 'USUARIOS_SEEDED'")
                row = c.fetchone()
                if not row or str(row[0]) != '1':
                    seed_users = [
                        (os.getenv('ADMIN_USER_RONALD', 'RONALD'), os.getenv('ADMIN_PASS_RONALD', '2200')),
                        (os.getenv('ADMIN_USER_ADMIN', 'admin'), os.getenv('ADMIN_PASS_ADMIN', '1515060055')),
                        (os.getenv('ADMIN_USER_SANDRA', 'SANDRA'), os.getenv('ADMIN_PASS_SANDRA', '1515060055')),
                        (os.getenv('ADMIN_USER_RH', 'RH'), os.getenv('ADMIN_PASS_RH', '1515060055')),
                    ]
                    # Crear o actualizar contraseña si ya existen
                    for uname, upass in seed_users:
                        uname = (uname or '').strip()
                        upass = (upass or '').strip()
                        if not (uname and upass):
                            continue
                        try:
                            # Intentar crear; si ya existe, actualizar contraseña
                            created = self._create_local_user(uname, upass, role='ADMIN', force=False)
                            if not created:
                                # Si no se creó (por restricción UNIQUE), intentamos cambiar contraseña
                                self.cambiar_password(uname, upass)
                        except Exception:
                            # Como fallback, forzar reemplazo controlado
                            self._create_local_user(uname, upass, role='ADMIN', force=True)
                    # Marcar que ya se sembraron
                    c.execute("INSERT OR REPLACE INTO configuraciones_local (clave, valor) VALUES ('USUARIOS_SEEDED', '1')")
                    self.sqlite_connection.commit()
            except Exception as se:
                print(f"Aviso: no se pudieron sembrar todas las cuentas ADMIN: {se}")
        except Exception as e:
            print(f"Error creando admin por defecto: {e}")
    
    def is_online(self):
        """Verificar si hay conexión válida a PostgreSQL con ping ligero."""
        return self._get_pg_conn() is not None
    
    def sync_empleados_to_local(self):
        """Sincronizar empleados de PostgreSQL a SQLite"""
        conn = self._get_pg_conn()
        if not conn:
            return False
            
        try:
            with self.lock:
                # Obtener empleados de PostgreSQL
                pg_cursor = conn.cursor()
                pg_cursor.execute("""
                    SELECT id, nombre_completo, cargo, rol, nfc_uid, foto_path, 
                           hora_entrada, hora_salida, activo
                    FROM empleados WHERE activo = TRUE
                """)
                empleados = pg_cursor.fetchall()
                
                # Limpiar y cargar en SQLite
                sqlite_cursor = self.sqlite_connection.cursor()
                sqlite_cursor.execute("DELETE FROM empleados_local")
                
                for emp in empleados:
                    sqlite_cursor.execute("""
                        INSERT INTO empleados_local 
                        (id, nombre_completo, cargo, rol, nfc_uid, foto_path, hora_entrada, hora_salida, activo)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, emp)
                
                self.sqlite_connection.commit()
                return True
                
        except Exception as e:
            print(f"Error sincronizando empleados: {e}")
            return False
    
    def sync_registros_to_cloud(self):
        """Sincronizar registros locales a PostgreSQL"""
        conn = self._get_pg_conn()
        if not conn:
            return False
            
        try:
            with self.lock:
                sqlite_cursor = self.sqlite_connection.cursor()
                sqlite_cursor.execute("""
                    SELECT empleado_id, ubicacion_nombre, fecha, hora_registro, 
                           tipo_movimiento, estado
                    FROM registros_local WHERE sincronizado = 0
                """)
                registros_pendientes = sqlite_cursor.fetchall()
                
                if not registros_pendientes:
                    return True
                
                pg_cursor = conn.cursor()
                
                for registro in registros_pendientes:
                    empleado_id, ubicacion_nombre, fecha, hora_registro, tipo_movimiento, estado = registro
                    
                    # Obtener ID de ubicación
                    pg_cursor.execute("SELECT id FROM ubicaciones WHERE nombre = %s", (ubicacion_nombre,))
                    ubicacion_result = pg_cursor.fetchone()
                    if not ubicacion_result:
                        continue
                    
                    ubicacion_id = ubicacion_result[0]
                    
                    # Insertar en PostgreSQL
                    pg_cursor.execute("""
                        INSERT INTO registros_asistencia 
                        (empleado_id, ubicacion_id, fecha, hora_registro, tipo_movimiento, estado, sincronizado)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                    """, (empleado_id, ubicacion_id, fecha, hora_registro, tipo_movimiento, estado))
                
                conn.commit()
                
                # Marcar como sincronizados en SQLite
                sqlite_cursor.execute("UPDATE registros_local SET sincronizado = 1 WHERE sincronizado = 0")
                self.sqlite_connection.commit()
                
                return True
                
        except Exception as e:
            print(f"Error sincronizando a la nube: {e}")
            return False
    
    def insertar_registro(self, empleado_id, ubicacion_nombre, tipo_movimiento, estado):
        """Insertar registro de asistencia"""
        fecha_actual = date.today().isoformat()
        hora_actual = datetime.now().isoformat()
        
        try:
            with self.lock:
                conn = self._get_pg_conn()
                if conn:
                    # Insertar directamente en PostgreSQL
                    pg_cursor = conn.cursor()
                    pg_cursor.execute("SELECT id FROM ubicaciones WHERE nombre = %s", (ubicacion_nombre,))
                    ubicacion_result = pg_cursor.fetchone()
                    
                    if ubicacion_result:
                        ubicacion_id = ubicacion_result[0]
                        pg_cursor.execute("""
                            INSERT INTO registros_asistencia 
                            (empleado_id, ubicacion_id, fecha, hora_registro, tipo_movimiento, estado, sincronizado)
                            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                        """, (empleado_id, ubicacion_id, fecha_actual, hora_actual, tipo_movimiento, estado))
                        conn.commit()
                else:
                    # Guardar localmente
                    sqlite_cursor = self.sqlite_connection.cursor()
                    sqlite_cursor.execute("""
                        INSERT INTO registros_local 
                        (empleado_id, ubicacion_nombre, fecha, hora_registro, tipo_movimiento, estado)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (empleado_id, ubicacion_nombre, fecha_actual, hora_actual, tipo_movimiento, estado))
                    self.sqlite_connection.commit()
                
                return True
                
        except Exception as e:
            print(f"Error insertando registro: {e}")
            return False
    
    def obtener_empleado_por_nfc(self, nfc_uid):
        """Obtener empleado por UID de NFC"""
        try:
            # Normalizar UID: quitar no-hex y espacios, a mayúsculas
            try:
                uid_norm = ''.join(ch for ch in str(nfc_uid) if ch.upper() in '0123456789ABCDEF').upper()
            except Exception:
                uid_norm = str(nfc_uid).replace(' ', '').upper()
            with self.lock:
                if self.is_online():
                    pg_cursor = self.pg_connection.cursor()
                    # Comparar por UID normalizado (UPPER y sin espacios)
                    pg_cursor.execute(
                        """
                        SELECT id, nombre_completo, cargo, rol, foto_path, hora_entrada, hora_salida
                        FROM empleados 
                        WHERE activo = TRUE AND REPLACE(UPPER(nfc_uid), ' ', '') = %s
                        """,
                        (uid_norm,)
                    )
                    return pg_cursor.fetchone()
                else:
                    sqlite_cursor = self.sqlite_connection.cursor()
                    sqlite_cursor.execute(
                        """
                        SELECT id, nombre_completo, cargo, rol, foto_path, hora_entrada, hora_salida
                        FROM empleados_local 
                        WHERE activo = 1 AND REPLACE(UPPER(nfc_uid), ' ', '') = ?
                        """,
                        (uid_norm,)
                    )
                    return sqlite_cursor.fetchone()
                    
        except Exception as e:
            print(f"Error obteniendo empleado: {e}")
            return None

    def obtener_horarios_map(self) -> dict:
        """Retorna un mapa {empleado_id: (hora_entrada, hora_salida)}"""
        result = {}
        try:
            if self.is_online():
                c = self.pg_connection.cursor()
                c.execute("SELECT id, hora_entrada, hora_salida FROM empleados WHERE activo = TRUE")
                for row in c.fetchall():
                    result[row[0]] = (str(row[1])[:5], str(row[2])[:5])
            else:
                c = self.sqlite_connection.cursor()
                c.execute("SELECT id, hora_entrada, hora_salida FROM empleados_local WHERE activo = 1")
                for row in c.fetchall():
                    he = str(row[1])
                    hs = str(row[2])
                    result[row[0]] = (he[:5], hs[:5])
        except Exception as e:
            print(f"Error obteniendo horarios: {e}")
        return result

    def obtener_horario_efectivo(self, empleado_id: int, fecha: date | str) -> tuple[str, str]:
        """Calcula el horario efectivo (HH:MM, HH:MM) de un empleado para una fecha:
        - Aplica rotación semanal de doble horario si está habilitada
        - Aplica personalizados por día (L-V) con flag unificado si existen columnas, y si no, legacy de salidas
        - Aplica regla de sábado 08:00–14:00 para todos excepto jefes (00:00–00:00)
        En PostgreSQL (nube), si no existen columnas personalizadas, retorna horario base.
        """
        try:
            if isinstance(fecha, str):
                try:
                    f = datetime.fromisoformat(fecha).date()
                except Exception:
                    f = date.today()
            else:
                f = fecha

            # Obtener base y columnas auxiliares
            if self.is_online():
                c = self.pg_connection.cursor()
                c.execute("SELECT hora_entrada, hora_salida FROM empleados WHERE id = %s", (empleado_id,))
                row = c.fetchone()
                if not row:
                    return ("09:00", "18:00")
                he = str(row[0])[:5]
                hs = str(row[1])[:5]
                # Sin campos avanzados en nube por ahora
                he_t, hs_t = he, hs
            else:
                c = self.sqlite_connection.cursor()
                c.execute("PRAGMA table_info(empleados_local)")
                cols = {r[1] for r in c.fetchall()}
                c.execute("SELECT hora_entrada, hora_salida FROM empleados_local WHERE id = ?", (empleado_id,))
                row = c.fetchone()
                if not row:
                    return ("09:00", "18:00")
                he_t = str(row[0])[:5]
                hs_t = str(row[1])[:5]
                # Doble horario
                if {'hora_entrada_alt','hora_salida_alt','rotacion_semanal','rotacion_semana_base'}.issubset(cols):
                    c.execute("SELECT hora_entrada_alt, hora_salida_alt, rotacion_semanal, rotacion_semana_base FROM empleados_local WHERE id = ?", (empleado_id,))
                    alt = c.fetchone()
                    if alt and (alt[2] or 0):
                        _, iso_week, _ = f.isocalendar()
                        base = int(alt[3] or 0)
                        use_alt = ((iso_week + base) % 2 == 1)
                        if use_alt and alt[0] and alt[1]:
                            try:
                                he_t = str(alt[0])[:5]
                                hs_t = str(alt[1])[:5]
                            except Exception:
                                pass
                # Personalizados unificados entrada/salida (L-V)
                has_unified = 'personalizado_por_dia_enabled' in cols
                has_entries = all(n in cols for n in ['entrada_lunes','entrada_martes','entrada_miercoles','entrada_jueves','entrada_viernes'])
                has_exits = all(n in cols for n in ['salida_lunes','salida_martes','salida_miercoles','salida_jueves','salida_viernes'])
                if has_unified and (has_entries or has_exits):
                    parts = ['personalizado_por_dia_enabled']
                    if has_entries:
                        parts += ['entrada_lunes','entrada_martes','entrada_miercoles','entrada_jueves','entrada_viernes']
                    if has_exits:
                        parts += ['salida_lunes','salida_martes','salida_miercoles','salida_jueves','salida_viernes']
                    c.execute(f"SELECT {', '.join(parts)} FROM empleados_local WHERE id = ?", (empleado_id,))
                    prow = c.fetchone()
                    if prow and (prow[0] or 0):
                        wd = f.weekday()
                        idx = 1
                        entradas = [None]*5
                        salidas = [None]*5
                        if has_entries:
                            for i in range(5):
                                entradas[i] = prow[idx]; idx += 1
                        if has_exits:
                            for i in range(5):
                                salidas[i] = prow[idx]; idx += 1
                        if wd in (0,1,2,3,4):
                            if has_entries and entradas[wd]:
                                he_t = str(entradas[wd])[:5]
                            if has_exits and salidas[wd]:
                                hs_t = str(salidas[wd])[:5]
                else:
                    # Legacy: solo salidas por día
                    if {'salida_por_dia_enabled','salida_lunes','salida_martes','salida_miercoles','salida_jueves','salida_viernes'}.issubset(cols):
                        c.execute("SELECT salida_por_dia_enabled, salida_lunes, salida_martes, salida_miercoles, salida_jueves, salida_viernes FROM empleados_local WHERE id = ?", (empleado_id,))
                        drow = c.fetchone()
                        if drow and (drow[0] or 0):
                            wd = f.weekday()
                            if wd in (0,1,2,3,4):
                                s_map = {0:drow[1],1:drow[2],2:drow[3],3:drow[4],4:drow[5]}
                                val = s_map.get(wd)
                                if val:
                                    hs_t = str(val)[:5]

            # Sábado especial 08:00–14:00 (excepto jefes)
            try:
                es_jefe = (he_t == '00:00' and hs_t == '00:00')
            except Exception:
                es_jefe = False
            if f.weekday() == 5 and not es_jefe:
                he_t, hs_t = '08:00', '14:00'

            return (he_t, hs_t)
        except Exception as e:
            print(f"Error calculando horario efectivo: {e}")
            return ("09:00", "18:00")

    def obtener_empleados_activos(self):
        """Retorna lista de empleados activos [(id, nombre_completo)]"""
        try:
            if self.is_online():
                c = self.pg_connection.cursor()
                c.execute("SELECT id, nombre_completo FROM empleados WHERE activo = TRUE")
                return c.fetchall()
            else:
                c = self.sqlite_connection.cursor()
                c.execute("SELECT id, nombre_completo FROM empleados_local WHERE activo = 1")
                return c.fetchall()
        except Exception as e:
            print(f"Error obteniendo empleados activos: {e}")
            return []

    def agregar_justificacion(self, empleado_id: int, fecha_iso: str, tipo: str, motivo: str = "", evidencia_path: str | None = None) -> bool:
        """Agregar una justificación local para RETARDO/FALTA/TEMPRANO."""
        try:
            c = self.sqlite_connection.cursor()
            c.execute(
                """
                INSERT INTO justificaciones_local (empleado_id, fecha, tipo, motivo, evidencia_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (empleado_id, fecha_iso, tipo.upper(), motivo or "", evidencia_path or None),
            )
            self.sqlite_connection.commit()
            return True
        except Exception as e:
            print(f"Error guardando justificación: {e}")
            return False

    def obtener_justificaciones_por_fecha(self, fecha_iso: str) -> dict:
        """Retorna un mapa { (empleado_id, tipo): motivo } para la fecha dada."""
        out = {}
        try:
            c = self.sqlite_connection.cursor()
            c.execute(
                "SELECT empleado_id, tipo, motivo FROM justificaciones_local WHERE fecha = ?",
                (fecha_iso,),
            )
            for emp_id, tipo, motivo in c.fetchall():
                out[(int(emp_id), str(tipo).upper())] = motivo or ""
        except Exception as e:
            print(f"Error leyendo justificaciones: {e}")
        return out
    
    def obtener_registros_dia(self, fecha=None):
        """Obtener registros del día"""
        if fecha is None:
            fecha = date.today().isoformat()
            
        try:
            with self.lock:
                conn = self._get_pg_conn()
                if conn:
                    pg_cursor = conn.cursor()
                    pg_cursor.execute("""
                        SELECT e.id, e.nombre_completo, e.foto_path, r.hora_registro, 
                               r.tipo_movimiento, r.estado, u.nombre
                        FROM registros_asistencia r
                        JOIN empleados e ON r.empleado_id = e.id
                        JOIN ubicaciones u ON r.ubicacion_id = u.id
                        WHERE r.fecha = %s
                        ORDER BY r.hora_registro DESC
                    """, (fecha,))
                    return pg_cursor.fetchall()
                else:
                    sqlite_cursor = self.sqlite_connection.cursor()
                    sqlite_cursor.execute("""
                        SELECT e.id, e.nombre_completo, e.foto_path, r.hora_registro,
                               r.tipo_movimiento, r.estado, r.ubicacion_nombre
                        FROM registros_local r
                        JOIN empleados_local e ON r.empleado_id = e.id
                        WHERE r.fecha = ?
                        ORDER BY r.hora_registro DESC
                    """, (fecha,))
                    return sqlite_cursor.fetchall()
                    
        except Exception as e:
            print(f"Error obteniendo registros del día: {e}")
            return []

    def borrar_registros_empleado_dia(self, empleado_id: int, fecha_iso: str) -> int:
        """Borrar registros de un empleado en una fecha específica. Retorna cantidad borrada."""
        try:
            with self.lock:
                conn = self._get_pg_conn()
                if conn:
                    cur = conn.cursor()
                    cur.execute(
                        "DELETE FROM registros_asistencia WHERE empleado_id = %s AND fecha = %s RETURNING 1",
                        (empleado_id, fecha_iso),
                    )
                    borrados = cur.rowcount
                    conn.commit()
                    return borrados
                else:
                    cur = self.sqlite_connection.cursor()
                    cur.execute(
                        "DELETE FROM registros_local WHERE empleado_id = ? AND fecha = ?",
                        (empleado_id, fecha_iso),
                    )
                    borrados = cur.rowcount
                    self.sqlite_connection.commit()
                    return borrados
        except Exception as e:
            print(f"Error borrando registros diarios: {e}")
            return 0

    def borrar_registros_empleado_mes(self, empleado_id: int, year: int, month: int) -> int:
        """Borrar registros de un empleado por mes (YYYY, MM). Retorna cantidad borrada."""
        try:
            with self.lock:
                conn = self._get_pg_conn()
                if conn:
                    cur = conn.cursor()
                    cur.execute(
                        "DELETE FROM registros_asistencia WHERE empleado_id = %s AND EXTRACT(YEAR FROM fecha) = %s AND EXTRACT(MONTH FROM fecha) = %s RETURNING 1",
                        (empleado_id, year, month),
                    )
                    borrados = cur.rowcount
                    conn.commit()
                    return borrados
                else:
                    cur = self.sqlite_connection.cursor()
                    cur.execute(
                        "DELETE FROM registros_local WHERE empleado_id = ? AND substr(fecha,1,4) = ? AND substr(fecha,6,2) = ?",
                        (empleado_id, str(year), f"{month:02d}"),
                    )
                    borrados = cur.rowcount
                    self.sqlite_connection.commit()
                    return borrados
        except Exception as e:
            print(f"Error borrando registros mensuales: {e}")
            return 0

    def borrar_registros_empleado_todos(self, empleado_id: int) -> int:
        """Borrar TODOS los registros de un empleado. Retorna cantidad borrada."""
        try:
            with self.lock:
                conn = self._get_pg_conn()
                if conn:
                    cur = conn.cursor()
                    cur.execute(
                        "DELETE FROM registros_asistencia WHERE empleado_id = %s RETURNING 1",
                        (empleado_id,),
                    )
                    borrados = cur.rowcount
                    conn.commit()
                    return borrados
                else:
                    cur = self.sqlite_connection.cursor()
                    cur.execute(
                        "DELETE FROM registros_local WHERE empleado_id = ?",
                        (empleado_id,),
                    )
                    borrados = cur.rowcount
                    self.sqlite_connection.commit()
                    return borrados
        except Exception as e:
            print(f"Error borrando todos los registros del empleado: {e}")
            return 0
    
    def close_connections(self):
        """Cerrar conexiones"""
        if self.pg_connection:
            self.pg_connection.close()
        if self.sqlite_connection:
            self.sqlite_connection.close()

    # ==========================
    # Gestión de Usuarios (Local)
    # ==========================
    def _hash_password(self, password: str, salt: bytes | None = None, iterations: int = 200_000) -> str:
        """Genera un hash PBKDF2-SHA256 con salt. Devuelve formato: pbkdf2_sha256$iter$salthex$hashhex"""
        salt = salt or secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return f"pbkdf2_sha256${iterations}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"

    def _verify_password(self, password: str, stored: str) -> bool:
        try:
            algo, iter_s, salt_hex, hash_hex = stored.split('$', 3)
            if algo != 'pbkdf2_sha256':
                return False
            iterations = int(iter_s)
            salt = binascii.unhexlify(salt_hex)
            calc = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
            return binascii.hexlify(calc).decode() == hash_hex
        except Exception:
            return False

    def _create_local_user(self, username: str, password: str, role: str = 'ADMIN', force: bool = False) -> bool:
        try:
            username = username.strip()
            if not username or not password:
                return False
            ph = self._hash_password(password)
            c = self.sqlite_connection.cursor()
            if force:
                c.execute(
                    "INSERT OR REPLACE INTO usuarios_local (id, username, password_hash, role, activo) "
                    "VALUES ((SELECT id FROM usuarios_local WHERE username = ?), ?, ?, ?, 1)",
                    (username, username, ph, role)
                )
            else:
                c.execute(
                    "INSERT INTO usuarios_local (username, password_hash, role, activo) VALUES (?, ?, ?, 1)",
                    (username, ph, role)
                )
            self.sqlite_connection.commit()
            return True
        except Exception as e:
            print(f"Error creando usuario: {e}")
            return False

    def crear_usuario(self, username: str, password: str, role: str = 'ADMIN') -> bool:
        return self._create_local_user(username, password, role=role, force=False)

    def verificar_usuario(self, username: str, password: str, required_role: str | None = None) -> bool:
        try:
            c = self.sqlite_connection.cursor()
            c.execute("SELECT password_hash, role, activo FROM usuarios_local WHERE username = ?", (username.strip(),))
            row = c.fetchone()
            if not row:
                return False
            stored, role, activo = row
            if not activo:
                return False
            if required_role and str(role).upper() != required_role.upper():
                return False
            return self._verify_password(password, stored)
        except Exception as e:
            print(f"Error verificando usuario: {e}")
            return False

    def cambiar_password(self, username: str, new_password: str) -> bool:
        try:
            ph = self._hash_password(new_password)
            c = self.sqlite_connection.cursor()
            c.execute("UPDATE usuarios_local SET password_hash = ? WHERE username = ?", (ph, username.strip()))
            self.sqlite_connection.commit()
            return c.rowcount > 0
        except Exception as e:
            print(f"Error cambiando contraseña: {e}")
            return False

    def listar_usuarios(self) -> list[tuple]:
        try:
            c = self.sqlite_connection.cursor()
            c.execute("SELECT id, username, role, activo, created_at FROM usuarios_local ORDER BY username")
            return c.fetchall()
        except Exception as e:
            print(f"Error listando usuarios: {e}")
            return []

    def activar_usuario(self, username: str, activo: bool) -> bool:
        try:
            c = self.sqlite_connection.cursor()
            c.execute("UPDATE usuarios_local SET activo = ? WHERE username = ?", (1 if activo else 0, username.strip()))
            self.sqlite_connection.commit()
            return c.rowcount > 0
        except Exception as e:
            print(f"Error actualizando estado de usuario: {e}")
            return False

# Instancia global del gestor de base de datos
db_manager = DatabaseManager()