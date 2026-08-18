from datetime import date, datetime, timezone

from modelos import ResultadoComando
from modelos_historial import CommitGit, ResultadoHistorial
from servicio_git import ServicioGit


class ServicioHistorialGit:
    """
    Servicio de solo lectura para consultar el historial de commits.

    Recibe un ServicioGit existente para reutilizar todas las
    validaciones y la ejecución segura de comandos Git.
    """

    SEPARADOR_CAMPO = "\x1f"
    SEPARADOR_REGISTRO = "\x1e"

    def __init__(self, servicio_git=None):
        self.servicio_git = (
            servicio_git
            if servicio_git is not None
            else ServicioGit()
        )

    def obtener_historial_commits(
        self,
        ruta_repositorio,
        limite=100,
        filtro_archivo="",
        fecha_desde="",
        fecha_hasta=""
    ):
        """
        Obtiene commits del repositorio local aplicando filtros opcionales.

        `filtro_archivo` busca una parte del nombre o ruta del archivo
        sin distinguir mayúsculas de minúsculas.

        `fecha_desde` y `fecha_hasta` utilizan el formato YYYY-MM-DD.
        Las fechas son inclusivas.

        Esta operación es de solo lectura y no consulta el remoto.
        """

        resultado_limite = self._validar_limite(
            limite
        )

        if not resultado_limite.exitoso:
            return resultado_limite

        resultado_filtros = self._validar_filtros(
            filtro_archivo,
            fecha_desde,
            fecha_hasta
        )

        if not resultado_filtros.exitoso:
            return resultado_filtros

        filtro_archivo = filtro_archivo.strip()
        fecha_desde = fecha_desde.strip()
        fecha_hasta = fecha_hasta.strip()

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return ResultadoHistorial(
                exitoso=False,
                error=(
                    estado.mensaje
                    if estado.mensaje
                    else "La carpeta indicada no es un repositorio Git."
                )
            )

        if not estado.tiene_commits:
            return ResultadoHistorial(
                exitoso=True,
                commits=[],
                mensaje="El repositorio todavía no tiene commits."
            )

        formato = (
            "%H%x1f"
            "%h%x1f"
            "%cI%x1f"
            "%an%x1f"
            "%ae%x1f"
            "%s%x1e"
        )

        argumentos = [
            "log",
            f"-{limite}",
            "--no-decorate",
            f"--format={formato}"
        ]

        if fecha_desde:
            argumentos.append(
                f"--since={fecha_desde} 00:00:00"
            )

        if fecha_hasta:
            argumentos.append(
                f"--until={fecha_hasta} 23:59:59"
            )

        if filtro_archivo:
            argumentos.extend(
                [
                    "--",
                    self._crear_pathspec_archivo(
                        filtro_archivo
                    )
                ]
            )

        resultado = self.servicio_git.ejecutar_git(
            argumentos,
            ruta_repositorio
        )

        if not resultado.exitoso:
            return ResultadoHistorial(
                exitoso=False,
                error=(
                    resultado.error
                    if resultado.error
                    else resultado.salida
                )
            )

        resultado_historial = self._interpretar_salida_historial(
            resultado.salida
        )

        # `git log` respeta la estructura del grafo de commits y, en
        # historiales con ramas o fechas modificadas, eso no garantiza
        # un orden estrictamente cronológico. Para una tabla de lectura
        # resulta más claro ordenar explícitamente por fecha de commit.
        if resultado_historial.exitoso:
            resultado_historial.commits.sort(
                key=self._clave_orden_fecha,
                reverse=True
            )

        if (
            resultado_historial.exitoso
            and not resultado_historial.commits
            and (
                filtro_archivo
                or fecha_desde
                or fecha_hasta
            )
        ):
            resultado_historial.mensaje = (
                "No se encontraron commits que cumplan los filtros."
            )

        return resultado_historial

    def obtener_cambios_commit(
        self,
        ruta_repositorio,
        hash_commit
    ):
        """
        Obtiene el parche de un commit mediante git show.

        Esta operación es de solo lectura: no modifica el working
        tree, no accede al remoto y no ejecuta Fetch.

        Se evitan los diff externos y los convertidores de texto
        configurados en Git (--no-ext-diff y --no-textconv).

        Devuelve un ResultadoComando. Si el commit no genera parche,
        el resultado es exitoso con salida vacía.
        """

        resultado_hash = self._validar_hash_commit(
            hash_commit
        )

        if not resultado_hash.exitoso:
            return resultado_hash

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    estado.mensaje
                    if estado.mensaje
                    else "La carpeta indicada no es un repositorio Git."
                ),
                comando=""
            )

        # Verifica que el hash corresponda realmente a un commit
        # del repositorio antes de pedir el parche.
        verificacion = self.servicio_git.ejecutar_git(
            [
                "rev-parse",
                "--verify",
                "--quiet",
                f"{hash_commit}^{{commit}}"
            ],
            ruta_repositorio
        )

        if not verificacion.exitoso:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "El hash indicado no corresponde a un commit "
                    "de este repositorio."
                ),
                comando=""
            )

        return self.servicio_git.ejecutar_git(
            [
                "show",
                "--format=",
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--unified=3",
                hash_commit,
                "--"
            ],
            ruta_repositorio
        )

    def _validar_hash_commit(self, hash_commit):
        """
        Valida que el hash sea una revisión Git completa y segura.

        Solamente se aceptan hashes hexadecimales completos de
        40 o 64 caracteres. No se acepta ningún otro texto como
        revisión Git.
        """

        if not isinstance(hash_commit, str):
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="El hash del commit debe ser texto.",
                comando=""
            )

        if not hash_commit:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="El hash del commit no puede estar vacío.",
                comando=""
            )

        if "\x00" in hash_commit:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "El hash del commit contiene caracteres "
                    "no permitidos."
                ),
                comando=""
            )

        if len(hash_commit) not in (40, 64):
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "El hash del commit debe tener 40 o 64 "
                    "caracteres hexadecimales."
                ),
                comando=""
            )

        if not all(
            caracter in "0123456789abcdefABCDEF"
            for caracter in hash_commit
        ):
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "El hash del commit debe contener solamente "
                    "caracteres hexadecimales."
                ),
                comando=""
            )

        return ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando=""
        )

    def _validar_limite(self, limite):
        """
        Valida el número máximo de commits a consultar.
        """

        if isinstance(limite, bool) or not isinstance(limite, int):
            return ResultadoHistorial(
                exitoso=False,
                error="El límite del historial debe ser un número entero."
            )

        if limite < 1:
            return ResultadoHistorial(
                exitoso=False,
                error="El límite del historial debe ser mayor que cero."
            )

        if limite > 500:
            return ResultadoHistorial(
                exitoso=False,
                error=(
                    "El límite máximo permitido para el historial "
                    "es de 500 commits."
                )
            )

        return ResultadoHistorial(
            exitoso=True
        )

    def _validar_filtros(
        self,
        filtro_archivo,
        fecha_desde,
        fecha_hasta
    ):
        """
        Valida los filtros antes de construir el comando Git.
        """

        for nombre, valor in (
            ("filtro de archivo", filtro_archivo),
            ("fecha desde", fecha_desde),
            ("fecha hasta", fecha_hasta)
        ):
            if not isinstance(valor, str):
                return ResultadoHistorial(
                    exitoso=False,
                    error=f"El valor de {nombre} debe ser texto."
                )

            if "\x00" in valor:
                return ResultadoHistorial(
                    exitoso=False,
                    error=f"El valor de {nombre} contiene un carácter no permitido."
                )

        filtro_archivo = filtro_archivo.strip()

        if "\r" in filtro_archivo or "\n" in filtro_archivo:
            return ResultadoHistorial(
                exitoso=False,
                error=(
                    "El filtro de archivo debe escribirse en una sola línea."
                )
            )

        resultado_desde = self._convertir_fecha_iso(
            fecha_desde,
            "desde"
        )

        if isinstance(resultado_desde, ResultadoHistorial):
            return resultado_desde

        resultado_hasta = self._convertir_fecha_iso(
            fecha_hasta,
            "hasta"
        )

        if isinstance(resultado_hasta, ResultadoHistorial):
            return resultado_hasta

        if (
            resultado_desde is not None
            and resultado_hasta is not None
            and resultado_desde > resultado_hasta
        ):
            return ResultadoHistorial(
                exitoso=False,
                error=(
                    "La fecha Desde no puede ser posterior a la fecha Hasta."
                )
            )

        return ResultadoHistorial(
            exitoso=True
        )

    @staticmethod
    def _convertir_fecha_iso(valor, nombre):
        """
        Convierte una fecha YYYY-MM-DD en date para validarla.
        """

        valor = valor.strip()

        if not valor:
            return None

        try:
            return date.fromisoformat(
                valor
            )
        except ValueError:
            return ResultadoHistorial(
                exitoso=False,
                error=(
                    f"La fecha {nombre} no es válida. "
                    "Utilice el formato YYYY-MM-DD."
                )
            )

    @staticmethod
    def _clave_orden_fecha(commit):
        """
        Devuelve una fecha comparable para ordenar los commits.

        Git entrega `%cI` en formato ISO 8601 con zona horaria.
        Si apareciera un valor inesperado, el commit se coloca al final
        sin impedir que el historial pueda mostrarse.
        """

        try:
            return datetime.fromisoformat(
                commit.fecha_iso
            )
        except (TypeError, ValueError):
            return datetime.min.replace(
                tzinfo=timezone.utc
            )

    @staticmethod
    def _crear_pathspec_archivo(filtro_archivo):
        """
        Crea un pathspec Git que busca el texto dentro del nombre o ruta.

        Los caracteres especiales de glob se escapan para que el usuario
        escriba texto literal y no una expresión de patrones Git.
        """

        texto = filtro_archivo.strip()

        texto = texto.replace(
            "\\",
            "\\\\"
        )

        for caracter in (
            "*",
            "?",
            "[",
            "]"
        ):
            texto = texto.replace(
                caracter,
                f"\\{caracter}"
            )

        return (
            f":(glob,icase)**/*{texto}*"
        )

    def _interpretar_salida_historial(self, salida):
        """
        Convierte la salida estructurada de git log en CommitGit.
        """

        if not salida:
            return ResultadoHistorial(
                exitoso=True,
                commits=[],
                mensaje="No se encontraron commits."
            )

        commits = []

        registros = salida.split(
            self.SEPARADOR_REGISTRO
        )

        for registro in registros:
            # Git agrega saltos de línea entre algunos registros.
            # Solamente retiramos CR/LF del comienzo y final para
            # no alterar el contenido real de los campos.
            registro = registro.strip("\r\n")

            if not registro:
                continue

            campos = registro.split(
                self.SEPARADOR_CAMPO,
                5
            )

            if len(campos) != 6:
                return ResultadoHistorial(
                    exitoso=False,
                    error=(
                        "Git devolvió un formato de historial inesperado. "
                        "No se modificó el repositorio."
                    )
                )

            commits.append(
                CommitGit(
                    hash_completo=campos[0],
                    hash_corto=campos[1],
                    fecha_iso=campos[2],
                    autor=campos[3],
                    correo=campos[4],
                    mensaje=campos[5]
                )
            )

        return ResultadoHistorial(
            exitoso=True,
            commits=commits,
            mensaje=(
                f"Se cargaron {len(commits)} commit(s)."
            )
        )
