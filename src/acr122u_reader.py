#!/usr/bin/env python3
"""
Módulo específico para lector ACR122U NFC/RFID
Compatible con tarjetas Mifare Classic, Mifare Ultralight, etc.
"""

import threading
import time
import os
import importlib
import binascii

def _load_smartcard():
    """Carga dinámica de módulos smartcard; retorna un dict con referencias o None si no disponible."""
    try:
        sys_mod = importlib.import_module('smartcard.System')
        util_mod = importlib.import_module('smartcard.util')
        cardtype_mod = importlib.import_module('smartcard.CardType')
        cardreq_mod = importlib.import_module('smartcard.CardRequest')
        exc_mod = importlib.import_module('smartcard.Exceptions')
        return {
            'System': sys_mod,
            'util': util_mod,
            'CardType': cardtype_mod,
            'CardRequest': cardreq_mod,
            'Exceptions': exc_mod,
        }
    except Exception:
        return None

class ACR122UReader:
    def __init__(self, callback=None, force_name: str | None = None, force_index: int | None = None):
        self.callback = callback
        self.is_reading = False
        self.reader = None
        self.connection = None
        self.last_uid = None
        self.last_read_time = 0
        self.debounce_time = 2  # 2 segundos entre lecturas de la misma tarjeta
        # Control de presencia para requerir quitar y volver a poner la tarjeta
        self.present_uid = None
        self.card_removed = True
        # Preferencias forzadas por instancia (para multi-lector)
        self._force_name = force_name
        self._force_index = force_index
        
        # Comandos APDU para lectura de UID
        self.GET_UID_COMMAND = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        
        self.setup_reader()
    
    def setup_reader(self, force_reader: str | None = None):
        """Configurar el lector ACR122U"""
        try:
            sc = _load_smartcard()
            if not sc:
                print("❌ Librerías smartcard no disponibles")
                return False
            # Obtener lista de lectores disponibles
            available_readers = sc['System'].readers()
            if available_readers:
                print("🔍 Lectores PC/SC detectados:")
                for i, r in enumerate(available_readers, 1):
                    print(f"  {i}. {r}")
            
            if not available_readers:
                print("❌ No se encontraron lectores NFC/RFID")
                print("Verifique que el ACR122U esté conectado correctamente")
                return False
            
            # Buscar el ACR122U específicamente
            acr122u_reader = None
            # Permitir selección por variables de entorno
            preferred_name = self._force_name or os.getenv('NFC_READER_NAME')
            preferred_index = self._force_index if self._force_index is not None else os.getenv('NFC_READER_INDEX')
            if force_reader:
                preferred_name = force_reader

            if preferred_name:
                for r in available_readers:
                    if preferred_name.lower() in str(r).lower():
                        acr122u_reader = r
                        print(f"✅ Usando lector por nombre configurado: {r}")
                        break
            elif preferred_index:
                try:
                    idx = int(preferred_index) - 1
                    if 0 <= idx < len(available_readers):
                        acr122u_reader = available_readers[idx]
                        print(f"✅ Usando lector por índice configurado: {acr122u_reader}")
                except Exception:
                    pass

            # Si aún no se eligió, tomar el primer ACR122U disponible
            if not acr122u_reader:
                for reader in available_readers:
                    reader_name = str(reader).lower()
                    if 'acr122' in reader_name or 'acr 122' in reader_name:
                        acr122u_reader = reader
                        break
            
            if not acr122u_reader:
                # Si no encuentra ACR122U por nombre, usar el primer lector disponible
                acr122u_reader = available_readers[0]
                print(f"⚠️  ACR122U no detectado por nombre, usando: {acr122u_reader}")
            else:
                print(f"✅ ACR122U detectado: {acr122u_reader}")
            
            self.reader = acr122u_reader
            return True
            
        except Exception as e:
            print(f"❌ Error configurando lector: {e}")
            return False
    
    def start_reading(self):
        """Iniciar lectura continua de tarjetas"""
        if not self.reader:
            print("❌ Lector no configurado")
            return False
        
        if self.is_reading:
            print("⚠️  La lectura ya está activa")
            return True
        
        self.is_reading = True
        
        # Iniciar hilo de lectura
        read_thread = threading.Thread(target=self._continuous_read, daemon=True)
        read_thread.start()
        
        print("🔄 Lectura NFC iniciada - Acerque una tarjeta al lector")
        return True
    
    def stop_reading(self):
        """Detener lectura de tarjetas"""
        self.is_reading = False
        if self.connection:
            try:
                self.connection.disconnect()
            except:
                pass
        print("⏹️  Lectura NFC detenida")
    
    def _continuous_read(self):
        """Bucle principal de lectura continua"""
        while self.is_reading:
            try:
                sc = _load_smartcard()
                if not sc:
                    time.sleep(0.5)
                    continue
                # Crear solicitud de tarjeta con timeout
                cardtype = sc['CardType'].AnyCardType()
                cardrequest = sc['CardRequest'].CardRequest(timeout=1, cardType=cardtype, readers=[self.reader])
                
                try:
                    # Esperar por una tarjeta
                    cardservice = cardrequest.waitforcard()
                    
                    # Conectar a la tarjeta
                    cardservice.connection.connect()
                    self.connection = cardservice.connection
                    
                    # Leer UID de la tarjeta
                    uid = self._read_card_uid()
                    
                    if uid:
                        current_time = time.time()
                        # Requerir que la tarjeta se retire antes de volver a registrar el mismo UID
                        # Además, mantener debounce de 2s como seguro adicional
                        allow = False
                        if uid != self.present_uid:
                            # Nueva tarjeta
                            allow = True
                        else:
                            # Misma tarjeta; solo permitir si se detectó ausencia desde la última lectura
                            if self.card_removed and (uid != self.last_uid or (current_time - self.last_read_time) > self.debounce_time):
                                allow = True

                        if allow:
                            self.present_uid = uid
                            self.card_removed = False
                            self.last_uid = uid
                            self.last_read_time = current_time
                            print(f"💳 Tarjeta detectada: {uid}")
                            if self.callback:
                                self.callback(uid)
                    
                    # Desconectar
                    cardservice.connection.disconnect()
                    
                except sc['Exceptions'].CardRequestTimeoutException:
                    # Timeout normal: interpretamos como que no hay tarjeta presente
                    self.card_removed = True
                    self.present_uid = None
                except sc['Exceptions'].NoCardException:
                    # No hay tarjeta, continuar
                    self.card_removed = True
                    self.present_uid = None
                except Exception as e:
                    print(f"⚠️  Error leyendo tarjeta: {e}")
                    time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error en bucle de lectura: {e}")
                time.sleep(1)
            
            # Pequeña pausa para no saturar el CPU
            time.sleep(0.1)
    
    def _read_card_uid(self):
        """Leer UID de la tarjeta Mifare"""
        try:
            if not self.connection:
                return None
            
            # Enviar comando para obtener UID
            response, sw1, sw2 = self.connection.transmit(self.GET_UID_COMMAND)
            
            # Verificar respuesta exitosa
            if sw1 == 0x90 and sw2 == 0x00:
                # Convertir respuesta a string hexadecimal
                uid = ''.join(['%02X' % x for x in response])
                return uid
            else:
                print(f"⚠️  Error en respuesta: SW1={sw1:02X}, SW2={sw2:02X}")
                return None
                
        except Exception as e:
            print(f"❌ Error leyendo UID: {e}")
            return None
    
    def read_single_card(self, timeout=10):
        """Leer una sola tarjeta (para registro manual)"""
        try:
            print(f"🔍 Esperando tarjeta... (timeout: {timeout}s)")
            
            sc = _load_smartcard()
            if not sc:
                print("❌ Librerías smartcard no disponibles")
                return None
            cardtype = sc['CardType'].AnyCardType()
            cardrequest = sc['CardRequest'].CardRequest(timeout=timeout, cardType=cardtype, readers=[self.reader])
            
            cardservice = cardrequest.waitforcard()
            cardservice.connection.connect()
            self.connection = cardservice.connection
            
            uid = self._read_card_uid()
            
            cardservice.connection.disconnect()
            
            if uid:
                print(f"✅ UID leído: {uid}")
                return uid
            else:
                print("❌ No se pudo leer el UID")
                return None
                
        except Exception as e:
            # Detectar timeout específico si existe la excepción
            sc = _load_smartcard()
            if sc and isinstance(e, sc['Exceptions'].CardRequestTimeoutException):
                print("⏰ Timeout esperando tarjeta")
                return None
            # Otro error
            print(f"❌ Error leyendo tarjeta: {e}")
            return None
    
    def write_mifare_data(self, uid, data, block=4):
        """Escribir datos en tarjeta Mifare (opcional para futuras expansiones)"""
        try:
            # Esta función puede expandirse para escribir datos adicionales
            # Por ahora solo retornamos True ya que solo necesitamos leer UID
            print(f"📝 Función de escritura preparada para UID: {uid}")
            return True
        except Exception as e:
            print(f"❌ Error escribiendo datos: {e}")
            return False
    
    def get_card_info(self):
        """Obtener información adicional de la tarjeta"""
        try:
            if not self.connection:
                return None
            
            # Comando para obtener información del chip
            info_command = [0xFF, 0x00, 0x48, 0x00, 0x00]
            response, sw1, sw2 = self.connection.transmit(info_command)
            
            if sw1 == 0x90 and sw2 == 0x00:
                return {
                    'chip_type': self._identify_chip_type(response),
                    'response': ' '.join([f"{b:02X}" for b in response])
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error obteniendo info de tarjeta: {e}")
            return None
    
    def _identify_chip_type(self, response):
        """Identificar tipo de chip Mifare"""
        if len(response) >= 2:
            atqa = response[0:2]
            if atqa == [0x00, 0x04]:
                return "Mifare Classic 1K"
            elif atqa == [0x00, 0x02]:
                return "Mifare Classic 4K"
            elif atqa == [0x00, 0x44]:
                return "Mifare Ultralight"
        
        return "Desconocido"
    
    def test_reader(self):
        """Probar funcionamiento del lector"""
        print("🧪 Probando lector ACR122U...")
        
        if not self.reader:
            print("❌ Lector no disponible")
            return False
        
        try:
            # Probar conexión básica
            sc = _load_smartcard()
            if not sc:
                print("❌ Librerías smartcard no disponibles")
                return False
            cardtype = sc['CardType'].AnyCardType()
            cardrequest = sc['CardRequest'].CardRequest(timeout=2, cardType=cardtype, readers=[self.reader])
            
            print("✅ Lector responde correctamente")
            print("💳 Acerque una tarjeta para probar lectura...")
            
            uid = self.read_single_card(5)
            if uid:
                print(f"✅ Prueba exitosa - UID: {uid}")
                return True
            else:
                print("⚠️  No se detectó tarjeta en el tiempo esperado")
                return False
                
        except Exception as e:
            print(f"❌ Error en prueba: {e}")
            return False

# Función de utilidad para detectar lectores
def detect_acr122u():
    """Detectar si el ACR122U está conectado"""
    try:
        sc = _load_smartcard()
        if not sc:
            print("❌ Librerías smartcard no disponibles")
            return False
        available_readers = sc['System'].readers()
        
        print("🔍 Lectores detectados:")
        for i, reader in enumerate(available_readers):
            reader_name = str(reader)
            print(f"  {i+1}. {reader_name}")
            
            if 'acr122' in reader_name.lower() or 'acr 122' in reader_name.lower():
                print(f"    ✅ ACR122U encontrado!")
                return True
        
        if available_readers:
            print("⚠️  ACR122U no detectado por nombre, pero hay lectores disponibles")
            return True
        else:
            print("❌ No se detectaron lectores")
            return False
            
    except Exception as e:
        print(f"❌ Error detectando lectores: {e}")
        return False

# Función principal de prueba
def main():
    """Función principal para probar el módulo"""
    print("🚀 Módulo ACR122U - Sistema de Asistencia NFC")
    print("=" * 50)
    
    # Detectar lector
    if not detect_acr122u():
        print("\n❌ No se puede continuar sin lector")
        return
    
    # Crear instancia del lector
    def card_detected(uid):
        print(f"🎯 Callback: Tarjeta procesada - {uid}")
    
    reader = ACR122UReader(callback=card_detected)
    
    # Probar lector
    if reader.test_reader():
        print("\n✅ Lector configurado correctamente")
        
        # Iniciar lectura continua
        reader.start_reading()
        
        try:
            print("\n🔄 Lectura continua activa...")
            print("💳 Acerque tarjetas al lector (Ctrl+C para salir)")
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n⏹️  Deteniendo lectura...")
            reader.stop_reading()
            print("✅ Proceso terminado")
    
    else:
        print("\n❌ Error en configuración del lector")

if __name__ == "__main__":
    main()