import queue
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from ayuda_interfaz import AyudaEmergente, configurar_estilos
from servicio_configuracion import ServicioConfiguracion
from servicio_exportacion_historial import ServicioExportacionHistorial
from servicio_historial_git import ServicioHistorialGit
from servicio_remoto_git import ServicioRemotoGit


class AplicacionGit:
    """
    Ventana principal de la aplicación Gestor Git.

    Las operaciones locales y remotas pasan por ServicioRemotoGit.

    Las operaciones de red se ejecutan en hilos secundarios
    para evitar que la interfaz de Tkinter se congele.
    """

    def __init__(self, ventana_principal):
        # Ventana principal de Tkinter.
        self.ventana_principal = ventana_principal

        # Configuramos la apariencia visual antes de crear
        # los controles de la aplicación.
        self.estilos = configurar_estilos(
            self.ventana_principal
        )

        # Servicio que contiene las operaciones locales,
        # Fetch, Pull y Push.
        self.servicio_git = ServicioRemotoGit()

        # Servicio que recuerda el último repositorio seleccionado.
        # Guarda únicamente la ruta local en config.json y nunca
        # credenciales; la carga automática no ejecuta Fetch.
        self.servicio_configuracion = ServicioConfiguracion(
            self.servicio_git
        )

        # Servicio independiente de solo lectura para consultar
        # el historial de commits. Reutiliza el mismo ServicioGit.
        self.servicio_historial = ServicioHistorialGit(
            self.servicio_git
        )

        # Servicio que guarda una copia del historial visible en CSV o TXT.
        # No ejecuta Git y no modifica el repositorio.
        self.servicio_exportacion_historial = ServicioExportacionHistorial()

        # La ventana de historial se crea únicamente cuando el usuario
        # la solicita y se reutiliza mientras permanezca abierta.
        self.ventana_historial = None
        self.tabla_historial = None
        self.variable_estado_historial = None
        self.variable_filtro_archivo_historial = None
        self.variable_fecha_desde_historial = None
        self.variable_fecha_hasta_historial = None
        self.boton_exportar_csv_historial = None
        self.boton_exportar_txt_historial = None

        # Relaciona las filas visibles del historial con su CommitGit.
        # La ventana de detalle utiliza esta relación y no vuelve
        # a consultar el historial.
        self.commits_historial_por_elemento = {}

        # Botón que muestra los cambios del commit seleccionado.
        self.boton_ver_cambios_historial = None

        # Ventana única con los cambios de un commit (solo lectura).
        self.ventana_detalle_commit = None
        self.texto_detalle_commit = None

        # Límite visual del diff mostrado en la ventana de detalle.
        # La truncación es solamente visual: no modifica el repositorio.
        self.limite_caracteres_detalle = 500000

        # La ventana de configuración de GitHub se crea únicamente
        # cuando el usuario la solicita y se reutiliza mientras
        # permanezca abierta.
        self.ventana_configuracion_github = None
        self.variable_url_github = None

        # Conserva exactamente los commits que se están mostrando.
        # Las exportaciones usan esta lista y no vuelven a ejecutar git log.
        self.commits_historial_actual = []

        # Conserva los filtros de la última consulta exitosa para que
        # el TXT documente exactamente qué información fue exportada.
        self.filtros_historial_aplicados = {
            "archivo": "",
            "desde": "",
            "hasta": ""
        }

        # Repositorio actualmente seleccionado.
        self.ruta_repositorio = ""

        # Lista de remotos del repositorio seleccionado.
        self.remotos_repositorio = []

        # Relaciona las filas visuales con CambioArchivo.
        self.cambios_por_elemento = {}

        # Indica si existen cambios pendientes de commit.
        self.hay_cambios_pendientes = False

        # Guarda el último EstadoSincronizacion calculado.
        self.estado_sincronizacion_actual = None

        # Pull y Push solamente se habilitan después
        # de un Fetch exitoso durante la sesión actual.
        self.fetch_exitoso_en_sesion = False

        # Los hilos secundarios devolverán resultados
        # mediante esta cola.
        self.cola_resultados = queue.Queue()

        # Evita ejecutar varias operaciones remotas simultáneamente.
        self.operacion_remota_en_curso = False

        self.configurar_ventana()
        self.crear_interfaz()
        self.verificar_git()
        self.cargar_repositorio_recordado()

        # Tkinter revisará periódicamente la cola
        # de resultados de los hilos.
        self.ventana_principal.after(
            100,
            self.procesar_cola_resultados
        )

    def configurar_ventana(self):
        """
        Configura las propiedades generales de la ventana.
        """

        self.ventana_principal.title(
            "Gestor Git"
        )

        self.ventana_principal.geometry(
            "1180x900"
        )

        self.ventana_principal.minsize(
            950,
            720
        )

    def crear_interfaz(self):
        """
        Crea todos los controles visibles.
        """

        marco_principal = ttk.Frame(
            self.ventana_principal,
            padding=15
        )

        marco_principal.pack(
            fill=tk.BOTH,
            expand=True
        )

        marco_principal.columnconfigure(
            0,
            weight=1
        )

        # La tabla ocupará el espacio vertical sobrante.
        marco_principal.rowconfigure(
            5,
            weight=1
        )

        # ---------------------------------------------------------
        # Título
        # ---------------------------------------------------------

        marco_titulo = ttk.Frame(
            marco_principal
        )

        marco_titulo.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 15)
        )

        etiqueta_titulo = ttk.Label(
            marco_titulo,
            text="Gestor Git",
            style="Titulo.TLabel"
        )

        etiqueta_titulo.pack(
            anchor="w"
        )

        etiqueta_subtitulo = ttk.Label(
            marco_titulo,
            text=(
                "Gestiona tus cambios paso a paso y aprende "
                "qué hace cada operación de Git."
            ),
            style="Subtitulo.TLabel"
        )

        etiqueta_subtitulo.pack(
            anchor="w",
            pady=(2, 0)
        )

        # ---------------------------------------------------------
        # Repositorio
        # ---------------------------------------------------------

        marco_repositorio = ttk.LabelFrame(
            marco_principal,
            text="Repositorio",
            padding=10
        )

        marco_repositorio.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        marco_repositorio.columnconfigure(
            0,
            weight=1
        )

        self.variable_ruta = tk.StringVar(
            value="Ningún repositorio seleccionado"
        )

        entrada_ruta = ttk.Entry(
            marco_repositorio,
            textvariable=self.variable_ruta,
            state="readonly"
        )

        entrada_ruta.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 10)
        )

        self.boton_seleccionar = ttk.Button(
            marco_repositorio,
            text="Seleccionar...",
            command=self.seleccionar_repositorio,
            style="Accion.TButton"
        )

        self.boton_seleccionar.grid(
            row=0,
            column=1
        )

        self.boton_actualizar = ttk.Button(
            marco_repositorio,
            text="Actualizar",
            command=self.actualizar_repositorio,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_actualizar.grid(
            row=0,
            column=2,
            padx=(10, 0)
        )

        # ---------------------------------------------------------
        # Información local
        # ---------------------------------------------------------

        marco_informacion = ttk.LabelFrame(
            marco_principal,
            text="Información local",
            padding=10
        )

        marco_informacion.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        self.variable_rama = tk.StringVar(
            value="-"
        )

        self.variable_remoto = tk.StringVar(
            value="-"
        )

        self.variable_commits = tk.StringVar(
            value="-"
        )

        ttk.Label(
            marco_informacion,
            text="Rama:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_informacion,
            textvariable=self.variable_rama
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 30)
        )

        ttk.Label(
            marco_informacion,
            text="Remoto(s):"
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_informacion,
            textvariable=self.variable_remoto
        ).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(0, 30)
        )

        ttk.Label(
            marco_informacion,
            text="Tiene commits:"
        ).grid(
            row=0,
            column=4,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_informacion,
            textvariable=self.variable_commits
        ).grid(
            row=0,
            column=5,
            sticky="w"
        )

        self.boton_historial = ttk.Button(
            marco_informacion,
            text="Historial...",
            command=self.abrir_historial,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_historial.grid(
            row=0,
            column=6,
            sticky="e",
            padx=(30, 0)
        )

        # ---------------------------------------------------------
        # Sincronización remota
        # ---------------------------------------------------------

        marco_sincronizacion = ttk.LabelFrame(
            marco_principal,
            text="Sincronización remota",
            padding=10
        )

        marco_sincronizacion.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        marco_sincronizacion.columnconfigure(
            7,
            weight=1
        )

        self.variable_upstream = tk.StringVar(
            value="-"
        )

        self.variable_rama_remota = tk.StringVar(
            value="-"
        )

        self.variable_por_subir = tk.StringVar(
            value="-"
        )

        self.variable_por_bajar = tk.StringVar(
            value="-"
        )

        self.variable_estado_sincronizacion = tk.StringVar(
            value="Seleccione un repositorio."
        )

        self.variable_ultima_consulta = tk.StringVar(
            value="Todavía no se ejecutó Fetch en esta sesión."
        )

        ttk.Label(
            marco_sincronizacion,
            text="Upstream:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_upstream
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 25)
        )

        ttk.Label(
            marco_sincronizacion,
            text="Rama remota:"
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_rama_remota
        ).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(0, 25)
        )

        ttk.Label(
            marco_sincronizacion,
            text="Por enviar:"
        ).grid(
            row=0,
            column=4,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_por_subir
        ).grid(
            row=0,
            column=5,
            sticky="w",
            padx=(0, 25)
        )

        ttk.Label(
            marco_sincronizacion,
            text="Por descargar:"
        ).grid(
            row=0,
            column=6,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_por_bajar
        ).grid(
            row=0,
            column=7,
            sticky="w"
        )

        ttk.Label(
            marco_sincronizacion,
            text="Estado:"
        ).grid(
            row=1,
            column=0,
            sticky="nw",
            padx=(0, 5),
            pady=(8, 0)
        )

        self.etiqueta_estado_sincronizacion = ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_estado_sincronizacion,
            wraplength=650,
            style="EstadoSincronizacion.TLabel"
        )

        self.etiqueta_estado_sincronizacion.grid(
            row=1,
            column=1,
            columnspan=5,
            sticky="ew",
            pady=(8, 10)
        )

        # ---------------------------------------------------------
        # Botones remotos
        # ---------------------------------------------------------

        marco_botones_remotos = ttk.Frame(
            marco_sincronizacion
        )

        marco_botones_remotos.grid(
            row=1,
            column=6,
            columnspan=2,
            sticky="e",
            pady=(8, 0)
        )

        self.boton_fetch = ttk.Button(
            marco_botones_remotos,
            text="Fetch",
            command=self.iniciar_fetch,
            state=tk.DISABLED,
            style="Fetch.TButton"
        )

        self.boton_fetch.pack(
            side=tk.LEFT
        )

        self.boton_pull = ttk.Button(
            marco_botones_remotos,
            text="Pull",
            command=self.iniciar_pull,
            state=tk.DISABLED,
            style="Pull.TButton"
        )

        self.boton_pull.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_push = ttk.Button(
            marco_botones_remotos,
            text="Push",
            command=self.iniciar_push,
            state=tk.DISABLED,
            style="Push.TButton"
        )

        self.boton_push.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_configurar_github = ttk.Button(
            marco_botones_remotos,
            text="Configurar GitHub...",
            command=self.abrir_configuracion_github,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_configurar_github.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_ultima_consulta
        ).grid(
            row=2,
            column=0,
            columnspan=8,
            sticky="w",
            pady=(8, 0)
        )

        etiqueta_guia_git = ttk.Label(
            marco_sincronizacion,
            text=(
                "Guía rápida:  "
                "Fetch = consultar cambios del remoto sin modificar tus archivos.   "
                "Pull = descargar commits remotos mediante fast-forward.   "
                "Push = enviar tus commits locales al remoto."
            ),
            style="AyudaVisible.TLabel",
            wraplength=1050
        )

        etiqueta_guia_git.grid(
            row=3,
            column=0,
            columnspan=8,
            sticky="ew",
            pady=(10, 0)
        )

        # ---------------------------------------------------------
        # Archivos con cambios
        # ---------------------------------------------------------

        etiqueta_cambios = ttk.Label(
            marco_principal,
            text="Archivos con cambios:",
            font=("Segoe UI", 10, "bold")
        )

        etiqueta_cambios.grid(
            row=4,
            column=0,
            sticky="w",
            pady=(5, 5)
        )

        marco_tabla = ttk.Frame(
            marco_principal
        )

        marco_tabla.grid(
            row=5,
            column=0,
            sticky="nsew"
        )

        marco_tabla.columnconfigure(
            0,
            weight=1
        )

        marco_tabla.rowconfigure(
            0,
            weight=1
        )

        columnas = (
            "estado",
            "preparado",
            "archivo"
        )

        self.tabla_cambios = ttk.Treeview(
            marco_tabla,
            columns=columnas,
            show="headings",
            selectmode="extended"
        )

        self.tabla_cambios.heading(
            "estado",
            text="Estado"
        )

        self.tabla_cambios.heading(
            "preparado",
            text="Preparado"
        )

        self.tabla_cambios.heading(
            "archivo",
            text="Archivo"
        )

        self.tabla_cambios.column(
            "estado",
            width=280,
            minwidth=180
        )

        self.tabla_cambios.column(
            "preparado",
            width=140,
            minwidth=110,
            anchor="center"
        )

        self.tabla_cambios.column(
            "archivo",
            width=650,
            minwidth=250
        )

        self.tabla_cambios.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        barra_vertical = ttk.Scrollbar(
            marco_tabla,
            orient=tk.VERTICAL,
            command=self.tabla_cambios.yview
        )

        barra_vertical.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.tabla_cambios.configure(
            yscrollcommand=barra_vertical.set
        )

        barra_horizontal = ttk.Scrollbar(
            marco_tabla,
            orient=tk.HORIZONTAL,
            command=self.tabla_cambios.xview
        )

        barra_horizontal.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        self.tabla_cambios.configure(
            xscrollcommand=barra_horizontal.set
        )

        # Actualiza los botones de archivos según la selección.
        self.tabla_cambios.bind(
            "<<TreeviewSelect>>",
            self.actualizar_estado_botones_archivos
        )

        # ---------------------------------------------------------
        # Acciones sobre archivos
        # ---------------------------------------------------------

        marco_acciones = ttk.Frame(
            marco_principal
        )

        marco_acciones.grid(
            row=6,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        self.boton_seleccionar_todo = ttk.Button(
            marco_acciones,
            text="Seleccionar todo",
            command=self.seleccionar_todos_los_cambios,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_seleccionar_todo.pack(
            side=tk.LEFT
        )

        self.boton_preparar = ttk.Button(
            marco_acciones,
            text="Preparar seleccionados",
            command=self.preparar_seleccionados,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_preparar.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_actualizar_preparados = ttk.Button(
            marco_acciones,
            text="Actualizar preparados",
            command=self.actualizar_preparados_seleccionados,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_actualizar_preparados.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_quitar_preparados = ttk.Button(
            marco_acciones,
            text="Quitar de preparados",
            command=self.quitar_preparados_seleccionados,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_quitar_preparados.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        # ---------------------------------------------------------
        # Crear commit
        # ---------------------------------------------------------

        marco_commit = ttk.LabelFrame(
            marco_principal,
            text="Crear commit",
            padding=10
        )

        marco_commit.grid(
            row=7,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        marco_commit.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            marco_commit,
            text="Mensaje:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10)
        )

        self.variable_mensaje_commit = tk.StringVar()

        self.entrada_mensaje_commit = ttk.Entry(
            marco_commit,
            textvariable=self.variable_mensaje_commit
        )

        self.entrada_mensaje_commit.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 10)
        )

        self.boton_crear_commit = ttk.Button(
            marco_commit,
            text="Crear commit",
            command=self.crear_commit_desde_interfaz,
            state=tk.DISABLED,
            style="Commit.TButton"
        )

        self.boton_crear_commit.grid(
            row=0,
            column=2
        )

        ttk.Label(
            marco_commit,
            text=(
                "El commit se guardará solamente en el repositorio local. "
                "Utilice Push para enviarlo al remoto."
            )
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 0)
        )

        # ---------------------------------------------------------
        # Barra de estado
        # ---------------------------------------------------------

        self.variable_estado = tk.StringVar(
            value="Listo."
        )

        self.etiqueta_estado = tk.Label(
            marco_principal,
            textvariable=self.variable_estado,
            anchor="w",
            padx=10,
            pady=7,
            background="#E2E8F0",
            foreground="#334155",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold")
        )

        self.etiqueta_estado.grid(
            row=8,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        # Cuando cambia el texto de estado actualizamos
        # automáticamente su apariencia.
        self.variable_estado.trace_add(
            "write",
            self.actualizar_apariencia_estado
        )

        self.actualizar_apariencia_estado()
        self.configurar_ayudas()

    def configurar_ayudas(self):
        """
        Agrega explicaciones educativas a los controles principales.

        Guardamos las ayudas en una lista para mantener
        sus objetos disponibles durante toda la aplicación.
        """

        self.ayudas_emergentes = [
            AyudaEmergente(
                self.boton_seleccionar,
                (
                    "Seleccionar repositorio\n\n"
                    "Elige una carpeta que contenga un repositorio Git.\n\n"
                    "La aplicación solamente analizará esa carpeta. "
                    "Seleccionarla no modifica archivos ni ejecuta Fetch, "
                    "Pull o Push."
                )
            ),

            AyudaEmergente(
                self.boton_actualizar,
                (
                    "Actualizar estado local\n\n"
                    "Vuelve a leer el estado del repositorio desde tu disco.\n\n"
                    "Sirve para detectar archivos modificados, preparados "
                    "o nuevos commits locales.\n\n"
                    "No consulta Internet ni el repositorio remoto."
                )
            ),

            AyudaEmergente(
                self.boton_historial,
                (
                    "Historial de commits\n\n"
                    "Muestra los commits más recientes del repositorio local.\n\n"
                    "Es una consulta de SOLO LECTURA: no cambia archivos, "
                    "ramas, commits ni el repositorio remoto.\n\n"
                    "También permite filtrar y exportar los resultados "
                    "visibles a CSV o TXT."
                )
            ),

            AyudaEmergente(
                self.boton_fetch,
                (
                    "Fetch\n\n"
                    "Consulta el repositorio remoto y actualiza la información "
                    "que Git conoce sobre sus ramas.\n\n"
                    "Fetch NO modifica tus archivos de trabajo.\n\n"
                    "Después de Fetch, Gestor Git puede saber si existen "
                    "commits por enviar o por descargar."
                )
            ),

            AyudaEmergente(
                self.boton_pull,
                (
                    "Pull\n\n"
                    "Descarga commits que existen en el remoto y que todavía "
                    "no tienes localmente.\n\n"
                    "Gestor Git solamente permite Pull mediante fast-forward "
                    "(--ff-only).\n\n"
                    "No crea Merge automático y no realiza Rebase automático."
                )
            ),

            AyudaEmergente(
                self.boton_push,
                (
                    "Push\n\n"
                    "Envía al repositorio remoto los commits que existen "
                    "solamente en tu repositorio local.\n\n"
                    "Antes de enviar, Gestor Git ejecuta Fetch nuevamente "
                    "para comprobar que el remoto no haya cambiado.\n\n"
                    "Nunca utiliza Push forzado."
                )
            ),

            AyudaEmergente(
                self.boton_configurar_github,
                (
                    "Configurar GitHub\n\n"
                    "Conecta este repositorio local con un repositorio "
                    "vacío de GitHub configurando el remoto origin.\n\n"
                    "Esta operación solamente modifica la configuración "
                    "local de Git.\n\n"
                    "No envía commits.\n"
                    "No descarga commits.\n"
                    "No almacena credenciales.\n\n"
                    "Después debes ejecutar Fetch y posteriormente "
                    "Push cuando sea seguro."
                )
            ),

            AyudaEmergente(
                self.boton_seleccionar_todo,
                (
                    "Seleccionar todo\n\n"
                    "Selecciona todas las filas visibles de la tabla.\n\n"
                    "Todavía no modifica Git. Solo cambia la selección "
                    "visual de archivos."
                )
            ),

            AyudaEmergente(
                self.boton_preparar,
                (
                    "Preparar seleccionados\n\n"
                    "Equivale conceptualmente a usar git add.\n\n"
                    "Los cambios seleccionados pasan al área preparada "
                    "(staging/index) y quedarán incluidos en el próximo commit.\n\n"
                    "Todavía no se crea ningún commit."
                )
            ),

            AyudaEmergente(
                self.boton_actualizar_preparados,
                (
                    "Actualizar preparados\n\n"
                    "Actualiza el área preparada con la versión actual "
                    "completa de los archivos seleccionados.\n\n"
                    "Úsalo cuando un archivo aparece como:\n"
                    "'preparado y vuelto a modificar'.\n\n"
                    "Equivale a volver a ejecutar git add sobre ese archivo.\n\n"
                    "No modifica ni elimina el archivo del disco.\n"
                    "No crea un commit.\n\n"
                    "Si preparaste solamente parte del archivo utilizando "
                    "otra herramienta, esta acción incluirá también los "
                    "cambios restantes de la versión actual."
                )
            ),

            AyudaEmergente(
                self.boton_quitar_preparados,
                (
                    "Quitar de preparados\n\n"
                    "Saca los archivos seleccionados del área preparada.\n\n"
                    "NO elimina los archivos y NO descarta sus modificaciones.\n\n"
                    "Simplemente deja esos cambios fuera del próximo commit."
                )
            ),

            AyudaEmergente(
                self.boton_crear_commit,
                (
                    "Crear commit\n\n"
                    "Guarda una instantánea local de todos los cambios "
                    "que están preparados.\n\n"
                    "Un commit pertenece primero a tu repositorio local.\n\n"
                    "Crear commit NO envía nada al remoto. Para eso existe Push."
                )
            )
        ]

    def actualizar_apariencia_estado(
        self,
        *_argumentos
    ):
        """
        Cambia el color de la barra inferior según
        el tipo de mensaje mostrado.

        Los mensajes de éxito se evalúan antes que
        las advertencias para evitar que frases como
        "No hay cambios pendientes" aparezcan en amarillo.
        """

        texto = (
            self.variable_estado.get().lower()
        )

        # Estado neutro.
        fondo = "#E2E8F0"
        texto_color = "#334155"

        palabras_error = (
            "error",
            "falló",
            "no realizado",
            "no fue posible",
            "conflicto",
            "bloqueado"
        )

        palabras_proceso = (
            "consultando",
            "analizando",
            "en curso",
            "preparando",
            "creando",
            "verificando"
        )

        palabras_exito = (
            "completado",
            "correctamente",
            "repositorio limpio",
            "sincronizada",
            "git disponible"
        )

        palabras_advertencia = (
            "pendiente",
            "diverg",
            "por descargar",
            "por enviar"
        )

        if any(
            palabra in texto
            for palabra in palabras_error
        ):
            fondo = "#FEE2E2"
            texto_color = "#991B1B"

        elif any(
            palabra in texto
            for palabra in palabras_proceso
        ):
            fondo = "#DBEAFE"
            texto_color = "#1E40AF"

        elif any(
            palabra in texto
            for palabra in palabras_exito
        ):
            fondo = "#DCFCE7"
            texto_color = "#166534"

        elif any(
            palabra in texto
            for palabra in palabras_advertencia
        ):
            fondo = "#FEF3C7"
            texto_color = "#92400E"

        self.etiqueta_estado.config(
            background=fondo,
            foreground=texto_color
        )

    def verificar_git(self):
        """
        Verifica que git.exe esté disponible.
        """

        if self.servicio_git.git_disponible():
            resultado = self.servicio_git.obtener_version()

            if resultado.exitoso:
                self.variable_estado.set(
                    f"Git disponible: {resultado.salida}"
                )
            else:
                self.variable_estado.set(
                    "Git fue encontrado, pero no pudo ejecutarse."
                )

            return

        self.variable_estado.set(
            "Git no fue encontrado."
        )

        self.boton_seleccionar.config(
            state=tk.DISABLED
        )

        messagebox.showerror(
            "Git no disponible",
            (
                "No fue posible encontrar git.exe.\n\n"
                "Verifique que Git esté instalado y disponible "
                "en el PATH de Windows."
            )
        )

    def seleccionar_repositorio(self):
        """
        Permite seleccionar un repositorio.
        """

        if self.operacion_remota_en_curso:
            return

        ruta_seleccionada = filedialog.askdirectory(
            title="Seleccionar repositorio Git"
        )

        if not ruta_seleccionada:
            return

        self.cargar_repositorio(
            ruta_seleccionada,
            reiniciar_fetch=True,
            guardar_configuracion=True
        )

    def cargar_repositorio_recordado(self):
        """
        Carga automáticamente el último repositorio seleccionado.

        Solamente carga el estado LOCAL del repositorio:
        no ejecuta Fetch, Pull ni Push.
        """

        if not self.servicio_git.git_disponible():
            return

        resultado = (
            self.servicio_configuracion.cargar_ultimo_repositorio()
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No se pudo cargar el repositorio recordado. "
                "Seleccione un repositorio manualmente."
            )

            return

        if not resultado.ruta_repositorio:
            return

        self.cargar_repositorio(
            resultado.ruta_repositorio
        )

        self.variable_estado.set(
            "Repositorio recordado cargado. "
            "Pulse Fetch para consultar el remoto."
        )

    def cargar_repositorio(
        self,
        ruta_repositorio,
        reiniciar_fetch=False,
        guardar_configuracion=False
    ):
        """
        Valida y carga un repositorio.

        Cuando reiniciar_fetch es True se exige un nuevo Fetch
        antes de habilitar Pull o Push.

        Cuando guardar_configuracion es True se recuerda la ruta
        en config.json para el próximo inicio; un fallo de
        guardado no impide seguir trabajando.
        """

        self.variable_estado.set(
            "Analizando repositorio..."
        )

        self.ventana_principal.update_idletasks()

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            self.limpiar_repositorio()

            messagebox.showwarning(
                "Repositorio no válido",
                estado.mensaje
            )

            self.variable_estado.set(
                estado.mensaje
            )

            return

        ruta_anterior = self.ruta_repositorio

        if (
            ruta_anterior
            and ruta_anterior != estado.ruta_raiz
        ):
            self.cerrar_historial()
            self.cerrar_configuracion_github()
            self.cerrar_detalle_commit()

        self.ruta_repositorio = estado.ruta_raiz

        self.remotos_repositorio = list(
            estado.remotos
        )

        if (
            reiniciar_fetch
            or ruta_anterior != self.ruta_repositorio
        ):
            self.fetch_exitoso_en_sesion = False

        self.variable_ruta.set(
            estado.ruta_raiz
        )

        self.variable_rama.set(
            estado.rama_actual
            if estado.rama_actual
            else "No determinada"
        )

        self.variable_remoto.set(
            ", ".join(estado.remotos)
            if estado.remotos
            else "Sin remoto"
        )

        self.variable_commits.set(
            "Sí"
            if estado.tiene_commits
            else "No"
        )

        self.boton_actualizar.config(
            state=tk.NORMAL
        )

        self.boton_historial.config(
            state=tk.NORMAL
        )

        self.boton_fetch.config(
            state=(
                tk.NORMAL
                if estado.remotos
                else tk.DISABLED
            )
        )

        self.boton_configurar_github.config(
            state=(
                tk.NORMAL
                if not estado.remotos
                else tk.DISABLED
            )
        )

        if not self.fetch_exitoso_en_sesion:
            self.variable_ultima_consulta.set(
                "Información local. Pulse Fetch para consultar el remoto."
            )

        self.cargar_cambios()

        # Esta consulta no accede a Internet.
        self.cargar_estado_sincronizacion_local()

        self.actualizar_historial_si_abierto()

        if guardar_configuracion:
            resultado_guardado = (
                self.servicio_configuracion.guardar_ultimo_repositorio(
                    self.ruta_repositorio
                )
            )

            if not resultado_guardado.exitoso:
                self.variable_estado.set(
                    "El repositorio fue cargado, pero no fue posible "
                    "recordarlo para el próximo inicio."
                )

    def cargar_cambios(self):
        """
        Consulta y muestra los archivos pendientes.
        """

        self.limpiar_tabla()

        if not self.ruta_repositorio:
            return

        resultado = self.servicio_git.obtener_cambios(
            self.ruta_repositorio
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible consultar los cambios."
            )

            self.hay_cambios_pendientes = True

            self.deshabilitar_botones_de_archivos()

            self.actualizar_estado_botones_sincronizacion()

            messagebox.showerror(
                "Error al consultar Git",
                resultado.error
            )

            return

        for cambio in resultado.cambios:
            if not cambio.preparado:
                texto_preparado = "No"
            elif cambio.requiere_actualizar_preparado:
                texto_preparado = "Sí (hay cambios nuevos)"
            else:
                texto_preparado = "Sí"

            identificador = self.tabla_cambios.insert(
                "",
                tk.END,
                values=(
                    cambio.descripcion,
                    texto_preparado,
                    cambio.ruta
                )
            )

            self.cambios_por_elemento[
                identificador
            ] = cambio

        cantidad = len(
            resultado.cambios
        )

        self.hay_cambios_pendientes = (
            cantidad > 0
        )

        self.actualizar_estado_botones_archivos()

        self.actualizar_estado_botones_sincronizacion()

        if cantidad == 0:
            self.variable_estado.set(
                "Repositorio limpio. No hay cambios pendientes."
            )

        elif cantidad == 1:
            self.variable_estado.set(
                "1 archivo con cambios pendientes."
            )

        else:
            self.variable_estado.set(
                f"{cantidad} archivos con cambios pendientes."
            )

    def cargar_estado_sincronizacion_local(self):
        """
        Muestra el estado utilizando únicamente
        las referencias disponibles localmente.

        No realiza conexión de red.
        """

        if not self.ruta_repositorio:
            self.limpiar_estado_sincronizacion()
            return

        estado = self.servicio_git.obtener_estado_sincronizacion(
            self.ruta_repositorio
        )

        self.aplicar_estado_sincronizacion(
            estado
        )

    def aplicar_estado_sincronizacion(
        self,
        estado
    ):
        """
        Copia EstadoSincronizacion a la interfaz.
        """

        self.estado_sincronizacion_actual = estado

        if not estado.exitoso:
            self.variable_upstream.set("-")
            self.variable_rama_remota.set("-")
            self.variable_por_subir.set("-")
            self.variable_por_bajar.set("-")

            self.variable_estado_sincronizacion.set(
                estado.error
            )

            self.actualizar_estado_botones_sincronizacion()

            return

        self.variable_upstream.set(
            "Configurado"
            if estado.upstream_configurado
            else "No configurado"
        )

        texto_rama_remota = (
            estado.rama_remota
        )

        if not estado.rama_remota_existe:
            texto_rama_remota += (
                " (no existe)"
            )

        self.variable_rama_remota.set(
            texto_rama_remota
        )

        self.variable_por_subir.set(
            str(
                estado.commits_por_subir
            )
        )

        self.variable_por_bajar.set(
            str(
                estado.commits_por_bajar
            )
        )

        self.variable_estado_sincronizacion.set(
            estado.mensaje
        )

        self.actualizar_estado_botones_sincronizacion()

    def actualizar_repositorio(self):
        """
        Vuelve a consultar el repositorio seleccionado.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        self.cargar_repositorio(
            self.ruta_repositorio,
            reiniciar_fetch=False
        )

    # =============================================================
    # HISTORIAL DE COMMITS
    # =============================================================

    def abrir_historial(self):
        """
        Abre una ventana de solo lectura con los commits locales.
        """

        if not self.ruta_repositorio:
            return

        if (
            self.ventana_historial is not None
            and self.ventana_historial.winfo_exists()
        ):
            self.ventana_historial.deiconify()
            self.ventana_historial.lift()
            self.ventana_historial.focus_force()
            self.cargar_historial()
            return

        self.crear_ventana_historial()
        self.cargar_historial()

    def crear_ventana_historial(self):
        """
        Construye la ventana, los filtros y la tabla del historial.
        """

        self.ventana_historial = tk.Toplevel(
            self.ventana_principal
        )

        self.ventana_historial.title(
            "Historial de commits - Gestor Git"
        )

        self.ventana_historial.geometry(
            "1180x640"
        )

        self.ventana_historial.minsize(
            900,
            480
        )

        self.ventana_historial.transient(
            self.ventana_principal
        )

        self.ventana_historial.protocol(
            "WM_DELETE_WINDOW",
            self.cerrar_historial
        )

        marco_historial = ttk.Frame(
            self.ventana_historial,
            padding=15
        )

        marco_historial.pack(
            fill=tk.BOTH,
            expand=True
        )

        marco_historial.columnconfigure(
            0,
            weight=1
        )

        marco_historial.rowconfigure(
            3,
            weight=1
        )

        ttk.Label(
            marco_historial,
            text="Historial de commits",
            style="Titulo.TLabel"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ttk.Label(
            marco_historial,
            text=(
                "Vista de solo lectura del historial local. "
                "Puedes filtrar por archivo y por un rango de fechas. "
                "No ejecuta Checkout, Reset, Revert, Pull ni Push."
            ),
            style="AyudaVisible.TLabel",
            wraplength=1050
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 10)
        )

        # ---------------------------------------------------------
        # Filtros del historial
        # ---------------------------------------------------------

        marco_filtros = ttk.LabelFrame(
            marco_historial,
            text="Filtros",
            padding=10
        )

        marco_filtros.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        marco_filtros.columnconfigure(
            1,
            weight=1
        )

        self.variable_filtro_archivo_historial = tk.StringVar()
        self.variable_fecha_desde_historial = tk.StringVar()
        self.variable_fecha_hasta_historial = tk.StringVar()

        ttk.Label(
            marco_filtros,
            text="Archivo contiene:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 6)
        )

        self.entrada_filtro_archivo_historial = ttk.Entry(
            marco_filtros,
            textvariable=self.variable_filtro_archivo_historial,
            width=34
        )

        self.entrada_filtro_archivo_historial.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 16)
        )

        ttk.Label(
            marco_filtros,
            text="Desde:"
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 6)
        )

        self.entrada_fecha_desde_historial = ttk.Entry(
            marco_filtros,
            textvariable=self.variable_fecha_desde_historial,
            width=12
        )

        self.entrada_fecha_desde_historial.grid(
            row=0,
            column=3,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_filtros,
            text="dd/mm/aaaa"
        ).grid(
            row=0,
            column=4,
            sticky="w",
            padx=(0, 16)
        )

        ttk.Label(
            marco_filtros,
            text="Hasta:"
        ).grid(
            row=0,
            column=5,
            sticky="w",
            padx=(0, 6)
        )

        self.entrada_fecha_hasta_historial = ttk.Entry(
            marco_filtros,
            textvariable=self.variable_fecha_hasta_historial,
            width=12
        )

        self.entrada_fecha_hasta_historial.grid(
            row=0,
            column=6,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_filtros,
            text="dd/mm/aaaa"
        ).grid(
            row=0,
            column=7,
            sticky="w",
            padx=(0, 16)
        )

        self.boton_aplicar_filtros_historial = ttk.Button(
            marco_filtros,
            text="Aplicar filtros",
            command=self.cargar_historial,
            style="Accion.TButton"
        )

        self.boton_aplicar_filtros_historial.grid(
            row=0,
            column=8,
            sticky="e"
        )

        self.boton_limpiar_filtros_historial = ttk.Button(
            marco_filtros,
            text="Limpiar",
            command=self.limpiar_filtros_historial,
            style="Accion.TButton"
        )

        self.boton_limpiar_filtros_historial.grid(
            row=0,
            column=9,
            sticky="e",
            padx=(8, 0)
        )

        # Presionar Enter en cualquiera de los filtros aplica la consulta.
        for entrada in (
            self.entrada_filtro_archivo_historial,
            self.entrada_fecha_desde_historial,
            self.entrada_fecha_hasta_historial
        ):
            entrada.bind(
                "<Return>",
                lambda _evento: self.cargar_historial()
            )

        self.ayuda_filtro_archivo_historial = AyudaEmergente(
            self.entrada_filtro_archivo_historial,
            (
                "Filtro por archivo\n\n"
                "Escribe todo o parte del nombre de un archivo.\n\n"
                "Por ejemplo: FINI004, .pls o Paquetes.\n\n"
                "La búsqueda no distingue mayúsculas de minúsculas "
                "y solamente muestra commits que modificaron archivos "
                "cuyo nombre o ruta contiene ese texto."
            )
        )

        self.ayuda_fecha_desde_historial = AyudaEmergente(
            self.entrada_fecha_desde_historial,
            (
                "Fecha Desde\n\n"
                "Muestra commits realizados a partir de esta fecha, "
                "incluyéndola.\n\n"
                "Formato: dd/mm/aaaa.\n"
                "Puedes dejarla vacía."
            )
        )

        self.ayuda_fecha_hasta_historial = AyudaEmergente(
            self.entrada_fecha_hasta_historial,
            (
                "Fecha Hasta\n\n"
                "Muestra commits realizados hasta esta fecha, "
                "incluyéndola.\n\n"
                "Formato: dd/mm/aaaa.\n"
                "Puedes dejarla vacía."
            )
        )

        self.ayuda_aplicar_filtros_historial = AyudaEmergente(
            self.boton_aplicar_filtros_historial,
            (
                "Aplicar filtros\n\n"
                "Consulta nuevamente el historial local utilizando "
                "el archivo y las fechas indicadas.\n\n"
                "Los filtros se combinan: si completas varios, "
                "el commit debe cumplirlos todos."
            )
        )

        self.ayuda_limpiar_filtros_historial = AyudaEmergente(
            self.boton_limpiar_filtros_historial,
            (
                "Limpiar filtros\n\n"
                "Vacía Archivo, Desde y Hasta y vuelve a mostrar "
                "el historial sin filtros."
            )
        )

        # ---------------------------------------------------------
        # Tabla del historial
        # ---------------------------------------------------------

        marco_tabla_historial = ttk.Frame(
            marco_historial
        )

        marco_tabla_historial.grid(
            row=3,
            column=0,
            sticky="nsew"
        )

        marco_tabla_historial.columnconfigure(
            0,
            weight=1
        )

        marco_tabla_historial.rowconfigure(
            0,
            weight=1
        )

        columnas = (
            "hash",
            "fecha",
            "autor",
            "mensaje"
        )

        self.tabla_historial = ttk.Treeview(
            marco_tabla_historial,
            columns=columnas,
            show="headings",
            selectmode="browse"
        )

        self.tabla_historial.heading(
            "hash",
            text="Hash"
        )

        self.tabla_historial.heading(
            "fecha",
            text="Fecha ↓"
        )

        self.tabla_historial.heading(
            "autor",
            text="Autor"
        )

        self.tabla_historial.heading(
            "mensaje",
            text="Mensaje"
        )

        self.tabla_historial.column(
            "hash",
            width=100,
            minwidth=85,
            stretch=False
        )

        self.tabla_historial.column(
            "fecha",
            width=155,
            minwidth=140,
            stretch=False
        )

        self.tabla_historial.column(
            "autor",
            width=190,
            minwidth=140
        )

        self.tabla_historial.column(
            "mensaje",
            width=540,
            minwidth=250
        )

        self.tabla_historial.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        barra_vertical = ttk.Scrollbar(
            marco_tabla_historial,
            orient=tk.VERTICAL,
            command=self.tabla_historial.yview
        )

        barra_vertical.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        barra_horizontal = ttk.Scrollbar(
            marco_tabla_historial,
            orient=tk.HORIZONTAL,
            command=self.tabla_historial.xview
        )

        barra_horizontal.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        self.tabla_historial.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set
        )

        self.tabla_historial.bind(
            "<<TreeviewSelect>>",
            self.actualizar_estado_boton_ver_cambios
        )

        self.tabla_historial.bind(
            "<Double-1>",
            self.abrir_detalle_commit_seleccionado
        )

        marco_inferior = ttk.Frame(
            marco_historial
        )

        marco_inferior.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        marco_inferior.columnconfigure(
            0,
            weight=1
        )

        self.variable_estado_historial = tk.StringVar(
            value="Listo para consultar el historial."
        )

        ttk.Label(
            marco_inferior,
            textvariable=self.variable_estado_historial
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.boton_ver_cambios_historial = ttk.Button(
            marco_inferior,
            text="Ver cambios...",
            command=self.abrir_detalle_commit_seleccionado,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_ver_cambios_historial.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(10, 0)
        )

        self.boton_exportar_csv_historial = ttk.Button(
            marco_inferior,
            text="Exportar CSV",
            command=self.exportar_historial_csv,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_exportar_csv_historial.grid(
            row=0,
            column=2,
            sticky="e",
            padx=(8, 0)
        )

        self.boton_exportar_txt_historial = ttk.Button(
            marco_inferior,
            text="Exportar TXT",
            command=self.exportar_historial_txt,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_exportar_txt_historial.grid(
            row=0,
            column=3,
            sticky="e",
            padx=(8, 0)
        )

        self.boton_actualizar_historial = ttk.Button(
            marco_inferior,
            text="Actualizar historial",
            command=self.cargar_historial,
            style="Accion.TButton"
        )

        self.boton_actualizar_historial.grid(
            row=0,
            column=4,
            sticky="e",
            padx=(8, 0)
        )

        self.ayuda_ver_cambios_historial = AyudaEmergente(
            self.boton_ver_cambios_historial,
            (
                "Ver cambios...\n\n"
                "Muestra los cambios de archivos introducidos "
                "por el commit seleccionado.\n\n"
                "Es una vista de solo lectura: no modifica archivos, "
                "commits ni ramas, y no consulta el remoto."
            )
        )

        self.ayuda_exportar_csv_historial = AyudaEmergente(
            self.boton_exportar_csv_historial,
            (
                "Exportar CSV\n\n"
                "Guarda exactamente los commits visibles en un archivo CSV.\n\n"
                "Incluye hash completo, hash corto, fecha ISO, autor, correo "
                "y mensaje.\n\n"
                "Se utiliza UTF-8 y un formato amigable para Excel en Windows."
            )
        )

        self.ayuda_exportar_txt_historial = AyudaEmergente(
            self.boton_exportar_txt_historial,
            (
                "Exportar TXT\n\n"
                "Guarda exactamente los commits visibles en un archivo de texto.\n\n"
                "Además deja registrados el repositorio y los filtros aplicados "
                "para facilitar análisis o documentación posterior."
            )
        )

        self.ayuda_actualizar_historial = AyudaEmergente(
            self.boton_actualizar_historial,
            (
                "Actualizar historial\n\n"
                "Vuelve a ejecutar la consulta local manteniendo "
                "los filtros actuales.\n\n"
                "No consulta el remoto y no modifica el repositorio."
            )
        )

        self.entrada_filtro_archivo_historial.focus_set()

    def cargar_historial(self):
        """
        Consulta y muestra hasta 100 commits aplicando los filtros visibles.
        """

        if not self.ruta_repositorio:
            return

        if self.tabla_historial is None:
            return

        filtro_archivo = ""
        texto_desde = ""
        texto_hasta = ""

        if self.variable_filtro_archivo_historial is not None:
            filtro_archivo = (
                self.variable_filtro_archivo_historial.get().strip()
            )

        if self.variable_fecha_desde_historial is not None:
            texto_desde = (
                self.variable_fecha_desde_historial.get().strip()
            )

        if self.variable_fecha_hasta_historial is not None:
            texto_hasta = (
                self.variable_fecha_hasta_historial.get().strip()
            )

        fecha_desde = self._convertir_fecha_filtro_historial(
            texto_desde,
            "Desde"
        )

        if fecha_desde is None:
            return

        fecha_hasta = self._convertir_fecha_filtro_historial(
            texto_hasta,
            "Hasta"
        )

        if fecha_hasta is None:
            return

        if (
            fecha_desde
            and fecha_hasta
            and fecha_desde > fecha_hasta
        ):
            if self.variable_estado_historial is not None:
                self.variable_estado_historial.set(
                    "El rango de fechas no es válido."
                )

            messagebox.showwarning(
                "Rango de fechas no válido",
                (
                    "La fecha Desde no puede ser posterior "
                    "a la fecha Hasta."
                ),
                parent=self.ventana_historial
            )

            return

        for elemento in self.tabla_historial.get_children():
            self.tabla_historial.delete(
                elemento
            )

        self.commits_historial_actual = []
        self.actualizar_estado_botones_exportacion_historial()

        # Al recargar, las filas anteriores dejan de existir:
        # se libera la relación fila -> commit y se deshabilita
        # el botón Ver cambios... hasta que haya una selección.
        self.commits_historial_por_elemento.clear()
        self.actualizar_estado_boton_ver_cambios()

        if self.variable_estado_historial is not None:
            self.variable_estado_historial.set(
                "Consultando historial local..."
            )

        resultado = self.servicio_historial.obtener_historial_commits(
            self.ruta_repositorio,
            limite=100,
            filtro_archivo=filtro_archivo,
            fecha_desde=(
                fecha_desde.isoformat()
                if fecha_desde
                else ""
            ),
            fecha_hasta=(
                fecha_hasta.isoformat()
                if fecha_hasta
                else ""
            )
        )

        if not resultado.exitoso:
            if self.variable_estado_historial is not None:
                self.variable_estado_historial.set(
                    "No fue posible consultar el historial."
                )

            messagebox.showerror(
                "Error al consultar historial",
                resultado.error,
                parent=self.ventana_historial
            )

            return

        self.commits_historial_actual = list(
            resultado.commits
        )

        self.filtros_historial_aplicados = {
            "archivo": filtro_archivo,
            "desde": texto_desde,
            "hasta": texto_hasta
        }

        self.actualizar_estado_botones_exportacion_historial()

        for commit in resultado.commits:
            identificador = self.tabla_historial.insert(
                "",
                tk.END,
                values=(
                    commit.hash_corto,
                    self._formatear_fecha_historial(
                        commit.fecha_iso
                    ),
                    commit.autor,
                    commit.mensaje
                )
            )

            # Relaciona la fila visible con el CommitGit para que
            # la ventana de detalle no tenga que volver a consultar
            # el historial.
            self.commits_historial_por_elemento[
                identificador
            ] = commit

        cantidad = len(
            resultado.commits
        )

        hay_filtros = bool(
            filtro_archivo
            or fecha_desde
            or fecha_hasta
        )

        if self.variable_estado_historial is not None:
            if cantidad == 0:
                if hay_filtros:
                    self.variable_estado_historial.set(
                        "No se encontraron commits que cumplan los filtros."
                    )
                else:
                    self.variable_estado_historial.set(
                        "El repositorio todavía no tiene commits."
                    )

            elif cantidad == 1:
                if hay_filtros:
                    self.variable_estado_historial.set(
                        "Se muestra 1 commit que cumple los filtros."
                    )
                else:
                    self.variable_estado_historial.set(
                        "Se muestra 1 commit."
                    )

            else:
                if hay_filtros:
                    self.variable_estado_historial.set(
                        f"Se muestran {cantidad} commits que cumplen los filtros."
                    )
                else:
                    self.variable_estado_historial.set(
                        f"Se muestran {cantidad} commits, del más reciente al más antiguo."
                    )

    def limpiar_filtros_historial(self):
        """
        Vacía todos los filtros y vuelve a cargar el historial.
        """

        if self.variable_filtro_archivo_historial is not None:
            self.variable_filtro_archivo_historial.set("")

        if self.variable_fecha_desde_historial is not None:
            self.variable_fecha_desde_historial.set("")

        if self.variable_fecha_hasta_historial is not None:
            self.variable_fecha_hasta_historial.set("")

        self.cargar_historial()

        if hasattr(
            self,
            "entrada_filtro_archivo_historial"
        ):
            self.entrada_filtro_archivo_historial.focus_set()

    def actualizar_estado_botones_exportacion_historial(self):
        """
        Habilita exportar solamente cuando existen commits visibles.
        """

        estado = (
            tk.NORMAL
            if self.commits_historial_actual
            else tk.DISABLED
        )

        if self.boton_exportar_csv_historial is not None:
            try:
                self.boton_exportar_csv_historial.config(
                    state=estado
                )
            except tk.TclError:
                pass

        if self.boton_exportar_txt_historial is not None:
            try:
                self.boton_exportar_txt_historial.config(
                    state=estado
                )
            except tk.TclError:
                pass

    def exportar_historial_csv(self):
        """
        Guarda exactamente los commits visibles en un archivo CSV.
        """

        if not self.commits_historial_actual:
            messagebox.showinfo(
                "Nada para exportar",
                "No hay commits visibles para exportar.",
                parent=self.ventana_historial
            )
            return

        ruta_destino = filedialog.asksaveasfilename(
            parent=self.ventana_historial,
            title="Guardar historial como CSV",
            defaultextension=".csv",
            filetypes=(
                ("Archivo CSV", "*.csv"),
                ("Todos los archivos", "*.*")
            ),
            initialfile=self._crear_nombre_archivo_historial(
                "csv"
            )
        )

        if not ruta_destino:
            return

        resultado = self.servicio_exportacion_historial.exportar_csv(
            ruta_destino,
            self.commits_historial_actual
        )

        self._procesar_resultado_exportacion_historial(
            resultado,
            "CSV"
        )

    def exportar_historial_txt(self):
        """
        Guarda exactamente los commits visibles en un archivo TXT.
        """

        if not self.commits_historial_actual:
            messagebox.showinfo(
                "Nada para exportar",
                "No hay commits visibles para exportar.",
                parent=self.ventana_historial
            )
            return

        ruta_destino = filedialog.asksaveasfilename(
            parent=self.ventana_historial,
            title="Guardar historial como TXT",
            defaultextension=".txt",
            filetypes=(
                ("Archivo de texto", "*.txt"),
                ("Todos los archivos", "*.*")
            ),
            initialfile=self._crear_nombre_archivo_historial(
                "txt"
            )
        )

        if not ruta_destino:
            return

        resultado = self.servicio_exportacion_historial.exportar_txt(
            ruta_destino,
            self.commits_historial_actual,
            ruta_repositorio=self.ruta_repositorio,
            filtro_archivo=self.filtros_historial_aplicados.get(
                "archivo",
                ""
            ),
            fecha_desde=self.filtros_historial_aplicados.get(
                "desde",
                ""
            ),
            fecha_hasta=self.filtros_historial_aplicados.get(
                "hasta",
                ""
            )
        )

        self._procesar_resultado_exportacion_historial(
            resultado,
            "TXT"
        )

    def _procesar_resultado_exportacion_historial(
        self,
        resultado,
        formato
    ):
        """
        Muestra el resultado de una exportación sin modificar Git.
        """

        if not resultado.exitoso:
            if self.variable_estado_historial is not None:
                self.variable_estado_historial.set(
                    f"No fue posible exportar el historial a {formato}."
                )

            messagebox.showerror(
                "Error al exportar historial",
                resultado.error,
                parent=self.ventana_historial
            )
            return

        if self.variable_estado_historial is not None:
            self.variable_estado_historial.set(
                f"Historial exportado correctamente a {formato}."
            )

        messagebox.showinfo(
            "Historial exportado",
            (
                f"El historial visible se exportó correctamente a {formato}.\n\n"
                f"Archivo:\n{resultado.ruta_archivo}"
            ),
            parent=self.ventana_historial
        )

    def _crear_nombre_archivo_historial(self, extension):
        """
        Crea un nombre sugerido seguro para Windows.
        """

        nombre_repositorio = (
            Path(self.ruta_repositorio).name
            if self.ruta_repositorio
            else "repositorio"
        )

        for caracter in '<>:"/\\|?*':
            nombre_repositorio = nombre_repositorio.replace(
                caracter,
                "_"
            )

        momento = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        return (
            f"historial_{nombre_repositorio}_{momento}.{extension}"
        )

    @staticmethod
    def _convertir_fecha_filtro_historial(
        texto_fecha,
        nombre_campo
    ):
        """
        Convierte dd/mm/aaaa a date para validar los filtros visuales.

        Devuelve una cadena vacía cuando el campo está vacío y None
        cuando el usuario escribió una fecha inválida.
        """

        texto_fecha = texto_fecha.strip()

        if not texto_fecha:
            return ""

        try:
            return datetime.strptime(
                texto_fecha,
                "%d/%m/%Y"
            ).date()

        except ValueError:
            messagebox.showwarning(
                "Fecha no válida",
                (
                    f"La fecha {nombre_campo} no es válida.\n\n"
                    "Utilice el formato dd/mm/aaaa.\n"
                    "Ejemplo: 18/08/2026"
                )
            )

            return None

    def actualizar_historial_si_abierto(self):
        """
        Refresca el historial únicamente si su ventana está abierta.
        """

        if self.ventana_historial is None:
            return

        try:
            existe = self.ventana_historial.winfo_exists()
        except tk.TclError:
            existe = False

        if not existe:
            return

        self.cargar_historial()

    def cerrar_historial(self):
        """
        Cierra y libera los controles asociados al historial.
        """

        if self.ventana_historial is not None:
            try:
                if self.ventana_historial.winfo_exists():
                    self.ventana_historial.destroy()
            except tk.TclError:
                pass

        self.ventana_historial = None
        self.tabla_historial = None
        self.variable_estado_historial = None
        self.variable_filtro_archivo_historial = None
        self.variable_fecha_desde_historial = None
        self.variable_fecha_hasta_historial = None
        self.boton_exportar_csv_historial = None
        self.boton_exportar_txt_historial = None
        self.boton_ver_cambios_historial = None
        self.commits_historial_actual = []
        self.commits_historial_por_elemento = {}
        self.filtros_historial_aplicados = {
            "archivo": "",
            "desde": "",
            "hasta": ""
        }

        # Si el historial se cierra, el detalle pierde su origen
        # visible y también se cierra.
        self.cerrar_detalle_commit()

    @staticmethod
    def _formatear_fecha_historial(fecha_iso):
        """
        Convierte la fecha ISO de Git a un formato compacto para la GUI.
        """

        if not fecha_iso:
            return "-"

        try:
            fecha = datetime.fromisoformat(
                fecha_iso
            )

            return fecha.strftime(
                "%d/%m/%Y %H:%M"
            )

        except ValueError:
            return fecha_iso

    # =============================================================
    # DETALLE DE CAMBIOS DE UN COMMIT
    # =============================================================

    def actualizar_estado_boton_ver_cambios(self, _evento=None):
        """
        Habilita Ver cambios... únicamente cuando existe un
        commit seleccionado en la tabla del historial.
        """

        hay_seleccion = False

        if self.tabla_historial is not None:
            try:
                hay_seleccion = bool(
                    self.tabla_historial.selection()
                )
            except tk.TclError:
                hay_seleccion = False

        estado = (
            tk.NORMAL
            if hay_seleccion
            else tk.DISABLED
        )

        if self.boton_ver_cambios_historial is not None:
            try:
                self.boton_ver_cambios_historial.config(
                    state=estado
                )
            except tk.TclError:
                pass

    def abrir_detalle_commit_seleccionado(self, _evento=None):
        """
        Abre los cambios del commit seleccionado en el historial.

        Utiliza la relación fila -> CommitGit almacenada al cargar
        la tabla y no vuelve a consultar el historial.
        """

        if self.tabla_historial is None:
            return

        try:
            seleccion = self.tabla_historial.selection()
        except tk.TclError:
            seleccion = ()

        if not seleccion:
            return

        commit = self.commits_historial_por_elemento.get(
            seleccion[0]
        )

        if commit is None:
            return

        self.abrir_detalle_commit(commit)

    def abrir_detalle_commit(self, commit):
        """
        Abre la ventana única con los cambios del commit.

        Si ya existe una ventana de detalle abierta, se destruye
        y se recrea con el commit solicitado.
        """

        self.cerrar_detalle_commit()

        self.crear_ventana_detalle_commit(commit)

    def crear_ventana_detalle_commit(self, commit):
        """
        Construye la ventana de solo lectura con el parche del commit.
        """

        self.ventana_detalle_commit = tk.Toplevel(
            self.ventana_principal
        )

        self.ventana_detalle_commit.title(
            "Cambios del commit - Gestor Git"
        )

        self.ventana_detalle_commit.geometry(
            "1100x700"
        )

        self.ventana_detalle_commit.minsize(
            850,
            500
        )

        self.ventana_detalle_commit.transient(
            self.ventana_principal
        )

        self.ventana_detalle_commit.protocol(
            "WM_DELETE_WINDOW",
            self.cerrar_detalle_commit
        )

        marco_detalle = ttk.Frame(
            self.ventana_detalle_commit,
            padding=15
        )

        marco_detalle.pack(
            fill=tk.BOTH,
            expand=True
        )

        marco_detalle.columnconfigure(
            0,
            weight=1
        )

        marco_detalle.rowconfigure(
            3,
            weight=1
        )

        ttk.Label(
            marco_detalle,
            text="Cambios del commit",
            style="Titulo.TLabel"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        advertencia = tk.Label(
            marco_detalle,
            text=(
                "Vista de solo lectura.\n"
                "Esta pantalla no modifica archivos, commits ni ramas."
            ),
            justify=tk.LEFT,
            anchor="w",
            background="#FEF2E0",
            foreground="#7C3A00",
            padx=10,
            pady=7,
            wraplength=1040
        )

        advertencia.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(10, 8)
        )

        marco_datos = ttk.Frame(
            marco_detalle
        )

        marco_datos.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        marco_datos.columnconfigure(
            1,
            weight=1
        )

        self._agregar_fila_dato(
            marco_datos,
            "Hash:",
            commit.hash_completo,
            0
        )

        self._agregar_fila_dato(
            marco_datos,
            "Fecha:",
            self._formatear_fecha_historial(
                commit.fecha_iso
            ),
            1
        )

        self._agregar_fila_dato(
            marco_datos,
            "Autor:",
            commit.autor,
            2
        )

        self._agregar_fila_dato(
            marco_datos,
            "Correo:",
            commit.correo,
            3
        )

        self._agregar_fila_dato(
            marco_datos,
            "Mensaje:",
            commit.mensaje,
            4
        )

        marco_diff = ttk.Frame(
            marco_detalle
        )

        marco_diff.grid(
            row=3,
            column=0,
            sticky="nsew"
        )

        marco_diff.columnconfigure(
            0,
            weight=1
        )

        marco_diff.rowconfigure(
            1,
            weight=1
        )

        ttk.Label(
            marco_diff,
            text="Cambios realizados",
            font=("Segoe UI", 10, "bold")
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 6)
        )

        self.texto_detalle_commit = tk.Text(
            marco_diff,
            wrap=tk.NONE,
            font=("Consolas", 10),
            relief=tk.SOLID,
            borderwidth=1,
            background="#FBFCFE",
            foreground="#1F2937"
        )

        self.texto_detalle_commit.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        barra_vertical_diff = ttk.Scrollbar(
            marco_diff,
            orient=tk.VERTICAL,
            command=self.texto_detalle_commit.yview
        )

        barra_vertical_diff.grid(
            row=1,
            column=1,
            sticky="ns"
        )

        barra_horizontal_diff = ttk.Scrollbar(
            marco_diff,
            orient=tk.HORIZONTAL,
            command=self.texto_detalle_commit.xview
        )

        barra_horizontal_diff.grid(
            row=2,
            column=0,
            sticky="ew"
        )

        self.texto_detalle_commit.configure(
            yscrollcommand=barra_vertical_diff.set,
            xscrollcommand=barra_horizontal_diff.set
        )

        self.texto_detalle_commit.tag_configure(
            "agregado",
            foreground="#1A7F37"
        )

        self.texto_detalle_commit.tag_configure(
            "eliminado",
            foreground="#CF222E"
        )

        self.texto_detalle_commit.tag_configure(
            "bloque",
            foreground="#0969DA",
            font=("Consolas", 10, "bold")
        )

        self.texto_detalle_commit.tag_configure(
            "tecnico",
            foreground="#57606A"
        )

        resultado = self.servicio_historial.obtener_cambios_commit(
            self.ruta_repositorio,
            commit.hash_completo
        )

        if not resultado.exitoso:
            self.texto_detalle_commit.insert(
                tk.END,
                (
                    "No fue posible obtener los cambios del commit.\n\n"
                    f"{resultado.error}"
                )
            )

        elif not resultado.salida:
            self.texto_detalle_commit.insert(
                tk.END,
                "Este commit no contiene cambios de archivos visibles."
            )

        else:
            self._mostrar_diff_en_texto(
                resultado.salida
            )

        self.texto_detalle_commit.config(
            state=tk.DISABLED
        )

        marco_botones_detalle = ttk.Frame(
            marco_detalle
        )

        marco_botones_detalle.grid(
            row=4,
            column=0,
            sticky="e",
            pady=(10, 0)
        )

        ttk.Button(
            marco_botones_detalle,
            text="Copiar diff",
            command=self.copiar_diff_commit,
            style="Accion.TButton"
        ).grid(
            row=0,
            column=0,
            sticky="e",
            padx=(0, 8)
        )

        ttk.Button(
            marco_botones_detalle,
            text="Cerrar",
            command=self.cerrar_detalle_commit,
            style="Accion.TButton"
        ).grid(
            row=0,
            column=1,
            sticky="e"
        )

    def _agregar_fila_dato(self, marco, nombre, valor, fila):
        """
        Agrega una fila nombre/valor en la ventana de detalle.
        """

        ttk.Label(
            marco,
            text=nombre,
            font=("Segoe UI", 9, "bold")
        ).grid(
            row=fila,
            column=0,
            sticky="nw",
            padx=(0, 8)
        )

        ttk.Label(
            marco,
            text=valor if valor else "-",
            wraplength=950
        ).grid(
            row=fila,
            column=1,
            sticky="w"
        )

    def _mostrar_diff_en_texto(self, salida):
        """
        Inserta el diff en el widget de texto con colores simples.

        La visualización se limita a
        self.limite_caracteres_detalle caracteres; la truncación
        es solamente visual y no modifica el repositorio.
        """

        texto = salida

        if len(texto) > self.limite_caracteres_detalle:
            texto = texto[:self.limite_caracteres_detalle]

        self.texto_detalle_commit.insert(
            tk.END,
            texto
        )

        lineas = texto.split("\n")

        # Posición inicial de cada línea dentro del texto insertado.
        posiciones = []
        posicion = 0

        for linea in lineas:
            posiciones.append(posicion)
            posicion += len(linea) + 1

        for numero, linea in enumerate(lineas, start=1):
            tag = self._tag_para_linea_diff(
                linea
            )

            if tag is None:
                continue

            inicio = posiciones[numero - 1]

            self.texto_detalle_commit.tag_add(
                tag,
                f"1.0+{inicio}c",
                f"1.0+{inicio + len(linea)}c"
            )

        if len(salida) > self.limite_caracteres_detalle:
            self.texto_detalle_commit.insert(
                tk.END,
                (
                    "\n\n[Vista truncada: el commit contiene más "
                    "cambios de los que se muestran en esta pantalla.]\n"
                )
            )

    @staticmethod
    def _tag_para_linea_diff(linea):
        """
        Devuelve el tag visual de una línea del diff o None.
        """

        if (
            linea.startswith("diff --git")
            or linea.startswith("---")
            or linea.startswith("+++")
        ):
            return "tecnico"

        if linea.startswith("@@"):
            return "bloque"

        if linea.startswith("+"):
            return "agregado"

        if linea.startswith("-"):
            return "eliminado"

        return None

    def copiar_diff_commit(self):
        """
        Copia el diff visible de la ventana al portapapeles.
        """

        if self.texto_detalle_commit is None:
            return

        try:
            # Solamente se copia el área del diff, no los metadatos
            # del commit mostrados arriba.
            contenido = self.texto_detalle_commit.get(
                "1.0",
                tk.END
            )

            self.ventana_detalle_commit.clipboard_clear()
            self.ventana_detalle_commit.clipboard_append(
                contenido.rstrip("\n")
            )
        except tk.TclError:
            pass

    def cerrar_detalle_commit(self):
        """
        Cierra la ventana de detalle si está abierta.
        """

        if self.ventana_detalle_commit is not None:
            try:
                if self.ventana_detalle_commit.winfo_exists():
                    self.ventana_detalle_commit.destroy()
            except tk.TclError:
                pass

        self.ventana_detalle_commit = None
        self.texto_detalle_commit = None

    # =============================================================
    # FETCH
    # =============================================================

    def iniciar_fetch(self):
        """
        Inicia Fetch en un hilo secundario.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        resultado_remoto = (
            self.servicio_git.obtener_remoto_sincronizacion(
                self.ruta_repositorio
            )
        )

        if not resultado_remoto.exitoso:
            messagebox.showerror(
                "No se puede ejecutar Fetch",
                resultado_remoto.error
            )

            return

        remoto = resultado_remoto.salida

        ruta_repositorio = (
            self.ruta_repositorio
        )

        self.operacion_remota_en_curso = True

        self.actualizar_controles_operacion_remota()

        self.variable_estado.set(
            f"Consultando remoto '{remoto}' mediante Fetch..."
        )

        self.variable_ultima_consulta.set(
            "Fetch en curso..."
        )

        hilo_fetch = threading.Thread(
            target=self.trabajo_fetch,
            args=(
                ruta_repositorio,
                remoto
            ),
            daemon=True
        )

        hilo_fetch.start()

    def trabajo_fetch(
        self,
        ruta_repositorio,
        remoto
    ):
        """
        Trabajo de Fetch ejecutado fuera del hilo principal.

        Este método nunca modifica controles Tkinter.
        """

        resultado_fetch = (
            self.servicio_git.ejecutar_fetch(
                ruta_repositorio,
                remoto
            )
        )

        estado_sincronizacion = None

        if resultado_fetch.exitoso:
            estado_sincronizacion = (
                self.servicio_git.obtener_estado_sincronizacion(
                    ruta_repositorio
                )
            )

        self.cola_resultados.put(
            (
                "fetch",
                ruta_repositorio,
                remoto,
                resultado_fetch,
                estado_sincronizacion
            )
        )

    # =============================================================
    # PULL
    # =============================================================

    def iniciar_pull(self):
        """
        Prepara y confirma un Pull seguro.

        La operación real se ejecuta en un hilo secundario.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        if not self.fetch_exitoso_en_sesion:
            messagebox.showinfo(
                "Fetch requerido",
                (
                    "Ejecute Fetch antes de realizar Pull.\n\n"
                    "Además, el motor de Pull realizará otro Fetch "
                    "inmediatamente antes de descargar los commits."
                )
            )

            return

        # Consultamos nuevamente el área de trabajo.
        resultado_cambios = self.servicio_git.obtener_cambios(
            self.ruta_repositorio
        )

        if not resultado_cambios.exitoso:
            messagebox.showerror(
                "No se puede realizar Pull",
                resultado_cambios.error
            )

            return

        if resultado_cambios.cambios:
            self.cargar_cambios()

            messagebox.showwarning(
                "Cambios pendientes",
                (
                    "No se realizará Pull porque existen cambios "
                    "sin commit en el repositorio.\n\n"
                    "La aplicación exige un área de trabajo "
                    "completamente limpia."
                )
            )

            return

        estado = self.servicio_git.obtener_estado_sincronizacion(
            self.ruta_repositorio
        )

        self.aplicar_estado_sincronizacion(
            estado
        )

        if not estado.exitoso:
            messagebox.showerror(
                "No se puede realizar Pull",
                estado.error
            )

            return

        if not estado.upstream_configurado:
            messagebox.showwarning(
                "Upstream no configurado",
                (
                    "No se puede realizar Pull porque la rama "
                    "actual no tiene upstream configurado."
                )
            )

            return

        if estado.divergente:
            messagebox.showwarning(
                "Ramas divergentes",
                (
                    "No se realizará Pull porque la rama local "
                    "y la rama remota han divergido.\n\n"
                    f"Por enviar: {estado.commits_por_subir}\n"
                    f"Por descargar: {estado.commits_por_bajar}\n\n"
                    "La aplicación no realizará Merge ni Rebase "
                    "automáticamente."
                )
            )

            return

        if estado.commits_por_subir > 0:
            messagebox.showwarning(
                "Hay commits locales",
                (
                    "No se realizará Pull porque existen commits "
                    "locales pendientes de enviar.\n\n"
                    f"Por enviar: {estado.commits_por_subir}"
                )
            )

            return

        if estado.commits_por_bajar <= 0:
            messagebox.showinfo(
                "Nada para descargar",
                "No hay commits remotos pendientes de descargar."
            )

            return

        mensaje_confirmacion = (
            self._crear_mensaje_confirmacion_pull(
                estado
            )
        )

        confirmado = messagebox.askyesno(
            "Confirmar Pull",
            mensaje_confirmacion
        )

        if not confirmado:
            return

        ruta_repositorio = (
            self.ruta_repositorio
        )

        self.operacion_remota_en_curso = True

        self.actualizar_controles_operacion_remota()

        self.variable_estado.set(
            "Verificando el remoto y ejecutando Pull..."
        )

        self.variable_ultima_consulta.set(
            (
                "Pull en curso. Se ejecutará Fetch nuevamente "
                "antes de descargar."
            )
        )

        hilo_pull = threading.Thread(
            target=self.trabajo_pull,
            args=(
                ruta_repositorio,
            ),
            daemon=True
        )

        hilo_pull.start()

    def trabajo_pull(
        self,
        ruta_repositorio
    ):
        """
        Ejecuta Pull seguro fuera del hilo principal.

        Este método nunca modifica controles Tkinter.
        """

        resultado_pull = (
            self.servicio_git.ejecutar_pull_seguro(
                ruta_repositorio
            )
        )

        resultado_fetch_final = None
        estado_sincronizacion = None

        if resultado_pull.exitoso:
            resultado_remoto = (
                self.servicio_git.obtener_remoto_sincronizacion(
                    ruta_repositorio
                )
            )

            if resultado_remoto.exitoso:
                resultado_fetch_final = (
                    self.servicio_git.ejecutar_fetch(
                        ruta_repositorio,
                        resultado_remoto.salida
                    )
                )

                if resultado_fetch_final.exitoso:
                    estado_sincronizacion = (
                        self.servicio_git.obtener_estado_sincronizacion(
                            ruta_repositorio
                        )
                    )

        self.cola_resultados.put(
            (
                "pull",
                ruta_repositorio,
                resultado_pull,
                resultado_fetch_final,
                estado_sincronizacion
            )
        )

    # =============================================================
    # PUSH
    # =============================================================

    def iniciar_push(self):
        """
        Prepara y confirma un Push seguro.

        La ejecución real se realiza en un hilo secundario.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        if not self.fetch_exitoso_en_sesion:
            messagebox.showinfo(
                "Fetch requerido",
                (
                    "Ejecute Fetch antes de realizar Push.\n\n"
                    "Además, el motor de Push realizará otro Fetch "
                    "inmediatamente antes de enviar los commits."
                )
            )

            return

        resultado_cambios = self.servicio_git.obtener_cambios(
            self.ruta_repositorio
        )

        if not resultado_cambios.exitoso:
            messagebox.showerror(
                "No se puede realizar Push",
                resultado_cambios.error
            )

            return

        if resultado_cambios.cambios:
            self.cargar_cambios()

            messagebox.showwarning(
                "Cambios pendientes",
                (
                    "No se realizará Push porque existen cambios "
                    "sin commit en el repositorio.\n\n"
                    "Nuestra aplicación exige un área de trabajo "
                    "limpia antes de enviar."
                )
            )

            return

        estado = self.servicio_git.obtener_estado_sincronizacion(
            self.ruta_repositorio
        )

        self.aplicar_estado_sincronizacion(
            estado
        )

        if not estado.exitoso:
            messagebox.showerror(
                "No se puede realizar Push",
                estado.error
            )

            return

        if estado.divergente:
            messagebox.showwarning(
                "Ramas divergentes",
                (
                    "No se realizará Push porque la rama local "
                    "y la rama remota han divergido.\n\n"
                    f"Por enviar: {estado.commits_por_subir}\n"
                    f"Por descargar: {estado.commits_por_bajar}"
                )
            )

            return

        if estado.commits_por_bajar > 0:
            messagebox.showwarning(
                "Hay commits por descargar",
                (
                    "No se realizará Push porque existen commits "
                    "remotos que primero deben descargarse.\n\n"
                    f"Por descargar: {estado.commits_por_bajar}"
                )
            )

            return

        if estado.commits_por_subir <= 0:
            messagebox.showinfo(
                "Nada para enviar",
                "No hay commits locales pendientes de enviar."
            )

            return

        mensaje_confirmacion = (
            self._crear_mensaje_confirmacion_push(
                estado
            )
        )

        confirmado = messagebox.askyesno(
            "Confirmar Push",
            mensaje_confirmacion
        )

        if not confirmado:
            return

        ruta_repositorio = (
            self.ruta_repositorio
        )

        self.operacion_remota_en_curso = True

        self.actualizar_controles_operacion_remota()

        self.variable_estado.set(
            "Verificando el remoto y ejecutando Push..."
        )

        self.variable_ultima_consulta.set(
            (
                "Push en curso. Se ejecutará Fetch nuevamente "
                "antes de enviar."
            )
        )

        hilo_push = threading.Thread(
            target=self.trabajo_push,
            args=(
                ruta_repositorio,
            ),
            daemon=True
        )

        hilo_push.start()

    def trabajo_push(
        self,
        ruta_repositorio
    ):
        """
        Ejecuta Push seguro fuera del hilo principal.

        Este método nunca modifica controles Tkinter.
        """

        resultado_push = (
            self.servicio_git.ejecutar_push_seguro(
                ruta_repositorio
            )
        )

        resultado_fetch_final = None
        estado_sincronizacion = None

        if resultado_push.exitoso:
            resultado_remoto = (
                self.servicio_git.obtener_remoto_sincronizacion(
                    ruta_repositorio
                )
            )

            if resultado_remoto.exitoso:
                resultado_fetch_final = (
                    self.servicio_git.ejecutar_fetch(
                        ruta_repositorio,
                        resultado_remoto.salida
                    )
                )

                if resultado_fetch_final.exitoso:
                    estado_sincronizacion = (
                        self.servicio_git.obtener_estado_sincronizacion(
                            ruta_repositorio
                        )
                    )

        self.cola_resultados.put(
            (
                "push",
                ruta_repositorio,
                resultado_push,
                resultado_fetch_final,
                estado_sincronizacion
            )
        )

    # =============================================================
    # COLA DE RESULTADOS
    # =============================================================

    def procesar_cola_resultados(self):
        """
        Procesa los resultados enviados por los hilos secundarios.
        """

        try:
            while True:
                elemento = (
                    self.cola_resultados.get_nowait()
                )

                tipo_operacion = elemento[0]

                if tipo_operacion == "fetch":
                    self.procesar_resultado_fetch(
                        *elemento[1:]
                    )

                elif tipo_operacion == "pull":
                    self.procesar_resultado_pull(
                        *elemento[1:]
                    )

                elif tipo_operacion == "push":
                    self.procesar_resultado_push(
                        *elemento[1:]
                    )

        except queue.Empty:
            pass

        self.ventana_principal.after(
            100,
            self.procesar_cola_resultados
        )

    def procesar_resultado_fetch(
        self,
        ruta_repositorio,
        remoto,
        resultado_fetch,
        estado_sincronizacion
    ):
        """
        Actualiza la interfaz cuando Fetch termina.
        """

        self.operacion_remota_en_curso = False

        self.actualizar_controles_operacion_remota()

        if ruta_repositorio != self.ruta_repositorio:
            return

        if not resultado_fetch.exitoso:
            self.fetch_exitoso_en_sesion = False

            self.variable_estado.set(
                "Fetch falló."
            )

            self.variable_ultima_consulta.set(
                "El último Fetch no pudo completarse."
            )

            self.actualizar_estado_botones_sincronizacion()

            detalle = (
                resultado_fetch.error
                if resultado_fetch.error
                else resultado_fetch.salida
            )

            messagebox.showerror(
                "Error durante Fetch",
                detalle
            )

            return

        self.fetch_exitoso_en_sesion = True

        if estado_sincronizacion is None:
            self.variable_estado.set(
                (
                    "Fetch completado, pero no se pudo "
                    "calcular el estado."
                )
            )

            self.actualizar_estado_botones_sincronizacion()

            return

        self.aplicar_estado_sincronizacion(
            estado_sincronizacion
        )

        self.variable_ultima_consulta.set(
            f"Fetch completado correctamente desde '{remoto}'."
        )

        if estado_sincronizacion.exitoso:
            self.variable_estado.set(
                "Fetch completado. Estado remoto actualizado."
            )
        else:
            self.variable_estado.set(
                (
                    "Fetch completado, pero el estado "
                    "no pudo calcularse."
                )
            )

    def procesar_resultado_pull(
        self,
        ruta_repositorio,
        resultado_pull,
        resultado_fetch_final,
        estado_sincronizacion
    ):
        """
        Actualiza la interfaz cuando Pull termina.
        """

        self.operacion_remota_en_curso = False

        self.actualizar_controles_operacion_remota()

        if ruta_repositorio != self.ruta_repositorio:
            return

        if not resultado_pull.exitoso:
            # Exigimos otro Fetch después de cualquier Pull fallido.
            self.fetch_exitoso_en_sesion = False

            # El motor pudo haber actualizado las referencias remotas
            # antes de decidir que Pull no era seguro.
            self.cargar_estado_sincronizacion_local()

            self.variable_estado.set(
                "Pull no realizado."
            )

            self.variable_ultima_consulta.set(
                (
                    "Pull no realizado. Ejecute Fetch nuevamente "
                    "antes de reintentarlo."
                )
            )

            detalle = (
                resultado_pull.error
                if resultado_pull.error
                else resultado_pull.salida
            )

            messagebox.showerror(
                "Pull no realizado",
                detalle
            )

            return

        # Pull fue exitoso.
        self.fetch_exitoso_en_sesion = True

        if (
            resultado_fetch_final is not None
            and resultado_fetch_final.exitoso
            and estado_sincronizacion is not None
        ):
            self.aplicar_estado_sincronizacion(
                estado_sincronizacion
            )

            self.variable_ultima_consulta.set(
                (
                    "Pull completado y estado remoto "
                    "verificado correctamente."
                )
            )

        else:
            self.cargar_estado_sincronizacion_local()

            self.variable_ultima_consulta.set(
                (
                    "Pull completado. No fue posible completar "
                    "la verificación remota posterior."
                )
            )

        # Los archivos y el historial pudieron cambiar
        # como consecuencia del fast-forward.
        self.cargar_cambios()
        self.actualizar_historial_si_abierto()

        self.variable_estado.set(
            "Pull completado correctamente mediante fast-forward."
        )

        messagebox.showinfo(
            "Pull completado",
            (
                "Los commits remotos fueron descargados correctamente.\n\n"
                "La actualización se realizó mediante fast-forward.\n\n"
                "No se creó ningún Merge automático.\n"
                "No se realizó ningún Rebase automático."
            )
        )

    def procesar_resultado_push(
        self,
        ruta_repositorio,
        resultado_push,
        resultado_fetch_final,
        estado_sincronizacion
    ):
        """
        Actualiza la interfaz cuando Push termina.
        """

        self.operacion_remota_en_curso = False

        self.actualizar_controles_operacion_remota()

        if ruta_repositorio != self.ruta_repositorio:
            return

        if not resultado_push.exitoso:
            # Después de un fallo exigimos otro Fetch
            # antes de permitir un nuevo Push.
            self.fetch_exitoso_en_sesion = False

            self.cargar_estado_sincronizacion_local()

            self.variable_estado.set(
                "Push no realizado."
            )

            self.variable_ultima_consulta.set(
                (
                    "Push no realizado. Ejecute Fetch nuevamente "
                    "antes de reintentarlo."
                )
            )

            detalle = (
                resultado_push.error
                if resultado_push.error
                else resultado_push.salida
            )

            messagebox.showerror(
                "Push no realizado",
                detalle
            )

            return

        self.fetch_exitoso_en_sesion = True

        if (
            resultado_fetch_final is not None
            and resultado_fetch_final.exitoso
            and estado_sincronizacion is not None
        ):
            self.aplicar_estado_sincronizacion(
                estado_sincronizacion
            )

            self.variable_ultima_consulta.set(
                (
                    "Push completado y estado remoto "
                    "verificado correctamente."
                )
            )

        else:
            self.cargar_estado_sincronizacion_local()

            self.variable_ultima_consulta.set(
                (
                    "Push completado. No fue posible completar "
                    "la verificación remota posterior."
                )
            )

        self.cargar_cambios()

        self.variable_estado.set(
            "Push completado correctamente."
        )

        messagebox.showinfo(
            "Push completado",
            (
                "Los commits fueron enviados correctamente.\n\n"
                "No se utilizó Push forzado.\n\n"
                "La información de sincronización fue actualizada."
            )
        )

    # =============================================================
    # ESTADO DE CONTROLES REMOTOS
    # =============================================================

    def actualizar_controles_operacion_remota(self):
        """
        Evita operaciones incompatibles mientras
        Fetch, Pull o Push están activos.
        """

        if self.operacion_remota_en_curso:
            self.boton_seleccionar.config(
                state=tk.DISABLED
            )

            self.boton_actualizar.config(
                state=tk.DISABLED
            )

            self.boton_historial.config(
                state=tk.DISABLED
            )

            self.boton_fetch.config(
                state=tk.DISABLED
            )

            self.boton_configurar_github.config(
                state=tk.DISABLED
            )

            self.boton_pull.config(
                state=tk.DISABLED
            )

            self.boton_push.config(
                state=tk.DISABLED
            )

            return

        self.boton_seleccionar.config(
            state=tk.NORMAL
        )

        self.boton_actualizar.config(
            state=(
                tk.NORMAL
                if self.ruta_repositorio
                else tk.DISABLED
            )
        )

        self.boton_historial.config(
            state=(
                tk.NORMAL
                if self.ruta_repositorio
                else tk.DISABLED
            )
        )

        self.boton_fetch.config(
            state=(
                tk.NORMAL
                if (
                    self.ruta_repositorio
                    and self.remotos_repositorio
                )
                else tk.DISABLED
            )
        )

        self.boton_configurar_github.config(
            state=(
                tk.NORMAL
                if (
                    self.ruta_repositorio
                    and not self.remotos_repositorio
                )
                else tk.DISABLED
            )
        )

        self.actualizar_estado_botones_sincronizacion()

    def actualizar_estado_botones_sincronizacion(self):
        """
        Habilita Pull o Push solamente cuando el estado
        conocido permite considerarlos candidatos.

        El servicio vuelve a validar todo antes
        de ejecutar la operación real.
        """

        puede_hacer_pull = False
        puede_hacer_push = False

        estado = (
            self.estado_sincronizacion_actual
        )

        condiciones_generales = (
            not self.operacion_remota_en_curso
            and bool(self.ruta_repositorio)
            and self.fetch_exitoso_en_sesion
            and not self.hay_cambios_pendientes
            and estado is not None
            and estado.exitoso
            and not estado.divergente
        )

        if condiciones_generales:
            # Pull:
            #
            # - upstream configurado
            # - ningún commit local pendiente
            # - uno o más commits remotos pendientes
            if (
                estado.upstream_configurado
                and estado.commits_por_subir == 0
                and estado.commits_por_bajar > 0
            ):
                puede_hacer_pull = True

            # Push:
            #
            # - uno o más commits locales pendientes
            # - ningún commit remoto pendiente
            if (
                estado.commits_por_subir > 0
                and estado.commits_por_bajar == 0
            ):
                puede_hacer_push = True

        self.boton_pull.config(
            state=(
                tk.NORMAL
                if puede_hacer_pull
                else tk.DISABLED
            )
        )

        self.boton_push.config(
            state=(
                tk.NORMAL
                if puede_hacer_push
                else tk.DISABLED
            )
        )

    # =============================================================
    # CONFIGURACIÓN INICIAL DE GITHUB
    # =============================================================

    def abrir_configuracion_github(self):
        """
        Abre la ventana educativa para configurar el primer remoto.

        Solamente está disponible cuando el repositorio no tiene
        ningún remoto configurado.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        if self.remotos_repositorio:
            messagebox.showinfo(
                "Remoto ya configurado",
                (
                    "Este repositorio ya tiene remoto(s) "
                    "configurado(s).\n\n"
                    "La aplicación no modificará ni eliminará "
                    "remotos existentes."
                )
            )

            return

        # Reutilizamos la ventana existente en lugar de crear otra.
        if (
            self.ventana_configuracion_github is not None
            and self.ventana_configuracion_github.winfo_exists()
        ):
            self.ventana_configuracion_github.deiconify()
            self.ventana_configuracion_github.lift()
            self.ventana_configuracion_github.focus_force()
            return

        self.ventana_configuracion_github = tk.Toplevel(
            self.ventana_principal
        )

        self.ventana_configuracion_github.title(
            "Configurar GitHub - Gestor Git"
        )

        self.ventana_configuracion_github.geometry(
            "760x520"
        )

        self.ventana_configuracion_github.minsize(
            640,
            440
        )

        self.ventana_configuracion_github.transient(
            self.ventana_principal
        )

        marco_configuracion = ttk.Frame(
            self.ventana_configuracion_github,
            padding=15
        )

        marco_configuracion.pack(
            fill=tk.BOTH,
            expand=True
        )

        ttk.Label(
            marco_configuracion,
            text="Configurar GitHub",
            style="Titulo.TLabel"
        ).pack(
            anchor="w"
        )

        ttk.Label(
            marco_configuracion,
            text=(
                "Paso a paso para conectar este repositorio local "
                "con un repositorio de GitHub:"
            ),
            style="AyudaVisible.TLabel",
            wraplength=700
        ).pack(
            anchor="w",
            pady=(8, 10)
        )

        pasos = (
            "1. Primero crea un repositorio VACÍO en GitHub.",
            "2. No agregues README, .gitignore ni licencia desde "
            "GitHub para este caso, porque el proyecto local ya "
            "tiene historial.",
            "3. Copia la URL HTTPS del repositorio.",
            "4. Pégala en GestorGit.",
            "5. GestorGit configurará solamente el remoto origin.",
            "6. Después será necesario ejecutar Fetch.",
            "7. Finalmente Push podrá enviar los commits locales "
            "si las validaciones existentes lo permiten.",
        )

        for paso in pasos:
            ttk.Label(
                marco_configuracion,
                text=paso,
                wraplength=700
            ).pack(
                anchor="w",
                pady=(1, 0)
            )

        ttk.Label(
            marco_configuracion,
            text=(
                "\nGestorGit NO inicia sesión, no recibe usuario, "
                "contraseña ni PAT, y no utiliza la API de GitHub. "
                "Solamente abre el navegador."
            ),
            style="AyudaVisible.TLabel",
            wraplength=700
        ).pack(
            anchor="w",
            pady=(8, 0)
        )

        self.boton_abrir_github = ttk.Button(
            marco_configuracion,
            text="Abrir GitHub para crear repositorio",
            command=self.abrir_github_para_crear_repositorio,
            style="Accion.TButton"
        )

        self.boton_abrir_github.pack(
            anchor="w",
            pady=(10, 0)
        )

        marco_url = ttk.Frame(
            marco_configuracion
        )

        marco_url.pack(
            fill=tk.X,
            pady=(14, 0)
        )

        ttk.Label(
            marco_url,
            text="URL HTTPS de GitHub:"
        ).pack(
            side=tk.LEFT
        )

        self.variable_url_github = tk.StringVar()

        entrada_url = ttk.Entry(
            marco_url,
            textvariable=self.variable_url_github,
            width=52
        )

        entrada_url.pack(
            side=tk.LEFT,
            padx=(8, 0)
        )

        entrada_url.focus_set()

        marco_botones = ttk.Frame(
            marco_configuracion
        )

        marco_botones.pack(
            anchor="e",
            pady=(14, 0)
        )

        self.boton_agregar_origin = ttk.Button(
            marco_botones,
            text="Agregar origin",
            command=self.agregar_origin_desde_ventana,
            style="Commit.TButton"
        )

        self.boton_agregar_origin.pack(
            side=tk.LEFT
        )

        self.boton_cancelar_configuracion = ttk.Button(
            marco_botones,
            text="Cancelar",
            command=self.cerrar_configuracion_github,
            style="Accion.TButton"
        )

        self.boton_cancelar_configuracion.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.ventana_configuracion_github.protocol(
            "WM_DELETE_WINDOW",
            self.cerrar_configuracion_github
        )

    def abrir_github_para_crear_repositorio(self):
        """
        Abre el navegador en la página de creación de repositorios.

        La aplicación no inicia sesión ni recibe credenciales.
        """

        navegador_abierto = False

        try:
            navegador_abierto = webbrowser.open(
                "https://github.com/new"
            )
        except Exception:
            navegador_abierto = False

        if not navegador_abierto:
            messagebox.showerror(
                "No fue posible abrir el navegador",
                (
                    "No fue posible abrir el navegador.\n\n"
                    "Puede ingresar manualmente a:\n"
                    "https://github.com/new"
                )
            )

    def agregar_origin_desde_ventana(self):
        """
        Configura el remoto origin con la URL indicada por el usuario.

        Solamente modifica la configuración local de Git.
        No ejecuta Fetch ni Push automáticamente.
        """

        if self.operacion_remota_en_curso:
            messagebox.showinfo(
                "Operación en curso",
                (
                    "Espere a que termine la operación remota "
                    "en curso antes de configurar el remoto."
                )
            )

            return

        if not self.ruta_repositorio:
            self.cerrar_configuracion_github()
            return

        url_remoto = (
            self.variable_url_github.get()
        )

        self.variable_estado.set(
            "Configurando el remoto origin..."
        )

        self.ventana_principal.update_idletasks()

        resultado = self.servicio_git.agregar_remoto_github(
            self.ruta_repositorio,
            url_remoto
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible configurar el remoto origin."
            )

            detalle = (
                resultado.error
                if resultado.error
                else resultado.salida
            )

            messagebox.showerror(
                "No fue posible configurar origin",
                detalle
            )

            return

        self.cerrar_configuracion_github()

        # Volvemos a cargar el repositorio para actualizar remotos
        # e información local, y exigimos un Fetch nuevo antes de
        # habilitar Pull o Push.
        self.cargar_repositorio(
            self.ruta_repositorio,
            reiniciar_fetch=True
        )

        messagebox.showinfo(
            "Remoto origin configurado",
            (
                "El remoto origin fue configurado correctamente.\n\n"
                "Ahora ejecute Fetch para consultar GitHub."
            )
        )

    def cerrar_configuracion_github(self):
        """
        Cierra la ventana de configuración si está abierta.
        """

        if hasattr(
            self,
            "ventana_configuracion_github"
        ):
            ventana = self.ventana_configuracion_github

            if ventana is not None:
                try:
                    if ventana.winfo_exists():
                        ventana.destroy()
                except tk.TclError:
                    pass

            self.ventana_configuracion_github = None
            self.variable_url_github = None

    # =============================================================
    # ARCHIVOS
    # =============================================================

    def seleccionar_todos_los_cambios(self):
        """
        Selecciona todos los archivos visibles.
        """

        elementos = self.tabla_cambios.get_children()

        if not elementos:
            return

        self.tabla_cambios.selection_set(
            elementos
        )

    def preparar_seleccionados(self):
        """
        Prepara los archivos seleccionados para commit.
        """

        if not self.ruta_repositorio:
            return

        seleccion = self.tabla_cambios.selection()

        if not seleccion:
            messagebox.showinfo(
                "Sin selección",
                "Seleccione al menos un archivo."
            )

            return

        rutas_archivos = []

        for identificador in seleccion:
            cambio = self.cambios_por_elemento.get(
                identificador
            )

            if cambio is None:
                continue

            if cambio.preparado:
                continue

            rutas_archivos.append(
                cambio.ruta
            )

        if not rutas_archivos:
            messagebox.showinfo(
                "Sin archivos pendientes",
                (
                    "Los archivos seleccionados ya están "
                    "preparados para commit."
                )
            )

            return

        mensaje = self._crear_mensaje_confirmacion_archivos(
            rutas_archivos,
            singular=(
                "Se preparará 1 archivo para el próximo commit."
            ),
            plural=(
                "Se prepararán {cantidad} archivos "
                "para el próximo commit."
            )
        )

        confirmado = messagebox.askyesno(
            "Preparar archivos",
            mensaje
        )

        if not confirmado:
            return

        self.variable_estado.set(
            "Preparando archivos..."
        )

        self.ventana_principal.update_idletasks()

        resultado = self.servicio_git.agregar_archivos(
            self.ruta_repositorio,
            rutas_archivos
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible preparar los archivos."
            )

            messagebox.showerror(
                "Error al preparar archivos",
                resultado.error
            )

            return

        self.cargar_cambios()

    def quitar_preparados_seleccionados(self):
        """
        Quita del área preparada los archivos seleccionados.

        Esta operación NO borra archivos.
        """

        if not self.ruta_repositorio:
            return

        seleccion = self.tabla_cambios.selection()

        if not seleccion:
            messagebox.showinfo(
                "Sin selección",
                "Seleccione al menos un archivo preparado."
            )

            return

        rutas_archivos = []

        for identificador in seleccion:
            cambio = self.cambios_por_elemento.get(
                identificador
            )

            if cambio is None:
                continue

            if not cambio.preparado:
                continue

            rutas_archivos.append(
                cambio.ruta
            )

        if not rutas_archivos:
            messagebox.showinfo(
                "Sin archivos preparados",
                (
                    "Los archivos seleccionados no están "
                    "preparados para commit."
                )
            )

            return

        mensaje = self._crear_mensaje_confirmacion_archivos(
            rutas_archivos,
            singular=(
                "Se quitará 1 archivo del próximo commit."
            ),
            plural=(
                "Se quitarán {cantidad} archivos "
                "del próximo commit."
            ),
            texto_final=(
                "Los archivos NO serán eliminados del disco.\n\n"
                "¿Desea continuar?"
            )
        )

        confirmado = messagebox.askyesno(
            "Quitar de preparados",
            mensaje
        )

        if not confirmado:
            return

        self.variable_estado.set(
            "Quitando archivos del área preparada..."
        )

        self.ventana_principal.update_idletasks()

        resultado = (
            self.servicio_git.quitar_archivos_preparados(
                self.ruta_repositorio,
                rutas_archivos
            )
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible quitar los archivos."
            )

            messagebox.showerror(
                "Error al quitar archivos",
                resultado.error
            )

            return

        self.cargar_cambios()

    def actualizar_preparados_seleccionados(self):
        """
        Actualiza el área preparada con la versión actual completa
        de los archivos seleccionados que lo requieran.

        Equivale a volver a ejecutar git add sobre cada ruta.
        No modifica el working tree y no crea commits.
        """

        if not self.ruta_repositorio:
            return

        seleccion = self.tabla_cambios.selection()

        if not seleccion:
            messagebox.showinfo(
                "Sin selección",
                "Seleccione al menos un archivo."
            )

            return

        rutas_archivos = []

        for identificador in seleccion:
            cambio = self.cambios_por_elemento.get(
                identificador
            )

            if cambio is None:
                continue

            if not cambio.requiere_actualizar_preparado:
                continue

            rutas_archivos.append(
                cambio.ruta
            )

        if not rutas_archivos:
            messagebox.showinfo(
                "Sin archivos para actualizar",
                (
                    "Ninguno de los archivos seleccionados "
                    "necesita actualización: ya están preparados "
                    "con su versión actual completa."
                )
            )

            return

        mensaje = self._crear_mensaje_confirmacion_archivos(
            rutas_archivos,
            singular=(
                "Se actualizará 1 archivo preparado "
                "con sus cambios actuales."
            ),
            plural=(
                "Se actualizarán {cantidad} archivos preparados "
                "con sus cambios actuales."
            ),
            texto_final=(
                "La versión preparada anterior de estos archivos "
                "será reemplazada en el área preparada por su "
                "versión actual completa.\n\n"
                "Los archivos del disco NO serán modificados "
                "ni eliminados.\n"
                "No se creará ningún commit.\n\n"
                "Si preparaste solamente parte de alguno de estos "
                "archivos con otra herramienta, también se "
                "incluirán sus cambios restantes.\n\n"
                "¿Desea continuar?"
            )
        )

        confirmado = messagebox.askyesno(
            "Actualizar preparados",
            mensaje
        )

        if not confirmado:
            return

        self.variable_estado.set(
            "Actualizando archivos preparados..."
        )

        self.ventana_principal.update_idletasks()

        resultado = (
            self.servicio_git.actualizar_archivos_preparados(
                self.ruta_repositorio,
                rutas_archivos
            )
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible actualizar los archivos preparados."
            )

            messagebox.showerror(
                "Error al actualizar preparados",
                resultado.error
            )

            return

        self.cargar_cambios()

    # =============================================================
    # COMMIT
    # =============================================================

    def crear_commit_desde_interfaz(self):
        """
        Crea un commit local con todos los archivos preparados.
        """

        if not self.ruta_repositorio:
            return

        mensaje_commit = (
            self.variable_mensaje_commit.get().strip()
        )

        if not mensaje_commit:
            messagebox.showinfo(
                "Mensaje obligatorio",
                "Escriba un mensaje para el commit."
            )

            self.entrada_mensaje_commit.focus_set()

            return

        resultado_cambios = self.servicio_git.obtener_cambios(
            self.ruta_repositorio
        )

        if not resultado_cambios.exitoso:
            messagebox.showerror(
                "Error al consultar Git",
                resultado_cambios.error
            )

            return

        rutas_preparadas = [
            cambio.ruta
            for cambio in resultado_cambios.cambios
            if cambio.preparado
        ]

        if not rutas_preparadas:
            messagebox.showinfo(
                "Sin archivos preparados",
                "No hay archivos preparados para crear el commit."
            )

            self.cargar_cambios()

            return

        resumen_archivos = self._crear_resumen_rutas(
            rutas_preparadas
        )

        mensaje_confirmacion = (
            "Se creará un commit LOCAL.\n\n"
            f"Mensaje:\n{mensaje_commit}\n\n"
            "Archivos que entrarán en el commit:\n"
            f"{resumen_archivos}\n\n"
            "El commit no será enviado automáticamente.\n\n"
            "¿Desea continuar?"
        )

        confirmado = messagebox.askyesno(
            "Crear commit",
            mensaje_confirmacion
        )

        if not confirmado:
            return

        self.variable_estado.set(
            "Creando commit..."
        )

        self.ventana_principal.update_idletasks()

        resultado = self.servicio_git.crear_commit(
            self.ruta_repositorio,
            mensaje_commit
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible crear el commit."
            )

            detalle_error = (
                resultado.error
                if resultado.error
                else resultado.salida
            )

            messagebox.showerror(
                "No fue posible crear el commit",
                detalle_error
            )

            self.cargar_cambios()

            return

        resultado_hash = self.servicio_git.obtener_hash_actual(
            self.ruta_repositorio
        )

        hash_commit = (
            resultado_hash.salida
            if resultado_hash.exitoso
            else "No disponible"
        )

        self.variable_mensaje_commit.set(
            ""
        )

        self.cargar_repositorio(
            self.ruta_repositorio,
            reiniciar_fetch=False
        )

        messagebox.showinfo(
            "Commit creado",
            (
                "El commit fue creado correctamente.\n\n"
                f"Hash: {hash_commit}\n\n"
                "El commit existe solamente en el repositorio local.\n"
                "Utilice Push cuando desee enviarlo al remoto."
            )
        )

    # =============================================================
    # LIMPIEZA
    # =============================================================

    def limpiar_tabla(self):
        """
        Limpia la tabla de cambios.
        """

        for elemento in self.tabla_cambios.get_children():
            self.tabla_cambios.delete(
                elemento
            )

        self.cambios_por_elemento.clear()

    def deshabilitar_botones_de_archivos(self):
        """
        Deshabilita las acciones relacionadas con archivos.
        """

        self.boton_seleccionar_todo.config(
            state=tk.DISABLED
        )

        self.boton_preparar.config(
            state=tk.DISABLED
        )

        self.boton_actualizar_preparados.config(
            state=tk.DISABLED
        )

        self.boton_quitar_preparados.config(
            state=tk.DISABLED
        )

        self.boton_crear_commit.config(
            state=tk.DISABLED
        )

    def actualizar_estado_botones_archivos(self, _evento=None):
        """
        Actualiza el estado de los botones de archivos según
        el contenido de la tabla y la selección actual.
        """

        cambios = [
            self.cambios_por_elemento[elemento]
            for elemento in self.tabla_cambios.get_children()
            if elemento in self.cambios_por_elemento
        ]

        cambios_seleccionados = [
            self.cambios_por_elemento[elemento]
            for elemento in self.tabla_cambios.selection()
            if elemento in self.cambios_por_elemento
        ]

        hay_cambios_visibles = len(
            cambios
        ) > 0

        # Preparar actúa sobre los seleccionados que todavía
        # no están en el área preparada.
        hay_no_preparados_seleccionados = any(
            not cambio.preparado
            for cambio in cambios_seleccionados
        )

        # Quitar actúa sobre los seleccionados ya preparados.
        hay_preparados_seleccionados = any(
            cambio.preparado
            for cambio in cambios_seleccionados
        )

        # Actualizar actúa sobre los seleccionados que tienen
        # cambios nuevos fuera del índice.
        hay_que_actualizar = any(
            cambio.requiere_actualizar_preparado
            for cambio in cambios_seleccionados
        )

        self.boton_seleccionar_todo.config(
            state=(
                tk.NORMAL
                if hay_cambios_visibles
                else tk.DISABLED
            )
        )

        self.boton_preparar.config(
            state=(
                tk.NORMAL
                if hay_no_preparados_seleccionados
                else tk.DISABLED
            )
        )

        self.boton_actualizar_preparados.config(
            state=(
                tk.NORMAL
                if hay_que_actualizar
                else tk.DISABLED
            )
        )

        self.boton_quitar_preparados.config(
            state=(
                tk.NORMAL
                if hay_preparados_seleccionados
                else tk.DISABLED
            )
        )

        # El commit se habilita cuando hay preparados; el servicio
        # vuelve a bloquearlo con su mensaje educativo si algún
        # archivo fue modificado después de haber sido preparado.
        self.boton_crear_commit.config(
            state=(
                tk.NORMAL
                if any(
                    cambio.preparado
                    for cambio in cambios
                )
                else tk.DISABLED
            )
        )

    def limpiar_estado_sincronizacion(self):
        """
        Restablece la información de sincronización.
        """

        self.estado_sincronizacion_actual = None

        self.variable_upstream.set(
            "-"
        )

        self.variable_rama_remota.set(
            "-"
        )

        self.variable_por_subir.set(
            "-"
        )

        self.variable_por_bajar.set(
            "-"
        )

        self.variable_estado_sincronizacion.set(
            "Seleccione un repositorio."
        )

        self.variable_ultima_consulta.set(
            "Todavía no se ejecutó Fetch en esta sesión."
        )

        self.actualizar_estado_botones_sincronizacion()

    def limpiar_repositorio(self):
        """
        Restablece toda la información visual.
        """

        self.ruta_repositorio = ""

        self.remotos_repositorio = []

        self.hay_cambios_pendientes = False

        self.estado_sincronizacion_actual = None

        self.fetch_exitoso_en_sesion = False

        self.variable_ruta.set(
            "Ningún repositorio seleccionado"
        )

        self.variable_rama.set("-")
        self.variable_remoto.set("-")
        self.variable_commits.set("-")

        self.variable_mensaje_commit.set(
            ""
        )

        self.boton_actualizar.config(
            state=tk.DISABLED
        )

        self.boton_historial.config(
            state=tk.DISABLED
        )

        self.boton_fetch.config(
            state=tk.DISABLED
        )

        self.boton_configurar_github.config(
            state=tk.DISABLED
        )

        self.boton_pull.config(
            state=tk.DISABLED
        )

        self.boton_push.config(
            state=tk.DISABLED
        )

        self.deshabilitar_botones_de_archivos()

        self.limpiar_tabla()

        self.limpiar_estado_sincronizacion()

        self.cerrar_configuracion_github()

        self.cerrar_historial()

        self.cerrar_detalle_commit()

    # =============================================================
    # MENSAJES DE CONFIRMACIÓN
    # =============================================================

    @staticmethod
    def _crear_mensaje_confirmacion_pull(
        estado
    ):
        """
        Construye la confirmación detallada de Pull.
        """

        cantidad = (
            estado.commits_por_bajar
        )

        if cantidad == 1:
            encabezado = (
                "Se descargará 1 commit."
            )
        else:
            encabezado = (
                f"Se descargarán {cantidad} commits."
            )

        return (
            f"{encabezado}\n\n"
            f"Rama local: {estado.rama_local}\n"
            f"Remoto: {estado.remoto}\n"
            f"Origen: {estado.rama_remota}\n\n"
            "Antes de descargar se ejecutará Fetch nuevamente.\n"
            "Si el estado remoto cambió, Pull será bloqueado.\n\n"
            "La actualización solamente se permitirá mediante "
            "fast-forward.\n\n"
            "No se realizará Merge automático.\n"
            "No se realizará Rebase automático.\n\n"
            "¿Desea continuar?"
        )

    @staticmethod
    def _crear_mensaje_confirmacion_push(
        estado
    ):
        """
        Construye la confirmación detallada de Push.
        """

        cantidad = (
            estado.commits_por_subir
        )

        if cantidad == 1:
            encabezado = (
                "Se enviará 1 commit."
            )
        else:
            encabezado = (
                f"Se enviarán {cantidad} commits."
            )

        if (
            not estado.upstream_configurado
            and not estado.rama_remota_existe
        ):
            explicacion_destino = (
                "La rama remota todavía no existe.\n"
                "Se creará y quedará configurada como upstream."
            )

        elif not estado.upstream_configurado:
            explicacion_destino = (
                "La rama remota ya existe, pero todavía no está "
                "configurada como upstream.\n"
                "El Push establecerá esa relación."
            )

        else:
            explicacion_destino = (
                "La rama ya tiene su upstream configurado."
            )

        return (
            f"{encabezado}\n\n"
            f"Rama local: {estado.rama_local}\n"
            f"Remoto: {estado.remoto}\n"
            f"Destino: {estado.rama_remota}\n\n"
            f"{explicacion_destino}\n\n"
            "Antes de enviar se ejecutará Fetch nuevamente.\n"
            "Si el remoto cambió, Push será bloqueado.\n\n"
            "Nunca se utilizará Push forzado.\n\n"
            "¿Desea continuar?"
        )

    @staticmethod
    def _crear_resumen_rutas(rutas):
        """
        Crea un resumen de rutas para mostrar
        en una confirmación.
        """

        limite = 15

        rutas_visibles = rutas[
            :limite
        ]

        texto = "\n".join(
            f"- {ruta}"
            for ruta in rutas_visibles
        )

        cantidad_restante = (
            len(rutas)
            - len(rutas_visibles)
        )

        if cantidad_restante > 0:
            texto += (
                f"\n- ... y {cantidad_restante} archivo(s) más"
            )

        return texto

    def _crear_mensaje_confirmacion_archivos(
        self,
        rutas,
        singular,
        plural,
        texto_final="¿Desea continuar?"
    ):
        """
        Construye mensajes de confirmación para archivos.
        """

        cantidad = len(
            rutas
        )

        if cantidad == 1:
            encabezado = singular
        else:
            encabezado = plural.format(
                cantidad=cantidad
            )

        resumen = self._crear_resumen_rutas(
            rutas
        )

        return (
            f"{encabezado}\n\n"
            f"{resumen}\n\n"
            f"{texto_final}"
        )


def iniciar_aplicacion():
    """
    Inicia la aplicación.
    """

    ventana_principal = tk.Tk()

    AplicacionGit(
        ventana_principal
    )

    ventana_principal.mainloop()


if __name__ == "__main__":
    iniciar_aplicacion()
