"""
Servicio de resolucion segura de objetos Oracle V1.

Recibe un ManifiestoProyecto ya validado y resuelve rutas
relativas Git a objetos Oracle.

Este servicio:

- no lee red;
- no lee config.json;
- no modifica Git;
- no crea reservas;
- no crea refs;
- no hace Push.

Solo resuelve identidades de objetos y produce un
ResultadoResolucionObjeto controlado.
"""

import hashlib
import re
from pathlib import PurePosixPath

from modelos_reservas import (
    ClaveObjetoOracle,
    ManifiestoProyecto,
    ResultadoResolucionObjeto,
    ResultadoRenombradoObjeto,
    EXTENSIONES_ORACLE_SOPORTADAS_V1,
)


# Extensiones consideradas familia Oracle potencial.
# Solo .pls esta soportada en V1; el resto se reconoce
# como familia Oracle pero NO resoluble de forma segura.
EXTENSIONES_FAMILIA_ORACLE = {".pls", ".pks", ".pkb", ".sql"}

# Regla de nombre seguro de identificador Oracle V1.
# Conservadora: letra inicial, luego letras, digitos, _, $, #.
# No se aceptan identificadores entrecomillados en V1.
_PATRON_NOMBRE_ORACLE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*$")


def _ruta_es_valida(ruta: str) -> bool:
    """
    Valida que una ruta sea relativa y no intente salir
    de la raiz del repositorio.
    """

    if not isinstance(ruta, str):
        return False

    if not ruta:
        return False

    # NUL, CR, LF no permitidos.
    for caracter in ("\x00", "\r", "\n"):
        if caracter in ruta:
            return False

    # Rutas absolutas con unidad Windows (C:, D:, ...) no validas.
    if len(ruta) >= 2 and ruta[1] == ":":
        return False

    # Rutas absolutas con barra inicial no validas.
    if ruta.startswith("/") or ruta.startswith("\\"):
        return False

    # Normalizar separadores Windows a Posix para validacion.
    ruta_norm = ruta.replace("\\", "/")

    # No permitir .. como componente.
    componentes = ruta_norm.split("/")

    for componente in componentes:
        if componente == "..":
            return False

    # PurePosixPath rechaza componentes vacios consecutivos pero
    # acepta rutas como "a//b". Las rutas con componentes vacios
    # no son validas en V1.
    if "//" in ruta_norm:
        return False

    return True


def _normalizar_ruta(ruta: str) -> str:
    """
    Normaliza separadores Windows a Posix para comparacion
    interna determinista.
    """

    return ruta.replace("\\", "/")


def _es_nombre_oracle_valido(nombre: str) -> bool:
    """
    Comprueba que un nombre base es un identificador Oracle
    seguro en V1.
    """

    if not isinstance(nombre, str) or not nombre:
        return False

    return bool(_PATRON_NOMBRE_ORACLE.match(nombre))


def _es_carpeta_mapeada(
    ruta_normalizada: str,
    manifiesto: ManifiestoProyecto
) -> str | None:
    """
    Devuelve el nombre de la carpeta mapeada si la ruta
    empieza por una carpeta del layout, o None si no.

    En V1 una carpeta del layout es un nombre simple (sin
    subcarpetas). La coincidencia debe ser exacta con el
    primer componente de la ruta.
    """

    componentes = ruta_normalizada.split("/")

    if not componentes:
        return None

    carpeta = componentes[0]

    reglas = manifiesto.reglas_por_carpeta()

    if carpeta in reglas:
        return carpeta

    return None


def _extender_extension(nombre: str, extension: str) -> bool:
    """
    Comprueba si nombre termina exactamente en extension.
    """

    return nombre.endswith(extension)


