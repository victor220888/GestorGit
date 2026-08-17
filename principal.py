import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from servicio_git import ServicioGit


class AplicacionGit:
    """
    Ventana principal de la aplicación Gestor Git.

    Toda comunicación con Git se realiza mediante ServicioGit.
    """

    def __init__(self, ventana_principal):
        # Guardamos la ventana principal.
        self.ventana_principal = ventana_principal

        # Servicio encargado de comunicarse con Git.
        self.servicio_git = ServicioGit()

        # Ruta del repositorio actualmente seleccionado.
        self.ruta_repositorio = ""

        # Relaciona las filas de la tabla con CambioArchivo.
        self.cambios_por_elemento = {}

        self.configurar_ventana()
        self.crear_interfaz()
        self.verificar_git()

    def configurar_ventana(self):
        """
        Configura las propiedades generales de la ventana.
        """

        self.ventana_principal.title(
            "Gestor Git"
        )

        self.ventana_principal.geometry(
            "1100x760"
        )

        self.ventana_principal.minsize(
            850,
            620
        )

    def crear_interfaz(self):
        """
        Crea todos los controles visibles.
        """

        # ---------------------------------------------------------
        # Marco principal
        # ---------------------------------------------------------

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

        # La tabla ocupa el espacio vertical sobrante.
        marco_principal.rowconfigure(
            4,
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
        # Información del repositorio
        # ---------------------------------------------------------

        marco_informacion = ttk.LabelFrame(
            marco_principal,
            text="Información",
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
            text="Remoto:"
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
        # Archivos con cambios
        # ---------------------------------------------------------

        etiqueta_cambios = ttk.Label(
            marco_principal,
            text="Archivos con cambios:",
            font=("Segoe UI", 10, "bold")
        )

        etiqueta_cambios.grid(
            row=3,
            column=0,
            sticky="w",
            pady=(5, 5)
        )

        marco_tabla = ttk.Frame(
            marco_principal
        )

        marco_tabla.grid(
            row=4,
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
            width=600,
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
            row=5,
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
            row=6,
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
                "Todavía no se enviará a GitHub."
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
            row=7,
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

        ruta_seleccionada = filedialog.askdirectory(
            title="Seleccionar repositorio Git"
        )

        if not ruta_seleccionada:
            return

        self.cargar_repositorio(
            ruta_seleccionada
        )

    def cargar_repositorio(self, ruta_repositorio):
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

        self.cargar_cambios()

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

        if cantidad > 0:
            self.boton_seleccionar_todo.config(
                state=tk.NORMAL
            )
        else:
            self.boton_seleccionar_todo.config(
                state=tk.DISABLED
            )

        if hay_no_preparados:
            self.boton_preparar.config(
                state=tk.NORMAL
            )
        else:
            self.boton_preparar.config(
                state=tk.DISABLED
            )

        if hay_preparados:
            self.boton_quitar_preparados.config(
                state=tk.NORMAL
            )

            self.boton_crear_commit.config(
                state=tk.NORMAL
            )

        else:
            self.boton_quitar_preparados.config(
                state=tk.DISABLED
            )

            self.boton_crear_commit.config(
                state=tk.DISABLED
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

    def actualizar_repositorio(self):
        """
        Vuelve a consultar el repositorio seleccionado.
        """

        if not self.ruta_repositorio:
            return

        self.cargar_repositorio(
            self.ruta_repositorio
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
            singular="Se preparará 1 archivo para el próximo commit.",
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
            singular="Se quitará 1 archivo del próximo commit.",
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

        mensaje_commit = self.variable_mensaje_commit.get().strip()

        if not mensaje_commit:
            messagebox.showinfo(
                "Mensaje obligatorio",
                "Escriba un mensaje para el commit."
            )

            self.entrada_mensaje_commit.focus_set()

            return

        # Consultamos nuevamente el estado para no confiar
        # solamente en la información visual de la tabla.
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
            "Este paso todavía NO enviará nada a GitHub.\n\n"
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

            # Volvemos a leer el estado por si Git realizó
            # alguna modificación parcial antes de fallar.
            self.cargar_cambios()

            return

        # Obtenemos el hash del commit recién creado.
        resultado_hash = self.servicio_git.obtener_hash_actual(
            self.ruta_repositorio
        )

        if resultado_hash.exitoso:
            hash_commit = resultado_hash.salida
        else:
            hash_commit = "No disponible"

        # Limpiamos el mensaje después de un commit exitoso.
        self.variable_mensaje_commit.set(
            ""
        )

        # Actualizamos toda la información del repositorio.
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
        Limpia la tabla.
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

    def limpiar_repositorio(self):
        """
        Restablece la información visual.
        """

        self.ruta_repositorio = ""

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

        self.deshabilitar_botones_de_archivos()

        self.limpiar_tabla()

    @staticmethod
    def _crear_resumen_rutas(rutas):
        """
        Crea un resumen de rutas para mostrar en una confirmación.

        Limitamos la cantidad mostrada para evitar diálogos enormes.
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
        Construye el mensaje utilizado para confirmar
        operaciones sobre uno o varios archivos.
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