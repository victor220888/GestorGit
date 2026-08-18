import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from servicio_historial_git import ServicioHistorialGit


class PruebasDetalleCommitGit(unittest.TestCase):
    """
    Pruebas del visor de cambios de un commit (solo lectura).
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
            "Usuario Detalle"
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "config",
            "user.email",
            "detalle@example.com"
        )

        self.servicio = ServicioHistorialGit()

    def tearDown(self):
        self.temporal.cleanup()

    def test_obtener_cambios_commit_muestra_archivo_agregado(self):
        """
        Un commit con archivo nuevo debe mostrar diff --git
        y la línea agregada esperada.
        """

        self._crear_commit(
            "nuevo.sql",
            "CREATE TABLE prueba (id NUMBER);\n",
            "Agrega tabla de prueba"
        )

        hash_commit = self._hash_head()

        resultado = self.servicio.obtener_cambios_commit(
            str(self.ruta_repositorio),
            hash_commit
        )

        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertIn("diff --git", resultado.salida)
        self.assertIn(
            "+CREATE TABLE prueba (id NUMBER);",
            resultado.salida
        )

    def test_obtener_cambios_commit_muestra_modificacion(self):
        """
        Un commit que modifica una línea debe mostrar
        la línea eliminada y la línea agregada.
        """

        self._crear_commit(
            "consulta.sql",
            "SELECT 1;\n",
            "Agrega consulta inicial"
        )

        self._crear_commit(
            "consulta.sql",
            "SELECT 2;\n",
            "Modifica consulta"
        )

        hash_commit = self._hash_head()

        resultado = self.servicio.obtener_cambios_commit(
            str(self.ruta_repositorio),
            hash_commit
        )

        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertIn("-SELECT 1;", resultado.salida)
        self.assertIn("+SELECT 2;", resultado.salida)

    def test_obtener_cambios_commit_no_modifica_repositorio(self):
        """
        Consultar los cambios de un commit no debe alterar
        el estado del repositorio.
        """

        self._crear_commit(
            "estable.sql",
            "SELECT 3;\n",
            "Agrega consulta estable"
        )

        self._crear_commit(
            "estable.sql",
            "SELECT 4;\n",
            "Modifica consulta estable"
        )

        hash_commit = self._hash_head()

        status_antes = self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "status",
            "--porcelain"
        )

        resultado = self.servicio.obtener_cambios_commit(
            str(self.ruta_repositorio),
            hash_commit
        )

        self.assertTrue(resultado.exitoso, resultado.error)

        status_despues = self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "status",
            "--porcelain"
        )

        self.assertEqual(
            status_antes.stdout,
            status_despues.stdout
        )

    def test_obtener_cambios_commit_rechaza_hash_invalido(self):
        """
        Los hashes inválidos deben rechazarse sin ejecutar git show.
        """

        hashes_invalidos = [
            "",
            "../../archivo",
            "--help",
            "xyz",
            "ruta\nmaliciosa"
        ]

        for hash_invalido in hashes_invalidos:
            with self.subTest(hash_invalido=hash_invalido):
                resultado = self.servicio.obtener_cambios_commit(
                    str(self.ruta_repositorio),
                    hash_invalido
                )

                self.assertFalse(resultado.exitoso)
                self.assertEqual("", resultado.comando)
                self.assertNotIn("show", resultado.comando)

    def test_obtener_cambios_commit_rechaza_hash_inexistente(self):
        """
        Un hash hexadecimal válido pero inexistente debe
        devolver un error controlado.
        """

        self._crear_commit(
            "base.sql",
            "SELECT 5;\n",
            "Agrega consulta base"
        )

        hash_inexistente = "a" * 40

        resultado = self.servicio.obtener_cambios_commit(
            str(self.ruta_repositorio),
            hash_inexistente
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "no corresponde a un commit",
            resultado.error
        )

    def test_obtener_cambios_commit_no_utiliza_diff_externo(self):
        """
        La consulta debe usar git show con --no-ext-diff,
        --no-textconv y --no-color, y no contener comandos
        destructivos.
        """

        self._crear_commit(
            "seguro.sql",
            "SELECT 6;\n",
            "Agrega consulta segura"
        )

        hash_commit = self._hash_head()

        resultado = self.servicio.obtener_cambios_commit(
            str(self.ruta_repositorio),
            hash_commit
        )

        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertIn("show", resultado.comando)
        self.assertIn("--no-ext-diff", resultado.comando)
        self.assertIn("--no-textconv", resultado.comando)
        self.assertIn("--no-color", resultado.comando)

        comando_minusculas = resultado.comando.lower()

        for comando_destructivo in (
            "reset",
            "revert",
            "checkout",
            "merge",
            "rebase",
            "cherry-pick",
            "push",
            "pull",
            "fetch",
            "clean",
            "commit"
        ):
            self.assertNotIn(
                comando_destructivo,
                comando_minusculas
            )

    def _crear_commit(
        self,
        nombre_archivo,
        contenido,
        mensaje
    ):
        """Crea un commit temporal para una prueba."""

        ruta_archivo = (
            self.ruta_repositorio
            / nombre_archivo
        )

        ruta_archivo.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        ruta_archivo.write_text(
            contenido,
            encoding="utf-8"
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "add",
            "--",
            nombre_archivo
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "commit",
            "-m",
            mensaje
        )

    def _hash_head(self):
        """Devuelve el hash completo del último commit."""

        resultado = self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "rev-parse",
            "HEAD"
        )

        return resultado.stdout.strip()

    @staticmethod
    def _ejecutar_git(*argumentos):
        """Ejecuta Git solamente para preparar escenarios de prueba."""

        resultado = subprocess.run(
            ["git", *argumentos],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=os.environ.copy()
        )

        if resultado.returncode != 0:
            detalle = (
                resultado.stderr
                if resultado.stderr
                else resultado.stdout
            )

            raise AssertionError(
                f"Falló Git durante la prueba:\n{detalle}"
            )

        return resultado


if __name__ == "__main__":
    unittest.main()