class ServicioObjetosOracle:
    """
    Resuelve rutas relativas Git a objetos Oracle V1 usando
    exclusivamente el layout compartido del manifiesto.

    No inventa tipos, esquemas ni rutas no mapeadas.
    """

    def __init__(self, manifiesto: ManifiestoProyecto):
        """
        Crea el servicio con un manifiesto ya validado.

        El manifiesto debe ser valido; si es None se lanza
        ValueError porque un servicio sin manifiesto no
        puede resolver nada de forma segura.
        """

        if manifiesto is None:
            raise ValueError(
                "ServicioObjetosOracle requiere un "
                "ManifiestoProyecto valido."
            )

        self.manifiesto = manifiesto

    def resolver(self, ruta: str) -> ResultadoResolucionObjeto:
        """
        Resuelve una ruta relativa Git a un objeto Oracle.

        Devuelve un ResultadoResolucionObjeto controlado:
        nunca lanza excepciones hacia la capa llamadora.
        """

        # 1. Validacion de la ruta.
        if not _ruta_es_valida(ruta):
            return ResultadoResolucionObjeto.ruta_invalida(
                f"La ruta '{ruta}' no es una ruta relativa valida."
            )

        ruta_norm = _normalizar_ruta(ruta)

        # 2. Carpeta mapeada?
        carpeta = _es_carpeta_mapeada(ruta_norm, self.manifiesto)

        # 3. Nombre del archivo.
        nombre_archivo = ruta_norm.split("/")[-1]

        # 4. Extension del archivo.
        #    Se usa PurePosixPath para obtener el sufijo de forma
        #    determinista.
        sufijo = PurePosixPath(nombre_archivo).suffix.lower()

        # 5. Extension de la familia Oracle?
        if carpeta is None:
            # Si la carpeta no esta mapeada pero el archivo tiene
            # una extension Oracle, lo marcamos como Oracle no
            # resoluble. Si no, no es Oracle.
            if sufijo in EXTENSIONES_FAMILIA_ORACLE:
                return ResultadoResolucionObjeto.oracle_no_resoluble(
                    f"La ruta '{ruta}' tiene apariencia Oracle "
                    f"(extension {sufijo}) pero la carpeta no esta "
                    f"mapeada en el manifiesto del proyecto. "
                    f"No puede determinarse TIPO|NOMBRE de forma "
                    f"segura en V1."
                )

            return ResultadoResolucionObjeto.no_oracle(
                f"La ruta '{ruta}' no corresponde a un objeto "
                f"Oracle segun el manifiesto del proyecto."
            )

        # 6. La carpeta esta mapeada. Recuperamos la regla.
        regla = self.manifiesto.reglas_por_carpeta()[carpeta]

        # 7. La extension del archivo coincide con la del layout?
        if sufijo != regla.extension.lower():
            # Si la extension es de la familia Oracle pero no
            # coincide con la del layout, es Oracle no resoluble.
            if sufijo in EXTENSIONES_FAMILIA_ORACLE:
                return ResultadoResolucionObjeto.oracle_no_resoluble(
                    f"La ruta '{ruta}' esta en la carpeta mapeada "
                    f"'{carpeta}' pero su extension '{sufijo}' no "
                    f"coincide con la extension soportada "
                    f"'{regla.extension}' para el tipo '{regla.tipo}'. "
                    f"No puede determinarse TIPO|NOMBRE de forma "
                    f"segura en V1."
                )

            # Extension no Oracle: no es objeto Oracle.
            return ResultadoResolucionObjeto.no_oracle(
                f"La ruta '{ruta}' no tiene una extension Oracle "
                f"reconocida por el manifiesto del proyecto."
            )

        # 8. Subcarpetas no soportadas en V1.
        #    Una carpeta mapeada es un nombre simple; si la ruta
        #    tiene mas de dos componentes (carpeta/archivo) no
        #    es resoluble.
        componentes = ruta_norm.split("/")

        if len(componentes) != 2:
            return ResultadoResolucionObjeto.oracle_no_resoluble(
                f"La ruta '{ruta}' esta dentro de la carpeta "
                f"mapeada '{carpeta}' pero contiene subcarpetas. "
                f"V1 solo soporta {carpeta}/<NOMBRE>{regla.extension} "
                f"sin niveles intermedios."
            )

        # 9. Nombre base sin la extension.
        #    Comparamos la extension de forma case-insensitive
        #    (Windows: .PLS y .pls son el mismo tipo de archivo)
        #    pero extraemos el nombre base usando el sufijo real
        #    del archivo.
        if not nombre_archivo.lower().endswith(regla.extension.lower()):
            return ResultadoResolucionObjeto.oracle_no_resoluble(
                f"El archivo '{nombre_archivo}' no termina en "
                f"'{regla.extension}'."
            )

        #    El sufijo real puede tener mayusculas; usamos su
        #    longitud para extraer el nombre base.
        sufijo_real = PurePosixPath(nombre_archivo).suffix
        nombre_base = nombre_archivo[: -len(sufijo_real)]

        if not nombre_base:
            return ResultadoResolucionObjeto.oracle_no_resoluble(
                f"El archivo '{nombre_archivo}' no tiene un nombre "
                f"valido antes de la extension '{regla.extension}'."
            )

        # 10. El backup de PL/SQL Developer (.~pls) no debe
        #     confundirse con un .pls valido.
        if nombre_base.endswith("~"):
            return ResultadoResolucionObjeto.oracle_no_resoluble(
                f"El archivo '{nombre_archivo}' parece un backup "
                f"(*.{regla.extension.lstrip('.')}) y no un "
                f"objeto Oracle resoluble de forma segura."
            )

        # 11. Validar el nombre Oracle.
        if not _es_nombre_oracle_valido(nombre_base):
            return ResultadoResolucionObjeto.oracle_no_resoluble(
                f"El nombre '{nombre_base}' no es un identificador "
                f"Oracle valido en V1."
            )

        # 12. Normalizar a mayusculas y construir la clave.
        nombre_mayusculas = nombre_base.upper()

        clave = ClaveObjetoOracle(
            tipo=regla.tipo,
            nombre=nombre_mayusculas
        )

        return ResultadoResolucionObjeto.reservable(clave)

    def resolver_renombrado(
        self,
        ruta_actual: str,
        ruta_anterior: str | None = None
    ) -> ResultadoRenombradoObjeto:
        """
        Resuelve un rename/move evaluando la ruta actual y,
        si existe, la ruta anterior.

        Devuelve las claves involucradas sin duplicados.

        Si cualquiera de las rutas Oracle implicadas no es
        resoluble de forma segura, el resultado es fail-safe
        y la operacion protegida futura debe bloquear.
        """

        rutas_invalidas: list[str] = []
        rutas_no_resolvibles: list[str] = []
        claves: list[ClaveObjetoOracle] = []

        # Resolver ruta actual.
        resultado_actual = self.resolver(ruta_actual)

        if not resultado_actual.es_ruta_valida:
            rutas_invalidas.append(ruta_actual)
        elif resultado_actual.es_objeto_oracle and not resultado_actual.es_reservable:
            rutas_no_resolvibles.append(ruta_actual)
        elif resultado_actual.es_reservable and resultado_actual.objeto is not None:
            if resultado_actual.objeto not in claves:
                claves.append(resultado_actual.objeto)

        # Resolver ruta anterior si existe.
        if ruta_anterior is not None and ruta_anterior != "":
            resultado_anterior = self.resolver(ruta_anterior)

            if not resultado_anterior.es_ruta_valida:
                rutas_invalidas.append(ruta_anterior)
            elif resultado_anterior.es_objeto_oracle and not resultado_anterior.es_reservable:
                rutas_no_resolvibles.append(ruta_anterior)
            elif resultado_anterior.es_reservable and resultado_anterior.objeto is not None:
                if resultado_anterior.objeto not in claves:
                    claves.append(resultado_anterior.objeto)

        es_resoluble = (
            len(rutas_invalidas) == 0
            and len(rutas_no_resolvibles) == 0
        )

        mensaje = ""

        if not es_resoluble:
            partes = []
            if rutas_invalidas:
                partes.append(
                    f"Rutas invalidas: {', '.join(rutas_invalidas)}"
                )
            if rutas_no_resolvibles:
                partes.append(
                    f"Rutas Oracle no resolubles: "
                    f"{', '.join(rutas_no_resolvibles)}"
                )
            mensaje = "; ".join(partes)

        return ResultadoRenombradoObjeto(
            es_resoluble=es_resoluble,
            rutas_invalidas=rutas_invalidas,
            rutas_no_resolvibles=rutas_no_resolvibles,
            claves=claves,
            mensaje=mensaje
        )


