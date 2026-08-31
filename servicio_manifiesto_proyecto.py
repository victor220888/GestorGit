"""
Servicio de carga y validacion del manifiesto compartido
de Modo Equipo Oracle V1.1.

La fuente autoritativa del manifiesto es la version committed en
HEAD del repositorio Oracle:

    HEAD:.gestorgit/proyecto.json

No se lee el working tree como fuente de autorizacion: una
modificacion local no commitida no puede redefinir
project_uuid, oracle_layout ni la identidad de los objetos.

V1.1 soporta 7 tipos Oracle: PACKAGE (.pls), PROCEDURE,
FUNCTION, TABLE, VIEW, TRIGGER y SEQUENCE (todos .sql).
El layout se define en el manifiesto y la validacion es
generica respecto a los catalogos de tipos y extensiones.

Reglas permanentes:

- shell=False
- sin GitPython
- sin red
- sin credenciales
- sin modificar el repositorio Oracle productivo
- sin crear el manifiesto real

Este servicio es de solo lectura y no modifica ningun repositorio.
"""

import json
import re
import uuid
from pathlib import Path

from modelos_reservas import (
    ManifiestoProyecto,
    ReglaLayoutOracle,
    ResultadoManifiestoProyecto,
    TIPOS_ORACLE_SOPORTADOS_V1,
    EXTENSIONES_ORACLE_SOPORTADAS_V1,
)


# Ruta relativa del manifiesto dentro del repositorio Oracle.
RUTA_MANIFIESTO_PROYECTO = ".gestorgit/proyecto.json"

# Version unica soportada por esta implementacion.
FORMAT_VERSION_SOPORTADO = 1

# Caracteres prohibidos dentro del nombre de una carpeta del layout.
# En V1 una carpeta es un nombre simple, no una ruta con separadores.
_CARACTERES_PROHIBIDOS_CARPETA = ("\x00", "\r", "\n", "/", "\\", ".")


def _es_uuid4_canonico(valor: str) -> bool:
    """
    Comprueba que valor es un UUID4 en representacion canonica
    en minusculas y con guiones.

    Ejemplo canonico:

        00000000-0000-4000-8000-000000000000
    """

    if not isinstance(valor, str):
        return False

    patron = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )

    if not patron.match(valor):
        return False

    try:
        u = uuid.UUID(valor)
    except (ValueError, AttributeError, TypeError):
        return False

    return u.version == 4 and str(u) == valor


def _es_carpeta_valida(carpeta: str) -> bool:
    """
    Valida una carpeta del layout V1.

    Reglas:

    - no vacia;
    - no '.' ni '..';
    - sin separadores '/' o '\\';
    - sin NUL, CR, LF;
    - sin componentes vacios.
    """

    if not isinstance(carpeta, str):
        return False

    if not carpeta:
        return False

    if carpeta in (".", ".."):
        return False

    for caracter in _CARACTERES_PROHIBIDOS_CARPETA:
        if caracter in carpeta:
            return False

    # Un nombre que tras quitar puntos terminales sigue siendo
    # vacio no es valido.
    if carpeta.strip() == "":
        return False

    return True


def _es_extension_valida(extension: str) -> bool:
    """
    Valida que una extension sea de la forma '.pls' (punto
    inicial seguido de al menos un caracter alfanumerico).
    """

    if not isinstance(extension, str):
        return False

    if not extension.startswith("."):
        return False

    if len(extension) < 2:
        return False

    resto = extension[1:]

    return resto.isalnum()


def _detectar_claves_duplicadas(texto: str) -> list[str]:
    """
    Detecta claves JSON duplicadas en cualquier nivel del texto.

    El modulo estandar json de Python, al parsear un objeto con
    claves repetidas, se queda con la ultima y descarta las
    anteriores de forma silenciosa. Para un manifiesto de
    identidad de proyecto esto es inaceptable: se debe rechazar
    el manifiesto.

    Se usa object_pairs_hook para interceptar cada objeto en el
    momento del parseo y detectar duplicados antes de que se
    construya el dict.
    """

    duplicadas: list[str] = []

    def _revisar_pares(pares):
        vistas: set[str] = set()
        for clave, _valor in pares:
            if clave in vistas:
                duplicadas.append(clave)
            else:
                vistas.add(clave)
        return dict(pares)

    try:
        json.loads(texto, object_pairs_hook=_revisar_pares)
    except json.JSONDecodeError:
        # El JSON invalido se reporta en otro sitio.
        return []

    return duplicadas


