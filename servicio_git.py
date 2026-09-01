import shutil
import subprocess
from pathlib import Path

from modelos import (
    CambioArchivo,
    EstadoRepositorio,
    ResultadoCambios,
    ResultadoComando,
)
from servicio_proteccion_reservas_git import (
    ResultadoProteccionReservasGit,
)


class ServicioGit:
    """
    Se encarga de toda la comunicación entre nuestra aplicación y Git.

    La interfaz gráfica nunca ejecutará comandos Git directamente.
    Todas las operaciones pasarán por esta clase.

    Modo Equipo Oracle V1 (Bloque E):

    Si se inyecta un protector_reservas
    (ServicioProteccionReservasGit), el staging y el commit pasan
    obligatoriamente por la protección de reservas ANTES del primer
    comando Git de escritura. Sin protector configurado se conserva
    el comportamiento histórico.
    """

    def __init__(self, protector_reservas=None):
        # Buscamos git.exe utilizando el PATH configurado en Windows.
        self.ruta_git = shutil.which("git")

        # Dependencia opcional de Modo Equipo Oracle V1.
        self.protector_reservas = protector_reservas

    def git_disponible(self):
        """
        Indica si Git fue encontrado en el sistema.
        """

        return self.ruta_git is not None

    def obtener_ruta_git(self):
        """
        Devuelve la ruta completa donde fue encontrado git.exe.
        """

        return self.ruta_git

    # REV3 FIX: gramática positiva POR COMANDO. Con protector de
    # Modo Equipo activo, el ejecutor PÚBLICO solo admite las
    # formas EXACTAS de consulta requeridas por los call sites
    # auditados de GestorGit; cualquier variante no reconocida
    # BLOQUEA (default deny). No se autoriza un comando solo por
    # su verbo, ni se mantiene listas de "subcomandos malos": la
    # autorización reconoce opciones y posicionales concretos.
    _OPCION_GLOBAL_PERMITIDA_PREVIA = "--literal-pathspecs"

    @classmethod
    def _comando_lectura_permitido(cls, argumentos):
        """
        Decide si un comando pertenece a la gramática positiva de
        solo lectura (con protector activo).

        Estructura: [opciones globales inertes] <verbo> <opciones
        y posicionales> [-- <rutas>]. El verbo se resuelve contra
        una gramática específica; ante cualquier duda devuelve
        False (BLOQUEAR).
        """

        if not argumentos:
            return False

        if argumentos == ["--version"]:
            return True

        indice = 0

        if argumentos[0] == cls._OPCION_GLOBAL_PERMITIDA_PREVIA:
            indice = 1

        if indice >= len(argumentos):
            return False

        verbo = argumentos[indice]

        if verbo == "--" or verbo.startswith("-"):
            return False

        gramatica = cls._GRAMATICAS_LECTURA.get(verbo)

        if gramatica is None:
            return False

        opciones, posicionales, tras_doble_guion = (
            cls._separar_zonas(argumentos[indice + 1:])
        )

        return gramatica(opciones, posicionales, tras_doble_guion)

    @staticmethod
    def _separar_zonas(argumentos):
        """
        Separa los argumentos que siguen al verbo en:

        - opciones: tokens que empiezan por "-", antes de "--";
        - posicionales: demás tokens antes de "--";
        - tras_doble_guion: tokens después de "--" (rutas).
        """

        opciones = []
        posicionales = []
        tras_doble_guion = []
        zona_tras = False

        for token in argumentos:
            if zona_tras:
                tras_doble_guion.append(token)
                continue

            if token == "--":
                zona_tras = True
                continue

            if token.startswith("-"):
                opciones.append(token)
            else:
                posicionales.append(token)

        return opciones, posicionales, tras_doble_guion

    @staticmethod
    def _gramatica_rev_parse(opciones, posicionales, tras):
        """
        Formas auditadas:

            rev-parse --is-inside-work-tree
            rev-parse --show-toplevel
            rev-parse --git-dir
            rev-parse --verify [--quiet] <ref>
            rev-parse --short <ref>
            rev-parse --git-path <nombre>
        """

        if tras:
            return False

        permitidas = {
            "--is-inside-work-tree",
            "--show-toplevel",
            "--git-dir",
            "--git-path",
            "--verify",
            "--short",
            "--quiet",
        }

        if (
            not set(opciones) <= permitidas
            or len(opciones) != len(set(opciones))
        ):
            return False

        primarios = [
            opcion for opcion in opciones
            if opcion != "--quiet"
        ]

        if len(primarios) != 1:
            return False

        primario = primarios[0]

        if "--quiet" in opciones and primario not in (
            "--verify",
            "--short",
        ):
            return False

        esperados = (
            1 if primario in ("--git-path", "--verify", "--short")
            else 0
        )

        return len(posicionales) == esperados

    @staticmethod
    def _gramatica_status(opciones, posicionales, tras):
        """
        Formas auditadas: subconjunto de

            status --porcelain=v1 -z --untracked-files=all

        sin rutas (el estado se consulta del repositorio completo).
        """

        if tras or posicionales:
            return False

        permitidas = {
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        }

        return (
            set(opciones) <= permitidas
            and len(opciones) == len(set(opciones))
        )

    @staticmethod
    def _gramatica_diff(opciones, posicionales, tras):
        """
        REV4: dos familias positivas EXACTAS; cualquier otra
        combinación BLOQUEA (una forma productora de patch puede
        ejecutar un diff.external configurado aunque no se
        escriba --ext-diff).

        Familia A - staged set de Bloque E (_leer_staged_set):

            diff --cached --name-status -z -C --find-copies-harder

            las cinco opciones exactas, sin rutas ni posicionales.

        Familia B - vista local de UNA ruta (cambios locales):

            diff [--cached] --no-ext-diff --no-textconv
                 (--no-color --unified=3 | --numstat)
                 -- <una ruta>

            las formas productoras de patch exigen --no-ext-diff
            y --no-textconv; --numstat y --unified=3 no coexisten;
            --no-color se exige en la forma unified (el call site
            numstat real no lo pasa).
        """

        if (
            posicionales
            or len(tras) > 1
            or len(opciones) != len(set(opciones))
        ):
            return False

        opciones_set = set(opciones)

        if not tras:
            # Familia A: staged set exacto, sin rutas.
            return opciones_set == {
                "--cached",
                "--name-status",
                "-z",
                "-C",
                "--find-copies-harder",
            }

        # Familia B: vista de exactamente una ruta.
        requeridas = {"--no-ext-diff", "--no-textconv"}

        if not requeridas <= opciones_set:
            return False

        modo = opciones_set & {"--numstat", "--unified=3"}

        if len(modo) != 1:
            return False

        permitidas = requeridas | modo | {"--cached"}

        if "--unified=3" in modo:
            permitidas.add("--no-color")

        return opciones_set <= permitidas

    @staticmethod
    def _gramatica_show(opciones, posicionales, tras):
        """
        Forma auditada: show HEAD:<ruta-interna> (lectura de un
        blob del commit actual, sin opciones).
        """

        return (
            not opciones
            and not tras
            and len(posicionales) == 1
            and posicionales[0].startswith("HEAD:")
        )

    @staticmethod
    def _gramatica_log(opciones, posicionales, tras):
        """Forma auditada: log -1 --format=%s."""

        return (
            not tras
            and not posicionales
            and len(opciones) == 2
            and set(opciones) == {"-1", "--format=%s"}
        )

    @staticmethod
    def _gramatica_for_each_ref(opciones, posicionales, tras):
        """
        Forma auditada:

            for-each-ref [--format=<formato>] [refs/<raíz>]
        """

        if tras or len(opciones) > 1:
            return False

        if opciones and not opciones[0].startswith("--format="):
            return False

        if len(posicionales) > 1:
            return False

        return (
            not posicionales
            or posicionales[0].startswith("refs/")
        )

    @staticmethod
    def _gramatica_check_ref_format(opciones, posicionales, tras):
        """Forma auditada: check-ref-format refs/<raíz>/<nombre>."""

        return (
            not opciones
            and not tras
            and len(posicionales) == 1
            and posicionales[0].startswith("refs/")
        )

    @staticmethod
    def _gramatica_symbolic_ref(opciones, posicionales, tras):
        """
        Forma auditada (SOLO consulta):

            symbolic-ref [--quiet] [--short] HEAD

        --delete/-d y la forma con nuevo valor BLOQUEAN.
        """

        if tras:
            return False

        if not set(opciones) <= {"--quiet", "--short"}:
            return False

        return len(posicionales) == 1 and posicionales[0] == "HEAD"

    @staticmethod
    def _gramatica_config(opciones, posicionales, tras):
        """
        Forma auditada (única usada por los call sites):

            config --get <clave>

        get-all/get-regexp no se usan hoy: no están admitidas.
        Cualquier otra acción o combinación BLOQUEA.
        """

        return (
            not tras
            and opciones == ["--get"]
            and len(posicionales) == 1
        )

    @staticmethod
    def _gramatica_remote(opciones, posicionales, tras):
        """
        Formas de lectura local auditadas/admitidas:

            remote
            remote [-v | --verbose]
            remote get-url [--all] [--push] <remoto>

        Subcomandos de escritura (update/set-head/rm/remove/add/
        rename/set-url/set-branches/prune) y `remote show`
        (puede implicar red) BLOQUEAN.
        """

        if tras:
            return False

        if len(set(opciones)) != len(opciones):
            return False

        if not set(opciones) <= {"-v", "--verbose", "--all", "--push"}:
            return False

        if not posicionales:
            # Listado: solo con -v/--verbose como opciones.
            return all(
                opcion in ("-v", "--verbose")
                for opcion in opciones
            )

        subcomando = posicionales[0]

        if subcomando != "get-url":
            return False

        return len(posicionales) == 2

    @staticmethod
    def _gramatica_restore(opciones, posicionales, tras):
        """
        Excepción estrecha para el descarte auditado (Bloque G no
        iniciado): únicamente

            restore --worktree -- <una ruta>

        Sin --staged, sin --source, sin otras opciones.
        """

        return (
            opciones == ["--worktree"]
            and not posicionales
            and len(tras) == 1
        )

    _GRAMATICAS_LECTURA = {
        "rev-parse": _gramatica_rev_parse,
        "status": _gramatica_status,
        "diff": _gramatica_diff,
        "show": _gramatica_show,
        "log": _gramatica_log,
        "for-each-ref": _gramatica_for_each_ref,
        "check-ref-format": _gramatica_check_ref_format,
        "symbolic-ref": _gramatica_symbolic_ref,
        "config": _gramatica_config,
        "remote": _gramatica_remote,
        "restore": _gramatica_restore,
    }

    def ejecutar_git(
        self,
        argumentos,
        ruta_repositorio=None,
        tiempo_maximo=30
    ):
        """
        Ejecutor PÚBLICO de Git.

        Con protector de Modo Equipo configurado (REV2 FIX A)
        solo acepta comandos de la allowlist de SOLO LECTURA
        (con sus restricciones por verbo); todo comando no
        reconocido como inequívocamente read-only BLOQUEA, de
        modo que el ejecutor público nunca puede convertirse en
        una vía arbitraria de escritura Git (ni mediante aliases).

        Sin protector se conserva el comportamiento histórico
        completo.

        Las operaciones productivas protegidas (staging, commit,
        unstaging y detección de copies) usan el ejecutor interno
        SOLO después de sus guardas.
        """

        if self.protector_reservas is not None:
            if not self._comando_lectura_permitido(argumentos):
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        "Modo Equipo Oracle: el comando Git "
                        "solicitado no es una consulta de solo "
                        "lectura reconocida y no puede ejecutarse "
                        "mientras el protector de reservas está "
                        "activo.\n\n"
                        "Use las operaciones de staging y commit "
                        "de GestorGit, que validan las reservas "
                        "de los objetos Oracle antes de escribir "
                        "el índice."
                    ),
                    comando=self._convertir_comando_a_texto(
                        ["git"] + list(argumentos)
                    )
                )

        return self._ejecutar_git_interno(
            argumentos,
            ruta_repositorio=ruta_repositorio,
            tiempo_maximo=tiempo_maximo
        )

    def _ejecutar_git_interno(
        self,
        argumentos,
        ruta_repositorio=None,
        tiempo_maximo=30
    ):
        """
        Ejecutor Git CRUDO/INTERNO (sin guarda del protector).

        Uso exclusivo interno: las API protegidas lo invocan
        SOLO después de una protección de reservas positiva.
        """

        if not self.git_disponible():
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="Git no fue encontrado en el sistema.",
                comando=""
            )

        # Construimos siempre el comando como una lista.
        #
        # Nunca utilizamos shell=True.
        comando = [self.ruta_git] + argumentos

        carpeta_trabajo = None

        if ruta_repositorio is not None:
            carpeta_trabajo = Path(ruta_repositorio)

            if not carpeta_trabajo.exists():
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error="La carpeta indicada no existe.",
                    comando=self._convertir_comando_a_texto(comando)
                )

            if not carpeta_trabajo.is_dir():
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error="La ruta indicada no corresponde a una carpeta.",
                    comando=self._convertir_comando_a_texto(comando)
                )

        try:
            resultado = subprocess.run(
                comando,
                cwd=carpeta_trabajo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=tiempo_maximo,
                shell=False
            )

            # No utilizamos strip() porque algunos espacios
            # iniciales tienen significado en la salida de Git.
            salida = resultado.stdout.rstrip("\r\n")
            error = resultado.stderr.rstrip("\r\n")

            return ResultadoComando(
                exitoso=resultado.returncode == 0,
                codigo_salida=resultado.returncode,
                salida=salida,
                error=error,
                comando=self._convertir_comando_a_texto(comando)
            )

        except subprocess.TimeoutExpired:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    f"El comando superó el tiempo máximo "
                    f"de {tiempo_maximo} segundos."
                ),
                comando=self._convertir_comando_a_texto(comando)
            )

        except FileNotFoundError:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="No fue posible encontrar git.exe.",
                comando=self._convertir_comando_a_texto(comando)
            )

        except PermissionError:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="Windows denegó el acceso al ejecutar Git.",
                comando=self._convertir_comando_a_texto(comando)
            )

        except OSError as error_sistema:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=f"Error del sistema operativo: {error_sistema}",
                comando=self._convertir_comando_a_texto(comando)
            )

    def obtener_version(self):
        """
        Obtiene la versión instalada de Git.
        """

        return self.ejecutar_git(
            argumentos=["--version"]
        )

    def analizar_repositorio(self, ruta_repositorio):
        """
        Analiza una carpeta para determinar si contiene
        un repositorio Git válido.

        Esta operación solamente consulta información.
        """

        if ruta_repositorio is None:
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="No se indicó ninguna carpeta."
            )

        ruta_texto = str(ruta_repositorio).strip()

        if not ruta_texto:
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="No se indicó ninguna carpeta."
            )

        carpeta = Path(ruta_texto)

        if not carpeta.exists():
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="La carpeta indicada no existe."
            )

        if not carpeta.is_dir():
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="La ruta indicada no corresponde a una carpeta."
            )

        resultado_validacion = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--is-inside-work-tree"
            ],
            ruta_repositorio=carpeta
        )

        if (
            not resultado_validacion.exitoso
            or resultado_validacion.salida.lower() != "true"
        ):
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="La carpeta no corresponde a un repositorio Git."
            )

        # Obtenemos la raíz verdadera del repositorio.
        resultado_raiz = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--show-toplevel"
            ],
            ruta_repositorio=carpeta
        )

        if resultado_raiz.exitoso:
            ruta_raiz = resultado_raiz.salida
        else:
            ruta_raiz = str(carpeta.resolve())

        # Obtenemos la rama actual.
        resultado_rama = self.ejecutar_git(
            argumentos=[
                "symbolic-ref",
                "--quiet",
                "--short",
                "HEAD"
            ],
            ruta_repositorio=ruta_raiz
        )

        if resultado_rama.exitoso:
            rama_actual = resultado_rama.salida
        else:
            # Esto puede ocurrir cuando HEAD está separado.
            rama_actual = ""

        # Comprobamos si existe al menos un commit.
        resultado_head = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--verify",
                "HEAD"
            ],
            ruta_repositorio=ruta_raiz
        )

        tiene_commits = resultado_head.exitoso

        # Obtenemos los remotos configurados.
        resultado_remotos = self.ejecutar_git(
            argumentos=["remote"],
            ruta_repositorio=ruta_raiz
        )

        remotos = []

        if resultado_remotos.exitoso and resultado_remotos.salida:
            remotos = [
                linea.strip()
                for linea in resultado_remotos.salida.splitlines()
                if linea.strip()
            ]

        return EstadoRepositorio(
            es_repositorio=True,
            ruta_raiz=ruta_raiz,
            rama_actual=rama_actual,
            tiene_commits=tiene_commits,
            remotos=remotos,
            mensaje="Repositorio Git válido."
        )

    def obtener_cambios(self, ruta_repositorio):
        """
        Obtiene todos los archivos que tienen cambios.

        Esta operación solamente consulta información.
        """

        resultado = self.ejecutar_git(
            argumentos=[
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all"
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return ResultadoCambios(
                exitoso=False,
                error=resultado.error
            )

        if not resultado.salida:
            return ResultadoCambios(
                exitoso=True,
                cambios=[]
            )

        cambios = []

        # Git separa los registros mediante NUL cuando usamos -z.
        registros = resultado.salida.split("\0")

        indice = 0

        while indice < len(registros):
            registro = registros[indice]

            if not registro:
                indice += 1
                continue

            if len(registro) < 4:
                return ResultadoCambios(
                    exitoso=False,
                    error=(
                        "Git devolvió un estado de archivo "
                        "con un formato inesperado."
                    )
                )

            estado_indice = registro[0]
            estado_trabajo = registro[1]
            ruta_archivo = registro[3:]

            ruta_anterior = ""

            # Los renombrados y copiados utilizan una segunda ruta.
            if (
                estado_indice in ("R", "C")
                or estado_trabajo in ("R", "C")
            ):
                if indice + 1 >= len(registros):
                    return ResultadoCambios(
                        exitoso=False,
                        error=(
                            "Git informó un archivo renombrado "
                            "o copiado sin indicar su ruta anterior."
                        )
                    )

                ruta_anterior = registros[indice + 1]
                indice += 1

            descripcion = self._traducir_estado_archivo(
                estado_indice,
                estado_trabajo
            )

            preparado = estado_indice not in (
                " ",
                "?",
                "!"
            )

            # Los conflictos de merge son un estado especial:
            # no son "preparados para commit" ni "sin preparar".
            # El dato estructurado procede exclusivamente de los
            # códigos Git; nunca del texto de la descripción.
            en_conflicto = self._es_estado_conflicto(
                estado_indice,
                estado_trabajo
            )

            # El área preparada quedó desactualizada cuando el
            # archivo está preparado y además existe un cambio
            # posterior en el working tree. Los conflictos no
            # son actualizables mediante git add.
            requiere_actualizar_preparado = (
                preparado
                and estado_trabajo not in (
                    " ",
                    "?",
                    "!"
                )
                and not en_conflicto
            )

            cambios.append(
                CambioArchivo(
                    ruta=ruta_archivo,
                    estado_indice=estado_indice,
                    estado_trabajo=estado_trabajo,
                    descripcion=descripcion,
                    preparado=preparado,
                    ruta_anterior=ruta_anterior,
                    requiere_actualizar_preparado=(
                        requiere_actualizar_preparado
                    ),
                    en_conflicto=en_conflicto
                )
            )

            indice += 1

        return ResultadoCambios(
            exitoso=True,
            cambios=cambios
        )

    def agregar_archivos(
        self,
        ruta_repositorio,
        rutas_archivos
    ):
        """
        Prepara uno o varios archivos para el próximo commit.

        Equivale a git add.
        """

        estado_repositorio = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado_repositorio.es_repositorio:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=estado_repositorio.mensaje,
                comando=""
            )

        rutas_validas, mensaje_error = (
            self._validar_rutas_relativas(
                rutas_archivos
            )
        )

        if mensaje_error:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=mensaje_error,
                comando=""
            )

        # Defensa en profundidad: consultamos nuevamente el estado
        # antes del git add productivo. Si alguna ruta está en
        # conflicto, bloqueamos TODA la operación: un conflicto no
        # debe poder entrar en el área preparada mediante
        # "Preparar seleccionados".
        resultado_cambios = self.obtener_cambios(
            estado_repositorio.ruta_raiz
        )

        if not resultado_cambios.exitoso:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=resultado_cambios.error,
                comando=""
            )

        cambios_por_ruta = {
            cambio.ruta: cambio
            for cambio in resultado_cambios.cambios
        }

        for ruta_archivo in rutas_validas:
            cambio = cambios_por_ruta.get(
                ruta_archivo
            )

            if (
                cambio is not None
                and cambio.en_conflicto
            ):
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        f"El archivo '{ruta_archivo}' está en "
                        "conflicto y no se preparará.\n\n"
                        "Git necesita que una persona decida cómo "
                        "resolver el conflicto. GestorGit no elige "
                        "una versión automáticamente."
                    ),
                    comando=""
                )

        # Bloque E: protección de reservas de Modo Equipo.
        #
        # Antes del primer comando Git de escritura sobre el índice,
        # TODAS las rutas involucradas deben pasar la protección
        # local: rutas indicadas + lado origen de renombrados
        # (ruta_anterior) + origen de copias inequívocas (REV2 FIX
        # B, solo lectura). Si la protección BLOQUEA no se ejecuta
        # ningún git add.
        exitoso_expansion, rutas_expandidas, error_expansion = (
            self._expandir_rutas_con_origenes_copia(
                estado_repositorio.ruta_raiz,
                rutas_validas
            )
        )

        if not exitoso_expansion:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=error_expansion,
                comando=""
            )

        rutas_involucradas = self._rutas_para_proteccion(
            rutas_expandidas,
            cambios_por_ruta
        )

        # V1.2: el staging valida el contenido EXACTO del working
        # tree que se va a preparar contra la identidad de la ruta.
        exitoso_contenido, contenido_por_ruta, error_contenido = (
            self._obtener_contenido_working_tree(
                estado_repositorio.ruta_raiz,
                rutas_involucradas
            )
        )

        if not exitoso_contenido:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=error_contenido,
                comando=""
            )

        resultado_proteccion = self._aplicar_proteccion_reservas(
            "staging",
            rutas_involucradas,
            contenido_por_ruta=contenido_por_ruta
        )

        if resultado_proteccion is not None:
            return resultado_proteccion

        argumentos = [
            "--literal-pathspecs",
            "add",
            "--",
        ]

        argumentos.extend(
            rutas_validas
        )

        # Escritura productiva por el ejecutor interno: solo se
        # alcanza si la protección devolvió PERMITIDA (o si no
        # hay protector configurado).
        return self._ejecutar_git_interno(
            argumentos=argumentos,
            ruta_repositorio=estado_repositorio.ruta_raiz
        )

    def quitar_archivos_preparados(
        self,
        ruta_repositorio,
        rutas_archivos
    ):
        """
        Quita uno o varios archivos del área preparada.

        IMPORTANTE:
            Esta operación NO elimina los archivos del disco.
        """

        estado_repositorio = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado_repositorio.es_repositorio:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=estado_repositorio.mensaje,
                comando=""
            )

        rutas_validas, mensaje_error = (
            self._validar_rutas_relativas(
                rutas_archivos
            )
        )

        if mensaje_error:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=mensaje_error,
                comando=""
            )

        # Defensa en profundidad: consultamos nuevamente el estado
        # antes del restore --staged / rm --cached productivo. Cada
        # ruta debe seguir siendo un cambio válido para quitar de
        # preparados y NO debe estar en conflicto; un conflicto no
        # se "quita de preparados" (eso alteraría el estado unmerged
        # del índice). Un error de consulta bloquea: nunca se
        # interpreta un fallo como estado seguro.
        resultado_cambios = self.obtener_cambios(
            estado_repositorio.ruta_raiz
        )

        if not resultado_cambios.exitoso:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=resultado_cambios.error,
                comando=""
            )

        cambios_por_ruta = {
            cambio.ruta: cambio
            for cambio in resultado_cambios.cambios
        }

        for ruta_archivo in rutas_validas:
            cambio = cambios_por_ruta.get(
                ruta_archivo
            )

            if cambio is None:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        f"El archivo '{ruta_archivo}' ya no "
                        "presenta cambios pendientes."
                    ),
                    comando=""
                )

            if cambio.en_conflicto:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        f"El archivo '{ruta_archivo}' está en "
                        "conflicto y no se quitará de preparados."
                        " No se ejecutó ningún comando Git.\n\n"
                        "Git necesita que una persona decida cómo "
                        "resolver el conflicto. GestorGit no elige "
                        "una versión automáticamente."
                    ),
                    comando=""
                )

            if not cambio.preparado:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        f"El archivo '{ruta_archivo}' ya no "
                        "está preparado."
                    ),
                    comando=""
                )

        if estado_repositorio.tiene_commits:
            # Ya existe HEAD.
            argumentos = [
                "--literal-pathspecs",
                "restore",
                "--staged",
                "--",
            ]

        else:
            # En el primer commit todavía no existe HEAD.
            #
            # rm --cached quita el archivo del índice,
            # pero conserva el archivo físico.
            argumentos = [
                "--literal-pathspecs",
                "rm",
                "--cached",
                "--",
            ]

        argumentos.extend(
            rutas_validas
        )

        # Unstaging por el ejecutor interno: quitar del índice
        # reduce el riesgo y no requiere reserva (comportamiento
        # histórico), pero usa el camino interno del servicio.
        return self._ejecutar_git_interno(
            argumentos=argumentos,
            ruta_repositorio=estado_repositorio.ruta_raiz
        )

    def actualizar_archivos_preparados(
        self,
        ruta_repositorio,
        rutas_archivos
    ):
        """
        Actualiza el área preparada con la versión actual completa
        de los archivos indicados.

        Equivale a volver a ejecutar git add sobre cada ruta
        explícita.

        No modifica el working tree y no crea commits.
        No quita los archivos del staging antes de actualizar.
        """

        estado_repositorio = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado_repositorio.es_repositorio:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=estado_repositorio.mensaje,
                comando=""
            )

        rutas_validas, mensaje_error = (
            self._validar_rutas_relativas(
                rutas_archivos
            )
        )

        if mensaje_error:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=mensaje_error,
                comando=""
            )

        if not rutas_validas:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "No se indicó ningún archivo "
                    "para actualizar."
                ),
                comando=""
            )

        # Consultamos nuevamente el estado antes de ejecutar Git:
        # cada archivo debe seguir preparado, con cambios nuevos
        # fuera del índice y sin conflictos.
        resultado_cambios = self.obtener_cambios(
            estado_repositorio.ruta_raiz
        )

        if not resultado_cambios.exitoso:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=resultado_cambios.error,
                comando=""
            )

        cambios_por_ruta = {
            cambio.ruta: cambio
            for cambio in resultado_cambios.cambios
        }

        rutas_actualizar = []

        for ruta_archivo in rutas_validas:
            cambio = cambios_por_ruta.get(
                ruta_archivo
            )

            if cambio is None:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        f"El archivo '{ruta_archivo}' ya no "
                        "presenta cambios pendientes."
                    ),
                    comando=""
                )

            if not cambio.preparado:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        f"El archivo '{ruta_archivo}' ya no "
                        "está preparado."
                    ),
                    comando=""
                )

            if cambio.en_conflicto:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        f"El archivo '{ruta_archivo}' está en "
                        "conflicto y no se actualizará."
                    ),
                    comando=""
                )

            if not cambio.requiere_actualizar_preparado:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        f"El archivo '{ruta_archivo}' ya no "
                        "requiere actualización de los cambios "
                        "preparados."
                    ),
                    comando=""
                )

            rutas_actualizar.append(
                ruta_archivo
            )

        # Bloque E: protección de reservas de Modo Equipo.
        #
        # Actualizar preparados vuelve a ejecutar git add sobre las
        # rutas indicadas: también pasa por la expansión de copias
        # (REV2 FIX B) y por la protección antes del primer comando
        # de escritura, incluyendo el lado origen cuando la entrada
        # es un renombrado/copiado.
        exitoso_expansion, rutas_expandidas, error_expansion = (
            self._expandir_rutas_con_origenes_copia(
                estado_repositorio.ruta_raiz,
                rutas_actualizar
            )
        )

        if not exitoso_expansion:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=error_expansion,
                comando=""
            )

        rutas_involucradas = self._rutas_para_proteccion(
            rutas_expandidas,
            cambios_por_ruta
        )

        # V1.2: Actualizar preparados revalida el contenido EXACTO
        # del working tree (nunca reutiliza una validación previa).
        exitoso_contenido, contenido_por_ruta, error_contenido = (
            self._obtener_contenido_working_tree(
                estado_repositorio.ruta_raiz,
                rutas_involucradas
            )
        )

        if not exitoso_contenido:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=error_contenido,
                comando=""
            )

        resultado_proteccion = self._aplicar_proteccion_reservas(
            "staging",
            rutas_involucradas,
            contenido_por_ruta=contenido_por_ruta
        )

        if resultado_proteccion is not None:
            return resultado_proteccion

        argumentos = [
            "--literal-pathspecs",
            "add",
            "--",
        ]

        argumentos.extend(
            rutas_actualizar
        )

        # Escritura productiva por el ejecutor interno: solo se
        # alcanza si la protección devolvió PERMITIDA (o si no
        # hay protector configurado).
        return self._ejecutar_git_interno(
            argumentos=argumentos,
            ruta_repositorio=estado_repositorio.ruta_raiz
        )

    def crear_commit(
        self,
        ruta_repositorio,
        mensaje_commit
    ):
        """
        Crea un commit utilizando todos los archivos
        que actualmente están preparados.

        La función realiza varias validaciones antes
        de permitir el commit.
        """

        estado_repositorio = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado_repositorio.es_repositorio:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=estado_repositorio.mensaje,
                comando=""
            )

        # No permitimos commits cuando HEAD está separado.
        if not estado_repositorio.rama_actual:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "No se puede crear el commit porque HEAD "
                    "no está asociado a una rama."
                ),
                comando=""
            )

        # Validamos el mensaje.
        if mensaje_commit is None:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="El mensaje del commit es obligatorio.",
                comando=""
            )

        mensaje = str(
            mensaje_commit
        ).strip()

        if not mensaje:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="El mensaje del commit es obligatorio.",
                comando=""
            )

        # Un argumento de proceso no puede contener NUL.
        if "\x00" in mensaje:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="El mensaje del commit contiene un carácter inválido.",
                comando=""
            )

        # Comprobamos si Git está realizando otra operación.
        operacion_en_curso = self.detectar_operacion_en_curso(
            estado_repositorio.ruta_raiz
        )

        if operacion_en_curso:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=operacion_en_curso,
                comando=""
            )

        # Nunca eliminamos index.lock automáticamente.
        ruta_bloqueo = self._obtener_ruta_git_interna(
            estado_repositorio.ruta_raiz,
            "index.lock"
        )

        if (
            ruta_bloqueo is not None
            and ruta_bloqueo.exists()
        ):
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "Git informa que el índice está bloqueado "
                    "mediante index.lock.\n\n"
                    "Compruebe que no exista otro proceso Git "
                    "trabajando sobre este repositorio.\n\n"
                    "La aplicación no eliminará el bloqueo "
                    "automáticamente."
                ),
                comando=""
            )

        # Comprobamos identidad de Git.
        mensaje_identidad = self._validar_identidad_git(
            estado_repositorio.ruta_raiz
        )

        if mensaje_identidad:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=mensaje_identidad,
                comando=""
            )

        # Consultamos nuevamente el estado real antes del commit.
        resultado_cambios = self.obtener_cambios(
            estado_repositorio.ruta_raiz
        )

        if not resultado_cambios.exitoso:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=resultado_cambios.error,
                comando=""
            )

        # No permitimos commits mientras existan conflictos.
        # La decisión usa el dato estructurado en_conflicto
        # (procedente de los códigos Git), nunca el texto
        # localizado de la descripción.
        archivos_conflicto = [
            cambio.ruta
            for cambio in resultado_cambios.cambios
            if cambio.en_conflicto
        ]

        if archivos_conflicto:
            lista = "\n".join(
                archivos_conflicto
            )

            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "No se puede crear el commit porque existen "
                    "archivos con conflictos:\n\n"
                    f"{lista}"
                ),
                comando=""
            )

        archivos_preparados = [
            cambio
            for cambio in resultado_cambios.cambios
            if cambio.preparado
        ]

        if not archivos_preparados:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "No hay archivos preparados para crear "
                    "el commit."
                ),
                comando=""
            )

        # Si un archivo fue preparado y luego volvió a cambiar,
        # el commit incluiría una versión distinta de la que el
        # usuario está viendo actualmente.
        #
        # Para evitar confusión bloqueamos el commit.
        archivos_modificados_despues = [
            cambio.ruta
            for cambio in archivos_preparados
            if cambio.estado_trabajo not in (
                " ",
                "?",
                "!"
            )
        ]

        if archivos_modificados_despues:
            lista = "\n".join(
                archivos_modificados_despues
            )

            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "No se puede crear el commit porque algunos "
                    "archivos fueron modificados después de "
                    "haber sido preparados:\n\n"
                    f"{lista}\n\n"
                    "Use 'Actualizar preparados' para incluir su "
                    "versión actual completa en el próximo commit.\n\n"
                    "También puede usar 'Quitar de preparados' "
                    "si no desea incluir la versión actualmente "
                    "preparada."
                ),
                comando=""
            )

        # Bloque E: el commit vuelve a validar las reservas del
        # conjunto preparado REAL, aunque el staging haya sido
        # permitido antes. Así se protege también el caso de un
        # archivo Oracle preparado fuera de GestorGit: el commit
        # se bloquea igualmente si la reserva no es válida.
        if self.protector_reservas is not None:
            resultado_proteccion_commit = (
                self._proteger_commit_con_relectura(
                    estado_repositorio.ruta_raiz
                )
            )

            if resultado_proteccion_commit is not None:
                return resultado_proteccion_commit

        # Ejecutamos finalmente el commit por el ejecutor interno:
        # solo se alcanza tras protección positiva y relectura
        # (o sin protector configurado).
        #
        # No utilizamos --no-verify porque respetamos cualquier
        # hook configurado en el repositorio.
        return self._ejecutar_git_interno(
            argumentos=[
                "commit",
                "-m",
                mensaje
            ],
            ruta_repositorio=estado_repositorio.ruta_raiz,
            tiempo_maximo=60
        )

    def _aplicar_proteccion_reservas(self, operacion, rutas,
                                     contenido_por_ruta=None):
        """
        Aplica la protección de reservas de Modo Equipo si hay un
        protector configurado.

        contenido_por_ruta (V1.2) transporta el contenido exacto a
        validar: working tree para staging y blob del índice para
        commit. None conserva la semántica V1.1 (sin validación
        de contenido).

        Devuelve None cuando la operación puede continuar (no hay
        protector o la protección devuelve PERMITIDA), o un
        ResultadoComando fallido y controlado cuando la protección
        BLOQUEA.

        Fail-safe estricto (REV1 FIX 3 + REV2 FIX C): solo se
        acepta como respuesta autorizante el contrato real,
        `ResultadoProteccionReservasGit` (por isinstance), con
        `permitido` booleano exacto y `componer_mensaje()`
        verificable cuando bloquea. Cualquier otra cosa
        BLOQUEA; nunca se degrada a permitido.

        Fail-safe de mensajes (REV1 FIX 4): las barreras
        genéricas nunca incluyen str(error), tracebacks ni
        detalle técnico en el texto devuelto.
        """

        if self.protector_reservas is None:
            return None

        try:
            if operacion == "staging":
                resultado = self.protector_reservas.proteger_staging(
                    rutas,
                    contenido_por_ruta=contenido_por_ruta,
                )
            else:
                resultado = self.protector_reservas.proteger_commit(
                    rutas,
                    contenido_por_ruta=contenido_por_ruta,
                )
        except Exception:
            return self._proteccion_fallida_generico()

        if not isinstance(resultado, ResultadoProteccionReservasGit):
            # REV2 FIX C: un objeto ajeno con permitido=True no
            # autoriza nunca; solo el contrato real.
            return self._proteccion_fallida_generico()

        permitido = resultado.permitido

        if not isinstance(permitido, bool):
            return self._proteccion_fallida_generico()

        if permitido is True:
            return None

        componer = getattr(resultado, "componer_mensaje", None)

        if not callable(componer):
            return self._proteccion_fallida_generico()

        mensaje = componer()

        if not isinstance(mensaje, str) or not mensaje:
            return self._proteccion_fallida_generico()

        return ResultadoComando(
            exitoso=False,
            codigo_salida=-1,
            salida="",
            error=mensaje,
            comando=""
        )

    @staticmethod
    def _proteccion_fallida_generico():
        """
        Resultado controlado para un protector que falló de forma
        inesperada o devolvió un resultado no contractual.

        Sin detalle técnico: la información interna no entra al
        texto listo para la GUI.
        """

        return ResultadoComando(
            exitoso=False,
            codigo_salida=-1,
            salida="",
            error=(
                "La protección de reservas de Modo Equipo falló "
                "de forma inesperada; la operación queda "
                "bloqueada por seguridad."
            ),
            comando=""
        )

    @staticmethod
    def _rutas_para_proteccion(rutas_base, cambios_por_ruta):
        """
        Determina el conjunto de rutas involucradas para la
        protección de reservas.

        Incluye cada ruta indicada y, cuando el cambio es un
        renombrado/copiado, también la ruta anterior: ambos lados
        de la transformación quedan protegidos sin perder el lado
        origen (se reutiliza el dato ruta_anterior del modelo
        existente).
        """

        rutas_involucradas = []

        for ruta in rutas_base:
            if ruta not in rutas_involucradas:
                rutas_involucradas.append(ruta)

            cambio = (
                cambios_por_ruta.get(ruta)
                if cambios_por_ruta
                else None
            )

            if (
                cambio is not None
                and cambio.ruta_anterior
                and cambio.ruta_anterior not in rutas_involucradas
            ):
                rutas_involucradas.append(cambio.ruta_anterior)

        return rutas_involucradas

    def _expandir_rutas_con_origenes_copia(self, ruta_raiz, rutas):
        """
        REV2 FIX B: determina, ANTES del primer write productivo del
        índice, si alguna ruta por preparar es una copia del
        contenido de otra ruta rastreada; en ese caso el ORIGEN se
        incorpora al conjunto de protección.

        Estrategia 100% local, de SOLO LECTURA y sin escribir
        objetos en el repositorio productivo:

        1. el contenido del HEAD se mapea con
           `git ls-tree -r -z HEAD` (solo lectura);
        2. el contenido ACTUAL de cada ruta Oracle se identifica
           con `git hash-object` SIN -w (calcula el OID sin
           almacenar nada);
        3. se buscan rutas rastreadas con el mismo OID:

           - ninguna coincidencia (o solo la propia ruta):
             archivo genuinamente nuevo/modificado;
           - exactamente una coincidencia: copia inequívoca, se
             exige la reserva del origen;
           - más de una coincidencia: copia AMBIGUA -> BLOQUEAR
             (incertidumbre -> BLOQUEAR);
           - contenido no calculable o árbol HEAD ilegible:
             BLOQUEAR.

        Nunca modifica el índice ni escribe objetos: si algo no
        puede determinarse con seguridad, la operación se bloquea.
        Solo se analizan las rutas que el resolvedor del protector
        clasifica como objetos Oracle reservables: una copia entre
        archivos ordinarios no afecta a reservas.

        Devuelve (exitoso, rutas_expandidas, error).
        """

        # Sin protector no hay protección que alimentar: las rutas
        # se devuelven tal cual (comportamiento histórico).
        if self.protector_reservas is None:
            return (True, list(rutas), "")

        es_oracle, mapa_contenido, error = (
            self._mapear_contenido_head(ruta_raiz)
        )

        if not es_oracle:
            return (False, [], error)

        rutas_expandidas = []
        for ruta in rutas:
            if ruta not in rutas_expandidas:
                rutas_expandidas.append(ruta)

        for ruta in rutas:
            if not self._ruta_requiere_analisis_copia(ruta):
                continue

            # Una ruta eliminada en el working tree no tiene
            # contenido nuevo que copiar: no aplica análisis de
            # copia (la reserva de la ruta se exige igualmente en
            # la protección).
            if not (Path(ruta_raiz) / ruta).exists():
                continue

            resultado_oid = self._ejecutar_git_interno(
                argumentos=["hash-object", "--", ruta],
                ruta_repositorio=ruta_raiz
            )

            if not resultado_oid.exitoso:
                return (
                    False,
                    [],
                    (
                        "Modo Equipo Oracle: no fue posible "
                        "determinar de forma segura el contenido "
                        f"de '{ruta}' antes de preparar; operación "
                        "bloqueada."
                    ),
                )

            oid = resultado_oid.salida.strip()
            coincidencias = [
                ruta_rastreada
                for ruta_rastreada in mapa_contenido.get(oid, [])
                if ruta_rastreada != ruta
            ]

            if len(coincidencias) > 1:
                return (
                    False,
                    [],
                    (
                        "Modo Equipo Oracle: origen de copia "
                        f"ambiguo para '{ruta}': su contenido "
                        f"coincide con {len(coincidencias)} rutas "
                        "rastreadas ("
                        + ", ".join(sorted(coincidencias))
                        + "). No puede determinarse el origen de "
                        "forma segura; operación bloqueada."
                    ),
                )

            if (
                len(coincidencias) == 1
                and coincidencias[0] not in rutas_expandidas
            ):
                rutas_expandidas.append(coincidencias[0])

        return (True, rutas_expandidas, "")

    def _mapear_contenido_head(self, ruta_raiz):
        """
        Mapea el contenido del árbol HEAD: OID blob -> rutas.

        Consulta de SOLO LECTURA (`git ls-tree -r -z HEAD`) con
        parser fail-safe. Un repositorio sin commits no tiene
        contenido rastreado (mapa vacío, no es error).

        Devuelve (exitoso, mapa, error).
        """

        resultado_head = self._ejecutar_git_interno(
            argumentos=["rev-parse", "--verify", "--quiet", "HEAD"],
            ruta_repositorio=ruta_raiz
        )

        if not resultado_head.exitoso:
            return (True, {}, "")

        resultado_arbol = self._ejecutar_git_interno(
            argumentos=["ls-tree", "-r", "-z", "HEAD"],
            ruta_repositorio=ruta_raiz
        )

        if not resultado_arbol.exitoso:
            return (
                False,
                None,
                (
                    "Modo Equipo Oracle: no fue posible leer el "
                    "árbol HEAD para analizar copias; operación "
                    "bloqueada."
                )
            )

        mapa = {}

        for entrada in resultado_arbol.salida.split("\0"):
            if not entrada:
                continue

            partes = entrada.split("\t", 1)

            if len(partes) != 2:
                return (
                    False,
                    None,
                    (
                        "Modo Equipo Oracle: salida de ls-tree "
                        "malformada; operación bloqueada."
                    )
                )

            meta = partes[0].split()

            if len(meta) != 3:
                return (
                    False,
                    None,
                    (
                        "Modo Equipo Oracle: salida de ls-tree "
                        "malformada; operación bloqueada."
                    )
                )

            _modo, tipo, oid = meta

            if tipo != "blob":
                continue

            mapa.setdefault(oid, []).append(partes[1])

        return (True, mapa, "")

    def _ruta_requiere_analisis_copia(self, ruta):
        """
        True si la ruta resuelve, según el resolvedor inyectado del
        protector, a un objeto Oracle reservable (solo esas rutas
        necesitan análisis de copia).

        Ante cualquier resultado no verificable se pide análisis
        (conservador): la protección final decide.
        """

        resolvedor = getattr(
            self.protector_reservas, "resolvedor_oracle", None
        )

        if resolvedor is None or not callable(
            getattr(resolvedor, "resolver", None)
        ):
            return True

        try:
            resultado = resolvedor.resolver(ruta)
        except Exception:
            return True

        if resultado is None:
            return True

        return bool(
            getattr(resultado, "es_ruta_valida", False)
            and getattr(resultado, "es_objeto_oracle", False)
            and getattr(resultado, "es_reservable", False)
        )

    def _ruta_oracle_reservable(self, ruta):
        """
        V1.2: True SOLO si la ruta resuelve a un objeto Oracle
        reservable según el resolvedor inyectado del protector.

        A diferencia de _ruta_requiere_analisis_copia, un resultado
        no verificable devuelve False: esas rutas ya bloquean por
        sí mismas dentro de la protección y no reciben lectura de
        contenido.
        """

        resolvedor = getattr(
            self.protector_reservas, "resolvedor_oracle", None
        )

        if resolvedor is None or not callable(
            getattr(resolvedor, "resolver", None)
        ):
            return False

        try:
            resultado = resolvedor.resolver(ruta)
        except Exception:
            return False

        if resultado is None:
            return False

        return bool(
            getattr(resultado, "es_ruta_valida", False)
            and getattr(resultado, "es_objeto_oracle", False)
            and getattr(resultado, "es_reservable", False)
        )

    def _obtener_contenido_working_tree(self, ruta_raiz, rutas):
        """
        V1.2 (REV1 R4): lee los bytes EXACTOS del working tree de
        las rutas Oracle reservables y las incluye EXPLÍCITAMENTE
        en el mapeo. Preparar y Actualizar preparados validan el
        contenido que realmente se va a stagear.

        - ruta sin archivo: None explícito (eliminación/lado
          origen demostrado → NO_APLICA en el protector);
        - fallo de lectura: BLOQUEA (fail-closed).

        Devuelve (exitoso, contenido_por_ruta, error). Sin
        protector devuelve (True, None, "").
        """

        if self.protector_reservas is None:
            return (True, None, "")

        contenido = {}

        for ruta in rutas:
            if not self._ruta_oracle_reservable(ruta):
                continue

            archivo = Path(ruta_raiz) / ruta

            if not archivo.exists():
                contenido[ruta] = None
                continue

            try:
                contenido[ruta] = archivo.read_bytes()
            except OSError:
                return (
                    False,
                    None,
                    (
                        "Modo Equipo Oracle: no fue posible leer "
                        f"el contenido de '{ruta}' para verificar "
                        "el objeto declarado; la operación queda "
                        "bloqueada."
                    ),
                )

        return (True, contenido, "")

    def _obtener_contenido_staged(self, ruta_repositorio, entradas):
        """
        V1.2 (REV1 R3+R4, REV2 R/C): lee los bytes EXACTOS de los
        blobs preparados en el índice para las rutas Oracle
        reservables del staged set y captura los OIDs para
        revalidación.

        El commit valida lo YA preparado, nunca el working tree.
        Consultas 100% de SOLO LECTURA (ls-files --stage para el
        OID del índice; cat-file blob para el contenido).

        Mapa por lado:

        - A/M/T Oracle -> bytes exactos staged + OID;
        - D Oracle -> None explícito (NO_APLICA);
        - R/C destino Oracle -> bytes exactos staged + OID del
          DESTINO (validación SQL ↔ identidad del destino);
        - R/C origen Oracle -> None explícito (NO_APLICA de
          contenido; su reserva SIGUE siendo obligatoria y la
          exige el protector por la ruta involucrada); nunca se
          lee el working tree para suplir el origen y nunca entra
          en oids_por_ruta.

        Si una entrada propia del origen aporta contenido real
        (p. ej. el origen de una copia fue también modificado),
        ese contenido gana sobre el None estructural.

        Si el OID o el blob no pueden determinarse con certeza
        BLOQUEA.

        Devuelve (exitoso, contenido_por_ruta, oids_por_ruta,
        error). Sin protector devuelve (True, None, None, "").
        """

        if self.protector_reservas is None:
            return (True, None, None, "")

        contenido = {}
        oids = {}

        for estado, ruta, ruta_anterior in entradas:
            # REV2: lado origen de renombrado/copiado explícito.
            if (
                estado in ("R", "C")
                and ruta_anterior
                and ruta_anterior not in contenido
                and self._ruta_oracle_reservable(ruta_anterior)
            ):
                contenido[ruta_anterior] = None

            if not self._ruta_oracle_reservable(ruta):
                continue

            if estado == "D":
                contenido[ruta] = None
                continue

            exitoso_oid, oid, error_oid = self._leer_oid_staged(
                ruta_repositorio,
                ruta
            )

            if not exitoso_oid:
                return (False, None, None, error_oid)

            exitoso_blob, datos, error_blob = self._leer_blob_staged(
                ruta_repositorio,
                oid,
                ruta
            )

            if not exitoso_blob:
                return (False, None, None, error_blob)

            contenido[ruta] = datos
            oids[ruta] = oid

        return (True, contenido, oids, "")

    def _leer_oid_staged(self, ruta_repositorio, ruta):
        """
        Lee el OID del blob de la ruta en el índice (etapa 0) con
        `git ls-files --stage -z` (SOLO LECTURA).

        Devuelve (exitoso, oid, error). Un registro malformado, un
        conflicto no resuelto o la ausencia de la ruta BLOQUEAN.
        """

        resultado = self._ejecutar_git_interno(
            argumentos=[
                "--literal-pathspecs",
                "ls-files",
                "--stage",
                "-z",
                "--",
                ruta,
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return (
                False,
                None,
                (
                    "Modo Equipo Oracle: no fue posible consultar "
                    f"el área preparada de '{ruta}'; la operación "
                    "queda bloqueada."
                ),
            )

        oid = None

        for entrada in resultado.salida.split("\0"):
            if not entrada:
                continue

            meta, separador, ruta_entrada = entrada.partition("\t")

            if not separador:
                return (
                    False,
                    None,
                    (
                        "Modo Equipo Oracle: salida de ls-files "
                        "malformada; la operación queda "
                        "bloqueada."
                    ),
                )

            partes = meta.split()

            if len(partes) != 3:
                return (
                    False,
                    None,
                    (
                        "Modo Equipo Oracle: salida de ls-files "
                        "malformada; la operación queda "
                        "bloqueada."
                    ),
                )

            _modo, oid_entrada, etapa = partes

            if ruta_entrada != ruta:
                continue

            if etapa != "0":
                return (
                    False,
                    None,
                    (
                        f"La ruta '{ruta}' presenta etapas de "
                        "conflicto en el índice; resuélvalas "
                        "antes de continuar."
                    ),
                )

            oid = oid_entrada.lower()

        if oid is None:
            return (
                False,
                None,
                (
                    "Modo Equipo Oracle: no se encontró la "
                    f"versión preparada de '{ruta}' en el "
                    "índice; la operación queda bloqueada."
                ),
            )

        if (
            len(oid) not in (40, 64)
            or any(caracter not in "0123456789abcdef" for caracter in oid)
        ):
            return (
                False,
                None,
                (
                    "Modo Equipo Oracle: identificador de blob "
                    "no reconocido; la operación queda "
                    "bloqueada."
                ),
            )

        return (True, oid, "")

    def _leer_blob_staged(self, ruta_repositorio, oid, ruta):
        """
        Lee el contenido EXACTO (bytes) de un blob preparado con
        `git cat-file blob <oid>` (SOLO LECTURA).

        Devuelve (exitoso, bytes, error).
        """

        exitoso, datos, error = self._ejecutar_git_bytes(
            argumentos=["cat-file", "blob", oid],
            ruta_repositorio=ruta_repositorio
        )

        if not exitoso or datos is None:
            return (
                False,
                None,
                (
                    "Modo Equipo Oracle: no fue posible leer el "
                    f"contenido preparado de '{ruta}' para "
                    "verificar el objeto declarado; la operación "
                    "queda bloqueada."
                ),
            )

        return (True, datos, "")

    def _ejecutar_git_bytes(
        self,
        argumentos,
        ruta_repositorio=None,
        tiempo_maximo=30
    ):
        """
        Ejecutor Git de SOLO LECTURA con salida binaria exacta.

        Uso exclusivo V1.2: leer el contenido exacto de un blob
        del índice (git cat-file blob <oid>) para la validación
        SQL ↔ archivo, sin la decodificación con reemplazo del
        ejecutor textual. El llamador solo pasa formas auditadas
        de lectura; nunca ejecuta escrituras.
        """

        if not self.git_disponible():
            return (False, None, "Git no fue encontrado en el sistema.")

        comando = [self.ruta_git] + argumentos

        carpeta_trabajo = None

        if ruta_repositorio is not None:
            carpeta_trabajo = Path(ruta_repositorio)

            if not carpeta_trabajo.exists():
                return (
                    False,
                    None,
                    "La carpeta indicada no existe."
                )

            if not carpeta_trabajo.is_dir():
                return (
                    False,
                    None,
                    "La ruta indicada no corresponde a una carpeta."
                )

        try:
            resultado = subprocess.run(
                comando,
                cwd=carpeta_trabajo,
                capture_output=True,
                text=False,
                timeout=tiempo_maximo,
                shell=False
            )

            if resultado.returncode != 0:
                error = resultado.stderr.decode(
                    "utf-8", errors="replace"
                ).rstrip("\r\n")

                return (False, None, error)

            return (True, resultado.stdout, "")

        except subprocess.TimeoutExpired:
            return (
                False,
                None,
                (
                    f"El comando superó el tiempo máximo "
                    f"de {tiempo_maximo} segundos."
                ),
            )

        except FileNotFoundError:
            return (
                False,
                None,
                "No fue posible encontrar git.exe."
            )

        except PermissionError:
            return (
                False,
                None,
                "No fue posible ejecutar Git (permiso denegado)."
            )

        except OSError:
            return (
                False,
                None,
                "Error inesperado del sistema al ejecutar Git."
            )

    def _leer_staged_set(self, ruta_repositorio):
        """
        Lee el conjunto preparado con una consulta Git de SOLO
        LECTURA que preserva renames/copias sin ambigüedad y
        habilita deliberadamente la detección de copies
        (REV1 FIX 2):

            git diff --cached --name-status -z -C --find-copies-harder

        Devuelve (exitoso, entradas, error) donde cada entrada es
        una tupla (estado, ruta, ruta_anterior).

        Con -z las rutas van separadas por NUL: nunca se parsea la
        salida humana con espacios o comillas. Un estado
        desconocido o un registro malformado produce un fallo
        controlado (la protección BLOQUEA). Esta inspección no
        modifica el índice.
        """

        resultado = self.ejecutar_git(
            argumentos=[
                "diff",
                "--cached",
                "--name-status",
                "-z",
                "-C",
                "--find-copies-harder"
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return (
                False,
                [],
                (
                    resultado.error
                    or "La consulta del área preparada falló."
                )
            )

        tokens = resultado.salida.split("\0")
        entradas = []
        indice = 0

        while indice < len(tokens):
            estado = tokens[indice]

            if not estado:
                indice += 1
                continue

            letra = estado[0]

            if letra in ("A", "M", "D", "T"):
                if (
                    indice + 1 >= len(tokens)
                    or not tokens[indice + 1]
                ):
                    return (
                        False,
                        [],
                        (
                            "Git devolvió un registro preparado "
                            "malformado."
                        )
                    )

                entradas.append((letra, tokens[indice + 1], ""))
                indice += 2
                continue

            if letra in ("R", "C"):
                if (
                    indice + 2 >= len(tokens)
                    or not tokens[indice + 1]
                    or not tokens[indice + 2]
                ):
                    return (
                        False,
                        [],
                        (
                            "Git devolvió un renombrado/copiado "
                            "preparado sin sus dos rutas."
                        )
                    )

                # En git diff --name-status -z, los registros R/C
                # emiten PRIMERO la ruta ORIGEN (lado A/HEAD) y
                # DESPUÉS la ruta DESTINO (lado B/índice). La
                # entrada conserva (ruta=destino, ruta_anterior=
                # origen), la misma convención del modelo
                # CambioArchivo de obtener_cambios.
                entradas.append(
                    (letra, tokens[indice + 2], tokens[indice + 1])
                )
                indice += 3
                continue

            return (
                False,
                [],
                (
                    "Git devolvió un estado preparado no "
                    f"reconocido ('{estado}')."
                )
            )

        return (True, entradas, "")

    def _proteger_commit_con_relectura(self, ruta_repositorio):
        """
        Protege el commit con relectura conservadora del conjunto
        preparado (REV1 R3: también revalida OIDs):

            snapshot staged inicial (rutas + OIDs)
            -> obtener contenido + OIDs del índice
            -> validar contenido (V1.2 SQL ↔ archivo)
            -> validar reservas
            -> releer staged set + OIDs
            -> si difiere: BLOQUEAR y pedir reintento
            -> si coincide: permitir el commit histórico

        OIDs revalidados: aunque las tuplas de staged set sean
        idénticas (mismas rutas/estados), un OID diferente
        demuestra que el contenido validado ya NO es el
        contenido preparado -> BLOQUEAR.

        Devuelve None si el commit puede continuar o un
        ResultadoComando fallido y controlado. Nunca "arregla" el
        índice.
        """

        exitoso_lectura, entradas, error_lectura = (
            self._leer_staged_set(ruta_repositorio)
        )

        if not exitoso_lectura:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "No fue posible leer el conjunto preparado "
                    "para validar las reservas de Modo Equipo; "
                    "commit bloqueado.\n\n"
                    f"Detalle: {error_lectura}"
                ),
                comando=""
            )

        rutas_involucradas = []

        for _estado, ruta, ruta_anterior in entradas:
            if ruta not in rutas_involucradas:
                rutas_involucradas.append(ruta)

            if (
                ruta_anterior
                and ruta_anterior not in rutas_involucradas
            ):
                rutas_involucradas.append(ruta_anterior)

        # V1.2 (REV1 R3+R4): el commit valida el contenido EXACTO
        # ya preparado en el índice (blobs staged) y captura los
        # OIDs para revalidación posterior.
        (
            exitoso_contenido,
            contenido_por_ruta,
            oids_por_ruta,
            error_contenido,
        ) = self._obtener_contenido_staged(
            ruta_repositorio,
            entradas
        )

        if not exitoso_contenido:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=error_contenido,
                comando=""
            )

        resultado_proteccion = self._aplicar_proteccion_reservas(
            "commit",
            rutas_involucradas,
            contenido_por_ruta=contenido_por_ruta
        )

        if resultado_proteccion is not None:
            return resultado_proteccion

        # Relectura conservadora del staged set + OIDs (REV1 R3).
        exitoso_relectura, entradas_relectura, error_relectura = (
            self._leer_staged_set(ruta_repositorio)
        )

        if not exitoso_relectura:
            detalle = error_relectura
        else:
            # Comparar staged set de rutas/estados.
            if entradas_relectura != entradas:
                detalle = (
                    "El conjunto preparado cambió durante la "
                    "validación."
                )
            else:
                # Comparar OIDs de las rutas Oracle relevantes:
                # aunque el staged set sea idéntico, el blob
                # contenido en un OID diferente debe bloquear.
                exitoso_oids2, oids_relectura, error_oids2 = (
                    self._releer_oids_staged(
                        ruta_repositorio, oids_por_ruta
                    )
                )

                if not exitoso_oids2:
                    detalle = error_oids2
                elif oids_relectura != oids_por_ruta:
                    detalle = (
                        "El contenido preparado (blob OID) cambió "
                        "durante la validación a pesar de que el "
                        "conjunto de rutas preparadas es el mismo."
                    )
                else:
                    return None

        return ResultadoComando(
            exitoso=False,
            codigo_salida=-1,
            salida="",
            error=(
                "El conjunto preparado cambió durante la "
                "validación de reservas de Modo Equipo; commit "
                "bloqueado.\n\n"
                "No se creó ningún commit y el índice no fue "
                "modificado. Revise el área preparada e intente "
                "de nuevo.\n\n"
                f"Detalle: {detalle}"
            ),
            comando=""
        )

    def _releer_oids_staged(self, ruta_repositorio, oids_por_ruta):
        """
        V1.2 REV1 R3: relee los OIDs del índice para las rutas
        Oracle previamente validadas.

        Devuelve (exitoso, oids_relectura, error). Una ruta que
        desapareció del índice o cuyo OID no puede leerse se
        considera cambio (BLOQUEAR).
        """

        if oids_por_ruta is None:
            return (True, None, "")

        oids_relectura = {}

        for ruta, _oid_esperado in oids_por_ruta.items():
            exitoso_oid, oid, error_oid = self._leer_oid_staged(
                ruta_repositorio, ruta
            )

            if not exitoso_oid:
                return (
                    False,
                    None,
                    (
                        "No fue posible releer el identificador "
                        f"del contenido preparado de '{ruta}' "
                        "para confirmar la validez del commit; "
                        "operación bloqueada."
                    ),
                )

            oids_relectura[ruta] = oid

        return (True, oids_relectura, "")

    def obtener_hash_actual(self, ruta_repositorio):
        """
        Devuelve el identificador corto del commit actual.
        """

        return self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--short",
                "HEAD"
            ],
            ruta_repositorio=ruta_repositorio
        )

    def detectar_operacion_en_curso(self, ruta_repositorio):
        """
        Detecta operaciones Git que requieren intervención
        especial antes de permitir un commit normal.

        Devuelve una cadena vacía si no existe ninguna.
        """

        comprobaciones = [
            (
                "MERGE_HEAD",
                "Hay una operación merge en curso."
            ),
            (
                "CHERRY_PICK_HEAD",
                "Hay una operación cherry-pick en curso."
            ),
            (
                "REVERT_HEAD",
                "Hay una operación revert en curso."
            ),
            (
                "rebase-merge",
                "Hay una operación rebase en curso."
            ),
            (
                "rebase-apply",
                "Hay una operación rebase en curso."
            ),
            (
                "sequencer",
                "Hay una secuencia de operaciones Git en curso."
            ),
        ]

        for nombre_git, mensaje in comprobaciones:
            ruta = self._obtener_ruta_git_interna(
                ruta_repositorio,
                nombre_git
            )

            if ruta is not None and ruta.exists():
                return (
                    f"{mensaje}\n\n"
                    "La aplicación no realizará un commit "
                    "normal hasta que esa operación termine."
                )

        return ""

    def _validar_identidad_git(self, ruta_repositorio):
        """
        Comprueba que Git tenga nombre y correo configurados.

        Devuelve una cadena vacía cuando todo está correcto.
        """

        resultado_nombre = self.ejecutar_git(
            argumentos=[
                "config",
                "--get",
                "user.name"
            ],
            ruta_repositorio=ruta_repositorio
        )

        if (
            not resultado_nombre.exitoso
            or not resultado_nombre.salida.strip()
        ):
            return (
                "Git no tiene configurado user.name.\n\n"
                "Debe configurar el nombre del autor "
                "antes de crear commits."
            )

        resultado_correo = self.ejecutar_git(
            argumentos=[
                "config",
                "--get",
                "user.email"
            ],
            ruta_repositorio=ruta_repositorio
        )

        if (
            not resultado_correo.exitoso
            or not resultado_correo.salida.strip()
        ):
            return (
                "Git no tiene configurado user.email.\n\n"
                "Debe configurar el correo del autor "
                "antes de crear commits."
            )

        return ""

    def _obtener_ruta_git_interna(
        self,
        ruta_repositorio,
        nombre
    ):
        """
        Obtiene una ruta interna del repositorio Git.

        Este método funciona también en repositorios
        que utilizan worktrees.
        """

        resultado = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--git-path",
                nombre
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return None

        ruta = Path(
            resultado.salida
        )

        if not ruta.is_absolute():
            ruta = (
                Path(ruta_repositorio)
                / ruta
            )

        return ruta

    @staticmethod
    def _validar_rutas_relativas(rutas_archivos):
        """
        Valida una colección de rutas recibidas desde la interfaz.

        Devuelve:
            rutas_validas
            mensaje_error
        """

        if rutas_archivos is None:
            return (
                None,
                "No se indicó ningún archivo."
            )

        rutas_validas = []

        for ruta_archivo in rutas_archivos:

            if ruta_archivo is None:
                return (
                    None,
                    "Se recibió una ruta de archivo inválida."
                )

            ruta_texto = str(
                ruta_archivo
            )

            if "\x00" in ruta_texto:
                return (
                    None,
                    "La ruta del archivo contiene un carácter inválido."
                )

            if not ruta_texto or ruta_texto.isspace():
                return (
                    None,
                    "Se recibió una ruta de archivo vacía."
                )

            ruta_objeto = Path(
                ruta_texto
            )

            if ruta_objeto.is_absolute():
                return (
                    None,
                    (
                        "Los archivos deben indicarse mediante "
                        "rutas relativas al repositorio."
                    )
                )

            if ".." in ruta_objeto.parts:
                return (
                    None,
                    (
                        "La ruta del archivo intenta salir "
                        "del repositorio."
                    )
                )

            if ruta_texto not in rutas_validas:
                rutas_validas.append(
                    ruta_texto
                )

        if not rutas_validas:
            return (
                None,
                "No se indicó ningún archivo."
            )

        return (
            rutas_validas,
            ""
        )

    @staticmethod
    def _traducir_estado_archivo(
        estado_indice,
        estado_trabajo
    ):
        """
        Convierte los códigos utilizados por Git
        en una descripción comprensible.
        """

        codigo = estado_indice + estado_trabajo

        if codigo == "??":
            return "Nuevo"

        if codigo == "!!":
            return "Ignorado"

        codigos_conflicto = ServicioGit._es_estado_conflicto(
            estado_indice,
            estado_trabajo
        )

        if codigos_conflicto:
            return "Conflicto"

        if "R" in codigo:
            return "Renombrado"

        if "C" in codigo:
            return "Copiado"

        if estado_indice == "A":
            if estado_trabajo == "M":
                return "Agregado y modificado después"

            if estado_trabajo == "D":
                return "Agregado y eliminado después"

            return "Agregado y preparado"

        if estado_indice == "D":
            return "Eliminado y preparado"

        if estado_trabajo == "D":
            return "Eliminado"

        if (
            estado_indice == "M"
            and estado_trabajo == "M"
        ):
            return "Modificado, preparado y vuelto a modificar"

        if estado_indice == "M":
            return "Modificado y preparado"

        if estado_trabajo == "M":
            return "Modificado"

        if estado_indice == "T":
            return "Tipo de archivo modificado y preparado"

        if estado_trabajo == "T":
            return "Tipo de archivo modificado"

        return "Cambio detectado"

    @staticmethod
    def _es_estado_conflicto(estado_indice, estado_trabajo):
        """
        Determina si el par de códigos de git status
        corresponde a un conflicto de merge.
        """

        return (estado_indice + estado_trabajo) in {
            "DD",
            "AU",
            "UD",
            "UA",
            "DU",
            "AA",
            "UU",
        }

    @staticmethod
    def _convertir_comando_a_texto(comando):
        """
        Convierte la lista del comando en texto únicamente
        para mostrarla o registrarla.
        """

        return " ".join(
            str(parte)
            for parte in comando
        )