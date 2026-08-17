import tempfile
import unittest
from pathlib import Path

from servicio_remoto_git import ServicioRemotoGit


class PruebasPullGit(unittest.TestCase):
    """
    Pruebas del Pull seguro.

    Todos los remotos utilizados son repositorios bare temporales.

    Ninguna prueba se conecta a GitHub.
    Ninguna prueba modifica repositorios reales.
    """

    def configurar_identidad(
        self,
        servicio_git,
        ruta_repositorio
    ):
        """
        Configura una identidad Git local para las pruebas.
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
        Crea un repositorio local con un commit inicial.
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
        ruta_base
    ):
        """
        Crea un repositorio bare temporal.
        """

        ruta_remoto = (
            ruta_base
            / "remoto.git"
        )

        ruta_remoto.mkdir()

        resultado_init = servicio_git.ejecutar_git(
            argumentos=[
                "init",
                "--bare",
                "-b",
                "master"
            ],
            ruta_repositorio=ruta_remoto
        )

        self.assertTrue(
            resultado_init.exitoso,
            resultado_init.error
        )

        return ruta_remoto

    def agregar_remoto(
        self,
        servicio_git,
        ruta_local,
        ruta_remoto
    ):
        """
        Agrega origin al repositorio local.
        """

        resultado = servicio_git.ejecutar_git(
            argumentos=[
                "remote",
                "add",
                "origin",
                str(ruta_remoto)
            ],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(
            resultado.exitoso,
            resultado.error
        )

    def preparar_repositorio_sincronizado(
        self,
        ruta_base
    ):
        """
        Crea un repositorio local y remoto sincronizados.

        La rama local queda siguiendo origin/master.
        """

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

        resultado_push = (
            servicio_git.ejecutar_push_seguro(
                ruta_local
            )
        )

        self.assertTrue(
            resultado_push.exitoso,
            resultado_push.error
        )

        return (
            servicio_git,
            ruta_local,
            ruta_remoto
        )

    def clonar_otro_desarrollador(
        self,
        servicio_git,
        ruta_base,
        ruta_remoto
    ):
        """
        Crea un segundo clon temporal.
        """

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

        return ruta_otro

    def crear_commit_adicional(
        self,
        servicio_git,
        ruta_repositorio,
        nombre_archivo,
        mensaje,
        contenido
    ):
        """
        Crea un archivo nuevo y un commit.
        """

        archivo = (
            ruta_repositorio
            / nombre_archivo
        )

        archivo.write_text(
            contenido,
            encoding="utf-8"
        )

        resultado_add = servicio_git.ejecutar_git(
            argumentos=[
                "add",
                nombre_archivo
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_add.exitoso,
            resultado_add.error
        )

        resultado_commit = servicio_git.ejecutar_git(
            argumentos=[
                "commit",
                "-m",
                mensaje
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_commit.exitoso,
            resultado_commit.error
        )

    def enviar_commit_desde_otro(
        self,
        servicio_git,
        ruta_otro
    ):
        """
        Crea un commit en el segundo clon y lo envía al remoto.
        """

        self.crear_commit_adicional(
            servicio_git,
            ruta_otro,
            "remoto.sql",
            "Cambio remoto",
            "SELECT 2;\n"
        )

        resultado_push = servicio_git.ejecutar_git(
            argumentos=[
                "push",
                "origin",
                "master"
            ],
            ruta_repositorio=ruta_otro,
            tiempo_maximo=60
        )

        self.assertTrue(
            resultado_push.exitoso,
            resultado_push.error
        )

    def test_pull_descarga_commit_remoto(self):
        """
        Comprueba un Pull fast-forward correcto.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_base = Path(
                carpeta_temporal
            )

            (
                servicio_git,
                ruta_local,
                ruta_remoto
            ) = self.preparar_repositorio_sincronizado(
                ruta_base
            )

            ruta_otro = self.clonar_otro_desarrollador(
                servicio_git,
                ruta_base,
                ruta_remoto
            )

            self.enviar_commit_desde_otro(
                servicio_git,
                ruta_otro
            )

            resultado = servicio_git.ejecutar_pull_seguro(
                ruta_local
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            # La operación debe utilizar obligatoriamente
            # la protección fast-forward.
            self.assertIn(
                "--ff-only",
                resultado.comando
            )

            resultado_mensaje = servicio_git.ejecutar_git(
                argumentos=[
                    "log",
                    "-1",
                    "--pretty=%s"
                ],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(
                resultado_mensaje.exitoso,
                resultado_mensaje.error
            )

            self.assertEqual(
                resultado_mensaje.salida,
                "Cambio remoto"
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
                0
            )

    def test_pull_rechaza_repositorio_sin_cambios_remotos(self):
        """
        Comprueba que no ejecutemos Pull innecesariamente.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local, _ = (
                self.preparar_repositorio_sincronizado(
                    ruta_base
                )
            )

            resultado = servicio_git.ejecutar_pull_seguro(
                ruta_local
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "no hay commits remotos",
                resultado.error.lower()
            )

    def test_pull_rechaza_commits_locales_pendientes(self):
        """
        Comprueba que Pull sea bloqueado
        cuando existen commits locales por enviar.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local, _ = (
                self.preparar_repositorio_sincronizado(
                    ruta_base
                )
            )

            self.crear_commit_adicional(
                servicio_git,
                ruta_local,
                "local.sql",
                "Cambio local",
                "SELECT 3;\n"
            )

            resultado = servicio_git.ejecutar_pull_seguro(
                ruta_local
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "commits locales",
                resultado.error.lower()
            )

    def test_pull_rechaza_divergencia(self):
        """
        Comprueba que Pull no realice Merge ni Rebase
        cuando las ramas han divergido.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_base = Path(
                carpeta_temporal
            )

            (
                servicio_git,
                ruta_local,
                ruta_remoto
            ) = self.preparar_repositorio_sincronizado(
                ruta_base
            )

            ruta_otro = self.clonar_otro_desarrollador(
                servicio_git,
                ruta_base,
                ruta_remoto
            )

            self.crear_commit_adicional(
                servicio_git,
                ruta_local,
                "local.sql",
                "Cambio local",
                "SELECT 4;\n"
            )

            self.enviar_commit_desde_otro(
                servicio_git,
                ruta_otro
            )

            resultado = servicio_git.ejecutar_pull_seguro(
                ruta_local
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "divergido",
                resultado.error.lower()
            )

    def test_pull_rechaza_cambios_sin_commit(self):
        """
        Comprueba que Pull exija un área de trabajo limpia.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local, _ = (
                self.preparar_repositorio_sincronizado(
                    ruta_base
                )
            )

            archivo_pendiente = (
                ruta_local
                / "pendiente.sql"
            )

            archivo_pendiente.write_text(
                "SELECT 5;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.ejecutar_pull_seguro(
                ruta_local
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "cambios sin commit",
                resultado.error.lower()
            )

    def test_pull_rechaza_rama_sin_upstream(self):
        """
        Comprueba que Pull no adivine la rama remota
        cuando todavía no existe upstream.
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

            resultado = servicio_git.ejecutar_pull_seguro(
                ruta_local
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "upstream",
                resultado.error.lower()
            )


if __name__ == "__main__":
    unittest.main()