import tempfile
import unittest
from pathlib import Path

from servicio_remoto_git import ServicioRemotoGit


class PruebasSincronizacionGit(unittest.TestCase):
    """
    Pruebas de Fetch y sincronización.

    Todas utilizan repositorios temporales locales.

    Ninguna prueba se conecta a GitHub.
    Ninguna prueba modifica repositorios reales.
    """

    def configurar_identidad(
        self,
        servicio_git,
        ruta_repositorio
    ):
        """
        Configura una identidad exclusiva para el repositorio de prueba.
        """

        resultado_nombre = servicio_git.ejecutar_git(
            argumentos=[
                "config",
                "user.name",
                "Usuario Prueba"
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_nombre.exitoso,
            resultado_nombre.error
        )

        resultado_correo = servicio_git.ejecutar_git(
            argumentos=[
                "config",
                "user.email",
                "prueba@example.com"
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_correo.exitoso,
            resultado_correo.error
        )

    def crear_repositorio_local(
        self,
        ruta_base
    ):
        """
        Crea un repositorio local con un commit.
        """

        servicio_git = ServicioRemotoGit()

        ruta_local = (
            ruta_base
            / "local"
        )

        ruta_local.mkdir()

        resultado_init = servicio_git.ejecutar_git(
            argumentos=[
                "init",
                "-b",
                "master"
            ],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(
            resultado_init.exitoso,
            resultado_init.error
        )

        self.configurar_identidad(
            servicio_git,
            ruta_local
        )

        archivo = (
            ruta_local
            / "archivo.sql"
        )

        archivo.write_text(
            "SELECT 1;\n",
            encoding="utf-8"
        )

        resultado_add = servicio_git.ejecutar_git(
            argumentos=[
                "add",
                "archivo.sql"
            ],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(
            resultado_add.exitoso,
            resultado_add.error
        )

        resultado_commit = servicio_git.ejecutar_git(
            argumentos=[
                "commit",
                "-m",
                "Commit inicial"
            ],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(
            resultado_commit.exitoso,
            resultado_commit.error
        )

        return (
            servicio_git,
            ruta_local
        )

    def crear_remoto_vacio(
        self,
        servicio_git,
        ruta_base,
        nombre="remoto.git"
    ):
        """
        Crea un repositorio bare que funciona como servidor remoto.
        """

        ruta_remoto = (
            ruta_base
            / nombre
        )

        ruta_remoto.mkdir()

        resultado = servicio_git.ejecutar_git(
            argumentos=[
                "init",
                "--bare",
                "-b",
                "master"
            ],
            ruta_repositorio=ruta_remoto
        )

        self.assertTrue(
            resultado.exitoso,
            resultado.error
        )

        return ruta_remoto

    def agregar_remoto(
        self,
        servicio_git,
        ruta_local,
        ruta_remoto,
        nombre="origin"
    ):
        """
        Agrega un remoto local al repositorio de prueba.
        """

        resultado = servicio_git.ejecutar_git(
            argumentos=[
                "remote",
                "add",
                nombre,
                str(ruta_remoto)
            ],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(
            resultado.exitoso,
            resultado.error
        )

    def test_fetch_remoto_vacio(self):
        """
        Comprueba que Fetch funcione contra un remoto vacío.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:

            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local = (
                self.crear_repositorio_local(
                    ruta_base
                )
            )

            ruta_remoto = self.crear_remoto_vacio(
                servicio_git,
                ruta_base
            )

            self.agregar_remoto(
                servicio_git,
                ruta_local,
                ruta_remoto
            )

            resultado = servicio_git.ejecutar_fetch(
                ruta_local,
                "origin"
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

    def test_estado_sin_upstream_y_remoto_vacio(self):
        """
        Comprueba el escenario del primer Push:
        hay commits locales pero todavía no existe origin/master.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:

            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local = (
                self.crear_repositorio_local(
                    ruta_base
                )
            )

            ruta_remoto = self.crear_remoto_vacio(
                servicio_git,
                ruta_base
            )

            self.agregar_remoto(
                servicio_git,
                ruta_local,
                ruta_remoto
            )

            resultado_fetch = servicio_git.ejecutar_fetch(
                ruta_local,
                "origin"
            )

            self.assertTrue(
                resultado_fetch.exitoso,
                resultado_fetch.error
            )

            estado = (
                servicio_git.obtener_estado_sincronizacion(
                    ruta_local
                )
            )

            self.assertTrue(
                estado.exitoso,
                estado.error
            )

            self.assertEqual(
                estado.remoto,
                "origin"
            )

            self.assertFalse(
                estado.upstream_configurado
            )

            self.assertFalse(
                estado.rama_remota_existe
            )

            self.assertEqual(
                estado.commits_por_subir,
                1
            )

            self.assertEqual(
                estado.commits_por_bajar,
                0
            )

    def test_estado_sincronizado_con_upstream(self):
        """
        Comprueba una rama sincronizada después de establecer upstream.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:

            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local = (
                self.crear_repositorio_local(
                    ruta_base
                )
            )

            ruta_remoto = self.crear_remoto_vacio(
                servicio_git,
                ruta_base
            )

            self.agregar_remoto(
                servicio_git,
                ruta_local,
                ruta_remoto
            )

            # Este Push ocurre solamente contra un repositorio
            # temporal creado por la prueba.
            resultado_push = servicio_git.ejecutar_git(
                argumentos=[
                    "push",
                    "-u",
                    "origin",
                    "master"
                ],
                ruta_repositorio=ruta_local,
                tiempo_maximo=60
            )

            self.assertTrue(
                resultado_push.exitoso,
                resultado_push.error
            )

            estado = (
                servicio_git.obtener_estado_sincronizacion(
                    ruta_local
                )
            )

            self.assertTrue(
                estado.exitoso,
                estado.error
            )

            self.assertTrue(
                estado.upstream_configurado
            )

            self.assertTrue(
                estado.rama_remota_existe
            )

            self.assertEqual(
                estado.commits_por_subir,
                0
            )

            self.assertEqual(
                estado.commits_por_bajar,
                0
            )

    def test_estado_local_adelantado(self):
        """
        Comprueba la detección de commits locales por enviar.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:

            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local = (
                self.crear_repositorio_local(
                    ruta_base
                )
            )

            ruta_remoto = self.crear_remoto_vacio(
                servicio_git,
                ruta_base
            )

            self.agregar_remoto(
                servicio_git,
                ruta_local,
                ruta_remoto
            )

            resultado_push = servicio_git.ejecutar_git(
                argumentos=[
                    "push",
                    "-u",
                    "origin",
                    "master"
                ],
                ruta_repositorio=ruta_local,
                tiempo_maximo=60
            )

            self.assertTrue(
                resultado_push.exitoso,
                resultado_push.error
            )

            archivo = (
                ruta_local
                / "archivo.sql"
            )

            archivo.write_text(
                "SELECT 2;\n",
                encoding="utf-8"
            )

            resultado_add = servicio_git.ejecutar_git(
                argumentos=[
                    "add",
                    "archivo.sql"
                ],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(
                resultado_add.exitoso,
                resultado_add.error
            )

            resultado_commit = servicio_git.ejecutar_git(
                argumentos=[
                    "commit",
                    "-m",
                    "Local adelante"
                ],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(
                resultado_commit.exitoso,
                resultado_commit.error
            )

            estado = (
                servicio_git.obtener_estado_sincronizacion(
                    ruta_local
                )
            )

            self.assertTrue(
                estado.exitoso,
                estado.error
            )

            self.assertEqual(
                estado.commits_por_subir,
                1
            )

            self.assertEqual(
                estado.commits_por_bajar,
                0
            )

    def test_estado_remoto_adelantado(self):
        """
        Comprueba la detección de commits remotos por descargar.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:

            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local = (
                self.crear_repositorio_local(
                    ruta_base
                )
            )

            ruta_remoto = self.crear_remoto_vacio(
                servicio_git,
                ruta_base
            )

            self.agregar_remoto(
                servicio_git,
                ruta_local,
                ruta_remoto
            )

            resultado_push = servicio_git.ejecutar_git(
                argumentos=[
                    "push",
                    "-u",
                    "origin",
                    "master"
                ],
                ruta_repositorio=ruta_local,
                tiempo_maximo=60
            )

            self.assertTrue(
                resultado_push.exitoso,
                resultado_push.error
            )

            # Creamos un segundo repositorio local temporal
            # que simula a otro desarrollador.
            ruta_otro = (
                ruta_base
                / "otro"
            )

            resultado_clone = servicio_git.ejecutar_git(
                argumentos=[
                    "clone",
                    str(ruta_remoto),
                    str(ruta_otro)
                ],
                ruta_repositorio=ruta_base,
                tiempo_maximo=60
            )

            self.assertTrue(
                resultado_clone.exitoso,
                resultado_clone.error
            )

            self.configurar_identidad(
                servicio_git,
                ruta_otro
            )

            archivo_remoto = (
                ruta_otro
                / "remoto.sql"
            )

            archivo_remoto.write_text(
                "SELECT 3;\n",
                encoding="utf-8"
            )

            resultado_add = servicio_git.ejecutar_git(
                argumentos=[
                    "add",
                    "remoto.sql"
                ],
                ruta_repositorio=ruta_otro
            )

            self.assertTrue(
                resultado_add.exitoso,
                resultado_add.error
            )

            resultado_commit = servicio_git.ejecutar_git(
                argumentos=[
                    "commit",
                    "-m",
                    "Remoto adelante"
                ],
                ruta_repositorio=ruta_otro
            )

            self.assertTrue(
                resultado_commit.exitoso,
                resultado_commit.error
            )

            resultado_push_otro = servicio_git.ejecutar_git(
                argumentos=[
                    "push",
                    "origin",
                    "master"
                ],
                ruta_repositorio=ruta_otro,
                tiempo_maximo=60
            )

            self.assertTrue(
                resultado_push_otro.exitoso,
                resultado_push_otro.error
            )

            resultado_fetch = servicio_git.ejecutar_fetch(
                ruta_local,
                "origin"
            )

            self.assertTrue(
                resultado_fetch.exitoso,
                resultado_fetch.error
            )

            estado = (
                servicio_git.obtener_estado_sincronizacion(
                    ruta_local
                )
            )

            self.assertTrue(
                estado.exitoso,
                estado.error
            )

            self.assertEqual(
                estado.commits_por_subir,
                0
            )

            self.assertEqual(
                estado.commits_por_bajar,
                1
            )

    def test_estado_divergente(self):
        """
        Comprueba que detectemos una divergencia.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:

            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local = (
                self.crear_repositorio_local(
                    ruta_base
                )
            )

            ruta_remoto = self.crear_remoto_vacio(
                servicio_git,
                ruta_base
            )

            self.agregar_remoto(
                servicio_git,
                ruta_local,
                ruta_remoto
            )

            resultado_push = servicio_git.ejecutar_git(
                argumentos=[
                    "push",
                    "-u",
                    "origin",
                    "master"
                ],
                ruta_repositorio=ruta_local,
                tiempo_maximo=60
            )

            self.assertTrue(
                resultado_push.exitoso,
                resultado_push.error
            )

            ruta_otro = (
                ruta_base
                / "otro"
            )

            resultado_clone = servicio_git.ejecutar_git(
                argumentos=[
                    "clone",
                    str(ruta_remoto),
                    str(ruta_otro)
                ],
                ruta_repositorio=ruta_base,
                tiempo_maximo=60
            )

            self.assertTrue(
                resultado_clone.exitoso,
                resultado_clone.error
            )

            self.configurar_identidad(
                servicio_git,
                ruta_otro
            )

            # Commit exclusivamente local.
            archivo_local = (
                ruta_local
                / "local.sql"
            )

            archivo_local.write_text(
                "SELECT 4;\n",
                encoding="utf-8"
            )

            resultado_add_local = servicio_git.ejecutar_git(
                argumentos=[
                    "add",
                    "local.sql"
                ],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(
                resultado_add_local.exitoso,
                resultado_add_local.error
            )

            resultado_commit_local = servicio_git.ejecutar_git(
                argumentos=[
                    "commit",
                    "-m",
                    "Cambio local"
                ],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(
                resultado_commit_local.exitoso,
                resultado_commit_local.error
            )

            # Commit diferente en el segundo repositorio.
            archivo_remoto = (
                ruta_otro
                / "remoto.sql"
            )

            archivo_remoto.write_text(
                "SELECT 5;\n",
                encoding="utf-8"
            )

            resultado_add_remoto = servicio_git.ejecutar_git(
                argumentos=[
                    "add",
                    "remoto.sql"
                ],
                ruta_repositorio=ruta_otro
            )

            self.assertTrue(
                resultado_add_remoto.exitoso,
                resultado_add_remoto.error
            )

            resultado_commit_remoto = servicio_git.ejecutar_git(
                argumentos=[
                    "commit",
                    "-m",
                    "Cambio remoto"
                ],
                ruta_repositorio=ruta_otro
            )

            self.assertTrue(
                resultado_commit_remoto.exitoso,
                resultado_commit_remoto.error
            )

            resultado_push_remoto = servicio_git.ejecutar_git(
                argumentos=[
                    "push",
                    "origin",
                    "master"
                ],
                ruta_repositorio=ruta_otro,
                tiempo_maximo=60
            )

            self.assertTrue(
                resultado_push_remoto.exitoso,
                resultado_push_remoto.error
            )

            resultado_fetch = servicio_git.ejecutar_fetch(
                ruta_local,
                "origin"
            )

            self.assertTrue(
                resultado_fetch.exitoso,
                resultado_fetch.error
            )

            estado = (
                servicio_git.obtener_estado_sincronizacion(
                    ruta_local
                )
            )

            self.assertTrue(
                estado.exitoso,
                estado.error
            )

            self.assertEqual(
                estado.commits_por_subir,
                1
            )

            self.assertEqual(
                estado.commits_por_bajar,
                1
            )

            self.assertTrue(
                estado.divergente
            )

    def test_varios_remotos_sin_upstream_se_rechazan(self):
        """
        Comprueba que no elijamos un remoto al azar.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:

            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local = (
                self.crear_repositorio_local(
                    ruta_base
                )
            )

            ruta_remoto_1 = self.crear_remoto_vacio(
                servicio_git,
                ruta_base,
                nombre="remoto1.git"
            )

            ruta_remoto_2 = self.crear_remoto_vacio(
                servicio_git,
                ruta_base,
                nombre="remoto2.git"
            )

            self.agregar_remoto(
                servicio_git,
                ruta_local,
                ruta_remoto_1,
                nombre="origin"
            )

            self.agregar_remoto(
                servicio_git,
                ruta_local,
                ruta_remoto_2,
                nombre="respaldo"
            )

            resultado = (
                servicio_git.obtener_remoto_sincronizacion(
                    ruta_local
                )
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "varios remotos",
                resultado.error.lower()
            )


if __name__ == "__main__":
    unittest.main()