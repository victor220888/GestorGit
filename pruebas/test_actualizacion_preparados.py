"""
Pruebas de la actualización de archivos preparados.

Cubren el escenario real:
"archivo preparado y vuelto a modificar después".

Utilizan exclusivamente carpetas temporales:
nunca tocan GitHub ni los repositorios reales.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from servicio_git import ServicioGit


class TestActualizacionPreparados(unittest.TestCase):
    """
    Pruebas de detección y actualización de archivos
    con staging desactualizado.
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
            "Usuario Actualización"
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "config",
            "user.email",
            "actualizacion@example.com"
        )

        self.servicio = ServicioGit()

    def tearDown(self):
        self.temporal.cleanup()

    def _ejecutar_git(self, *argumentos):
        """
        Ejecuta Git dentro del repositorio temporal.
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
            "primera versión\n"
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

    def _obtener_cambio(self, ruta_archivo):
        """
        Obtiene el CambioArchivo correspondiente a una ruta.
        """

        resultado = self.servicio.obtener_cambios(
            str(self.ruta_repositorio)
        )

        self.assertTrue(resultado.exitoso)

        for cambio in resultado.cambios:
            if cambio.ruta == ruta_archivo:
                return cambio

        self.fail(
            f"No se encontró el cambio para: {ruta_archivo}"
        )

    def _contenido_staged(self, ruta_archivo):
        """
        Devuelve el diff de un archivo según el índice.
        """

        resultado = subprocess.run(
            ["git", "diff", "--cached", "--", ruta_archivo],
            cwd=self.ruta_repositorio,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return resultado.stdout

    def _contenido_unstaged(self, ruta_archivo):
        """
        Devuelve el diff de un archivo según el working tree.
        """

        resultado = subprocess.run(
            ["git", "diff", "--", ruta_archivo],
            cwd=self.ruta_repositorio,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return resultado.stdout

    def test_detecta_archivo_preparado_y_modificado_despues(self):
        """
        Un archivo preparado y luego modificado debe marcarse
        como pendiente de actualización.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "segunda versión\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        self._escribir_archivo(
            "archivo.txt",
            "tercera versión\n"
        )

        cambio = self._obtener_cambio(
            "archivo.txt"
        )

        self.assertTrue(cambio.preparado)
        self.assertTrue(cambio.requiere_actualizar_preparado)

    def test_actualizar_preparado_incluye_version_actual(self):
        """
        Actualizar un archivo preparado debe dejar en el índice
        la versión actual completa.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "segunda versión\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        self._escribir_archivo(
            "archivo.txt",
            "tercera versión\n"
        )

        resultado = (
            self.servicio.actualizar_archivos_preparados(
                str(self.ruta_repositorio),
                ["archivo.txt"]
            )
        )

        self.assertTrue(resultado.exitoso)

        # Ya no quedan cambios sin preparar para ese archivo.
        self.assertEqual(
            self._contenido_unstaged("archivo.txt"),
            ""
        )

        # El índice contiene la versión final.
        self.assertIn(
            "tercera versión",
            self._contenido_staged("archivo.txt")
        )

        cambio = self._obtener_cambio(
            "archivo.txt"
        )

        self.assertTrue(cambio.preparado)
        self.assertFalse(cambio.requiere_actualizar_preparado)

    def test_actualizar_varios_archivos_preparados(self):
        """
        Actualización múltiple de archivos preparados
        y modificados después.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "segunda versión\n"
        )

        self._escribir_archivo(
            "otro.txt",
            "primera versión\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt",
            "otro.txt"
        )

        self._ejecutar_git_repositorio(
            "commit",
            "-m",
            "Segundo commit"
        )

        self._escribir_archivo(
            "archivo.txt",
            "tercera versión\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        self._escribir_archivo(
            "archivo.txt",
            "cuarta versión\n"
        )

        self._escribir_archivo(
            "otro.txt",
            "segunda versión\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "otro.txt"
        )

        self._escribir_archivo(
            "otro.txt",
            "tercera versión\n"
        )

        resultado = (
            self.servicio.actualizar_archivos_preparados(
                str(self.ruta_repositorio),
                ["archivo.txt", "otro.txt"]
            )
        )

        self.assertTrue(resultado.exitoso)

        for ruta_archivo in ("archivo.txt", "otro.txt"):
            cambio = self._obtener_cambio(
                ruta_archivo
            )

            self.assertTrue(cambio.preparado)
            self.assertFalse(
                cambio.requiere_actualizar_preparado
            )

    def test_actualizar_preparado_rechaza_archivo_no_preparado(self):
        """
        Un archivo modificado solamente en el working tree
        no puede actualizarse con esta operación.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "segunda versión\n"
        )

        resultado = (
            self.servicio.actualizar_archivos_preparados(
                str(self.ruta_repositorio),
                ["archivo.txt"]
            )
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "ya no está preparado",
            resultado.error
        )

        # El índice no fue modificado.
        self.assertEqual(
            self._contenido_staged("archivo.txt"),
            ""
        )

        self.assertNotEqual(
            self._contenido_unstaged("archivo.txt"),
            ""
        )

    def test_actualizar_preparado_rechaza_archivo_sin_cambios_nuevos(self):
        """
        Un archivo preparado sin cambios nuevos fuera del índice
        no requiere actualización.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "segunda versión\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        resultado = (
            self.servicio.actualizar_archivos_preparados(
                str(self.ruta_repositorio),
                ["archivo.txt"]
            )
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "ya no requiere actualización",
            resultado.error
        )

        # El estado preparado se conserva intacto.
        self.assertEqual(
            self._contenido_unstaged("archivo.txt"),
            ""
        )

        cambio = self._obtener_cambio(
            "archivo.txt"
        )

        self.assertTrue(cambio.preparado)
        self.assertFalse(cambio.requiere_actualizar_preparado)

    def test_commit_bloqueado_hasta_actualizar_preparado(self):
        """
        El escenario real: el commit queda bloqueado hasta
        actualizar los archivos preparados.
        """

        self._crear_commit_inicial()

        self._escribir_archivo(
            "archivo.txt",
            "segunda versión\n"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        self._escribir_archivo(
            "archivo.txt",
            "tercera versión\n"
        )

        commit_bloqueado = self.servicio.crear_commit(
            str(self.ruta_repositorio),
            "Nuevo commit"
        )

        self.assertFalse(commit_bloqueado.exitoso)
        self.assertIn(
            "modificados después de haber sido preparados",
            commit_bloqueado.error
        )

        actualizacion = (
            self.servicio.actualizar_archivos_preparados(
                str(self.ruta_repositorio),
                ["archivo.txt"]
            )
        )

        self.assertTrue(actualizacion.exitoso)

        commit_exitoso = self.servicio.crear_commit(
            str(self.ruta_repositorio),
            "Nuevo commit"
        )

        self.assertTrue(commit_exitoso.exitoso)

        resultado_mensaje = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=self.ruta_repositorio,
            check=True,
            capture_output=True,
            text=True
        )

        self.assertEqual(
            resultado_mensaje.stdout.strip(),
            "Nuevo commit"
        )

    def test_actualizar_preparado_rechaza_ruta_con_nul(self):
        """
        Una ruta que contiene un carácter NUL (\x00)
        debe ser rechazada antes de ejecutar git add.

        El resultado debe ser un error controlado,
        no una excepción.
        """

        self._crear_commit_inicial()

        ruta_con_nul = "archivo\x00.txt"

        resultado = (
            self.servicio.actualizar_archivos_preparados(
                str(self.ruta_repositorio),
                [ruta_con_nul]
            )
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "carácter inválido",
            resultado.error
        )

        # Verificar que el índice no fue modificado.
        self.assertEqual(
            self._contenido_staged("archivo.txt"),
            ""
        )


if __name__ == "__main__":
    unittest.main()