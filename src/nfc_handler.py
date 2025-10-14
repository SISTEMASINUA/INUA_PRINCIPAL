import threading
import time
from datetime import datetime, time as dt_time, timedelta
from database_manager import db_manager
from acr122u_driver import acr122u_reader
from acr122u_reader import ACR122UReader
import os
import json
from pathlib import Path

class NFCReader:
    def __init__(self, main_screen=None):
        self.main_screen = main_screen
        self.is_reading = False
        self.tolerance_minutes = 10  # 10 minutos de tolerancia
        self.ubicacion_actual = os.getenv('UBICACION_PRINCIPAL', 'Tepanecos')
        # Sitio que controla la visual (foto grande). Los otros sitios sólo registran y aparecen en la lista.
        self.visual_site = os.getenv('UBICACION_PRINCIPAL', 'Tepanecos')
        self._last_readers = []
        
        # Configurar el lector ACR122U con callback
        acr122u_reader.callback_function = self.process_nfc_card
        
    def start_reading(self):
        """Iniciar lectura continua de NFC"""
        if not self.is_reading:
            self.is_reading = True
            print("🚀 Iniciando lector NFC ACR122U...")
            
            # Probar lector primero
            available_readers = acr122u_reader.get_available_readers()
            if not available_readers:
                print("❌ No se encontró ningún lector PC/SC")
                print("   Verifica conexión USB y que el servicio 'Tarjeta inteligente' esté activo.")
                print("   Esperando conexión (hot-plug)…")
                # Iniciar watcher para detectar conexión futura
                threading.Thread(target=self._hotplug_watcher, daemon=True).start()
                # Dialogo para ayudar a configurar
                try:
                    if self.main_screen:
                        import tkinter as tk
                        from tkinter import messagebox
                        if messagebox.askyesno("Sin lector detectado",
                                                "No se detectó ningún lector.\n\n¿Deseas abrir la configuración de lectores para asignar por sitio?",
                                                parent=self.main_screen.root):
                            from admin_interface import AdminInterface
                            AdminInterface(self.main_screen.root)
                except Exception:
                    pass
                return
            
            print("🔍 Lectores disponibles:")
            for i, r in enumerate(available_readers, 1):
                print(f"  {i}. {r}")
            self._last_readers = list(available_readers)
            
            # Intentar fijar lector por configuración persistente por sitio
            self._apply_site_reader_preferences()
            print(f"✅ Usando lector preferido para sitio '{self.ubicacion_actual}' (si está disponible)")
            # Reconfigurar con el entorno actual y arrancar
            try:
                if hasattr(acr122u_reader, 'reconfigure_with_env'):
                    acr122u_reader.reconfigure_with_env()
            except Exception:
                pass
            acr122u_reader.start_reading()
            # Iniciar watcher de hot-plug
            threading.Thread(target=self._hotplug_watcher, daemon=True).start()
    
    def stop_reading(self):
        """Detener lectura de NFC"""
        self.is_reading = False
        acr122u_reader.stop_reading()
        print("⏹️ Lector NFC detenido")
    
    # Eliminado modo simulación

    def _hotplug_watcher(self):
        """Vigilar cambios en la lista de lectores y reconfigurar si es necesario."""
        while self.is_reading:
            try:
                if hasattr(acr122u_reader, 'refresh_readers'):
                    readers = acr122u_reader.refresh_readers()
                    if readers != self._last_readers:
                        print("🔁 Lectores actualizados:")
                        for i, r in enumerate(readers or [], 1):
                            print(f"  {i}. {r}")
                        self._last_readers = list(readers or [])
                        # Re-aplicar preferencia por sitio tras cambios
                        self._apply_site_reader_preferences()
                        # Reconfigurar con entorno actual (nombre/índice) si está disponible
                        try:
                            if hasattr(acr122u_reader, 'reconfigure_with_env'):
                                acr122u_reader.reconfigure_with_env()
                        except Exception:
                            pass
                        # Si ahora hay lectores disponibles, iniciar lectura
                        if readers:
                            try:
                                acr122u_reader.start_reading()
                            except Exception:
                                pass
                # Escaneo más rápido para reconectar en segundos
                time.sleep(1.5)
            except Exception:
                time.sleep(2)

    def _apply_site_reader_preferences(self):
        """Leer config/readers.json y fijar variables de entorno para el lector según el sitio actual."""
        try:
            config_path = Path(__file__).resolve().parent.parent / 'config' / 'readers.json'
            if not config_path.exists():
                # No hay config; mantener env existentes o defaults
                return
            data = json.loads(config_path.read_text(encoding='utf-8'))
            site = self.ubicacion_actual
            site_cfg = (data.get('sites') or {}).get(site)
            if not site_cfg:
                return
            reader_name = site_cfg.get('readerName')
            reader_index = site_cfg.get('readerIndex')
            if reader_name:
                os.environ['NFC_READER_NAME'] = str(reader_name)
                if 'NFC_READER_INDEX' in os.environ:
                    del os.environ['NFC_READER_INDEX']
            elif reader_index:
                os.environ['NFC_READER_INDEX'] = str(reader_index)
                if 'NFC_READER_NAME' in os.environ:
                    del os.environ['NFC_READER_NAME']
        except Exception as e:
            print(f"⚠️  No se pudo aplicar preferencia de lector por sitio: {e}")
    
    def process_nfc_card(self, nfc_uid):
        """Procesar tarjeta NFC leída"""
        try:
            print(f"📱 Tarjeta NFC detectada: {nfc_uid}")
            
            # Buscar empleado por UID
            empleado = db_manager.obtener_empleado_por_nfc(nfc_uid)
            
            if not empleado:
                print("❌ Tarjeta no registrada")
                print(f"   UID: {nfc_uid}")
                print("   Registra esta tarjeta en la administración")
                return False
            
            empleado_id = empleado[0]
            nombre = empleado[1]
            hora_entrada = empleado[5]
            hora_salida = empleado[6]
            
            print(f"✅ Empleado identificado: {nombre}")
            
            # Determinar tipo de movimiento y estado
            tipo_movimiento, estado = self._determine_movement_and_status(
                empleado_id, hora_entrada, hora_salida
            )
            
            print(f"📋 Registro: {tipo_movimiento} - {estado}")
            
            # Registrar asistencia
            success = db_manager.insertar_registro(
                empleado_id, self.ubicacion_actual, tipo_movimiento, estado
            )
            
            if success:
                print(f"💾 Registro guardado exitosamente")
                
                # Mostrar en pantalla principal sólo si la lectura corresponde al sitio visual
                if self.main_screen and str(self.ubicacion_actual).upper() == str(self.visual_site).upper():
                    self.main_screen.show_employee_registration(empleado, tipo_movimiento, estado)
                
                return True
            else:
                print("❌ Error al registrar asistencia")
                return False
                
        except Exception as e:
            print(f"❌ Error procesando tarjeta NFC: {e}")
            return False
    
    def _determine_movement_and_status(self, empleado_id, hora_entrada_str, hora_salida_str):
        """Determinar tipo de movimiento y estado según horarios"""
        try:
            now = datetime.now()
            current_time = now.time()
            current_date = now.date()
            
            # Convertir strings de hora a objetos time
            if isinstance(hora_entrada_str, str):
                hora_entrada = dt_time.fromisoformat(hora_entrada_str)
            else:
                hora_entrada = hora_entrada_str
                
            if isinstance(hora_salida_str, str):
                hora_salida = dt_time.fromisoformat(hora_salida_str)
            else:
                hora_salida = hora_salida_str
            
            # Cargar posible doble horario con rotación semanal
            try:
                c = db_manager.sqlite_connection.cursor()
                c.execute("PRAGMA table_info(empleados_local)")
                cols = {r[1] for r in c.fetchall()}
                # Primero cargar posibles overrides de doble horario
                c.execute("SELECT hora_entrada_alt, hora_salida_alt, rotacion_semanal, rotacion_semana_base FROM empleados_local WHERE id = ?", (empleado_id,))
                row = c.fetchone()
                if row and (row[2] or 0):
                    # Determinar semana par/impar respecto a base
                    # Usamos número de semana ISO
                    iso_year, iso_week, _ = now.isocalendar()
                    base = int(row[3] or 0)
                    use_alt = ((iso_week + base) % 2 == 1)
                    if use_alt and row[0] and row[1]:
                        # Sobrescribir horario con alternos
                        try:
                            hora_entrada = dt_time.fromisoformat(str(row[0])[:5])
                            hora_salida = dt_time.fromisoformat(str(row[1])[:5])
                        except Exception:
                            pass
                # Luego, aplicar personalizados por día (L-V)
                has_unified = 'personalizado_por_dia_enabled' in cols
                has_entries = all(n in cols for n in ['entrada_lunes','entrada_martes','entrada_miercoles','entrada_jueves','entrada_viernes'])
                has_exits = all(n in cols for n in ['salida_lunes','salida_martes','salida_miercoles','salida_jueves','salida_viernes'])
                if has_unified and (has_entries or has_exits):
                    # Usar flag unificado
                    entry_part = ', '.join(['entrada_lunes','entrada_martes','entrada_miercoles','entrada_jueves','entrada_viernes']) if has_entries else ''
                    exit_part = ', '.join(['salida_lunes','salida_martes','salida_miercoles','salida_jueves','salida_viernes']) if has_exits else ''
                    cols_select = 'personalizado_por_dia_enabled'
                    if entry_part:
                        cols_select += ', ' + entry_part
                    if exit_part:
                        cols_select += ', ' + exit_part
                    c.execute(f"SELECT {cols_select} FROM empleados_local WHERE id = ?", (empleado_id,))
                    prow = c.fetchone()
                    if prow and (prow[0] or 0):
                        wd = now.weekday()
                        if wd in (0,1,2,3,4):
                            idx = 1
                            entradas = [None]*5
                            salidas = [None]*5
                            if has_entries:
                                for i in range(5):
                                    entradas[i] = prow[idx]; idx += 1
                            if has_exits:
                                for i in range(5):
                                    salidas[i] = prow[idx]; idx += 1
                            if has_entries and entradas[wd]:
                                try:
                                    hora_entrada = dt_time.fromisoformat(str(entradas[wd])[:5])
                                except Exception:
                                    pass
                            if has_exits and salidas[wd]:
                                try:
                                    hora_salida = dt_time.fromisoformat(str(salidas[wd])[:5])
                                except Exception:
                                    pass
                else:
                    # Compatibilidad legacy: sólo salidas por día
                    if {'salida_por_dia_enabled','salida_lunes','salida_martes','salida_miercoles','salida_jueves','salida_viernes'}.issubset(cols):
                        c.execute("""
                            SELECT salida_por_dia_enabled, salida_lunes, salida_martes, salida_miercoles, salida_jueves, salida_viernes
                            FROM empleados_local WHERE id = ?
                        """, (empleado_id,))
                        drow = c.fetchone()
                        if drow and (drow[0] or 0):
                            wd = now.weekday()  # 0=Lunes ... 6=Domingo
                            if wd in (0,1,2,3,4):
                                s_map = {0:drow[1],1:drow[2],2:drow[3],3:drow[4],4:drow[5]}
                                val = s_map.get(wd)
                                if val:
                                    try:
                                        hora_salida = dt_time.fromisoformat(str(val)[:5])
                                    except Exception:
                                        pass
            except Exception:
                pass

            # Regla especial: Sábado 08:00-14:00 para todos
            # weekday(): Monday=0 .. Sunday=6; Saturday=5
            if now.weekday() == 5:
                try:
                    # Detectar "Jefe" por horario 00:00-00:00
                    if isinstance(hora_entrada_str, str):
                        he_s = str(hora_entrada_str)[:5]
                    else:
                        he_s = f"{hora_entrada.hour:02d}:{hora_entrada.minute:02d}"
                    if isinstance(hora_salida_str, str):
                        hs_s = str(hora_salida_str)[:5]
                    else:
                        hs_s = f"{hora_salida.hour:02d}:{hora_salida.minute:02d}"
                    es_jefe = (he_s == '00:00' and hs_s == '00:00')
                except Exception:
                    es_jefe = False
                if not es_jefe:
                    hora_entrada = dt_time(8, 0)
                    hora_salida = dt_time(14, 0)

            # Modo "sin horario" para jefes: si hora_entrada y hora_salida vienen nulas o '00:00'
            no_schedule = False
            try:
                if (hora_entrada == dt_time(0, 0) and hora_salida == dt_time(0, 0)):
                    no_schedule = True
            except Exception:
                pass

            # Verificar último registro del día
            ultimo_registro = self._get_last_record_today(empleado_id, current_date)
            
            if not ultimo_registro:
                # Primer registro del día - debe ser entrada (aquí sí se evalúa RETARDO/A_TIEMPO)
                tipo_movimiento = "ENTRADA"
                if no_schedule:
                    estado = "A_TIEMPO"  # Sin horario, nunca retardo
                else:
                    estado = self._calculate_entry_status(current_time, hora_entrada)
                print(f"   Primer registro del día: {estado}")
            else:
                ultimo_tipo = ultimo_registro[4]  # tipo_movimiento del último registro
                
                if ultimo_tipo == "ENTRADA":
                    # El último fue entrada, ahora debe ser salida
                    tipo_movimiento = "SALIDA"
                    if no_schedule:
                        estado = "A_TIEMPO"  # Sin horario, salida siempre a tiempo
                    else:
                        estado = self._calculate_exit_status(current_time, hora_salida)
                    print(f"   Registrando salida: {estado}")
                else:
                    # El último fue salida, ahora debe ser entrada
                    # Por requerimiento: NO recalcular retardo en entradas posteriores; marcarlas como A_TIEMPO
                    tipo_movimiento = "ENTRADA"
                    estado = "A_TIEMPO"
                    print(f"   Nueva entrada (neutral): {estado}")
            
            return tipo_movimiento, estado
            
        except Exception as e:
            print(f"Error determinando movimiento: {e}")
            return "ENTRADA", "A_TIEMPO"
    
    def _get_last_record_today(self, empleado_id, fecha):
        """Obtener último registro del empleado en el día"""
        try:
            if db_manager.is_online():
                cursor = db_manager.pg_connection.cursor()
                cursor.execute("""
                    SELECT * FROM registros_asistencia 
                    WHERE empleado_id = %s AND fecha = %s 
                    ORDER BY hora_registro DESC LIMIT 1
                """, (empleado_id, fecha))
                return cursor.fetchone()
            else:
                cursor = db_manager.sqlite_connection.cursor()
                cursor.execute("""
                    SELECT * FROM registros_local 
                    WHERE empleado_id = ? AND fecha = ? 
                    ORDER BY hora_registro DESC LIMIT 1
                """, (empleado_id, fecha.isoformat()))
                return cursor.fetchone()
                
        except Exception as e:
            print(f"Error obteniendo último registro: {e}")
            return None
    
    def _calculate_entry_status(self, current_time, hora_entrada):
        """Calcular estado de entrada"""
        try:
            # Convertir a datetime para facilitar cálculos
            hora_entrada_dt = datetime.combine(datetime.today().date(), hora_entrada)
            hora_limite_dt = hora_entrada_dt + timedelta(minutes=self.tolerance_minutes)
            current_dt = datetime.combine(datetime.today().date(), current_time)
            
            if current_dt <= hora_limite_dt:
                return "A_TIEMPO"  # Llegó a tiempo (incluyendo tolerancia)
            else:
                return "RETARDO"   # Llegó tarde
                
        except Exception as e:
            print(f"Error calculando estado de entrada: {e}")
            return "A_TIEMPO"
    
    def _calculate_exit_status(self, current_time, hora_salida):
        """Calcular estado de salida"""
        try:
            # Convertir a datetime para facilitar cálculos
            hora_salida_dt = datetime.combine(datetime.today().date(), hora_salida)
            current_dt = datetime.combine(datetime.today().date(), current_time)
            
            if current_dt < hora_salida_dt:
                return "TEMPRANO"  # Salió antes de su hora
            else:
                return "A_TIEMPO"   # Salió a tiempo o después
                
        except Exception as e:
            print(f"Error calculando estado de salida: {e}")
            return "A_TIEMPO"
    
    def manual_nfc_input(self, nfc_uid):
        """Procesar UID de NFC ingresado manualmente (para pruebas)"""
        return self.process_nfc_card(nfc_uid)
    
    def read_single_card_manual(self):
        """Leer una tarjeta manualmente (para administración)"""
        try:
            print("🏷️ Acerca una tarjeta al lector ACR122U...")
            uid, mensaje = acr122u_reader.read_single_card(timeout=15)
            
            if uid:
                print(f"✅ Tarjeta leída: {uid}")
                return uid
            else:
                print(f"❌ {mensaje}")
                return None
                
        except Exception as e:
            print(f"❌ Error leyendo tarjeta: {e}")
            return None

