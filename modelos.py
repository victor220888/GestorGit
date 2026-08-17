from dataclasses import dataclass, field


@dataclass
class ResultadoComando:
    """
    Representa el resultado obtenido al ejecutar un comando Git.
    """

    exitoso: bool
    codigo_salida: int
    salida: str
    error: str
    comando: str


@dataclass
class EstadoRepositorio:
    """
    Representa la información general de un repositorio Git.

    Esta clase solamente contiene información.
    No ejecuta ningún comando ni modifica archivos.
    """

    es_repositorio: bool

    # Carpeta raíz real del repositorio.
    ruta_raiz: str = ""

    # Rama sobre la que estamos trabajando.
    rama_actual: str = ""

    # Indica si el repositorio ya tiene al menos un commit.
    tiene_commits: bool = False

    # Lista de remotos configurados, por ejemplo: origin.
    remotos: list[str] = field(default_factory=list)

    # Mensaje sencillo para mostrar al usuario.
    mensaje: str = ""