"""
Servicio de validación de contenido SQL ↔ archivo Oracle (V1.2).

Segunda evidencia de identidad para el Modo Equipo Oracle:

- EVIDENCIA 1 (V1.1): la ruta/carpeta/extensión/nombre resuelve a
  TIPO|NOMBRE (ServicioObjetosOracle, sin cambios);
- EVIDENCIA 2 (V1.2, este servicio): el contenido CREATE... del
  archivo declara un TIPO|NOMBRE.

Para operaciones protegidas ambas evidencias deben concordar.

Este servicio es deliberadamente conservador y NO es un parser
completo de PL/SQL:

- si detecta con certeza -> permite comparar;
- si hay contradicción -> NO_COINCIDE_NOMBRE / NO_COINCIDE_TIPO;
- si hay ambigüedad -> AMBIGUO;
- si no puede verificar -> NO_VERIFICABLE;
- sin contenido que comparar -> NO_APLICA.

Reglas léxicas:

- localiza declaraciones CREATE soportadas FUERA de comentarios
  de línea (--), comentarios de bloque (/* */) y literales
  'string' (con escape '');
- los literales alternativos Oracle q'...' / Q'...' / nq'...' /
  NQ'...' (delimitadores emparejados [], {}, (), <> o simple de
  un carácter) se consumen completos sin exponer su contenido
  interno al detector de CREATE; si están mal cerrados o no
  pueden interpretarse con certeza el resultado es
  NO_VERIFICABLE (fail-closed, sin recuperación parcial);
- reconoce CREATE [OR REPLACE] con gramática positiva por tipo:
  EDITIONABLE/NONEDITIONABLE (tipos editables), FORCE / NO FORCE
  (solo VIEW) y GLOBAL TEMPORARY (solo TABLE); cualquier otra
  combinación de modificadores hace que la sentencia se ignore
  (no inventa identidad);
- PACKAGE BODY <nombre> se normaliza a PACKAGE|<nombre> (no
  habilita .pks/.pkb ni identidades separadas spec/body);
- tolera sintácticamente SCHEMA.OBJETO con punto adyacente
  comparando solo el objeto;
- los identificadores entrecomillados quedan fuera de alcance:
  su presencia produce NO_VERIFICABLE;
- la comparación es case-insensitive sobre la canonización vigente
  (mayúsculas), sin crear una segunda regla de normalización.

Política de decodificación conservadora (entorno Windows):

- BOM UTF-8 -> decode utf-8-sig estricto (sin alternativa);
- sin BOM -> UTF-8 estricto y, si falla, Windows-1252 estricto;
- sin errors="replace" nunca;
- BOM UTF-16, bytes NUL o decodificación imposible -> NO_VERIFICABLE.

Este servicio:

- no lee archivos ni Git (recibe contenido en bytes);
- no hace red;
- no modifica la identidad canónica TIPO|NOMBRE;
- no lanza excepciones como mecanismo normal de clasificación
  (los resultados son estructurados y controlados).
"""

import re
from dataclasses import dataclass

from modelos_reservas import (
    ClaveObjetoOracle,
    TIPOS_ORACLE_SOPORTADOS_V1,
)


# Estados del resultado de validación.
COINCIDE = "COINCIDE"
NO_COINCIDE_NOMBRE = "NO_COINCIDE_NOMBRE"
NO_COINCIDE_TIPO = "NO_COINCIDE_TIPO"
AMBIGUO = "AMBIGUO"
NO_VERIFICABLE = "NO_VERIFICABLE"
NO_APLICA = "NO_APLICA"


_TIPOS_SOPORTADOS = frozenset(TIPOS_ORACLE_SOPORTADOS_V1)