def _validar_regla_layout(
    carpeta: str,
    regla
) -> ReglaLayoutOracle | str:
    """
    Valida una regla individual del oracle_layout.

    Devuelve un ReglaLayoutOracle si es valida o una cadena
    con el mensaje de error si no lo es.
    """

    if not isinstance(regla, dict):
        return "La regla de layout debe ser un objeto JSON."

    # Campos esperados exactamente en V1:
    # tipo y extension.
    claves_esperadas = {"tipo", "extension"}
    claves_presentes = set(regla.keys())

    if claves_presentes != claves_esperadas:
        return (
            "La regla de layout debe contener exactamente "
            "los campos 'tipo' y 'extension'."
        )

    tipo = regla.get("tipo")
    extension = regla.get("extension")

    if not isinstance(tipo, str) or not tipo:
        return "El tipo Oracle no puede ser vacio."

    if tipo not in TIPOS_ORACLE_SOPORTADOS_V1:
        return (
            f"Tipo Oracle no soportado en V1: '{tipo}'. "
            f"Tipos soportados: {', '.join(TIPOS_ORACLE_SOPORTADOS_V1)}."
        )

    extension_esperada = EXTENSIONES_ORACLE_SOPORTADAS_V1.get(tipo, "")

    if not isinstance(extension, str) or not extension:
        return "La extension no puede ser vacia."

    if extension != extension_esperada:
        return (
            f"La extension '{extension}' no coincide con la "
            f"extension soportada para el tipo '{tipo}' "
            f"('{extension_esperada}')."
        )

    if not _es_carpeta_valida(carpeta):
        return (
            f"La carpeta '{carpeta}' no es un nombre de carpeta "
            f"valido para V1."
        )

    return ReglaLayoutOracle(
        carpeta=carpeta,
        tipo=tipo,
        extension=extension
    )


def _construir_manifiesto(datos: dict) -> ManifiestoProyecto | str:
    """
    Construye y valida un ManifiestoProyecto desde un dict
    ya parseado.

    Devuelve el manifiesto o una cadena con el mensaje de error.
    """

    if not isinstance(datos, dict):
        return "El manifiesto no es un objeto JSON."

    # En V1 se aceptan exactamente tres campos en la raiz.
    # Cualquier campo extra se rechaza para evitar ambiguedades.
    claves_raiz_esperadas = {"format_version", "project_uuid", "oracle_layout"}
    claves_raiz_presentes = set(datos.keys())

    if claves_raiz_presentes != claves_raiz_esperadas:
        extras = claves_raiz_presentes - claves_raiz_esperadas
        faltantes = claves_raiz_esperadas - claves_raiz_presentes

        if extras:
            return (
                f"El manifiesto contiene campos no reconocidos en V1: "
                f"{', '.join(sorted(extras))}."
            )

        if faltantes:
            return (
                f"El manifiesto falta campos obligatorios: "
                f"{', '.join(sorted(faltantes))}."
            )

    # format_version
    if "format_version" not in datos:
        return "Falta el campo 'format_version'."

    format_version = datos.get("format_version")

    if isinstance(format_version, bool):
        return "'format_version' debe ser un entero, no un booleano."

    if not isinstance(format_version, int):
        return "'format_version' debe ser un entero."

    if format_version != FORMAT_VERSION_SOPORTADO:
        return (
            f"format_version={format_version} no soportado. "
            f"Version soportada: {FORMAT_VERSION_SOPORTADO}."
        )

    # project_uuid
    if "project_uuid" not in datos:
        return "Falta el campo 'project_uuid'."

    project_uuid = datos.get("project_uuid")

    if not _es_uuid4_canonico(project_uuid):
        return (
            "'project_uuid' debe ser un UUID version 4 canonico "
            "en minusculas y con guiones."
        )

    # oracle_layout
    if "oracle_layout" not in datos:
        return "Falta el campo 'oracle_layout'."

    oracle_layout = datos.get("oracle_layout")

    if not isinstance(oracle_layout, dict):
        return "'oracle_layout' debe ser un objeto."

    if len(oracle_layout) == 0:
        return "'oracle_layout' no puede estar vacio."

    reglas: list[ReglaLayoutOracle] = []
    tipos_vistos: dict[str, str] = {}

    for carpeta, regla in oracle_layout.items():
        resultado_regla = _validar_regla_layout(carpeta, regla)

        if isinstance(resultado_regla, str):
            return (
                f"Regla invalida para la carpeta '{carpeta}': "
                f"{resultado_regla}"
            )

        # En V1 no se permite que dos carpetas diferentes
        # definan el mismo tipo.
        if resultado_regla.tipo in tipos_vistos:
            carpeta_anterior = tipos_vistos[resultado_regla.tipo]
            return (
                f"El tipo '{resultado_regla.tipo}' esta definido "
                f"para dos carpetas: '{carpeta_anterior}' y "
                f"'{carpeta}'. V1 no permite redefinir un mismo "
                f"tipo en varias carpetas."
            )

        tipos_vistos[resultado_regla.tipo] = carpeta
        reglas.append(resultado_regla)

    return ManifiestoProyecto(
        format_version=format_version,
        project_uuid=project_uuid,
        oracle_layout=tuple(reglas)
    )


