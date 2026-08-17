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
    """

    es_repositorio: bool

    # Carpeta raíz real del repositorio.
    ruta_raiz: str = ""

    # Rama sobre la que estamos trabajando.
    rama_actual: str = ""

    # Indica si el repositorio ya tiene al menos un commit.
    tiene_commits: bool = False

    # Lista de remotos configurados.
    remotos: list[str] = field(default_factory=list)

    # Mensaje sencillo para mostrar al usuario.
    mensaje: str = ""


@dataclass
class CambioArchivo:
    """
    Representa un archivo que tiene algún cambio dentro de Git.

    Git maneja dos estados principales:

    estado_indice:
        Estado del archivo preparado para el próximo commit.

    estado_trabajo:
        Estado del archivo que todavía permanece en la carpeta
        de trabajo y no fue preparado.
    """

    # Ruta relativa del archivo dentro del repositorio.
    ruta: str

    # Estado informado por Git para el área preparada.
    estado_indice: str

    # Estado informado por Git para el área de trabajo.
    estado_trabajo: str

    # Descripción comprensible para el usuario.
    descripcion: str

    # True si el archivo tiene algún cambio preparado para commit.
    preparado: bool

    # Se utiliza principalmente cuando un archivo fue renombrado.
    ruta_anterior: str = ""


@dataclass
class ResultadoCambios:
    """
    Representa el resultado de consultar los archivos modificados.
    """

    exitoso: bool

    # Lista de archivos encontrados.
    cambios: list[CambioArchivo] = field(default_factory=list)

    # Mensaje de error, si ocurrió alguno.
    error: str = ""