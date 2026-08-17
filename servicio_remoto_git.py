from modelos import EstadoSincronizacion, ResultadoComando
from servicio_git import ServicioGit


class ServicioRemotoGit(ServicioGit):
    """
    Amplía ServicioGit con operaciones relacionadas con remotos.

    Las operaciones de red utilizan tiempos máximos superiores
    a las operaciones locales.

    Nunca utilizamos Push forzado.
    El Pull solamente permite actualizaciones fast-forward.
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
            return self._crear_resultado_error(
                estado.mensaje
            )

        if not estado.rama_actual:
            return self._crear_resultado_error(
                (
                    "No se puede determinar el remoto porque HEAD "
                    "no está asociado a una rama."
                )
            )

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

            if remoto_upstream == ".":
                return self._crear_resultado_error(
                    (
                        "La rama utiliza el repositorio local como "
                        "upstream. Esa configuración no se utilizará "
                        "para operaciones de red."
                    )
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

                return self._crear_resultado_error(
                    (
                        f"La rama indica un remoto upstream llamado "
                        f"'{remoto_upstream}', pero ese remoto "
                        "ya no existe."
                    )
                )

        if len(estado.remotos) == 1:
            return ResultadoComando(
                exitoso=True,
                codigo_salida=0,
                salida=estado.remotos[0],
                error="",
                comando=""
            )

        if len(estado.remotos) == 0:
            return self._crear_resultado_error(
                "El repositorio no tiene ningún remoto configurado."
            )

        return self._crear_resultado_error(
            (
                "La rama no tiene upstream y existen varios remotos. "
                "La aplicación no elegirá uno automáticamente."
            )
        )

    def ejecutar_fetch(
        self,
        ruta_repositorio,
        remoto
    ):
        """
        Ejecuta Fetch sobre un remoto existente.

        Fetch no modifica los archivos del área de trabajo.
        """

        estado = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return self._crear_resultado_error(
                estado.mensaje
            )

        if remoto is None:
            return self._crear_resultado_error(
                "No se indicó el remoto que debe consultarse."
            )

        nombre_remoto = str(
            remoto
        ).strip()

        if not nombre_remoto:
            return self._crear_resultado_error(
                "No se indicó el remoto que debe consultarse."
            )

        if nombre_remoto.startswith("-"):
            return self._crear_resultado_error(
                "El nombre del remoto no es válido."
            )

        if nombre_remoto not in estado.remotos:
            return self._crear_resultado_error(
                (
                    f"El remoto '{nombre_remoto}' no existe "
                    "en este repositorio."
                )
            )

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

        Este método NO se conecta a Internet.

        Para disponer de información actualizada debe
        ejecutarse Fetch antes.
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
                    "No se puede calcular la sincronización porque "
                    "HEAD no está asociado a una rama."
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

    def ejecutar_push_seguro(
        self,
        ruta_repositorio
    ):
        """
        Ejecuta un Push conservador.

        Antes de enviar:

        1. Valida el repositorio.
        2. Comprueba que exista una rama actual.
        3. Comprueba que existan commits.
        4. Bloquea operaciones Git en curso.
        5. Bloquea index.lock.
        6. Exige un área de trabajo limpia.
        7. Ejecuta Fetch nuevamente.
        8. Calcula nuevamente la sincronización.
        9. Bloquea Push si existen commits por descargar.
        10. Bloquea ramas divergentes.

        Nunca utiliza --force.
        """

        estado = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return self._crear_resultado_error(
                estado.mensaje
            )

        if not estado.rama_actual:
            return self._crear_resultado_error(
                (
                    "No se puede realizar Push porque HEAD "
                    "no está asociado a una rama."
                )
            )

        if not estado.tiene_commits:
            return self._crear_resultado_error(
                (
                    "No se puede realizar Push porque "
                    "el repositorio todavía no tiene commits."
                )
            )

        operacion_en_curso = self.detectar_operacion_en_curso(
            estado.ruta_raiz
        )

        if operacion_en_curso:
            return self._crear_resultado_error(
                operacion_en_curso
            )

        ruta_bloqueo = self._obtener_ruta_git_interna(
            estado.ruta_raiz,
            "index.lock"
        )

        if (
            ruta_bloqueo is not None
            and ruta_bloqueo.exists()
        ):
            return self._crear_resultado_error(
                (
                    "No se puede realizar Push porque existe "
                    "un archivo index.lock.\n\n"
                    "Compruebe que no haya otro proceso Git "
                    "trabajando sobre el repositorio.\n\n"
                    "La aplicación no eliminará el bloqueo "
                    "automáticamente."
                )
            )

        resultado_cambios = self.obtener_cambios(
            estado.ruta_raiz
        )

        if not resultado_cambios.exitoso:
            return self._crear_resultado_error(
                resultado_cambios.error
            )

        archivos_conflicto = [
            cambio.ruta
            for cambio in resultado_cambios.cambios
            if cambio.descripcion == "Conflicto"
        ]

        if archivos_conflicto:
            lista_archivos = "\n".join(
                archivos_conflicto
            )

            return self._crear_resultado_error(
                (
                    "No se puede realizar Push porque existen "
                    "archivos con conflictos:\n\n"
                    f"{lista_archivos}"
                )
            )

        if resultado_cambios.cambios:
            return self._crear_resultado_error(
                (
                    "No se puede realizar Push porque existen "
                    "cambios sin commit en el repositorio.\n\n"
                    "Prepare y confirme esos cambios, o déjelos "
                    "fuera del área de trabajo antes de continuar."
                )
            )

        resultado_remoto = self.obtener_remoto_sincronizacion(
            estado.ruta_raiz
        )

        if not resultado_remoto.exitoso:
            return self._crear_resultado_error(
                resultado_remoto.error
            )

        remoto = resultado_remoto.salida

        resultado_fetch = self.ejecutar_fetch(
            estado.ruta_raiz,
            remoto
        )

        if not resultado_fetch.exitoso:
            detalle = (
                resultado_fetch.error
                if resultado_fetch.error
                else resultado_fetch.salida
            )

            return self._crear_resultado_error(
                (
                    "No se realizará Push porque el Fetch previo "
                    "no pudo completarse.\n\n"
                    f"{detalle}"
                )
            )

        estado_sincronizacion = (
            self.obtener_estado_sincronizacion(
                estado.ruta_raiz
            )
        )

        if not estado_sincronizacion.exitoso:
            return self._crear_resultado_error(
                estado_sincronizacion.error
            )

        if estado_sincronizacion.divergente:
            return self._crear_resultado_error(
                (
                    "No se realizará Push porque la rama local "
                    "y la rama remota han divergido.\n\n"
                    f"Commits locales por enviar: "
                    f"{estado_sincronizacion.commits_por_subir}\n"
                    f"Commits remotos por descargar: "
                    f"{estado_sincronizacion.commits_por_bajar}"
                )
            )

        if estado_sincronizacion.commits_por_bajar > 0:
            return self._crear_resultado_error(
                (
                    "No se realizará Push porque existen commits "
                    "remotos que primero deben descargarse.\n\n"
                    f"Commits por descargar: "
                    f"{estado_sincronizacion.commits_por_bajar}"
                )
            )

        if (
            estado_sincronizacion.commits_por_subir == 0
            and estado_sincronizacion.upstream_configurado
        ):
            return self._crear_resultado_error(
                "No hay commits locales pendientes de enviar."
            )

        rama_local = estado_sincronizacion.rama_local

        if not estado_sincronizacion.upstream_configurado:
            argumentos_push = [
                "push",
                "--porcelain",
                "--set-upstream",
                remoto,
                (
                    f"{rama_local}:"
                    f"refs/heads/{rama_local}"
                )
            ]

        else:
            rama_remota = (
                estado_sincronizacion.rama_remota
            )

            prefijo_remoto = (
                f"{remoto}/"
            )

            if not rama_remota.startswith(
                prefijo_remoto
            ):
                return self._crear_resultado_error(
                    (
                        "No fue posible determinar de forma segura "
                        "la rama remota de destino."
                    )
                )

            nombre_rama_remota = rama_remota[
                len(prefijo_remoto):
            ]

            if not nombre_rama_remota:
                return self._crear_resultado_error(
                    (
                        "No fue posible determinar la rama "
                        "remota de destino."
                    )
                )

            argumentos_push = [
                "push",
                "--porcelain",
                remoto,
                (
                    f"{rama_local}:"
                    f"refs/heads/{nombre_rama_remota}"
                )
            ]

        return self.ejecutar_git(
            argumentos=argumentos_push,
            ruta_repositorio=estado.ruta_raiz,
            tiempo_maximo=180
        )

    def ejecutar_pull_seguro(
        self,
        ruta_repositorio
    ):
        """
        Descarga cambios remotos mediante Pull fast-forward.

        Política conservadora:

        1. El repositorio debe ser válido.
        2. HEAD debe pertenecer a una rama.
        3. Debe existir al menos un commit.
        4. No puede existir otra operación Git en curso.
        5. No puede existir index.lock.
        6. El área de trabajo debe estar completamente limpia.
        7. Se ejecuta Fetch antes de decidir.
        8. La rama debe tener upstream configurado.
        9. No puede haber divergencia.
        10. No puede haber commits locales pendientes de Push.
        11. Deben existir commits remotos por descargar.
        12. El Pull utiliza exclusivamente --ff-only.
        """

        estado = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return self._crear_resultado_error(
                estado.mensaje
            )

        if not estado.rama_actual:
            return self._crear_resultado_error(
                (
                    "No se puede realizar Pull porque HEAD "
                    "no está asociado a una rama."
                )
            )

        if not estado.tiene_commits:
            return self._crear_resultado_error(
                (
                    "No se puede realizar Pull porque "
                    "el repositorio todavía no tiene commits."
                )
            )

        operacion_en_curso = self.detectar_operacion_en_curso(
            estado.ruta_raiz
        )

        if operacion_en_curso:
            return self._crear_resultado_error(
                operacion_en_curso
            )

        ruta_bloqueo = self._obtener_ruta_git_interna(
            estado.ruta_raiz,
            "index.lock"
        )

        if (
            ruta_bloqueo is not None
            and ruta_bloqueo.exists()
        ):
            return self._crear_resultado_error(
                (
                    "No se puede realizar Pull porque existe "
                    "un archivo index.lock.\n\n"
                    "Compruebe que no haya otro proceso Git "
                    "trabajando sobre el repositorio.\n\n"
                    "La aplicación no eliminará el bloqueo "
                    "automáticamente."
                )
            )

        resultado_cambios = self.obtener_cambios(
            estado.ruta_raiz
        )

        if not resultado_cambios.exitoso:
            return self._crear_resultado_error(
                resultado_cambios.error
            )

        archivos_conflicto = [
            cambio.ruta
            for cambio in resultado_cambios.cambios
            if cambio.descripcion == "Conflicto"
        ]

        if archivos_conflicto:
            lista_archivos = "\n".join(
                archivos_conflicto
            )

            return self._crear_resultado_error(
                (
                    "No se puede realizar Pull porque existen "
                    "archivos con conflictos:\n\n"
                    f"{lista_archivos}"
                )
            )

        if resultado_cambios.cambios:
            return self._crear_resultado_error(
                (
                    "No se puede realizar Pull porque existen "
                    "cambios sin commit en el repositorio.\n\n"
                    "La aplicación exige un área de trabajo "
                    "completamente limpia antes de descargar."
                )
            )

        resultado_remoto = self.obtener_remoto_sincronizacion(
            estado.ruta_raiz
        )

        if not resultado_remoto.exitoso:
            return self._crear_resultado_error(
                resultado_remoto.error
            )

        remoto = resultado_remoto.salida

        # Actualizamos primero las referencias remotas.
        resultado_fetch = self.ejecutar_fetch(
            estado.ruta_raiz,
            remoto
        )

        if not resultado_fetch.exitoso:
            detalle = (
                resultado_fetch.error
                if resultado_fetch.error
                else resultado_fetch.salida
            )

            return self._crear_resultado_error(
                (
                    "No se realizará Pull porque el Fetch previo "
                    "no pudo completarse.\n\n"
                    f"{detalle}"
                )
            )

        estado_sincronizacion = (
            self.obtener_estado_sincronizacion(
                estado.ruta_raiz
            )
        )

        if not estado_sincronizacion.exitoso:
            return self._crear_resultado_error(
                estado_sincronizacion.error
            )

        if not estado_sincronizacion.upstream_configurado:
            return self._crear_resultado_error(
                (
                    "No se puede realizar Pull porque la rama "
                    "actual no tiene upstream configurado."
                )
            )

        if estado_sincronizacion.divergente:
            return self._crear_resultado_error(
                (
                    "No se realizará Pull porque la rama local "
                    "y la rama remota han divergido.\n\n"
                    f"Commits locales por enviar: "
                    f"{estado_sincronizacion.commits_por_subir}\n"
                    f"Commits remotos por descargar: "
                    f"{estado_sincronizacion.commits_por_bajar}\n\n"
                    "La aplicación no realizará Merge ni Rebase "
                    "automáticamente."
                )
            )

        if estado_sincronizacion.commits_por_subir > 0:
            return self._crear_resultado_error(
                (
                    "No se realizará Pull porque existen commits "
                    "locales pendientes de enviar.\n\n"
                    f"Commits por enviar: "
                    f"{estado_sincronizacion.commits_por_subir}"
                )
            )

        if estado_sincronizacion.commits_por_bajar <= 0:
            return self._crear_resultado_error(
                "No hay commits remotos pendientes de descargar."
            )

        rama_remota = (
            estado_sincronizacion.rama_remota
        )

        prefijo_remoto = (
            f"{remoto}/"
        )

        if not rama_remota.startswith(
            prefijo_remoto
        ):
            return self._crear_resultado_error(
                (
                    "No fue posible determinar de forma segura "
                    "la rama remota que debe descargarse."
                )
            )

        nombre_rama_remota = rama_remota[
            len(prefijo_remoto):
        ]

        if not nombre_rama_remota:
            return self._crear_resultado_error(
                (
                    "No fue posible determinar la rama remota "
                    "que debe descargarse."
                )
            )

        # La opción --ff-only impide que Git cree
        # automáticamente un commit de Merge.
        return self.ejecutar_git(
            argumentos=[
                "pull",
                "--ff-only",
                remoto,
                nombre_rama_remota
            ],
            ruta_repositorio=estado.ruta_raiz,
            tiempo_maximo=180
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
                    "La rama tiene upstream configurado, pero "
                    "la referencia remota no está disponible "
                    "localmente. Ejecute Fetch."
                )
            )

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
                    or (
                        "No fue posible comparar la rama "
                        "con su upstream."
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
                    (
                        f"HEAD..."
                        f"{referencia_remota}"
                    )
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
        Interpreta la salida de rev-list --left-right --count.
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

    @staticmethod
    def _crear_resultado_error(
        mensaje
    ):
        """
        Facilita la construcción de resultados bloqueados
        antes de ejecutar un comando Git.
        """

        return ResultadoComando(
            exitoso=False,
            codigo_salida=-1,
            salida="",
            error=mensaje,
            comando=""
        )