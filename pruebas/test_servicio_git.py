import tempfile
import unittest
from pathlib import Path

from servicio_git import ServicioGit


class PruebasServicioGit(unittest.TestCase):
    """
    Pruebas automáticas del servicio encargado de Git.
    """

    def test_git_esta_disponible(self):
        """Comprueba que git.exe pueda encontrarse."""

        servicio_git = ServicioGit()

        self.assertTrue(
            servicio_git.git_disponible(),
            "Git debería estar disponible en el sistema."
        )

    def test_obtener_version_git(self):
        """Comprueba que podamos ejecutar git --version."""

        servicio_git = ServicioGit()

        resultado = servicio_git.obtener_version()

        self.assertTrue(
            resultado.exitoso,
            resultado.error
        )

        self.assertIn(
            "git version",
            resultado.salida.lower()
        )

    def test_carpeta_normal_no_es_repositorio(self):
        """
        Comprueba que una carpeta común no sea confundida
        con un repositorio Git.
        """

        servicio_git = ServicioGit()

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            estado = servicio_git.analizar_repositorio(
                carpeta_temporal
            )

            self.assertFalse(
                estado.es_repositorio
            )

    def test_repositorio_vacio_es_detectado(self):
        """
        Crea un repositorio Git temporal y comprueba que
        pueda detectarse aunque todavía no tenga commits.
        """

        servicio_git = ServicioGit()

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            # Creamos únicamente un repositorio de prueba temporal.
            resultado_init = servicio_git.ejecutar_git(
                argumentos=["init"],
                ruta_repositorio=ruta_temporal
            )

            self.assertTrue(
                resultado_init.exitoso,
                resultado_init.error
            )

            estado = servicio_git.analizar_repositorio(
                ruta_temporal
            )

            self.assertTrue(
                estado.es_repositorio
            )

            self.assertFalse(
                estado.tiene_commits
            )

            self.assertNotEqual(
                estado.ruta_raiz,
                ""
            )

            self.assertNotEqual(
                estado.rama_actual,
                ""
            )


if __name__ == "__main__":
    unittest.main()