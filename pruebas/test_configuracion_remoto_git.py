import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from servicio_remoto_git import ServicioRemotoGit


class PruebasConfiguracionRemotoGit(unittest.TestCase):
    """
    Pruebas de la configuración inicial del remoto origin.

    Todas las pruebas utilizan repositorios temporales y
    nunca contactan a GitHub ni a Internet.
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
            "Usuario Configuracion"
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "config",
            "user.email",
            "configuracion@example.com"
        )

        self.servicio = ServicioRemotoGit()

    def tearDown(self):
        self.temporal.cleanup()

    def test_agregar_remoto_github_configura_origin(self):
        """Configura origin con una URL HTTPS válida de GitHub."""

        url_github = (
            "https://github.com/usuario/repositorio"
        )

        resultado = self.servicio.agregar_remoto_github(
            str(self.ruta_repositorio),
            url_github
        )

        self.assertTrue(
            resultado.exitoso,
            resultado.error
        )

        url_configurada = self._obtener_url_remoto(
            "origin"
        )

        self.assertEqual(
            url_github,
            url_configurada
        )

    def test_agregar_remoto_github_rechaza_url_vacia(self):
        """Una URL vacía debe rechazarse."""

        resultado = self.servicio.agregar_remoto_github(
            str(self.ruta_repositorio),
            "   "
        )

        self.assertFalse(resultado.exitoso)
        self.assertNotEqual("", resultado.error)

        self.assertEqual(
            [],
            self._obtener_remotos()
        )

    def test_agregar_remoto_github_rechaza_http(self):
        """HTTP no debe aceptarse, aunque el host sea github.com."""

        resultado = self.servicio.agregar_remoto_github(
            str(self.ruta_repositorio),
            "http://github.com/usuario/repositorio.git"
        )

        self.assertFalse(resultado.exitoso)
        self.assertNotEqual("", resultado.error)

        self.assertEqual(
            [],
            self._obtener_remotos()
        )

    def test_agregar_remoto_github_rechaza_otro_host(self):
        """Un host distinto de github.com debe rechazarse."""

        resultado = self.servicio.agregar_remoto_github(
            str(self.ruta_repositorio),
            "https://example.com/usuario/repositorio.git"
        )

        self.assertFalse(resultado.exitoso)
        self.assertNotEqual("", resultado.error)

        self.assertEqual(
            [],
            self._obtener_remotos()
        )

    def test_agregar_remoto_github_rechaza_credenciales_en_url(self):
        """
        Las URLs con usuario o contraseña deben rechazarse.

        La aplicación nunca debe recibir ni almacenar PAT,
        token o contraseña dentro de la URL.
        """

        resultado = self.servicio.agregar_remoto_github(
            str(self.ruta_repositorio),
            "https://usuario:token@github.com/usuario/repositorio.git"
        )

        self.assertFalse(resultado.exitoso)
        self.assertNotEqual("", resultado.error)

        # El remoto no debe haber sido creado.
        self.assertEqual(
            [],
            self._obtener_remotos()
        )

    def test_agregar_remoto_github_rechaza_si_ya_existe_remoto(self):
        """
        Si el repositorio ya tiene un remoto, no debe modificarlo.

        Ni siquiera cuando el remoto existente se llama origin
        y la URL es válida.
        """

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "remote",
            "add",
            "origin",
            "https://github.com/original/origen.git"
        )

        resultado = self.servicio.agregar_remoto_github(
            str(self.ruta_repositorio),
            "https://github.com/nuevo/repositorio.git"
        )

        self.assertFalse(resultado.exitoso)
        self.assertNotEqual("", resultado.error)

        # La configuración existente debe conservarse intacta.
        self.assertEqual(
            ["origin"],
            self._obtener_remotos()
        )

        url_original = self._obtener_url_remoto(
            "origin"
        )

        self.assertEqual(
            "https://github.com/original/origen.git",
            url_original
        )

    def test_agregar_remoto_github_no_necesita_contactar_el_remoto(self):
        """
        remote add funciona sin acceder a la red.

        Aunque el repositorio no exista en GitHub, la configuración
        local debe completarse porque solamente modifica .git/config.
        """

        url_inexistente = (
            "https://github.com/gestorgit-pruebas/"
            "repositorio-deliberadamente-inexistente.git"
        )

        resultado = self.servicio.agregar_remoto_github(
            str(self.ruta_repositorio),
            url_inexistente
        )

        self.assertTrue(
            resultado.exitoso,
            resultado.error
        )

        url_configurada = self._obtener_url_remoto(
            "origin"
        )

        self.assertEqual(
            url_inexistente,
            url_configurada
        )

    # ---------------------------------------------------------
    # Ayudantes
    # ---------------------------------------------------------

    def _obtener_remotos(self):
        """
        Devuelve la lista de remotos configurados.
        """

        resultado = self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "remote"
        )

        return [
            linea.strip()
            for linea in resultado.stdout.splitlines()
            if linea.strip()
        ]

    def _obtener_url_remoto(self, nombre_remoto):
        """
        Devuelve la URL exacta configurada para un remoto.
        """

        resultado = self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "remote",
            "get-url",
            nombre_remoto
        )

        return resultado.stdout.rstrip("\r\n")

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
