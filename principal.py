import tkinter as tk
from tkinter import ttk


class AplicacionGit:
    """
    Ventana principal de la aplicación Gestor Git.

    Esta clase se encargará de crear y controlar
    la interfaz gráfica de nuestra aplicación.
    """

    def __init__(self, ventana_principal):
        # Guardamos la referencia de la ventana principal.
        self.ventana_principal = ventana_principal

        # Configuramos las propiedades de la ventana.
        self.configurar_ventana()

        # Creamos los controles visibles.
        self.crear_interfaz()

    def configurar_ventana(self):
        """Configura las propiedades generales de la ventana."""

        # Título que aparecerá en la barra superior.
        self.ventana_principal.title("Gestor Git")

        # Tamaño inicial de la ventana.
        self.ventana_principal.geometry("900x600")

        # Tamaño mínimo permitido.
        self.ventana_principal.minsize(700, 450)

    def crear_interfaz(self):
        """Crea los controles iniciales de la aplicación."""

        # Marco principal que contendrá todos los controles.
        marco_principal = ttk.Frame(
            self.ventana_principal,
            padding=20
        )

        marco_principal.pack(
            fill=tk.BOTH,
            expand=True
        )

        # Título principal.
        etiqueta_titulo = ttk.Label(
            marco_principal,
            text="Gestor Git",
            font=("Segoe UI", 18, "bold")
        )

        etiqueta_titulo.pack(
            pady=(0, 10)
        )

        # Mensaje que nos permitirá comprobar
        # que la aplicación inició correctamente.
        etiqueta_estado = ttk.Label(
            marco_principal,
            text="Aplicación iniciada correctamente."
        )

        etiqueta_estado.pack(
            pady=10
        )

        # Botón para cerrar la aplicación.
        boton_cerrar = ttk.Button(
            marco_principal,
            text="Cerrar",
            command=self.ventana_principal.destroy
        )

        boton_cerrar.pack(
            pady=20
        )


def iniciar_aplicacion():
    """Crea la ventana principal e inicia Tkinter."""

    # Creamos la ventana raíz de Tkinter.
    ventana_principal = tk.Tk()

    # Creamos nuestra aplicación.
    AplicacionGit(ventana_principal)

    # Iniciamos el ciclo de eventos.
    # Este ciclo mantiene la ventana abierta.
    ventana_principal.mainloop()


if __name__ == "__main__":
    iniciar_aplicacion()