def calcular_ref_reserva(
    project_uuid: str,
    clave_objeto: ClaveObjetoOracle
) -> str:
    """
    Calcula el identificador determinista del ref de reserva
    aprobado en la arquitectura V1.

    sha256(
        project_uuid + "\\0" + clave_objeto_canonica
    ).hexdigest()

    Devuelve exactamente 64 caracteres hexadecimales
    en minusculas.

    No crea refs Git.
    No hace Push.
    No prefija con refs/heads/...
    """

    if not isinstance(project_uuid, str) or not project_uuid:
        raise ValueError("project_uuid debe ser un texto no vacio.")

    if not isinstance(clave_objeto, ClaveObjetoOracle):
        raise ValueError("clave_objeto debe ser un ClaveObjetoOracle.")

    contenido = (
        project_uuid
        + "\x00"
        + clave_objeto.canonica()
    )

    return hashlib.sha256(
        contenido.encode("utf-8")
    ).hexdigest()


# Patron estricto del hash de un ref de reserva:
# exactamente 64 caracteres hexadecimales en minusculas.
_PATRON_HASH_RESERVA = re.compile(r"^[0-9a-f]{64}$")


def ref_reserva_completo(hash_reserva: str) -> str:
    """
    Construye el nombre completo del ref remoto de reservas
    a partir del hash SHA-256.

    Acepta exclusivamente:

    - str;
    - longitud 64;
    - hexadecimal;
    - minusculas;
    - sin '/', '\\', '..', espacios ni mayusculas.

    No crea el ref ni lo escribe en Git.
    """

    if not isinstance(hash_reserva, str):
        raise ValueError(
            "hash_reserva debe ser un texto de 64 caracteres "
            "hexadecimales en minusculas."
        )

    if not _PATRON_HASH_RESERVA.match(hash_reserva):
        raise ValueError(
            "hash_reserva debe ser un texto de 64 caracteres "
            "hexadecimales en minusculas."
        )

    return f"refs/heads/gestorgit-reservas/{hash_reserva}"
