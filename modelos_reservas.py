"""
Modelos de datos para Modo Equipo Oracle V1.

Este modulo contiene los modelos estructurados que representan:

- la identidad canonica de un objeto Oracle (ClaveObjetoOracle);
- una regla del layout Oracle compartido (ReglaLayoutOracle);
- el manifiesto de proyecto versionado (ManifiestoProyecto);
- el resultado de cargar y validar el manifiesto
  (ResultadoManifiestoProyecto);
- el resultado de resolver una ruta a un objeto Oracle
  (ResultadoResolucionObjeto).

Estos modelos son puramente locales y deterministas:
no dependen de Tkinter, no hacen red, no leen Git, no leen config.json.

El backend de reservas, los refs, los commits, los TTL, el id_cliente
y la GUI de Modo Equipo NO se implementan en este modulo.
"""

from dataclasses import dataclass, field


# Tipos Oracle soportados en V1.
# Cualquier tipo fuera de este conjunto hace que el manifiesto
# o la resolucion de un objeto se considiere no soportado.
#
# Ampliar este conjunto requiere una tarea explicita y auditada
# (cambio compartido y versionado del manifiesto).
TIPOS_ORACLE_SOPORTADOS_V1 = ("PACKAGE",)

# Extensiones soportadas por tipo en V1.
# La clave es el tipo Oracle y el valor es la extension
# (con punto inicial) que se acepta para ese tipo.
EXTENSIONES_ORACLE_SOPORTADAS_V1 = {
    "PACKAGE": ".pls",
}


@dataclass(frozen=True)
class ClaveObjetoOracle:
    """
    Identidad canonica de un objeto Oracle V1.

    La representacion canonica determinista es:

        TIPO|NOMBRE

    Por ejemplo:

        PACKAGE|FINI004

    El nombre se almacena en mayusculas y sin extension.
    No contiene rutas absolutas, nombres de PC, alias ni
    separadores dependientes de Windows.
    """

    tipo: str
    nombre: str

    def canonica(self) -> str:
        """
        Devuelve la representacion canonica determinista:

            TIPO|NOMBRE

        Ambos componentes en mayusculas.
        """

        return f"{self.tipo.upper()}|{self.nombre.upper()}"

    def __str__(self) -> str:
        return self.canonica()


@dataclass(frozen=True)
class ReglaLayoutOracle:
    """
    Una regla del layout Oracle compartido.

    Representa como una carpeta del repositorio se mapea
    a un tipo Oracle y una extension de archivo.

    La carpeta es relativa a la raiz del repositorio, sin
    ruta absoluta y sin componentes como '.' o '..'.
    """

    carpeta: str
    tipo: str
    extension: str


@dataclass(frozen=True)
class ManifiestoProyecto:
    """
    Manifiesto de proyecto versionado en el repositorio Oracle.

    Fuente autoritativa de la identidad compartida del proyecto
    y del layout Oracle. Se lee desde:

        HEAD:.gestorgit/proyecto.json

    Nunca desde el working tree.
    """

    format_version: int
    project_uuid: str
    oracle_layout: tuple[ReglaLayoutOracle, ...]

    def reglas_por_carpeta(self) -> dict[str, ReglaLayoutOracle]:
        """
        Devuelve un diccionario carpeta -> regla.
        """

        return {
            regla.carpeta: regla for regla in self.oracle_layout
        }


@dataclass
class ResultadoManifiestoProyecto:
    """
    Resultado controlado de la carga del manifiesto.

    Un error Git, JSON invalido o manifiesto no soportado
    no se eleva como excepcion: se representa como un resultado
    no exitoso con un mensaje pedagogico.
    """

    exitoso: bool
    mensaje: str = ""
    manifiesto: ManifiestoProyecto | None = None


@dataclass
class ResultadoResolucionObjeto:
    """
    Resultado de resolver una ruta a un objeto Oracle V1.

    Distingue tres situaciones:

    - La ruta no corresponde a un objeto Oracle (no Oracle).
    - La ruta corresponde a un objeto Oracle reservable.
    - La ruta tiene apariencia Oracle pero no se puede resolver
      de forma segura en V1 (Oracle no resoluble).

    En todos los casos el resultado es controlado: nunca se
    lanza una excepcion hacia la capa llamadora.
    """

    es_ruta_valida: bool
    es_objeto_oracle: bool
    es_reservable: bool
    objeto: ClaveObjetoOracle | None = None
    mensaje: str = ""

    @staticmethod
    def no_oracle(mensaje: str = "") -> "ResultadoResolucionObjeto":
        """
        Construye el resultado para una ruta que no es
        un objeto Oracle y por tanto no requiere reserva
        de Modo Equipo.
        """

        return ResultadoResolucionObjeto(
            es_ruta_valida=True,
            es_objeto_oracle=False,
            es_reservable=False,
            objeto=None,
            mensaje=mensaje
        )

    @staticmethod
    def reservable(objeto: ClaveObjetoOracle) -> "ResultadoResolucionObjeto":
        """
        Construye el resultado para una ruta que resuelve
        a un objeto Oracle reservable en V1.
        """

        return ResultadoResolucionObjeto(
            es_ruta_valida=True,
            es_objeto_oracle=True,
            es_reservable=True,
            objeto=objeto,
            mensaje=""
        )

    @staticmethod
    def oracle_no_resoluble(mensaje: str) -> "ResultadoResolucionObjeto":
        """
        Construye el resultado para una ruta con apariencia
        Oracle que no puede resolverse de forma segura en V1.

        La operacion protegida futura debe BLOQUEAR.
        """

        return ResultadoResolucionObjeto(
            es_ruta_valida=True,
            es_objeto_oracle=True,
            es_reservable=False,
            objeto=None,
            mensaje=mensaje
        )

    @staticmethod
    def ruta_invalida(mensaje: str) -> "ResultadoResolucionObjeto":
        """
        Construye el resultado para una ruta invalida
        (absoluta, con '..', con NUL, etc.).
        """

        return ResultadoResolucionObjeto(
            es_ruta_valida=False,
            es_objeto_oracle=False,
            es_reservable=False,
            objeto=None,
            mensaje=mensaje
        )


@dataclass
class ResultadoRenombradoObjeto:
    """
    Resultado de evaluar un rename/move de una o dos rutas
    Oracle.

    Si ambas rutas son objetos Oracle reservables, se devuelven
    las claves involucradas sin duplicados.

    Si cualquiera de las rutas Oracle implicadas no es resoluble
    de forma segura, el resultado es fail-safe y la operacion
    protegida futura debe bloquear.
    """

    es_resoluble: bool
    rutas_invalidas: list[str] = field(default_factory=list)
    rutas_no_resolvibles: list[str] = field(default_factory=list)
    claves: list[ClaveObjetoOracle] = field(default_factory=list)
    mensaje: str = ""
