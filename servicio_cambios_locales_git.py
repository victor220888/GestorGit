"""
Servicio de solo lectura para inspeccionar los cambios locales
de un archivo en las tres zonas de Git:

    working tree -> índice  (diff sin preparar)
    índice -> HEAD          (diff preparado)

No ejecuta operaciones remotas y no modifica el working tree,
el índice ni los commits.
"""

from pathlib import Path

from modelos import ResultadoComando
from modelos_cambios_locales import (
    DetalleCambioLocal,
    ResultadoDetalleCambioLocal,
)
from servicio_git import ServicioGit


class ServicioCambiosLocalesGit:
    """
    Consulta los cambios locales de un archivo sin modificarlos.

    Reutiliza un ServicioGit existente para la ejecución segura
    de comandos Git: nunca duplica subprocess.run y nunca utiliza
    shell=True.
    """

    def __init__(self, servicio_git=None):
        self.servicio_git = (
            servicio_git
            if servicio_git is not None
            else ServicioGit()
        )

    def obtener_detalle(self, ruta_repositorio, ruta_archivo):
        """
        Obtiene el detalle estructurado de los cambios locales
        de un archivo.

        La ruta del archivo debe ser relativa al repositorio.

        Devuelve un ResultadoDetalleCambioLocal. Un archivo que ya
        no tiene cambios pendientes NO es un error: se devuelve
        exitoso=True con detalle=None y un mensaje informativo.
        """

        # La validación de la ruta ocurre antes de ejecutar
        # cualquier comando Git: una ruta inválida nunca llega
        # a construir un diff.
        mensaje_error = self._validar_ruta_archivo(
            ruta_archivo
        )

        if mensaje_error:
            return ResultadoDetalleCambioLocal(
                exitoso=False,
                error=mensaje_error
            )

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return ResultadoDetalleCambioLocal(
                exitoso=False,
                error=(
                    estado.mensaje
                    if estado.mensaje
                    else "La carpeta indicada no es un repositorio Git."
                )
            )

        resultado_cambios = self.servicio_git.obtener_cambios(
            estado.ruta_raiz
        )

        if not resultado_cambios.exitoso:
            return ResultadoDetalleCambioLocal(
                exitoso=False,
                error=resultado_cambios.error
            )

        cambio_encontrado = None

        for cambio in resultado_cambios.cambios:
            if cambio.ruta == ruta_archivo:
                cambio_encontrado = cambio
                break

        if cambio_encontrado is None:
            return ResultadoDetalleCambioLocal(
                exitoso=True,
                detalle=None,
                mensaje=(
                    "El archivo ya no tiene cambios locales pendientes."
                )
            )

        detalle = DetalleCambioLocal(
            ruta=cambio_encontrado.ruta,
            descripcion=cambio_encontrado.descripcion,
            preparado=cambio_encontrado.preparado,
            requiere_actualizar_preparado=(
                cambio_encontrado.requiere_actualizar_preparado
            ),
            nuevo_sin_preparar=(
                cambio_encontrado.estado_indice == "?"
                and cambio_encontrado.estado_trabajo == "?"
            ),
            en_conflicto=self._calcular_en_conflicto(
                cambio_encontrado.estado_indice,
                cambio_encontrado.estado_trabajo
            )
        )

        resultado_sin_preparar = self._ejecutar_diff(
            estado.ruta_raiz,
            ruta_archivo,
            preparado=False
        )

        if not resultado_sin_preparar.exitoso:
            return self._resultado_error_diff(
                resultado_sin_preparar
            )

        detalle.diff_sin_preparar = (
            resultado_sin_preparar.salida
        )

        resultado_preparado = self._ejecutar_diff(
            estado.ruta_raiz,
            ruta_archivo,
            preparado=True
        )

        if not resultado_preparado.exitoso:
            return self._resultado_error_diff(
                resultado_preparado
            )

        detalle.diff_preparado = resultado_preparado.salida

        resumen_sin_preparar = self._obtener_resumen(
            estado.ruta_raiz,
            ruta_archivo,
            preparado=False
        )

        if isinstance(
            resumen_sin_preparar,
            ResultadoDetalleCambioLocal
        ):
            return resumen_sin_preparar

        resumen_preparado = self._obtener_resumen(
            estado.ruta_raiz,
            ruta_archivo,
            preparado=True
        )

        if isinstance(
            resumen_preparado,
            ResultadoDetalleCambioLocal
        ):
            return resumen_preparado

        detalle.inserciones_sin_preparar = (
            resumen_sin_preparar[0]
        )

        detalle.eliminaciones_sin_preparar = (
            resumen_sin_preparar[1]
        )

        detalle.binario_sin_preparar = (
            resumen_sin_preparar[2]
        )

        detalle.inserciones_preparadas = (
            resumen_preparado[0]
        )

        detalle.eliminaciones_preparadas = (
            resumen_preparado[1]
        )

        detalle.binario_preparado = (
            resumen_preparado[2]
        )

        self._completar_ultimo_commit(
            estado.ruta_raiz,
            estado.tiene_commits,
            detalle
        )

        return ResultadoDetalleCambioLocal(
            exitoso=True,
            detalle=detalle
        )

    @staticmethod
    def _calcular_en_conflicto(estado_indice, estado_trabajo):
        """
        Determina si el par de códigos de git status corresponde
        a un conflicto de merge.

        Helper propio del servicio (sin acoplarse a métodos
        privados de ServicioGit): la seguridad se decide desde
        los códigos estructurados, nunca desde el texto
        localizado de descripcion.
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

    def _ejecutar_diff(
        self,
        ruta_repositorio,
        ruta_archivo,
        preparado
    ):
        """
        Ejecuta git diff sobre una ruta explícita.

        Nunca se utiliza shell=True y la ruta siempre se separa
        mediante "--" después de los argumentos de configuración.
        """

        argumentos = [
            "--literal-pathspecs",
            "diff",
        ]

        if preparado:
            argumentos.append("--cached")

        argumentos.extend(
            [
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--unified=3",
                "--",
                ruta_archivo,
            ]
        )

        return self.servicio_git.ejecutar_git(
            argumentos,
            ruta_repositorio=ruta_repositorio
        )

    def _obtener_resumen(
        self,
        ruta_repositorio,
        ruta_archivo,
        preparado
    ):
        """
        Calcula inserciones y eliminaciones mediante --numstat.

        Devuelve la tupla (inserciones, eliminaciones, binario)
        cuando la consulta es exitosa.

        Cuando la consulta FALLA devuelve un
        ResultadoDetalleCambioLocal con exitoso=False y un mensaje
        controlado: nunca se informa 0 inserciones / 0 eliminaciones
        como si fueran datos reales.

        Para archivos binarios Git devuelve "-"; en ese caso se
        marca binario=True y no se intenta convertir el texto.
        """

        argumentos = [
            "--literal-pathspecs",
            "diff",
        ]

        if preparado:
            argumentos.append("--cached")

        argumentos.extend(
            [
                "--numstat",
                "--no-ext-diff",
                "--no-textconv",
                "--",
                ruta_archivo,
            ]
        )

        resultado = self.servicio_git.ejecutar_git(
            argumentos,
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return ResultadoDetalleCambioLocal(
                exitoso=False,
                error=(
                    resultado.error
                    if resultado.error
                    else (
                        "No fue posible calcular el resumen de "
                        "inserciones y eliminaciones del archivo."
                    )
                )
            )

        return self._interpretar_numstat(
            resultado.salida
        )

    @staticmethod
    def _interpretar_numstat(salida):
        """
        Convierte la salida estructurada de --numstat
        en conteos de inserciones y eliminaciones.
        """

        inserciones = 0
        eliminaciones = 0
        binario = False

        for linea in salida.splitlines():
            if not linea:
                continue

            partes = linea.split("\t", 2)

            if len(partes) < 2:
                continue

            if partes[0] == "-" or partes[1] == "-":
                binario = True
                continue

            try:
                inserciones += int(partes[0])
                eliminaciones += int(partes[1])
            except ValueError:
                binario = True

        return (
            inserciones,
            eliminaciones,
            binario
        )

    def _completar_ultimo_commit(
        self,
        ruta_repositorio,
        tiene_commits,
        detalle
    ):
        """
        Agrega el hash corto y el mensaje del último commit local.

        Cuando el repositorio todavía no tiene commits, el detalle
        se deja con los textos vacíos y la interfaz muestra un
        mensaje educativo.
        """

        if not tiene_commits:
            return

        resultado_hash = self.servicio_git.ejecutar_git(
            ["rev-parse", "--short", "HEAD"],
            ruta_repositorio=ruta_repositorio
        )

        if resultado_hash.exitoso:
            detalle.hash_commit = resultado_hash.salida

        resultado_mensaje = self.servicio_git.ejecutar_git(
            ["log", "-1", "--format=%s"],
            ruta_repositorio=ruta_repositorio
        )

        if resultado_mensaje.exitoso:
            detalle.mensaje_commit = resultado_mensaje.salida

    def _resultado_error_diff(self, resultado_comando):
        """
        Convierte el error de un diff en ResultadoDetalleCambioLocal.
        """

        return ResultadoDetalleCambioLocal(
            exitoso=False,
            error=(
                resultado_comando.error
                if resultado_comando.error
                else "No fue posible consultar los cambios del archivo."
            )
        )

    @staticmethod
    def _validar_ruta_archivo(ruta_archivo):
        """
        Valida una ruta de archivo recibida desde la interfaz.

        Solo se aceptan rutas relativas al repositorio, sin ".."
        y sin caracteres NUL. Devuelve el mensaje de error o una
        cadena vacía si la ruta es válida.
        """

        if ruta_archivo is None:
            return "No se indicó ningún archivo."

        ruta_texto = str(ruta_archivo)

        if "\x00" in ruta_texto:
            return (
                "La ruta del archivo contiene un carácter inválido."
            )

        if not ruta_texto or ruta_texto.isspace():
            return (
                "Se recibió una ruta de archivo vacía."
            )

        ruta_objeto = Path(ruta_texto)

        if ruta_objeto.is_absolute():
            return (
                "Los archivos deben indicarse mediante rutas "
                "relativas al repositorio."
            )

        if ".." in ruta_objeto.parts:
            return (
                "La ruta del archivo intenta salir "
                "del repositorio."
            )

        return ""