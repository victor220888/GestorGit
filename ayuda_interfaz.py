import tkinter as tk
from tkinter import ttk


def calcular_posicion_ayuda(
    ancla_x,
    ancla_y,
    ancla_y_arriba,
    ancho,
    alto,
    pantalla_ancho,
    pantalla_alto,
    margen=8
):
    """
    Calcula la posición final de una ayuda emergente para que
    todo el tooltip quede dentro de la zona visible de la
    pantalla.

    ancla_x / ancla_y: posición normal de la ayuda (debajo del
    control). ancla_y_arriba: coordenada Y justo encima del
    control, base para recolocar la ayuda por arriba cuando no
    cabe debajo.

    Reglas:

    - si la posición normal desborda por abajo, la ayuda se
      coloca por encima del control;
    - si desborda por la derecha, se desplaza hacia la izquierda;
    - las coordenadas resultantes nunca son menores que margen.

    Devuelve (x, y).
    """

    x = ancla_x

    if x + ancho > pantalla_ancho - margen:
        x = pantalla_ancho - margen - ancho

    if x < margen:
        x = margen

    y = ancla_y

    if y + alto > pantalla_alto - margen:
        y = ancla_y_arriba - alto

    if y < margen:
        y = margen

    return (x, y)


class AyudaEmergente:
    """
    Muestra una pequeña ventana de ayuda cuando el mouse
    permanece sobre un control.
    """

    def __init__(
        self,
        control,
        texto,
        demora_milisegundos=550,
        ancho_texto=380
    ):
        self.control = control
        self.texto = texto
        self.demora_milisegundos = demora_milisegundos
        self.ancho_texto = ancho_texto
        self.identificador_after = None
        self.ventana_ayuda = None

        self.control.bind("<Enter>", self.programar_mostrar, add="+")
        self.control.bind("<Leave>", self.ocultar, add="+")
        self.control.bind("<ButtonPress>", self.ocultar, add="+")

    def programar_mostrar(self, _evento=None):
        """Programa la aparición de la ayuda."""

        self.cancelar_programacion()

        self.identificador_after = self.control.after(
            self.demora_milisegundos,
            self.mostrar
        )

    def cancelar_programacion(self):
        """Cancela una ayuda pendiente."""

        if self.identificador_after is None:
            return

        try:
            self.control.after_cancel(self.identificador_after)
        except tk.TclError:
            pass

        self.identificador_after = None

    def mostrar(self):
        """
        Muestra la ayuda cerca del control sin salirse de la
        pantalla.

        La geometría se fija DESPUÉS de conocer el tamaño
        requerido real del tooltip: si no cabe debajo del control
        se recoloca por arriba y, si desborda lateralmente, se
        desplaza hacia la izquierda.
        """

        self.identificador_after = None

        if self.ventana_ayuda is not None or not self.texto:
            return

        try:
            ancla_x = self.control.winfo_rootx() + 12
            ancla_y = (
                self.control.winfo_rooty()
                + self.control.winfo_height()
                + 8
            )
            ancla_y_arriba = self.control.winfo_rooty() - 8
        except tk.TclError:
            return

        self.ventana_ayuda = tk.Toplevel(self.control)
        self.ventana_ayuda.wm_overrideredirect(True)

        try:
            self.ventana_ayuda.attributes("-topmost", True)
        except tk.TclError:
            pass

        etiqueta = tk.Label(
            self.ventana_ayuda,
            text=self.texto,
            justify=tk.LEFT,
            wraplength=self.ancho_texto,
            background="#FFF8D8",
            foreground="#1F2937",
            relief=tk.SOLID,
            borderwidth=1,
            padx=10,
            pady=8,
            font=("Segoe UI", 9)
        )

        etiqueta.pack()

        # Actualizar las tareas pendientes para que el tamaño
        # requerido del tooltip ya esté calculado antes de fijar
        # su posición definitiva.
        self.ventana_ayuda.update_idletasks()

        posicion_x, posicion_y = calcular_posicion_ayuda(
            ancla_x=ancla_x,
            ancla_y=ancla_y,
            ancla_y_arriba=ancla_y_arriba,
            ancho=self.ventana_ayuda.winfo_reqwidth(),
            alto=self.ventana_ayuda.winfo_reqheight(),
            pantalla_ancho=self.control.winfo_screenwidth(),
            pantalla_alto=self.control.winfo_screenheight()
        )

        self.ventana_ayuda.wm_geometry(
            f"+{posicion_x}+{posicion_y}"
        )

    def ocultar(self, _evento=None):
        """Oculta la ayuda."""

        self.cancelar_programacion()

        if self.ventana_ayuda is None:
            return

        try:
            self.ventana_ayuda.destroy()
        except tk.TclError:
            pass

        self.ventana_ayuda = None


