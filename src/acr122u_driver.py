"""
Fachada para lector ACR122U.
Si el hardware/librerías no están disponibles, funciona en modo "sin lector"
sin simulación automática.
"""

import threading
import time

# Fachada para unificar interfaz entre lector real y simulador
class ACR122UFacade:
    def __init__(self, real_reader=None):
        self._real = real_reader
        self.callback_function = None  # para compatibilidad con NFCReader
        self._last_readers = []
        self._reading = False
        self._active_reader_name = None

    def get_available_readers(self):
        try:
            import importlib
            sc_sys = importlib.import_module('smartcard.System')
            readers_func = getattr(sc_sys, 'readers', None)
            if callable(readers_func):
                r = readers_func()
                readers_list = [str(x) for x in r]
                self._last_readers = readers_list
                return readers_list
            return []
        except Exception:
            return []

    def start_reading(self):
        if not self._real:
            print("❌ No hay lector NFC configurado. Conéctelo para iniciar la lectura.")
            return False
        # Propagar callback si se asignó por NFCReader
        if self.callback_function:
            try:
                self._real.callback = self.callback_function
            except Exception:
                pass
        ok = self._real.start_reading()
        if ok:
            self._reading = True
            try:
                # Tomar nombre del lector activo
                self._active_reader_name = str(getattr(self._real, 'reader', None) or '')
            except Exception:
                self._active_reader_name = None
        return ok

    def stop_reading(self):
        if self._real:
            self._real.stop_reading()
        self._reading = False
        self._active_reader_name = None

    def read_single_card(self, timeout=10):
        if not self._real:
            return None, "Lector no disponible"
        uid = self._real.read_single_card(timeout=timeout)
        # Normalizar a tupla para compatibilidad
        if uid:
            return uid, "Lectura exitosa"
        return None, "No se detectó tarjeta"

    def refresh_readers(self):
        """Intentar reconfigurar el lector real si hay cambios (hot-plug)."""
        try:
            current = self.get_available_readers()
            if current != self._last_readers:
                print("🔁 Cambio en lista de lectores detectado. Reconfigurando…")
                # Recordar estado de lectura
                should_be_reading = bool(self._reading)
                # Detener lector actual si existe
                try:
                    if self._real:
                        self._real.stop_reading()
                except Exception:
                    pass
                # Reinstanciar el lector real con el callback actual
                from acr122u_reader import ACR122UReader
                self._real = ACR122UReader(callback=self.callback_function)
                # Reiniciar lectura si corresponde y hay lectores
                if should_be_reading and current:
                    try:
                        ok = self._real.start_reading()
                        self._reading = bool(ok)
                        if ok:
                            try:
                                self._active_reader_name = str(getattr(self._real, 'reader', None) or '')
                            except Exception:
                                self._active_reader_name = None
                    except Exception:
                        self._reading = False
                else:
                    self._reading = False
            return current
        except Exception:
            return self._last_readers

    def reconfigure_with_env(self):
        """Re-instanciar el lector real respetando variables de entorno actuales.
        Útil cuando cambian UBICACION_PRINCIPAL/NFC_READER_NAME/NFC_READER_INDEX sin cambios físicos.
        """
        try:
            from acr122u_reader import ACR122UReader
            _new = ACR122UReader(callback=self.callback_function)
            self._real = _new
            try:
                self._active_reader_name = str(getattr(self._real, 'reader', None) or '')
            except Exception:
                self._active_reader_name = None
            return True
        except Exception as e:
            print(f"⚠️  No se pudo reconfigurar el lector con entorno actual: {e}")
            return False

    def get_active_reader_name(self):
        """Nombre (string) del lector actualmente activo, si hay."""
        return self._active_reader_name

# Crear instancia global según disponibilidad de hardware (sin simulación)
try:
    import importlib
    sc_sys = importlib.import_module('smartcard.System')
    readers_func = getattr(sc_sys, 'readers', None)
    available_readers = readers_func() if callable(readers_func) else []
    if available_readers:
        print("🔍 Lectores PC/SC detectados:")
        for i, r in enumerate(available_readers, 1):
            print(f"  {i}. {r}")
    acr122u_found = any('acr122' in str(reader).lower() for reader in available_readers)

    if acr122u_found:
        print("✅ Lector ACR122U físico detectado")
        from acr122u_reader import ACR122UReader
        _real = ACR122UReader()
        acr122u_reader = ACR122UFacade(real_reader=_real)
    else:
        print("⚠️ No se encontró lector ACR122U físico. Modo sin lector (no simulación).")
        acr122u_reader = ACR122UFacade(real_reader=None)

except Exception as e:
    # Librerías no disponibles o error detectando hardware
    print("📦 Librerías smartcard no disponibles o error detectando hardware. Modo sin lector (no simulación).")
    acr122u_reader = ACR122UFacade(real_reader=None)