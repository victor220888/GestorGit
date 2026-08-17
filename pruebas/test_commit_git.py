import tempfile
import unittest
from pathlib import Path

from servicio_git import ServicioGit


class PruebasCommitGit(unittest.TestCase):
    """
    Pruebas específicas de la creación de commits.

    Todos los repositorios utilizados son temporales.
    Nunca modificamos repositorios reales.
    """

    def inicializar_repositorio(
        self,
        ruta_repositorio,
        configurar_identidad=True
    ):
        """
        Inicializa un repositorio Git temporal.

        Opcionalmente configura una identidad local
        exclusiva para las pruebas.
        """

        servicio_git = ServicioGit()

        resultado_init = servicio_git.ejecutar_git(
            argumentos=["init"],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_init.exitoso,
            resultado_init.error
        )

        if configurar_identidad:
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

        return servicio_git

    def crear_archivo_y_preparar(
        self,
        servicio_git,
        ruta_repositorio,
        nombre="nuevo.sql",
        contenido="SELECT 1;\n"
    ):
        """
        Crea un archivo dentro del repositorio
        y lo prepara para commit.
        """

        archivo = (
            ruta_repositorio
            / nombre
        )

        archivo.write_text(
            contenido,
            encoding="utf-8"
        )

        resultado = servicio_git.agregar_archivos(
            ruta_repositorio,
            [
                nombre
            ]
        )

        self.assertTrue(
            resultado.exitoso,
            resultado.error
        )

        return archivo

    def obtener_ruta_git_interna(
        self,
        servicio_git,
        ruta_repositorio,
        nombre
    ):
        """
        Obtiene una ruta interna de Git para utilizarla
        solamente dentro de las pruebas.
        """

        resultado = servicio_git.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--git-path",
                nombre
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado.exitoso,
            resultado.error
        )

        ruta = Path(
            resultado.salida
        )

        if not ruta.is_absolute():
            ruta = (
                ruta_repositorio
                / ruta
            )

        return ruta

    def test_crear_commit_correctamente(self):
        """
        Comprueba la creación de un primer commit.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git = self.inicializar_repositorio(
                ruta_temporal
            )

            self.crear_archivo_y_preparar(
                servicio_git,
                ruta_temporal
            )

            resultado = servicio_git.crear_commit(
                ruta_temporal,
                "Commit inicial de prueba"
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            estado = servicio_git.analizar_repositorio(
                ruta_temporal
            )

            self.assertTrue(
                estado.tiene_commits
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertEqual(
                len(cambios.cambios),
                0
            )

            resultado_mensaje = servicio_git.ejecutar_git(
                argumentos=[
                    "log",
                    "-1",
                    "--pretty=%s"
                ],
                ruta_repositorio=ruta_temporal
            )

            self.assertEqual(
                resultado_mensaje.salida,
                "Commit inicial de prueba"
            )

    def test_commit_rechaza_mensaje_vacio(self):
        """
        Comprueba que no se permita un mensaje vacío.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git = self.inicializar_repositorio(
                ruta_temporal
            )

            self.crear_archivo_y_preparar(
                servicio_git,
                ruta_temporal
            )

            resultado = servicio_git.crear_commit(
                ruta_temporal,
                "   "
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "mensaje",
                resultado.error.lower()
            )

    def test_commit_rechaza_sin_archivos_preparados(self):
        """
        Comprueba que no se permita crear un commit
        cuando no existen archivos preparados.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git = self.inicializar_repositorio(
                ruta_temporal
            )

            # Creamos un archivo, pero NO lo preparamos.
            archivo = (
                ruta_temporal
                / "pendiente.sql"
            )

            archivo.write_text(
                "SELECT 2;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.crear_commit(
                ruta_temporal,
                "No debería crearse"
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "preparados",
                resultado.error.lower()
            )

    def test_commit_rechaza_archivo_modificado_despues_de_preparar(self):
        """
        Comprueba que se bloquee un commit cuando un archivo
        fue modificado después de ejecutar git add.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git = self.inicializar_repositorio(
                ruta_temporal
            )

            archivo = self.crear_archivo_y_preparar(
                servicio_git,
                ruta_temporal
            )

            # Modificamos nuevamente el archivo después de prepararlo.
            archivo.write_text(
                "SELECT 999;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.crear_commit(
                ruta_temporal,
                "Commit que debe bloquearse"
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "después",
                resultado.error.lower()
            )

    def test_commit_rechaza_merge_en_curso(self):
        """
        Comprueba que no se permita un commit normal
        cuando detectamos una operación merge en curso.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git = self.inicializar_repositorio(
                ruta_temporal
            )

            self.crear_archivo_y_preparar(
                servicio_git,
                ruta_temporal
            )

            ruta_merge_head = self.obtener_ruta_git_interna(
                servicio_git,
                ruta_temporal,
                "MERGE_HEAD"
            )

            ruta_merge_head.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            ruta_merge_head.write_text(
                "0000000000000000000000000000000000000000\n",
                encoding="utf-8"
            )

            resultado = servicio_git.crear_commit(
                ruta_temporal,
                "Commit que debe bloquearse"
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "merge",
                resultado.error.lower()
            )

    def test_commit_rechaza_index_lock(self):
        """
        Comprueba que nunca intentemos eliminar
        index.lock automáticamente.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git = self.inicializar_repositorio(
                ruta_temporal
            )

            self.crear_archivo_y_preparar(
                servicio_git,
                ruta_temporal
            )

            ruta_index_lock = self.obtener_ruta_git_interna(
                servicio_git,
                ruta_temporal,
                "index.lock"
            )

            ruta_index_lock.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            ruta_index_lock.write_text(
                "",
                encoding="utf-8"
            )

            resultado = servicio_git.crear_commit(
                ruta_temporal,
                "Commit que debe bloquearse"
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "index.lock",
                resultado.error.lower()
            )

            # El archivo debe seguir existiendo porque nuestra
            # aplicación nunca lo elimina automáticamente.
            self.assertTrue(
                ruta_index_lock.exists()
            )

    def test_commit_rechaza_identidad_vacia(self):
        """
        Comprueba que user.name vacío bloquee el commit.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(
                carpeta_temporal
            )

            servicio_git = self.inicializar_repositorio(
                ruta_temporal
            )

            self.crear_archivo_y_preparar(
                servicio_git,
                ruta_temporal
            )

            # Configuramos expresamente un nombre vacío
            # para que la configuración local prevalezca.
            resultado_config = servicio_git.ejecutar_git(
                argumentos=[
                    "config",
                    "user.name",
                    ""
                ],
                ruta_repositorio=ruta_temporal
            )

            self.assertTrue(
                resultado_config.exitoso,
                resultado_config.error
            )

            resultado = servicio_git.crear_commit(
                ruta_temporal,
                "Commit que debe bloquearse"
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "user.name",
                resultado.error.lower()
            )


if __name__ == "__main__":
    unittest.main()