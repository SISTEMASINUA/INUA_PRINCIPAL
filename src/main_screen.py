import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageOps
import datetime
import threading
import time
import os
from database_manager import db_manager
from admin_interface import AdminInterface

class MainPublicScreen:
    def __init__(self):
        self.root = tk.Tk()
        # Versión del sistema
        self.version = os.getenv('APP_VERSION', '2.0')
        self.root.title(f"Sistema de Asistencia NFC v{self.version}")
        self.root.state('zoomed')  # Pantalla completa en Windows
        # Icono de la aplicación (si existe)
        try:
            from pathlib import Path
            ico = Path(__file__).resolve().parents[1] / 'assets' / 'app_icon.ico'
            if ico.exists():
                self.root.iconbitmap(default=str(ico))
        except Exception:
            pass
        # Paleta moderna
        self.bg_primary = '#0B132B'     # fondo oscuro
        self.bg_card = '#1C2541'        # tarjetas
        self.accent = '#5BC0BE'         # acento
        self.accent_alt = '#FFD166'     # acento secundario
        self.text_primary = '#E0E0E0'
        self.text_muted = '#A0AEC0'
        self.ok = '#4CAF50'
        self.warn = '#FF9800'
        self.err = '#EF5350'
        self.root.configure(bg=self.bg_primary)
        
        # Variables
        self.current_time = tk.StringVar()
        self.current_date = tk.StringVar()
        self.last_employee_name = tk.StringVar(value="Sistema Iniciado")
        self.last_employee_action = tk.StringVar(value="Listo para registrar")
        self.last_employee_time = tk.StringVar(value="")
        self.last_employee_role = tk.StringVar(value="")
        
        # Variable para foto actual
        self.current_photo = None
        
        self.setup_ui()
        self.start_time_update()
        self.start_sync_service()
        
        # Combinación de teclas para acceder a administración
        self.root.bind('<Control-Alt-a>', self.open_admin)
        
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        # Barra de menú simplificada: Sesión + Sitio
        menubar = tk.Menu(self.root)
        sesion_menu = tk.Menu(menubar, tearoff=0)
        sesion_menu.add_command(label="Iniciar sesión (Admin)\tCtrl+Alt+A", command=self.open_admin)
        sesion_menu.add_command(label="Cerrar sesión (cerrar ventanas Admin)", command=self.close_admin_sessions)
        sesion_menu.add_separator()
        sesion_menu.add_command(label="Salir del sistema", command=self.root.quit)
        menubar.add_cascade(label="Sesión", menu=sesion_menu)

        # Menú de sitio para seleccionar ubicación y reconfigurar lectores (con estado seleccionado)
        self.sitio_var = tk.StringVar(value=os.getenv('UBICACION_PRINCIPAL', 'Tepanecos'))
        sitio_menu = tk.Menu(menubar, tearoff=0)
        for sitio in ("Tepanecos", "Lerdo", "DESTINO"):
            sitio_menu.add_radiobutton(label=sitio, variable=self.sitio_var, value=sitio,
                                       command=lambda s=sitio: self.change_site(s))
        menubar.add_cascade(label="Sitio", menu=sitio_menu)

        # Menú Lector: prueba rápida
        lector_menu = tk.Menu(menubar, tearoff=0)
        lector_menu.add_command(label="Probar lector actual…", command=self.test_active_reader)
        menubar.add_cascade(label="Lector", menu=lector_menu)

        # Menú Ayuda
        ayuda_menu = tk.Menu(menubar, tearoff=0)
        ayuda_menu.add_command(label="Acerca de…", command=self.show_about)
        menubar.add_cascade(label="Ayuda", menu=ayuda_menu)

        self.root.config(menu=menubar)

        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.bg_primary)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Título del sistema
        title_frame = tk.Frame(main_frame, bg=self.bg_primary)
        title_frame.pack(fill='x', pady=(0, 20))
        tk.Label(title_frame, text="SISTEMA DE CONTROL DE ASISTENCIA",
                 font=('Segoe UI', 28, 'bold'), fg=self.text_primary, bg=self.bg_primary).pack()

        # Frame superior - Fecha y hora
        datetime_frame = tk.Frame(main_frame, bg=self.bg_card, relief='flat', bd=0, highlightthickness=1, highlightbackground='#2A3456')
        datetime_frame.pack(fill='x', pady=(0, 20))

        # Fecha (más grande)
        tk.Label(datetime_frame, textvariable=self.current_date,
                 font=('Segoe UI', 26, 'bold'), fg=self.text_primary, bg=self.bg_card).pack(pady=(10, 4))

        # Hora (más grande para vista clara)
        tk.Label(datetime_frame, textvariable=self.current_time,
                 font=('Segoe UI', 56, 'bold'), fg=self.accent_alt, bg=self.bg_card).pack(pady=(0, 12))

        # Frame central - División en dos columnas
        center_frame = tk.Frame(main_frame, bg=self.bg_primary)
        center_frame.pack(fill='both', expand=True)

        # Columna izquierda - Último registro
        left_frame = tk.LabelFrame(center_frame, text="ÚLTIMO REGISTRO",
                                   font=('Segoe UI', 14, 'bold'), fg=self.text_primary, bg=self.bg_card,
                                   labelanchor='n')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Foto del empleado
        self.photo_frame = tk.Frame(
            left_frame,
            bg='white', relief='flat', bd=0,
            highlightbackground='#2A3456', highlightthickness=1,
            width=560, height=560
        )
        self.photo_frame.pack(pady=10)
        self.photo_frame.pack_propagate(False)
        # Área fija 560x560 para mostrar foto completa sin deformar
        self.photo_label = tk.Label(
            self.photo_frame,
            text="ESPERANDO\nREGISTRO",
            font=('Segoe UI', 18, 'bold'), fg='#666666', bg='white'
        )
        self.photo_label.place(relx=0.5, rely=0.5, anchor='center')

        # Información del empleado
        info_frame = tk.Frame(left_frame, bg=self.bg_card)
        info_frame.pack(fill='x', padx=20, pady=20)
        tk.Label(info_frame, textvariable=self.last_employee_name,
                 font=('Segoe UI', 20, 'bold'), fg=self.text_primary, bg=self.bg_card).pack()
        tk.Label(info_frame, textvariable=self.last_employee_action,
                 font=('Segoe UI', 14), fg=self.accent_alt, bg=self.bg_card).pack(pady=(5, 0))
        # Rol visible debajo del nombre/acción
        tk.Label(info_frame, textvariable=self.last_employee_role,
                 font=('Segoe UI', 13, 'bold'), fg=self.text_muted, bg=self.bg_card).pack(pady=(4, 0))
        tk.Label(info_frame, textvariable=self.last_employee_time,
                 font=('Segoe UI', 16, 'bold'), fg=self.text_muted, bg=self.bg_card).pack(pady=(6, 0))

        # Columna derecha - Lista de registros del día
        right_frame = tk.LabelFrame(center_frame, text="REGISTROS DEL DÍA",
                                    font=('Segoe UI', 14, 'bold'), fg=self.text_primary, bg=self.bg_card,
                                    labelanchor='n')
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        # Treeview para registros (agrega 'Sitio')
        columns = ('Hora', 'Empleado', 'Acción', 'Estado', 'Sitio')
        self.records_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=20)

        # Configurar columnas
        self.records_tree.heading('Hora', text='HORA')
        self.records_tree.heading('Empleado', text='EMPLEADO')
        self.records_tree.heading('Acción', text='ACCIÓN')
        self.records_tree.heading('Estado', text='ESTADO')
        self.records_tree.heading('Sitio', text='SITIO')

        self.records_tree.column('Hora', width=100, anchor='center')
        self.records_tree.column('Empleado', width=220, anchor='center')
        self.records_tree.column('Acción', width=110, anchor='center')
        self.records_tree.column('Estado', width=110, anchor='center')
        self.records_tree.column('Sitio', width=140, anchor='center')

        # Scrollbar para la lista
        scrollbar = ttk.Scrollbar(right_frame, orient='vertical', command=self.records_tree.yview)
        self.records_tree.configure(yscrollcommand=scrollbar.set)

        self.records_tree.pack(side='left', fill='both', expand=True, padx=20, pady=20)
        scrollbar.pack(side='right', fill='y', pady=20)

        # Configurar estilos para colores
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Treeview",
                        font=('Segoe UI', 10),
                        background='white',
                        fieldbackground='white',
                        rowheight=26)
        style.configure("Treeview.Heading",
                        font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#2A9D8F')], foreground=[('selected', 'white')])

        # Cargar registros iniciales
        self.update_records_list()

        # Frame inferior - Información del sistema
        footer_frame = tk.Frame(main_frame, bg=self.bg_card, relief='flat', bd=0, highlightbackground='#2A3456', highlightthickness=1)
        footer_frame.pack(fill='x', pady=(20, 0))
        # Estado en el pie con sitio actual
        sitio_actual = os.getenv('UBICACION_PRINCIPAL', 'Tepanecos')
        # Intentar mostrar el lector activo desde la fachada
        try:
            from acr122u_driver import acr122u_reader
            lector = acr122u_reader.get_active_reader_name() if hasattr(acr122u_reader, 'get_active_reader_name') else None
        except Exception:
            lector = None
        lector_txt = lector if lector else '—'
        self.status_text = tk.StringVar(value=f"Sistema listo • v{self.version} • Sitio: {sitio_actual} • Lector: {lector_txt} • Ctrl+Alt+A Administración")
        tk.Label(footer_frame, textvariable=self.status_text,
                 font=('Segoe UI', 10), fg=self.text_primary, bg=self.bg_card).pack(pady=6)
    
    def start_time_update(self):
        """Actualizar fecha/hora usando after en el hilo principal (sin threads)."""
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        def tick():
            now = datetime.datetime.now()
            dia_semana = dias_semana[now.weekday()]
            mes = meses[now.month - 1]
            fecha_completa = f"{dia_semana}, {now.day} de {mes} de {now.year}"
            hora_actual = now.strftime("%H:%M:%S")
            self.current_date.set(fecha_completa)
            self.current_time.set(hora_actual)
            self.root.after(1000, tick)

        tick()
    
    def start_sync_service(self):
        """Iniciar servicio de sincronización"""
        try:
            sync_interval = int(os.getenv('SYNC_INTERVAL_SECONDS', '10'))
        except Exception:
            sync_interval = 10
        def sync_service():
            while True:
                try:
                    # Intentar sincronizar datos cada 30 segundos
                    if db_manager.is_online():
                        db_manager.sync_empleados_to_local()
                        db_manager.sync_registros_to_cloud()

                except Exception as e:
                    print(f"Error en sincronización: {e}")
                
                time.sleep(max(2, sync_interval))
        
        sync_thread = threading.Thread(target=sync_service, daemon=True)
        sync_thread.start()

        # Refresco periódico de la lista de registros sin usar hilos secundarios
        def refresh_loop():
            try:
                self.update_records_list()
            except Exception as e:
                print(f"Error actualizando lista: {e}")
            finally:
                self.root.after(max(2000, sync_interval * 1000), refresh_loop)
        self.root.after(max(2000, sync_interval * 1000), refresh_loop)
    
    def update_records_list(self):
        """Actualizar lista de registros del día"""
        try:
            # Limpiar lista actual
            for item in self.records_tree.get_children():
                self.records_tree.delete(item)
            
            # Obtener registros del día
            records = db_manager.obtener_registros_dia()
            # Mapas auxiliares
            # 1) Primer registro del día (cualquier movimiento) y última SALIDA por empleado
            first_time = {}
            last_exit = {}
            for rec in sorted(records, key=lambda r: r[3]):
                emp_id, nombre, foto_path, hora_registro, tipo_mov, estado, ubicacion = rec
                if emp_id not in first_time:
                    first_time[emp_id] = hora_registro
                if tipo_mov == 'SALIDA':
                    last_exit[emp_id] = hora_registro
            # 2) Justificaciones del día
            from datetime import date
            hoy_iso = date.today().isoformat()
            just_map = db_manager.obtener_justificaciones_por_fecha(hoy_iso)
            # 3) Empleados activos para detectar faltas
            empleados_activos = {emp_id: nombre for emp_id, nombre in db_manager.obtener_empleados_activos()}
            empleados_con_registro = set([r[0] for r in records])
            
            # Para colorear solo primer registro (ENTRADA) por empleado
            primeras_entradas = set()
            
            for record in records:
                empleado_id, nombre, foto_path, hora_registro, tipo_movimiento, estado, ubicacion = record
                
                # Formatear hora
                if isinstance(hora_registro, str):
                    hora_dt = datetime.datetime.fromisoformat(hora_registro)
                else:
                    hora_dt = hora_registro
                
                hora_str = hora_dt.strftime("%H:%M:%S")
                
                # Determinar color con reglas:
                # - Sólo el primer registro del día (del empleado) y la última SALIDA del día se colorean por estado.
                # - Todos los intermedios quedan en blanco/normal y Estado vacío.
                # - Justificaciones: RETARDO justificado -> verde y marcar con asterisco en Estado (solo si aplica en primer/último mostrado).
                tag = 'normal'
                est_up = (estado or '').upper()
                estado_mostrar = ''
                retardo_justificado = (empleado_id, 'RETARDO') in just_map and est_up == 'RETARDO'
                # ¿Es el primer registro del día de este empleado?
                is_first = (first_time.get(empleado_id) == hora_registro)
                if is_first:
                    estado_mostrar = estado  # mostrar estado sólo en el primero
                    if est_up in ('A_TIEMPO', 'TEMPRANO'):
                        tag = 'verde'
                    elif est_up == 'RETARDO':
                        tag = 'verde' if retardo_justificado else 'amarillo'
                        if retardo_justificado:
                            estado_mostrar = 'RETARDO*'
                    elif est_up in ('FALTA',):
                        tag = 'normal' if (empleado_id, 'FALTA') in just_map else 'rojo'
                else:
                    # ¿Es la última salida del día?
                    if tipo_movimiento == 'SALIDA' and last_exit.get(empleado_id) == hora_registro:
                        estado_mostrar = estado  # mostrar estado en la última salida
                        if est_up in ('A_TIEMPO', 'TEMPRANO'):
                            tag = 'verde'
                        elif est_up == 'RETARDO':
                            if retardo_justificado:
                                tag = 'verde'
                                estado_mostrar = 'RETARDO*'
                            else:
                                tag = 'amarillo'
                        elif est_up in ('FALTA',):
                            tag = 'rojo' if (empleado_id, 'FALTA') not in just_map else 'normal'
                    else:
                        # Intermedios: normal y estado vacío
                        tag = 'normal'
                        estado_mostrar = ''
                
                # Insertar registro
                sitio_str = (ubicacion or '').upper()
                item = self.records_tree.insert('', 'end', values=(
                    hora_str, nombre, tipo_movimiento, estado_mostrar, sitio_str
                ), tags=(tag,))

            # Si ya es mediodía o después, para empleados sin registros hoy y sin justificación FALTA, mostrar fila de falta
            ahora = datetime.datetime.now().time()
            try:
                es_despues_mediodia = ahora >= datetime.time(12, 0, 0)
            except Exception:
                es_despues_mediodia = False
            if es_despues_mediodia:
                for emp_id, nombre_emp in empleados_activos.items():
                    if emp_id not in empleados_con_registro:
                        # Si existe justificación de FALTA, no marcar en rojo
                        if (emp_id, 'FALTA') in just_map:
                            continue
                        self.records_tree.insert('', 'end', values=(
                            '--:--:--', nombre_emp, '—', 'FALTA', (os.getenv('UBICACION_PRINCIPAL', '')).upper()
                        ), tags=('rojo',))
            
            # Configurar colores
            self.records_tree.tag_configure('verde', background='#1B5E20', foreground='#A5D6A7')
            self.records_tree.tag_configure('amarillo', background='#7C4D00', foreground='#FFE082')
            self.records_tree.tag_configure('rojo', background='#B71C1C', foreground='#EF9A9A')
            self.records_tree.tag_configure('normal', background='white', foreground='#111111')
            
        except Exception as e:
            print(f"Error actualizando registros: {e}")
    
    def show_employee_registration(self, empleado_data, tipo_movimiento, estado):
        """Mostrar registro de empleado en pantalla"""
        try:
            nombre, foto_path = empleado_data[1], empleado_data[4]
            # rol puede venir en índice 2 (cargo) o 3 (rol)
            rol = (empleado_data[3] or empleado_data[2]) if len(empleado_data) > 3 else ''
            
            # Actualizar información del empleado
            self.last_employee_name.set(nombre.upper())
            self.last_employee_role.set(str(rol).upper() if rol else "")
            
            accion_text = "ENTRADA" if tipo_movimiento == "ENTRADA" else "SALIDA"
            if estado == 'A_TIEMPO':
                accion_text += " - A TIEMPO"
                color = self.ok
            elif estado == 'RETARDO':
                accion_text += " - RETARDO"
                color = self.warn
            elif estado == 'TEMPRANO':
                accion_text += " - TEMPRANO"
                color = self.ok
            else:
                color = self.accent
            
            self.last_employee_action.set(accion_text)
            self.last_employee_time.set(datetime.datetime.now().strftime("%H:%M:%S"))
            
            # Cargar foto del empleado: usar contain para NO recortar y mostrar completa
            if foto_path and os.path.exists(foto_path):
                try:
                    img = Image.open(foto_path)
                    # Escalar para que quepa completa dentro de 560x560, agregando bandas si hace falta
                    img = ImageOps.contain(img, (560, 560), Image.Resampling.LANCZOS)
                    # Añadir un lienzo blanco 560x560 para centrar si quedó con bandas
                    canvas = Image.new('RGB', (560, 560), 'white')
                    x = (560 - img.width) // 2
                    y = (560 - img.height) // 2
                    canvas.paste(img, (x, y))
                    img = canvas
                    photo = ImageTk.PhotoImage(img)
                    # Fondo de la tarjeta se pinta acorde al estado pero el marco de foto se mantiene blanco para contraste
                    self.photo_frame.configure(bg='white')
                    self.photo_label.configure(image=photo, text="", bg='white')
                    self.photo_label.image = photo
                except Exception as e:
                    print(f"Error cargando foto: {e}")
                    self.photo_label.configure(image="", text=nombre.upper(), bg=color,
                                             font=('Segoe UI', 14, 'bold'), fg='white')
            else:
                self.photo_label.configure(image="", text=nombre.upper(), bg=color,
                                         font=('Segoe UI', 14, 'bold'), fg='white')
            
            # Mostrar solo 2s el último registro y luego reset visual
            def reset_last():
                # Regresar a estado neutro
                self.photo_label.configure(image="", text="ESPERANDO\nREGISTRO", bg='white',
                                           font=('Segoe UI', 18, 'bold'), fg='#666666')
                self.last_employee_name.set("Sistema Iniciado")
                self.last_employee_action.set("Listo para registrar")
                self.last_employee_time.set("")
                self.last_employee_role.set("")
                self.update_records_list()
            self.root.after(2000, reset_last)
            
        except Exception as e:
            print(f"Error mostrando registro: {e}")
    
    def open_admin(self, event=None):
        """Abrir interfaz de administración"""
        try:
            admin_window = AdminInterface(self.root)
            self.status_text.set("Administración abierta")
        except Exception as e:
            print(f"Error abriendo administración: {e}")

    def close_admin_sessions(self):
        """Cerrar todas las ventanas de administración abiertas (si existen)."""
        try:
            # Buscar toplevels hijos y destruir los que tengan título de administración
            for w in self.root.winfo_children():
                try:
                    if isinstance(w, tk.Toplevel) or hasattr(w, 'title'):
                        title = ''
                        try:
                            title = w.title()
                        except Exception:
                            pass
                        if title and ('Administración' in title or 'ADMINISTRACIÓN' in title):
                            w.destroy()
                except Exception:
                    continue
            self.status_text.set("Sesión de administración cerrada")
        except Exception as e:
            print(f"Error cerrando sesiones: {e}")

    def change_site(self, new_site: str):
        """Cambiar sitio activo y re-aplicar preferencia de lector."""
        try:
            import os
            from nfc_handler import nfc_reader
            os.environ['UBICACION_PRINCIPAL'] = new_site
            # Actualizar estado en footer
            try:
                from acr122u_driver import acr122u_reader
                lector = acr122u_reader.get_active_reader_name() if hasattr(acr122u_reader, 'get_active_reader_name') else None
            except Exception:
                lector = None
            lector_txt = lector if lector else '—'
            self.status_text.set(f"Sistema listo • v{self.version} • Sitio: {new_site} • Lector: {lector_txt} • Ctrl+Alt+A Administración")
            # Re-aplicar preferencias y refrescar lectores
            if hasattr(nfc_reader, 'ubicacion_actual'):
                nfc_reader.ubicacion_actual = new_site
            # Establecer el sitio visual para la pantalla (foto grande)
            if hasattr(nfc_reader, 'set_visual_site'):
                try:
                    nfc_reader.set_visual_site(new_site)
                except Exception:
                    pass
            if hasattr(nfc_reader, '_apply_site_reader_preferences'):
                nfc_reader._apply_site_reader_preferences()
            try:
                from acr122u_driver import acr122u_reader as facade
                if hasattr(facade, 'reconfigure_with_env'):
                    facade.reconfigure_with_env()
                elif hasattr(facade, 'refresh_readers'):
                    facade.refresh_readers()
            except Exception:
                pass
        except Exception as e:
            print(f"Error cambiando sitio: {e}")

    def refresh_footer_reader(self):
        """Actualizar el nombre del lector activo en el pie."""
        try:
            sitio = os.getenv('UBICACION_PRINCIPAL', 'Tepanecos')
            # Si está en modo multi, listar por sitio; si no, mostrar lector único
            try:
                from nfc_handler import nfc_reader
                if hasattr(nfc_reader, 'get_active_reader_names'):
                    m = nfc_reader.get_active_reader_names() or {}
                    if m:
                        parejas = [f"{k}:{(v if v else '—')}" for k, v in m.items()]
                        lectores = " | ".join(parejas)
                        self.status_text.set(f"Sistema listo • v{self.version} • Sitio: {sitio} • Lectores: {lectores} • Ctrl+Alt+A Administración")
                        return
            except Exception:
                pass
            # Fallback lector único
            from acr122u_driver import acr122u_reader
            lector = acr122u_reader.get_active_reader_name() if hasattr(acr122u_reader, 'get_active_reader_name') else None
            lector_txt = lector if lector else '—'
            self.status_text.set(f"Sistema listo • v{self.version} • Sitio: {sitio} • Lector: {lector_txt} • Ctrl+Alt+A Administración")
        except Exception:
            pass

    def test_active_reader(self):
        """Prueba rápida del lector activo: intenta leer una sola tarjeta con timeout y muestra el resultado."""
        try:
            from acr122u_driver import acr122u_reader
            # Ventana no modal con progreso
            win = tk.Toplevel(self.root)
            win.title("Probar lector actual")
            win.configure(bg=self.bg_card)
            tk.Label(win, text="Acerca una tarjeta al lector…", font=('Segoe UI', 12), bg=self.bg_card, fg=self.text_primary).pack(padx=16, pady=(12, 6))
            status = tk.StringVar(value="Esperando… (15s)")
            tk.Label(win, textvariable=status, font=('Segoe UI', 10), bg=self.bg_card, fg=self.text_muted).pack(padx=16, pady=(0, 12))

            def do_read():
                uid, msg = acr122u_reader.read_single_card(timeout=15)
                if uid:
                    status.set(f"✅ UID: {uid}")
                else:
                    status.set(f"❌ {msg}")
                # Actualizar footer con posible lector activo
                self.refresh_footer_reader()

            threading.Thread(target=do_read, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo probar el lector: {e}")
    
    def run(self):
        """Ejecutar aplicación"""
        self.root.mainloop()

    def show_about(self):
        try:
            info = [
                f"Sistema de Asistencia NFC v{self.version}",
                "Ubicaciones: Tepanecos, Lerdo, DESTINO",
                "Primer registro/Última salida con colores y justificaciones",
                "Reportes PDF/Excel con colores",
                "Ruta de descargas configurable (persistente)",
            ]
            messagebox.showinfo("Acerca de", "\n".join(info))
        except Exception:
            pass

if __name__ == "__main__":
    import os
    app = MainPublicScreen()
    app.run()