"""
Servicio remoto de reservas de Modo Equipo Oracle V1 (Bloque D).

Bajo nivel Git sobre el backend bare local preparado por Bloque C.

Responsabilidades:

- Fetch explicito con el refspec aprobado de reservas;
- lectura y validacion del head remoto observado;
- validacion commit/tree/payload;
- construccion de commits tecnicos con plumbing:
      hash-object / mktree / commit-tree
- publicacion mediante Push normal (sin force);
- devolucion de resultados estructurados.

Este servicio:

- NO usa Tkinter;
- NO conoce staging/commit del repositorio productivo;
- NO toca ServicioGit, servicio_remoto_git ni principal.py;
- NO modifica Git global/system;
- NO crea ramas locales por objeto;
- NO usa `git update-ref` en el camino normal;
- NO usa red real: opera sobre la ruta del backend ya preparada.

Toda ejecucion de Git usa lista de argumentos, shell=False, captura
de stdout/stderr, UTF-8 y timeout finito. Los errores previsibles
(TimeoutExpired, OSError, FileNotFoundError, PermissionError,
returncode != 0) se transforman en resultados controlados.
"""

import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from modelos_reservas import (
    ClasificacionReservaObservada,
    EstadoReservaPersistido,
    ReservaPayloadV1,
    calcular_ref_reserva,
    parsear_timestamp_utc,
    validar_payload_reserva,
    TTL_RESERVAS_SEGUNDOS_V1,
)


# Refspec exacto de reservas aprobado en GG-PROMPT-024-REV3.
REFSPEC_RESERVAS_V1 = (
    "+refs/heads/gestorgit-reservas/*:refs/remotes/origin/gestorgit-reservas/*"
)

# Identidad tecnica fija para TODOS los commits de reservas.
# Se aplica por variables de entorno del subproceso; nunca se
# modifica user.name / user.email de ningun repo ni Git global.
IDENTIDAD_TECNICA_RESERVAS = {
    "GIT_AUTHOR_NAME": "GestorGit Reservas",
    "GIT_AUTHOR_EMAIL": "reservas@gestorgit.invalid",
    "GIT_COMMITTER_NAME": "GestorGit Reservas",
    "GIT_COMMITTER_EMAIL": "reservas@gestorgit.invalid",
}

NOMBRE_ARCHIVO_RESERVA = "reserva.json"
_PREFIJO_REF_HEADS = "refs/heads/gestorgit-reservas/"
_PREFIJO_REF_REMOTO = "refs/remotes/origin/gestorgit-reservas/"


@dataclass
class ResultadoLecturaReserva:
    """
    Resultado controlado de leer el head remoto de un objeto.

    clasificacion:

    - LIBRE: no existe ref o el payload valido es LIBERADA;
    - RESERVADO_POR_MI / RESERVADO_POR_OTRO / VENCIDO_PROPIO /
      VENCIDO_AJENO: payload ACTIVA valido clasificado con el
      id_cliente local;
    - NO_VERIFICABLE: cualquier inconsistencia o error de lectura.

    Nunca se interpreta corrupcion/inconsistencia como LIBRE.
    """

    exitoso: bool
    clasificacion: ClasificacionReservaObservada
    head_existe: bool = False
    payload: ReservaPayloadV1 | None = None
    parent: str = ""
    mensaje: str = ""
    error: str = ""


@dataclass
class ResultadoPublicacionReserva:
    """
    Resultado controlado de publicar un commit tecnico.

    exitoso es True solo si el Push termino con returncode 0.
    Un Push rechazado (non-fast-forward) o incierto queda
    representado como no exitoso; la reconciliacion la orquesta
    ServicioReservas con Fetch + relectura del head.
    """

    exitoso: bool
    oid: str = ""
    mensaje: str = ""
    error: str = ""


def _es_uuid4_canonico(texto):
    """Comprueba que texto sea un UUID v4 canonico."""

    if not isinstance(texto, str):
        return False
    try:
        u = uuid.UUID(texto)
    except (ValueError, AttributeError):
        return False
    if u.version != 4:
        return False
    return texto == str(u)


