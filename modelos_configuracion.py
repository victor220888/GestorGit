"""
Modelos de datos de la configuración de Gestor Git.

La configuración recuerda únicamente el último repositorio
seleccionado por el usuario.

Nunca guarda credenciales, tokens, correos, URLs de remotos
ni información de Git Credential Manager.
"""

from dataclasses import dataclass


@dataclass
class ResultadoConfiguracion:
    """
    Resultado de una operación de lectura o escritura
    de la configuración.
    """

    exitoso: bool
    ruta_repositorio: str = ""
    mensaje: str = ""
    error: str = ""