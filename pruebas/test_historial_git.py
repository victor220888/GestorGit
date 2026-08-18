import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from servicio_historial_git import ServicioHistorialGit


class PruebasHistorialGit(unittest.TestCase):
    """
    Pruebas del historial de commits de solo lectura.
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
            "Usuario Historial"
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "config",
            "user.email",
            "historial@example.com"
        )

        self.servicio = ServicioHistorialGit()

    def tearDown(self):
        self.temporal.cleanup()

    def test_historial_repositorio_sin_commits(self):
        """Un repositorio nuevo debe devolver una lista vacía."""

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio)
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual([], resultado.commits)
        self.assertIn(
            "todavía no tiene commits",
            resultado.mensaje
        )

    def test_historial_devuelve_commit_con_datos(self):
        """Comprueba hash, autor, correo y mensaje del commit."""

        self._crear_commit(
            "archivo.sql",
            "SELECT 1;",
            "Agrega consulta inicial"
        )

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio)
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(1, len(resultado.commits))

        commit = resultado.commits[0]

        self.assertEqual(
            "Usuario Historial",
            commit.autor
        )
        self.assertEqual(
            "historial@example.com",
            commit.correo
        )
        self.assertEqual(
            "Agrega consulta inicial",
            commit.mensaje
        )
        self.assertTrue(commit.hash_completo)
        self.assertTrue(commit.hash_corto)
        self.assertTrue(commit.fecha_iso)

    def test_historial_respeta_orden_mas_reciente_primero(self):
        """
        El historial debe ordenarse por fecha aunque el orden
        topológico de Git sea diferente.
        """

        self._crear_commit(
            "uno.sql",
            "SELECT 1;",
            "Commit con fecha más reciente",
            fecha_iso="2026-08-20"
        )

        # Este commit se crea después y por lo tanto Git debe
        # mantenerlo como descendiente del anterior. Sin embargo,
        # su fecha se establece deliberadamente como más antigua
        # para comprobar el orden cronológico de nuestra tabla.
        self._crear_commit(
            "dos.sql",
            "SELECT 2;",
            "Commit creado después con fecha anterior",
            fecha_iso="2026-08-10"
        )

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio)
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(2, len(resultado.commits))
        self.assertEqual(
            "Commit con fecha más reciente",
            resultado.commits[0].mensaje
        )
        self.assertEqual(
            "Commit creado después con fecha anterior",
            resultado.commits[1].mensaje
        )

    def test_historial_respeta_limite(self):
        """Comprueba que no se devuelvan más commits del límite."""

        for numero in range(1, 5):
            self._crear_commit(
                f"archivo_{numero}.sql",
                f"SELECT {numero};",
                f"Commit número {numero}"
            )

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio),
            limite=2
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(2, len(resultado.commits))
        self.assertEqual(
            "Commit número 4",
            resultado.commits[0].mensaje
        )
        self.assertEqual(
            "Commit número 3",
            resultado.commits[1].mensaje
        )

    def test_historial_rechaza_limite_invalido(self):
        """Un límite inválido debe rechazarse sin ejecutar git log."""

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio),
            limite=0
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "mayor que cero",
            resultado.error
        )

    def test_historial_filtra_por_nombre_de_archivo(self):
        """El filtro de archivo debe aceptar texto parcial sin distinguir caso."""

        self._crear_commit(
            "Paquetes/FINI004.pls",
            "PACKAGE FINI004;",
            "Agrega paquete FINI004",
            fecha_iso="2026-08-10"
        )

        self._crear_commit(
            "Consultas/OTRA.sql",
            "SELECT 2;",
            "Agrega otra consulta",
            fecha_iso="2026-08-11"
        )

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio),
            filtro_archivo="fini004"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(1, len(resultado.commits))
        self.assertEqual(
            "Agrega paquete FINI004",
            resultado.commits[0].mensaje
        )

    def test_historial_filtra_desde_fecha_inclusive(self):
        """Desde debe incluir la fecha indicada y excluir las anteriores."""

        self._crear_commit(
            "uno.sql",
            "SELECT 1;",
            "Commit anterior",
            fecha_iso="2026-08-10"
        )

        self._crear_commit(
            "dos.sql",
            "SELECT 2;",
            "Commit desde",
            fecha_iso="2026-08-15"
        )

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio),
            fecha_desde="2026-08-15"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(1, len(resultado.commits))
        self.assertEqual(
            "Commit desde",
            resultado.commits[0].mensaje
        )

    def test_historial_filtra_hasta_fecha_inclusive(self):
        """Hasta debe incluir la fecha indicada y excluir las posteriores."""

        self._crear_commit(
            "uno.sql",
            "SELECT 1;",
            "Commit hasta",
            fecha_iso="2026-08-10"
        )

        self._crear_commit(
            "dos.sql",
            "SELECT 2;",
            "Commit posterior",
            fecha_iso="2026-08-15"
        )

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio),
            fecha_hasta="2026-08-10"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(1, len(resultado.commits))
        self.assertEqual(
            "Commit hasta",
            resultado.commits[0].mensaje
        )

    def test_historial_filtra_rango_de_fechas(self):
        """Desde y Hasta deben funcionar juntos como rango inclusivo."""

        self._crear_commit(
            "uno.sql",
            "SELECT 1;",
            "Commit primero",
            fecha_iso="2026-08-01"
        )

        self._crear_commit(
            "dos.sql",
            "SELECT 2;",
            "Commit dentro",
            fecha_iso="2026-08-10"
        )

        self._crear_commit(
            "tres.sql",
            "SELECT 3;",
            "Commit último",
            fecha_iso="2026-08-20"
        )

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio),
            fecha_desde="2026-08-05",
            fecha_hasta="2026-08-15"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(1, len(resultado.commits))
        self.assertEqual(
            "Commit dentro",
            resultado.commits[0].mensaje
        )

    def test_historial_combina_archivo_y_fechas(self):
        """Los filtros de archivo y fecha deben combinarse mediante AND."""

        self._crear_commit(
            "Paquetes/FINI004.pls",
            "VERSION 1",
            "FINI004 anterior",
            fecha_iso="2026-08-01"
        )

        self._crear_commit(
            "Paquetes/FINI004.pls",
            "VERSION 2",
            "FINI004 dentro del rango",
            fecha_iso="2026-08-10"
        )

        self._crear_commit(
            "Paquetes/OTRO.pls",
            "OTRO",
            "Otro archivo dentro del rango",
            fecha_iso="2026-08-11"
        )

        resultado = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio),
            filtro_archivo="FINI004",
            fecha_desde="2026-08-05",
            fecha_hasta="2026-08-15"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(1, len(resultado.commits))
        self.assertEqual(
            "FINI004 dentro del rango",
            resultado.commits[0].mensaje
        )

    def test_historial_rechaza_fecha_invalida_y_rango_invertido(self):
        """Fechas inválidas o un rango invertido deben rechazarse."""

        resultado_fecha = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio),
            fecha_desde="2026-02-30"
        )

        self.assertFalse(resultado_fecha.exitoso)
        self.assertIn(
            "no es válida",
            resultado_fecha.error
        )

        resultado_rango = self.servicio.obtener_historial_commits(
            str(self.ruta_repositorio),
            fecha_desde="2026-08-20",
            fecha_hasta="2026-08-10"
        )

        self.assertFalse(resultado_rango.exitoso)
        self.assertIn(
            "no puede ser posterior",
            resultado_rango.error
        )

    def _crear_commit(
        self,
        nombre_archivo,
        contenido,
        mensaje,
        fecha_iso=None
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

        entorno_extra = None

        if fecha_iso:
            fecha_git = (
                f"{fecha_iso}T12:00:00+00:00"
            )

            entorno_extra = {
                "GIT_AUTHOR_DATE": fecha_git,
                "GIT_COMMITTER_DATE": fecha_git
            }

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "commit",
            "-m",
            mensaje,
            entorno_extra=entorno_extra
        )

    @staticmethod
    def _ejecutar_git(
        *argumentos,
        entorno_extra=None
    ):
        """Ejecuta Git solamente para preparar escenarios de prueba."""

        entorno = os.environ.copy()

        if entorno_extra:
            entorno.update(
                entorno_extra
            )

        resultado = subprocess.run(
            ["git", *argumentos],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=entorno
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