# Gramática positiva de modificadores por tipo (REV1 R2): tras
# CREATE [OR REPLACE] SOLO se aceptan exactamente estas
# secuencias de tokens antes del tipo. Cualquier otra
# combinación (cruzada, duplicada o imposible) hace que la
# sentencia se ignore por completo: nunca se inventa identidad.
_SECUENCIAS_EDICION = (
    (),
    ("EDITIONABLE",),
    ("NONEDITIONABLE",),
)
_SECUENCIAS_MODIFICADORES = {
    "PACKAGE": frozenset(_SECUENCIAS_EDICION),
    "PROCEDURE": frozenset(_SECUENCIAS_EDICION),
    "FUNCTION": frozenset(_SECUENCIAS_EDICION),
    "TRIGGER": frozenset(_SECUENCIAS_EDICION),
    "VIEW": frozenset(
        _SECUENCIAS_EDICION
        + (
            ("FORCE",),
            ("NO", "FORCE"),
            ("EDITIONABLE", "FORCE"),
            ("EDITIONABLE", "NO", "FORCE"),
            ("NONEDITIONABLE", "FORCE"),
            ("NONEDITIONABLE", "NO", "FORCE"),
        )
    ),
    "TABLE": frozenset(((), ("GLOBAL", "TEMPORARY"))),
    "SEQUENCE": frozenset(((),)),
}

# Identificador Oracle simple sin comillas (misma regla de nombre
# seguro usada por ServicioObjetosOracle). El lookbehind evita
# encontrar CREATE dentro de un token más largo.
_PATRON_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_$#])[A-Za-z][A-Za-z0-9_$#]*"
)

_BOM_UTF8 = b"\xef\xbb\xbf"
_BOM_UTF16_LE = b"\xff\xfe"
_BOM_UTF16_BE = b"\xfe\xff"

_MENSAJE_NO_VERIFICABLE = (
    "No se pudo verificar de forma segura el objeto declarado "
    "en el archivo."
)


@dataclass
class DeteccionContenidoOracle:
    """
    Resultado controlado de la detección de identidades en el
    contenido SQL (sin comparar contra ninguna ruta).

    exitoso:
        True solo si se detectó al menos una identidad soportada
        sin encontrar identificadores entrecomillados.
    identidades:
        Tupla de cadenas canónicas "TIPO|NOMBRE" en mayúsculas,
        en orden de aparición y sin duplicados.
    nombre_entrecomillado:
        True si apareció un identificador entrecomillado en una
        declaración soportada (fuera de alcance en V1.2).
    motivo:
        Texto pedagógico cuando la detección no fue posible.
    """

    exitoso: bool
    identidades: tuple = ()
    nombre_entrecomillado: bool = False
    motivo: str = ""


@dataclass
class ResultadoValidacionContenido:
    """
    Resultado controlado de la validación contenido ↔ ruta.

    resultado:
        Uno de los estados COINCIDE, NO_COINCIDE_NOMBRE,
        NO_COINCIDE_TIPO, AMBIGUO, NO_VERIFICABLE o NO_APLICA.
    tipo_ruta / nombre_ruta:
        Identidad esperada según la ruta.
    tipo_detectado / nombre_detectado:
        Identidad detectada en el contenido cuando existe una
        única identidad verificable; vacío en caso contrario.
    motivo:
        Texto pedagógico del resultado; vacío si COINCIDE.
    """

    resultado: str
    tipo_ruta: str = ""
    nombre_ruta: str = ""
    tipo_detectado: str = ""
    nombre_detectado: str = ""
    motivo: str = ""

    @staticmethod
    def coincidir(tipo_ruta, nombre_ruta, tipo_detectado,
                  nombre_detectado):
        """Construye el resultado de coincidencia exacta."""

        return ResultadoValidacionContenido(
            resultado=COINCIDE,
            tipo_ruta=tipo_ruta,
            nombre_ruta=nombre_ruta,
            tipo_detectado=tipo_detectado,
            nombre_detectado=nombre_detectado,
            motivo="",
        )

    @staticmethod
    def no_coincide(tipo_ruta, nombre_ruta, tipo_detectado,
                    nombre_detectado, estado, motivo):
        """Construye un resultado de contradicción."""

        return ResultadoValidacionContenido(
            resultado=estado,
            tipo_ruta=tipo_ruta,
            nombre_ruta=nombre_ruta,
            tipo_detectado=tipo_detectado,
            nombre_detectado=nombre_detectado,
            motivo=motivo,
        )

    @staticmethod
    def no_verificable(tipo_ruta, nombre_ruta, motivo):
        """Construye un resultado NO_VERIFICABLE."""

        return ResultadoValidacionContenido(
            resultado=NO_VERIFICABLE,
            tipo_ruta=tipo_ruta,
            nombre_ruta=nombre_ruta,
            motivo=motivo,
        )


