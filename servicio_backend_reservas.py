"""
Servicio del backend local de reservas de Modo Equipo Oracle V1.

Prepara y verifica el repositorio Git bare local donde mas adelante
se sincronizaran las reservas del equipo.

Responsabilidades de este modulo (Bloque C):

- validar project_uuid (UUID v4 canonico);
- validar backend_reservas_url (defensa en profundidad, sin red);
- construir la ruta local del backend:

      <base>/<project_uuid>/backend.git

  donde <base> es por defecto:

      %APPDATA%\\GestorGit\\reservas

- crear el repositorio bare si no existe (git init --bare);
- verificar que un backend preexistente es un bare Git valido;
- configurar el remote origin con backend_reservas_url;
- configurar el refspec exacto de reservas:

      +refs/heads/gestorgit-reservas/*:refs/remotes/origin/gestorgit-reservas/*

- verificar localmente la configuracion escrita;
- devolver un ResultadoBackendReservas con la ruta absoluta.

NO implementa:

- Fetch, Pull, Push, ls-remote ni ninguna operacion de red;
- adquisicion, renovacion ni liberacion de reservas;
- operation_id, payloads ni commit-tree;
- mutex de red;
- modificacion del repositorio Oracle productivo;
- modificacion de la configuracion Git global o system;
- dependencia de ServicioGit.

Toda ejecucion de Git usa lista de argumentos, shell=False,
timeout finito y captura de stdout/stderr. Los errores de
proceso, sistema operativo y timeout se transforman en un
resultado estructurado, sin propagar excepciones previsibles.

Ante cualquier estado invalido o incierto (backend preexistente
que no es bare, que no es Git, o que no puede inspeccionarse):
BLOQUEAR Y EXPLICAR, sin borrar, limpiar ni reconstruir
automaticamente.
"""

import os
import shutil
import subprocess
import urllib.parse
import uuid
from pathlib import Path

from modelos_backend_reservas import ResultadoBackendReservas


# Refspec exacto de reservas de Modo Equipo Oracle V1.
# Se configura en el remote origin del bare local de reservas.
REFSPEC_RESERVAS_V1 = (
    "+refs/heads/gestorgit-reservas/*:refs/remotes/origin/gestorgit-reservas/*"
)

# Esquemas de URL de backend admitidos en V1.
_ESQUEMAS_BACKEND_ADMITIDOS = ("http", "https")

# Caracteres no validos en una URL de backend.
_CARACTERES_NO_VALIDOS = ("\x00", "\r", "\n")


def _contiene_caracteres_no_validos(texto):
    """Comprueba si un texto contiene NUL, CR o LF."""

    return any(c in texto for c in _CARACTERES_NO_VALIDOS)


def _es_uuid4_canonico(texto):
    """
    Comprueba que texto sea un UUID v4 en representacion
    canonica: minusculas, con guiones, 36 caracteres.

    Un valor no-string, vacio, no-v4, en mayusculas, sin
    guiones o con caracteres de ruta se rechaza.
    """

    if not isinstance(texto, str):
        return False
    try:
        u = uuid.UUID(texto)
    except (ValueError, AttributeError):
        return False
    if u.version != 4:
        return False
    return texto == str(u)