class AttendanceValidator:
    """Clase para validaciones adicionales de asistencia"""
    
    @staticmethod
    def check_daily_attendance():
        """Verificar asistencias diarias y marcar faltas"""
        try:
            current_date = datetime.now().date()
            
            # Obtener todos los empleados activos
            if db_manager.is_online():
                cursor = db_manager.pg_connection.cursor()
                cursor.execute("SELECT id, nombre_completo FROM empleados WHERE activo = TRUE")
                empleados = cursor.fetchall()
                
                for empleado_id, nombre in empleados:
                    # Verificar si tiene registro de entrada hoy
                    cursor.execute("""
                        SELECT COUNT(*) FROM registros_asistencia 
                        WHERE empleado_id = %s AND fecha = %s AND tipo_movimiento = 'ENTRADA'
                    """, (empleado_id, current_date))
                    
                    tiene_entrada = cursor.fetchone()[0] > 0
                    
                    if not tiene_entrada:
                        # Verificar si ya hay un registro de falta
                        cursor.execute("""
                            SELECT COUNT(*) FROM registros_asistencia 
                            WHERE empleado_id = %s AND fecha = %s AND estado = 'FALTA'
                        """, (empleado_id, current_date))
                        
                        tiene_falta = cursor.fetchone()[0] > 0
                        
                        if not tiene_falta:
                            # Registrar falta si ya pasó la hora límite
                            now = datetime.now()
                            if now.hour >= 12:  # Después del mediodía, considerar falta
                                cursor.execute("""
                                    INSERT INTO registros_asistencia 
                                    (empleado_id, ubicacion_id, fecha, hora_registro, tipo_movimiento, estado)
                                    VALUES (%s, 1, %s, %s, 'ENTRADA', 'FALTA')
                                """, (empleado_id, current_date, now))
                
                db_manager.pg_connection.commit()
                print(f"✅ Verificación de asistencias completada")
                
        except Exception as e:
            print(f"Error verificando asistencias diarias: {e}")
    
    @staticmethod
    def get_employee_monthly_summary(empleado_id, year, month):
        """Obtener resumen mensual de un empleado"""
        try:
            if db_manager.is_online():
                cursor = db_manager.pg_connection.cursor()
                cursor.execute("""
                    SELECT 
                        fecha,
                        MIN(CASE WHEN tipo_movimiento = 'ENTRADA' THEN hora_registro END) as primera_entrada,
                        MAX(CASE WHEN tipo_movimiento = 'SALIDA' THEN hora_registro END) as ultima_salida,
                        MIN(CASE WHEN tipo_movimiento = 'ENTRADA' THEN estado END) as estado_entrada,
                        MAX(CASE WHEN tipo_movimiento = 'SALIDA' THEN estado END) as estado_salida
                    FROM registros_asistencia 
                    WHERE empleado_id = %s 
                    AND EXTRACT(YEAR FROM fecha) = %s 
                    AND EXTRACT(MONTH FROM fecha) = %s
                    GROUP BY fecha
                    ORDER BY fecha
                """, (empleado_id, year, month))
                
                return cursor.fetchall()
                
        except Exception as e:
            print(f"Error obteniendo resumen mensual: {e}")
            return []

