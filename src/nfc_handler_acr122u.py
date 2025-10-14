import threading
import time
from datetime import datetime, time as dt_time, timedelta
from database_manager import db_manager
from acr122u_driver import acr122u_reader
import os

class NFCReader:
    def __init__(self, main_screen=None):
        self.main_screen = main_screen
        self.is_reading = False
        self.tolerance_minutes = 10  # 10 minutos de tolerancia
        self.ubicacion_actual = os.getenv('UBICACION_PRINCIPAL', 'Tepanecos')
        
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
                print("❌ No se encontró lector ACR122U")
                print("   Verifica que esté conectado y los drivers instalados")
                print("   Continuando en modo simulación...")
                self._start_simulation_mode()
                return
            
            print(f"✅ Lector encontrado: {available_readers[0]}")
            acr122u_reader.start_reading()
    
    def stop_reading(self):
        """Detener lectura de NFC"""
        self.is_reading = False
        acr122u_reader.stop_reading()
        print("⏹️ Lector NFC detenido")
    
    def _start_simulation_mode(self):
        """Iniciar modo simulación si no hay lector real"""
        print("🎮 Modo simulación activado")
        print("   Usa Ctrl+Alt+N en la pantalla principal para simular tarjetas")
        
        # Thread para simulación automática ocasional
        sim_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        sim_thread.start()
    
    def _simulation_loop(self):
        """Bucle de simulación automática"""
        test_cards = ["1234567890", "0987654321", "1111111111", "2222222222"]
        
        while self.is_reading:
            time.sleep(30)  # Cada 30 segundos
            
            # 10% de probabilidad de simular una tarjeta
            if time.time() % 10 < 1:
                import random
                if random.randint(1, 100) <= 10:
                    uid = random.choice(test_cards)
                    print(f"🎮 Simulando tarjeta: {uid}")
                    self.process_nfc_card(uid)
    
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
                
                # Mostrar en pantalla principal si está disponible
                if self.main_screen:
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
            
            # Verificar último registro del día
            ultimo_registro = self._get_last_record_today(empleado_id, current_date)
            
            if not ultimo_registro:
                # Primer registro del día - debe ser entrada
                tipo_movimiento = "ENTRADA"
                estado = self._calculate_entry_status(current_time, hora_entrada)
                print(f"   Primer registro del día: {estado}")
            else:
                ultimo_tipo = ultimo_registro[4]  # tipo_movimiento del último registro
                
                if ultimo_tipo == "ENTRADA":
                    # El último fue entrada, ahora debe ser salida
                    tipo_movimiento = "SALIDA"
                    estado = self._calculate_exit_status(current_time, hora_salida)
                    print(f"   Registrando salida: {estado}")
                else:
                    # El último fue salida, ahora debe ser entrada
                    tipo_movimiento = "ENTRADA"
                    estado = self._calculate_entry_status(current_time, hora_entrada)
                    print(f"   Nueva entrada: {estado}")
            
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
nfc_reader = NFCReader()