def _validar_backend_url(url):
    """
    Valida backend_reservas_url de forma compatible con las
    reglas cerradas en ServicioConfiguracion, sin relajar
    ninguna.

    Devuelve (url_limpia, None) si es valida o
    (None, mensaje_error) si no lo es.

    Reglas V1:

    - debe ser str;
    - strip() no vacio;
    - sin NUL/CR/LF;
    - sin espacios ni espacios en blanco internos;
    - sin SSH (ssh://, git+ssh://, ssh+git://);
    - sin sintaxis scp-like (usuario@host:ruta);
    - sin credenciales embebidas (usuario:password@ o token@);
    - sin query ni fragment;
    - esquema http o https;
    - hostname y path presentes;
    - puerto, si es explicito, valido;
    - no se realiza red.
    """

    if not isinstance(url, str):
        return None, "backend_reservas_url debe ser texto."

    if _contiene_caracteres_no_validos(url):
        return None, "backend_reservas_url no puede contener NUL, CR o LF."

    url_limpia = url.strip()
    if not url_limpia:
        return None, "backend_reservas_url no puede estar vacio."

    if any(caracter.isspace() for caracter in url_limpia):
        return None, (
            "backend_reservas_url no puede contener espacios "
            "ni espacios en blanco internos."
        )

    url_minuscula = url_limpia.lower()
    if (
        url_minuscula.startswith("ssh://")
        or url_minuscula.startswith("git+ssh://")
        or url_minuscula.startswith("ssh+git://")
    ):
        return None, (
            "Las URLs SSH no se admiten en V1: configure SSH "
            "externamente."
        )

    if "://" not in url_minuscula:
        if "@" in url_limpia.split("/", 1)[0]:
            return None, (
                "Las URLs scp-like (usuario@host:ruta) no se "
                "admiten en V1."
            )
        return None, (
            "backend_reservas_url debe incluir un esquema "
            "(http:// o https://)."
        )

    try:
        parsed = urllib.parse.urlparse(url_limpia)
    except ValueError as error:
        return None, f"backend_reservas_url no es una URL valida: {error}"

    if parsed.scheme.lower() not in _ESQUEMAS_BACKEND_ADMITIDOS:
        return None, (
            "Solo se admiten esquemas http y https en V1 para "
            "backend_reservas_url."
        )

    if parsed.username or parsed.password:
        return None, (
            "backend_reservas_url no puede contener credenciales "
            "embebidas (usuario:password@ o token@)."
        )

    if "?" in url_limpia:
        return None, "backend_reservas_url no puede contener query."

    if "#" in url_limpia:
        return None, "backend_reservas_url no puede contener fragment."

    if not parsed.netloc:
        return None, "backend_reservas_url incompleta: falta el host."

    try:
        hostname = parsed.hostname
        puerto = parsed.port
    except ValueError as error:
        return None, f"backend_reservas_url no es una URL valida: {error}"

    if not hostname:
        return None, "backend_reservas_url incompleta: falta el host."

    if not parsed.path:
        return None, (
            "backend_reservas_url incompleta: falta la ruta "
            "del repositorio."
        )

    return url_limpia, None