# Instancia global del lector NFC
def _try_load_sites_config():
    try:
        config_path = Path(__file__).resolve().parent.parent / 'config' / 'readers.json'
        if config_path.exists():
            return json.loads(config_path.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {"sites": {}}


class NFCReaderMulti(NFCReader):
    """Lector que permite operar dos lectores en paralelo, uno por sitio."""
    def __init__(self, main_screen=None):
        super().__init__(main_screen)
        self._threads: dict[str, threading.Thread] = {}
        self._instances: dict[str, ACR122UReader] = {}
        self._instance_running: dict[str, bool] = {}
        self._sites = []
        self._site_cfg = {}
        self.dual_enabled = False
        self._active_reader_names: dict[str, str] = {}

    def start_reading(self):
        cfg = _try_load_sites_config()
        sites = list((cfg.get('sites') or {}).keys())
        self._site_cfg = cfg.get('sites') or {}

        # Activar dual si hay al menos 2 sitios configurados
        self.dual_enabled = len(sites) >= 2

        # Auto-multi sin configuración: si no hay 2 sitios pero sí hay >=2 lectores físicos,
        # construimos un mapeo efímero por nombre para 2 sitios por defecto.
        if not self.dual_enabled:
            try:
                readers = acr122u_reader.get_available_readers() if hasattr(acr122u_reader, 'get_available_readers') else []
            except Exception:
                readers = []
            if readers and len(readers) >= 2:
                # Seleccionar dos primeros lectores y asignarlos a sitios por defecto
                r1, r2 = readers[0], readers[1]
                default_sites = ['Tepanecos', 'Lerdo']
                self._site_cfg = {
                    default_sites[0]: {'readerName': r1},
                    default_sites[1]: {'readerName': r2},
                }
                sites = default_sites
                self.dual_enabled = True
                print("⚙️  Auto-multi activado: mapeo efímero por defecto Tepanecos/Lerdo → lectores físicos detectados")

        if not self.dual_enabled:
            return super().start_reading()

        if self.is_reading:
            return
        self.is_reading = True
        self._sites = sites  # Soportamos N sitios en paralelo

        print(f"🧵 Iniciando lectura en sitios: {self._sites}")

        for site in self._sites:
            scfg = self._site_cfg.get(site) or {}
            fname = scfg.get('readerName')
            findex = scfg.get('readerIndex')
            try:
                inst = ACR122UReader(callback=lambda uid, _s=site: self._process_with_site(uid, _s),
                                     force_name=fname, force_index=findex)
                ok = inst.start_reading()
                self._instances[site] = inst
                self._instance_running[site] = bool(ok)
                try:
                    self._active_reader_names[site] = str(getattr(inst, 'reader', None) or '') if ok else ''
                except Exception:
                    self._active_reader_names[site] = ''
                print(f"  • {site}: {'OK' if ok else 'NO DISPONIBLE'}")
            except Exception as e:
                print(f"⚠️  Error iniciando lector para {site}: {e}")
                self._instance_running[site] = False

        # Hot-plug watcher para dual
        threading.Thread(target=self._hotplug_dual_watcher, daemon=True).start()

    def stop_reading(self):
        if not self.dual_enabled:
            return super().stop_reading()
        self.is_reading = False
        for site, inst in list(self._instances.items()):
            try:
                inst.stop_reading()
            except Exception:
                pass
        self._instances.clear()
        self._instance_running.clear()
        self._active_reader_names.clear()
        print("⏹️ Lectura detenida para todos los sitios")

    def _process_with_site(self, uid: str, site_override: str):
        prev = self.ubicacion_actual
        try:
            self.ubicacion_actual = site_override
            return self.process_nfc_card(uid)
        finally:
            self.ubicacion_actual = prev

    def _hotplug_dual_watcher(self):
        while self.is_reading and self.dual_enabled:
            try:
                # Reintentar iniciar los que estén caídos
                for site in list(self._sites):
                    inst = self._instances.get(site)
                    running = self._instance_running.get(site, False)
                    if inst and running:
                        continue
                    scfg = self._site_cfg.get(site) or {}
                    fname = scfg.get('readerName')
                    findex = scfg.get('readerIndex')
                    try:
                        inst = ACR122UReader(callback=lambda uid, _s=site: self._process_with_site(uid, _s),
                                             force_name=fname, force_index=findex)
                        ok = inst.start_reading()
                        self._instances[site] = inst
                        self._instance_running[site] = bool(ok)
                        try:
                            self._active_reader_names[site] = str(getattr(inst, 'reader', None) or '') if ok else ''
                        except Exception:
                            self._active_reader_names[site] = ''
                        if ok:
                            print(f"🔁 {site}: lector reconectado")
                    except Exception:
                        pass
                time.sleep(2)
            except Exception:
                time.sleep(3)

    def set_visual_site(self, site: str):
        """Cambiar el sitio que controla la visual (foto grande)."""
        self.visual_site = site

    # Exponer mapa de lectores activos por sitio (para UI)
    def get_active_reader_names(self) -> dict:
        try:
            return dict(self._active_reader_names)
        except Exception:
            return {}


# Elegir instancia global: si hay 2 sitios configurados, usar multi; si no, usar simple
_cfg = _try_load_sites_config()
_sites_count = len((_cfg.get('sites') or {}).keys())
try:
    _readers_count = len(acr122u_reader.get_available_readers()) if hasattr(acr122u_reader, 'get_available_readers') else 0
except Exception:
    _readers_count = 0

# Usar Multi si hay ≥2 sitios configurados o ≥2 lectores físicos detectados
_use_multi = _sites_count >= 2 or _readers_count >= 2
nfc_reader = NFCReaderMulti() if _use_multi else NFCReader()