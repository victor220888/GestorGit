"""
Servicio de persistencia de la configuracion de Gestor Git.

Responsabilidades:

- recordar el ultimo repositorio local seleccionado (config.json);
- recordar la configuracion local del Modo Equipo Oracle V1
  (modo_equipo_habilitado, backend_reservas_url, alias_equipo
  y los tiempos canonicos V1);
- preservar las claves desconocidas del JSON en toda escritura
  exitosa (no destruye campos futuros ni de terceros);
- no crear nunca campos de credenciales, token, password ni
  correo.

La identidad tecnica de instalacion (id_cliente) NO vive aqui:
vive en %APPDATA%\\GestorGit\\identidad_instalacion.json y la
gestiona ServicioIdentidadEquipo.

La escritura es conservadora: primero se escribe un archivo
temporal en la misma carpeta y despues se reemplaza config.json
mediante os.replace, evitando dejar un JSON parcialmente escrito
si la aplicacion se interrumpe.

Este servicio no ejecuta operaciones remotas ni usa shell=True.
"""

import json
import os
import urllib.parse
from pathlib import Path

from modelos_configuracion import (
    ConfiguracionModoEquipo,
    ResultadoConfiguracion,
    ResultadoConfiguracionModoEquipo,
    TTL_RESERVAS_SEGUNDOS_V1,
    RENOVACION_RESERVAS_SEGUNDOS_V1,
    MARGEN_MINIMO_RESERVA_SEGUNDOS_V1,
    FRESCURA_RESERVAS_SEGUNDOS_V1,
    MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS_V1,
)
from servicio_git import ServicioGit

# Caracteres que no pueden aparecer en una ruta guardada.
_CARACTERES_NO_VALIDOS = ("\x00", "\r", "\n")

# Claves conocidas de config.json. Cualquier otra clave se
# preserva como desconocida en las escrituras.
_CLAVE_RUTA_REPOSITORIO = "ruta_repositorio"
_CLAVE_MODO_EQUIPO_HABILITADO = "modo_equipo_habilitado"
_CLAVE_BACKEND_RESERVAS_URL = "backend_reservas_url"
_CLAVE_ALIAS_EQUIPO = "alias_equipo"
_CLAVE_TTL_RESERVAS_SEGUNDOS = "ttl_reservas_segundos"
_CLAVE_RENOVACION_RESERVAS_SEGUNDOS = "renovacion_reservas_segundos"
_CLAVE_MARGEN_MINIMO_RESERVA_SEGUNDOS = (
    "margen_minimo_reserva_segundos"
)
_CLAVE_FRESCURA_RESERVAS_SEGUNDOS = "frescura_reservas_segundos"
_CLAVE_MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS = (
    "margen_gracia_vencimiento_segundos"
)

_CLAVES_MODO_EQUIPO = frozenset({
    _CLAVE_MODO_EQUIPO_HABILITADO,
    _CLAVE_BACKEND_RESERVAS_URL,
    _CLAVE_ALIAS_EQUIPO,
    _CLAVE_TTL_RESERVAS_SEGUNDOS,
    _CLAVE_RENOVACION_RESERVAS_SEGUNDOS,
    _CLAVE_MARGEN_MINIMO_RESERVA_SEGUNDOS,
    _CLAVE_FRESCURA_RESERVAS_SEGUNDOS,
    _CLAVE_MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS,
})

_CLAVES_CONOCIDAS = frozenset(
    {_CLAVE_RUTA_REPOSITORIO} | set(_CLAVES_MODO_EQUIPO)
)

# Valores temporales canonicos V1. No admiten divergencia
# silenciosa: un valor presente en config.json que no coincida
# con el canonico se rechaza de forma controlada.
_TIEMPOS_CANONICOS_V1 = {
    _CLAVE_TTL_RESERVAS_SEGUNDOS: TTL_RESERVAS_SEGUNDOS_V1,
    _CLAVE_RENOVACION_RESERVAS_SEGUNDOS: RENOVACION_RESERVAS_SEGUNDOS_V1,
    _CLAVE_MARGEN_MINIMO_RESERVA_SEGUNDOS: (
        MARGEN_MINIMO_RESERVA_SEGUNDOS_V1
    ),
    _CLAVE_FRESCURA_RESERVAS_SEGUNDOS: FRESCURA_RESERVAS_SEGUNDOS_V1,
    _CLAVE_MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS: (
        MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS_V1
    ),
}

