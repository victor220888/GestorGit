from dataclasses import dataclass, field


@dataclass
class ResultadoComando:
    """
    Representa el resultado de ejecutar un comando Git.
    """

    exitoso: bool
    codigo_salida: int
    salida: str
    error: str
    comando: str


@dataclass
class EstadoRepositorio:
    """
    Contiene información general de un repositorio Git.
    """

    es_repositorio: bool
    ruta_raiz: str = ""
    rama_actual: str = ""
    tiene_commits: bool = False
    remotos: list[str] = field(default_factory=list)
    mensaje: str = ""


@dataclass
class CambioArchivo:
    """
    Representa un archivo que tiene cambios dentro del repositorio.
    """

    ruta: str
    estado_indice: str
    estado_trabajo: str
    descripcion: str
    preparado: bool
    ruta_anterior: str = ""


@dataclass
class ResultadoCambios:
    """
    Contiene el resultado de consultar los archivos modificados.
    """

    exitoso: bool
    cambios: list[CambioArchivo] = field(default_factory=list)
    error: str = ""


@dataclass
class EstadoSincronizacion:
    """
    Representa la relación entre la rama local
    y la información conocida de la rama remota.
    """

    exitoso: bool

    rama_local: str = ""
    remoto: str = ""
    rama_remota: str = ""

    upstream_configurado: bool = False
    rama_remota_existe: bool = False

    commits_por_subir: int = 0
    commits_por_bajar: int = 0

    divergente: bool = False

    mensaje: str = ""
    error: str = ""