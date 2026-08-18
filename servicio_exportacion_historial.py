import csv
from datetime import datetime
from pathlib import Path

from modelos_historial import ResultadoExportacion


class ServicioExportacionHistorial:
    """
    Exporta a archivos los commits ya consultados por la interfaz.

    Este servicio no ejecuta comandos Git y no modifica el repositorio.
    Solamente escribe una copia del historial visible en un archivo elegido
    explícitamente por el usuario.
    """

    def exportar_csv(
        self,
        ruta_destino,
        commits
    ):
        """
        Exporta commits a CSV compatible con Excel.

        Se utiliza UTF-8 con BOM y punto y coma como separador para facilitar
        la apertura en instalaciones de Windows con configuración regional
        en español.
        """

        error_validacion = self._validar_exportacion(
            ruta_destino,
            commits
        )

        if error_validacion:
            return ResultadoExportacion(
                exitoso=False,
                error=error_validacion
            )

        ruta = Path(ruta_destino)

        try:
            with ruta.open(
                "w",
                encoding="utf-8-sig",
                newline=""
            ) as archivo:
                escritor = csv.writer(
                    archivo,
                    delimiter=";",
                    quoting=csv.QUOTE_MINIMAL,
                    lineterminator="\n"
                )

                escritor.writerow(
                    [
                        "Hash completo",
                        "Hash corto",
                        "Fecha ISO",
                        "Autor",
                        "Correo",
                        "Mensaje"
                    ]
                )

                for commit in commits:
                    escritor.writerow(
                        [
                            self._proteger_celda_csv(commit.hash_completo),
                            self._proteger_celda_csv(commit.hash_corto),
                            self._proteger_celda_csv(commit.fecha_iso),
                            self._proteger_celda_csv(commit.autor),
                            self._proteger_celda_csv(commit.correo),
                            self._proteger_celda_csv(commit.mensaje)
                        ]
                    )

        except OSError as error:
            return ResultadoExportacion(
                exitoso=False,
                error=(
                    "No fue posible escribir el archivo CSV.\n\n"
                    f"Detalle: {error}"
                )
            )

        return ResultadoExportacion(
            exitoso=True,
            ruta_archivo=str(ruta),
            mensaje=(
                f"Se exportaron {len(commits)} commit(s) a CSV."
            )
        )

    def exportar_txt(
        self,
        ruta_destino,
        commits,
        ruta_repositorio="",
        filtro_archivo="",
        fecha_desde="",
        fecha_hasta=""
    ):
        """
        Exporta el historial a un TXT legible por personas.

        El encabezado deja registrados el repositorio y los filtros que
        estaban aplicados cuando se generó la exportación.
        """

        error_validacion = self._validar_exportacion(
            ruta_destino,
            commits
        )

        if error_validacion:
            return ResultadoExportacion(
                exitoso=False,
                error=error_validacion
            )

        ruta = Path(ruta_destino)

        lineas = [
            "HISTORIAL DE COMMITS - GESTOR GIT",
            "=" * 72,
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"Repositorio: {ruta_repositorio or '-'}",
            f"Filtro de archivo: {filtro_archivo or '(sin filtro)'}",
            f"Desde: {fecha_desde or '(sin límite)'}",
            f"Hasta: {fecha_hasta or '(sin límite)'}",
            f"Cantidad de commits: {len(commits)}",
            "=" * 72,
            ""
        ]

        for numero, commit in enumerate(commits, start=1):
            lineas.extend(
                [
                    f"COMMIT {numero}",
                    "-" * 72,
                    f"Hash completo: {commit.hash_completo}",
                    f"Hash corto: {commit.hash_corto}",
                    f"Fecha: {commit.fecha_iso}",
                    f"Autor: {commit.autor}",
                    f"Correo: {commit.correo}",
                    f"Mensaje: {commit.mensaje}",
                    ""
                ]
            )

        try:
            ruta.write_text(
                "\n".join(lineas),
                encoding="utf-8-sig"
            )

        except OSError as error:
            return ResultadoExportacion(
                exitoso=False,
                error=(
                    "No fue posible escribir el archivo TXT.\n\n"
                    f"Detalle: {error}"
                )
            )

        return ResultadoExportacion(
            exitoso=True,
            ruta_archivo=str(ruta),
            mensaje=(
                f"Se exportaron {len(commits)} commit(s) a TXT."
            )
        )

    @staticmethod
    def _validar_exportacion(
        ruta_destino,
        commits
    ):
        """
        Valida los datos mínimos antes de escribir un archivo.
        """

        if not isinstance(ruta_destino, str):
            return "La ruta de destino debe ser texto."

        ruta_destino = ruta_destino.strip()

        if not ruta_destino:
            return "Debe indicar una ruta de destino."

        if "\x00" in ruta_destino:
            return "La ruta de destino contiene un carácter no permitido."

        if not isinstance(commits, (list, tuple)):
            return "La lista de commits no es válida."

        if not commits:
            return "No hay commits visibles para exportar."

        return ""

    @staticmethod
    def _proteger_celda_csv(valor):
        """
        Reduce el riesgo de fórmulas CSV al abrir el archivo en Excel.

        Un mensaje o nombre de autor que comience con =, +, -, @, tabulación
        o retorno de carro se trata como texto anteponiendo una comilla simple.
        """

        texto = str(valor)
        texto_sin_espacios = texto.lstrip()

        if texto_sin_espacios.startswith(
            ("=", "+", "-", "@", "\t", "\r")
        ):
            return "'" + texto

        return texto
