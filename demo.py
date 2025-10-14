#!/usr/bin/env python3
"""
Script de prueba para el Sistema de Control de Asistencia NFC
Simula empleados y registros para demostrar el funcionamiento
"""

import os
import sys
import time
from datetime import datetime, timedelta
import random

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database_manager import db_manager
from nfc_handler import nfc_reader

class SistemaDemo:
    def __init__(self):
        self.empleados_demo = [
            {
                'nombre': 'Ronald García',
                'cargo': 'Administrador',
                'rol': 'Gerente',
                'nfc_uid': '1234567890',
                'hora_entrada': '09:00:00',
                'hora_salida': '18:00:00'
            },
            {
                'nombre': 'María López',
                'cargo': 'Secretaria',
                'rol': 'Administrativa',
                'nfc_uid': '0987654321',
                'hora_entrada': '08:30:00',
                'hora_salida': '17:30:00'
            },
            {
                'nombre': 'Juan Pérez',
                'cargo': 'Vendedor',
                'rol': 'Ventas',
                'nfc_uid': '1111111111',
                'hora_entrada': '09:00:00',
                'hora_salida': '18:00:00'
            },
            {
                'nombre': 'Ana Martínez',
                'cargo': 'Contadora',
                'rol': 'Finanzas',
                'nfc_uid': '2222222222',
                'hora_entrada': '08:00:00',
                'hora_salida': '17:00:00'
            }
        ]
    
    def setup_demo_database(self):
        """Configurar base de datos con datos de demostración"""
        print("Configurando base de datos de demostración...")
        
        try:
            # Inicializar base de datos
            db_manager.setup_local_db()
            
            if db_manager.connect_postgresql():
                print("✓ Conectado a PostgreSQL")
                cursor = db_manager.pg_connection.cursor()
                
                # Limpiar datos existentes
                cursor.execute("DELETE FROM registros_asistencia")
                cursor.execute("DELETE FROM empleados")
                
                # Reiniciar secuencias
                cursor.execute("ALTER SEQUENCE empleados_id_seq RESTART WITH 1")
                cursor.execute("ALTER SEQUENCE registros_asistencia_id_seq RESTART WITH 1")
                
                # Insertar empleados de demostración
                for emp in self.empleados_demo:
                    cursor.execute("""
                        INSERT INTO empleados (nombre_completo, cargo, rol, nfc_uid, hora_entrada, hora_salida, activo)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                    """, (emp['nombre'], emp['cargo'], emp['rol'], emp['nfc_uid'], 
                         emp['hora_entrada'], emp['hora_salida']))
                
                db_manager.pg_connection.commit()
                print(f"✓ {len(self.empleados_demo)} empleados de demostración creados")
                
                # Sincronizar a base local
                db_manager.sync_empleados_to_local()
                
            else:
                print("⚠ Usando solo base de datos local")
                cursor = db_manager.sqlite_connection.cursor()
                
                # Limpiar datos existentes
                cursor.execute("DELETE FROM empleados_local")
                cursor.execute("DELETE FROM registros_local")
                
                # Insertar empleados de demostración
                for i, emp in enumerate(self.empleados_demo, 1):
                    cursor.execute("""
                        INSERT INTO empleados_local (id, nombre_completo, cargo, rol, nfc_uid, hora_entrada, hora_salida, activo)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """, (i, emp['nombre'], emp['cargo'], emp['rol'], emp['nfc_uid'], 
                         emp['hora_entrada'], emp['hora_salida']))
                
                db_manager.sqlite_connection.commit()
                print(f"✓ {len(self.empleados_demo)} empleados de demostración creados (local)")
            
        except Exception as e:
            print(f"Error configurando base de datos: {e}")
    
    def simulate_daily_attendance(self, days_back=0):
        """Simular asistencia de un día"""
        fecha_simulacion = datetime.now().date() - timedelta(days=days_back)
        print(f"Simulando asistencia para {fecha_simulacion}")
        
        for i, emp in enumerate(self.empleados_demo):
            empleado_id = i + 1
            nfc_uid = emp['nfc_uid']
            
            # Simular diferentes escenarios
            escenario = random.choice(['normal', 'retardo', 'temprano', 'falta'])
            
            if escenario == 'falta':
                print(f"  {emp['nombre']}: FALTA")
                continue
            
            # Simular entrada
            hora_entrada_base = datetime.strptime(emp['hora_entrada'], '%H:%M:%S').time()
            entrada_dt = datetime.combine(fecha_simulacion, hora_entrada_base)
            
            if escenario == 'retardo':
                # Llegar 15-30 minutos tarde
                minutos_retraso = random.randint(15, 30)
                entrada_dt += timedelta(minutes=minutos_retraso)
                estado_entrada = 'RETARDO'
                print(f"  {emp['nombre']}: ENTRADA {entrada_dt.strftime('%H:%M:%S')} (RETARDO)")
            else:
                # Llegar a tiempo o temprano
                if random.choice([True, False]):
                    # Llegar temprano (0-15 minutos)
                    minutos_temprano = random.randint(0, 15)
                    entrada_dt -= timedelta(minutes=minutos_temprano)
                estado_entrada = 'A_TIEMPO'
                print(f"  {emp['nombre']}: ENTRADA {entrada_dt.strftime('%H:%M:%S')} (A TIEMPO)")
            
            # Registrar entrada
            self.register_attendance_for_date(empleado_id, entrada_dt, 'ENTRADA', estado_entrada)
            
            # Simular salida (si no es falta)
            hora_salida_base = datetime.strptime(emp['hora_salida'], '%H:%M:%S').time()
            salida_dt = datetime.combine(fecha_simulacion, hora_salida_base)
            
            if escenario == 'temprano':
                # Salir 30-60 minutos temprano
                minutos_temprano = random.randint(30, 60)
                salida_dt -= timedelta(minutes=minutos_temprano)
                estado_salida = 'TEMPRANO'
                print(f"  {emp['nombre']}: SALIDA {salida_dt.strftime('%H:%M:%S')} (TEMPRANO)")
            else:
                # Salir a tiempo o tarde
                if random.choice([True, False]):
                    # Quedarse más tiempo (0-30 minutos)
                    minutos_extra = random.randint(0, 30)
                    salida_dt += timedelta(minutes=minutos_extra)
                estado_salida = 'A_TIEMPO'
                print(f"  {emp['nombre']}: SALIDA {salida_dt.strftime('%H:%M:%S')} (A TIEMPO)")
            
            # Registrar salida
            self.register_attendance_for_date(empleado_id, salida_dt, 'SALIDA', estado_salida)
    
    def register_attendance_for_date(self, empleado_id, fecha_hora, tipo_movimiento, estado):
        """Registrar asistencia para una fecha específica"""
        try:
            fecha = fecha_hora.date().isoformat()
            hora = fecha_hora.isoformat()
            ubicacion = 'Tepanecos'
            
            if db_manager.is_online():
                cursor = db_manager.pg_connection.cursor()
                cursor.execute("SELECT id FROM ubicaciones WHERE nombre = %s", (ubicacion,))
                ubicacion_result = cursor.fetchone()
                
                if ubicacion_result:
                    ubicacion_id = ubicacion_result[0]
                    cursor.execute("""
                        INSERT INTO registros_asistencia 
                        (empleado_id, ubicacion_id, fecha, hora_registro, tipo_movimiento, estado, sincronizado)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                    """, (empleado_id, ubicacion_id, fecha, hora, tipo_movimiento, estado))
                    db_manager.pg_connection.commit()
            else:
                cursor = db_manager.sqlite_connection.cursor()
                cursor.execute("""
                    INSERT INTO registros_local 
                    (empleado_id, ubicacion_nombre, fecha, hora_registro, tipo_movimiento, estado)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (empleado_id, ubicacion, fecha, hora, tipo_movimiento, estado))
                db_manager.sqlite_connection.commit()
                
        except Exception as e:
            print(f"Error registrando asistencia: {e}")
    
    def simulate_week_attendance(self):
        """Simular asistencia de una semana"""
        print("Simulando asistencia de los últimos 7 días...")
        for day in range(7):
            print(f"\nDía {day + 1}:")
            self.simulate_daily_attendance(day)
    
    def test_nfc_reading(self):
        """Probar lectura de NFC con empleados de demostración"""
        print("\nPrueba de lectura NFC:")
        print("Simulando tarjetas NFC de empleados...")
        
        for emp in self.empleados_demo:
            print(f"\nSimulando tarjeta de {emp['nombre']} ({emp['nfc_uid']})")
            resultado = nfc_reader.process_nfc_card(emp['nfc_uid'])
            if resultado:
                print("✓ Registro exitoso")
            else:
                print("✗ Error en registro")
            time.sleep(2)  # Pausa entre registros
    
    def show_demo_info(self):
        """Mostrar información de la demostración"""
        print("\n" + "="*60)
        print("SISTEMA DE ASISTENCIA NFC - MODO DEMOSTRACIÓN")
        print("="*60)
        print("\nEmpleados de demostración:")
        for emp in self.empleados_demo:
            print(f"  📋 {emp['nombre']} - {emp['cargo']}")
            print(f"     🕘 Horario: {emp['hora_entrada']} - {emp['hora_salida']}")
            print(f"     🏷️  NFC UID: {emp['nfc_uid']}")
            print()
        
        print("Funciones disponibles:")
        print("  1. Configurar base de datos")
        print("  2. Simular asistencia diaria")
        print("  3. Simular asistencia semanal")
        print("  4. Probar lectura NFC")
        print("  5. Ejecutar sistema completo")
        print("="*60)
    
    def run_demo(self):
        """Ejecutar demostración interactiva"""
        self.show_demo_info()
        
        while True:
            print("\nSeleccione una opción:")
            print("1. Configurar base de datos")
            print("2. Simular asistencia hoy")
            print("3. Simular semana completa")
            print("4. Probar NFC")
            print("5. Ejecutar sistema")
            print("0. Salir")
            
            opcion = input("\nOpción: ").strip()
            
            if opcion == "1":
                self.setup_demo_database()
            elif opcion == "2":
                self.simulate_daily_attendance()
            elif opcion == "3":
                self.simulate_week_attendance()
            elif opcion == "4":
                self.test_nfc_reading()
            elif opcion == "5":
                print("Ejecutando sistema completo...")
                os.system("python main.py")
            elif opcion == "0":
                print("¡Hasta luego!")
                break
            else:
                print("Opción no válida")

def main():
    print("🚀 DEMO - Sistema de Control de Asistencia NFC")
    
    try:
        demo = SistemaDemo()
        demo.run_demo()
    except KeyboardInterrupt:
        print("\n\nDemo interrumpido por el usuario")
    except Exception as e:
        print(f"\nError en demo: {e}")

if __name__ == "__main__":
    main()