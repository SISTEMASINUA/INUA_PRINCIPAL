import boto3
import threading
import time
import json
import os
from datetime import datetime
from database_manager import db_manager
from dotenv import load_dotenv

load_dotenv()

class CloudSyncManager:
    def __init__(self):
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.bucket_name = os.getenv('AWS_BUCKET_NAME', 'asistencia-nfc-bucket')
        
        self.s3_client = None
        self.sync_interval = 60  # Sincronizar cada 60 segundos
        self.is_syncing = False
        
        self.init_aws_connection()
    
    def init_aws_connection(self):
        """Inicializar conexión con AWS"""
        try:
            if self.aws_access_key and self.aws_secret_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                
                # Verificar si el bucket existe, si no, crearlo
                try:
                    self.s3_client.head_bucket(Bucket=self.bucket_name)
                    print("Conexión con AWS S3 establecida")
                except Exception as e:
                    # Credenciales inválidas o bucket inexistente sin permisos -> desactivar S3
                    print(f"AWS S3 desactivado: {e}")
                    self.s3_client = None
            else:
                print("Credenciales de AWS no configuradas")
                
        except Exception as e:
            print(f"Error conectando con AWS: {e}")
    
    def start_sync_service(self):
        """Iniciar servicio de sincronización automática"""
        if not self.is_syncing:
            self.is_syncing = True
            sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            sync_thread.start()
            print("Servicio de sincronización iniciado")
    
    def stop_sync_service(self):
        """Detener servicio de sincronización"""
        self.is_syncing = False
        print("Servicio de sincronización detenido")
    
    def _sync_loop(self):
        """Bucle principal de sincronización"""
        while self.is_syncing:
            try:
                # Verificar conexión a internet
                if db_manager.is_online():
                    # Sincronizar datos locales a PostgreSQL
                    db_manager.sync_registros_to_cloud()
                    
                    # Sincronizar empleados desde PostgreSQL a local
                    db_manager.sync_empleados_to_local()
                    
                    # Sincronizar datos con AWS S3
                    if self.s3_client:
                        self.sync_data_to_s3()
                        self.sync_data_from_s3()
                
                time.sleep(self.sync_interval)
                
            except Exception as e:
                print(f"Error en bucle de sincronización: {e}")
                time.sleep(30)  # Esperar más tiempo si hay error
    
    def sync_data_to_s3(self):
        """Sincronizar datos a AWS S3"""
        try:
            if not self.s3_client:
                return
            
            # Obtener datos de empleados
            employees_data = self._get_employees_data()
            if employees_data:
                self._upload_json_to_s3(employees_data, 'employees.json')
            
            # Obtener datos de registros recientes (último mes)
            records_data = self._get_recent_records_data()
            if records_data:
                self._upload_json_to_s3(records_data, 'recent_records.json')
            
            # Subir configuraciones
            config_data = self._get_config_data()
            if config_data:
                self._upload_json_to_s3(config_data, 'config.json')
            
        except Exception as e:
            print(f"Error sincronizando a S3: {e}")
    
    def sync_data_from_s3(self):
        """Sincronizar datos desde AWS S3"""
        try:
            if not self.s3_client:
                return
            
            # Descargar y aplicar configuraciones
            config_data = self._download_json_from_s3('config.json')
            if config_data:
                self._apply_config_data(config_data)
            
            # Sincronizar empleados si la base de datos local está vacía
            if self._is_local_employees_empty():
                employees_data = self._download_json_from_s3('employees.json')
                if employees_data:
                    self._apply_employees_data(employees_data)
            
        except Exception as e:
            print(f"Error sincronizando desde S3: {e}")
    
    def _get_employees_data(self):
        """Obtener datos de empleados para sincronización"""
        try:
            if db_manager.is_online():
                cursor = db_manager.pg_connection.cursor()
                cursor.execute("""
                    SELECT id, nombre_completo, cargo, rol, nfc_uid, foto_path,
                           hora_entrada, hora_salida, activo, fecha_registro
                    FROM empleados
                """)
                rows = cursor.fetchall()
                
                employees = []
                for row in rows:
                    employee = {
                        'id': row[0],
                        'nombre_completo': row[1],
                        'cargo': row[2],
                        'rol': row[3],
                        'nfc_uid': row[4],
                        'foto_path': row[5],
                        'hora_entrada': str(row[6]) if row[6] else None,
                        'hora_salida': str(row[7]) if row[7] else None,
                        'activo': row[8],
                        'fecha_registro': row[9].isoformat() if row[9] else None
                    }
                    employees.append(employee)
                
                return {
                    'employees': employees,
                    'last_sync': datetime.now().isoformat(),
                    'source': 'postgresql'
                }
            
        except Exception as e:
            print(f"Error obteniendo datos de empleados: {e}")
            return None
    
    def _get_recent_records_data(self):
        """Obtener datos de registros recientes"""
        try:
            if db_manager.is_online():
                cursor = db_manager.pg_connection.cursor()
                cursor.execute("""
                    SELECT r.id, r.empleado_id, r.ubicacion_id, r.fecha,
                           r.hora_registro, r.tipo_movimiento, r.estado,
                           e.nombre_completo, u.nombre as ubicacion
                    FROM registros_asistencia r
                    JOIN empleados e ON r.empleado_id = e.id
                    JOIN ubicaciones u ON r.ubicacion_id = u.id
                    WHERE r.fecha >= CURRENT_DATE - INTERVAL '30 days'
                    ORDER BY r.fecha DESC, r.hora_registro DESC
                """)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = {
                        'id': row[0],
                        'empleado_id': row[1],
                        'ubicacion_id': row[2],
                        'fecha': row[3].isoformat() if row[3] else None,
                        'hora_registro': row[4].isoformat() if row[4] else None,
                        'tipo_movimiento': row[5],
                        'estado': row[6],
                        'empleado_nombre': row[7],
                        'ubicacion_nombre': row[8]
                    }
                    records.append(record)
                
                return {
                    'records': records,
                    'last_sync': datetime.now().isoformat(),
                    'source': 'postgresql'
                }
            
        except Exception as e:
            print(f"Error obteniendo registros recientes: {e}")
            return None
    
    def _get_config_data(self):
        """Obtener datos de configuración"""
        try:
            if db_manager.is_online():
                cursor = db_manager.pg_connection.cursor()
                cursor.execute("SELECT clave, valor, descripcion FROM configuraciones")
                rows = cursor.fetchall()
                
                config = {}
                for row in rows:
                    config[row[0]] = {
                        'valor': row[1],
                        'descripcion': row[2]
                    }
                
                return {
                    'config': config,
                    'last_sync': datetime.now().isoformat(),
                    'source': 'postgresql'
                }
            
        except Exception as e:
            print(f"Error obteniendo configuración: {e}")
            return None
    
    def _upload_json_to_s3(self, data, filename):
        """Subir datos JSON a S3"""
        try:
            json_string = json.dumps(data, ensure_ascii=False, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=json_string.encode('utf-8'),
                ContentType='application/json'
            )
            
            print(f"Archivo {filename} subido a S3")
            
        except Exception as e:
            print(f"Error subiendo {filename} a S3: {e}")
    
    def _download_json_from_s3(self, filename):
        """Descargar datos JSON desde S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=filename)
            data = json.loads(response['Body'].read().decode('utf-8'))
            return data
            
        except Exception as e:
            print(f"Error descargando {filename} desde S3: {e}")
            return None
    
    def _apply_config_data(self, config_data):
        """Aplicar datos de configuración"""
        try:
            if 'config' not in config_data:
                return
            
            cursor = db_manager.sqlite_connection.cursor()
            
            for clave, data in config_data['config'].items():
                cursor.execute("""
                    INSERT OR REPLACE INTO configuraciones_local (clave, valor)
                    VALUES (?, ?)
                """, (clave, data['valor']))
            
            db_manager.sqlite_connection.commit()
            print("Configuración sincronizada desde S3")
            
        except Exception as e:
            print(f"Error aplicando configuración: {e}")
    
    def _apply_employees_data(self, employees_data):
        """Aplicar datos de empleados"""
        try:
            if 'employees' not in employees_data:
                return
            
            cursor = db_manager.sqlite_connection.cursor()
            cursor.execute("DELETE FROM empleados_local")
            
            for employee in employees_data['employees']:
                cursor.execute("""
                    INSERT INTO empleados_local 
                    (id, nombre_completo, cargo, rol, nfc_uid, foto_path, 
                     hora_entrada, hora_salida, activo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    employee['id'],
                    employee['nombre_completo'],
                    employee['cargo'],
                    employee['rol'],
                    employee['nfc_uid'],
                    employee['foto_path'],
                    employee['hora_entrada'],
                    employee['hora_salida'],
                    employee['activo']
                ))
            
            db_manager.sqlite_connection.commit()
            print(f"Sincronizados {len(employees_data['employees'])} empleados desde S3")
            
        except Exception as e:
            print(f"Error aplicando datos de empleados: {e}")
    
    def _is_local_employees_empty(self):
        """Verificar si la tabla local de empleados está vacía"""
        try:
            cursor = db_manager.sqlite_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM empleados_local WHERE activo = 1")
            count = cursor.fetchone()[0]
            return count == 0
            
        except Exception as e:
            print(f"Error verificando empleados locales: {e}")
            return True
    
    def manual_sync(self):
        """Sincronización manual"""
        try:
            print("Iniciando sincronización manual...")
            
            if db_manager.is_online():
                # Sincronizar registros locales a la nube
                db_manager.sync_registros_to_cloud()
                # Sincronizar empleados de la nube a local
                db_manager.sync_empleados_to_local()
                
                # Sincronizar con S3
                if self.s3_client:
                    self.sync_data_to_s3()
                    self.sync_data_from_s3()
                
                print("Sincronización manual completada")
                return True
            else:
                print("No hay conexión a internet para sincronización")
                return False
                
        except Exception as e:
            print(f"Error en sincronización manual: {e}")
            return False
    
    def backup_to_s3(self, backup_name=None):
        """Crear backup completo en S3"""
        try:
            if not self.s3_client:
                return False
            
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Backup de empleados
            employees_data = self._get_employees_data()
            if employees_data:
                self._upload_json_to_s3(employees_data, f"backups/{backup_name}/employees.json")
            
            # Backup de todos los registros
            all_records = self._get_all_records_data()
            if all_records:
                self._upload_json_to_s3(all_records, f"backups/{backup_name}/all_records.json")
            
            # Backup de configuración
            config_data = self._get_config_data()
            if config_data:
                self._upload_json_to_s3(config_data, f"backups/{backup_name}/config.json")
            
            print(f"Backup {backup_name} creado en S3")
            return True
            
        except Exception as e:
            print(f"Error creando backup: {e}")
            return False
    
    def _get_all_records_data(self):
        """Obtener todos los registros para backup"""
        try:
            if db_manager.is_online():
                cursor = db_manager.pg_connection.cursor()
                cursor.execute("""
                    SELECT r.*, e.nombre_completo, u.nombre as ubicacion
                    FROM registros_asistencia r
                    JOIN empleados e ON r.empleado_id = e.id
                    JOIN ubicaciones u ON r.ubicacion_id = u.id
                    ORDER BY r.fecha DESC, r.hora_registro DESC
                """)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = {
                        'id': row[0],
                        'empleado_id': row[1],
                        'ubicacion_id': row[2],
                        'fecha': row[3].isoformat() if row[3] else None,
                        'hora_registro': row[4].isoformat() if row[4] else None,
                        'tipo_movimiento': row[5],
                        'estado': row[6],
                        'sincronizado': row[7],
                        'fecha_creacion': row[8].isoformat() if row[8] else None,
                        'empleado_nombre': row[9],
                        'ubicacion_nombre': row[10]
                    }
                    records.append(record)
                
                return {
                    'records': records,
                    'backup_date': datetime.now().isoformat(),
                    'source': 'postgresql'
                }
            
        except Exception as e:
            print(f"Error obteniendo todos los registros: {e}")
            return None

# Instancia global del gestor de sincronización
cloud_sync = CloudSyncManager()