def _decodificar_contenido(contenido):
    """
    Política de decodificación conservadora.

    Devuelve (texto, motivo). texto es None cuando el contenido
    no puede decodificarse con certeza (NO_VERIFICABLE).
    """

    if contenido.startswith(_BOM_UTF16_LE) or contenido.startswith(
        _BOM_UTF16_BE
    ):
        return (
            None,
            (
                "El contenido usa una codificación UTF-16, no "
                "soportada en V1.2."
            ),
        )

    if contenido.startswith(_BOM_UTF8):
        try:
            return (contenido.decode("utf-8-sig"), "")
        except UnicodeDecodeError:
            return (
                None,
                (
                    "El contenido declara BOM UTF-8 pero no es "
                    "UTF-8 válido; no puede decodificarse con "
                    "certeza."
                ),
            )

    try:
        return (contenido.decode("utf-8"), "")
    except UnicodeDecodeError:
        pass

    try:
        return (contenido.decode("cp1252"), "")
    except UnicodeDecodeError:
        return (
            None,
            (
                "El contenido no es UTF-8 ni Windows-1252 "
                "válido; no puede decodificarse con certeza."
            ),
        )


def _es_inicio_q_quote(texto, i):
    """
    True si el apóstrofo en la posición i abre un literal
    alternativo Oracle q'...' / Q'...' / nq'...' / NQ'...'.

    La q/Q (o nq/NQ) debe estar inmediatamente antes del
    apóstrofo y no puede ser la cola de un identificador más
    largo (p. ej. mi_varq'...' no es un q-quote).
    """

    def _es_caracter_identificador(caracter):
        return caracter.isalnum() or caracter in "_$#"

    # nq / NQ
    if i >= 2 and texto[i - 2:i].lower() == "nq":
        if i == 2 or not _es_caracter_identificador(texto[i - 3]):
            return True

    # q / Q
    if i >= 1 and texto[i - 1].lower() == "q":
        if i == 1 or not _es_caracter_identificador(texto[i - 2]):
            return True

    return False


_PARES_DELIMITADOR_QQUOTE = {
    "[": "]",
    "{": "}",
    "(": ")",
    "<": ">",
}


def _consumir_q_quote(texto, i):
    """
    Consume un literal alternativo Oracle a partir del apóstrofo
    inicial en la posición i (q'<delim>...<delim>').

    Devuelve (cerrado, posicion_siguiente). cerrado es False
    cuando el literal está mal cerrado o usa un delimitador no
    interpretable con certeza: en ese caso el contenido restante
    no se recupera parcialmente (fail-closed).
    """

    if i + 1 >= len(texto):
        return (False, len(texto))

    apertura = texto[i + 1]

    if apertura == "'":
        # Un apóstrofo no puede actuar de delimitador propio.
        return (False, len(texto))

    if apertura.isspace():
        # Delimitador blanco: forma no válida.
        return (False, len(texto))

    if apertura in _PARES_DELIMITADOR_QQUOTE:
        cierre = _PARES_DELIMITADOR_QQUOTE[apertura]
        busqueda = cierre + "'"
        fin = texto.find(busqueda, i + 2)

        if fin == -1:
            return (False, len(texto))

        return (True, fin + 2)

    # Delimitador simple de un carácter: q'!texto!'
    busqueda = apertura + "'"
    fin = texto.find(busqueda, i + 2)

    if fin == -1:
        return (False, len(texto))

    return (True, fin + 2)


