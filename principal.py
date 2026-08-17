import queue
import threading
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from servicio_remoto_git import ServicioRemotoGit


class AplicacionGit:
    """
    Ventana principal de la aplicación Gestor Git.

    Las operaciones locales y remotas pasan por ServicioRemotoGit.

    Las operaciones de red se ejecutan en un hilo secundario
    para no bloquear la interfaz de Tkinter.
    """

    def __init__(self, ventana_principal):
        self.ventana_principal = ventana_principal

        # Servicio que incluye las operaciones locales anteriores
        # y las nuevas operaciones remotas.
        self.servicio_git = ServicioRemotoGit()

        self.ruta_repositorio = ""
        self.remotos_repositorio = []

        self.cambios_por_elemento = {}

        # Los hilos secundarios nunca modificarán directamente
        # los controles de Tkinter.
        #
        # Utilizarán esta cola para devolver sus resultados.
        self.cola_resultados = queue.Queue()

        self.operacion_remota_en_curso = False

        self.configurar_ventana()
        self.crear_interfaz()
        self.verificar_git()

        # Tkinter comprobará periódicamente si existe
        # algún resultado enviado por los hilos.
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
            "1180x880"
        )

        self.ventana_principal.minsize(
            950,
            700
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

        # La tabla ocupará el espacio vertical restante.
        marco_principal.rowconfigure(
            5,
            weight=1
        )

        # ---------------------------------------------------------
        # Título
        # ---------------------------------------------------------

        etiqueta_titulo = ttk.Label(
            marco_principal,
            text="Gestor Git",
            font=("Segoe UI", 18, "bold")
        )

        etiqueta_titulo.grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 15)
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
            command=self.seleccionar_repositorio
        )

        self.boton_seleccionar.grid(
            row=0,
            column=1
        )

        self.boton_actualizar = ttk.Button(
            marco_repositorio,
            text="Actualizar",
            command=self.actualizar_repositorio,
            state=tk.DISABLED
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

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_estado_sincronizacion,
            wraplength=760
        ).grid(
            row=1,
            column=1,
            columnspan=6,
            sticky="w",
            pady=(8, 0)
        )

        self.boton_fetch = ttk.Button(
            marco_sincronizacion,
            text="Fetch",
            command=self.iniciar_fetch,
            state=tk.DISABLED
        )

        self.boton_fetch.grid(
            row=1,
            column=7,
            sticky="e",
            pady=(8, 0)
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
            width=100,
            minwidth=80,
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
            state=tk.DISABLED
        )

        self.boton_seleccionar_todo.pack(
            side=tk.LEFT
        )

        self.boton_preparar = ttk.Button(
            marco_acciones,
            text="Preparar seleccionados",
            command=self.preparar_seleccionados,
            state=tk.DISABLED
        )

        self.boton_preparar.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_quitar_preparados = ttk.Button(
            marco_acciones,
            text="Quitar de preparados",
            command=self.quitar_preparados_seleccionados,
            state=tk.DISABLED
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
            state=tk.DISABLED
        )

        self.boton_crear_commit.grid(
            row=0,
            column=2
        )

        ttk.Label(
            marco_commit,
            text=(
                "El commit se guardará solamente en el repositorio local. "
                "Todavía no se enviará al remoto."
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

        etiqueta_estado = ttk.Label(
            marco_principal,
            textvariable=self.variable_estado,
            relief=tk.SUNKEN,
            anchor="w",
            padding=(5, 4)
        )

        etiqueta_estado.grid(
            row=8,
            column=0,
            sticky="ew",
            pady=(10, 0)
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
            ruta_seleccionada
        )

    def cargar_repositorio(
        self,
        ruta_repositorio
    ):
        """
        Valida y carga un repositorio.
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

        self.ruta_repositorio = estado.ruta_raiz

        self.remotos_repositorio = list(
            estado.remotos
        )

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

        if estado.remotos:
            self.boton_fetch.config(
                state=tk.NORMAL
            )
        else:
            self.boton_fetch.config(
                state=tk.DISABLED
            )

        self.variable_ultima_consulta.set(
            "Información local. Pulse Fetch para consultar el remoto."
        )

        self.cargar_cambios()

        # Esta consulta no accede a Internet.
        self.cargar_estado_sincronizacion_local()

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

            self.deshabilitar_botones_de_archivos()

            messagebox.showerror(
                "Error al consultar Git",
                resultado.error
            )

            return

        for cambio in resultado.cambios:

            texto_preparado = (
                "Sí"
                if cambio.preparado
                else "No"
            )

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

        hay_no_preparados = any(
            not cambio.preparado
            for cambio in resultado.cambios
        )

        hay_preparados = any(
            cambio.preparado
            for cambio in resultado.cambios
        )

        self.boton_seleccionar_todo.config(
            state=(
                tk.NORMAL
                if cantidad > 0
                else tk.DISABLED
            )
        )

        self.boton_preparar.config(
            state=(
                tk.NORMAL
                if hay_no_preparados
                else tk.DISABLED
            )
        )

        self.boton_quitar_preparados.config(
            state=(
                tk.NORMAL
                if hay_preparados
                else tk.DISABLED
            )
        )

        self.boton_crear_commit.config(
            state=(
                tk.NORMAL
                if hay_preparados
                else tk.DISABLED
            )
        )

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
        Muestra el estado basado en las referencias
        disponibles localmente.

        Este método NO realiza conexión de red.
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

        if not estado.exitoso:
            self.variable_upstream.set("-")
            self.variable_rama_remota.set("-")
            self.variable_por_subir.set("-")
            self.variable_por_bajar.set("-")

            self.variable_estado_sincronizacion.set(
                estado.error
            )

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

    def actualizar_repositorio(self):
        """
        Vuelve a consultar el repositorio seleccionado.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        self.cargar_repositorio(
            self.ruta_repositorio
        )

    def iniciar_fetch(self):
        """
        Inicia Fetch en un hilo secundario.

        Tkinter continúa funcionando mientras Git
        espera la respuesta del remoto.
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
        Trabajo que se ejecuta fuera del hilo principal.

        MUY IMPORTANTE:

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

        # El hilo secundario deposita el resultado en la cola.
        self.cola_resultados.put(
            (
                "fetch",
                ruta_repositorio,
                remoto,
                resultado_fetch,
                estado_sincronizacion
            )
        )

    def procesar_cola_resultados(self):
        """
        Procesa resultados de los hilos secundarios
        desde el hilo principal de Tkinter.
        """

        try:
            while True:

                elemento = (
                    self.cola_resultados.get_nowait()
                )

                if elemento[0] == "fetch":
                    self.procesar_resultado_fetch(
                        *elemento[1:]
                    )

        except queue.Empty:
            pass

        # Volvemos a consultar la cola dentro de 100 ms.
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

        # Protección adicional por si el repositorio
        # actual cambió mientras terminaba el hilo.
        if ruta_repositorio != self.ruta_repositorio:
            return

        if not resultado_fetch.exitoso:

            self.variable_estado.set(
                "Fetch falló."
            )

            self.variable_ultima_consulta.set(
                "El último Fetch no pudo completarse."
            )

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

        if estado_sincronizacion is None:
            self.variable_estado.set(
                "Fetch completado, pero no se pudo calcular el estado."
            )

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
                "Fetch completado, pero el estado no pudo calcularse."
            )

    def actualizar_controles_operacion_remota(self):
        """
        Evita iniciar otras operaciones incompatibles
        mientras Fetch está activo.
        """

        if self.operacion_remota_en_curso:

            self.boton_seleccionar.config(
                state=tk.DISABLED
            )

            self.boton_actualizar.config(
                state=tk.DISABLED
            )

            self.boton_fetch.config(
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
            "Este paso todavía NO enviará nada al remoto.\n\n"
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
            self.ruta_repositorio
        )

        messagebox.showinfo(
            "Commit creado",
            (
                "El commit fue creado correctamente.\n\n"
                f"Hash: {hash_commit}\n\n"
                "El commit existe solamente en el repositorio local.\n"
                "Todavía NO fue enviado al repositorio remoto."
            )
        )

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

        self.boton_quitar_preparados.config(
            state=tk.DISABLED
        )

        self.boton_crear_commit.config(
            state=tk.DISABLED
        )

    def limpiar_estado_sincronizacion(self):
        """
        Restablece la información de sincronización.
        """

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

    def limpiar_repositorio(self):
        """
        Restablece la información visual.
        """

        self.ruta_repositorio = ""

        self.remotos_repositorio = []

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

        self.boton_fetch.config(
            state=tk.DISABLED
        )

        self.deshabilitar_botones_de_archivos()

        self.limpiar_tabla()

        self.limpiar_estado_sincronizacion()

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