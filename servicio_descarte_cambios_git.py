"""
Servicio para descartar los cambios SIN PREPARAR de un archivo.

Restaura el working tree del archivo desde el área preparada
(índice/staging):

    HEAD
      ↓
    Staging        = versión preparada  (se conserva intacta)
      ↓
    Working tree   = versión preparada  (cambios posteriores eliminados)

Equivale conceptualmente a:

    git --literal-pathspecs restore --worktree -- <ruta>

Sin --source explícito, `git restore --worktree` restaura desde el
índice, no desde HEAD: eso permite que en un archivo "MM" el working
tree vuelva a la versión preparada sin tocar el staging.

No crea commits, no modifica HEAD, no quita archivos del staging
y no ejecuta operaciones remotas (Fetch, Pull o Push).
"""

from pathlib import Path

from modelos import ResultadoComando
from servicio_git import ServicioGit


class ServicioDescarteCambiosGit:
    """
    Descarta los cambios sin preparar de UN archivo explícito.

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

    def descartar_cambios_sin_preparar(
        self,
        ruta_repositorio,
        ruta_archivo
    ):
        """
        Elimina únicamente los cambios que el archivo tiene en el
        working tree respecto del índice.

        La ruta del archivo debe ser relativa al repositorio.
        Devuelve un ResultadoComando.

        La operación es 100 % local y conserva exactamente lo que
        está preparado.
        """

        mensaje_error = self._validar_ruta_archivo(
            ruta_archivo
        )

        if mensaje_error:
            return self._resultado_error(
                mensaje_error
            )

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return self._resultado_error(
                estado.mensaje
                if estado.mensaje
                else "La carpeta indicada no es un repositorio Git."
            )

        # No confiamos en el estado que mostraba la interfaz: se
        # vuelve a consultar justo antes de ejecutar el restore.
        resultado_cambios = self.servicio_git.obtener_cambios(
            estado.ruta_raiz
        )

        if not resultado_cambios.exitoso:
            return self._resultado_error(
                resultado_cambios.error
            )

        cambio_encontrado = None

        for cambio in resultado_cambios.cambios:
            if cambio.ruta == ruta_archivo:
                cambio_encontrado = cambio
                break

        if cambio_encontrado is None:
            return self._resultado_error(
                "El archivo ya no tiene cambios sin preparar."
            )

        # Un archivo nuevo (??) no se puede "descartar": hacerlo
        # significaría borrarlo físicamente del disco, lo cual
        # queda FUERA de esta funcionalidad.
        if (
            cambio_encontrado.estado_indice == "?"
            and cambio_encontrado.estado_trabajo == "?"
        ):
            return self._resultado_error(
                "Este archivo es nuevo y todavía no está bajo "
                "seguimiento.\n\n"
                "GestorGit no lo eliminará automáticamente."
            )

        # Nunca se ejecuta restore sobre estados de conflicto.
        if self._es_estado_conflicto(
            cambio_encontrado.estado_indice,
            cambio_encontrado.estado_trabajo
        ):
            return self._resultado_error(
                "El archivo está en conflicto. GestorGit no "
                "descartará cambios automáticamente mientras "
                "exista un conflicto."
            )

        # La regla se basa en los códigos de estado, nunca en la
        # descripción: el working tree debe tener una diferencia
        # real respecto del índice.
        if cambio_encontrado.estado_trabajo in (
            " ",
            "?",
            "!"
        ):
            return self._resultado_error(
                "El archivo no tiene cambios sin preparar "
                "para descartar."
            )

        argumentos = [
            "--literal-pathspecs",
            "restore",
            "--worktree",
            "--",
            ruta_archivo,
        ]

        return self.servicio_git.ejecutar_git(
            argumentos,
            ruta_repositorio=estado.ruta_raiz
        )

    @staticmethod
    def _resultado_error(mensaje):
        """
        Construye un ResultadoComando de error controlado.
        """

        return ResultadoComando(
            exitoso=False,
            codigo_salida=-1,
            salida="",
            error=mensaje,
            comando=""
        )

    @staticmethod
    def _es_estado_conflicto(estado_indice, estado_trabajo):
        """
        Determina si el par de códigos de git status corresponde
        a un conflicto de merge.

        Helper propio del servicio: no se acopla a métodos privados
        de ServicioGit.
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
    def _validar_ruta_archivo(ruta_archivo):
        """
        Valida una ruta de archivo recibida desde la interfaz.

        Solo se aceptan rutas relativas al repositorio, sin ".."
        y sin caracteres NUL. Devuelve el mensaje de error o una
        cadena vacía si la ruta es válida.

        Los nombres que comienzan por guión o contienen caracteres
        especiales son válidos: la seguridad la aportan
        --literal-pathspecs y "--" al construir el comando.
        """

        if ruta_archivo is None:
            return "No se indicó ningún archivo."

        ruta_texto = str(ruta_archivo)

        # El NUL se comprueba antes de construir cualquier Path.
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