def _limpiar_comentarios_y_strings(texto):
    """
    Devuelve (texto_limpio, malformado) con comentarios de línea
    (--), comentarios de bloque (/* */), literales 'string' (con
    escape '') y literales alternativos Oracle q'...' / Q'...' /
    nq'...' / NQ'...' ya consumidos, de modo que solo quede
    código observable.

    El contenido interno de los literales alternativos (con
    apóstrofes simples sin escape incluidos) NUNCA se expone al
    detector de CREATE.

    Un comentario, literal o q-quote sin cerrar deja malformado
    en True (interpretación conservadora: el archivo no puede
    verificarse con certeza y NO se recupera parcialmente).
    """

    largo = len(texto)
    salida = []
    i = 0

    while i < largo:
        par = texto[i:i + 2]

        if par == "--":
            # Comentario de línea: se omite hasta el salto real.
            salto = texto.find("\n", i)

            if salto == -1:
                i = largo
            else:
                salida.append("\n")
                i = salto + 1

            continue

        if par == "/*":
            cierre = texto.find("*/", i + 2)

            if cierre == -1:
                return ("".join(salida), True)

            salida.append(" ")
            i = cierre + 2

            continue

        if texto[i] == "'":
            # Literal alternativo Oracle: consumido completo sin
            # exponer su contenido.
            if _es_inicio_q_quote(texto, i):
                cerrado, siguiente = _consumir_q_quote(texto, i)

                if not cerrado:
                    return ("".join(salida), True)

                salida.append(" ")
                i = siguiente

                continue

            # Literal SQL con escape '' entre comillas simples.
            i += 1
            cerrado = False

            while i < largo:
                if texto[i] == "'":
                    if i + 1 < largo and texto[i + 1] == "'":
                        i += 2
                        continue

                    i += 1
                    cerrado = True
                    break

                i += 1

            if not cerrado:
                return ("".join(salida), True)

            salida.append(" ")
            continue

        salida.append(texto[i])
        i += 1

    return "".join(salida), False


def _token_entrecomillado(texto_limpio, token):
    """
    True si el token va inmediatamente precedido de una comilla
    doble (inicio de identificador entrecomillado). Las cadenas
    SQL ya fueron eliminadas, así que toda comilla doble restante
    corresponde a un identificador entrecomillado.
    """

    inicio = token[1]

    return inicio > 0 and texto_limpio[inicio - 1] == '"'


def _extraer_identidades(texto_limpio, tokens):
    """
    Recorre los tokens del texto limpio y extrae las identidades
    "TIPO|NOMBRE" de las declaraciones CREATE soportadas.

    Devuelve (identidades, nombre_entrecomillado).

    Una sentencia cuya construcción no se reconoce se ignora sin
    inventar identidad: un archivo con solo esas sentencias
    producirá "sin CREATE soportado" (NO_VERIFICABLE).
    """

    identidades = []
    entrecomillado = False
    total = len(tokens)
    i = 0

    while i < total:
        if tokens[i][0] != "CREATE":
            i += 1
            continue

        j = i + 1

        # CREATE [OR REPLACE] ...
        if j < total and tokens[j][0] == "OR":
            if j + 1 < total and tokens[j + 1][0] == "REPLACE":
                j += 2
            else:
                i += 1
                continue

        # Gramática positiva (REV1 R2): se recolectan los tokens
        # previos al tipo y la sentencia SOLO se acepta si esa
        # secuencia está autorizada para ESE tipo concreto.
        modificadores = []

        while (
            j < total
            and tokens[j][0] not in _TIPOS_SOPORTADOS
            and len(modificadores) < 4
        ):
            modificadores.append(tokens[j][0])
            j += 1

        if j >= total or tokens[j][0] not in _TIPOS_SOPORTADOS:
            # Sin tipo soportado recognizable: la sentencia se
            # ignora (no se inventa identidad).
            i += 1
            continue

        tipo = tokens[j][0]
        j += 1

        if (
            tuple(modificadores)
            not in _SECUENCIAS_MODIFICADORES[tipo]
        ):
            # Secuencia de modificadores no autorizada para este
            # tipo (cruzada, duplicada o imposible): la sentencia
            # se ignora por completo.
            i += 1
            continue

        # PACKAGE BODY <nombre> se normaliza a PACKAGE|<nombre>.
        if (
            tipo == "PACKAGE"
            and j < total
            and tokens[j][0] == "BODY"
        ):
            j += 1

        if j >= total:
            i += 1
            continue

        # Nombre con schema opcional: SCHEMA.OBJETO. El punto no
        # es un token: se detecta adyacente en el texto limpio.
        if (
            j < total
            and texto_limpio[tokens[j][2]:tokens[j][2] + 1] == "."
            and j + 1 < total
        ):
            if _token_entrecomillado(texto_limpio, tokens[j]):
                entrecomillado = True

            indice_nombre = j + 1
            indice_avance = j + 2
        else:
            indice_nombre = j
            indice_avance = j + 1

        if indice_nombre >= total:
            i += 1
            continue

        if _token_entrecomillado(
            texto_limpio, tokens[indice_nombre]
        ):
            entrecomillado = True
            i = indice_avance
            continue

        # Más de un nivel calificado (o un punto final suelto):
        # construcción no soportada, la sentencia se ignora.
        fin_nombre = tokens[indice_nombre][2]

        if texto_limpio[fin_nombre:fin_nombre + 1] == ".":
            i = indice_avance
            continue

        identidad = (
            f"{tipo}|{tokens[indice_nombre][0]}"
        )

        if identidad not in identidades:
            identidades.append(identidad)

        i = indice_avance

    return identidades, entrecomillado


