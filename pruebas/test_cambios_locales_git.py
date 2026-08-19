"""
Pruebas del inspector de cambios locales (solo lectura).

Cubren la consulta estructurada de los cambios de un archivo
en las zonas working tree / índice / HEAD:

- diffs sin preparar y preparados;
- resúmenes mediante --numstat;
- archivos nuevos sin preparar y archivos eliminados;
- seguridad de rutas y de argumentos de Git.

Utilizan exclusivamente carpetas temporales:
nunca tocan GitHub ni los repositorios reales.
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
from servicio_cambios_locales_git import ServicioCambiosLocalesGit
from servicio_git import ServicioGit


class ServicioGitEspia:
    """
    Sustituto de ServicioGit para pruebas.

    Registra las llamadas a ejecutar_git sin ejecutar Git real y
    devuelve resultados controlados para que el flujo del servicio
    llegue a construir los diffs.
    """

    def __init__(self, ruta_cambio="servicio_git.py"):
        self.ruta_cambio = ruta_cambio
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
            cambios=[
                CambioArchivo(
                    ruta=self.ruta_cambio,
                    estado_indice="M",
                    estado_trabajo="M",
                    descripcion="Modificado, preparado y vuelto a modificar",
                    preparado=True,
                    requiere_actualizar_preparado=True
                )
            ]
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
            salida="salida de prueba",
            error="",
            comando=""
        )


class TestCambiosLocalesGit(unittest.TestCase):
    """
    Pruebas del inspector de cambios locales.
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
            "Usuario Cambios Locales"
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "config",
            "user.email",
            "cambioslocales@example.com"
        )

        self.servicio = ServicioCambiosLocalesGit(
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

    def _crear_commit_inicial(self):
        """
        Crea un commit inicial con un archivo de prueba.
        """

        self._escribir_archivo(
            "archivo.txt",
            "linea uno\nlinea dos\nlinea tres\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
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

    def test_archivo_modificado_solamente_sin_preparar(self):
        """
        Un archivo modificado sin preparar muestra su diff en
        "sin preparar" y deja vacío el diff preparado.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "linea uno cambiada\nlinea dos\nlinea tres\n"
        )

        resultado = self.servicio.obtener_detalle(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertIsNotNone(resultado.detalle)
        self.assertFalse(resultado.detalle.preparado)
        self.assertTrue(resultado.detalle.diff_sin_preparar)
        self.assertEqual(resultado.detalle.diff_preparado, "")
        self.assertFalse(resultado.detalle.nuevo_sin_preparar)

    def test_archivo_solamente_preparado(self):
        """
        Un archivo solamente preparado muestra su diff en
        "preparados" y deja vacío el diff sin preparar.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "linea uno\nlinea dos\nlinea tres nueva\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        resultado = self.servicio.obtener_detalle(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertTrue(resultado.detalle.preparado)
        self.assertEqual(resultado.detalle.diff_sin_preparar, "")
        self.assertTrue(resultado.detalle.diff_preparado)

    def test_archivo_preparado_y_vuelto_a_modificar(self):
        """
        En el caso MM (preparado y vuelto a modificar) ambos
        diffs existen y contienen información distinta.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "version preparada\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        self._escribir_archivo(
            "archivo.txt",
            "version del working tree\n"
        )

        resultado = self.servicio.obtener_detalle(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertTrue(resultado.detalle.preparado)
        self.assertTrue(resultado.detalle.requiere_actualizar_preparado)
        self.assertTrue(resultado.detalle.diff_preparado)
        self.assertTrue(resultado.detalle.diff_sin_preparar)
        self.assertNotEqual(
            resultado.detalle.diff_preparado,
            resultado.detalle.diff_sin_preparar
        )

    def test_resumen_inserciones_eliminaciones_numstat(self):
        """
        Los resúmenes de inserciones y eliminaciones se calculan
        mediante --numstat en ambas zonas.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "linea uno\nlinea extra 1\nlinea extra 2\nlinea tres\n"
        )

        resultado = self.servicio.obtener_detalle(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(
            resultado.detalle.inserciones_sin_preparar,
            2
        )

        self.assertEqual(
            resultado.detalle.eliminaciones_sin_preparar,
            1
        )

        self.assertFalse(
            resultado.detalle.binario_sin_preparar
        )

        self.assertEqual(
            resultado.detalle.inserciones_preparadas,
            0
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        self._escribir_archivo(
            "archivo.txt",
            "linea uno\nlinea extra 1\nlinea extra 2\nlinea tres final\n"
        )

        resultado = self.servicio.obtener_detalle(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertEqual(
            resultado.detalle.inserciones_preparadas,
            2
        )

        self.assertEqual(
            resultado.detalle.eliminaciones_preparadas,
            1
        )

        self.assertEqual(
            resultado.detalle.inserciones_sin_preparar,
            1
        )

        self.assertEqual(
            resultado.detalle.eliminaciones_sin_preparar,
            1
        )

    def test_archivo_nuevo_sin_preparar_educativo(self):
        """
        Un archivo nuevo sin preparar (??) es un resultado normal:
        se marca como nuevo y no se inventa ningún diff.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "nuevo.txt",
            "contenido nuevo\n"
        )

        resultado = self.servicio.obtener_detalle(
            str(self.ruta_repositorio),
            "nuevo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertTrue(resultado.detalle.nuevo_sin_preparar)
        self.assertEqual(resultado.detalle.diff_sin_preparar, "")
        self.assertEqual(resultado.detalle.diff_preparado, "")

    def test_archivo_eliminado_muestra_diff(self):
        """
        Un archivo eliminado muestra su diff sin excepciones.
        """

        self._crear_commit_inicial()

        (
            self.ruta_repositorio / "archivo.txt"
        ).unlink()

        resultado = self.servicio.obtener_detalle(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertTrue(resultado.detalle.diff_sin_preparar)
        self.assertIn(
            "-",
            resultado.detalle.diff_sin_preparar
        )

    def test_rechazo_ruta_con_nul_antes_de_ejecutar_diff(self):
        """
        Una ruta con NUL se rechaza antes de construir o ejecutar
        cualquier diff: el registro de llamadas queda vacío.
        """

        espia = ServicioGitEspia()

        servicio = ServicioCambiosLocalesGit(
            espia
        )

        resultado = servicio.obtener_detalle(
            "c:/repositorio",
            "archivo\x00malo.txt"
        )

        self.assertFalse(resultado.exitoso)
        self.assertTrue(resultado.error)
        self.assertEqual(
            espia.llamadas_ejecutar_git,
            []
        )

    def test_ruta_con_globs_y_guion_tratada_literal(self):
        """
        Una ruta con caracteres especiales o que empieza por guión
        se trata literalmente: aparece completa después de "--"
        en los argumentos del diff.
        """

        ruta_con_globs = "-servicio[1].txt"

        espia = ServicioGitEspia(
            ruta_cambio=ruta_con_globs
        )

        servicio = ServicioCambiosLocalesGit(
            espia
        )

        resultado = servicio.obtener_detalle(
            "c:/repositorio",
            ruta_con_globs
        )

        self.assertTrue(resultado.exitoso)

        diffs = [
            llamada
            for llamada in espia.llamadas_ejecutar_git
            if "diff" in llamada
        ]

        self.assertTrue(diffs)

        for llamada in diffs:
            indice_separador = llamada.index("--")
            self.assertEqual(
                llamada[indice_separador + 1],
                ruta_con_globs
            )

        # Con Git real un archivo cuyo nombre empieza por guión
        # también se consulta correctamente.
        self._crear_commit_inicial()

        self._escribir_archivo(
            "-guion.txt",
            "contenido\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "--",
            "-guion.txt"
        )

        self._ejecutar_git_repositorio(
            "commit",
            "-m",
            "Commit con guion"
        )

        self._escribir_archivo(
            "-guion.txt",
            "contenido modificado\n"
        )

        resultado = self.servicio.obtener_detalle(
            str(self.ruta_repositorio),
            "-guion.txt"
        )

        self.assertTrue(resultado.exitoso)
        self.assertTrue(resultado.detalle.diff_sin_preparar)

    def test_comandos_seguros_y_argumentos_esperados(self):
        """
        Todos los diffs usan --literal-pathspecs, --no-color,
        --no-ext-diff, --no-textconv y "--"; el preparado incluye
        --cached; nunca se ejecuta un comando destructivo.
        """

        espia = ServicioGitEspia()

        servicio = ServicioCambiosLocalesGit(
            espia
        )

        resultado = servicio.obtener_detalle(
            "c:/repositorio",
            "servicio_git.py"
        )

        self.assertTrue(resultado.exitoso)
        self.assertTrue(espia.llamadas_ejecutar_git)

        diff_sin_preparar = [
            "--literal-pathspecs",
            "diff",
            "--no-color",
            "--no-ext-diff",
            "--no-textconv",
            "--unified=3",
            "--",
            "servicio_git.py",
        ]

        self.assertIn(
            diff_sin_preparar,
            espia.llamadas_ejecutar_git
        )

        diff_preparado = [
            "--literal-pathspecs",
            "diff",
            "--cached",
            "--no-color",
            "--no-ext-diff",
            "--no-textconv",
            "--unified=3",
            "--",
            "servicio_git.py",
        ]

        self.assertIn(
            diff_preparado,
            espia.llamadas_ejecutar_git
        )

        numstat_sin_preparar = [
            "--literal-pathspecs",
            "diff",
            "--numstat",
            "--no-ext-diff",
            "--no-textconv",
            "--",
            "servicio_git.py",
        ]

        self.assertIn(
            numstat_sin_preparar,
            espia.llamadas_ejecutar_git
        )

        numstat_preparado = [
            "--literal-pathspecs",
            "diff",
            "--cached",
            "--numstat",
            "--no-ext-diff",
            "--no-textconv",
            "--",
            "servicio_git.py",
        ]

        self.assertIn(
            numstat_preparado,
            espia.llamadas_ejecutar_git
        )

        comandos_destructivos = {
            "add",
            "commit",
            "reset",
            "restore",
            "checkout",
            "fetch",
            "pull",
            "push",
            "clean",
            "branch",
            "rm",
            "mv",
            "stash",
            "rebase",
            "merge",
            "revert",
            "cherry-pick",
            "tag",
            "gc",
            "prune",
        }

        comandos_consultas = {
            "diff",
            "rev-parse",
            "log",
        }

        for llamada in espia.llamadas_ejecutar_git:
            for parte in llamada:
                self.assertNotIn(
                    parte,
                    comandos_destructivos
                )

            if llamada[0] == "--literal-pathspecs":
                primer_comando = llamada[1]
            else:
                primer_comando = llamada[0]

            self.assertIn(
                primer_comando,
                comandos_consultas
            )

        for llamada in espia.llamadas_ejecutar_git:
            if "diff" not in llamada:
                continue

            self.assertIn("--", llamada)

            indice_separador = llamada.index("--")

            self.assertEqual(
                llamada[indice_separador + 1],
                "servicio_git.py"
            )

    def test_consulta_no_modifica_repositorio(self):
        """
        Consultar el inspector deja el repositorio exactamente
        igual: el estado antes y después es idéntico.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "primera modificacion\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        self._escribir_archivo(
            "archivo.txt",
            "segunda modificacion\n"
        )

        estado_antes = self._estado_crudo()

        resultado = self.servicio.obtener_detalle(
            str(self.ruta_repositorio),
            "archivo.txt"
        )

        self.assertTrue(resultado.exitoso)

        estado_despues = self._estado_crudo()

        self.assertEqual(
            estado_antes,
            estado_despues
        )


if __name__ == "__main__":
    unittest.main()