# Esquemas de URL de backend admitidos en V1.
_ESQUEMAS_BACKEND_ADMITIDOS = ("http", "https")


def _detectar_claves_duplicadas(pairs):
    """
    Hook para json.loads que rechaza claves duplicadas
    en cualquier nivel del objeto JSON.
    """

    vistos = set()
    resultado = {}
    for clave, valor in pairs:
        if clave in vistos:
            raise ValueError(
                f"Clave duplicada en JSON: {clave!r}"
            )
        vistos.add(clave)
        resultado[clave] = valor
    return resultado


def _contiene_caracteres_no_validos(texto):
    """
    Comprueba si un texto contiene NUL, CR o LF.
    """

    return any(c in texto for c in _CARACTERES_NO_VALIDOS)


def _validar_backend_url_detallado(url):
    """
    Valida una URL de backend de reservas.

    Devuelve None si es valida o un mensaje de error.
    La URL vacia es valida a nivel de sintaxis (la regla de
    no vacio cuando el modo esta habilitado la aplica el
    llamador).

    Reglas V1:

    - sin credenciales embebidas (usuario:password@ o token@);
    - sin esquemas SSH (ssh://, git+ssh://, ssh+git://);
    - sin sintaxis scp-like (usuario@host:ruta);
    - sin query ni fragment;
    - esquema http o https;
    - netloc y path no vacios.
    """

    if not isinstance(url, str):
        return "backend_reservas_url debe ser texto."

    if _contiene_caracteres_no_validos(url):
        return "backend_reservas_url no puede contener NUL, CR o LF."

    url_limpia = url.strip()
    if not url_limpia:
        return None

    # Ningun espacio ni espacio en blanco interno: urlparse los
    # toleraria dentro del host o de la ruta y no deben llegar
    # nunca a Git.
    if any(caracter.isspace() for caracter in url_limpia):
        return (
            "backend_reservas_url no puede contener espacios "
            "ni espacios en blanco internos."
        )

    url_minuscula = url_limpia.lower()
    if (
        url_minuscula.startswith("ssh://")
        or url_minuscula.startswith("git+ssh://")
        or url_minuscula.startswith("ssh+git://")
    ):
        return (
            "Las URLs SSH no se admiten en V1: configure SSH "
            "externamente."
        )

    if "://" not in url_minuscula:
        if "@" in url_limpia.split("/", 1)[0]:
            return (
                "Las URLs scp-like (usuario@host:ruta) no se "
                "admiten en V1."
            )
        return (
            "backend_reservas_url debe incluir un esquema "
            "(http:// o https://)."
        )

    try:
        parsed = urllib.parse.urlparse(url_limpia)
    except ValueError as error:
        return (
            f"backend_reservas_url no es una URL valida: {error}"
        )

    if parsed.scheme.lower() not in _ESQUEMAS_BACKEND_ADMITIDOS:
        return (
            "Solo se admiten esquemas http y https en V1 para "
            "backend_reservas_url."
        )

    if parsed.username or parsed.password:
        return (
            "backend_reservas_url no puede contener credenciales "
            "embebidas (usuario:password@ o token@)."
        )

    # La mera presencia de ? o # se rechaza aunque query/fragment
    # parseen como vacios: una URL de backend no los necesita.
    if "?" in url_limpia:
        return (
            "backend_reservas_url no puede contener query."
        )

    if "#" in url_limpia:
        return (
            "backend_reservas_url no puede contener fragment."
        )

    if not parsed.netloc:
        return (
            "backend_reservas_url incompleta: falta el host."
        )

    # urlparse no valida el puerto: el acceso controlado a
    # hostname/port detecta puertos no numericos o fuera de
    # rango (ValueError) sin dejar escapar la excepcion.
    try:
        hostname = parsed.hostname
        puerto = parsed.port
    except ValueError as error:
        return (
            f"backend_reservas_url no es una URL valida: {error}"
        )

    if not hostname:
        return (
            "backend_reservas_url incompleta: falta el host."
        )

    if not parsed.path:
        return (
            "backend_reservas_url incompleta: falta la ruta "
            "del repositorio."
        )

    return None


