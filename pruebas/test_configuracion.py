"""
Pruebas del servicio de configuración de Gestor Git.

Utilizan exclusivamente carpetas temporales: nunca tocan el
config.json real, GitHub ni los repositorios reales.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from servicio_configuracion import ServicioConfiguracion
from servicio_git import ServicioGit


class TestConfiguracion(unittest.TestCase):
    """
    Pruebas de la persistencia del último repositorio.
    """

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta_temporal = Path(
            self.temporal.name
        )

        self.servicio = ServicioConfiguracion(
            servicio_git=ServicioGit(),
            ruta_configuracion=(
                self.ruta_temporal / "config.json"
            )
        )

    def tearDown(self):
        self.temporal.cleanup()

    def _ejecutar_git(self, *argumentos):
        """
        Ejecuta Git dentro de la carpeta temporal.
        """

        return subprocess.run(
            ["git", *argumentos],
            cwd=self.ruta_temporal,
            check=True,
            capture_output=True,
            text=True
        )

    def _crear_repositorio_git(self, nombre="repositorio"):
        """
        Crea un repositorio Git vacío dentro de la carpeta temporal.
        """

        ruta_repositorio = self.ruta_temporal / nombre

        self._ejecutar_git(
            "init",
            "--initial-branch=master",
            str(ruta_repositorio)
        )

        return ruta_repositorio

    def _escribir_configuracion(self, datos):
        """
        Escribe config.json dentro de la carpeta temporal.
        """

        self.servicio.ruta_configuracion.write_text(
            json.dumps(
                datos,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    def test_cargar_configuracion_inexistente_no_falla(self):
        """
        Sin config.json el resultado debe ser exitoso
        con la ruta vacía: es un primer inicio normal.
        """

        resultado = self.servicio.cargar_ultimo_repositorio()

        self.assertTrue(resultado.exitoso)
        self.assertEqual(resultado.ruta_repositorio, "")

    def test_guardar_y_cargar_repositorio_valido(self):
        """
        Guardar y cargar un repositorio válido
        debe conservar la misma ruta.
        """

        repositorio = self._crear_repositorio_git()

        resultado_guardado = (
            self.servicio.guardar_ultimo_repositorio(
                str(repositorio)
            )
        )

        self.assertTrue(resultado_guardado.exitoso)

        resultado_cargado = (
            self.servicio.cargar_ultimo_repositorio()
        )

        self.assertTrue(resultado_cargado.exitoso)

        self.assertEqual(
            Path(resultado_cargado.ruta_repositorio).resolve(),
            repositorio.resolve()
        )

    def test_cargar_configuracion_json_invalido_no_falla(self):
        """
        Un config.json con JSON inválido debe devolver
        un error controlado sin lanzar excepción.
        """

        self.servicio.ruta_configuracion.write_text(
            "{esto no es json",
            encoding="utf-8"
        )

        resultado = self.servicio.cargar_ultimo_repositorio()

        self.assertFalse(resultado.exitoso)
        self.assertTrue(resultado.error)
        self.assertEqual(resultado.ruta_repositorio, "")

    def test_cargar_configuracion_ruta_inexistente(self):
        """
        Una ruta guardada que no existe no debe cargarse.
        """

        ruta_inexistente = self.ruta_temporal / "no-existe"

        self._escribir_configuracion({
            "ruta_repositorio": str(ruta_inexistente)
        })

        resultado = self.servicio.cargar_ultimo_repositorio()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_repositorio, "")

    def test_cargar_configuracion_ruta_no_git(self):
        """
        Una carpeta real que no es repositorio Git
        no debe cargarse.
        """

        carpeta_sin_git = self.ruta_temporal / "solo-carpeta"
        carpeta_sin_git.mkdir()

        self._escribir_configuracion({
            "ruta_repositorio": str(carpeta_sin_git)
        })

        resultado = self.servicio.cargar_ultimo_repositorio()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_repositorio, "")

    def test_guardar_configuracion_solo_escribe_ruta_repositorio(self):
        """
        La escritura siempre debe conservar únicamente
        la clave ruta_repositorio.
        """

        repositorio = self._crear_repositorio_git()

        self._escribir_configuracion({
            "ruta_repositorio": str(repositorio),
            "token": "secreto"
        })

        resultado_guardado = (
            self.servicio.guardar_ultimo_repositorio(
                str(repositorio)
            )
        )

        self.assertTrue(resultado_guardado.exitoso)

        datos = json.loads(
            self.servicio.ruta_configuracion.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            set(datos.keys()),
            {"ruta_repositorio"}
        )

        self.assertEqual(
            Path(datos["ruta_repositorio"]).resolve(),
            repositorio.resolve()
        )

        for clave in (
            "token",
            "pat",
            "password",
            "usuario",
            "remoto",
            "correo"
        ):
            self.assertNotIn(clave, datos)

    def test_guardar_repositorio_invalido_no_sobrescribe_configuracion_valida(self):
        """
        Guardar una ruta inválida debe fallar sin alterar
        la configuración válida anterior.
        """

        repositorio = self._crear_repositorio_git()

        primer_guardado = (
            self.servicio.guardar_ultimo_repositorio(
                str(repositorio)
            )
        )

        self.assertTrue(primer_guardado.exitoso)

        segundo_guardado = (
            self.servicio.guardar_ultimo_repositorio(
                str(self.ruta_temporal / "no-existe")
            )
        )

        self.assertFalse(segundo_guardado.exitoso)

        datos = json.loads(
            self.servicio.ruta_configuracion.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            Path(datos["ruta_repositorio"]).resolve(),
            repositorio.resolve()
        )

    def test_cargar_configuracion_rechaza_ruta_no_texto(self):
        """
        Una ruta guardada que no es texto debe fallar
        de forma controlada.
        """

        self._escribir_configuracion({
            "ruta_repositorio": 123
        })

        resultado = self.servicio.cargar_ultimo_repositorio()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_repositorio, "")


if __name__ == "__main__":
    unittest.main()