import tempfile
import unittest
from pathlib import Path

from servicio_remoto_git import ServicioRemotoGit


class PruebasPushGit(unittest.TestCase):
    """
    Pruebas del Push seguro.

    Todos los remotos utilizados son repositorios bare temporales
    ubicados en el propio equipo.

    Ninguna prueba se conecta a GitHub.
    Ninguna prueba modifica repositorios reales.
    """

    def configurar_identidad(
        self,
        servicio_git,
        ruta_repositorio
    ):
        """
        Configura una identidad local exclusiva
        para los repositorios utilizados en las pruebas.
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
        ruta_base,
        con_commit=True
    ):
        """
        Crea un repositorio Git local temporal.

        Opcionalmente crea también un commit inicial.
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

        if con_commit:
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

        Este repositorio funciona como remoto durante las pruebas.
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
        Agrega el remoto origin al repositorio temporal.
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

    def crear_commit_adicional(
        self,
        servicio_git,
        ruta_repositorio,
        nombre_archivo,
        mensaje,
        contenido
    ):
        """
        Crea un nuevo archivo y un nuevo commit
        dentro del repositorio indicado.
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

    def clonar_otro_desarrollador(
        self,
        servicio_git,
        ruta_base,
        ruta_remoto
    ):
        """
        Crea un segundo clon temporal.

        Este clon simula el trabajo realizado
        por otro desarrollador.
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

    def test_push_inicial_crea_rama_y_upstream(self):
        """
        Comprueba el primer Push contra un remoto vacío.

        Debe crear origin/master y configurar upstream.
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

            resultado = servicio_git.ejecutar_push_seguro(
                ruta_local
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            # Nuestra implementación nunca debe
            # utilizar Push forzado.
            self.assertNotIn(
                "--force",
                resultado.comando
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

            self.assertTrue(
                estado.upstream_configurado
            )

            self.assertTrue(
                estado.rama_remota_existe
            )

            self.assertEqual(
                estado.rama_remota,
                "origin/master"
            )

            self.assertEqual(
                estado.commits_por_subir,
                0
            )

            self.assertEqual(
                estado.commits_por_bajar,
                0
            )

    def test_push_envia_nuevo_commit_local(self):
        """
        Comprueba un Push normal después
        de haber configurado el upstream.
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

            resultado_inicial = (
                servicio_git.ejecutar_push_seguro(
                    ruta_local
                )
            )

            self.assertTrue(
                resultado_inicial.exitoso,
                resultado_inicial.error
            )

            self.crear_commit_adicional(
                servicio_git,
                ruta_local,
                "segundo.sql",
                "Segundo commit",
                "SELECT 2;\n"
            )

            resultado = servicio_git.ejecutar_push_seguro(
                ruta_local
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            self.assertNotIn(
                "--force",
                resultado.comando
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
                0
            )

    def test_push_rechaza_remoto_adelantado(self):
        """
        Comprueba que Push sea rechazado cuando
        existen commits remotos que faltan localmente.
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

            resultado_inicial = (
                servicio_git.ejecutar_push_seguro(
                    ruta_local
                )
            )

            self.assertTrue(
                resultado_inicial.exitoso,
                resultado_inicial.error
            )

            ruta_otro = self.clonar_otro_desarrollador(
                servicio_git,
                ruta_base,
                ruta_remoto
            )

            self.crear_commit_adicional(
                servicio_git,
                ruta_otro,
                "remoto.sql",
                "Cambio remoto",
                "SELECT 3;\n"
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

            resultado = servicio_git.ejecutar_push_seguro(
                ruta_local
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "descargar",
                resultado.error.lower()
            )

    def test_push_rechaza_divergencia(self):
        """
        Comprueba que Push sea bloqueado
        cuando las ramas han divergido.
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

            resultado_inicial = (
                servicio_git.ejecutar_push_seguro(
                    ruta_local
                )
            )

            self.assertTrue(
                resultado_inicial.exitoso,
                resultado_inicial.error
            )

            ruta_otro = self.clonar_otro_desarrollador(
                servicio_git,
                ruta_base,
                ruta_remoto
            )

            # Creamos un commit exclusivamente local.
            self.crear_commit_adicional(
                servicio_git,
                ruta_local,
                "local.sql",
                "Cambio local",
                "SELECT 4;\n"
            )

            # Creamos otro commit diferente
            # en el segundo repositorio.
            self.crear_commit_adicional(
                servicio_git,
                ruta_otro,
                "remoto.sql",
                "Cambio remoto",
                "SELECT 5;\n"
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

            resultado = servicio_git.ejecutar_push_seguro(
                ruta_local
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "divergido",
                resultado.error.lower()
            )

    def test_push_rechaza_cambios_sin_commit(self):
        """
        Comprueba que nuestra política conservadora
        exija un área de trabajo limpia.
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

            archivo_pendiente = (
                ruta_local
                / "pendiente.sql"
            )

            archivo_pendiente.write_text(
                "SELECT 6;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.ejecutar_push_seguro(
                ruta_local
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "cambios sin commit",
                resultado.error.lower()
            )

    def test_push_rechaza_repositorio_sin_commits(self):
        """
        Comprueba que no se intente Push
        cuando todavía no existe ningún commit.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_base = Path(
                carpeta_temporal
            )

            servicio_git, ruta_local = (
                self.crear_repositorio_local(
                    ruta_base,
                    con_commit=False
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

            resultado = servicio_git.ejecutar_push_seguro(
                ruta_local
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "no tiene commits",
                resultado.error.lower()
            )


if __name__ == "__main__":
    unittest.main()