def _parsear_modo_equipo_de_dict(datos):
    """
    Construye una ConfiguracionModoEquipo desde un dict crudo
    de config.json aplicando defaults V1 a las claves ausentes
    y validando estrictamente las presentes.

    Devuelve (config, None) o (None, mensaje_error).
    """

    config = ConfiguracionModoEquipo()

    if _CLAVE_MODO_EQUIPO_HABILITADO in datos:
        valor = datos[_CLAVE_MODO_EQUIPO_HABILITADO]
        if not isinstance(valor, bool):
            return None, (
                "modo_equipo_habilitado debe ser true o false."
            )
        config.modo_equipo_habilitado = valor

    if _CLAVE_BACKEND_RESERVAS_URL in datos:
        valor = datos[_CLAVE_BACKEND_RESERVAS_URL]
        if not isinstance(valor, str):
            return None, (
                "backend_reservas_url debe ser texto."
            )
        if _contiene_caracteres_no_validos(valor):
            return None, (
                "backend_reservas_url no puede contener NUL, "
                "CR o LF."
            )
        config.backend_reservas_url = valor

    if _CLAVE_ALIAS_EQUIPO in datos:
        valor = datos[_CLAVE_ALIAS_EQUIPO]
        if not isinstance(valor, str):
            return None, "alias_equipo debe ser texto."
        if _contiene_caracteres_no_validos(valor):
            return None, (
                "alias_equipo no puede contener NUL, CR o LF."
            )
        config.alias_equipo = valor

    for clave, canonico in _TIEMPOS_CANONICOS_V1.items():
        if clave in datos:
            valor = datos[clave]
            if isinstance(valor, bool) or not isinstance(valor, int):
                return None, (
                    f"{clave} debe ser un entero (no un bool)."
                )
            if valor != canonico:
                return None, (
                    f"{clave} no admite un valor distinto del "
                    f"canonico V1 ({canonico})."
                )
            setattr(config, clave, valor)

    if (
        config.modo_equipo_habilitado
        and not config.backend_reservas_url.strip()
    ):
        return None, (
            "backend_reservas_url no puede estar vacio cuando "
            "el Modo Equipo esta habilitado."
        )

    error_url = _validar_backend_url_detallado(
        config.backend_reservas_url
    )
    if error_url:
        return None, error_url

    return config, None


def _validar_config_modo_equipo_para_guardar(config):
    """
    Valida una ConfiguracionModoEquipo aportada por el
    llamador antes de guardarla.

    Devuelve (config_limpio, None) o (None, mensaje_error).
    """

    if not isinstance(config, ConfiguracionModoEquipo):
        return None, "config debe ser ConfiguracionModoEquipo."

    if not isinstance(config.modo_equipo_habilitado, bool):
        return None, "modo_equipo_habilitado debe ser true o false."

    if not isinstance(config.backend_reservas_url, str):
        return None, "backend_reservas_url debe ser texto."

    if _contiene_caracteres_no_validos(config.backend_reservas_url):
        return None, (
            "backend_reservas_url no puede contener NUL, CR o LF."
        )

    if not isinstance(config.alias_equipo, str):
        return None, "alias_equipo debe ser texto."

    if _contiene_caracteres_no_validos(config.alias_equipo):
        return None, "alias_equipo no puede contener NUL, CR o LF."

    for clave, canonico in _TIEMPOS_CANONICOS_V1.items():
        valor = getattr(config, clave)
        if isinstance(valor, bool) or not isinstance(valor, int):
            return None, (
                f"{clave} debe ser un entero (no un bool)."
            )
        if valor != canonico:
            return None, (
                f"{clave} no admite un valor distinto del "
                f"canonico V1 ({canonico})."
            )

    url_limpia = config.backend_reservas_url.strip()
    alias_limpio = config.alias_equipo.strip()

    if config.modo_equipo_habilitado and not url_limpia:
        return None, (
            "backend_reservas_url no puede estar vacio cuando "
            "el Modo Equipo esta habilitado."
        )

    if url_limpia:
        error_url = _validar_backend_url_detallado(url_limpia)
        if error_url:
            return None, error_url

    return ConfiguracionModoEquipo(
        modo_equipo_habilitado=config.modo_equipo_habilitado,
        backend_reservas_url=url_limpia,
        alias_equipo=alias_limpio,
        ttl_reservas_segundos=config.ttl_reservas_segundos,
        renovacion_reservas_segundos=config.renovacion_reservas_segundos,
        margen_minimo_reserva_segundos=(
            config.margen_minimo_reserva_segundos
        ),
        frescura_reservas_segundos=config.frescura_reservas_segundos,
        margen_gracia_vencimiento_segundos=(
            config.margen_gracia_vencimiento_segundos
        ),
    ), None


