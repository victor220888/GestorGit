"""
Modelos de datos para Modo Equipo Oracle V1.

Este modulo contiene los modelos estructurados que representan:

- la identidad canonica de un objeto Oracle (ClaveObjetoOracle);
- una regla del layout Oracle compartido (ReglaLayoutOracle);
- el manifiesto de proyecto versionado (ManifiestoProyecto);
- el resultado de cargar y validar el manifiesto
  (ResultadoManifiestoProyecto);
- el resultado de resolver una ruta a un objeto Oracle
  (ResultadoResolucionObjeto);
- modelos remotos de reservas: estados persistidos,
  clasificaciones observadas, payload V1, resultados estructurados
  y funciones auxiliares de validacion/serializacion.

Los modelos de Bloque A son puramente locales y deterministas.
Los modelos de Bloque D (reservas remotas) no dependen de Tkinter,
no hacen red, no leen Git directamente y no leen config.json.

Las operaciones Git y la orquestacion de reservas estan en
servicio_remoto_reservas.py y servicio_reservas.py.
"""

from dataclasses import dataclass, field


# Tipos Oracle soportados en V1.1.
# Cualquier tipo fuera de este conjunto hace que el manifiesto
# o la resolucion de un objeto se considere no soportado.
#
# Ampliar este conjunto requiere una tarea explicita y auditada
# (cambio compartido y versionado del manifiesto).
#
# V1.1 anade PROCEDURE, FUNCTION, TABLE, VIEW, TRIGGER y
# SEQUENCE (todos con extension .sql) al tipo PACKAGE original
# (extension .pls).
TIPOS_ORACLE_SOPORTADOS_V1 = (
    "PACKAGE",
    "PROCEDURE",
    "FUNCTION",
    "TABLE",
    "VIEW",
    "TRIGGER",
    "SEQUENCE",
)

