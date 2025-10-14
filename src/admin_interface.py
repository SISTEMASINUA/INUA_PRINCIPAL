import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from PIL import Image, ImageTk, ImageOps
import os
import shutil
import json
from database_manager import db_manager
from pathlib import Path
from report_generator import ReportGenerator
import re

# Mejora de nitidez en pantallas Windows de alta DPI
if os.name == 'nt':
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

class AdminInterface:
    def __init__(self, parent=None):
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("Sistema de Asistencia NFC - Administración")
        self.window.geometry("1200x820")
        # Icono de la aplicación (si existe)
        try:
            from pathlib import Path
            ico = Path(__file__).resolve().parent.parent / 'assets' / 'app_icon.ico'
            if ico.exists():
                self.window.iconbitmap(default=str(ico))
        except Exception:
            pass
        # Tema visual moderno
        self.bg_primary = '#0B132B'
        self.bg_card = '#1C2541'
        self.accent = '#5BC0BE'
        self.accent_alt = '#FFD166'
        self.text_primary = '#E0E0E0'
        self.text_muted = '#A0AEC0'
        self.window.configure(bg=self.bg_primary)
        # Ruta global para imágenes
        self.images_base_dir = Path(r"C:\Users\100214031\Documents\SISTEMAS\setups\nfc\images")
        try:
            self.images_base_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        # Verificar autenticación de admin (solo al abrir administración)
        if not self.authenticate_admin():
            self.window.destroy()
            return
            
        self.setup_ui()
        self.load_employees()

    # ==== Diálogo ancho reutilizable para entrada de texto ====
    def _ask_wide_string(self, title: str, label: str, initial: str = "", center_text: bool = False) -> str | None:
        """Muestra un diálogo con campo de texto ancho y opcionalmente centrado.
        Devuelve el texto o None si se canceló.
        """
        dlg = tk.Toplevel(self.window)
        dlg.title(title)
        # Dimensiones cómodas y centrado sobre la ventana principal
        try:
            self.window.update_idletasks()
            w, h = 560, 160
            x = self.window.winfo_rootx() + (self.window.winfo_width() // 2) - (w // 2)
            y = self.window.winfo_rooty() + (self.window.winfo_height() // 2) - (h // 2)
            dlg.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            dlg.geometry("560x160")
        dlg.transient(self.window)
        dlg.grab_set()
        dlg.resizable(True, False)

        body = tk.Frame(dlg, padx=14, pady=12)
        body.pack(fill='both', expand=True)
        tk.Label(body, text=label, font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 6))
        var = tk.StringVar(value=initial)
        entry = tk.Entry(body, textvariable=var, font=('Segoe UI', 12))
        if center_text:
            entry.configure(justify='center')
        entry.pack(fill='x')

        result: list[str | None] = [None]

        def ok():
            result[0] = var.get().strip()
            dlg.destroy()

        def cancel():
            result[0] = None
            dlg.destroy()

        btns = tk.Frame(body)
        btns.pack(anchor='e', pady=12)
        tk.Button(btns, text="OK", width=12, command=ok).pack(side='right', padx=(6, 0))
        tk.Button(btns, text="Cancel", width=12, command=cancel).pack(side='right')

        entry.focus()
        dlg.bind('<Return>', lambda e: ok())
        dlg.bind('<Escape>', lambda e: cancel())
        dlg.wait_window()
        return result[0]

    # Botones modernos con hover y animación ligera
    def make_button(self, parent, text, command, bg, fg='white', hover_bg=None, active_bg=None, font=('Segoe UI', 10, 'bold')):
        btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, font=font, bd=0, relief='flat', padx=12, pady=8, activebackground=active_bg or bg)
        base_bg = bg
        hover = hover_bg or base_bg
        def on_enter(e):
            try:
                btn.configure(bg=hover)
            except Exception:
                pass
        def on_leave(e):
            try:
                btn.configure(bg=base_bg)
            except Exception:
                pass
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        return btn
        
    def authenticate_admin(self):
        """Ventana de autenticación (usuario + contraseña) contra usuarios_local con rol ADMIN."""
        auth_window = tk.Toplevel(self.window)
        auth_window.title("Iniciar sesión - Administración")
        # Tamaño y comportamiento
        auth_window.geometry("560x380")
        auth_window.minsize(560, 380)
        auth_window.resizable(False, False)
        auth_window.configure(bg='#0B132B')
        auth_window.transient(self.window)
        auth_window.grab_set()

        # Centrar ventana
        try:
            auth_window.update_idletasks()
            x = self.window.winfo_rootx() + (self.window.winfo_width() // 2) - 280
            y = self.window.winfo_rooty() + (self.window.winfo_height() // 2) - 190
            auth_window.geometry(f"+{x}+{y}")
        except Exception:
            pass

        title = tk.Label(auth_window, text="Acceso a Administración", font=('Segoe UI', 20, 'bold'),
                         bg='#0B132B', fg='white')
        title.pack(pady=(26, 10))

        frame = tk.Frame(auth_window, bg='#1C2541', padx=28, pady=28, bd=0, relief='flat')
        frame.pack(expand=True, fill='both', padx=26, pady=16)

        # Usuario
        tk.Label(frame, text="Usuario", font=('Segoe UI', 12, 'bold'), bg='#1C2541', fg='#E0E0E0').grid(row=0, column=0, sticky='w', pady=(0, 6))
        user_var = tk.StringVar()
        user_entry = tk.Entry(frame, textvariable=user_var, font=('Segoe UI', 13))
        user_entry.grid(row=1, column=0, sticky='ew', pady=(0, 12))
        user_entry.insert(0, os.getenv('ADMIN_USER', 'admin'))

        # Contraseña
        tk.Label(frame, text="Contraseña", font=('Segoe UI', 12, 'bold'), bg='#1C2541', fg='#E0E0E0').grid(row=2, column=0, sticky='w', pady=(0, 6))
        password_var = tk.StringVar()
        password_entry = tk.Entry(frame, textvariable=password_var, show='*', font=('Segoe UI', 13))
        password_entry.grid(row=3, column=0, sticky='ew')

        frame.columnconfigure(0, weight=1)

        authenticated = [False]

        def verify_credentials():
            username = user_var.get().strip()
            password = password_var.get().strip()
            from database_manager import db_manager
            if db_manager.verificar_usuario(username, password, required_role='ADMIN'):
                authenticated[0] = True
                auth_window.destroy()
            else:
                messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos o usuario inactivo")
                password_entry.delete(0, tk.END)
                password_entry.focus()

        def on_enter(event=None):
            verify_credentials()

        password_entry.bind('<Return>', on_enter)

        # Botones
        btns = tk.Frame(auth_window, bg='#0B132B')
        btns.pack(pady=(4, 24))
        ingresar_btn = tk.Button(btns, text="Ingresar", command=verify_credentials,
                  bg='#5BC0BE', activebackground='#4AAFAE', fg='black', font=('Segoe UI', 12, 'bold'), padx=30, pady=10, bd=0)
        ingresar_btn.pack(side=tk.LEFT, padx=12)
        tk.Button(btns, text="Cancelar", command=auth_window.destroy,
                  bg='#E63946', activebackground='#D62839', fg='white', font=('Segoe UI', 12, 'bold'), padx=30, pady=10, bd=0).pack(side=tk.LEFT, padx=12)

        # Accesibilidad: Enter = Ingresar, Esc = Cancelar
        auth_window.bind('<Escape>', lambda e: auth_window.destroy())
        auth_window.bind('<Return>', on_enter)

        user_entry.focus()
        auth_window.wait_window()
        return authenticated[0]
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        # Menú superior
        menubar = tk.Menu(self.window)
        # Menú Configuración
        config_menu = tk.Menu(menubar, tearoff=0)
        config_menu.add_command(label="Configurar Lectores…", command=self.open_reader_config_dialog)
        config_menu.add_command(label="Usuarios…", command=self.open_users_dialog)
        config_menu.add_command(label="Ruta de Descargas…", command=self.choose_downloads_folder)
        config_menu.add_command(label="Abrir carpeta de Descargas", command=self.open_downloads_folder)
        menubar.add_cascade(label="Configuración", menu=config_menu)
        # Menú Reportes Generales
        reports_menu = tk.Menu(menubar, tearoff=0)
        reports_menu.add_command(label="Reporte Diario General (PDF+Excel)", command=self.generate_general_daily)
        reports_menu.add_command(label="Reporte Mensual General (PDF+Excel)", command=self.generate_general_monthly)
        menubar.add_cascade(label="Reportes", menu=reports_menu)
        self.window.config(menu=menubar)

        # Título principal
        title_frame = tk.Frame(self.window, bg=self.bg_card, height=60)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="ADMINISTRACIÓN DE EMPLEADOS",
            font=('Segoe UI', 18, 'bold'),
            fg=self.text_primary,
            bg=self.bg_card,
        ).pack(expand=True)

        # Frame principal
        main_frame = tk.Frame(self.window, bg=self.bg_primary)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Frame izquierdo - Lista de empleados
        left_frame = tk.LabelFrame(
            main_frame,
            text="Lista de Empleados",
            font=('Segoe UI', 12, 'bold'),
            fg=self.text_primary,
            bg=self.bg_card,
        )
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Barra de búsqueda
        search_bar = tk.Frame(left_frame, bg=self.bg_card)
        search_bar.pack(fill='x', padx=4, pady=(4, 2))
        tk.Label(search_bar, text="Buscar:", fg=self.text_primary, bg=self.bg_card, font=('Segoe UI', 9, 'bold')).pack(side='left')
        self.employee_search_var = tk.StringVar()
        search_entry = tk.Entry(search_bar, textvariable=self.employee_search_var, width=28)
        search_entry.pack(side='left', padx=6, fill='x', expand=True)
        def _on_search_key(event=None):
            self.filter_employee_list()
        search_entry.bind('<KeyRelease>', _on_search_key)
        tk.Button(search_bar, text='✕', command=lambda: (self.employee_search_var.set(''), self.filter_employee_list()), bg='#444', fg='white', bd=0, padx=6).pack(side='left', padx=(4,0))

        # Contenedor tree
        tree_container = tk.Frame(left_frame, bg=self.bg_card)
        tree_container.pack(fill='both', expand=True)

        # Treeview para empleados (unificar Cargo/Rol en "Rol")
        columns = ('ID', 'Nombre', 'Rol', 'NFC UID', 'Entrada', 'Salida')
        self.employee_tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=20)
        # Definir anchos fijos y desactivar stretch
        fixed_widths = {
            'ID': 60,
            'Nombre': 420,
            'Rol': 220,
            'NFC UID': 120,
            'Entrada': 90,
            'Salida': 90,
        }
        for col in columns:
            self.employee_tree.heading(col, text=col)
            w = fixed_widths.get(col, 120)
            self.employee_tree.column(col, width=w, minwidth=w, stretch=False, anchor='w')

        scrollbar = ttk.Scrollbar(tree_container, orient='vertical', command=self.employee_tree.yview)
        self.employee_tree.configure(yscrollcommand=scrollbar.set)
        self.employee_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bloquear resize por arrastre en encabezados (separadores)
        def _block_resize(event):
            region = self.employee_tree.identify_region(event.x, event.y)
            if region == 'separator':
                return 'break'
        self.employee_tree.bind('<Button-1>', _block_resize, add='+')

        # Eventos del treeview
        self.employee_tree.bind('<<TreeviewSelect>>', self.on_employee_select)
        self.employee_tree.bind('<Double-1>', lambda e: self.view_employee_history())

        # Lista completa cacheada para filtrado
        self._all_employees_cache = []  # Cada item: (id, nombre, rol_val, nfc, entrada, salida)

        # Frame derecho - Formulario con scroll
        right_frame = tk.LabelFrame(
            main_frame,
            text="Gestión de Empleado",
            font=('Segoe UI', 12, 'bold'),
            fg=self.text_primary,
            bg=self.bg_card,
        )
        right_frame.pack(side='right', fill='both', expand=False, padx=(10, 0))

        # Canvas + Scrollbar
        canvas = tk.Canvas(right_frame, bg=self.bg_card, highlightthickness=0)
        vscroll = ttk.Scrollbar(right_frame, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side='left', fill='both', expand=True)
        vscroll.pack(side='right', fill='y')

        # Contenedor scrollable
        scroll_container = tk.Frame(canvas, bg=self.bg_card)
        canvas.create_window((0, 0), window=scroll_container, anchor='nw')

        def _on_frame_configure(event):
            # Ajustar área scroll cuando cambie tamaño del contenido
            canvas.configure(scrollregion=canvas.bbox('all'))
        scroll_container.bind('<Configure>', _on_frame_configure)

        def _on_mousewheel(event):
            # Soporte de rueda de ratón
            delta = -1 if event.delta > 0 else 1
            canvas.yview_scroll(delta, 'units')
        scroll_container.bind_all('<MouseWheel>', _on_mousewheel)

        # Variables del formulario
        self.employee_id = tk.StringVar()
        self.nombre_var = tk.StringVar()
        # Unificar: eliminar Cargo y dejar solo Rol
        self.rol_var = tk.StringVar()
        self.nfc_uid_var = tk.StringVar()
        self.hora_entrada_var = tk.StringVar(value="09:00")
        self.hora_salida_var = tk.StringVar(value="18:00")
        self.hora_entrada_alt_var = tk.StringVar(value="08:00")
        self.hora_salida_alt_var = tk.StringVar(value="16:30")
        self.rotacion_semanal_var = tk.BooleanVar(value=False)
        self.rotacion_semana_base_var = tk.IntVar(value=0)
        self.foto_path = tk.StringVar()
        # Overrides personalizado por día (L-V)
        self.salida_por_dia_enabled = tk.BooleanVar(value=False)
        self.salida_lunes_var = tk.StringVar(value="18:00")
        self.salida_martes_var = tk.StringVar(value="18:00")
        self.salida_miercoles_var = tk.StringVar(value="18:00")
        self.salida_jueves_var = tk.StringVar(value="18:00")
        self.salida_viernes_var = tk.StringVar(value="18:00")
        self.personalizado_por_dia_enabled = tk.BooleanVar(value=False)
        self.entrada_lunes_var = tk.StringVar(value="09:00")
        self.entrada_martes_var = tk.StringVar(value="09:00")
        self.entrada_miercoles_var = tk.StringVar(value="09:00")
        self.entrada_jueves_var = tk.StringVar(value="09:00")
        self.entrada_viernes_var = tk.StringVar(value="09:00")

        # Campos del formulario
        form_frame = tk.Frame(scroll_container, bg=self.bg_card)
        form_frame.pack(fill='both', expand=True, padx=16, pady=16)

        # Foto
        self.foto_frame = tk.Frame(
            form_frame,
            bg=self.bg_card,
            relief='flat',
            bd=0,
            highlightbackground='#2A3456',
            highlightthickness=1,
            width=340,
            height=340,
        )
        self.foto_frame.pack(pady=10)
        self.foto_frame.pack_propagate(False)
        self.foto_label = tk.Label(
            self.foto_frame, text="Sin foto", bg='white', font=('Segoe UI', 10)
        )
        self.foto_label.pack(expand=True, fill='both', padx=6, pady=6)

        self.make_button(form_frame, "Seleccionar Foto", self.select_photo, bg=self.accent, fg='black', hover_bg='#7FD6D4').pack(pady=5, fill='x')

        # Campos de texto
        fields = [
            ("Nombre Completo:", self.nombre_var),
            ("ROL:", self.rol_var),
            ("NFC UID:", self.nfc_uid_var),
        ]
        for label_text, var in fields:
            tk.Label(
                form_frame,
                text=label_text,
                font=('Segoe UI', 10),
                fg=self.text_primary,
                bg=self.bg_card,
            ).pack(anchor='w', pady=(10, 0))
            entry = tk.Entry(form_frame, textvariable=var, font=('Segoe UI', 10), width=30)
            entry.pack(pady=(0, 5), fill='x')

        # Bloquear NFC UID y añadir botón de escaneo primero
        # Poner el campo NFC como readonly y con fondo suave
        for child in form_frame.winfo_children():
            if isinstance(child, tk.Entry) and child.cget('textvariable') == str(self.nfc_uid_var):
                child.configure(state='readonly', readonlybackground='#E5F6F7')
                break

        # Sección colapsable: Expediente (cerrada por defecto)
        exp_header = tk.Frame(form_frame, bg=self.bg_card)
        exp_header.pack(fill='x', pady=(12, 0))
        exp_toggle_var = tk.BooleanVar(value=False)
        def toggle_exp():
            if exp_toggle_var.get():
                exp_content.pack_forget()
                exp_toggle_var.set(False)
                exp_btn.configure(text='▶ Expediente')
            else:
                # Cerrar otras secciones (acordeón)
                if hasattr(self, '_accordion_sections'):
                    for sec in self._accordion_sections:
                        if sec['content'] is not exp_content:
                            sec['content'].pack_forget()
                            sec['var'].set(False)
                            sec['btn'].configure(text=f"▶ {sec['title']}")
                exp_content.pack(fill='x', after=exp_header)
                exp_toggle_var.set(True)
                exp_btn.configure(text='▼ Expediente')
        exp_btn = self.make_button(exp_header, '▶ Expediente', toggle_exp, bg=self.bg_card, fg=self.text_primary, hover_bg='#2A3456')
        exp_btn.configure(anchor='w')
        exp_btn.pack(fill='x')
        exp_content = tk.Frame(form_frame, bg=self.bg_card)
        # Contenido de expediente
        self.make_button(exp_content, "Descargar Diario (PDF+Excel)", self.download_employee_daily, bg=self.accent_alt, fg='black', hover_bg='#FFD98C').pack(pady=6, fill='x')
        self.make_button(exp_content, "Descargar Mensual (PDF+Excel)", self.download_employee_monthly, bg=self.accent_alt, fg='black', hover_bg='#FFD98C').pack(pady=6, fill='x')
        self.make_button(exp_content, "Descargar Expediente Completo (PDF)", self.download_employee_full, bg='#06D6A0', fg='black', hover_bg='#4CE0B9').pack(pady=8, fill='x')
        # Registrar sección
        self._accordion_sections = getattr(self, '_accordion_sections', [])
        self._accordion_sections.append({'title': 'Expediente', 'btn': exp_btn, 'content': exp_content, 'var': exp_toggle_var})

        # Sección colapsable: Historial (cerrada por defecto)
        hist_header = tk.Frame(form_frame, bg=self.bg_card)
        hist_header.pack(fill='x', pady=(12, 0))
        hist_toggle_var = tk.BooleanVar(value=False)
        def toggle_hist():
            if hist_toggle_var.get():
                hist_content.pack_forget()
                hist_toggle_var.set(False)
                hist_btn.configure(text='▶ Historial')
            else:
                if hasattr(self, '_accordion_sections'):
                    for sec in self._accordion_sections:
                        if sec['content'] is not hist_content:
                            sec['content'].pack_forget()
                            sec['var'].set(False)
                            sec['btn'].configure(text=f"▶ {sec['title']}")
                hist_content.pack(fill='x', after=hist_header)
                hist_toggle_var.set(True)
                hist_btn.configure(text='▼ Historial')
        hist_btn = self.make_button(hist_header, '▶ Historial', toggle_hist, bg=self.bg_card, fg=self.text_primary, hover_bg='#2A3456')
        hist_btn.configure(anchor='w')
        hist_btn.pack(fill='x')
        hist_content = tk.Frame(form_frame, bg=self.bg_card)
        tk.Label(hist_content, text="Fecha (YYYY-MM-DD):", font=('Segoe UI', 10), bg=self.bg_card, fg=self.text_primary).pack(anchor='w')
        self.hist_fecha_var = tk.StringVar()
        tk.Entry(hist_content, textvariable=self.hist_fecha_var, font=('Segoe UI', 10)).pack(fill='x', pady=(0, 6))
        tk.Label(hist_content, text="Mes (YYYY-MM):", font=('Segoe UI', 10), bg=self.bg_card, fg=self.text_primary).pack(anchor='w')
        self.hist_mes_var = tk.StringVar()
        tk.Entry(hist_content, textvariable=self.hist_mes_var, font=('Segoe UI', 10)).pack(fill='x', pady=(0, 6))
        self.make_button(hist_content, "Ver Historial", self.view_employee_history, bg=self.accent, fg='black', hover_bg='#7FD6D4').pack(pady=4, fill='x')
        self.make_button(hist_content, "Exportar Diario", self.export_employee_daily, bg=self.accent, fg='black', hover_bg='#7FD6D4').pack(pady=2, fill='x')
        self.make_button(hist_content, "Exportar Mensual", self.export_employee_monthly, bg=self.accent, fg='black', hover_bg='#7FD6D4').pack(pady=2, fill='x')
        # Nueva: Justificar retardo/falta/temprano para la fecha
        def add_justification():
            try:
                if not self.employee_id.get():
                    messagebox.showerror("Selecciona empleado", "Primero selecciona un empleado.")
                    return
                fecha = self.hist_fecha_var.get().strip()
                if not fecha:
                    messagebox.showerror("Fecha requerida", "Ingresa la fecha (YYYY-MM-DD) a justificar.")
                    return
                tipo = simpledialog.askstring("Tipo de justificación", "RETARDO / FALTA / TEMPRANO",
                                              parent=self.window)
                if not tipo:
                    return
                tipo = tipo.strip().upper()
                if tipo not in ("RETARDO", "FALTA", "TEMPRANO"):
                    messagebox.showerror("Tipo inválido", "Usa: RETARDO, FALTA o TEMPRANO")
                    return
                motivo = simpledialog.askstring("Motivo", "Describe el motivo:", parent=self.window) or ""
                # Guardar localmente
                from database_manager import db_manager
                ok = db_manager.agregar_justificacion(int(self.employee_id.get()), fecha, tipo, motivo)
                if ok:
                    messagebox.showinfo("Guardado", "Justificación registrada")
                else:
                    messagebox.showerror("Error", "No se pudo registrar la justificación")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo justificar: {e}")
        self.make_button(hist_content, "Agregar Justificación (día)", add_justification, bg='#F4A261', fg='black', hover_bg='#F6B27B').pack(pady=4, fill='x')
        self.make_button(hist_content, "Borrar Día", self.delete_employee_daily, bg='#E76F51', fg='white', hover_bg='#F08A6B').pack(pady=2, fill='x')
        self.make_button(hist_content, "Borrar Mes", self.delete_employee_monthly, bg='#E63946', fg='white', hover_bg='#EF5350').pack(pady=2, fill='x')
        self.make_button(hist_content, "Borrar Todo", self.delete_employee_all, bg='#9C27B0', fg='white', hover_bg='#B85BC7').pack(pady=2, fill='x')
        # Registrar sección
        self._accordion_sections.append({'title': 'Historial', 'btn': hist_btn, 'content': hist_content, 'var': hist_toggle_var})

        # Sección colapsable: Tarjeta NFC (cerrada por defecto)
        nfc_header = tk.Frame(form_frame, bg=self.bg_card)
        nfc_header.pack(fill='x', pady=(12, 0))
        nfc_toggle_var = tk.BooleanVar(value=False)
        def toggle_nfc():
            if nfc_toggle_var.get():
                nfc_content.pack_forget()
                nfc_toggle_var.set(False)
                nfc_btn.configure(text='▶ Tarjeta NFC')
            else:
                if hasattr(self, '_accordion_sections'):
                    for sec in self._accordion_sections:
                        if sec['content'] is not nfc_content:
                            sec['content'].pack_forget()
                            sec['var'].set(False)
                            sec['btn'].configure(text=f"▶ {sec['title']}")
                nfc_content.pack(fill='x', after=nfc_header)
                nfc_toggle_var.set(True)
                nfc_btn.configure(text='▼ Tarjeta NFC')
        nfc_btn = self.make_button(nfc_header, '▶ Tarjeta NFC', toggle_nfc, bg=self.bg_card, fg=self.text_primary, hover_bg='#2A3456')
        nfc_btn.configure(anchor='w')
        nfc_btn.pack(fill='x')
        nfc_content = tk.Frame(form_frame, bg=self.bg_card)
        # Contenido NFC
        self.make_button(nfc_content, "Asignar/Cambiar Tarjeta (Escanear)", self.scan_and_assign_nfc, bg=self.accent_alt, fg='black', hover_bg='#FFD98C').pack(pady=6, fill='x')
        self.make_button(nfc_content, "Ingresar UID Manual", self.enter_uid_manual, bg='#FFB703', fg='black', hover_bg='#FFCC4D').pack(pady=6, fill='x')
        self.make_button(nfc_content, "Crear Empleado con Lector NFC", self.new_employee_with_nfc, bg='#06D6A0', fg='black', hover_bg='#4CE0B9').pack(pady=6, fill='x')
        # Registrar sección
        self._accordion_sections.append({'title': 'Tarjeta NFC', 'btn': nfc_btn, 'content': nfc_content, 'var': nfc_toggle_var})

        # Sección colapsable: Horario (cerrada por defecto)
        self.sin_horario_var = tk.BooleanVar(value=False)
        # Opciones de horarios
        entrada_options = [
            f"{h:02d}:{m:02d}" for h in range(6, 10) for m in (0, 30)
            if not (h == 9 and m == 30)  # hasta 09:00 inclusive
        ]
        salida_options = [
            f"{h:02d}:{m:02d}" for h in range(15, 19) for m in (0, 30)
            if not (h == 18 and m == 30)  # hasta 18:00 inclusive
        ]
        def toggle_sin_horario():
            if self.sin_horario_var.get():
                self.hora_entrada_var.set('00:00')
                self.hora_salida_var.set('00:00')
                try:
                    self.hora_entrada_combo.configure(state='disabled')
                    self.hora_salida_combo.configure(state='disabled')
                except Exception:
                    pass
            else:
                if self.hora_entrada_var.get() == '00:00':
                    self.hora_entrada_var.set('09:00')
                if self.hora_salida_var.get() == '00:00':
                    self.hora_salida_var.set('18:00')
                try:
                    self.hora_entrada_combo.configure(state='readonly')
                    self.hora_salida_combo.configure(state='readonly')
                except Exception:
                    pass

        horario_header = tk.Frame(form_frame, bg=self.bg_card)
        horario_header.pack(fill='x', pady=(12, 0))
        horario_toggle_var = tk.BooleanVar(value=False)
        def toggle_hor():
            if horario_toggle_var.get():
                horario_content.pack_forget()
                horario_toggle_var.set(False)
                horario_btn.configure(text='▶ Horario')
            else:
                if hasattr(self, '_accordion_sections'):
                    for sec in self._accordion_sections:
                        if sec['content'] is not horario_content:
                            sec['content'].pack_forget()
                            sec['var'].set(False)
                            sec['btn'].configure(text=f"▶ {sec['title']}")
                horario_content.pack(fill='x', after=horario_header)
                horario_toggle_var.set(True)
                horario_btn.configure(text='▼ Horario')
        horario_btn = self.make_button(horario_header, '▶ Horario', toggle_hor, bg=self.bg_card, fg=self.text_primary, hover_bg='#2A3456')
        horario_btn.configure(anchor='w')
        horario_btn.pack(fill='x')
        horario_content = tk.Frame(form_frame, bg=self.bg_card)
        # Contenido Horario
        tk.Label(horario_content, text="Hora Entrada:", font=('Segoe UI', 10), fg=self.text_primary, bg=self.bg_card).pack(anchor='w', pady=(8, 0))
        self.hora_entrada_combo = ttk.Combobox(horario_content, textvariable=self.hora_entrada_var, values=entrada_options, state='readonly')
        self.hora_entrada_combo.pack(pady=(0, 5), fill='x')
        tk.Label(horario_content, text="Hora Salida:", font=('Segoe UI', 10), fg=self.text_primary, bg=self.bg_card).pack(anchor='w', pady=(8, 0))
        self.hora_salida_combo = ttk.Combobox(horario_content, textvariable=self.hora_salida_var, values=salida_options, state='readonly')
        self.hora_salida_combo.pack(pady=(0, 5), fill='x')
        # Doble horario (rotación semanal)
        tk.Label(horario_content, text="Hora Entrada (Alt):", font=('Segoe UI', 10), fg=self.text_primary, bg=self.bg_card).pack(anchor='w', pady=(10, 0))
        self.hora_entrada_alt_combo = ttk.Combobox(horario_content, textvariable=self.hora_entrada_alt_var, values=entrada_options, state='readonly')
        self.hora_entrada_alt_combo.pack(pady=(0, 5), fill='x')
        tk.Label(horario_content, text="Hora Salida (Alt):", font=('Segoe UI', 10), fg=self.text_primary, bg=self.bg_card).pack(anchor='w', pady=(8, 0))
        self.hora_salida_alt_combo = ttk.Combobox(horario_content, textvariable=self.hora_salida_alt_var, values=salida_options, state='readonly')
        self.hora_salida_alt_combo.pack(pady=(0, 5), fill='x')
        ttk.Separator(horario_content, orient='horizontal').pack(fill='x', pady=6)
        tk.Checkbutton(
            horario_content,
            text="Rotación semanal (usa Alt una semana sí/otra no)",
            variable=self.rotacion_semanal_var,
            bg=self.bg_card,
            fg=self.text_primary,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
        ).pack(anchor='w')
        tk.Label(horario_content, text="Semana base (0 o 1)", font=('Segoe UI', 9), fg=self.text_muted, bg=self.bg_card).pack(anchor='w')
        tk.Spinbox(horario_content, from_=0, to=1, textvariable=self.rotacion_semana_base_var, width=6).pack(anchor='w', pady=(0, 6))
        tk.Checkbutton(
            horario_content,
            text="Sin horario (Jefe)",
            variable=self.sin_horario_var,
            command=toggle_sin_horario,
            bg=self.bg_card,
            fg=self.text_primary,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
        ).pack(anchor='w', pady=(2, 6))
        # Registrar sección
        self._accordion_sections.append({'title': 'Horario', 'btn': horario_btn, 'content': horario_content, 'var': horario_toggle_var})

        # Sección colapsable: Personalizado (L-V)
        salida_header = tk.Frame(form_frame, bg=self.bg_card)
        salida_header.pack(fill='x', pady=(12, 0))
        salida_toggle_var = tk.BooleanVar(value=False)
        def toggle_salida():
            if salida_toggle_var.get():
                salida_content.pack_forget()
                salida_toggle_var.set(False)
                salida_btn.configure(text='▶ Personalizado (L-V)')
            else:
                if hasattr(self, '_accordion_sections'):
                    for sec in self._accordion_sections:
                        if sec['content'] is not salida_content:
                            sec['content'].pack_forget()
                            sec['var'].set(False)
                            sec['btn'].configure(text=f"▶ {sec['title']}")
                salida_content.pack(fill='x', after=salida_header)
                salida_toggle_var.set(True)
                salida_btn.configure(text='▼ Personalizado (L-V)')
        salida_btn = self.make_button(salida_header, '▶ Personalizado (L-V)', toggle_salida, bg=self.bg_card, fg=self.text_primary, hover_bg='#2A3456')
        salida_btn.configure(anchor='w')
        salida_btn.pack(fill='x')
        salida_content = tk.Frame(form_frame, bg=self.bg_card)

        tk.Checkbutton(
            salida_content,
            text="Activar horarios personalizados por día (Lunes a Viernes)",
            variable=self.personalizado_por_dia_enabled,
            bg=self.bg_card, fg=self.text_primary,
            selectcolor=self.bg_card, activebackground=self.bg_card,
        ).pack(anchor='w', pady=(6, 8))

        def _row(parent, text, var_in, var_out):
            row = tk.Frame(parent, bg=self.bg_card)
            row.pack(fill='x', pady=2)
            tk.Label(row, text=text, font=('Segoe UI', 10), fg=self.text_primary, bg=self.bg_card, width=12, anchor='w').pack(side='left')
            # Entrada 06:00 a 12:00 cada 30 min
            cb_in = ttk.Combobox(row, textvariable=var_in, values=[f"{h:02d}:{m:02d}" for h in range(6, 13) for m in (0,30)], state='readonly', width=10)
            cb_in.pack(side='left', padx=(0,8))
            # Salida 15:00 a 21:00 cada 30 min (ajustado a petición)
            cb_out = ttk.Combobox(row, textvariable=var_out, values=[f"{h:02d}:{m:02d}" for h in range(15, 21) for m in (0,30)], state='readonly', width=10)
            cb_out.pack(side='left')

    # Variables de entrada por día ya definidas arriba

        _row(salida_content, 'Lunes:', self.entrada_lunes_var, self.salida_lunes_var)
        _row(salida_content, 'Martes:', self.entrada_martes_var, self.salida_martes_var)
        _row(salida_content, 'Miércoles:', self.entrada_miercoles_var, self.salida_miercoles_var)
        _row(salida_content, 'Jueves:', self.entrada_jueves_var, self.salida_jueves_var)
        _row(salida_content, 'Viernes:', self.entrada_viernes_var, self.salida_viernes_var)
        tk.Label(salida_content, text="Nota: Sábado fijo para todos (08:00–14:00), excepto Jefes (Sin horario)", font=('Segoe UI', 9), fg=self.text_muted, bg=self.bg_card).pack(anchor='w', pady=(6,0))
        # Registrar sección
        self._accordion_sections.append({'title': 'Personalizado (L-V)', 'btn': salida_btn, 'content': salida_content, 'var': salida_toggle_var})

        # Botones (al final del formulario derecho)
        btn_frame = tk.Frame(form_frame, bg=self.bg_card)
        btn_frame.pack(pady=24, fill='x')
        self.make_button(btn_frame, "Nuevo", self.new_employee, bg='#4CAF50', fg='white', hover_bg='#66BB6A').pack(pady=6, fill='x')
        self.make_button(btn_frame, "Guardar", self.save_employee, bg=self.accent, fg='black', hover_bg='#7FD6D4').pack(pady=6, fill='x')
        self.make_button(btn_frame, "Eliminar", self.delete_employee, bg='#E63946', fg='white', hover_bg='#EF5350').pack(pady=10, fill='x')
        # Botón para cerrar
        self.make_button(form_frame, "Cerrar", self.window.destroy, bg='#9E9E9E', fg='white', hover_bg='#BDBDBD').pack(pady=12, fill='x')

    

    # ==========================
    # Configuración de Lectores
    # ==========================
    def _reader_config_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / 'config' / 'readers.json'

    def _load_reader_config(self) -> dict:
        try:
            path = self._reader_config_path()
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            pass
        # Config por defecto
        return {
            "sites": {
                "Tepanecos": {"readerName": "ACR122U", "readerIndex": 1},
                "Lerdo": {"readerName": "ACR122U", "readerIndex": 2}
            }
        }

    def _save_reader_config(self, data: dict) -> bool:
        try:
            path = self._reader_config_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(data, ensure_ascii=False, indent=2)
            path.write_text(text, encoding='utf-8')
            return True
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")
            return False

    def _detect_pcsc_readers(self) -> list[str]:
        # Intentar detectar lectores reales via PC/SC; fallback a fachada simulada
        try:
            import importlib
            sc_sys = importlib.import_module('smartcard.System')
            readers_func = getattr(sc_sys, 'readers', None)
            if callable(readers_func):
                r = readers_func()
                return [str(x) for x in r]
        except Exception:
            pass
        try:
            from acr122u_driver import acr122u_reader as facade
            return facade.get_available_readers()
        except Exception:
            return []

    def open_reader_config_dialog(self):
        cfg = self._load_reader_config()
        sites_cfg: dict = cfg.get('sites') or {}
        # Si no hay sitios, inicializar con dos comunes
        if not sites_cfg:
            sites_cfg = {
                "Tepanecos": {"readerName": "ACR122U", "readerIndex": 1},
                "Lerdo": {"readerName": "ACR122U", "readerIndex": 2},
            }

        readers = self._detect_pcsc_readers()

        win = tk.Toplevel(self.window)
        win.title("Configurar Lectores por Sitio")
        win.configure(bg=self.bg_primary)
        win.transient(self.window)
        win.grab_set()
        win.geometry("720x420")

        header = tk.Frame(win, bg=self.bg_card)
        header.pack(fill='x')
        tk.Label(header, text="LECTORES POR SITIO", font=('Segoe UI', 14, 'bold'),
                 bg=self.bg_card, fg=self.text_primary).pack(padx=16, pady=12)

        body = tk.Frame(win, bg=self.bg_primary)
        body.pack(fill='both', expand=True, padx=16, pady=12)

        # Encabezados
        tk.Label(body, text="Sitio", font=('Segoe UI', 10, 'bold'), bg=self.bg_primary, fg=self.text_muted, width=16, anchor='w').grid(row=0, column=0, sticky='w')
        tk.Label(body, text="Nombre contiene", font=('Segoe UI', 10, 'bold'), bg=self.bg_primary, fg=self.text_muted, width=28, anchor='w').grid(row=0, column=1, sticky='w')
        tk.Label(body, text="Índice (1..n)", font=('Segoe UI', 10, 'bold'), bg=self.bg_primary, fg=self.text_muted, width=12, anchor='w').grid(row=0, column=2, sticky='w')
        tk.Label(body, text="Detectados", font=('Segoe UI', 10, 'bold'), bg=self.bg_primary, fg=self.text_muted, width=28, anchor='w').grid(row=0, column=3, sticky='w')

        row_vars = {}
        for r, (site, scfg) in enumerate(sites_cfg.items(), start=1):
            tk.Label(body, text=site, font=('Segoe UI', 10), bg=self.bg_primary, fg=self.text_primary).grid(row=r, column=0, sticky='w', pady=4)

            name_var = tk.StringVar(value=str(scfg.get('readerName') or ''))
            idx_var = tk.StringVar(value=str(scfg.get('readerIndex') or ''))
            name_entry = tk.Entry(body, textvariable=name_var, font=('Segoe UI', 10))
            name_entry.grid(row=r, column=1, sticky='ew', padx=(4, 8))
            idx_entry = tk.Entry(body, textvariable=idx_var, font=('Segoe UI', 10), width=8)
            idx_entry.grid(row=r, column=2, sticky='w', padx=(4, 8))

            # Combo de lectores detectados para facilitar selección por nombre
            combo = ttk.Combobox(body, values=readers, state='readonly')
            if readers:
                # Preseleccionar el primero que contenga el texto actual
                pre = next((rname for rname in readers if name_var.get().lower() in rname.lower()), '')
                if pre:
                    combo.set(pre)
            combo.grid(row=r, column=3, sticky='ew', padx=(4, 0))

            def on_combo_sel(event, _name_var=name_var, _combo=combo):
                _name_var.set(_combo.get())

            combo.bind("<<ComboboxSelected>>", on_combo_sel)

            row_vars[site] = (name_var, idx_var)

        # Ajuste de columnas
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(3, weight=1)

        # Zona de lectores detectados (lista)
        right = tk.Frame(win, bg=self.bg_card)
        right.pack(fill='x', padx=16, pady=(0, 12))
        tk.Label(right, text="Lectores detectados ahora:", font=('Segoe UI', 10, 'bold'),
                 bg=self.bg_card, fg=self.text_primary).pack(anchor='w', padx=12, pady=(8, 4))
        txt = tk.Text(right, height=4, bg='#111827', fg='#D1D5DB')
        txt.pack(fill='x', padx=12, pady=(0, 12))
        if readers:
            for rn in readers:
                txt.insert('end', f"• {rn}\n")
        else:
            txt.insert('end', "No se detectaron lectores PC/SC. Conéctelos y vuelva a abrir este diálogo.")
        txt.configure(state='disabled')

        # Botonera
        btns = tk.Frame(win, bg=self.bg_primary)
        btns.pack(fill='x', padx=16, pady=(0, 16))

        def do_save():
            # Construir objeto de sitios
            new_sites = {}
            for site, (nvar, ivar) in row_vars.items():
                name_val = (nvar.get() or '').strip()
                idx_val = (ivar.get() or '').strip()
                site_cfg = {}
                if name_val:
                    site_cfg['readerName'] = name_val
                if idx_val.isdigit():
                    site_cfg['readerIndex'] = int(idx_val)
                new_sites[site] = site_cfg

            data = {"sites": new_sites}
            if self._save_reader_config(data):
                messagebox.showinfo("Guardado", "Configuración de lectores guardada.\nSe aplicará al iniciar/reenchufar lectores o al reiniciar la app.")
                try:
                    # Intento best-effort: aplicar en caliente si el lector corre en este proceso
                    from nfc_handler import nfc_reader as global_reader
                    if hasattr(global_reader, '_apply_site_reader_preferences'):
                        global_reader._apply_site_reader_preferences()
                except Exception:
                    pass
                win.destroy()

        ttk.Button(btns, text="Guardar", command=do_save).pack(side='right')
        ttk.Button(btns, text="Cerrar", command=win.destroy).pack(side='right', padx=(0, 8))

    def open_users_dialog(self):
        """Gestión básica de usuarios (local)."""
        from database_manager import db_manager
        win = tk.Toplevel(self.window)
        win.title("Usuarios del sistema")
        win.configure(bg=self.bg_primary)
        win.geometry("640x420")
        win.transient(self.window)
        win.grab_set()

        header = tk.Frame(win, bg=self.bg_card)
        header.pack(fill='x')
        tk.Label(header, text="USUARIOS", font=('Segoe UI', 14, 'bold'), bg=self.bg_card, fg=self.text_primary).pack(padx=16, pady=10)

        cols = ('ID','Usuario','Rol','Activo','Creado')
        tree = ttk.Treeview(win, columns=cols, show='headings', height=12)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=110, anchor='center')
        vs = ttk.Scrollbar(win, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vs.set)
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        vs.pack(side='right', fill='y', pady=10)

        def refresh():
            for it in tree.get_children():
                tree.delete(it)
            for uid, uname, role, activo, created in db_manager.listar_usuarios():
                tree.insert('', 'end', values=(uid, uname, role, 'Sí' if activo else 'No', created))
        refresh()

        form = tk.Frame(win, bg=self.bg_primary)
        form.pack(fill='x', padx=10, pady=(0,10))
        un_var = tk.StringVar(); pw_var = tk.StringVar(); role_var = tk.StringVar(value='ADMIN')
        tk.Label(form, text="Usuario", bg=self.bg_primary, fg=self.text_primary).grid(row=0, column=0, sticky='w')
        tk.Entry(form, textvariable=un_var).grid(row=1, column=0, sticky='ew', padx=(0,6))
        tk.Label(form, text="Contraseña", bg=self.bg_primary, fg=self.text_primary).grid(row=0, column=1, sticky='w')
        tk.Entry(form, textvariable=pw_var, show='*').grid(row=1, column=1, sticky='ew', padx=(0,6))
        tk.Label(form, text="Rol", bg=self.bg_primary, fg=self.text_primary).grid(row=0, column=2, sticky='w')
        ttk.Combobox(form, textvariable=role_var, values=['ADMIN'], state='readonly').grid(row=1, column=2, sticky='ew')
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(2, weight=1)

        btns = tk.Frame(win, bg=self.bg_primary)
        btns.pack(fill='x', padx=10, pady=(0,10))
        def do_add():
            if not un_var.get().strip() or not pw_var.get().strip():
                messagebox.showerror("Datos requeridos", "Usuario y contraseña son obligatorios")
                return
            if db_manager.crear_usuario(un_var.get().strip(), pw_var.get().strip(), role_var.get().strip()):
                messagebox.showinfo("Listo", "Usuario creado")
                refresh()
                un_var.set(""); pw_var.set("")
            else:
                messagebox.showerror("Error", "No se pudo crear el usuario")
        def do_reset():
            sel = tree.selection()
            if not sel:
                messagebox.showerror("Selecciona", "Elige un usuario de la lista")
                return
            item = tree.item(sel[0]); uname = item['values'][1]
            new_pw = simpledialog.askstring("Nueva contraseña", f"Nueva contraseña para {uname}:", parent=win, show='*')
            if not new_pw:
                return
            if db_manager.cambiar_password(uname, new_pw):
                messagebox.showinfo("Listo", "Contraseña actualizada")
            else:
                messagebox.showerror("Error", "No se pudo actualizar la contraseña")
        def do_toggle():
            sel = tree.selection()
            if not sel:
                messagebox.showerror("Selecciona", "Elige un usuario de la lista")
                return
            item = tree.item(sel[0]); uname = item['values'][1]; activo = item['values'][3] == 'Sí'
            if db_manager.activar_usuario(uname, not activo):
                refresh()
        ttk.Button(btns, text="Crear", command=do_add).pack(side='left')
        ttk.Button(btns, text="Cambiar contraseña", command=do_reset).pack(side='left', padx=6)
        ttk.Button(btns, text="Activar/Desactivar", command=do_toggle).pack(side='left')

    def choose_downloads_folder(self):
        """Permitir seleccionar y persistir la carpeta de DESCARGAS usada por ReportGenerator."""
        try:
            # Leer actual desde configuraciones_local
            from database_manager import db_manager
            c = db_manager.sqlite_connection.cursor()
            current = None
            try:
                c.execute("SELECT valor FROM configuraciones_local WHERE clave = 'DESCARGAS_DIR'")
                row = c.fetchone()
                current = row[0] if row and row[0] else None
            except Exception:
                current = None

            initialdir = current if current and os.path.isdir(current) else os.path.join(os.path.expanduser('~'), 'Documents')
            new_dir = filedialog.askdirectory(parent=self.window, title="Selecciona carpeta de DESCARGAS", initialdir=initialdir)
            if not new_dir:
                return
            new_dir = os.path.expandvars(new_dir)
            os.makedirs(new_dir, exist_ok=True)
            # Persistir
            try:
                c.execute("INSERT OR REPLACE INTO configuraciones_local (clave, valor) VALUES ('DESCARGAS_DIR', ?)", (new_dir,))
                db_manager.sqlite_connection.commit()
                messagebox.showinfo("Guardado", f"Ruta de descargas actualizada:\n{new_dir}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar la ruta: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cambiar la carpeta: {e}")

    def open_downloads_folder(self):
        """Abrir la carpeta de descargas configurada en el explorador de archivos."""
        try:
            from database_manager import db_manager
            c = db_manager.sqlite_connection.cursor()
            c.execute("SELECT valor FROM configuraciones_local WHERE clave = 'DESCARGAS_DIR'")
            row = c.fetchone()
            base = row[0] if row and row[0] else None
            if not base:
                # Fallback por defecto
                user_docs = os.path.join(os.path.expanduser('~'), 'Documents')
                base = os.path.join(user_docs, 'SISTEMAS', 'setups', 'nfc', 'sistema_asistencia', 'DESCARGAS')
            os.makedirs(base, exist_ok=True)
            # Windows
            if os.name == 'nt':
                os.startfile(base)  # type: ignore
            else:
                import subprocess
                subprocess.Popen(['xdg-open', base])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")
    
    def load_employees(self):
        """Cargar empleados en el treeview"""
        # Limpiar treeview
        for item in self.employee_tree.get_children():
            self.employee_tree.delete(item)
        self._all_employees_cache = []
        try:
            if db_manager.is_online():
                db_manager.connect_postgresql()
                cursor = db_manager.pg_connection.cursor()
                cursor.execute("""
                    SELECT id, nombre_completo, cargo, rol, nfc_uid, hora_entrada, hora_salida
                    FROM empleados WHERE activo = TRUE
                    ORDER BY nombre_completo
                """)
                employees = cursor.fetchall()
            else:
                cursor = db_manager.sqlite_connection.cursor()
                cursor.execute("""
                    SELECT id, nombre_completo, cargo, rol, nfc_uid, hora_entrada, hora_salida
                    FROM empleados_local WHERE activo = 1
                    ORDER BY nombre_completo
                """)
                employees = cursor.fetchall()
            for emp in employees:
                rol_val = emp[3] if emp[3] else emp[2]
                row = (emp[0], emp[1], rol_val, emp[4], emp[5], emp[6])
                self._all_employees_cache.append(row)
            # Insertar filtrado inicial (sin filtro)
            for row in self._all_employees_cache:
                self.employee_tree.insert('', 'end', values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando empleados: {e}")

    def filter_employee_list(self):
        """Filtrar la lista según el texto de búsqueda (nombre, rol, NFC)."""
        query = (self.employee_search_var.get() or '').strip().lower()
        # Limpiar
        for item in self.employee_tree.get_children():
            self.employee_tree.delete(item)
        if not query:
            for row in self._all_employees_cache:
                self.employee_tree.insert('', 'end', values=row)
            return
        tokens = [t for t in re.split(r"\s+", query) if t]
        for row in self._all_employees_cache:
            texto = ' '.join(str(x).lower() for x in row if x is not None)
            if all(tok in texto for tok in tokens):
                self.employee_tree.insert('', 'end', values=row)

    def on_employee_select(self, event):
        """Evento al seleccionar un empleado"""
        selection = self.employee_tree.selection()
        if selection:
            item = self.employee_tree.item(selection[0])
            values = item['values']
            
            # values: (ID, Nombre, Rol, NFC UID, Entrada, Salida)
            self.employee_id.set(values[0])
            self.nombre_var.set(values[1])
            self.rol_var.set(values[2])
            self.nfc_uid_var.set(values[3] if values[3] else "")
            entrada_hhmm = str(values[4])[:5] if values[4] else "09:00"
            salida_hhmm = str(values[5])[:5] if values[5] else "18:00"
            self.hora_entrada_var.set(entrada_hhmm)
            self.hora_salida_var.set(salida_hhmm)

            # Sin horario (Jefe) si ambas son 00:00
            is_jefe = (entrada_hhmm == '00:00' and salida_hhmm == '00:00')
            self.sin_horario_var.set(is_jefe)
            try:
                if is_jefe:
                    self.hora_entrada_combo.configure(state='disabled')
                    self.hora_salida_combo.configure(state='disabled')
                else:
                    self.hora_entrada_combo.configure(state='readonly')
                    self.hora_salida_combo.configure(state='readonly')
            except Exception:
                pass
            
            # Cargar foto si existe
            self.load_employee_photo(values[0])
            # Cargar campos de doble horario y personalizados por día (si existen en BD)
            try:
                c = db_manager.sqlite_connection.cursor()
                c.execute("PRAGMA table_info(empleados_local)")
                cols = {r[1] for r in c.fetchall()}
                query_cols = []
                if 'hora_entrada_alt' in cols: query_cols.append('hora_entrada_alt')
                if 'hora_salida_alt' in cols: query_cols.append('hora_salida_alt')
                if 'rotacion_semanal' in cols: query_cols.append('rotacion_semanal')
                if 'rotacion_semana_base' in cols: query_cols.append('rotacion_semana_base')
                # Flag unificado
                flag_cols = []
                if 'personalizado_por_dia_enabled' in cols:
                    flag_cols.append('personalizado_por_dia_enabled')
                # Entradas por día
                entrada_cols = []
                for nm in ['entrada_lunes','entrada_martes','entrada_miercoles','entrada_jueves','entrada_viernes']:
                    if nm in cols:
                        entrada_cols.append(nm)
                # Salidas por día (legacy + valores)
                salida_cols = []
                for nm in ['salida_por_dia_enabled','salida_lunes','salida_martes','salida_miercoles','salida_jueves','salida_viernes']:
                    if nm in cols:
                        salida_cols.append(nm)
                sel_list = ", ".join(query_cols + flag_cols + entrada_cols + salida_cols) if (query_cols or flag_cols or entrada_cols or salida_cols) else None
                row = None
                if sel_list:
                    c.execute(f"SELECT {sel_list} FROM empleados_local WHERE id = ?", (int(values[0]),))
                    row = c.fetchone()
                if row:
                    idx = 0
                    if 'hora_entrada_alt' in query_cols:
                        he_alt = (row[idx] or '08:00')[:5]; idx += 1
                        self.hora_entrada_alt_var.set(he_alt)
                    if 'hora_salida_alt' in query_cols:
                        hs_alt = (row[idx] or '16:30')[:5]; idx += 1
                        self.hora_salida_alt_var.set(hs_alt)
                    if 'rotacion_semanal' in query_cols:
                        self.rotacion_semanal_var.set(bool(row[idx] or 0)); idx += 1
                    if 'rotacion_semana_base' in query_cols:
                        self.rotacion_semana_base_var.set(int(row[idx] or 0)); idx += 1
                    # Flag unificado o legacy (si no existe el unificado)
                    if 'personalizado_por_dia_enabled' in flag_cols:
                        self.personalizado_por_dia_enabled.set(bool(row[idx] or 0)); idx += 1
                    elif 'salida_por_dia_enabled' in salida_cols:
                        self.personalizado_por_dia_enabled.set(bool(row[idx] or 0)); idx += 1
                    # Entradas por día
                    for nm in ['entrada_lunes','entrada_martes','entrada_miercoles','entrada_jueves','entrada_viernes']:
                        if nm in entrada_cols:
                            val = (row[idx] or '09:00')[:5]; idx += 1
                            getattr(self, f"{nm}_var").set(val)
                    # Salidas por día
                    if 'salida_por_dia_enabled' in salida_cols:
                        # Si existe este flag legacy y no hay unificado, sincronizar estado visual
                        if 'personalizado_por_dia_enabled' not in flag_cols:
                            self.salida_por_dia_enabled.set(bool(row[idx] or 0))
                        idx += 1
                    if 'salida_lunes' in salida_cols:
                        self.salida_lunes_var.set((row[idx] or '18:00')[:5]); idx += 1
                    if 'salida_martes' in salida_cols:
                        self.salida_martes_var.set((row[idx] or '18:00')[:5]); idx += 1
                    if 'salida_miercoles' in salida_cols:
                        self.salida_miercoles_var.set((row[idx] or '18:00')[:5]); idx += 1
                    if 'salida_jueves' in salida_cols:
                        self.salida_jueves_var.set((row[idx] or '18:00')[:5]); idx += 1
                    if 'salida_viernes' in salida_cols:
                        self.salida_viernes_var.set((row[idx] or '18:00')[:5]); idx += 1
            except Exception:
                pass
    
    def load_employee_photo(self, employee_id):
        """Cargar foto del empleado"""
        try:
            # Buscar primero en la ruta global
            foto_path = str(self.images_base_dir / f"empleado_{employee_id}.jpg")
            
            if os.path.exists(foto_path):
                img = Image.open(foto_path)
                img = ImageOps.fit(img, (320, 320), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                photo = ImageTk.PhotoImage(img)
                self.foto_label.configure(image=photo, text="")
                self.foto_label.image = photo
                self.foto_path.set(foto_path)
            else:
                self.foto_label.configure(image="", text="Sin foto")
                self.foto_label.image = None
                self.foto_path.set("")
        except Exception as e:
            print(f"Error cargando foto: {e}")
    
    def select_photo(self):
        """Seleccionar foto para el empleado"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar foto",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        
        if file_path:
            try:
                img = Image.open(file_path)
                img = ImageOps.fit(img, (320, 320), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                photo = ImageTk.PhotoImage(img)
                self.foto_label.configure(image=photo, text="")
                self.foto_label.image = photo
                self.foto_path.set(file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Error cargando imagen: {e}")
    
    def new_employee(self):
        """Limpiar formulario para nuevo empleado"""
        self.employee_id.set("")
        self.nombre_var.set("")
        self.rol_var.set("")
        self.nfc_uid_var.set("")
        self.hora_entrada_var.set("09:00")
        self.hora_salida_var.set("18:00")
        self.sin_horario_var.set(False)
        try:
            self.hora_entrada_combo.configure(state='readonly')
            self.hora_salida_combo.configure(state='readonly')
        except Exception:
            pass
        self.foto_path.set("")
        self.foto_label.configure(image="", text="Sin foto")
        self.foto_label.image = None
    
    def save_employee(self):
        """Guardar empleado"""
        if not self.nombre_var.get().strip():
            messagebox.showerror("Error", "El nombre es obligatorio")
            return
        
        if not self.rol_var.get().strip():
            messagebox.showerror("Error", "El ROL es obligatorio")
            return
        
        try:
            # Validar formato de hora HH:MM (permitir 00:00 para jefes)
            def _valid_time(s: str) -> bool:
                return bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", s))

            he = self.hora_entrada_var.get().strip()
            hs = self.hora_salida_var.get().strip()
            he_alt = self.hora_entrada_alt_var.get().strip()
            hs_alt = self.hora_salida_alt_var.get().strip()
            if not (_valid_time(he) and _valid_time(hs)):
                messagebox.showerror("Hora inválida", "Usa formato HH:MM (ej. 09:00).")
                return
            if self.rotacion_semanal_var.get() and not (_valid_time(he_alt) and _valid_time(hs_alt)):
                messagebox.showerror("Hora inválida", "Completa también el horario alterno HH:MM.")
                return

            hora_entrada = he + ":00"
            hora_salida = hs + ":00"
            hora_entrada_alt = (he_alt + ":00") if self.rotacion_semanal_var.get() else None
            hora_salida_alt = (hs_alt + ":00") if self.rotacion_semanal_var.get() else None
            rotacion = 1 if self.rotacion_semanal_var.get() else 0
            semana_base = int(self.rotacion_semana_base_var.get() or 0)
            # Personalizado por día (L-V)
            personalizado_enabled = 1 if self.personalizado_por_dia_enabled.get() else 0
            # Entradas por día
            entrada_lu = (self.entrada_lunes_var.get().strip() + ":00") if self.entrada_lunes_var.get().strip() else None
            entrada_ma = (self.entrada_martes_var.get().strip() + ":00") if self.entrada_martes_var.get().strip() else None
            entrada_mi = (self.entrada_miercoles_var.get().strip() + ":00") if self.entrada_miercoles_var.get().strip() else None
            entrada_ju = (self.entrada_jueves_var.get().strip() + ":00") if self.entrada_jueves_var.get().strip() else None
            entrada_vi = (self.entrada_viernes_var.get().strip() + ":00") if self.entrada_viernes_var.get().strip() else None
            # Salidas por día
            salida_lu = (self.salida_lunes_var.get().strip() + ":00") if self.salida_lunes_var.get().strip() else None
            salida_ma = (self.salida_martes_var.get().strip() + ":00") if self.salida_martes_var.get().strip() else None
            salida_mi = (self.salida_miercoles_var.get().strip() + ":00") if self.salida_miercoles_var.get().strip() else None
            salida_ju = (self.salida_jueves_var.get().strip() + ":00") if self.salida_jueves_var.get().strip() else None
            salida_vi = (self.salida_viernes_var.get().strip() + ":00") if self.salida_viernes_var.get().strip() else None

            def _normalize_uid(uid_text: str) -> str:
                try:
                    import re as _re
                    return _re.sub(r"[^0-9A-Fa-f]", "", uid_text or "").upper()
                except Exception:
                    return (uid_text or "").replace(" ", "").upper()

            uid_raw = self.nfc_uid_var.get().strip()
            uid_norm = _normalize_uid(uid_raw) if uid_raw else None

            # Validación de duplicados de UID (si viene alguno)
            if uid_norm:
                try:
                    if db_manager.is_online():
                        c = db_manager.pg_connection.cursor()
                        if self.employee_id.get():
                            c.execute(
                                """
                                SELECT COUNT(*) FROM empleados 
                                WHERE activo = TRUE AND REPLACE(UPPER(nfc_uid),' ','') = %s AND id <> %s
                                """,
                                (uid_norm, int(self.employee_id.get()))
                            )
                        else:
                            c.execute(
                                """
                                SELECT COUNT(*) FROM empleados 
                                WHERE activo = TRUE AND REPLACE(UPPER(nfc_uid),' ','') = %s
                                """,
                                (uid_norm,)
                            )
                        if (c.fetchone() or [0])[0] > 0:
                            messagebox.showerror("Tarjeta en uso", "Esta tarjeta NFC ya está asignada a otro empleado.")
                            return
                    else:
                        c = db_manager.sqlite_connection.cursor()
                        if self.employee_id.get():
                            c.execute(
                                """
                                SELECT COUNT(*) FROM empleados_local 
                                WHERE activo = 1 AND REPLACE(UPPER(nfc_uid),' ','') = ? AND id <> ?
                                """,
                                (uid_norm, int(self.employee_id.get()))
                            )
                        else:
                            c.execute(
                                """
                                SELECT COUNT(*) FROM empleados_local 
                                WHERE activo = 1 AND REPLACE(UPPER(nfc_uid),' ','') = ?
                                """,
                                (uid_norm,)
                            )
                        if (c.fetchone() or [0])[0] > 0:
                            messagebox.showerror("Tarjeta en uso", "Esta tarjeta NFC ya está asignada a otro empleado.")
                            return
                except Exception:
                    # En caso de error de validación, seguimos y dejamos que UNIQUE de la BD actúe
                    pass

            # Preparar datos (usar uid normalizado)
            rol_val = self.rol_var.get().strip()
            empleado_data = {
                'nombre_completo': self.nombre_var.get().strip(),
                'cargo': rol_val,
                'rol': rol_val,
                'nfc_uid': uid_norm if uid_norm else None,
                'hora_entrada': hora_entrada,
                'hora_salida': hora_salida,
                'hora_entrada_alt': hora_entrada_alt,
                'hora_salida_alt': hora_salida_alt,
                'rotacion_semanal': rotacion,
                'rotacion_semana_base': semana_base,
                'personalizado_por_dia_enabled': personalizado_enabled,
                'salida_por_dia_enabled': personalizado_enabled,  # compatibilidad legacy
                'entrada_lunes': entrada_lu,
                'entrada_martes': entrada_ma,
                'entrada_miercoles': entrada_mi,
                'entrada_jueves': entrada_ju,
                'entrada_viernes': entrada_vi,
                'salida_lunes': salida_lu,
                'salida_martes': salida_ma,
                'salida_miercoles': salida_mi,
                'salida_jueves': salida_ju,
                'salida_viernes': salida_vi
            }
            
            # Guardar en base de datos
            if db_manager.is_online():
                cursor = db_manager.pg_connection.cursor()
                
                if self.employee_id.get():
                    # Actualizar
                    cursor.execute("""
                        UPDATE empleados SET 
                        nombre_completo = %s, cargo = %s, rol = %s, nfc_uid = %s,
                        hora_entrada = %s, hora_salida = %s
                        WHERE id = %s
                    """, (
                        empleado_data['nombre_completo'], empleado_data['cargo'], empleado_data['rol'], empleado_data['nfc_uid'],
                        empleado_data['hora_entrada'], empleado_data['hora_salida'],
                        self.employee_id.get()
                    ))
                    employee_id = self.employee_id.get()
                else:
                    # Insertar
                    cursor.execute(
                        """
                        INSERT INTO empleados (nombre_completo, cargo, rol, nfc_uid, hora_entrada, hora_salida)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                        """,
                        (
                            empleado_data['nombre_completo'], empleado_data['cargo'], empleado_data['rol'], empleado_data['nfc_uid'],
                            empleado_data['hora_entrada'], empleado_data['hora_salida']
                        )
                    )
                    employee_id = cursor.fetchone()[0]
                
                db_manager.pg_connection.commit()
                # Espejo local para aplicar personalizados en lector y reportes incluso en modo online
                try:
                    conn = db_manager.sqlite_connection
                    cur_l = conn.cursor()
                    cur_l.execute("PRAGMA table_info(empleados_local)")
                    cols = {row[1] for row in cur_l.fetchall()}
                    # Asegurar últimas migraciones si faltan columnas
                    try:
                        missing = {"hora_entrada_alt", "hora_salida_alt", "rotacion_semanal", "rotacion_semana_base",
                                   "salida_por_dia_enabled","salida_lunes","salida_martes","salida_miercoles","salida_jueves","salida_viernes",
                                   "personalizado_por_dia_enabled","entrada_lunes","entrada_martes","entrada_miercoles","entrada_jueves","entrada_viernes"} - cols
                        if missing:
                            from migrations import apply_pending_migrations
                            apply_pending_migrations(conn)
                            cur_l.execute("PRAGMA table_info(empleados_local)")
                            cols = {row[1] for row in cur_l.fetchall()}
                    except Exception:
                        pass
                    # Preparar datos filtrados y forzar id consistente con nube
                    filtered = {k: v for k, v in empleado_data.items() if k in cols or k in {'nombre_completo','cargo','rol','nfc_uid','hora_entrada','hora_salida'}}
                    filtered['id'] = int(employee_id)
                    # Upsert: INSERT OR REPLACE por id
                    columns = ", ".join(filtered.keys())
                    placeholders = ", ".join(["?"] * len(filtered))
                    values = list(filtered.values())
                    cur_l.execute(f"INSERT OR REPLACE INTO empleados_local ({columns}) VALUES ({placeholders})", values)
                    conn.commit()
                except Exception:
                    pass
            else:
                # Verificar columnas disponibles y aplicar migraciones si faltan
                conn = db_manager.sqlite_connection
                cursor = conn.cursor()
                try:
                    cursor.execute("PRAGMA table_info(empleados_local)")
                    cols = {row[1] for row in cursor.fetchall()}
                except Exception:
                    cols = set()
                # Intentar actualizar esquema si faltan columnas relevantes
                try:
                    missing = {"hora_entrada_alt", "hora_salida_alt", "rotacion_semanal", "rotacion_semana_base",
                               "salida_por_dia_enabled","salida_lunes","salida_martes","salida_miercoles","salida_jueves","salida_viernes",
                               "personalizado_por_dia_enabled","entrada_lunes","entrada_martes","entrada_miercoles","entrada_jueves","entrada_viernes"} - cols
                    if missing:
                        from migrations import apply_pending_migrations
                        apply_pending_migrations(conn)
                        cursor.execute("PRAGMA table_info(empleados_local)")
                        cols = {row[1] for row in cursor.fetchall()}
                except Exception:
                    pass

                # Filtrar solo columnas existentes
                filtered = {k: v for k, v in empleado_data.items() if k in cols or k in {'nombre_completo','cargo','rol','nfc_uid','hora_entrada','hora_salida'}}

                if self.employee_id.get():
                    assignments = ", ".join([f"{k} = ?" for k in filtered.keys()])
                    values = list(filtered.values()) + [self.employee_id.get()]
                    cursor.execute(f"UPDATE empleados_local SET {assignments} WHERE id = ?", values)
                    employee_id = self.employee_id.get()
                else:
                    columns = ", ".join(filtered.keys())
                    placeholders = ", ".join(["?"] * len(filtered))
                    values = list(filtered.values())
                    cursor.execute(f"INSERT INTO empleados_local ({columns}) VALUES ({placeholders})", values)
                    employee_id = cursor.lastrowid

                conn.commit()
            
            # Guardar foto si existe
            if self.foto_path.get():
                self.save_employee_photo(employee_id)
            
            messagebox.showinfo("Éxito", "Empleado guardado correctamente")
            self.load_employees()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error guardando empleado: {e}")

    def download_employee_full(self):
        """Generar Expediente Completo (PDF) del empleado seleccionado."""
        try:
            if not self.employee_id.get():
                messagebox.showerror("Selecciona empleado", "Primero selecciona un empleado.")
                return
            rg = ReportGenerator()
            files = rg.generate_employee_full_report(int(self.employee_id.get()))
            if not files:
                messagebox.showwarning("Sin datos", "No hay historial para este empleado.")
                return
            messagebox.showinfo("Expediente generado", "\n".join(files))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el expediente: {e}")

    def new_employee_with_nfc(self):
        """Flujo rápido: escanear tarjeta, pedir datos mínimos y guardar empleado."""
        try:
            from acr122u_driver import acr122u_reader
            # 1) Escanear tarjeta
            uid, msg = acr122u_reader.read_single_card(timeout=20)
            if not uid:
                messagebox.showwarning("Sin lectura", msg or "No se detectó ninguna tarjeta.")
                return

            # 2) Validar duplicado
            exists = False
            def _norm(u: str) -> str:
                try:
                    import re as _re
                    return _re.sub(r"[^0-9A-Fa-f]", "", u or "").upper()
                except Exception:
                    return (u or "").replace(" ", "").upper()
            uid_norm = _norm(uid)
            if db_manager.is_online():
                c = db_manager.pg_connection.cursor()
                c.execute(
                    "SELECT COUNT(*) FROM empleados WHERE REPLACE(UPPER(nfc_uid),' ','') = %s AND activo = TRUE",
                    (uid_norm,)
                )
                exists = c.fetchone()[0] > 0
            else:
                c = db_manager.sqlite_connection.cursor()
                c.execute(
                    "SELECT COUNT(*) FROM empleados_local WHERE REPLACE(UPPER(nfc_uid),' ','') = ? AND activo = 1",
                    (uid_norm,)
                )
                exists = c.fetchone()[0] > 0
            if exists:
                messagebox.showerror("Tarjeta en uso", "Esta tarjeta NFC ya está asignada a otro empleado.")
                return

            # 3) Pedir datos mínimos
            # Nombre completo: campo ANCHO (alineación por defecto a la izquierda)
            nombre = self._ask_wide_string("Nuevo Empleado", "Nombre completo:", center_text=False)
            if not nombre:
                return
            # ROL: campo ANCHO y texto CENTRADO
            rol = self._ask_wide_string("Nuevo Empleado", "ROL:", center_text=True)
            if not rol:
                return

            # 4) Cargar en formulario y guardar
            self.employee_id.set("")
            self.nombre_var.set(nombre.strip())
            self.rol_var.set(rol.strip())
            # Establecer UID normalizado en formulario (sin espacios)
            self.nfc_uid_var.set(uid_norm)
            self.hora_entrada_var.set("09:00")
            self.hora_salida_var.set("18:00")
            self.save_employee()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el empleado: {e}")
    
    def save_employee_photo(self, employee_id):
        """Guardar foto del empleado"""
        try:
            if self.foto_path.get():
                # Guardar SIEMPRE en la ruta global
                dest_path = str(self.images_base_dir / f"empleado_{employee_id}.jpg")
                
                # Redimensionar y guardar imagen
                img = Image.open(self.foto_path.get())
                img = ImageOps.fit(img, (480, 480), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                img.save(dest_path, "JPEG", quality=90)
                
                # Actualizar path en base de datos
                if db_manager.is_online():
                    cursor = db_manager.pg_connection.cursor()
                    cursor.execute("UPDATE empleados SET foto_path = %s WHERE id = %s", 
                                 (dest_path, employee_id))
                    db_manager.pg_connection.commit()
                else:
                    cursor = db_manager.sqlite_connection.cursor()
                    cursor.execute("UPDATE empleados_local SET foto_path = ? WHERE id = ?", 
                                 (dest_path, employee_id))
                    db_manager.sqlite_connection.commit()
                    
        except Exception as e:
            print(f"Error guardando foto: {e}")
    
    def delete_employee(self):
        """Eliminar empleado"""
        if not self.employee_id.get():
            messagebox.showerror("Error", "Seleccione un empleado para eliminar")
            return
        
        if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar este empleado?"):
            try:
                if db_manager.is_online():
                    cursor = db_manager.pg_connection.cursor()
                    cursor.execute("UPDATE empleados SET activo = FALSE WHERE id = %s", 
                                 (self.employee_id.get(),))
                    db_manager.pg_connection.commit()
                else:
                    cursor = db_manager.sqlite_connection.cursor()
                    cursor.execute("UPDATE empleados_local SET activo = 0 WHERE id = ?", 
                                 (self.employee_id.get(),))
                    db_manager.sqlite_connection.commit()
                
                messagebox.showinfo("Éxito", "Empleado eliminado correctamente")
                self.load_employees()
                self.new_employee()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error eliminando empleado: {e}")
    
    def read_nfc(self):
        """Leer tarjeta NFC ACR122U"""
        try:
            from acr122u_reader import ACR122UReader
            
            # Crear instancia temporal del lector
            reader = ACR122UReader()
            
            # Mostrar ventana de espera
            wait_window = tk.Toplevel(self.window)
            wait_window.title("Leyendo Tarjeta NFC")
            wait_window.geometry("400x200")
            wait_window.configure(bg='#f0f0f0')
            wait_window.transient(self.window)
            wait_window.grab_set()
            
            # Centrar ventana
            wait_window.geometry("+%d+%d" % (self.window.winfo_rootx() + 400, self.window.winfo_rooty() + 300))
            
            frame = tk.Frame(wait_window, bg='#f0f0f0', padx=20, pady=20)
            frame.pack(expand=True, fill='both')
            
            tk.Label(frame, text="🔍 Leyendo tarjeta NFC...", 
                    font=('Arial', 14, 'bold'), bg='#f0f0f0').pack(pady=10)
            
            status_label = tk.Label(frame, text="Acerque la tarjeta al lector ACR122U", 
                                  font=('Arial', 12), bg='#f0f0f0', fg='#666666')
            status_label.pack(pady=10)
            
            progress_label = tk.Label(frame, text="⏳ Esperando...", 
                                    font=('Arial', 10), bg='#f0f0f0', fg='#2196F3')
            progress_label.pack(pady=5)
            
            def cancel_read():
                wait_window.destroy()
            
            tk.Button(frame, text="Cancelar", command=cancel_read,
                     bg='#f44336', fg='white', font=('Arial', 10), padx=20).pack(pady=20)
            
            # Variable para almacenar el UID leído
            uid_result = [None]
            
            def read_in_thread():
                try:
                    # Actualizar estado
                    status_label.config(text="🔄 Buscando lector ACR122U...")
                    wait_window.update()
                    
                    if not reader.reader:
                        status_label.config(text="❌ Lector ACR122U no encontrado", fg='red')
                        progress_label.config(text="Verifique la conexión del lector")
                        return
                    
                    status_label.config(text="✅ Lector ACR122U detectado")
                    progress_label.config(text="💳 Acerque la tarjeta al lector...")
                    wait_window.update()
                    
                    # Leer tarjeta con timeout de 10 segundos
                    uid = reader.read_single_card(timeout=10)
                    
                    if uid:
                        uid_result[0] = uid
                        status_label.config(text="✅ Tarjeta leída exitosamente!", fg='green')
                        progress_label.config(text=f"UID: {uid}")
                        wait_window.update()
                        
                        # Esperar un momento antes de cerrar
                        time.sleep(1)
                        wait_window.after(0, wait_window.destroy)
                    else:
                        status_label.config(text="⏰ Tiempo agotado", fg='orange')
                        progress_label.config(text="No se detectó ninguna tarjeta")
                        
                except Exception as e:
                    status_label.config(text="❌ Error leyendo tarjeta", fg='red')
                    progress_label.config(text=f"Error: {str(e)}")
            
            # Iniciar lectura en hilo separado
            import threading
            import time
            read_thread = threading.Thread(target=read_in_thread, daemon=True)
            read_thread.start()
            
            # Esperar a que termine la lectura
            wait_window.wait_window()
            
            # Usar el UID leído
            if uid_result[0]:
                self.nfc_uid_var.set(uid_result[0])
                messagebox.showinfo("Éxito", f"Tarjeta NFC leída correctamente!\nUID: {uid_result[0]}")
            
        except ImportError:
            # Fallback a entrada manual si no está disponible el lector
            nfc_uid = tk.simpledialog.askstring("NFC", "Ingrese UID de tarjeta NFC manualmente:")
            if nfc_uid:
                self.nfc_uid_var.set(nfc_uid)

    def scan_and_assign_nfc(self):
        """Flujo: Escanear tarjeta primero y asignar al formulario (usa lector unificado)."""
        try:
            from acr122u_driver import acr122u_reader
            uid, msg = acr122u_reader.read_single_card(timeout=15)
            if uid:
                # Validar si ese UID ya está asignado
                exists = False
                def _norm(u: str) -> str:
                    try:
                        import re as _re
                        return _re.sub(r"[^0-9A-Fa-f]", "", u or "").upper()
                    except Exception:
                        return (u or "").replace(" ", "").upper()
                uid_norm = _norm(uid)
                if db_manager.is_online():
                    c = db_manager.pg_connection.cursor()
                    c.execute(
                        "SELECT COUNT(*) FROM empleados WHERE REPLACE(UPPER(nfc_uid),' ','') = %s AND activo = TRUE",
                        (uid_norm,)
                    )
                    exists = c.fetchone()[0] > 0
                else:
                    c = db_manager.sqlite_connection.cursor()
                    c.execute(
                        "SELECT COUNT(*) FROM empleados_local WHERE REPLACE(UPPER(nfc_uid),' ','') = ? AND activo = 1",
                        (uid_norm,)
                    )
                    exists = c.fetchone()[0] > 0

                if exists:
                    messagebox.showerror("Tarjeta en uso", "Esta tarjeta NFC ya está asignada a otro empleado.")
                else:
                    self.nfc_uid_var.set(uid_norm)
                    messagebox.showinfo("Tarjeta asignada", f"UID asignado: {uid_norm}\nAhora completa los datos y pulsa Guardar.")
            else:
                messagebox.showwarning("Sin lectura", msg or "No se detectó ninguna tarjeta.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la tarjeta: {e}")

    def enter_uid_manual(self):
        """Solicita el UID manualmente y lo coloca en el campo NFC UID.
        Acepta hex con o sin espacios y valida longitud par mínima (8 dígitos = 4 bytes).
        """
        uid = simpledialog.askstring(
            "Ingresar UID",
            "Escribe el UID de la tarjeta (hex):\nEjemplos: 04A1B2C3 o 04 A1 B2 C3",
            parent=self.window,
        )
        if uid is None:
            return
        uid_raw = uid.strip()
        # Dejar solo caracteres hexadecimales
        uid_hex = re.sub(r"[^0-9A-Fa-f]", "", uid_raw)
        if len(uid_hex) < 8 or len(uid_hex) % 2 != 0:
            messagebox.showerror(
                "UID inválido",
                "Debe contener solo hex (0-9 A-F), tener longitud par y al menos 8 dígitos.",
            )
            return
        uid_hex = uid_hex.upper()
        pretty = " ".join(uid_hex[i:i+2] for i in range(0, len(uid_hex), 2))
        # Asignar al formulario (guardamos normalizado sin espacios)
        try:
            self.nfc_uid_var.set(uid_hex)
            messagebox.showinfo("UID capturado", f"UID: {pretty}\nSe guardará como: {uid_hex}\nAhora pulsa Guardar para registrar.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo establecer el UID: {e}")

    def download_employee_daily(self):
        """Generar y guardar expediente diario del empleado actual."""
        try:
            if not self.employee_id.get():
                messagebox.showerror("Selecciona empleado", "Primero selecciona o guarda un empleado.")
                return
            from report_generator import report_generator
            files = report_generator.generate_employee_daily_report(int(self.employee_id.get()), formato='both')
            if files:
                messagebox.showinfo("Expediente generado", "\n".join(files))
            else:
                messagebox.showwarning("Sin datos", "No hay registros para hoy.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el expediente: {e}")

    def download_employee_monthly(self):
        """Generar y guardar expediente mensual del empleado actual."""
        try:
            if not self.employee_id.get():
                messagebox.showerror("Selecciona empleado", "Primero selecciona o guarda un empleado.")
                return
            from datetime import datetime
            from report_generator import report_generator
            now = datetime.now()
            files = report_generator.generate_employee_report(int(self.employee_id.get()), now.year, now.month, 'both')
            if files:
                messagebox.showinfo("Expediente generado", "\n".join(files))
            else:
                messagebox.showwarning("Sin datos", "No hay registros en el mes actual.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el expediente: {e}")

    def export_employee_daily(self):
        try:
            if not self.employee_id.get():
                messagebox.showerror("Selecciona empleado", "Primero selecciona o guarda un empleado.")
                return
            from datetime import datetime
            from report_generator import report_generator
            fecha_str = self.hist_fecha_var.get().strip()
            fecha = None
            if fecha_str:
                fecha = datetime.fromisoformat(fecha_str).date()
            files = report_generator.generate_employee_daily_report(int(self.employee_id.get()), fecha=fecha, formato='both')
            if files:
                messagebox.showinfo("Exportado", "\n".join(files))
            else:
                messagebox.showwarning("Sin datos", "No hay registros para esa fecha.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def export_employee_monthly(self):
        try:
            if not self.employee_id.get():
                messagebox.showerror("Selecciona empleado", "Primero selecciona o guarda un empleado.")
                return
            from datetime import datetime
            from report_generator import report_generator
            mes_str = self.hist_mes_var.get().strip()
            if not mes_str:
                now = datetime.now()
                year, month = now.year, now.month
            else:
                year, month = map(int, mes_str.split('-'))
            files = report_generator.generate_employee_report(int(self.employee_id.get()), year, month, 'both')
            if files:
                messagebox.showinfo("Exportado", "\n".join(files))
            else:
                messagebox.showwarning("Sin datos", "No hay registros para ese mes.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def delete_employee_daily(self):
        try:
            if not self.employee_id.get():
                messagebox.showerror("Selecciona empleado", "Primero selecciona un empleado.")
                return
            fecha = self.hist_fecha_var.get().strip()
            if not fecha:
                messagebox.showerror("Fecha requerida", "Ingresa la fecha (YYYY-MM-DD).")
                return
            if not messagebox.askyesno("Confirmar", f"¿Borrar registros del {fecha}? Esta acción no se puede deshacer."):
                return
            borrados = db_manager.borrar_registros_empleado_dia(int(self.employee_id.get()), fecha)
            messagebox.showinfo("Completado", f"Registros borrados: {borrados}")
            self.load_employees()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo borrar: {e}")

    def view_employee_history(self):
        try:
            if not self.employee_id.get():
                messagebox.showerror("Selecciona empleado", "Primero selecciona un empleado.")
                return
            emp_id = int(self.employee_id.get())
            fecha = self.hist_fecha_var.get().strip()
            mes = self.hist_mes_var.get().strip()

            # Obtener datos
            rows = []
            if fecha:
                if db_manager.is_online():
                    c = db_manager.pg_connection.cursor()
                    c.execute("""
                        SELECT fecha, hora_registro, tipo_movimiento, estado, u.nombre
                        FROM registros_asistencia r
                        JOIN ubicaciones u ON r.ubicacion_id = u.id
                        WHERE r.empleado_id = %s AND r.fecha = %s
                        ORDER BY hora_registro
                    """, (emp_id, fecha))
                    rows = c.fetchall()
                else:
                    c = db_manager.sqlite_connection.cursor()
                    c.execute("""
                        SELECT fecha, hora_registro, tipo_movimiento, estado, ubicacion_nombre
                        FROM registros_local
                        WHERE empleado_id = ? AND fecha = ?
                        ORDER BY hora_registro
                    """, (emp_id, fecha))
                    rows = c.fetchall()
            else:
                # Mes
                from datetime import datetime
                if not mes:
                    now = datetime.now()
                    year, month = now.year, now.month
                else:
                    year, month = map(int, mes.split('-'))
                if db_manager.is_online():
                    c = db_manager.pg_connection.cursor()
                    c.execute("""
                        SELECT fecha, hora_registro, tipo_movimiento, estado, u.nombre
                        FROM registros_asistencia r
                        JOIN ubicaciones u ON r.ubicacion_id = u.id
                        WHERE r.empleado_id = %s AND EXTRACT(YEAR FROM fecha) = %s AND EXTRACT(MONTH FROM fecha) = %s
                        ORDER BY fecha, hora_registro
                    """, (emp_id, year, month))
                    rows = c.fetchall()
                else:
                    c = db_manager.sqlite_connection.cursor()
                    c.execute("""
                        SELECT fecha, hora_registro, tipo_movimiento, estado, ubicacion_nombre
                        FROM registros_local
                        WHERE empleado_id = ? AND substr(fecha,1,4) = ? AND substr(fecha,6,2) = ?
                        ORDER BY fecha, hora_registro
                    """, (emp_id, str(year), f"{month:02d}"))
                    rows = c.fetchall()

            # Ventana modal
            win = tk.Toplevel(self.window)
            win.title("Historial de movimientos")
            win.geometry("760x520")
            win.configure(bg=self.bg_primary)
            win.transient(self.window)
            win.grab_set()

            title = tk.Label(win, text="Historial de movimientos", font=('Segoe UI', 14, 'bold'), bg=self.bg_primary, fg=self.text_primary)
            title.pack(pady=8)

            cols = ('Fecha', 'Hora', 'Movimiento', 'Estado', 'Ubicación')
            tree = ttk.Treeview(win, columns=cols, show='headings', height=18)
            for c in cols:
                tree.heading(c, text=c)
                width = 120 if c in ('Fecha','Hora','Estado') else 200
                tree.column(c, width=width, anchor='center')
            vs = ttk.Scrollbar(win, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=vs.set)
            tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
            vs.pack(side='right', fill='y', pady=10)

            # Cargar filas
            from datetime import datetime as dt
            for r in rows:
                fecha_val, hora_val, mov, est, ubi = r
                # Normalizar
                fecha_str = str(fecha_val)
                ubi_str = str(ubi).upper()
                if isinstance(hora_val, str):
                    try:
                        h = dt.fromisoformat(hora_val)
                        hora_str = h.strftime('%H:%M:%S')
                    except Exception:
                        hora_str = hora_val
                else:
                    hora_str = hora_val.strftime('%H:%M:%S') if hasattr(hora_val, 'strftime') else str(hora_val)
                tree.insert('', 'end', values=(fecha_str, hora_str, mov, est, ubi_str))

            # Botonera de exportación y borrado rápido
            btns = tk.Frame(win, bg=self.bg_primary)
            btns.pack(fill='x', pady=(0,10))
            self.make_button(btns, 'Exportar Diario', self.export_employee_daily, bg=self.accent, fg='black', hover_bg='#7FD6D4').pack(side='left', padx=6)
            self.make_button(btns, 'Exportar Mensual', self.export_employee_monthly, bg=self.accent, fg='black', hover_bg='#7FD6D4').pack(side='left', padx=6)
            self.make_button(btns, 'Descargar Expediente Mensual (PDF)', self.download_employee_monthly, bg='#06D6A0', fg='black', hover_bg='#4CE0B9').pack(side='left', padx=6)
            # Borrado
            self.make_button(btns, 'Borrar Día', self.delete_employee_daily, bg='#E76F51', fg='white', hover_bg='#F08A6B').pack(side='right', padx=6)
            self.make_button(btns, 'Borrar Mes', self.delete_employee_monthly, bg='#E63946', fg='white', hover_bg='#EF5350').pack(side='right', padx=6)
            self.make_button(btns, 'Borrar Todo', self.delete_employee_all, bg='#9C27B0', fg='white', hover_bg='#B85BC7').pack(side='right', padx=6)
            self.make_button(btns, 'Cerrar', win.destroy, bg='#9E9E9E', fg='white', hover_bg='#BDBDBD').pack(side='right', padx=6)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo mostrar el historial: {e}")

    def delete_employee_monthly(self):
        try:
            if not self.employee_id.get():
                messagebox.showerror("Selecciona empleado", "Primero selecciona un empleado.")
                return
            mes_str = self.hist_mes_var.get().strip()
            if not mes_str:
                messagebox.showerror("Mes requerido", "Ingresa el mes (YYYY-MM).")
                return
            year, month = map(int, mes_str.split('-'))
            if not messagebox.askyesno("Confirmar", f"¿Borrar registros de {year}-{month:02d}? Esta acción no se puede deshacer."):
                return
            borrados = db_manager.borrar_registros_empleado_mes(int(self.employee_id.get()), year, month)
            messagebox.showinfo("Completado", f"Registros borrados: {borrados}")
            self.load_employees()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo borrar: {e}")

    # ==== Reportes Generales (menú Reportes) ====
    def generate_general_daily(self):
        """Genera el reporte general diario (PDF+Excel) solicitando fecha."""
        try:
            # Preguntar fecha (YYYY-MM-DD)
            from datetime import datetime
            hoy = datetime.now().strftime('%Y-%m-%d')
            fecha_str = simpledialog.askstring("Fecha del reporte diario", "Ingresa la fecha (YYYY-MM-DD):", initialvalue=hoy, parent=self.window)
            if not fecha_str:
                return
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                messagebox.showerror("Formato inválido", "La fecha debe tener el formato YYYY-MM-DD.")
                return

            rg = ReportGenerator()
            files = rg.generate_daily_report(fecha=fecha, formato='both')
            if not files:
                messagebox.showwarning("Sin datos", f"No hay registros para {fecha_str}.")
                return
            # Mostrar rutas generadas
            msg = "\n".join(files)
            messagebox.showinfo("Reporte diario generado", f"Se generaron los siguientes archivos:\n\n{msg}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el reporte diario: {e}")

    def generate_general_monthly(self):
        """Genera el reporte general mensual (PDF+Excel) solicitando año y mes."""
        try:
            from datetime import datetime
            hoy = datetime.now()
            default_mes = hoy.strftime('%Y-%m')
            mes_str = simpledialog.askstring("Mes del reporte mensual", "Ingresa el mes (YYYY-MM):", initialvalue=default_mes, parent=self.window)
            if not mes_str:
                return
            try:
                year, month = map(int, mes_str.split('-'))
                if month < 1 or month > 12:
                    raise ValueError
            except Exception:
                messagebox.showerror("Formato inválido", "El mes debe tener el formato YYYY-MM.")
                return

            rg = ReportGenerator()
            files = rg.generate_monthly_report(year=year, month=month, formato='both')
            if not files:
                messagebox.showwarning("Sin datos", f"No hay registros para {year}-{month:02d}.")
                return
            msg = "\n".join(files)
            messagebox.showinfo("Reporte mensual generado", f"Se generaron los siguientes archivos:\n\n{msg}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el reporte mensual: {e}")

    def delete_employee_all(self):
        try:
            if not self.employee_id.get():
                messagebox.showerror("Selecciona empleado", "Primero selecciona un empleado.")
                return
            emp_id = int(self.employee_id.get())
            if not messagebox.askyesno("Confirmar", "¿Borrar TODOS los registros del empleado? Esta acción no se puede deshacer."):
                return
            borrados = db_manager.borrar_registros_empleado_todos(emp_id)
            messagebox.showinfo("Completado", f"Registros borrados: {borrados}")
            self.load_employees()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo borrar: {e}")

if __name__ == "__main__":
    import tkinter.simpledialog
    app = AdminInterface()
    app.window.mainloop()