class ServicioConfiguracion:
    """
    Lee y escribe config.json para recordar el ultimo
    repositorio seleccionado y la configuracion local del
    Modo Equipo Oracle V1.

    La escritura es conservadora: primero se escribe un archivo
    temporal en la misma carpeta y despues se reemplaza
    config.json mediante os.replace, evitando dejar un JSON
    parcialmente escrito si la aplicacion se interrumpe.

    Toda escritura exitosa preserva las claves conocidas que
    no se estan modificando y las claves desconocidas presentes
    en el JSON existente.
    """

    def __init__(
        self,
        servicio_git=None,
        ruta_configuracion=None
    ):
        """
        Crea el servicio de configuracion.

        Si no se indican, crea un ServicioGit nuevo y usa
        config.json junto a los archivos de la aplicacion,
        sin depender del directorio desde el cual se ejecute
        la aplicacion.
        """

        if servicio_git is None:
            servicio_git = ServicioGit()

        self.servicio_git = servicio_git

        if ruta_configuracion is None:
            ruta_configuracion = (
                Path(__file__).resolve().parent / "config.json"
            )

        self.ruta_configuracion = Path(
            ruta_configuracion
        )

    def _resultado_error(self, mensaje):
        """
        Construye un resultado de error controlado para
        operaciones de ultimo repositorio.
        """

        return ResultadoConfiguracion(
            exitoso=False,
            mensaje=mensaje,
            error=mensaje
        )

    def _resultado_error_modo_equipo(self, mensaje):
        """
        Construye un resultado de error controlado para
        operaciones de configuracion de Modo Equipo.
        """

        return ResultadoConfiguracionModoEquipo(
            exitoso=False,
            mensaje=mensaje,
            error=mensaje
        )

    def _validar_ruta_guardada(self, ruta_repositorio):
        """
        Valida una ruta guardada y devuelve la raiz confirmada
        por Git.

        Solamente se aceptan rutas de texto, sin NUL, CR o LF,
        que existan, sean directorios y repositorios Git validos.
        """

        if not isinstance(ruta_repositorio, str):
            return self._resultado_error(
                "La ruta guardada no es texto."
            )

        if _contiene_caracteres_no_validos(ruta_repositorio):
            return self._resultado_error(
                "La ruta guardada contiene caracteres no validos."
            )

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return self._resultado_error(
                estado.mensaje
            )

        return ResultadoConfiguracion(
            exitoso=True,
            ruta_repositorio=estado.ruta_raiz,
            mensaje="Repositorio recordado valido."
        )

    def _leer_config_crudo(self):
        """
        Lee config.json y lo devuelve como dict.

        Si el archivo no existe, devuelve ({}, None): config
        vacio interpretable como ausencia de claves.

        Si el archivo existe pero esta corrupto (UTF-8 invalido,
        JSON invalido, raiz no objeto, claves duplicadas),
        devuelve (None, mensaje_error).

        La inspeccion inicial de la ruta es fail-safe: errores
        del sistema (OSError) o de ruta invalida (ValueError) al
        consultar exists()/read_text() terminan en un error
        controlado, nunca en una excepcion hacia la GUI.

        No valida el contenido: solo garantiza que es un
        objeto JSON sin claves duplicadas.
        """

        try:
            existe = self.ruta_configuracion.exists()
        except (OSError, ValueError) as error:
            return None, (
                f"No fue posible inspeccionar la ruta de "
                f"config.json: {error}"
            )

        if not existe:
            return {}, None

        try:
            contenido = self.ruta_configuracion.read_text(
                encoding="utf-8"
            )
        except (OSError, ValueError, UnicodeDecodeError) as error:
            return None, (
                f"No fue posible leer config.json: {error}"
            )

        if "\ufffd" in contenido:
            return None, (
                "config.json contiene texto que no pudo "
                "decodificarse como UTF-8 valido."
            )

        try:
            datos = json.loads(
                contenido,
                object_pairs_hook=_detectar_claves_duplicadas
            )
        except (json.JSONDecodeError, ValueError) as error:
            return None, (
                f"config.json no contiene JSON valido: {error}"
            )

        if not isinstance(datos, dict):
            return None, (
                "El contenido de config.json no es un "
                "objeto JSON."
            )

        return datos, None

    def _parsear_config(self, datos):
        """
        Valida el contenido de un dict crudo de config.json.

        Devuelve (ruta_repositorio, config_equipo, desconocidas,
        None) o (None, None, None, mensaje_error).

        Las claves desconocidas se devuelven como dict para
        que el llamador pueda preservarlas al escribir.

        Las claves ausentes de Modo Equipo toman los defaults V1.
        Las claves ausentes de ruta_repositorio se devuelven
        como None (el llamador decide que hacer).
        """

        ruta_repositorio = None
        if _CLAVE_RUTA_REPOSITORIO in datos:
            valor = datos[_CLAVE_RUTA_REPOSITORIO]
            if not isinstance(valor, str):
                return None, None, None, (
                    "ruta_repositorio debe ser texto."
                )
            if _contiene_caracteres_no_validos(valor):
                return None, None, None, (
                    "ruta_repositorio contiene caracteres "
                    "no validos."
                )
            ruta_repositorio = valor

        config_equipo, error = _parsear_modo_equipo_de_dict(datos)
        if error:
            return None, None, None, error

        desconocidas = {
            clave: valor
            for clave, valor in datos.items()
            if clave not in _CLAVES_CONOCIDAS
        }

        return ruta_repositorio, config_equipo, desconocidas, None

    def _escribir_config(self, datos):
        """
        Escribe config.json de forma atomica.

        Devuelve None si se escribio correctamente o un
        mensaje de error. Ante cualquier fallo, config.json
        anterior permanece intacto.
        """

        contenido = json.dumps(
            datos,
            ensure_ascii=False,
            indent=2
        )

        ruta_temporal = self.ruta_configuracion.with_name(
            self.ruta_configuracion.name + ".tmp"
        )

        try:
            self.ruta_configuracion.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            ruta_temporal.write_text(
                contenido,
                encoding="utf-8"
            )

            os.replace(
                ruta_temporal,
                self.ruta_configuracion
            )
        except OSError as error:
            try:
                if ruta_temporal.exists():
                    ruta_temporal.unlink()
            except OSError:
                pass

            return f"No fue posible guardar config.json: {error}"

        return None

    def cargar_ultimo_repositorio(self):
        """
        Devuelve la ruta del ultimo repositorio seleccionado.

        Si config.json no existe, el resultado es exitoso con
        ruta vacia: corresponde a un primer inicio normal.

        Si config.json existe y es valido pero la clave
        ruta_repositorio esta AUSENTE, el resultado tambien es
        exitoso con ruta vacia: la clave es opcional en el JSON
        local y su ausencia representa que todavia no hay
        repositorio recordado, no una corrupcion.

        Si la clave esta PRESENTE pero es invalida (tipo
        incorrecto, caracteres no validos o ruta no confirmada
        por Git), el resultado es un error controlado.

        Las claves desconocidas se preservan en el JSON pero no
        se devuelven aqui. Las claves conocidas de Modo Equipo
        se validan estrictamente: un tipo invalido en una
        clave conocida se trata como error controlado.
        """

        datos, error = self._leer_config_crudo()
        if error:
            return self._resultado_error(error)

        if not datos:
            return ResultadoConfiguracion(
                exitoso=True,
                ruta_repositorio="",
                mensaje="No hay configuracion guardada."
            )

        ruta, _config, _desconocidas, error = self._parsear_config(
            datos
        )
        if error:
            return self._resultado_error(error)

        # Clave ausente: primer inicio o config solo de Modo
        # Equipo. No es un error y no debe validarse con Git.
        if ruta is None:
            return ResultadoConfiguracion(
                exitoso=True,
                ruta_repositorio="",
                mensaje="No hay repositorio guardado."
            )

        return self._validar_ruta_guardada(ruta)

    def guardar_ultimo_repositorio(self, ruta_repositorio):
        """
        Guarda la ruta raiz del ultimo repositorio seleccionado.

        La ruta se valida con Git antes de escribir: si es
        invalida no se altera la configuracion existente.

        La escritura preserva las claves conocidas de Modo
        Equipo y las claves desconocidas presentes en
        config.json. Solo se actualiza ruta_repositorio.

        Si config.json existe y esta corrupto, no se
        sobrescribe: se devuelve un error controlado.
        """

        resultado_validacion = self._validar_ruta_guardada(
            ruta_repositorio
        )
        if not resultado_validacion.exitoso:
            return resultado_validacion

        ruta_validada = resultado_validacion.ruta_repositorio

        datos, error = self._leer_config_crudo()
        if error:
            return self._resultado_error(error)

        _, _config, _desconocidas, error = self._parsear_config(datos)
        if error:
            return self._resultado_error(
                f"config.json existente es invalido: {error}"
            )

        datos[_CLAVE_RUTA_REPOSITORIO] = ruta_validada

        error = self._escribir_config(datos)
        if error:
            return self._resultado_error(error)

        return ResultadoConfiguracion(
            exitoso=True,
            ruta_repositorio=ruta_validada,
            mensaje="Configuracion guardada."
        )

    def cargar_configuracion_modo_equipo(self):
        """
        Carga la configuracion de Modo Equipo desde config.json.

        No exige que ruta_repositorio exista ni que sea un
        repositorio Git valido: solo valida su tipo si esta
        presente.

        Las claves ausentes toman los defaults V1.

        Un tipo invalido en una clave conocida (por ejemplo
        modo_equipo_habilitado=1 o ttl_reservas_segundos=3600)
        produce un resultado no exitoso.
        """

        datos, error = self._leer_config_crudo()
        if error:
            return self._resultado_error_modo_equipo(error)

        _ruta, config, _desconocidas, error = self._parsear_config(
            datos
        )
        if error:
            return self._resultado_error_modo_equipo(error)

        return ResultadoConfiguracionModoEquipo(
            exitoso=True,
            configuracion=config,
            mensaje="Configuracion de Modo Equipo cargada."
        )

    def guardar_configuracion_modo_equipo(self, config):
        """
        Guarda la configuracion de Modo Equipo en config.json.

        Preserva ruta_repositorio y las claves desconocidas
        presentes en el JSON existente.

        Si config.json existe y esta corrupto, no se
        sobrescribe: se devuelve un error controlado.

        alias_equipo y backend_reservas_url se recortan
        (espacios exteriores) de forma determinista al guardar.
        """

        config_limpio, error = _validar_config_modo_equipo_para_guardar(
            config
        )
        if error:
            return self._resultado_error_modo_equipo(error)

        datos, error = self._leer_config_crudo()
        if error:
            return self._resultado_error_modo_equipo(error)

        _, _config_existente, _desconocidas, error = (
            self._parsear_config(datos)
        )
        if error:
            return self._resultado_error_modo_equipo(
                f"config.json existente es invalido: {error}"
            )

        datos[_CLAVE_MODO_EQUIPO_HABILITADO] = (
            config_limpio.modo_equipo_habilitado
        )
        datos[_CLAVE_BACKEND_RESERVAS_URL] = (
            config_limpio.backend_reservas_url
        )
        datos[_CLAVE_ALIAS_EQUIPO] = config_limpio.alias_equipo
        datos[_CLAVE_TTL_RESERVAS_SEGUNDOS] = (
            config_limpio.ttl_reservas_segundos
        )
        datos[_CLAVE_RENOVACION_RESERVAS_SEGUNDOS] = (
            config_limpio.renovacion_reservas_segundos
        )
        datos[_CLAVE_MARGEN_MINIMO_RESERVA_SEGUNDOS] = (
            config_limpio.margen_minimo_reserva_segundos
        )
        datos[_CLAVE_FRESCURA_RESERVAS_SEGUNDOS] = (
            config_limpio.frescura_reservas_segundos
        )
        datos[_CLAVE_MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS] = (
            config_limpio.margen_gracia_vencimiento_segundos
        )

        error = self._escribir_config(datos)
        if error:
            return self._resultado_error_modo_equipo(error)

        return ResultadoConfiguracionModoEquipo(
            exitoso=True,
            configuracion=config_limpio,
            mensaje="Configuracion de Modo Equipo guardada."
        )