class ServicioValidacionContenidoOracle:
    """
    Valida que el contenido SQL de un archivo Oracle concuerde con
    la identidad TIPO|NOMBRE resuelta por la ruta.

    El contenido se recibe ya leído (bytes exactos del working
    tree o del blob preparado según la operación); este servicio
    nunca accede al filesystem ni a Git.
    """

    def detectar(self, contenido):
        """
        Detecta las identidades "TIPO|NOMBRE" declaradas en el
        contenido (bytes) sin comparar contra ninguna ruta.

        Nunca lanza excepciones previsibles: los problemas se
        representan con exitoso=False y un motivo pedagógico.
        """

        if not isinstance(contenido, (bytes, bytearray)):
            return DeteccionContenidoOracle(
                exitoso=False,
                motivo=(
                    "El contenido recibido no es legible como "
                    "bytes del archivo."
                ),
            )

        contenido = bytes(contenido)

        texto, motivo = _decodificar_contenido(contenido)

        if texto is None:
            return DeteccionContenidoOracle(
                exitoso=False,
                motivo=motivo,
            )

        if "\x00" in texto:
            return DeteccionContenidoOracle(
                exitoso=False,
                motivo=(
                    "El contenido parece binario o UTF-16 sin "
                    "BOM; no puede verificarse con certeza."
                ),
            )

        texto_limpio, malformado = _limpiar_comentarios_y_strings(
            texto
        )

        if malformado:
            return DeteccionContenidoOracle(
                exitoso=False,
                motivo=(
                    "El contenido tiene un comentario, literal o "
                    "literal alternativo Oracle (q'...') sin "
                    "cerrar o no interpretable con certeza; no "
                    "puede verificarse de forma segura."
                ),
            )

        tokens = [
            (coincidencia.group(0).upper(),
             coincidencia.start(),
             coincidencia.end())
            for coincidencia in _PATRON_TOKEN.finditer(texto_limpio)
        ]

        identidades, entrecomillado = _extraer_identidades(
            texto_limpio, tokens
        )

        if entrecomillado:
            return DeteccionContenidoOracle(
                exitoso=False,
                identidades=tuple(identidades),
                nombre_entrecomillado=True,
                motivo=(
                    "Se encontró un identificador entrecomillado "
                    "en una declaración soportada; los "
                    "identificadores entrecomillados quedan "
                    "fuera de alcance en V1.2."
                ),
            )

        if not identidades:
            return DeteccionContenidoOracle(
                exitoso=False,
                motivo=(
                    "No se encontró ninguna declaración CREATE "
                    "soportada en el contenido."
                ),
            )

        return DeteccionContenidoOracle(
            exitoso=True,
            identidades=tuple(identidades),
        )

    def validar(self, clave_objeto, contenido):
        """
        Compara la identidad detectada en el contenido con la
        identidad esperada según la ruta.

        clave_objeto:
            ClaveObjetoOracle o cadena canónica "TIPO|NOMBRE".
        contenido:
            Bytes exactos del archivo/blob; None representa la
            ausencia de contenido (NO_APLICA).

        Devuelve un ResultadoValidacionContenido controlado.
        """

        tipo_ruta, nombre_ruta, clave_invalida = (
            self._normalizar_clave_ruta(clave_objeto)
        )

        if clave_invalida:
            return ResultadoValidacionContenido.no_verificable(
                tipo_ruta,
                nombre_ruta,
                "La identidad de la ruta no es una clave Oracle "
                "canónica válida.",
            )

        if contenido is None:
            return ResultadoValidacionContenido(
                resultado=NO_APLICA,
                tipo_ruta=tipo_ruta,
                nombre_ruta=nombre_ruta,
                motivo=(
                    "No existe contenido que comparar para esta "
                    "operación."
                ),
            )

        deteccion = self.detectar(contenido)

        if not deteccion.exitoso:
            motivo = deteccion.motivo or _MENSAJE_NO_VERIFICABLE

            return ResultadoValidacionContenido.no_verificable(
                tipo_ruta,
                nombre_ruta,
                motivo,
            )

        if deteccion.nombre_entrecomillado:
            return ResultadoValidacionContenido.no_verificable(
                tipo_ruta,
                nombre_ruta,
                deteccion.motivo,
            )

        if len(deteccion.identidades) > 1:
            lista = ", ".join(deteccion.identidades)

            return ResultadoValidacionContenido(
                resultado=AMBIGUO,
                tipo_ruta=tipo_ruta,
                nombre_ruta=nombre_ruta,
                motivo=(
                    "El archivo contiene varias declaraciones "
                    f"soportadas distintas ({lista}); el "
                    "contenido no puede atribuirse a una única "
                    "identidad."
                ),
            )

        tipo_detectado, nombre_detectado = (
            deteccion.identidades[0].split("|", 1)
        )

        if tipo_detectado != tipo_ruta:
            return ResultadoValidacionContenido.no_coincide(
                tipo_ruta,
                nombre_ruta,
                tipo_detectado,
                nombre_detectado,
                NO_COINCIDE_TIPO,
                (
                    "El contenido del archivo declara "
                    f"{tipo_detectado}|{nombre_detectado}, pero "
                    f"la ruta corresponde a {tipo_ruta}|"
                    f"{nombre_ruta}: el tipo de objeto declarado "
                    "no coincide con el tipo de la ruta."
                ),
            )

        if nombre_detectado != nombre_ruta:
            return ResultadoValidacionContenido.no_coincide(
                tipo_ruta,
                nombre_ruta,
                tipo_detectado,
                nombre_detectado,
                NO_COINCIDE_NOMBRE,
                (
                    "El contenido del archivo declara "
                    f"{tipo_detectado}|{nombre_detectado}, pero "
                    f"la ruta corresponde a {tipo_ruta}|"
                    f"{nombre_ruta}: el nombre del archivo no "
                    "coincide con el objeto declarado."
                ),
            )

        return ResultadoValidacionContenido.coincidir(
            tipo_ruta,
            nombre_ruta,
            tipo_detectado,
            nombre_detectado,
        )

    @staticmethod
    def _normalizar_clave_ruta(clave_objeto):
        """
        Normaliza la identidad de la ruta aceptando un
        ClaveObjetoOracle o una cadena canónica "TIPO|NOMBRE".

        Devuelve (tipo, nombre, invalida) en mayúsculas.
        """

        if isinstance(clave_objeto, ClaveObjetoOracle):
            return (
                clave_objeto.tipo.upper(),
                clave_objeto.nombre.upper(),
                False,
            )

        if isinstance(clave_objeto, str):
            partes = clave_objeto.split("|")

            if (
                len(partes) == 2
                and partes[0]
                and partes[1]
            ):
                return (
                    partes[0].strip().upper(),
                    partes[1].strip().upper(),
                    False,
                )

        return ("", "", True)