def configurar_estilos(ventana):
    """Configura una apariencia visual más clara."""

    estilos = ttk.Style(ventana)

    if "clam" in estilos.theme_names():
        estilos.theme_use("clam")

    ventana.configure(background="#F3F6F9")

    estilos.configure(".", font=("Segoe UI", 9))
    estilos.configure("TFrame", background="#F3F6F9")

    estilos.configure(
        "TLabelframe",
        background="#F3F6F9",
        bordercolor="#CBD5E1",
        relief="solid"
    )

    estilos.configure(
        "TLabelframe.Label",
        background="#F3F6F9",
        foreground="#334155",
        font=("Segoe UI", 9, "bold")
    )

    estilos.configure(
        "Titulo.TLabel",
        background="#F3F6F9",
        foreground="#0F172A",
        font=("Segoe UI", 20, "bold")
    )

    estilos.configure(
        "Subtitulo.TLabel",
        background="#F3F6F9",
        foreground="#64748B",
        font=("Segoe UI", 9)
    )

    estilos.configure(
        "AyudaVisible.TLabel",
        background="#EAF2FF",
        foreground="#1E3A5F",
        padding=(10, 7),
        font=("Segoe UI", 9)
    )

    estilos.configure(
        "EstadoSincronizacion.TLabel",
        background="#F8FAFC",
        foreground="#1F2937",
        padding=(10, 7),
        borderwidth=1,
        relief="solid"
    )

    estilos.configure(
        "Accion.TButton",
        padding=(10, 6),
        font=("Segoe UI", 9)
    )

    estilos.configure(
        "Fetch.TButton",
        background="#2563EB",
        foreground="white",
        padding=(14, 7),
        font=("Segoe UI", 9, "bold")
    )

    estilos.map(
        "Fetch.TButton",
        background=[("disabled", "#CBD5E1"), ("active", "#1D4ED8")],
        foreground=[("disabled", "#64748B"), ("active", "white")]
    )

    estilos.configure(
        "Pull.TButton",
        background="#0F766E",
        foreground="white",
        padding=(14, 7),
        font=("Segoe UI", 9, "bold")
    )

    estilos.map(
        "Pull.TButton",
        background=[("disabled", "#CBD5E1"), ("active", "#115E59")],
        foreground=[("disabled", "#64748B"), ("active", "white")]
    )

    estilos.configure(
        "Push.TButton",
        background="#7C3AED",
        foreground="white",
        padding=(14, 7),
        font=("Segoe UI", 9, "bold")
    )

    estilos.map(
        "Push.TButton",
        background=[("disabled", "#CBD5E1"), ("active", "#6D28D9")],
        foreground=[("disabled", "#64748B"), ("active", "white")]
    )

    estilos.configure(
        "Commit.TButton",
        background="#334155",
        foreground="white",
        padding=(12, 7),
        font=("Segoe UI", 9, "bold")
    )

    estilos.map(
        "Commit.TButton",
        background=[("disabled", "#CBD5E1"), ("active", "#1E293B")],
        foreground=[("disabled", "#64748B"), ("active", "white")]
    )

    return estilos