class ServicioBackendReservas:
    """
    Servicio del backend local de reservas de Modo Equipo
    Oracle V1.

    Uso tipico en produccion:

        servicio = ServicioBackendReservas()
        resultado = servicio.preparar_backend_local(
            project_uuid,
            backend_reservas_url
        )
        if resultado.exitoso:
            ruta = resultado.ruta_backend

    En pruebas se inyecta una ruta base temporal:

        servicio = ServicioBackendReservas(
            ruta_base=tmp / "reservas"
        )

    El servicio no ejecuta Fetch, Pull, Push ni ninguna
    operacion de red. No modifica la configuracion Git global
    ni system. No toca el repositorio Oracle productivo. No
    depende de ServicioGit.
    """

    REFSPEC = REFSPEC_RESERVAS_V1

    def __init__(
        self,
        ruta_base=None,
        git_ejecutable=None,
        tiempo_maximo_git=30
    ):
        """
        Crea el servicio.

        Si ruta_base es None, se deriva desde %APPDATA%:

            %APPDATA%\\GestorGit\\reservas

        Si APPDATA no esta definida o es invalida, el servicio
        queda sin ruta base y preparar_backend_local devolvera
        un resultado controlado, sin fallback a HOME, cwd, TEMP
        ni rutas alternativas silenciosas.

        Si git_ejecutable es None, se localiza git con
        shutil.which. Si git no se encuentra, las operaciones
        que requieren Git devolveran un resultado controlado.

        tiempo_maximo_git es el timeout finito en segundos para
        cada invocacion de Git.
        """

        if ruta_base is None:
            appdata = os.environ.get("APPDATA")
            if not appdata:
                self.ruta_base = None
                self._error_inicial = (
                    "La variable de entorno APPDATA no esta "
                    "definida; no se puede determinar la ruta "
                    "base de reservas."
                )
            else:
                self.ruta_base = (
                    Path(appdata) / "GestorGit" / "reservas"
                )
                self._error_inicial = None
        else:
            self.ruta_base = Path(ruta_base)
            self._error_inicial = None

        if git_ejecutable is None:
            self.git_ejecutable = shutil.which("git")
        else:
            self.git_ejecutable = git_ejecutable

        self.tiempo_maximo_git = tiempo_maximo_git

    # -- Validacion -----------------------------------------------

    def _validar_project_uuid(self, project_uuid):
        """
        Valida que project_uuid sea un UUID v4 canonico.

        Devuelve (True, None) o (False, mensaje).

        Nunca se usa un project_uuid no validado para construir
        una ruta.
        """

        if not _es_uuid4_canonico(project_uuid):
            return False, (
                "project_uuid no es un UUID v4 canonico valido "
                "(minusculas, guiones, version 4)."
            )
        return True, None

    def _resolver_ruta_contenida(self, ruta):
        """
        Resuelve canonicamente ruta y comprueba que su
        ruta efectiva quede contenida dentro de la base
        efectiva del servicio.

        Devuelve (ruta_resuelta, None) si esta contenida
        o (None, mensaje_error) en caso contrario.

        Usa Path.resolve y relative_to; nunca
        str.startswith como control de seguridad. Un
        symlink/reparse/junction que redirija fuera de la
        base queda bloqueado.
        """

        if self.ruta_base is None:
            return None, (
                "No hay ruta base configurada; no se "
                "puede resolver el backend."
            )

        try:
            base_resuelta = self.ruta_base.resolve()
        except (OSError, ValueError) as error:
            return None, (
                "No fue posible resolver la ruta base de "
                f"reservas: {error}"
            )

        try:
            ruta_resuelta = ruta.resolve()
        except (OSError, ValueError) as error:
            return None, (
                "No fue posible resolver la ruta del "
                f"backend: {error}"
            )

        try:
            ruta_resuelta.relative_to(base_resuelta)
        except ValueError:
            return None, (
                "La ruta efectiva del backend queda fuera "
                "de la ruta base de reservas."
            )

        return ruta_resuelta, None

    # -- Ejecucion Git --------------------------------------------

    def _ejecutar_git(self, argumentos, tiempo_maximo=None):
        """
        Ejecuta un comando Git de forma controlada.

        Devuelve (exitoso, stdout, stderr, codigo_salida).
        Nunca usa shell=True. Captura stdout y stderr. Usa
        timeout finito. Transforma errores de proceso, OS y
        timeout en una tupla controlada, sin propagar
        excepciones previsibles.

        No incluye secretos en los mensajes de error.
        """

        if self.git_ejecutable is None:
            return (
                False,
                "",
                "Git no fue encontrado en el sistema.",
                -1
            )

        comando = [self.git_ejecutable] + list(argumentos)
        tiempo = (
            tiempo_maximo
            if tiempo_maximo is not None
            else self.tiempo_maximo_git
        )

        try:
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=tiempo,
                shell=False
            )
            return (
                resultado.returncode == 0,
                resultado.stdout.rstrip("\r\n"),
                resultado.stderr.rstrip("\r\n"),
                resultado.returncode
            )
        except subprocess.TimeoutExpired:
            return (
                False,
                "",
                f"El comando supero el tiempo maximo "
                f"de {tiempo} segundos.",
                -1
            )
        except FileNotFoundError:
            return (
                False,
                "",
                "No fue posible encontrar git.",
                -1
            )
        except PermissionError:
            return (
                False,
                "",
                "El sistema operativo nego el acceso al "
                "ejecutar Git.",
                -1
            )
        except OSError as error:
            return (
                False,
                "",
                f"Error del sistema operativo: {error}",
                -1
            )

    # -- Resultados -----------------------------------------------

    def _error(self, mensaje):
        """Construye un resultado no exitoso."""

        return ResultadoBackendReservas(
            exitoso=False,
            ruta_backend="",
            mensaje=mensaje,
            error=mensaje
        )

    # -- Verificacion de bare --------------------------------------

    def _verificar_bare(self, ruta_backend):
        """
        Verifica que ruta_backend es un repositorio Git bare
        valido.

        Devuelve (ok, es_bare, mensaje_error).
        """

        try:
            if not ruta_backend.is_dir():
                return (
                    False,
                    False,
                    "La ruta del backend existe pero no es "
                    "un directorio."
                )
        except (OSError, ValueError) as error:
            return (
                False,
                False,
                f"No fue posible inspeccionar la ruta del "
                f"backend: {error}"
            )

        ok, stdout, stderr, _ = self._ejecutar_git(
            ["-C", str(ruta_backend),
             "rev-parse", "--is-bare-repository"]
        )
        if not ok:
            return (
                False,
                False,
                f"La ruta no es un repositorio Git valido: {stderr}"
            )
        es_bare = stdout == "true"
        if not es_bare:
            return (
                False,
                False,
                "El repositorio existe pero no es bare."
            )
        return True, True, ""

    # -- Configuracion de origin y refspec ------------------------

    def _asegurar_origin(self, ruta_backend, url):
        """
        Configura el remote origin con la URL exacta.

        La existencia de origin se decide solo con una
        consulta local que haya terminado correctamente
        (`git remote`). Un fallo, timeout o error de esa
        consulta NO se interpreta como "origin ausente":
        devuelve error controlado y no ejecuta
        add/set-url/config posteriores.
        """

        ok, stdout, stderr, _ = self._ejecutar_git(
            ["-C", str(ruta_backend), "remote"]
        )
        if not ok:
            return False, (
                "No fue posible consultar los remotes del "
                f"backend; no se configuro origin: {stderr}"
            )

        remotes = [
            linea.strip()
            for linea in stdout.splitlines()
            if linea.strip()
        ]
        if "origin" in remotes:
            ok2, _stdout2, stderr2, _ = self._ejecutar_git(
                ["-C", str(ruta_backend),
                 "remote", "set-url", "origin", url]
            )
            if not ok2:
                return False, (
                    f"No fue posible configurar origin: {stderr2}"
                )
            return True, None

        ok2, _stdout2, stderr2, _ = self._ejecutar_git(
            ["-C", str(ruta_backend),
             "remote", "add", "origin", url]
        )
        if not ok2:
            return False, (
                f"No fue posible configurar origin: {stderr2}"
            )
        return True, None

    def _asegurar_refspec(self, ruta_backend):
        """
        Configura el refspec exacto de reservas en origin.

        Usa --replace-all para evitar duplicados en ejecuciones
        repetidas. Devuelve (True, None) o (False, mensaje).
        """

        ok, _stdout, stderr, _ = self._ejecutar_git(
            ["-C", str(ruta_backend),
             "config", "--replace-all",
             "remote.origin.fetch", self.REFSPEC]
        )
        if not ok:
            return False, (
                f"No fue posible configurar el refspec: {stderr}"
            )
        return True, None

    def _asegurar_destino_push(self, ruta_backend, url):
        """
        Fija el destino de Push local de origin a la URL
        exacta.

        Configura SIEMPRE un remote.origin.pushurl local con
        la URL esperada usando --replace-all: colapsa
        duplicados locales y crea la clave si falta. Esto
        desacopla el Push de cualquier multiplicidad de
        remote.origin.url heredada de otros scopes.

        La unicidad efectiva se comprueba despues en
        _verificar_configuracion con
        `git remote get-url --push --all origin`, que debe
        devolver exactamente una linea: la URL esperada. Si
        existen destinos heredados de otros scopes que no
        pueden neutralizarse sin tocar Git global/system, la
        verificacion devuelve error controlado (BLOQUEAR Y
        EXPLICAR).

        No realiza red ni modifica Git global/system.
        """

        ok, _stdout, stderr, _ = self._ejecutar_git(
            ["-C", str(ruta_backend),
             "config", "--replace-all",
             "remote.origin.pushurl", url]
        )
        if not ok:
            return False, (
                "No fue posible fijar el destino de Push "
                f"de origin: {stderr}"
            )
        return True, None

    def _verificar_configuracion(self, ruta_backend, url_esperada):
        """
        Verifica localmente la configuracion escrita.

        Devuelve (True, None) o (False, mensaje).
        """

        ok, stdout, stderr, _ = self._ejecutar_git(
            ["-C", str(ruta_backend),
             "remote", "get-url", "origin"]
        )
        if not ok:
            return False, (
                f"No fue posible verificar origin: {stderr}"
            )
        if stdout != url_esperada:
            return False, "La URL de origin no coincide."

        ok, stdout, stderr, _ = self._ejecutar_git(
            ["-C", str(ruta_backend),
             "remote", "get-url", "--push", "--all",
             "origin"]
        )
        if not ok:
            return False, (
                "No fue posible verificar el destino de Push "
                f"de origin: {stderr}"
            )
        destinos_push = [
            linea.strip()
            for linea in stdout.splitlines()
            if linea.strip()
        ]
        if destinos_push != [url_esperada]:
            return False, (
                "El destino efectivo de Push de origin no "
                "es unico e igual a backend_reservas_url."
            )

        ok, stdout, stderr, _ = self._ejecutar_git(
            ["-C", str(ruta_backend),
             "config", "--get", "remote.origin.fetch"]
        )
        if not ok:
            return False, (
                f"No fue posible verificar el refspec: {stderr}"
            )
        if stdout != self.REFSPEC:
            return False, "El refspec no coincide."

        ok, stdout, stderr, _ = self._ejecutar_git(
            ["-C", str(ruta_backend),
             "rev-parse", "--is-bare-repository"]
        )
        if not ok:
            return False, (
                f"No fue posible verificar que es bare: {stderr}"
            )
        if stdout != "true":
            return False, "El repositorio no es bare."

        return True, None

    # -- API publica ----------------------------------------------

    def preparar_backend_local(self, project_uuid, backend_reservas_url):
        """
        Prepara el backend local de reservas para un proyecto.

        Pasos:

        1. valida project_uuid y backend_reservas_url;
        2. construye <base>/<project_uuid>/backend.git;
        3. crea los padres necesarios;
        4. si backend.git no existe, ejecuta git init --bare;
        5. si existe, verifica que es un bare Git valido;
        6. configura origin con backend_reservas_url;
        7. configura el refspec exacto de reservas;
        8. verifica localmente la configuracion escrita;
        9. devuelve ResultadoBackendReservas con la ruta
           absoluta.

        No ejecuta Fetch, Pull, Push ni ninguna operacion de
        red. No modifica Git global/system. Ante estados
        invalidos: error controlado sin borrar ni reconstruir.
        """

        ok_uuid, error_uuid = self._validar_project_uuid(project_uuid)
        if not ok_uuid:
            return self._error(error_uuid)

        url_limpia, error_url = _validar_backend_url(
            backend_reservas_url
        )
        if error_url:
            return self._error(error_url)

        if self.ruta_base is None:
            return self._error(self._error_inicial)

        try:
            ruta_proyecto = self.ruta_base / project_uuid
            ruta_backend = ruta_proyecto / "backend.git"
        except (OSError, ValueError) as error:
            return self._error(
                f"No fue posible construir la ruta del backend: {error}"
            )

        # H1: primera comprobacion de contencion antes de
        # crear padres ni escribir nada. Una ruta efectiva
        # fuera de la base (symlink/reparse/junction)
        # bloquea la preparacion.
        ruta_proyecto_resuelta, error = self._resolver_ruta_contenida(
            ruta_proyecto
        )
        if error:
            return self._error(error)
        ruta_backend_resuelta, error = self._resolver_ruta_contenida(
            ruta_backend
        )
        if error:
            return self._error(error)

        try:
            ruta_proyecto.mkdir(parents=True, exist_ok=True)
        except (OSError, ValueError) as error:
            return self._error(
                f"No fue posible crear la carpeta del proyecto: {error}"
            )

        # H1: segunda comprobacion tras crear padres y antes
        # de la primera operacion Git que escriba. Los
        # padres recien creados o redirecciones del
        # filesystem podrian cambiar la ruta efectiva.
        ruta_proyecto_resuelta, error = self._resolver_ruta_contenida(
            ruta_proyecto
        )
        if error:
            return self._error(error)
        ruta_backend_resuelta, error = self._resolver_ruta_contenida(
            ruta_backend
        )
        if error:
            return self._error(error)

        try:
            existe = ruta_backend_resuelta.exists()
        except (OSError, ValueError) as error:
            return self._error(
                f"No fue posible inspeccionar la ruta del "
                f"backend: {error}"
            )

        if existe:
            ok, _es_bare, error = self._verificar_bare(
                ruta_backend_resuelta
            )
            if not ok:
                return self._error(error)
        else:
            ok, _stdout, stderr, _ = self._ejecutar_git(
                ["init", "--bare", str(ruta_backend_resuelta)]
            )
            if not ok:
                return self._error(
                    f"No fue posible inicializar el repositorio "
                    f"bare: {stderr}"
                )
            ok, es_bare, error = self._verificar_bare(
                ruta_backend_resuelta
            )
            if not ok:
                return self._error(error)
            if not es_bare:
                return self._error(
                    "El repositorio creado no es bare."
                )

        ok, error = self._asegurar_origin(
            ruta_backend_resuelta, url_limpia
        )
        if not ok:
            return self._error(error)

        ok, error = self._asegurar_destino_push(
            ruta_backend_resuelta, url_limpia
        )
        if not ok:
            return self._error(error)

        ok, error = self._asegurar_refspec(ruta_backend_resuelta)
        if not ok:
            return self._error(error)

        ok, error = self._verificar_configuracion(
            ruta_backend_resuelta, url_limpia
        )
        if not ok:
            return self._error(error)

        return ResultadoBackendReservas(
            exitoso=True,
            ruta_backend=str(ruta_backend_resuelta),
            mensaje="Backend local de reservas preparado."
        )
