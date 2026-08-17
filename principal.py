import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from servicio_git import ServicioGit


class AplicacionGit:
    """
    Ventana principal de la aplicación Gestor Git.

    Esta clase solamente se encarga de la interfaz gráfica.

    Toda comunicación con Git se realiza mediante ServicioGit.
    """

    def __init__(self, ventana_principal):
        # Guardamos la ventana principal.
        self.ventana_principal = ventana_principal

        # Creamos una única instancia del servicio encargado de Git.
        self.servicio_git = ServicioGit()

        # Guardará la ruta del repositorio actualmente seleccionado.
        self.ruta_repositorio = ""

        # Configuramos la ventana.
        self.configurar_ventana()

        # Creamos los controles.
        self.crear_interfaz()

        # Verificamos que Git esté disponible.
        self.verificar_git()

    def configurar_ventana(self):
        """
        Configura las propiedades generales de la ventana.
        """

        self.ventana_principal.title("Gestor Git")

        # Tamaño inicial.
        self.ventana_principal.geometry("1100x700")

        # Evitamos que la ventana pueda reducirse demasiado.
        self.ventana_principal.minsize(850, 550)

    def crear_interfaz(self):
        """
        Crea todos los controles visibles de la aplicación.
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

        # Permitimos que la columna principal crezca
        # cuando el usuario cambie el tamaño de la ventana.
        marco_principal.columnconfigure(
            0,
            weight=1
        )

        # Permitimos que la tabla también crezca verticalmente.
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
        # Selección del repositorio
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

        # Variable de Tkinter que mostrará la ruta seleccionada.
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
        # Información general
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

        # Variables que iremos modificando al consultar Git.
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
        # Título de la lista de cambios
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

        # ---------------------------------------------------------
        # Tabla de archivos
        # ---------------------------------------------------------

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
            show="headings"
        )

        # Encabezados.
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

        # Tamaño aproximado de las columnas.
        self.tabla_cambios.column(
            "estado",
            width=260,
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

        # Barra vertical para repositorios con muchos archivos.
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

        # Barra horizontal para rutas largas.
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
            row=5,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

    def verificar_git(self):
        """
        Verifica que git.exe se encuentre disponible.

        Si Git no existe, bloqueamos las operaciones principales.
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
        Permite seleccionar una carpeta mediante
        el explorador de Windows.
        """

        ruta_seleccionada = filedialog.askdirectory(
            title="Seleccionar repositorio Git"
        )

        # Si el usuario canceló, no hacemos nada.
        if not ruta_seleccionada:
            return

        self.cargar_repositorio(
            ruta_seleccionada
        )

    def cargar_repositorio(self, ruta_repositorio):
        """
        Valida y carga la información de un repositorio.
        """

        self.variable_estado.set(
            "Analizando repositorio..."
        )

        # Forzamos una actualización visual para que el mensaje
        # pueda verse antes de ejecutar la consulta.
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

        # Guardamos la raíz real que nos devolvió Git.
        self.ruta_repositorio = estado.ruta_raiz

        self.variable_ruta.set(
            estado.ruta_raiz
        )

        if estado.rama_actual:
            self.variable_rama.set(
                estado.rama_actual
            )
        else:
            self.variable_rama.set(
                "No determinada"
            )

        if estado.remotos:
            self.variable_remoto.set(
                ", ".join(estado.remotos)
            )
        else:
            self.variable_remoto.set(
                "Sin remoto"
            )

        if estado.tiene_commits:
            self.variable_commits.set(
                "Sí"
            )
        else:
            self.variable_commits.set(
                "No"
            )

        # Una vez validado el repositorio podemos habilitar
        # el botón de actualización.
        self.boton_actualizar.config(
            state=tk.NORMAL
        )

        # Consultamos los cambios.
        self.cargar_cambios()

    def cargar_cambios(self):
        """
        Consulta Git y muestra los archivos pendientes en la tabla.
        """

        # Eliminamos los elementos anteriores de la tabla.
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

            messagebox.showerror(
                "Error al consultar Git",
                resultado.error
            )

            return

        # Insertamos cada archivo en la tabla.
        for cambio in resultado.cambios:
            if cambio.preparado:
                texto_preparado = "Sí"
            else:
                texto_preparado = "No"

            self.tabla_cambios.insert(
                "",
                tk.END,
                values=(
                    cambio.descripcion,
                    texto_preparado,
                    cambio.ruta
                )
            )

        cantidad = len(
            resultado.cambios
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
        Vuelve a consultar la información y los cambios
        del repositorio actualmente seleccionado.
        """

        if not self.ruta_repositorio:
            return

        # Volvemos a analizar todo porque la rama o los remotos
        # podrían haber cambiado desde la última consulta.
        self.cargar_repositorio(
            self.ruta_repositorio
        )

    def limpiar_tabla(self):
        """
        Elimina todos los registros de la tabla de cambios.
        """

        for elemento in self.tabla_cambios.get_children():
            self.tabla_cambios.delete(
                elemento
            )

    def limpiar_repositorio(self):
        """
        Restablece la información visual del repositorio.
        """

        self.ruta_repositorio = ""

        self.variable_ruta.set(
            "Ningún repositorio seleccionado"
        )

        self.variable_rama.set("-")
        self.variable_remoto.set("-")
        self.variable_commits.set("-")

        self.boton_actualizar.config(
            state=tk.DISABLED
        )

        self.limpiar_tabla()


def iniciar_aplicacion():
    """
    Crea la ventana principal e inicia la aplicación.
    """

    ventana_principal = tk.Tk()

    AplicacionGit(
        ventana_principal
    )

    ventana_principal.mainloop()


if __name__ == "__main__":
    iniciar_aplicacion()