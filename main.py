#!/usr/bin/env python3
"""
Sistema de Control de Asistencia NFC
Versión 1.0
Desarrollado para control de asistencia con tecnología NFC
Soporte para múltiples ubicaciones: Tepanecos, Lerdo, Destino
"""

import os
import sys
import threading
import time
from datetime import datetime
import socket

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database_manager import db_manager
from main_screen import MainPublicScreen
from nfc_handler import nfc_reader, AttendanceValidator
from report_generator import report_generator
from cloud_sync import cloud_sync

class SistemaAsistenciaNFC:
    def __init__(self):
        self.main_screen = None
        self.services_running = False
        
        print("Iniciando Sistema de Control de Asistencia NFC...")
        print("=" * 50)
        
        # Verificar dependencias
        self.check_dependencies()
        
        # Inicializar base de datos
        self.init_database()
        
        # Configurar servicios
        self.setup_services()
        
    def check_dependencies(self):
        """Verificar que todas las dependencias estén instaladas"""
        try:
            import tkinter
            import PIL
            import pandas
            print("✓ Dependencias básicas verificadas")
            
            # Verificar psycopg2 opcional
            try:
                import psycopg2
                print("✓ PostgreSQL disponible")
            except ImportError:
                print("⚠ PostgreSQL no disponible - funcionando solo con SQLite")
                
        except ImportError as e:
            print(f"✗ Error de dependencias críticas: {e}")
            print("Instale las dependencias ejecutando: pip install -r requirements.txt")
            sys.exit(1)
    
    def init_database(self):
        """Inicializar conexión a base de datos"""
        print("Configurando base de datos...")
        
        # Intentar conectar a PostgreSQL
        if db_manager.connect_postgresql():
            print("✓ Conectado a PostgreSQL")
            # Sincronizar empleados a base local
            db_manager.sync_empleados_to_local()
        else:
            print("⚠ PostgreSQL no disponible, usando base de datos local")
        
        print("✓ Base de datos inicializada")
    
    def setup_services(self):
        """Configurar todos los servicios del sistema"""
        print("Configurando servicios...")
        
        # Configurar lector NFC
        self.main_screen = MainPublicScreen()
        nfc_reader.main_screen = self.main_screen
        
        # Iniciar servicio de sincronización en la nube
        cloud_sync.start_sync_service()
        
        # Iniciar lector NFC
        nfc_reader.start_reading()
        
        # Programar tareas automáticas
        self.schedule_automatic_tasks()
        
        print("✓ Servicios configurados")
    
    def schedule_automatic_tasks(self):
        """Programar tareas automáticas"""
        def automatic_tasks():
            while self.services_running:
                try:
                    now = datetime.now()
                    
                    # Verificar asistencias diarias cada hora
                    if now.minute == 0:
                        AttendanceValidator.check_daily_attendance()
                    
                    # Generar reportes automáticos el primer día del mes a las 8 AM
                    if now.day == 1 and now.hour == 8 and now.minute == 0:
                        report_generator.auto_generate_monthly_reports()
                    
                    # Crear backup en la nube cada domingo a las 23:00
                    if now.weekday() == 6 and now.hour == 23 and now.minute == 0:
                        cloud_sync.backup_to_s3()
                    
                    time.sleep(60)  # Verificar cada minuto
                    
                except Exception as e:
                    print(f"Error en tareas automáticas: {e}")
                    time.sleep(300)  # Esperar 5 minutos si hay error
        
        self.services_running = True
        tasks_thread = threading.Thread(target=automatic_tasks, daemon=True)
        tasks_thread.start()
    
    def run(self):
        """Ejecutar el sistema"""
        try:
            print("=" * 50)
            print("Sistema iniciado correctamente")
            print("Pantalla principal: Pública para registros")
            print("Administración: Presione Ctrl+Alt+A")
            print("=" * 50)
            
            # Ejecutar interfaz principal
            self.main_screen.run()
            
        except KeyboardInterrupt:
            print("\nDeteniendo sistema...")
            self.shutdown()
        except Exception as e:
            print(f"Error ejecutando sistema: {e}")
            self.shutdown()
    
    def shutdown(self):
        """Cerrar sistema correctamente"""
        print("Cerrando servicios...")
        
        self.services_running = False
        
        # Detener servicios
        nfc_reader.stop_reading()
        cloud_sync.stop_sync_service()
        
        # Sincronización final
        if db_manager.is_online():
            db_manager.sync_registros_to_cloud()
        
        # Cerrar conexiones de base de datos
        db_manager.close_connections()
        
        print("✓ Sistema cerrado correctamente")

def print_banner():
    """Mostrar banner del sistema"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                SISTEMA DE CONTROL DE ASISTENCIA             ║
    ║                       TECNOLOGÍA NFC                        ║
    ║                                                              ║
    ║  Ubicaciones: Tepanecos • Lerdo • Destino                   ║
    ║  Sincronización en tiempo real                               ║
    ║  Reportes automáticos                                        ║
    ║                                                              ║
    ║  Versión 1.0 - Desarrollado con Python                      ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Función principal"""
    print_banner()
    
    try:
        # Guardia de instancia única (puerto local)
        lock_sock = None
        try:
            lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Puerto arbitrario estable; si está ocupado, ya hay instancia
            lock_sock.bind(('127.0.0.1', 49622))
            lock_sock.listen(1)
        except Exception:
            print("⚠ No se pudo establecer guardia de instancia única; continuando…")

        # Si se pasa --admin, abrir directamente la administración
        if '--admin' in sys.argv:
            from admin_interface import AdminInterface
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()  # Ocultar raíz
            AdminInterface(root)
            root.mainloop()
        else:
            # Crear e iniciar el sistema
            sistema = SistemaAsistenciaNFC()
            sistema.run()
        
    except Exception as e:
        print(f"Error crítico: {e}")
        print("Verifique la configuración e intente nuevamente")
        sys.exit(1)
    finally:
        try:
            if lock_sock:
                lock_sock.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()