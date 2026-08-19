"""
Pruebas del descarte de cambios sin preparar.

Cubren la restauración del working tree de UN archivo desde el
índice (staging) mediante:

    git --literal-pathspecs restore --worktree -- <ruta>

- casos " M", MM, " D", MD y AM;
- conservación exacta del staging;
- rechazo de archivos nuevos (??), conflictos y rutas peligrosas;
- argumentos exactos del comando y ausencia de verbos destructivos.

Utilizan exclusivamente carpetas temporales y nunca tocan GitHub
ni los repositorios reales.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from modelos import (
    CambioArchivo,
    EstadoRepositorio,
    ResultadoCambios,
    ResultadoComando,
)
from servicio_descarte_cambios_git import ServicioDescarteCambiosGit
from servicio_git import ServicioGit


class ServicioGitEspiaDescarte:
    """
    Sustituto de ServicioGit para pruebas.

    Registra las llamadas a ejecutar_git sin ejecutar Git real y
    devuelve el estado configurado para que el flujo del servicio
    llegue a decidir el descarte.
    """

    def __init__(self, cambios):
        self.cambios = cambios
        self.llamadas_ejecutar_git = []

    def analizar_repositorio(self, ruta_repositorio):
        return EstadoRepositorio(
            es_repositorio=True,
            ruta_raiz=str(ruta_repositorio),
            rama_actual="master",
            tiene_commits=True,
            remotos=[],
            mensaje="Repositorio Git valido."
        )

    def obtener_cambios(self, ruta_repositorio):
        return ResultadoCambios(
            exitoso=True,
            cambios=list(self.cambios)
        )

    def ejecutar_git(
        self,
        argumentos,
        ruta_repositorio=None,
        tiempo_maximo=30
    ):
        self.llamadas_ejecutar_git.append(
            list(argumentos)
        )

        return ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando=""
        )


class TestDescarteCambiosGit(unittest.TestCase):
    """
    Pruebas del descarte de cambios sin preparar.
    """

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()

        self.ruta_repositorio = Path(
            self.temporal.name
        ) / "repositorio"

        self._ejecutar_git(
            "init",
            "--initial-branch=master",
            str(self.ruta_repositorio)
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "config",
            "user.name",
            "Usuario Descarte"
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "config",
            "user.email",
            "descarte@example.com"
        )

        self.servicio = ServicioDescarteCambiosGit(
            ServicioGit()
        )

    def tearDown(self):
        self.temporal.cleanup()

    def _ejecutar_git(self, *argumentos):
        """
        Ejecuta Git fuera del repositorio temporal.
        """

        return subprocess.run(
            ["git", *argumentos],
            check=True,
            capture_output=True,
            text=True
        )

    def _ejecutar_git_repositorio(self, *argumentos):
        """
        Ejecuta Git dentro del repositorio temporal.
        """

        return subprocess.run(
            ["git", *argumentos],
            cwd=self.ruta_repositorio,
            check=True,
            capture_output=True,
            text=True
        )

    def _escribir_archivo(self, ruta_relativa, contenido):
        """
        Escribe un archivo dentro del repositorio temporal.
        """

        ruta_archivo = (
            self.ruta_repositorio / ruta_relativa
        )

        ruta_archivo.write_text(
            contenido,
            encoding="utf-8"
        )

    def _crear_commit_inicial(self, nombre="archivo.txt"):
        """
        Crea un commit inicial con un archivo de prueba.
        """

        self._escribir_archivo(
            nombre,
            "linea uno\nlinea dos\nlinea tres\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "--",
            nombre
        )

        self._ejecutar_git_repositorio(
            "commit",
            "-m",
            "Commit inicial"
        )

    def _estado_crudo(self):
        """
        Devuelve el estado sin procesar del repositorio temporal.
        """

        resultado = subprocess.run(
            [
                "git",
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            ],
            cwd=self.ruta_repositorio,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return (
            resultado.returncode,
            resultado.stdout,
            resultado.stderr
        )

    def _diff_cached(self, ruta_relativa):
        """
        Devuelve el diff preparado de un archivo.
        """

        resultado = subprocess.run(
            [
                "git",
                "diff",
                "--cached",
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--",
                ruta_relativa,
            ],
            cwd=self.ruta_repositorio,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return resultado.stdout

    def _contenido_archivo(self, ruta_relativa):
        """
        Devuelve el contenido actual de un archivo.
        """

        return (
            self.ruta_repositorio / ruta_relativa
        ).read_text(
            encoding="utf-8"
        )

    def test_descarte_archivo_modificado_sin_preparar(self):
        """
        Un archivo " M" vuelve a coincidir con índice/HEAD y el
        status queda limpio para ese archivo.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "version modificada sin preparar\n"
        )

        resultado = self.servicio.descartar_cambios_sin_preparar(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(
            self._contenido_archivo("archivo.txt"),
            "linea uno\nlinea dos\nlinea tres\n"
        )

        codigo, salida, _ = self._estado_crudo()
        self.assertEqual(codigo, 0)
        self.assertEqual(salida, "")

    def test_descarte_caso_mm_conserva_staging(self):
        """
        En el caso MM el working tree vuelve a la versión preparada
        y el diff --cached NO cambia: el staging queda intacto.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "version preparada\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "--",
            "archivo.txt"
        )

        self._escribir_archivo(
            "archivo.txt",
            "version preparada\ncambios posteriores\n"
        )

        diff_cached_antes = self._diff_cached(
            "archivo.txt"
        )

        resultado = self.servicio.descartar_cambios_sin_preparar(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)

        self.assertEqual(
            self._contenido_archivo("archivo.txt"),
            "version preparada\n"
        )

        diff_cached_despues = self._diff_cached(
            "archivo.txt"
        )

        self.assertEqual(
            diff_cached_antes,
            diff_cached_despues
        )

        codigo, salida, _ = self._estado_crudo()
        self.assertEqual(codigo, 0)
        self.assertIn("M ", salida)

        resultado_diff = subprocess.run(
            [
                "git",
                "diff",
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--",
                "archivo.txt",
            ],
            cwd=self.ruta_repositorio,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        self.assertEqual(resultado_diff.stdout, "")

    def test_descarte_archivo_eliminado_sin_preparar(self):
        """
        Un archivo " D" recupera su contenido desde el índice.
        """

        self._crear_commit_inicial()

        (
            self.ruta_repositorio / "archivo.txt"
        ).unlink()

        resultado = self.servicio.descartar_cambios_sin_preparar(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(
            self._contenido_archivo("archivo.txt"),
            "linea uno\nlinea dos\nlinea tres\n"
        )

        codigo, salida, _ = self._estado_crudo()
        self.assertEqual(codigo, 0)
        self.assertEqual(salida, "")

    def test_descarte_preparado_y_eliminado_despues(self):
        """
        En el caso MD el restore recupera la versión preparada en el
        working tree y el diff --cached permanece igual.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "version preparada md\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "--",
            "archivo.txt"
        )

        diff_cached_antes = self._diff_cached(
            "archivo.txt"
        )

        (
            self.ruta_repositorio / "archivo.txt"
        ).unlink()

        resultado = self.servicio.descartar_cambios_sin_preparar(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(
            self._contenido_archivo("archivo.txt"),
            "version preparada md\n"
        )

        diff_cached_despues = self._diff_cached(
            "archivo.txt"
        )

        self.assertEqual(
            diff_cached_antes,
            diff_cached_despues
        )

        codigo, salida, _ = self._estado_crudo()
        self.assertEqual(codigo, 0)
        self.assertIn("M ", salida)

    def test_descarte_archivo_nuevo_preparado_y_modificado_am_conserva_staging(self):
        """
        En el caso AM (nuevo preparado y vuelto a modificar) el
        restore utiliza el ÍNDICE, no HEAD: no existe una versión
        del archivo en HEAD y aun así el working tree vuelve a la
        versión preparada conservando el staging.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "nuevo.txt",
            "version preparada\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "--",
            "nuevo.txt"
        )

        self._escribir_archivo(
            "nuevo.txt",
            "version preparada\ncambio posterior\n"
        )

        codigo_estado, salida_estado, _ = self._estado_crudo()
        self.assertEqual(codigo_estado, 0)
        self.assertIn("AM nuevo.txt", salida_estado)

        diff_cached_antes = self._diff_cached(
            "nuevo.txt"
        )

        self.assertTrue(diff_cached_antes)

        resultado = self.servicio.descartar_cambios_sin_preparar(
            str(self.ruta_repositorio),
            "nuevo.txt"
        )

        self.assertTrue(resultado.exitoso)

        self.assertEqual(
            self._contenido_archivo("nuevo.txt"),
            "version preparada\n"
        )

        diff_trabajo = subprocess.run(
            [
                "git",
                "diff",
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--",
                "nuevo.txt",
            ],
            cwd=self.ruta_repositorio,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        self.assertEqual(diff_trabajo.stdout, "")

        diff_cached_despues = self._diff_cached(
            "nuevo.txt"
        )

        self.assertEqual(
            diff_cached_antes,
            diff_cached_despues
        )

        codigo_estado, salida_estado, _ = self._estado_crudo()
        self.assertEqual(codigo_estado, 0)
        self.assertIn("A  nuevo.txt", salida_estado)

    def test_descarte_archivo_nuevo_rechazado(self):
        """
        Un archivo ?? se rechaza con mensaje educativo, sigue
        existiendo y el repositorio no cambia.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "nuevo.txt",
            "contenido nuevo\n"
        )

        estado_antes = self._estado_crudo()

        resultado = self.servicio.descartar_cambios_sin_preparar(
            str(self.ruta_repositorio),
            "nuevo.txt"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "nuevo",
            resultado.error
        )
        self.assertIn(
            "eliminar",
            resultado.error
        )

        self.assertEqual(
            self._contenido_archivo("nuevo.txt"),
            "contenido nuevo\n"
        )

        estado_despues = self._estado_crudo()

        self.assertEqual(
            estado_antes,
            estado_despues
        )

    def test_descarte_archivo_nuevo_sin_ejecutar_restore(self):
        """
        Para un archivo ?? el spy demuestra que NO se ejecuta
        ningún comando Git: cero llamadas.
        """

        espia = ServicioGitEspiaDescarte(
            cambios=[
                CambioArchivo(
                    ruta="nuevo.txt",
                    estado_indice="?",
                    estado_trabajo="?",
                    descripcion="Nuevo",
                    preparado=False
                )
            ]
        )

        servicio = ServicioDescarteCambiosGit(
            espia
        )

        resultado = servicio.descartar_cambios_sin_preparar(
            "c:/repositorio",
            "nuevo.txt"
        )

        self.assertFalse(resultado.exitoso)
        self.assertEqual(
            espia.llamadas_ejecutar_git,
            []
        )

    def test_descarte_archivo_solamente_preparado_rechazado(self):
        """
        Un archivo solamente preparado (M ) se rechaza porque no
        tiene cambios sin preparar y el índice permanece intacto.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "version preparada solamente\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "--",
            "archivo.txt"
        )

        diff_cached_antes = self._diff_cached(
            "archivo.txt"
        )

        resultado = self.servicio.descartar_cambios_sin_preparar(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "no tiene cambios sin preparar",
            resultado.error
        )

        self.assertEqual(
            diff_cached_antes,
            self._diff_cached("archivo.txt")
        )

    def test_descarte_solamente_preparado_sin_ejecutar_restore(self):
        """
        Para un archivo "M " el spy demuestra que NO se ejecuta
        ningún comando Git: cero llamadas.
        """

        espia = ServicioGitEspiaDescarte(
            cambios=[
                CambioArchivo(
                    ruta="archivo.txt",
                    estado_indice="M",
                    estado_trabajo=" ",
                    descripcion="Modificado y preparado",
                    preparado=True
                )
            ]
        )

        servicio = ServicioDescarteCambiosGit(
            espia
        )

        resultado = servicio.descartar_cambios_sin_preparar(
            "c:/repositorio",
            "archivo.txt"
        )

        self.assertFalse(resultado.exitoso)
        self.assertEqual(
            espia.llamadas_ejecutar_git,
            []
        )

    def test_descarte_ruta_con_nul_rechazada_sin_comandos(self):
        """
        Una ruta con NUL se rechaza ANTES de ejecutar restore:
        el spy registra cero llamadas.
        """

        espia = ServicioGitEspiaDescarte(
            cambios=[]
        )

        servicio = ServicioDescarteCambiosGit(
            espia
        )

        resultado = servicio.descartar_cambios_sin_preparar(
            "c:/repositorio",
            "archivo\x00malo.txt"
        )

        self.assertFalse(resultado.exitoso)
        self.assertTrue(resultado.error)
        self.assertEqual(
            espia.llamadas_ejecutar_git,
            []
        )

    def test_descarte_ruta_absoluta_rechazada(self):
        """
        Una ruta absoluta se rechaza antes de ejecutar Git.
        """

        espia = ServicioGitEspiaDescarte(
            cambios=[]
        )

        servicio = ServicioDescarteCambiosGit(
            espia
        )

        ruta_absoluta = (
            Path(Path.cwd().anchor)
            / "fuera"
            / "archivo.txt"
        )

        resultado = servicio.descartar_cambios_sin_preparar(
            "c:/repositorio",
            str(ruta_absoluta)
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "relativas",
            resultado.error
        )
        self.assertEqual(
            espia.llamadas_ejecutar_git,
            []
        )

    def test_descarte_ruta_con_puntos_rechazada(self):
        """
        Una ruta con un componente ".." se rechaza antes de
        ejecutar Git.
        """

        espia = ServicioGitEspiaDescarte(
            cambios=[]
        )

        servicio = ServicioDescarteCambiosGit(
            espia
        )

        resultado = servicio.descartar_cambios_sin_preparar(
            "c:/repositorio",
            "carpeta/../afuera.txt"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "salir",
            resultado.error
        )
        self.assertEqual(
            espia.llamadas_ejecutar_git,
            []
        )

    def test_descarte_nombre_con_guion_y_caracteres_literal(self):
        """
        Un archivo cuyo nombre empieza por guión y contiene
        caracteres especiales se trata como pathspec literal:
        --literal-pathspecs y "--" preceden a la ruta, y con Git
        real el descarte funciona.
        """

        ruta_con_globs = "-servicio[1].txt"

        espia = ServicioGitEspiaDescarte(
            cambios=[
                CambioArchivo(
                    ruta=ruta_con_globs,
                    estado_indice=" ",
                    estado_trabajo="M",
                    descripcion="Modificado",
                    preparado=False
                )
            ]
        )

        servicio = ServicioDescarteCambiosGit(
            espia
        )

        resultado = servicio.descartar_cambios_sin_preparar(
            "c:/repositorio",
            ruta_con_globs
        )

        self.assertTrue(resultado.exitoso)

        self.assertEqual(
            espia.llamadas_ejecutar_git,
            [
                [
                    "--literal-pathspecs",
                    "restore",
                    "--worktree",
                    "--",
                    ruta_con_globs,
                ]
            ]
        )

        self._crear_commit_inicial(
            nombre=ruta_con_globs
        )

        self._escribir_archivo(
            ruta_con_globs,
            "version modificada\n"
        )

        resultado = self.servicio.descartar_cambios_sin_preparar(
            str(self.ruta_repositorio),
            ruta_con_globs
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(
            self._contenido_archivo(ruta_con_globs),
            "linea uno\nlinea dos\nlinea tres\n"
        )

    def test_descarte_argumentos_exactos_del_restore(self):
        """
        El comando ejecutado es exactamente:
        --literal-pathspecs restore --worktree -- <ruta>
        """

        espia = ServicioGitEspiaDescarte(
            cambios=[
                CambioArchivo(
                    ruta="servicio_git.py",
                    estado_indice=" ",
                    estado_trabajo="M",
                    descripcion="Modificado",
                    preparado=False
                )
            ]
        )

        servicio = ServicioDescarteCambiosGit(
            espia
        )

        resultado = servicio.descartar_cambios_sin_preparar(
            "c:/repositorio",
            "servicio_git.py"
        )

        self.assertTrue(resultado.exitoso)

        self.assertEqual(
            espia.llamadas_ejecutar_git,
            [
                [
                    "--literal-pathspecs",
                    "restore",
                    "--worktree",
                    "--",
                    "servicio_git.py",
                ]
            ]
        )

    def test_descarte_verbos_prohibidos_nunca_ejecutados(self):
        """
        Se identifica el VERBO Git real de cada llamada: aunque un
        archivo se llame "reset", el único verbo ejecutado es
        restore y "reset" aparece solamente como pathspec.
        """

        espia = ServicioGitEspiaDescarte(
            cambios=[
                CambioArchivo(
                    ruta="reset",
                    estado_indice=" ",
                    estado_trabajo="M",
                    descripcion="Modificado",
                    preparado=False
                )
            ]
        )

        servicio = ServicioDescarteCambiosGit(
            espia
        )

        resultado = servicio.descartar_cambios_sin_preparar(
            "c:/repositorio",
            "reset"
        )

        self.assertTrue(resultado.exitoso)

        verbos_prohibidos = {
            "add",
            "commit",
            "reset",
            "checkout",
            "clean",
            "rm",
            "mv",
            "stash",
            "rebase",
            "merge",
            "revert",
            "cherry-pick",
            "fetch",
            "pull",
            "push",
        }

        self.assertEqual(
            espia.llamadas_ejecutar_git,
            [
                [
                    "--literal-pathspecs",
                    "restore",
                    "--worktree",
                    "--",
                    "reset",
                ]
            ]
        )

        for llamada in espia.llamadas_ejecutar_git:
            if llamada[0] == "--literal-pathspecs":
                verbo = llamada[1]
            else:
                verbo = llamada[0]

            self.assertEqual(verbo, "restore")
            self.assertNotIn(
                verbo,
                verbos_prohibidos
            )

    def test_descarte_otro_archivo_conserva_sus_cambios(self):
        """
        Al descartar solamente el archivo A, el archivo B conserva
        exactamente sus cambios sin preparar.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "cambios de A\n"
        )

        self._escribir_archivo(
            "otro.txt",
            "cambios de B\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "--",
            "otro.txt"
        )

        self._ejecutar_git_repositorio(
            "commit",
            "-m",
            "Agrega otro.txt"
        )

        self._escribir_archivo(
            "otro.txt",
            "cambios de B modificados\n"
        )

        resultado = self.servicio.descartar_cambios_sin_preparar(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(
            self._contenido_archivo("archivo.txt"),
            "linea uno\nlinea dos\nlinea tres\n"
        )

        self.assertEqual(
            self._contenido_archivo("otro.txt"),
            "cambios de B modificados\n"
        )

        codigo, salida, _ = self._estado_crudo()
        self.assertEqual(codigo, 0)
        self.assertIn(" M otro.txt", salida)
        self.assertNotIn("archivo.txt", salida)

    def test_descarte_conflicto_rechazado_sin_restore(self):
        """
        Un estado de conflicto (UU) se rechaza con mensaje
        educativo y no se ejecuta ningún comando Git.
        """

        espia = ServicioGitEspiaDescarte(
            cambios=[
                CambioArchivo(
                    ruta="archivo.txt",
                    estado_indice="U",
                    estado_trabajo="U",
                    descripcion="Conflicto",
                    preparado=False
                )
            ]
        )

        servicio = ServicioDescarteCambiosGit(
            espia
        )

        resultado = servicio.descartar_cambios_sin_preparar(
            "c:/repositorio",
            "archivo.txt"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "conflicto",
            resultado.error.lower()
        )
        self.assertEqual(
            espia.llamadas_ejecutar_git,
            []
        )


if __name__ == "__main__":
    unittest.main()