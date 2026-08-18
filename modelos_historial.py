from dataclasses import dataclass, field


@dataclass
class CommitGit:
    """
    Representa un commit mostrado en el historial.

    El historial es solamente informativo. Este modelo no contiene
    ninguna operación que modifique el repositorio.
    """

    hash_completo: str
    hash_corto: str
    fecha_iso: str
    autor: str
    correo: str
    mensaje: str


@dataclass
class ResultadoHistorial:
    """
    Resultado de una consulta del historial de commits.
    """

    exitoso: bool
    commits: list[CommitGit] = field(default_factory=list)
    mensaje: str = ""
    error: str = ""


@dataclass
class ResultadoExportacion:
    """
    Resultado de exportar el historial de commits a un archivo.
    """

    exitoso: bool
    ruta_archivo: str = ""
    mensaje: str = ""
    error: str = ""
