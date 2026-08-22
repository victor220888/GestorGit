from urllib.parse import urlparse

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

    def agregar_remoto_github(
        self,
        ruta_repositorio,
        url_remoto
    ):
        """
        Configura el primer remoto de un repositorio local.

        Solamente se permite cuando el repositorio todavía no
        tiene ningún remoto configurado. No modifica remotos
        existentes y no ejecuta ninguna operación de red.

        El remoto se crea con el nombre 'origin' y únicamente
        acepta URLs HTTPS de github.com.

        La aplicación nunca recibe ni almacena PAT, token
        o contraseña dentro de la URL.
        """

        estado = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return self._crear_resultado_error(
                estado.mensaje
            )

        if estado.remotos:
            return self._crear_resultado_error(
                (
                    "El repositorio ya tiene remoto(s) configurado(s): "
                    f"{', '.join(estado.remotos)}.\n\n"
                    "Esta operación solamente configura el primer "
                    "remoto cuando no existe ninguno.\n\n"
                    "La aplicación no modificará ni eliminará "
                    "los remotos existentes."
                )
            )

        url_limpia, mensaje_error = (
            self._validar_url_remoto_github(
                url_remoto
            )
        )

        if mensaje_error:
            return self._crear_resultado_error(
                mensaje_error
            )

        # remote add solamente modifica .git/config.
        # No se conecta a Internet y no ejecuta Fetch.
        return self.ejecutar_git(
            argumentos=[
                "remote",
                "add",
                "origin",
                url_limpia
            ],
            ruta_repositorio=estado.ruta_raiz
        )

    def _validar_url_remoto_github(
        self,
        url_remoto
    ):
        """
        Valida una URL HTTPS de github.com.

        Devuelve:
            url_limpia
            mensaje_error

        Acepta únicamente:
            https://github.com/usuario/repositorio
            https://github.com/usuario/repositorio.git

        Rechaza credenciales embebidas, otros esquemas,
        otros hosts, query y fragmentos.
        """

        if url_remoto is None:
            return (
                "",
                "Debe indicar la URL HTTPS del repositorio de GitHub."
            )

        if not isinstance(url_remoto, str):
            return (
                "",
                "La URL del repositorio no es válida."
            )

        url_limpia = url_remoto.strip()

        if not url_limpia:
            return (
                "",
                "Debe indicar la URL HTTPS del repositorio de GitHub."
            )

        if "\x00" in url_limpia:
            return (
                "",
                "La URL contiene un carácter inválido."
            )

        if (
            "\n" in url_limpia
            or "\r" in url_limpia
        ):
            return (
                "",
                "La URL no puede contener saltos de línea."
            )

        if url_limpia.startswith("-"):
            return (
                "",
                "La URL no puede comenzar por '-'."
            )

        try:
            url_parseada = urlparse(
                url_limpia
            )
        except ValueError:
            return (
                "",
                "La URL del repositorio no es válida."
            )

        if (
            url_parseada.scheme != "https"
            or url_parseada.username is not None
            or url_parseada.password is not None
            or url_parseada.query
            or url_parseada.fragment
        ):
            return (
                "",
                (
                    "La URL debe ser HTTPS de GitHub, sin usuario, "
                    "sin contraseña, sin consulta (query) "
                    "y sin fragmento.\n\n"
                    "Ejemplo válido:\n"
                    "https://github.com/usuario/repositorio\n\n"
                    "La aplicación nunca recibe ni almacena "
                    "PAT, token o contraseñas."
                )
            )

        if url_parseada.hostname != "github.com":
            return (
                "",
                (
                    "La URL debe pertenecer exclusivamente "
                    "al host github.com.\n\n"
                    "En esta primera versión no se aceptan "
                    "otros hosts, rutas locales ni SSH."
                )
            )

        try:
            if url_parseada.port is not None:
                return (
                    "",
                    "La URL no puede incluir un puerto."
                )
        except ValueError:
            return (
                "",
                "La URL no puede incluir un puerto."
            )

        ruta_texto = url_parseada.path

        if (
            not ruta_texto
            or not ruta_texto.startswith("/")
        ):
            return (
                "",
                (
                    "La URL debe indicar el propietario "
                    "y el nombre del repositorio.\n\n"
                    "Ejemplo válido:\n"
                    "https://github.com/usuario/repositorio"
                )
            )

        partes_ruta = ruta_texto[1:].split("/")

        if len(partes_ruta) != 2:
            return (
                "",
                (
                    "La ruta de la URL debe representar "
                    "propietario/repositorio.\n\n"
                    "Ejemplo válido:\n"
                    "https://github.com/usuario/repositorio"
                )
            )

        propietario, repositorio = partes_ruta

        if (
            not propietario
            or not repositorio
        ):
            return (
                "",
                (
                    "La ruta de la URL debe representar "
                    "propietario/repositorio.\n\n"
                    "Ejemplo válido:\n"
                    "https://github.com/usuario/repositorio"
                )
            )

        if (
            propietario.startswith("-")
            or repositorio.startswith("-")
        ):
            return (
                "",
                "La URL no puede contener opciones que comiencen por '-'."
            )

        if repositorio.endswith(".git"):
            repositorio_sin_extension = repositorio[:-4]
        else:
            repositorio_sin_extension = repositorio

        if not repositorio_sin_extension:
            return (
                "",
                (
                    "La ruta de la URL debe representar "
                    "propietario/repositorio.\n\n"
                    "Ejemplo válido:\n"
                    "https://github.com/usuario/repositorio"
                )
            )

        return (
            url_limpia,
            ""
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

        if (
            not estado_sincronizacion.upstream_configurado
            and not estado_sincronizacion.rama_remota_existe
        ):
            otras_ramas = self._obtener_otras_ramas_remotas(
                estado.ruta_raiz,
                remoto,
                rama_local
            )

            if otras_ramas is None:
                return self._crear_resultado_error(
                    (
                        "No fue posible verificar si el "
                        "remoto está vacío de ramas.\n\n"
                        "No se realizará el primer Push.\n\n"
                        "Revise el repositorio remoto antes "
                        "de continuar."
                    )
                )

            if otras_ramas:
                lista_ramas = "\n".join(
                    f"- {rama}"
                    for rama in otras_ramas
                )

                return self._crear_resultado_error(
                    (
                        "El remoto no está vacío y contiene "
                        "otras ramas.\n\n"
                        "El flujo de primer Push de GestorGit "
                        "solamente crea la rama remota cuando "
                        "el repositorio remoto está vacío.\n\n"
                        f"Ramas encontradas:\n{lista_ramas}\n\n"
                        "Revise el repositorio remoto antes "
                        "de continuar."
                    )
                )

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

    def _obtener_otras_ramas_remotas(
        self,
        ruta_repositorio,
        remoto,
        rama_local
    ):
        """
        Devuelve las ramas conocidas del remoto distintas
        de la rama local actual.

        Utiliza las referencias actualizadas por el último
        Fetch, sin conectarse a Internet.

        Devuelve None si no fue posible consultar las ramas.
        """

        prefijo_remoto = (
            f"refs/remotes/{remoto}/"
        )

        resultado = self.ejecutar_git(
            argumentos=[
                "for-each-ref",
                "--format=%(refname)",
                prefijo_remoto
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return None

        otras_ramas = []

        for linea in resultado.salida.splitlines():
            nombre_ref = linea.strip()

            if not nombre_ref.startswith(prefijo_remoto):
                continue

            nombre_rama = nombre_ref[len(prefijo_remoto):]

            if not nombre_rama:
                continue

            if nombre_rama == "HEAD":
                continue

            if nombre_rama == rama_local:
                continue

            otras_ramas.append(
                f"{remoto}/{nombre_rama}"
            )

        return otras_ramas

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

    # =============================================================
    # Publicar rama local
    # =============================================================

    def publicar_rama_local(
        self,
        ruta_repositorio,
        remoto_esperado,
        rama_esperada
    ):
        """
        Publica la rama local ACTUAL en el único remoto determinable.

        Crea refs/heads/<rama> en el remoto y configura su upstream
        mediante un Push normal con --set-upstream. Es una operación
        DISTINTA del Push normal (ejecutar_push_seguro queda intacto)
        y no relaja ninguna de sus protecciones.

        Solo procede cuando la rama todavía NO tiene upstream y la
        rama remota homónima NO existe en el remoto, verificado con
        una consulta remota directa de solo lectura inmediatamente
        antes del Push:

            git ls-remote --heads <remoto> refs/heads/<rama>

        No ejecuta Fetch: la interfaz exige un Fetch manual exitoso
        previo y la consulta fresca la aporta ls-remote.

        Comando productivo:

            git push --porcelain --set-upstream <remoto> <rama>:refs/heads/<rama>
        """

        # La confirmación de la interfaz se hizo sobre esta rama y
        # este remoto: el servicio no confía ciegamente en la GUI y
        # vuelve a comprobar ambos contra el repositorio real.
        error_entrada = self._validar_datos_publicacion(
            remoto_esperado,
            rama_esperada
        )

        if error_entrada:
            return self._crear_resultado_error(error_entrada)

        # PRIMERA validación local completa: repositorio, commits,
        # rama esperada, upstream ausente, remoto seguro esperado,
        # operación en curso, index.lock, working tree/staging
        # limpios y sin conflictos.
        ruta_raiz, remoto, error = self._validar_publicacion_local(
            ruta_repositorio,
            remoto_esperado,
            rama_esperada
        )

        if error:
            return self._crear_resultado_error(error)

        # SEGUNDA validación local, releyendo todo el estado de
        # nuevo (defensa en profundidad contra cambios externos
        # aparecidos entre ambas pasadas, patrón de
        # ServicioRamasGit).
        ruta_raiz, remoto, error = self._validar_publicacion_local(
            ruta_repositorio,
            remoto_esperado,
            rama_esperada
        )

        if error:
            return self._crear_resultado_error(error)

        # Consulta remota directa de solo lectura, inmediatamente
        # antes del Push: ¿existe ya refs/heads/<rama> en el
        # remoto? Un error de consulta bloquea; nunca se interpreta
        # un error como ausencia. Sin --force-with-lease: la
        # limitación residual de carrera queda minimizada con esta
        # consulta fresca y documentada.
        existe_homonima, error_consulta = (
            self._consultar_rama_remota_homonima(
                ruta_raiz,
                remoto,
                rama_esperada
            )
        )

        if error_consulta:
            return self._crear_resultado_error(error_consulta)

        if existe_homonima:
            return self._crear_resultado_error(
                (
                    f"La rama remota '{rama_esperada}' ya existe "
                    f"en '{remoto}'.\n\n"
                    "\"Publicar rama local\" solo crea una rama "
                    "remota nueva.\n\n"
                    "No se realizó ninguna publicación.\n\n"
                    "Use el flujo normal de Push; GestorGit "
                    "aplicará allí sus comprobaciones de seguridad "
                    "y decidirá si puede continuar."
                )
            )

        # Comando productivo: Push normal con refspec explícito de
        # la única rama que se publica. Nunca --force ni
        # --force-with-lease, --all, --tags, --mirror ni --delete.
        return self.ejecutar_git(
            argumentos=[
                "push",
                "--porcelain",
                "--set-upstream",
                remoto,
                (
                    f"{rama_esperada}:"
                    f"refs/heads/{rama_esperada}"
                )
            ],
            ruta_repositorio=ruta_raiz,
            tiempo_maximo=180
        )

    def _validar_datos_publicacion(
        self,
        remoto_esperado,
        rama_esperada
    ):
        """
        Validación básica de los valores esperados recibidos.

        Rechaza valores que no son texto, vacíos, con caracteres
        NUL o que comienzan con guion (evita opciones Git
        inyectadas) antes de construir cualquier comando.

        Devuelve "" cuando ambos son válidos o el motivo del
        bloqueo.
        """

        valores = (
            (rama_esperada, "rama"),
            (remoto_esperado, "remoto")
        )

        for nombre, etiqueta in valores:
            if nombre is None or not isinstance(nombre, str):
                return (
                    f"El nombre del {etiqueta} a publicar debe "
                    "ser texto."
                )

            if not nombre.strip():
                return (
                    f"El nombre del {etiqueta} a publicar no "
                    "puede estar vacío."
                )

            if "\x00" in nombre:
                return (
                    f"El nombre del {etiqueta} no puede contener "
                    "caracteres NUL."
                )

            if nombre.startswith("-"):
                return (
                    f"El nombre del {etiqueta} no puede comenzar "
                    "con un guion."
                )

        return ""

    def _validar_publicacion_local(
        self,
        ruta_repositorio,
        remoto_esperado,
        rama_esperada
    ):
        """
        Valida las precondiciones LOCALES de la publicación.

        Se ejecuta DOS veces desde publicar_rama_local: antes de
        preparar la operación e inmediatamente antes de la consulta
        remota y del Push. No realiza operaciones de red.

        Devuelve (ruta_raiz, remoto, "") cuando puede proseguir, o
        (None, None, mensaje) con el motivo del bloqueo. Un error
        de consulta nunca se interpreta como estado seguro.
        """

        estado = self.analizar_repositorio(ruta_repositorio)

        if not estado.es_repositorio:
            return (None, None, estado.mensaje)

        if not estado.tiene_commits:
            return (
                None,
                None,
                (
                    "No se puede publicar la rama porque el "
                    "repositorio todavía no tiene commits."
                )
            )

        if not estado.rama_actual:
            return (
                None,
                None,
                (
                    "No se puede publicar la rama porque HEAD "
                    "no está asociado a una rama."
                )
            )

        if estado.rama_actual != rama_esperada:
            return (
                None,
                None,
                (
                    f"La rama actual cambió: la confirmación se "
                    f"hizo sobre la rama '{rama_esperada}', pero "
                    f"ahora la rama actual es "
                    f"'{estado.rama_actual}'. No se realizará la "
                    "publicación."
                )
            )

        upstream_configurado, nombre_upstream, error_upstream = (
            self._obtener_upstream_rama_actual(
                estado.ruta_raiz,
                estado.rama_actual
            )
        )

        if error_upstream:
            # Un error o una incertidumbre en la consulta NUNCA
            # equivale a "sin upstream": se bloquea la publicación.
            return (None, None, error_upstream)

        if upstream_configurado:
            return (
                None,
                None,
                (
                    f"La rama local '{estado.rama_actual}' ya "
                    "está vinculada a una rama remota: su "
                    f"upstream es '{nombre_upstream}'.\n\n"
                    "\"Publicar rama local\" sirve solamente para "
                    "ramas que todavía no fueron publicadas.\n\n"
                    "No se ejecutó ningún Push desde esta acción.\n\n"
                    "Use el flujo normal de Push para enviar "
                    "commits; GestorGit aplicará allí sus "
                    "comprobaciones de seguridad."
                )
            )

        # Remoto seguro: nunca se elige uno al azar. Con upstream
        # ausente, obtener_remoto_sincronizacion exige exactamente
        # un remoto (cero o varios remotos bloquean con su propio
        # mensaje educativo).
        resultado_remoto = self.obtener_remoto_sincronizacion(
            estado.ruta_raiz
        )

        if not resultado_remoto.exitoso:
            return (None, None, resultado_remoto.error)

        remoto = resultado_remoto.salida

        if remoto_esperado not in estado.remotos:
            return (
                None,
                None,
                (
                    f"El remoto '{remoto_esperado}' no figura "
                    "entre los remotos configurados del "
                    "repositorio."
                )
            )

        if remoto != remoto_esperado:
            return (
                None,
                None,
                (
                    f"El remoto determinable cambió: la "
                    f"confirmación se hizo sobre "
                    f"'{remoto_esperado}', pero el remoto seguro "
                    f"actual es '{remoto}'. No se realizará la "
                    "publicación."
                )
            )

        operacion_en_curso = self.detectar_operacion_en_curso(
            estado.ruta_raiz
        )

        if operacion_en_curso:
            return (
                None,
                None,
                (
                    operacion_en_curso
                    + "\n\nGestorGit no publicará la rama "
                    "mientras haya una operación Git en curso."
                )
            )

        ruta_bloqueo = self._obtener_ruta_git_interna(
            estado.ruta_raiz,
            "index.lock"
        )

        if (
            ruta_bloqueo is not None
            and ruta_bloqueo.exists()
        ):
            return (
                None,
                None,
                (
                    "No se puede publicar la rama porque existe "
                    "un archivo index.lock.\n\n"
                    "Compruebe que no haya otro proceso Git "
                    "trabajando sobre el repositorio.\n\n"
                    "La aplicación no eliminará el bloqueo "
                    "automáticamente."
                )
            )

        resultado_cambios = self.obtener_cambios(estado.ruta_raiz)

        if not resultado_cambios.exitoso:
            return (
                None,
                None,
                (
                    "No fue posible determinar el estado de los "
                    "archivos del repositorio; la publicación de "
                    "la rama quedó bloqueada."
                )
            )

        # Los conflictos se reconocen exclusivamente con el dato
        # estructurado en_conflicto (códigos Git XY), nunca con el
        # texto localizado de la descripción.
        conflictos = [
            cambio.ruta
            for cambio in resultado_cambios.cambios
            if cambio.en_conflicto
        ]

        if conflictos:
            lista_conflictos = "\n".join(conflictos)

            return (
                None,
                None,
                (
                    "No se puede publicar la rama porque existen "
                    "archivos en conflicto:\n\n"
                    f"{lista_conflictos}\n\n"
                    "Git necesita que una persona decida cómo "
                    "resolver el conflicto. GestorGit no elige "
                    "una versión automáticamente."
                )
            )

        if resultado_cambios.cambios:
            cantidad = len(resultado_cambios.cambios)

            return (
                None,
                None,
                (
                    "No se puede publicar la rama porque el "
                    f"repositorio no está limpio: hay {cantidad} "
                    "archivo(s) con cambios, preparados o nuevos "
                    "pendientes.\n\n"
                    "\"Publicar rama local\" exige un área de "
                    "trabajo completamente limpia. Confirme, "
                    "prepare o descarte los cambios y vuelva a "
                    "intentarlo."
                )
            )

        return (estado.ruta_raiz, remoto, "")

    def _obtener_upstream_rama_actual(
        self,
        ruta_repositorio,
        rama
    ):
        """
        Consulta ESTRUCTURADA del upstream configurado de una rama.

        Comando:

            git for-each-ref --format=%(upstream:short) refs/heads/<rama>

        for-each-ref representa la configuración de upstream de la
        rama aunque la remote-tracking ref de seguimiento esté
        ausente o marcada como gone (situación que
        rev-parse @{upstream} no resuelve: falla aunque el upstream
        siga configurado). Por eso un fallo del comando es un ERROR
        y nunca equivale a "sin upstream".

        Devuelve:
            (True, nombre, "")    -> upstream configurado;
            (False, "", "")       -> sin upstream configurado;
            (False, "", mensaje)  -> error de consulta.
        """

        resultado = self.ejecutar_git(
            argumentos=[
                "for-each-ref",
                "--format=%(upstream:short)",
                f"refs/heads/{rama}"
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            detalle = (
                resultado.error
                if resultado.error
                else resultado.salida
            )

            return (
                False,
                "",
                (
                    "No fue posible consultar el upstream de la "
                    f"rama '{rama}'.\n\n"
                    "No se realizará la publicación.\n\n"
                    f"{detalle}"
                )
            )

        nombre = resultado.salida.strip()

        if nombre:
            return (True, nombre, "")

        return (False, "", "")

    def _consultar_rama_remota_homonima(
        self,
        ruta_repositorio,
        remoto,
        rama
    ):
        """
        Consulta directamente en el remoto si existe la rama
        refs/heads/<rama>, mediante una operación de solo lectura:

            git ls-remote --heads <remoto> refs/heads/<rama>

        La presencia local de refs/remotes/<remoto>/<rama> depende
        del refspec de Fetch configurado, por lo que NO es fuente
        suficiente: la decisión crítica se toma con esta consulta
        remota fresca ejecutada inmediatamente antes del Push.

        Devuelve (existe, "") o (False, mensaje) cuando la consulta
        falla. Un error nunca se interpreta como ausencia.
        """

        resultado = self.ejecutar_git(
            argumentos=[
                "ls-remote",
                "--heads",
                remoto,
                f"refs/heads/{rama}"
            ],
            ruta_repositorio=ruta_repositorio,
            tiempo_maximo=180
        )

        if not resultado.exitoso:
            detalle = (
                resultado.error
                if resultado.error
                else resultado.salida
            )

            return (
                False,
                (
                    "No fue posible consultar el remoto para "
                    f"verificar si la rama '{rama}' ya existe.\n\n"
                    "No se realizará la publicación.\n\n"
                    f"{detalle}"
                )
            )

        # Salida vacía con comando exitoso: la rama homónima no
        # fue encontrada en el remoto.
        if not resultado.salida.strip():
            return (False, "")

        return (True, "")