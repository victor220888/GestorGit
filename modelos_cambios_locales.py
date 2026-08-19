from dataclasses import dataclass, field


@dataclass
class DetalleCambioLocal:
    """
    Información estructurada de los cambios locales de un archivo.

    Contiene tanto el diff sin preparar (working tree -> índice)
    como el diff preparado (índice -> HEAD), además de los
    resúmenes calculados mediante --numstat.
    """

    ruta: str = ""
    descripcion: str = ""
    preparado: bool = False
    requiere_actualizar_preparado: bool = False

    diff_sin_preparar: str = ""
    diff_preparado: str = ""

    inserciones_sin_preparar: int = 0
    eliminaciones_sin_preparar: int = 0

    inserciones_preparadas: int = 0
    eliminaciones_preparadas: int = 0

    binario_sin_preparar: bool = False
    binario_preparado: bool = False

    # True cuando el archivo es nuevo (??) y todavía no está
    # preparado: Git no tiene una versión anterior para comparar.
    nuevo_sin_preparar: bool = False

    # True cuando el par de códigos de git status corresponde a
    # un conflicto de merge (DD, AU, UD, UA, DU, AA, UU).
    # Se calcula desde los códigos estructurados, nunca desde
    # el texto localizado de descripcion.
    en_conflicto: bool = False

    hash_commit: str = ""
    mensaje_commit: str = ""


@dataclass
class ResultadoDetalleCambioLocal:
    """
    Resultado de consultar los cambios locales de un archivo.

    Un archivo sin cambios pendientes NO es un error: la consulta
    devuelve exitoso=True con detalle=None y un mensaje informativo.
    """

    exitoso: bool
    detalle: DetalleCambioLocal = None
    error: str = ""
    mensaje: str = ""