# Extensiones soportadas por tipo en V1.1.
# La clave es el tipo Oracle y el valor es la extension
# (con punto inicial) que se acepta para ese tipo.
# PACKAGE usa .pls; los demas tipos usan .sql.
EXTENSIONES_ORACLE_SOPORTADAS_V1 = {
    "PACKAGE": ".pls",
    "PROCEDURE": ".sql",
    "FUNCTION": ".sql",
    "TABLE": ".sql",
    "VIEW": ".sql",
    "TRIGGER": ".sql",
    "SEQUENCE": ".sql",
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


# ==================================================================
# Bloque D: Modelos de reservas remotas
# ==================================================================

from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import uuid


# -- Modelos de reservas remotas (Bloque D) -------------------------------

# TTL canónico: reutiliza la fuente V1 existente en
# modelos_configuracion.py. No duplicar el valor mágico.
from modelos_configuracion import TTL_RESERVAS_SEGUNDOS_V1

FORMAT_VERSION_RESERVA_V1 = 1


# -- Clasificacion de reserva observada ------------------------------

class ClasificacionReservaObservada(Enum):
    """Clasificacion resultante de consultar el estado remoto."""

    LIBRE = "LIBRE"
    RESERVADO_POR_MI = "RESERVADO_POR_MI"
    RESERVADO_POR_OTRO = "RESERVADO_POR_OTRO"
    VENCIDO_PROPIO = "VENCIDO_PROPIO"
    VENCIDO_AJENO = "VENCIDO_AJENO"
    NO_VERIFICABLE = "NO_VERIFICABLE"
    RESULTADO_INCIERTO = "RESULTADO_INCIERTO"
    OPERACION_EN_CURSO = "OPERACION_EN_CURSO"


# -- Estado persistido -----------------------------------------------

class EstadoReservaPersistido(Enum):
    """Estados que puede tener un payload de reserva en el remoto."""

    ACTIVA = "ACTIVA"
    LIBERADA = "LIBERADA"


# -- Payload V1 de reserva -------------------------------------------

_CLAVES_PAYLOAD_RESERVA_V1 = frozenset({
    "format_version",
    "operation_id",
    "project_uuid",
    "clave_objeto",
    "estado",
    "id_cliente",
    "alias",
    "hostname",
    "user_name",
    "inicio",
    "heartbeat",
    "vencimiento",
    "rama_local",
    "rutas",
})


@dataclass
class ReservaPayloadV1:
    """Payload V1 de reserva serializado como reserva.json."""

    format_version: int
    operation_id: str
    project_uuid: str
    clave_objeto: str
    estado: EstadoReservaPersistido
    id_cliente: str
    alias: str
    hostname: str
    user_name: str
    inicio: str
    heartbeat: str
    vencimiento: str
    rama_local: str
    rutas: tuple

    def es_activa(self) -> bool:
        return self.estado is EstadoReservaPersistido.ACTIVA

    def es_liberada(self) -> bool:
        return self.estado is EstadoReservaPersistido.LIBERADA

    def serializar(self) -> str:
        """Serializa a JSON con claves ordenadas, sin CR/LF, con LF final."""
        data = {
            "format_version": self.format_version,
            "operation_id": self.operation_id,
            "project_uuid": self.project_uuid,
            "clave_objeto": self.clave_objeto,
            "estado": self.estado.value,
            "id_cliente": self.id_cliente,
            "alias": self.alias,
            "hostname": self.hostname,
            "user_name": self.user_name,
            "inicio": self.inicio,
            "heartbeat": self.heartbeat,
            "vencimiento": self.vencimiento,
            "rama_local": self.rama_local,
            "rutas": list(self.rutas),
        }
        return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + chr(10)


@dataclass
class ResultadoConsultaReserva:
    """Resultado de consultar el estado remoto de una reserva."""

    exitoso: bool
    clasificacion: ClasificacionReservaObservada
    payload: ReservaPayloadV1 | None = None
    parent: str = ""
    mensaje: str = ""
    error: str = ""


@dataclass
class ResultadoOperacionReserva:
    """Resultado de una operacion de reserva."""

    exitoso: bool
    operacion: str
    clasificacion: ClasificacionReservaObservada
    operation_id: str = ""
    parent: str = ""
    oid_publicado: str = ""
    mensaje: str = ""
    error: str = ""


@dataclass
class ResultadoValidacionReservaPropia:
    """Resultado de validar localmente una reserva propia fresca."""

    valida: bool
    motivo: str = ""
    tiempo_restante: int = 0
    edad_verificacion: int = 0


# -- Funciones auxiliares --------------------------------------------

def _es_uuid4_canonico(valor):
    """Devuelve True si valor es un UUID v4 canonico (str)."""
    if not isinstance(valor, str):
        return False
    try:
        obj = uuid.UUID(valor)
    except (ValueError, AttributeError):
        return False
    return str(obj) == valor and obj.version == 4


def _texto_plano_valido(valor, permitir_vacio=True):
    """Devuelve True si valor es str sin NUL, CR ni LF."""
    if not isinstance(valor, str):
        return False
    if not permitir_vacio and not valor:
        return False
    return chr(0) not in valor and chr(13) not in valor and chr(10) not in valor


def ahora_utc():
    """Instante UTC actual sin microsegundos."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def formatear_timestamp_utc(instante):
    """Formatea un datetime UTC como RFC3339 V1."""
    if instante is None:
        return ""
    return instante.strftime("%Y-%m-%dT%H:%M:%SZ")


def parsear_timestamp_utc(texto):
    """Parsea un timestamp RFC3339 V1 exacto a datetime UTC.

    Formato exigido: YYYY-MM-DDTHH:MM:SSZ

    Se rechazan variantes relajadas que strptime pudiera tolerar:
    microsegundos, offset +00:00, minutos/horas sin cero inicial,
    espacios, 'z' minúscula.

    Devuelve None si es inválido.
    """
    if not isinstance(texto, str) or not texto:
        return None
    # Validación léxica exacta: 19 caracteres, formato estricto.
    if len(texto) != 20 or texto[-1] != 'Z':
        return None
    if texto[4] != '-' or texto[7] != '-' or texto[10] != 'T':
        return None
    if texto[13] != ':' or texto[16] != ':':
        return None
    # Comprobar que cada campo numérico contiene solo dígitos.
    for i, length in [(0, 4), (5, 2), (8, 2), (11, 2), (14, 2), (17, 2)]:
        if not texto[i:i+length].isdigit():
            return None
    try:
        dt = datetime.strptime(texto, "%Y-%m-%dT%H:%M:%SZ")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def calcular_ref_reserva(project_uuid, clave_objeto):
    """Calcula el hash SHA-256 completo para la ref de reserva.

    Fórmula exacta de la arquitectura:

        sha256(project_uuid + "\0" + clave_objeto).hexdigest()
    """
    datos = project_uuid + "\0" + clave_objeto
    return hashlib.sha256(datos.encode("utf-8")).hexdigest()


def _validar_relaciones_temporales(estado, inicio, heartbeat, vencimiento, ttl_segundos):
    """
    Valida las relaciones temporales V1.

    ACTIVA:
        inicio <= heartbeat < vencimiento
        vencimiento - heartbeat == TTL

    LIBERADA:
        inicio <= heartbeat
        vencimiento == heartbeat
    """
    if estado is EstadoReservaPersistido.ACTIVA:
        diferencia = (vencimiento - heartbeat).total_seconds()
        if diferencia != ttl_segundos:
            return (
                False,
                "Relacion temporal ACTIVA invalida: "
                f"vencimiento - heartbeat = {diferencia} s, "
                f"se esperaba {ttl_segundos} s."
            )
        if not (inicio <= heartbeat < vencimiento):
            return (
                False,
                "Relacion temporal ACTIVA invalida: se exige "
                "inicio <= heartbeat < vencimiento."
            )
        return True, ""

    if estado is EstadoReservaPersistido.LIBERADA:
        if vencimiento != heartbeat:
            return (
                False,
                "Relacion temporal LIBERADA invalida: "
                "se exige vencimiento == heartbeat."
            )
        if inicio > heartbeat:
            return (
                False,
                "Relacion temporal LIBERADA invalida: "
                "se exige inicio <= heartbeat."
            )
        return True, ""

    return False, "Estado persistido no soportado."


def _validar_rutas(rutas):
    """
    Valida que rutas sea una lista de strings validos:
    sin duplicados, sin ruta absoluta, sin componentes '.' o '..'.
    """
    if not isinstance(rutas, list):
        return False, "rutas debe ser una lista."
    prev = None
    vistos = set()
    for r in rutas:
        if not _texto_plano_valido(r, permitir_vacio=False):
            return False, f"Ruta invalida: {r!r}"
        if (r.startswith("/") or r.startswith(chr(92))
                or (len(r) >= 2 and r[1] == ":")):
            return False, f"Ruta absoluta no permitida: {r!r}"
        partes = r.replace(chr(92), "/").split("/")
        if ".." in partes or "." in partes:
            return False, f"Ruta con componentes '.' o '..': {r!r}"
        if prev is not None and r < prev:
            return False, "Las rutas no estan en orden determinista."
        if r in vistos:
            return False, f"Rutas con duplicados: {r!r}"
        vistos.add(r)
        prev = r
    return True, ""


def validar_payload_reserva(datos, project_uuid_esperado=None, clave_objeto_esperada=None, ttl_segundos=TTL_RESERVAS_SEGUNDOS_V1):
    """
    Valida un dict JSON como payload V1 de reserva.

    Devuelve (ok, payload, mensaje). En caso de error, payload es
    None y mensaje explica el motivo. Nunca lanza excepciones
    previsibles.

    Reglas:

    - objeto raiz;
    - claves exactas del esquema V1 (sin faltantes ni extra);
    - claves duplicadas rechazadas por el parser del llamador;
    - format_version == 1;
    - operation_id / project_uuid / id_cliente UUID v4 canonico;
    - clave_objeto exacta (y coincidente si se espera una);
    - estado en {ACTIVA, LIBERADA};
    - timestamps RFC3339 V1;
    - relaciones temporales V1;
    - rutas validas, sin duplicados, orden determinista.
    """

    if not isinstance(datos, dict):
        return False, None, "El payload debe ser un objeto JSON."

    claves = set(datos.keys())
    if claves != _CLAVES_PAYLOAD_RESERVA_V1:
        faltan = sorted(_CLAVES_PAYLOAD_RESERVA_V1 - claves)
        extra = sorted(claves - _CLAVES_PAYLOAD_RESERVA_V1)
        return (
            False,
            None,
            "Esquema invalido: claves faltantes "
            f"{faltan}, claves extra {extra}."
        )

    format_version = datos["format_version"]
    if (
        isinstance(format_version, bool)
        or not isinstance(format_version, int)
        or format_version != FORMAT_VERSION_RESERVA_V1
    ):
        return (
            False,
            None,
            "format_version debe ser 1."
        )

    if not _es_uuid4_canonico(datos["operation_id"]):
        return False, None, "operation_id no es un UUID v4 canonico."

    if not _es_uuid4_canonico(datos["project_uuid"]):
        return False, None, "project_uuid no es un UUID v4 canonico."

    if (
        project_uuid_esperado is not None
        and datos["project_uuid"] != project_uuid_esperado
    ):
        return False, None, "project_uuid no coincide con la consulta."

    clave_objeto = datos["clave_objeto"]
    if not _texto_plano_valido(clave_objeto, permitir_vacio=False):
        return False, None, "clave_objeto invalida."

    if (
        clave_objeto_esperada is not None
        and clave_objeto != clave_objeto_esperada
    ):
        return False, None, "clave_objeto no coincide con la consulta."

    estado_texto = datos["estado"]
    if estado_texto not in (
        EstadoReservaPersistido.ACTIVA.value,
        EstadoReservaPersistido.LIBERADA.value,
    ):
        return False, None, "estado invalido."

    estado = EstadoReservaPersistido(estado_texto)

    if not _es_uuid4_canonico(datos["id_cliente"]):
        return False, None, "id_cliente no es un UUID v4 canonico."

    for etiqueta in ("alias", "hostname", "user_name", "rama_local"):
        if not _texto_plano_valido(datos[etiqueta]):
            return (
                False,
                None,
                f"{etiqueta} invalido (debe ser texto sin NUL/CR/LF)."
            )

    inicio = parsear_timestamp_utc(datos["inicio"])
    heartbeat = parsear_timestamp_utc(datos["heartbeat"])
    vencimiento = parsear_timestamp_utc(datos["vencimiento"])
    if inicio is None or heartbeat is None or vencimiento is None:
        return (
            False,
            None,
            "Timestamps invalidos: se exige RFC3339 V1 "
            "(YYYY-MM-DDTHH:MM:SSZ)."
        )

    ok_temporal, mensaje_temporal = _validar_relaciones_temporales(
        estado, inicio, heartbeat, vencimiento, ttl_segundos
    )
    if not ok_temporal:
        return False, None, mensaje_temporal

    ok_rutas, mensaje_rutas = _validar_rutas(datos["rutas"])
    if not ok_rutas:
        return False, None, mensaje_rutas

    payload = ReservaPayloadV1(
        format_version=format_version,
        operation_id=datos["operation_id"],
        project_uuid=datos["project_uuid"],
        clave_objeto=clave_objeto,
        estado=estado,
        id_cliente=datos["id_cliente"],
        alias=datos["alias"],
        hostname=datos["hostname"],
        user_name=datos["user_name"],
        inicio=datos["inicio"],
        heartbeat=datos["heartbeat"],
        vencimiento=datos["vencimiento"],
        rama_local=datos["rama_local"],
        rutas=tuple(datos["rutas"]),
    )
    return True, payload, ""
