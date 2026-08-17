from modelos import EstadoSincronizacion, ResultadoComando
from servicio_git import ServicioGit


class ServicioRemotoGit(ServicioGit):
    """
    Amplía ServicioGit con operaciones relacionadas con remotos.

    En esta etapa solamente permitimos consultar el remoto mediante
    Fetch y calcular el estado de sincronización.

    Todavía NO implementamos Push ni Pull.
    """

    def obtener_remoto_sincronizacion(self, ruta_repositorio):
        """
        Determina qué remoto corresponde utilizar.

        Reglas:

        1. Si la rama ya tiene upstream, usamos su remoto.
        2. Si no tiene upstream y existe un solo remoto, usamos ese.
        3. Si existen varios remotos sin upstream, no elegimos
           uno automáticamente.
        """

        estado = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=estado.mensaje,
                comando=""
            )

        if not estado.rama_actual:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    "No se puede determinar el remoto porque HEAD "
                    "no está asociado a una rama."
                ),
                comando=""
            )

        # Consultamos el remoto asociado al upstream de la rama.
        #
        # Si la rama todavía no tiene upstream, Git devolverá
        # una cadena vacía.
        resultado_remoto_upstream = self.ejecutar_git(
            argumentos=[
                "for-each-ref",
                "--format=%(upstream:remotename)",
                f"refs/heads/{estado.rama_actual}"
            ],
            ruta_repositorio=estado.ruta_raiz
        )

        if resultado_remoto_upstream.exitoso:
            remoto_upstream = (
                resultado_remoto_upstream.salida.strip()
            )

            # Git utiliza "." para representar el propio
            # repositorio local como upstream.
            if remoto_upstream == ".":
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        "La rama utiliza el repositorio local como upstream. "
                        "Esa configuración no se utilizará para operaciones "
                        "de red."
                    ),
                    comando=""
                )

            if remoto_upstream:

                if remoto_upstream in estado.remotos:
                    return ResultadoComando(
                        exitoso=True,
                        codigo_salida=0,
                        salida=remoto_upstream,
                        error="",
                        comando=""
                    )

                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        f"La rama indica un remoto upstream llamado "
                        f"'{remoto_upstream}', pero ese remoto ya no existe."
                    ),
                    comando=""
                )

        # Si todavía no hay upstream pero solamente existe
        # un remoto, podemos seleccionarlo de forma inequívoca.
        if len(estado.remotos) == 1:
            return ResultadoComando(
                exitoso=True,
                codigo_salida=0,
                salida=estado.remotos[0],
                error="",
                comando=""
            )

        if len(estado.remotos) == 0:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="El repositorio no tiene ningún remoto configurado.",
                comando=""
            )

        # No queremos adivinar cuando existen varios remotos.
        return ResultadoComando(
            exitoso=False,
            codigo_salida=-1,
            salida="",
            error=(
                "La rama no tiene upstream y existen varios remotos. "
                "La aplicación no elegirá uno automáticamente."
            ),
            comando=""
        )

    def ejecutar_fetch(
        self,
        ruta_repositorio,
        remoto
    ):
        """
        Ejecuta git fetch --prune sobre un remoto existente.

        Fetch actualiza las referencias remotas locales.

        No modifica los archivos del área de trabajo.
        No crea commits.
        No hace Push.
        """

        estado = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=estado.mensaje,
                comando=""
            )

        if remoto is None or not str(remoto).strip():
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="No se indicó el remoto que debe consultarse.",
                comando=""
            )

        nombre_remoto = str(
            remoto
        ).strip()

        if nombre_remoto not in estado.remotos:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    f"El remoto '{nombre_remoto}' no existe "
                    "en este repositorio."
                ),
                comando=""
            )

        # Las operaciones remotas tienen un tiempo máximo
        # superior al utilizado para operaciones locales.
        return self.ejecutar_git(
            argumentos=[
                "fetch",
                "--prune",
                nombre_remoto
            ],
            ruta_repositorio=estado.ruta_raiz,
            tiempo_maximo=180
        )

    def obtener_estado_sincronizacion(
        self,
        ruta_repositorio
    ):
        """
        Calcula commits por subir y commits por bajar.

        IMPORTANTE:

        Este método NO se conecta a Internet.

        Utiliza las referencias remotas disponibles localmente.
        Para disponer de información actualizada debe ejecutarse
        Fetch antes.
        """

        estado = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return EstadoSincronizacion(
                exitoso=False,
                error=estado.mensaje
            )

        if not estado.rama_actual:
            return EstadoSincronizacion(
                exitoso=False,
                error=(
                    "No se puede calcular la sincronización porque HEAD "
                    "no está asociado a una rama."
                )
            )

        resultado_remoto = self.obtener_remoto_sincronizacion(
            estado.ruta_raiz
        )

        if not resultado_remoto.exitoso:
            return EstadoSincronizacion(
                exitoso=False,
                rama_local=estado.rama_actual,
                error=resultado_remoto.error
            )

        remoto = resultado_remoto.salida

        # Intentamos obtener el upstream configurado.
        resultado_upstream = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{upstream}"
            ],
            ruta_repositorio=estado.ruta_raiz
        )

        upstream_configurado = (
            resultado_upstream.exitoso
            and bool(
                resultado_upstream.salida.strip()
            )
        )

        if upstream_configurado:
            return self._calcular_con_upstream(
                ruta_repositorio=estado.ruta_raiz,
                rama_local=estado.rama_actual,
                remoto=remoto,
                rama_remota=resultado_upstream.salida.strip()
            )

        return self._calcular_sin_upstream(
            ruta_repositorio=estado.ruta_raiz,
            rama_local=estado.rama_actual,
            remoto=remoto,
            tiene_commits=estado.tiene_commits
        )

    def _calcular_con_upstream(
        self,
        ruta_repositorio,
        rama_local,
        remoto,
        rama_remota
    ):
        """
        Calcula el estado cuando la rama ya tiene upstream.
        """

        resultado_verificacion = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--verify",
                "@{upstream}^{commit}"
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado_verificacion.exitoso:
            return EstadoSincronizacion(
                exitoso=False,
                rama_local=rama_local,
                remoto=remoto,
                rama_remota=rama_remota,
                upstream_configurado=True,
                error=(
                    "La rama tiene upstream configurado, pero la referencia "
                    "remota no está disponible localmente. Ejecute Fetch."
                )
            )

        # HEAD...@{upstream}
        #
        # Con --left-right --count:
        #
        # primera cifra  = commits solamente locales
        # segunda cifra  = commits solamente remotos
        resultado_conteo = self.ejecutar_git(
            argumentos=[
                "rev-list",
                "--left-right",
                "--count",
                "HEAD...@{upstream}"
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado_conteo.exitoso:
            return EstadoSincronizacion(
                exitoso=False,
                rama_local=rama_local,
                remoto=remoto,
                rama_remota=rama_remota,
                upstream_configurado=True,
                error=(
                    resultado_conteo.error
                    or "No fue posible comparar la rama con su upstream."
                )
            )

        commits_por_subir, commits_por_bajar = (
            self._interpretar_conteo_sincronizacion(
                resultado_conteo.salida
            )
        )

        if commits_por_subir is None:
            return EstadoSincronizacion(
                exitoso=False,
                rama_local=rama_local,
                remoto=remoto,
                rama_remota=rama_remota,
                upstream_configurado=True,
                error=(
                    "Git devolvió un conteo de sincronización "
                    "con formato inesperado."
                )
            )

        divergente = (
            commits_por_subir > 0
            and commits_por_bajar > 0
        )

        mensaje = self._crear_mensaje_sincronizacion(
            upstream_configurado=True,
            rama_remota_existe=True,
            commits_por_subir=commits_por_subir,
            commits_por_bajar=commits_por_bajar
        )

        return EstadoSincronizacion(
            exitoso=True,
            rama_local=rama_local,
            remoto=remoto,
            rama_remota=rama_remota,
            upstream_configurado=True,
            rama_remota_existe=True,
            commits_por_subir=commits_por_subir,
            commits_por_bajar=commits_por_bajar,
            divergente=divergente,
            mensaje=mensaje
        )

    def _calcular_sin_upstream(
        self,
        ruta_repositorio,
        rama_local,
        remoto,
        tiene_commits
    ):
        """
        Calcula el estado cuando todavía no existe upstream.
        """

        # Mientras no exista upstream, utilizamos como candidato
        # la rama del mismo nombre en el único remoto disponible.
        rama_remota = (
            f"{remoto}/{rama_local}"
        )

        referencia_remota = (
            f"refs/remotes/{remoto}/{rama_local}"
        )

        resultado_existe = self.ejecutar_git(
            argumentos=[
                "show-ref",
                "--verify",
                "--quiet",
                referencia_remota
            ],
            ruta_repositorio=ruta_repositorio
        )

        rama_remota_existe = (
            resultado_existe.exitoso
        )

        if rama_remota_existe:

            resultado_conteo = self.ejecutar_git(
                argumentos=[
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"HEAD...{referencia_remota}"
                ],
                ruta_repositorio=ruta_repositorio
            )

            if not resultado_conteo.exitoso:
                return EstadoSincronizacion(
                    exitoso=False,
                    rama_local=rama_local,
                    remoto=remoto,
                    rama_remota=rama_remota,
                    rama_remota_existe=True,
                    error=(
                        resultado_conteo.error
                        or (
                            "No fue posible comparar las ramas "
                            "local y remota."
                        )
                    )
                )

            commits_por_subir, commits_por_bajar = (
                self._interpretar_conteo_sincronizacion(
                    resultado_conteo.salida
                )
            )

            if commits_por_subir is None:
                return EstadoSincronizacion(
                    exitoso=False,
                    rama_local=rama_local,
                    remoto=remoto,
                    rama_remota=rama_remota,
                    rama_remota_existe=True,
                    error=(
                        "Git devolvió un conteo de sincronización "
                        "con formato inesperado."
                    )
                )

        else:
            # Si la rama remota todavía no existe,
            # todos los commits locales serían candidatos
            # para el primer Push.
            commits_por_bajar = 0

            if tiene_commits:

                resultado_conteo_local = self.ejecutar_git(
                    argumentos=[
                        "rev-list",
                        "--count",
                        "HEAD"
                    ],
                    ruta_repositorio=ruta_repositorio
                )

                if not resultado_conteo_local.exitoso:
                    return EstadoSincronizacion(
                        exitoso=False,
                        rama_local=rama_local,
                        remoto=remoto,
                        rama_remota=rama_remota,
                        error=(
                            resultado_conteo_local.error
                            or (
                                "No fue posible contar "
                                "los commits locales."
                            )
                        )
                    )

                try:
                    commits_por_subir = int(
                        resultado_conteo_local.salida.strip()
                    )

                except ValueError:
                    return EstadoSincronizacion(
                        exitoso=False,
                        rama_local=rama_local,
                        remoto=remoto,
                        rama_remota=rama_remota,
                        error=(
                            "Git devolvió un número de commits "
                            "locales inválido."
                        )
                    )

            else:
                commits_por_subir = 0

        divergente = (
            commits_por_subir > 0
            and commits_por_bajar > 0
        )

        mensaje = self._crear_mensaje_sincronizacion(
            upstream_configurado=False,
            rama_remota_existe=rama_remota_existe,
            commits_por_subir=commits_por_subir,
            commits_por_bajar=commits_por_bajar
        )

        return EstadoSincronizacion(
            exitoso=True,
            rama_local=rama_local,
            remoto=remoto,
            rama_remota=rama_remota,
            upstream_configurado=False,
            rama_remota_existe=rama_remota_existe,
            commits_por_subir=commits_por_subir,
            commits_por_bajar=commits_por_bajar,
            divergente=divergente,
            mensaje=mensaje
        )

    @staticmethod
    def _interpretar_conteo_sincronizacion(
        salida
    ):
        """
        Interpreta la salida de:

            git rev-list --left-right --count
        """

        partes = salida.split()

        if len(partes) != 2:
            return None, None

        try:
            commits_por_subir = int(
                partes[0]
            )

            commits_por_bajar = int(
                partes[1]
            )

            return (
                commits_por_subir,
                commits_por_bajar
            )

        except ValueError:
            return None, None

    @staticmethod
    def _crear_mensaje_sincronizacion(
        upstream_configurado,
        rama_remota_existe,
        commits_por_subir,
        commits_por_bajar
    ):
        """
        Genera una descripción sencilla del estado.
        """

        if not rama_remota_existe:
            return (
                "La rama remota aún no existe. "
                "El primer Push deberá crearla "
                "y establecer el upstream."
            )

        if (
            commits_por_subir == 0
            and commits_por_bajar == 0
        ):
            if upstream_configurado:
                return (
                    "La rama local está sincronizada con su upstream "
                    "según la última información obtenida."
                )

            return (
                "La rama local coincide con la rama remota, "
                "pero todavía no tiene upstream configurado."
            )

        if (
            commits_por_subir > 0
            and commits_por_bajar > 0
        ):
            return (
                "La rama local y la rama remota han divergido. "
                "No se debe hacer Push directo."
            )

        if commits_por_subir > 0:
            return (
                f"Hay {commits_por_subir} commit(s) local(es) "
                "por enviar al remoto."
            )

        return (
            f"Hay {commits_por_bajar} commit(s) remoto(s) "
            "por descargar."
        )