def _texto_plano_valido(valor, permitir_vacio=True):
    """Valida un texto sin NUL/CR/LF."""

    if not isinstance(valor, str):
        return False
    if not permitir_vacio and not valor:
        return False
    if any(c in valor for c in ("\x00", "\r", "\n")):
        return False
    return True


class ServicioRemotoReservas:
    """
    Servicio de bajo nivel de reservas remotas.

    Uso tipico:

        servicio = ServicioRemotoReservas(ruta_backend)
        lectura = servicio.leer_head_reserva(
            project_uuid, clave_objeto, id_cliente_local
        )
        if lectura.clasificacion is ClasificacionReservaObservada.LIBRE:
            oid, ok, error = servicio.crear_commit_reserva(payload)
            resultado = servicio.publicar_reserva(
                oid, project_uuid, clave_objeto
            )

    La ruta del backend debe estar YA preparada por
    ServicioBackendReservas (Bloque C). Este servicio no la crea.
    """

    def __init__(
        self,
        ruta_backend,
        git_ejecutable=None,
        tiempo_maximo_git=30
    ):
        """
        Crea el servicio sobre un backend bare ya preparado.

        Si git_ejecutable es None, se localiza git con shutil.which.
        Si git no se encuentra, las operaciones devuelven resultados
        controlados.

        tiempo_maximo_git es el timeout finito en segundos para cada
        invocacion de Git.
        """

        self.ruta_backend = Path(ruta_backend)
        if git_ejecutable is None:
            self.git_ejecutable = shutil.which("git")
        else:
            self.git_ejecutable = git_ejecutable
        self.tiempo_maximo_git = tiempo_maximo_git

    # -- Ejecucion Git --------------------------------------------

    def _ejecutar_git(self, argumentos, env_extra=None, entrada=None):
        """
        Ejecuta Git de forma controlada.

        Devuelve (exitoso, stdout, stderr, codigo_salida).
        Nunca usa shell=True. Captura stdout/stderr. Usa UTF-8 y
        timeout finito. Transforma errores de proceso, OS y timeout
        en una tupla controlada, sin propagar excepciones
        previsibles.

        Si hay entrada, se envia por stdin en modo BINARIO con
        codificacion UTF-8 explicita: el modo texto de Windows
        traduciria \n a \r\n y corromperia la entrada exacta que
        exigen hash-object y mktree (LF terminador de linea).
        """

        if self.git_ejecutable is None:
            return (
                False,
                "",
                "Git no fue encontrado en el sistema.",
                -1
            )

        comando = [self.git_ejecutable, "-C", str(self.ruta_backend)]
        comando.extend(argumentos)

        entorno = None
        if env_extra:
            entorno = dict(os.environ)
            entorno.update(env_extra)

        try:
            if entrada is None:
                resultado = subprocess.run(
                    comando,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.tiempo_maximo_git,
                    shell=False,
                    env=entorno,
                )
                stdout = resultado.stdout
                stderr = resultado.stderr
            else:
                if isinstance(entrada, str):
                    entrada = entrada.encode("utf-8")
                resultado = subprocess.run(
                    comando,
                    capture_output=True,
                    input=entrada,
                    timeout=self.tiempo_maximo_git,
                    shell=False,
                    env=entorno,
                )
                stdout = resultado.stdout.decode(
                    "utf-8", errors="replace"
                )
                stderr = resultado.stderr.decode(
                    "utf-8", errors="replace"
                )
            return (
                resultado.returncode == 0,
                stdout.rstrip("\r\n"),
                stderr.rstrip("\r\n"),
                resultado.returncode,
            )
        except subprocess.TimeoutExpired:
            return (
                False,
                "",
                f"El comando supero el tiempo maximo de "
                f"{self.tiempo_maximo_git} segundos.",
                -1
            )
        except FileNotFoundError:
            return (False, "", "No fue posible encontrar git.", -1)
        except PermissionError:
            return (
                False,
                "",
                "El sistema operativo nego el acceso al ejecutar Git.",
                -1
            )
        except OSError as error:
            return (
                False,
                "",
                f"Error del sistema operativo: {error}",
                -1
            )

    # -- Validacion de entradas -----------------------------------

    def _validar_entrada(self, project_uuid, clave_objeto):
        """
        Valida project_uuid (UUID v4 canonico) y clave_objeto
        (texto plano no vacio).

        Devuelve (True, None) o (False, mensaje).
        """

        if not _es_uuid4_canonico(project_uuid):
            return False, (
                "project_uuid no es un UUID v4 canonico valido."
            )
        if not _texto_plano_valido(clave_objeto, permitir_vacio=False):
            return False, "clave_objeto invalida."
        return True, None

    def _ref_remoto(self, project_uuid, clave_objeto):
        """
        Devuelve la ref remota observada:

            refs/remotes/origin/gestorgit-reservas/<sha256_completo>
        """

        hash_ref = calcular_ref_reserva(project_uuid, clave_objeto)
        return _PREFIJO_REF_REMOTO + hash_ref

    def _ref_heads(self, project_uuid, clave_objeto):
        """
        Devuelve la ref de publicacion:

            refs/heads/gestorgit-reservas/<sha256_completo>
        """

        hash_ref = calcular_ref_reserva(project_uuid, clave_objeto)
        return _PREFIJO_REF_HEADS + hash_ref

    # -- Fetch ----------------------------------------------------

    def fetch_reservas(self):
        """
        Ejecuta el Fetch explicito de reservas con el refspec
        aprobado:

            git -C <backend.git> fetch --prune origin \
                +refs/heads/gestorgit-reservas/*:refs/remotes/origin/gestorgit-reservas/*

        Devuelve (exitoso, mensaje). No usa git pull ni el Fetch
        del repositorio GestorGit.

        Ultima barrera de la API publica: un fallo inesperado del
        proceso Git nunca se propaga hacia el orquestador.
        """

        try:
            ok, _stdout, stderr, _ = self._ejecutar_git(
                [
                    "fetch",
                    "--prune",
                    "origin",
                    REFSPEC_RESERVAS_V1,
                ]
            )
        except Exception as error:
            return False, (
                "No fue posible ejecutar el Fetch de reservas: "
                f"{error}"
            )
        if not ok:
            return False, (
                "No fue posible ejecutar el Fetch de reservas: "
                f"{stderr}"
            )
        return True, "Fetch de reservas completado."

    # -- Lectura del head -----------------------------------------

    def _leer_oid_ref(self, ref):
        """
        Lee el OID de una ref.

        Devuelve (exitoso, oid, stderr, codigo). exitoso=True solo
        si la ref existe y rev-parse --verify --quiet termina en 0.
        """

        return self._ejecutar_git(
            ["rev-parse", "--verify", "--quiet", ref]
        )

    def _leer_tipo_objeto(self, oid):
        """Devuelve el tipo del objeto o None si falla."""

        ok, stdout, _stderr, _ = self._ejecutar_git(
            ["cat-file", "-t", oid]
        )
        if not ok:
            return None
        return stdout

    def _leer_tree(self, oid):
        """
        Lee el tree de un commit y devuelve su contenido.

        Devuelve (ok, lineas) o (False, []).
        """

        ok, stdout, _stderr, _ = self._ejecutar_git(
            ["ls-tree", oid]
        )
        if not ok:
            return False, []
        lineas = [linea for linea in stdout.splitlines() if linea]
        return True, lineas

    def _leer_blob(self, oid_blob):
        """Lee el contenido de un blob o None si falla."""

        ok, stdout, _stderr, _ = self._ejecutar_git(
            ["cat-file", "blob", oid_blob]
        )
        if not ok:
            return None
        return stdout

    def _validar_tree_reserva(self, oid_commit):
        """
        Valida que el tree del commit contenga exactamente una
        entrada: reserva.json como blob de modo normal.

        Devuelve (ok, oid_blob, mensaje_error).
        """

        ok, lineas = self._leer_tree(oid_commit)
        if not ok:
            return False, "", (
                "No fue posible leer el tree del commit."
            )
        if len(lineas) != 1:
            return False, "", (
                "El tree del commit debe contener exactamente "
                "una entrada."
            )
        partes = lineas[0].split("\t")
        if len(partes) != 2:
            return False, "", "Entrada de tree mal formada."
        modo_tipo = partes[0].split()
        nombre = partes[1]
        if len(modo_tipo) != 3:
            return False, "", "Entrada de tree mal formada."
        modo, tipo, oid_blob = modo_tipo
        if modo != "100644":
            return False, "", (
                "reserva.json debe tener modo de archivo normal "
                "(100644)."
            )
        if tipo != "blob":
            return False, "", "reserva.json debe ser un blob."
        if nombre != NOMBRE_ARCHIVO_RESERVA:
            return False, "", (
                "La entrada del tree debe llamarse exactamente "
                "reserva.json."
            )
        return True, oid_blob, ""

    def leer_head_reserva(
        self,
        project_uuid,
        clave_objeto,
        id_cliente_local="",
        ttl_segundos=TTL_RESERVAS_SEGUNDOS_V1,
        ahora=None,
    ):
        """
        Lee y valida el head remoto observado de un objeto.

        Devuelve ResultadoLecturaReserva. Nunca interpreta
        corrupcion/inconsistencia como LIBRE.

        Si no existe la ref:

            LIBRE, parent = None

        Si existe, valida en orden:

            1. el OID es un commit;
            2. el tree contiene exactamente una entrada
               reserva.json como blob de modo normal;
            3. el JSON es valido y cumple el esquema V1 exacto;
            4. project_uuid y clave_objeto coinciden con la consulta.

        Cualquier inconsistencia: NO_VERIFICABLE.

        Si el payload es LIBERADA se devuelve clasificacion LIBRE
        (funcional), conservando payload y parent para auditoria.

        Ultima barrera de la API publica: un fallo inesperado se
        representa como NO_VERIFICABLE, nunca se propaga.
        """

        try:
            return self._leer_head_reserva_interna(
                project_uuid,
                clave_objeto,
                id_cliente_local,
                ttl_segundos,
                ahora,
            )
        except Exception as error:
            return ResultadoLecturaReserva(
                exitoso=False,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                mensaje="Error inesperado al leer el head de reservas.",
                error=str(error),
            )

    def _leer_head_reserva_interna(
        self,
        project_uuid,
        clave_objeto,
        id_cliente_local="",
        ttl_segundos=TTL_RESERVAS_SEGUNDOS_V1,
        ahora=None,
    ):
        """
        Implementacion de leer_head_reserva (sin barrera final).
        """

        ok_entrada, error_entrada = self._validar_entrada(
            project_uuid, clave_objeto
        )
        if not ok_entrada:
            return ResultadoLecturaReserva(
                exitoso=False,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                mensaje=error_entrada,
                error=error_entrada,
            )

        ref = self._ref_remoto(project_uuid, clave_objeto)
        ok, oid, stderr, codigo = self._leer_oid_ref(ref)
        if not ok:
            if codigo == 1:
                # Ref inexistente: LIBRE.
                return ResultadoLecturaReserva(
                    exitoso=True,
                    clasificacion=(
                        ClasificacionReservaObservada.LIBRE
                    ),
                    head_existe=False,
                    mensaje="No existe reserva para el objeto.",
                )
            return ResultadoLecturaReserva(
                exitoso=False,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                mensaje=(
                    "No fue posible leer el head remoto de "
                    f"reservas: {stderr}"
                ),
                error=stderr,
            )

        tipo = self._leer_tipo_objeto(oid)
        if tipo != "commit":
            return ResultadoLecturaReserva(
                exitoso=False,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                mensaje=(
                    "El head remoto de reservas no es un commit."
                ),
                error="tipo != commit",
            )

        ok_tree, oid_blob, error_tree = self._validar_tree_reserva(oid)
        if not ok_tree:
            return ResultadoLecturaReserva(
                exitoso=False,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                mensaje=error_tree,
                error=error_tree,
            )

        contenido = self._leer_blob(oid_blob)
        if contenido is None:
            return ResultadoLecturaReserva(
                exitoso=False,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                mensaje="No fue posible leer reserva.json.",
                error="cat-file blob fallo",
            )

        try:
            datos = json.loads(
                contenido,
                object_pairs_hook=_rechazar_claves_duplicadas,
            )
        except (ValueError, json.JSONDecodeError) as error:
            return ResultadoLecturaReserva(
                exitoso=False,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                mensaje="reserva.json no contiene JSON valido.",
                error=str(error),
            )

        ok_payload, payload, mensaje_payload = validar_payload_reserva(
            datos,
            project_uuid_esperado=project_uuid,
            clave_objeto_esperada=clave_objeto,
            ttl_segundos=ttl_segundos,
        )
        if not ok_payload:
            return ResultadoLecturaReserva(
                exitoso=False,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                mensaje=mensaje_payload,
                error=mensaje_payload,
            )

        clasificacion = self._clasificar_payload(
            payload, id_cliente_local, ahora
        )
        return ResultadoLecturaReserva(
            exitoso=True,
            clasificacion=clasificacion,
            head_existe=True,
            payload=payload,
            parent=oid,
            mensaje="Reserva leida y validada.",
        )

    def _clasificar_payload(self, payload, id_cliente_local, ahora):
        """
        Clasifica funcionalmente un payload validado.

        LIBERADA se interpreta funcionalmente como LIBRE.
        """

        if payload.es_liberada():
            return ClasificacionReservaObservada.LIBRE

        vencimiento = parsear_timestamp_utc(payload.vencimiento)
        if vencimiento is None:
            return ClasificacionReservaObservada.NO_VERIFICABLE

        if ahora is not None:
            instante_ahora = ahora
        else:
            from modelos_reservas import ahora_utc

            instante_ahora = ahora_utc()

        if instante_ahora >= vencimiento:
            if (
                id_cliente_local
                and payload.id_cliente == id_cliente_local
            ):
                return ClasificacionReservaObservada.VENCIDO_PROPIO
            return ClasificacionReservaObservada.VENCIDO_AJENO

        if (
            id_cliente_local
            and payload.id_cliente == id_cliente_local
        ):
            return ClasificacionReservaObservada.RESERVADO_POR_MI
        return ClasificacionReservaObservada.RESERVADO_POR_OTRO

    # -- Plumbing -------------------------------------------------

    def crear_commit_reserva(self, payload, parent_oid=None):
        """
        Construye un commit tecnico con plumbing:

            git hash-object -w --stdin
            git mktree
            git commit-tree <tree> [-p <parent>] -m <mensaje>

        El tree contiene exactamente una entrada:

            100644 blob <blob_oid>  reserva.json

        parent_oid debe ser el OID remoto observado o None para la
        primera reserva del objeto.

        La identidad tecnica se fija por variables de entorno del
        subproceso; nunca se toca configuracion Git de identidad.

        Devuelve (exitoso, oid, mensaje, error).

        Ultima barrera de la API publica: un fallo inesperado se
        devuelve controlado, nunca se propaga.
        """

        try:
            return self._crear_commit_reserva_interna(payload, parent_oid)
        except Exception as error:
            return (
                False,
                "",
                "Error inesperado al crear el commit de reserva.",
                str(error),
            )

    def _crear_commit_reserva_interna(self, payload, parent_oid=None):
        """
        Implementacion de crear_commit_reserva (sin barrera final).

        Validacion fail-safe: ANTES de ejecutar el primer comando
        Git de escritura (hash-object), se convierte la instancia a
        representacion V1 y se valida con la misma logica autoritativa
        usada para lectura.
        """
        if not isinstance(payload, ReservaPayloadV1):
            return (
                False,
                "",
                "payload debe ser un ReservaPayloadV1.",
                "tipo invalido",
            )

        # Validacion fail-safe antes de escribir objetos Git.
        contenido_json = payload.serializar()
        try:
            datos_dict = json.loads(contenido_json)
        except (ValueError, json.JSONDecodeError) as error:
            return (
                False,
                "",
                "El payload serializado no produce JSON valido.",
                str(error),
            )
        ok_payload, _, mensaje_validacion = validar_payload_reserva(
            datos_dict,
            project_uuid_esperado=payload.project_uuid,
            clave_objeto_esperada=payload.clave_objeto,
        )
        if not ok_payload:
            return (
                False,
                "",
                f"Validacion fail-safe del payload fallo: {mensaje_validacion}",
                "validacion fail-safe",
            )

        contenido = contenido_json

        # 1) Blob.
        ok, oid_blob, stderr, _ = self._ejecutar_git(
            ["hash-object", "-w", "--stdin"],
            entrada=contenido,
        )
        if not ok:
            return (
                False,
                "",
                "No fue posible crear el blob de reserva.",
                stderr,
            )

        # 2) Tree.
        entrada_tree = (
            f"100644 blob {oid_blob}\t{NOMBRE_ARCHIVO_RESERVA}\n"
        )
        ok, oid_tree, stderr, _ = self._ejecutar_git(
            ["mktree"],
            entrada=entrada_tree,
        )
        if not ok:
            return (
                False,
                "",
                "No fue posible crear el tree de reserva.",
                stderr,
            )

        # 3) Commit.
        argumentos = ["commit-tree", oid_tree]
        if parent_oid:
            argumentos.extend(["-p", parent_oid])
        mensaje_commit = (
            f"reserva {payload.clave_objeto} "
            f"{payload.estado.value}"
        )
        argumentos.extend(["-m", mensaje_commit])

        ok, oid_commit, stderr, _ = self._ejecutar_git(
            argumentos,
            env_extra=IDENTIDAD_TECNICA_RESERVAS,
        )
        if not ok:
            return (
                False,
                "",
                "No fue posible crear el commit de reserva.",
                stderr,
            )

        return True, oid_commit, "Commit tecnico creado.", ""

    def publicar_reserva(self, oid, project_uuid, clave_objeto):
        """
        Publica un commit tecnico:

            git -C <backend.git> push origin \
                <oid>:refs/heads/gestorgit-reservas/<hash>

        Sin '+', sin --force, sin --force-with-lease. No crea otros
        refs ni ramas locales.

        Devuelve ResultadoPublicacionReserva. Un Push rechazado o
        incierto se representa como no exitoso; la reconciliacion la
        hace ServicioReservas con Fetch + relectura.

        Ultima barrera de la API publica: un fallo inesperado se
        representa como no exitoso, nunca se propaga.
        """

        try:
            return self._publicar_reserva_interna(
                oid, project_uuid, clave_objeto
            )
        except Exception as error:
            return ResultadoPublicacionReserva(
                exitoso=False,
                oid=oid if isinstance(oid, str) else "",
                mensaje="Error inesperado al publicar la reserva.",
                error=str(error),
            )

    def _publicar_reserva_interna(self, oid, project_uuid, clave_objeto):
        """
        Implementacion de publicar_reserva (sin barrera final).
        """

        ok_entrada, error_entrada = self._validar_entrada(
            project_uuid, clave_objeto
        )
        if not ok_entrada:
            return ResultadoPublicacionReserva(
                exitoso=False,
                mensaje=error_entrada,
                error=error_entrada,
            )
        if not _texto_plano_valido(oid, permitir_vacio=False):
            return ResultadoPublicacionReserva(
                exitoso=False,
                mensaje="oid invalido.",
                error="oid invalido",
            )

        ref = self._ref_heads(project_uuid, clave_objeto)
        ok, stdout, stderr, _ = self._ejecutar_git(
            ["push", "origin", f"{oid}:{ref}"]
        )
        if not ok:
            return ResultadoPublicacionReserva(
                exitoso=False,
                oid=oid,
                mensaje=(
                    "El Push de la reserva no fue aceptado; "
                    "se requiere reconciliacion."
                ),
                error=stderr or stdout,
            )
        return ResultadoPublicacionReserva(
            exitoso=True,
            oid=oid,
            mensaje="Reserva publicada.",
        )


def _rechazar_claves_duplicadas(pairs):
    """
    Hook para json.loads que rechaza claves duplicadas en cualquier
    nivel del objeto JSON.
    """

    vistos = set()
    resultado = {}
    for clave, valor in pairs:
        if clave in vistos:
            raise ValueError(f"Clave duplicada en JSON: {clave!r}")
        vistos.add(clave)
        resultado[clave] = valor
    return resultado
