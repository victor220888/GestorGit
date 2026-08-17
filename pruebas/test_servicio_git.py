import tempfile
import unittest
from pathlib import Path

from servicio_git import ServicioGit


class PruebasServicioGit(unittest.TestCase):
    """
    Pruebas automáticas para comprobar el funcionamiento
    de ServicioGit.

    Todos los repositorios utilizados en estas pruebas
    son temporales.

    Nunca modificamos un repositorio real del usuario.
    """

    def preparar_repositorio_con_commit(self, ruta_repositorio):
        """
        Inicializa un repositorio temporal y crea un primer commit.

        Devuelve:
            servicio_git
            archivo_base
        """

        servicio_git = ServicioGit()

        # Inicializamos el repositorio.
        resultado_init = servicio_git.ejecutar_git(
            argumentos=["init"],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_init.exitoso,
            resultado_init.error
        )

        # Configuramos nombre y correo solamente para
        # este repositorio temporal.
        #
        # De esta manera las pruebas no dependen de la
        # configuración personal del usuario.
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

        # Creamos un archivo que utilizaremos como base
        # para las pruebas de modificación y eliminación.
        archivo_base = ruta_repositorio / "archivo_base.sql"

        archivo_base.write_text(
            "SELECT 1;\n",
            encoding="utf-8"
        )

        # Preparamos el archivo.
        resultado_agregar = servicio_git.ejecutar_git(
            argumentos=[
                "add",
                "--",
                archivo_base.name
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_agregar.exitoso,
            resultado_agregar.error
        )

        # Creamos el primer commit.
        resultado_commit = servicio_git.ejecutar_git(
            argumentos=[
                "commit",
                "-m",
                "Commit inicial de prueba"
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_commit.exitoso,
            resultado_commit.error
        )

        return servicio_git, archivo_base

    def test_git_esta_disponible(self):
        """
        Comprueba que git.exe pueda encontrarse.
        """

        servicio_git = ServicioGit()

        self.assertTrue(
            servicio_git.git_disponible(),
            "Git debería estar disponible en el sistema."
        )

    def test_obtener_version_git(self):
        """
        Comprueba que podamos ejecutar git --version.
        """

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
        Comprueba que un repositorio nuevo pueda detectarse
        aunque todavía no tenga commits.
        """

        servicio_git = ServicioGit()

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

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

    def test_repositorio_limpio_no_tiene_cambios(self):
        """
        Comprueba que un repositorio sin modificaciones
        devuelva una lista de cambios vacía.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            self.assertEqual(
                len(resultado.cambios),
                0
            )

    def test_archivo_nuevo_no_preparado(self):
        """
        Comprueba la detección de un archivo nuevo
        que todavía no fue agregado al índice.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_nuevo = (
                ruta_temporal / "nuevo.sql"
            )

            archivo_nuevo.write_text(
                "SELECT 2;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            self.assertEqual(
                len(resultado.cambios),
                1
            )

            cambio = resultado.cambios[0]

            self.assertEqual(
                cambio.ruta,
                "nuevo.sql"
            )

            self.assertEqual(
                cambio.descripcion,
                "Nuevo"
            )

            self.assertFalse(
                cambio.preparado
            )

    def test_archivo_nuevo_preparado(self):
        """
        Comprueba la detección de un archivo nuevo
        después de ejecutar git add.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_nuevo = (
                ruta_temporal / "nuevo.sql"
            )

            archivo_nuevo.write_text(
                "SELECT 2;\n",
                encoding="utf-8"
            )

            resultado_agregar = servicio_git.ejecutar_git(
                argumentos=[
                    "add",
                    "--",
                    archivo_nuevo.name
                ],
                ruta_repositorio=ruta_temporal
            )

            self.assertTrue(
                resultado_agregar.exitoso,
                resultado_agregar.error
            )

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            self.assertEqual(
                len(resultado.cambios),
                1
            )

            cambio = resultado.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Agregado y preparado"
            )

            self.assertTrue(
                cambio.preparado
            )

    def test_archivo_modificado_no_preparado(self):
        """
        Comprueba la detección de un archivo modificado
        que todavía no fue preparado.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, archivo_base = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_base.write_text(
                "SELECT 100;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            self.assertEqual(
                len(resultado.cambios),
                1
            )

            cambio = resultado.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Modificado"
            )

            self.assertFalse(
                cambio.preparado
            )

    def test_archivo_modificado_preparado(self):
        """
        Comprueba la detección de un archivo modificado
        después de ejecutar git add.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, archivo_base = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_base.write_text(
                "SELECT 200;\n",
                encoding="utf-8"
            )

            resultado_agregar = servicio_git.ejecutar_git(
                argumentos=[
                    "add",
                    "--",
                    archivo_base.name
                ],
                ruta_repositorio=ruta_temporal
            )

            self.assertTrue(
                resultado_agregar.exitoso,
                resultado_agregar.error
            )

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            self.assertEqual(
                len(resultado.cambios),
                1
            )

            cambio = resultado.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Modificado y preparado"
            )

            self.assertTrue(
                cambio.preparado
            )

    def test_archivo_eliminado_no_preparado(self):
        """
        Comprueba la detección de un archivo eliminado
        que todavía no fue preparado.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, archivo_base = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            # Eliminamos físicamente el archivo.
            archivo_base.unlink()

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            self.assertEqual(
                len(resultado.cambios),
                1
            )

            cambio = resultado.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Eliminado"
            )

            self.assertFalse(
                cambio.preparado
            )

    def test_archivo_eliminado_preparado(self):
        """
        Comprueba la detección de un archivo eliminado
        y preparado para commit.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, archivo_base = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_base.unlink()

            # git add -A registra también eliminaciones.
            resultado_agregar = servicio_git.ejecutar_git(
                argumentos=[
                    "add",
                    "-A",
                    "--",
                    archivo_base.name
                ],
                ruta_repositorio=ruta_temporal
            )

            self.assertTrue(
                resultado_agregar.exitoso,
                resultado_agregar.error
            )

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            self.assertEqual(
                len(resultado.cambios),
                1
            )

            cambio = resultado.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Eliminado y preparado"
            )

            self.assertTrue(
                cambio.preparado
            )

    def test_archivo_con_espacios_en_nombre(self):
        """
        Comprueba que los nombres con espacios
        puedan interpretarse correctamente.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_nuevo = (
                ruta_temporal
                / "paquete de prueba.sql"
            )

            archivo_nuevo.write_text(
                "SELECT 300;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            self.assertEqual(
                len(resultado.cambios),
                1
            )

            cambio = resultado.cambios[0]

            self.assertEqual(
                cambio.ruta,
                "paquete de prueba.sql"
            )

            self.assertEqual(
                cambio.descripcion,
                "Nuevo"
            )

            self.assertFalse(
                cambio.preparado
            )

    def test_agregar_archivo_nuevo(self):
        """
        Comprueba que un archivo nuevo pueda prepararse
        correctamente para commit.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_nuevo = (
                ruta_temporal / "nuevo.sql"
            )

            archivo_nuevo.write_text(
                "SELECT 500;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.agregar_archivos(
                ruta_temporal,
                [
                    "nuevo.sql"
                ]
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertEqual(
                len(cambios.cambios),
                1
            )

            cambio = cambios.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Agregado y preparado"
            )

            self.assertTrue(
                cambio.preparado
            )

    def test_agregar_archivo_modificado(self):
        """
        Comprueba que un archivo modificado pueda prepararse
        correctamente para commit.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, archivo_base = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_base.write_text(
                "SELECT 600;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.agregar_archivos(
                ruta_temporal,
                [
                    "archivo_base.sql"
                ]
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertEqual(
                len(cambios.cambios),
                1
            )

            cambio = cambios.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Modificado y preparado"
            )

            self.assertTrue(
                cambio.preparado
            )

    def test_agregar_archivo_eliminado(self):
        """
        Comprueba que la eliminación de un archivo pueda
        prepararse correctamente para commit.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, archivo_base = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_base.unlink()

            resultado = servicio_git.agregar_archivos(
                ruta_temporal,
                [
                    "archivo_base.sql"
                ]
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertEqual(
                len(cambios.cambios),
                1
            )

            cambio = cambios.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Eliminado y preparado"
            )

            self.assertTrue(
                cambio.preparado
            )

    def test_agregar_varios_archivos(self):
        """
        Comprueba que varios archivos puedan prepararse
        en una única operación.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_uno = (
                ruta_temporal / "uno.sql"
            )

            archivo_dos = (
                ruta_temporal / "dos.sql"
            )

            archivo_uno.write_text(
                "SELECT 1;\n",
                encoding="utf-8"
            )

            archivo_dos.write_text(
                "SELECT 2;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.agregar_archivos(
                ruta_temporal,
                [
                    "uno.sql",
                    "dos.sql"
                ]
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertEqual(
                len(cambios.cambios),
                2
            )

            for cambio in cambios.cambios:
                self.assertTrue(
                    cambio.preparado
                )

    def test_agregar_lista_vacia_es_rechazado(self):
        """
        Comprueba que una operación sin archivos
        sea rechazada de manera controlada.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            resultado = servicio_git.agregar_archivos(
                ruta_temporal,
                []
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "ningún archivo",
                resultado.error.lower()
            )

    def test_agregar_ruta_absoluta_es_rechazado(self):
        """
        Comprueba que no se permita agregar una ruta
        absoluta desde nuestro método.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_externo = (
                ruta_temporal / "externo.sql"
            )

            archivo_externo.write_text(
                "SELECT 700;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.agregar_archivos(
                ruta_temporal,
                [
                    str(archivo_externo.resolve())
                ]
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "rutas relativas",
                resultado.error.lower()
            )

    def test_agregar_nombre_con_caracteres_especiales(self):
        """
        Comprueba que Git trate literalmente nombres que
        contienen caracteres especiales de pathspec.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_especial = (
                ruta_temporal
                / "paquete[1].sql"
            )

            archivo_especial.write_text(
                "SELECT 800;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.agregar_archivos(
                ruta_temporal,
                [
                    "paquete[1].sql"
                ]
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertEqual(
                len(cambios.cambios),
                1
            )

            self.assertEqual(
                cambios.cambios[0].ruta,
                "paquete[1].sql"
            )

            self.assertTrue(
                cambios.cambios[0].preparado
            )

if __name__ == "__main__":
    unittest.main()