class ServicioManifiestoProyecto:
    """
    Carga y valida el manifiesto compartido de proyecto desde
    la version committed en HEAD del repositorio Oracle.

    No lee el working tree como fuente de autorizacion.
    No hace red.
    No modifica el repositorio.
    """

    def __init__(self, servicio_git=None):
        """
        Crea el servicio.

        Parametros:
            servicio_git:
                ServicioGit reutilizable. Si es None se crea uno
                nuevo. Se acepta inyectarlo para facilitar las
                pruebas con repositorios temporales.
        """

        if servicio_git is None:
            from servicio_git import ServicioGit
            servicio_git = ServicioGit()

        self.servicio_git = servicio_git

    def leer_manifiesto_head(self, ruta_repositorio) -> ResultadoManifiestoProyecto:
        """
        Lee el manifiesto desde HEAD:.gestorgit/proyecto.json
        del repositorio indicado.

        Devuelve un ResultadoManifiestoProyecto controlado:
        nunca lanza excepciones hacia la capa llamadora.
        """

        # Validacion de la ruta del repositorio.
        if ruta_repositorio is None:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje="No se indico la ruta del repositorio."
            )

        try:
            ruta_texto = str(ruta_repositorio).strip()
        except (TypeError, ValueError):
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje="No se indico la ruta del repositorio."
            )

        if not ruta_texto:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje="No se indico la ruta del repositorio."
            )

        # Inspeccion inicial de la ruta de forma controlada:
        # una ruta patologicamente invalida o demasiado larga
        # no debe escapar como OSError/ValueError hacia la capa
        # llamadora.
        try:
            carpeta = Path(ruta_texto)

            existe = carpeta.exists()
            es_directorio = carpeta.is_dir() if existe else False
        except (OSError, ValueError):
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje=(
                    "La ruta del repositorio no es valida o no pudo "
                    "inspeccionarse de forma segura."
                )
            )

        if not existe:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje="La carpeta indicada no existe."
            )

        if not es_directorio:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje="La ruta indicada no corresponde a una carpeta."
            )

        # Confirmamos que es un repositorio Git.
        resultado_rev_parse = self.servicio_git.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--is-inside-work-tree"
            ],
            ruta_repositorio=carpeta
        )

        if (
            not resultado_rev_parse.exitoso
            or resultado_rev_parse.salida.strip().lower() != "true"
        ):
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje="La carpeta no corresponde a un repositorio Git."
            )

        # Verificamos que el repositorio tenga al menos un commit.
        # Sin HEAD no existe version committed del manifiesto.
        resultado_head = self.servicio_git.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--verify",
                "HEAD"
            ],
            ruta_repositorio=carpeta
        )

        if not resultado_head.exitoso:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje=(
                    "El repositorio no tiene HEAD: no existe ningun "
                    "commit del cual leer el manifiesto."
                )
            )

        # Leemos la version committed en HEAD del manifiesto.
        # Usamos git show HEAD:.gestorgit/proyecto.json para no
        # depender del working tree.
        resultado_show = self.servicio_git.ejecutar_git(
            argumentos=[
                "show",
                f"HEAD:{RUTA_MANIFIESTO_PROYECTO}"
            ],
            ruta_repositorio=carpeta
        )

        if not resultado_show.exitoso:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje=(
                    f"No existe '{RUTA_MANIFIESTO_PROYECTO}' en HEAD "
                    f"de este repositorio."
                )
            )

        contenido = resultado_show.salida

        if not contenido:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje=(
                    f"El manifiesto 'HEAD:{RUTA_MANIFIESTO_PROYECTO}' "
                    f"esta vacio."
                )
            )

        # ServicioGit.ejecutar_git decodifica la salida de Git como
        # UTF-8 con errors="replace". Por tanto, si el blob committed
        # contiene bytes UTF-8 invalidos, la salida puede incluir
        # U+FFFD (caracter de reemplazo). Un manifiesto de identidad
        # de proyecto no puede contener U+FFFD: se rechaza de forma
        # controlada y se pide al usuario que corrija el manifiesto.
        if "\ufffd" in contenido:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje=(
                    "El manifiesto contiene texto que no pudo "
                    "decodificarse como UTF-8 valido."
                )
            )

        # Detectamos claves duplicadas antes de confiar en json.loads,
        # que silenciosamente se quedaria con la ultima.
        duplicadas = _detectar_claves_duplicadas(contenido)

        if duplicadas:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje=(
                    f"El manifiesto contiene claves JSON duplicadas: "
                    f"{', '.join(sorted(set(duplicadas)))}. "
                    f"Un manifiesto de proyecto no puede tener claves "
                    f"duplicadas."
                )
            )

        # Parseamos el JSON.
        try:
            datos = json.loads(contenido)
        except json.JSONDecodeError as error:
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje=(
                    f"El manifiesto no contiene JSON valido: {error.msg}"
                )
            )

        # Validamos y construimos el manifiesto.
        resultado_construccion = _construir_manifiesto(datos)

        if isinstance(resultado_construccion, str):
            return ResultadoManifiestoProyecto(
                exitoso=False,
                mensaje=resultado_construccion
            )

        return ResultadoManifiestoProyecto(
            exitoso=True,
            mensaje="Manifiesto cargado correctamente.",
            manifiesto=resultado_construccion
        )
