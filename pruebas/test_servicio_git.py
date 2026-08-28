import tempfile
import types
import unittest
from pathlib import Path

from modelos import CambioArchivo, ResultadoCambios, ResultadoComando
from modelos_reservas import (
    ManifiestoProyecto,
    ReglaLayoutOracle,
    ResultadoValidacionReservaPropia,
)
from servicio_git import ServicioGit
from servicio_objetos_oracle import ServicioObjetosOracle
from servicio_proteccion_reservas_git import ServicioProteccionReservasGit


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

        # Configuramos nombre solamente para este repositorio.
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

        # Configuramos correo solamente para este repositorio.
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

        # Creamos un archivo base.
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
        devuelva una lista vacía.
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
        Comprueba la detección de un archivo nuevo.
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
        Comprueba la detección de un archivo nuevo preparado.
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
        Comprueba la detección de un archivo modificado.
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
        Comprueba la detección de un archivo modificado preparado.
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
        Comprueba la detección de un archivo eliminado.
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

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
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
        Comprueba la detección de un archivo eliminado preparado.
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
        Comprueba nombres de archivo que contienen espacios.
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
        Comprueba que un archivo modificado pueda prepararse.
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
        Comprueba que la eliminación pueda prepararse.
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
        Comprueba que no se permita una operación sin archivos.
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
        Comprueba que no se permita una ruta absoluta.
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
        Comprueba nombres con caracteres especiales de pathspec.
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

    def test_quitar_archivo_nuevo_preparado(self):
        """
        Comprueba que un archivo nuevo pueda quitarse
        del área preparada sin eliminarse del disco.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_git, _ = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_nuevo = ruta_temporal / "nuevo.sql"

            archivo_nuevo.write_text(
                "SELECT 900;\n",
                encoding="utf-8"
            )

            servicio_git.agregar_archivos(
                ruta_temporal,
                ["nuevo.sql"]
            )

            resultado = (
                servicio_git.quitar_archivos_preparados(
                    ruta_temporal,
                    ["nuevo.sql"]
                )
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            # El archivo físico debe continuar existiendo.
            self.assertTrue(
                archivo_nuevo.exists()
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            cambio = cambios.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Nuevo"
            )

            self.assertFalse(
                cambio.preparado
            )

    def test_quitar_archivo_modificado_preparado(self):
        """
        Comprueba que un archivo modificado vuelva
        al estado no preparado.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_git, archivo_base = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_base.write_text(
                "SELECT 1000;\n",
                encoding="utf-8"
            )

            servicio_git.agregar_archivos(
                ruta_temporal,
                ["archivo_base.sql"]
            )

            resultado = (
                servicio_git.quitar_archivos_preparados(
                    ruta_temporal,
                    ["archivo_base.sql"]
                )
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            cambio = cambios.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Modificado"
            )

            self.assertFalse(
                cambio.preparado
            )

    def test_quitar_archivo_eliminado_preparado(self):
        """
        Comprueba que una eliminación preparada pueda
        quitarse del área preparada.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_git, archivo_base = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_base.unlink()

            servicio_git.agregar_archivos(
                ruta_temporal,
                ["archivo_base.sql"]
            )

            resultado = (
                servicio_git.quitar_archivos_preparados(
                    ruta_temporal,
                    ["archivo_base.sql"]
                )
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            cambio = cambios.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Eliminado"
            )

            self.assertFalse(
                cambio.preparado
            )

    def test_quitar_preparado_sin_commit_inicial(self):
        """
        Comprueba el caso especial de un repositorio
        que todavía no tiene ningún commit.
        """

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_git = ServicioGit()

            resultado_init = servicio_git.ejecutar_git(
                argumentos=["init"],
                ruta_repositorio=ruta_temporal
            )

            self.assertTrue(
                resultado_init.exitoso,
                resultado_init.error
            )

            archivo_nuevo = ruta_temporal / "primero.sql"

            archivo_nuevo.write_text(
                "SELECT 1100;\n",
                encoding="utf-8"
            )

            servicio_git.agregar_archivos(
                ruta_temporal,
                ["primero.sql"]
            )

            resultado = (
                servicio_git.quitar_archivos_preparados(
                    ruta_temporal,
                    ["primero.sql"]
                )
            )

            self.assertTrue(
                resultado.exitoso,
                resultado.error
            )

            # rm --cached no debe eliminar el archivo físico.
            self.assertTrue(
                archivo_nuevo.exists()
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            cambio = cambios.cambios[0]

            self.assertEqual(
                cambio.descripcion,
                "Nuevo"
            )

            self.assertFalse(
                cambio.preparado
            )


# =================================================================
# Conflictos estructurales (en_conflicto en CambioArchivo)
# =================================================================

CODIGOS_CONFLICTO = (
    "DD",
    "AU",
    "UD",
    "UA",
    "DU",
    "AA",
    "UU",
)


class ServicioGitEspiaEstado(ServicioGit):
    """
    Intercepta únicamente la consulta de git status para simular
    códigos de conflicto. El resto de comandos se delega en
    ServicioGit real (repositorios temporales con Git real).
    """

    def __init__(
        self,
        salida_porcelain="",
        error_estado=False
    ):
        super().__init__()
        self.salida_porcelain = salida_porcelain
        self.error_estado = error_estado
        self.comandos = []

    def _ejecutar_git_interno(self, argumentos, ruta_repositorio=None, tiempo_maximo=30):
        self.comandos.append(tuple(argumentos))

        if argumentos and argumentos[0] == "status":
            if self.error_estado:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=1,
                    salida="",
                    error="Error simulado de git status.",
                    comando=" ".join(argumentos)
                )

            return ResultadoComando(
                exitoso=True,
                codigo_salida=0,
                salida=self.salida_porcelain,
                error="",
                comando=" ".join(argumentos)
            )

        return super()._ejecutar_git_interno(
            argumentos,
            ruta_repositorio=ruta_repositorio
        )


class ServicioGitEspiaCambios(ServicioGit):
    """
    Reemplaza la consulta de cambios por completo (sin tocar
    repositorios) para probar la decisión estructural de
    crear_commit sin depender del texto de la descripción.
    """

    def __init__(self, cambios):
        super().__init__()
        self.cambios = cambios

    def obtener_cambios(self, ruta_repositorio):
        return ResultadoCambios(
            exitoso=True,
            cambios=self.cambios
        )


def tiene_comando_prohibido(
    comandos,
    verbos_prohibidos
):
    """
    Devuelve True si algún comando registrado contiene uno de
    los verbos productivos que no debieron ejecutarse.

    Reconoce el verbo Git aunque existan opciones globales delante
    (p. ej. --literal-pathspecs). Solo se examinan los argumentos
    anteriores al primer "--": una ruta situada después de "--"
    nunca se confunde con un verbo. La comparación es de igualdad
    exacta, sin substring.
    """

    for argumentos in comandos:
        argumentos_antes_doble_guion = []

        for argumento in argumentos:
            if argumento == "--":
                break

            argumentos_antes_doble_guion.append(argumento)

        for verbo in verbos_prohibidos:
            if verbo in argumentos_antes_doble_guion:
                return True

    return False


class PruebasConflictoEstructurado(unittest.TestCase):
    """
    Un conflicto es un estado especial: no es "preparado" ni
    "sin preparar", y bloquea las acciones de staging.
    """

    def preparar_repositorio_con_commit(
        self,
        ruta_repositorio
    ):
        """
        Reutiliza el helper de PruebasServicioGit sin heredar
        sus métodos de prueba.
        """

        return PruebasServicioGit().preparar_repositorio_con_commit(
            ruta_repositorio
        )

    def test_cambio_archivo_expone_en_conflicto_con_default_false(self):
        cambio = CambioArchivo(
            ruta="archivo.sql",
            estado_indice=" ",
            estado_trabajo="M",
            descripcion="Modificado",
            preparado=False
        )

        self.assertFalse(
            cambio.en_conflicto
        )

    def test_obtener_cambios_identifica_los_siete_conflictos(self):
        salida = "".join(
            f"{codigo} conflicto_{codigo}.sql\0"
            for codigo in CODIGOS_CONFLICTO
        )

        servicio = ServicioGitEspiaEstado(
            salida_porcelain=salida
        )

        resultado = servicio.obtener_cambios(
            "/ruta/irrelevante"
        )

        self.assertTrue(
            resultado.exitoso,
            resultado.error
        )

        self.assertEqual(
            len(resultado.cambios),
            7
        )

        for cambio, codigo in zip(
            resultado.cambios,
            CODIGOS_CONFLICTO
        ):
            self.assertTrue(
                cambio.en_conflicto,
                f"El par {codigo} no quedó marcado como conflicto."
            )

            # Semántica histórica conservada: el índice contiene
            # información (la posición no es un espacio), por lo
            # que preparado sigue siendo True a nivel de modelo.
            self.assertTrue(
                cambio.preparado
            )

            # Los conflictos nunca son actualizables.
            self.assertFalse(
                cambio.requiere_actualizar_preparado
            )

            self.assertEqual(
                cambio.descripcion,
                "Conflicto"
            )

    def test_estados_normales_no_quedan_marcados_como_conflicto(self):
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_git, archivo_base = (
                self.preparar_repositorio_con_commit(
                    ruta_temporal
                )
            )

            archivo_nuevo = ruta_temporal / "nuevo.sql"

            archivo_nuevo.write_text(
                "SELECT 1;\n",
                encoding="utf-8"
            )

            archivo_base.write_text(
                "SELECT 2;\n",
                encoding="utf-8"
            )

            servicio_git.agregar_archivos(
                ruta_temporal,
                ["archivo_base.sql"]
            )

            archivo_base.write_text(
                "SELECT 3;\n",
                encoding="utf-8"
            )

            resultado = servicio_git.obtener_cambios(
                ruta_temporal
            )

            cambios = {
                cambio.ruta: cambio
                for cambio in resultado.cambios
            }

            self.assertTrue(
                cambios["nuevo.sql"].en_conflicto is False
            )

            self.assertTrue(
                cambios["archivo_base.sql"].en_conflicto is False
            )

            self.assertTrue(
                cambios["archivo_base.sql"].requiere_actualizar_preparado
            )

    def test_agregar_archivo_en_conflicto_real_es_bloqueado(self):
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_git, archivo_conflicto = (
                self.preparar_repositorio_con_conflicto(
                    ruta_temporal
                )
            )

            resultado = servicio_git.agregar_archivos(
                ruta_temporal,
                [archivo_conflicto.name]
            )

            self.assertFalse(
                resultado.exitoso,
                "Un conflicto no debe poder prepararse."
            )

            self.assertIn(
                "conflicto",
                resultado.error.lower()
            )

            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                cambios.cambios[0].en_conflicto
            )

    def test_agregar_en_conflicto_no_ejecuta_git_add(self):
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_espia = ServicioGitEspiaEstado(
                salida_porcelain="UU conflicto.sql\0"
            )

            self.preparar_repositorio_con_commit(
                ruta_temporal
            )

            resultado = servicio_espia.agregar_archivos(
                ruta_temporal,
                ["conflicto.sql"]
            )

            self.assertFalse(
                resultado.exitoso,
                resultado.error
            )

            self.assertFalse(
                tiene_comando_prohibido(
                    servicio_espia.comandos,
                    ("add",)
                ),
                "Se ejecutó git add sobre un conflicto."
            )

    def test_quitar_archivo_en_conflicto_real_es_bloqueado(self):
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_git, archivo_conflicto = (
                self.preparar_repositorio_con_conflicto(
                    ruta_temporal
                )
            )

            resultado = servicio_git.quitar_archivos_preparados(
                ruta_temporal,
                [archivo_conflicto.name]
            )

            self.assertFalse(
                resultado.exitoso,
                "Un conflicto no debe poder quitarse de preparados."
            )

            self.assertIn(
                "conflicto",
                resultado.error.lower()
            )

            # El estado unmerged del índice permanece intacto.
            cambios = servicio_git.obtener_cambios(
                ruta_temporal
            )

            self.assertTrue(
                cambios.cambios[0].en_conflicto
            )

            # El working tree conserva los marcadores de conflicto.
            contenido = archivo_conflicto.read_text(
                encoding="utf-8",
                errors="replace"
            )

            self.assertIn(
                "<<<<<<<",
                contenido
            )

    def test_quitar_en_conflicto_no_ejecuta_restore_ni_rm(self):
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_espia = ServicioGitEspiaEstado(
                salida_porcelain="UU conflicto.sql\0"
            )

            self.preparar_repositorio_con_commit(
                ruta_temporal
            )

            resultado = servicio_espia.quitar_archivos_preparados(
                ruta_temporal,
                ["conflicto.sql"]
            )

            self.assertFalse(
                resultado.exitoso,
                resultado.error
            )

            self.assertFalse(
                tiene_comando_prohibido(
                    servicio_espia.comandos,
                    ("restore", "rm")
                ),
                "Se ejecutó restore o rm sobre un conflicto."
            )

    def test_quitar_bloquea_si_la_consulta_de_estado_falla(self):
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_espia = ServicioGitEspiaEstado(
                error_estado=True
            )

            self.preparar_repositorio_con_commit(
                ruta_temporal
            )

            resultado = servicio_espia.quitar_archivos_preparados(
                ruta_temporal,
                ["archivo_base.sql"]
            )

            self.assertFalse(
                resultado.exitoso,
                "Un error de consulta debe bloquear la operación."
            )

            self.assertFalse(
                tiene_comando_prohibido(
                    servicio_espia.comandos,
                    ("restore", "rm")
                ),
                "Se ejecutó restore o rm sin poder verificar el estado."
            )

    def test_quitar_bloquea_archivo_que_ya_no_esta_preparado(self):
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_espia = ServicioGitEspiaEstado(
                salida_porcelain=" M archivo_base.sql\0"
            )

            self.preparar_repositorio_con_commit(
                ruta_temporal
            )

            resultado = servicio_espia.quitar_archivos_preparados(
                ruta_temporal,
                ["archivo_base.sql"]
            )

            self.assertFalse(
                resultado.exitoso
            )

            self.assertIn(
                "ya no está preparado",
                resultado.error
            )

            self.assertFalse(
                tiene_comando_prohibido(
                    servicio_espia.comandos,
                    ("restore", "rm")
                )
            )

    def test_actualizar_preparados_bloquea_conflicto(self):
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            servicio_espia = ServicioGitEspiaEstado(
                salida_porcelain="UU conflicto.sql\0"
            )

            self.preparar_repositorio_con_commit(
                ruta_temporal
            )

            resultado = (
                servicio_espia.actualizar_archivos_preparados(
                    ruta_temporal,
                    ["conflicto.sql"]
                )
            )

            self.assertFalse(
                resultado.exitoso,
                resultado.error
            )

            self.assertIn(
                "conflicto",
                resultado.error.lower()
            )

            self.assertFalse(
                tiene_comando_prohibido(
                    servicio_espia.comandos,
                    ("add",)
                ),
                "Se ejecutó git add sobre un conflicto."
            )

    def test_crear_commit_bloquea_por_en_conflicto_sin_texto(self):
        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_temporal = Path(carpeta_temporal)

            self.preparar_repositorio_con_commit(
                ruta_temporal
            )

            servicio_espia = ServicioGitEspiaCambios(
                cambios=[
                    CambioArchivo(
                        ruta="archivo.sql",
                        estado_indice="U",
                        estado_trabajo="U",
                        descripcion="Texto que no dice Conflicto",
                        preparado=True,
                        en_conflicto=True
                    )
                ]
            )

            resultado = servicio_espia.crear_commit(
                ruta_temporal,
                "Mensaje de prueba"
            )

            self.assertFalse(
                resultado.exitoso,
                "El commit debe bloquearse con un conflicto."
            )

            self.assertIn(
                "conflictos",
                resultado.error.lower()
            )

            # Ningún commit nuevo fue creado.
            historial = servicio_espia.ejecutar_git(
                argumentos=[
                    "log",
                    "--oneline"
                ],
                ruta_repositorio=ruta_temporal
            )

            self.assertEqual(
                len(historial.salida.strip().splitlines()),
                1
            )

    def preparar_repositorio_con_conflicto(
        self,
        ruta_repositorio
    ):
        """
        Crea un conflicto de merge REAL (UU) en el repositorio
        temporal: dos ramas modifican el mismo archivo y se
        intenta fusionarlas.

        Devuelve:
            servicio_git
            archivo_conflicto
        """

        servicio_git, _ = self.preparar_repositorio_con_commit(
            ruta_repositorio
        )

        archivo_conflicto = (
            ruta_repositorio / "conflicto.sql"
        )

        archivo_conflicto.write_text(
            "línea base\n",
            encoding="utf-8"
        )

        resultado_agregar = servicio_git.ejecutar_git(
            argumentos=[
                "add",
                "--",
                archivo_conflicto.name
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_agregar.exitoso,
            resultado_agregar.error
        )

        resultado_commit = servicio_git.ejecutar_git(
            argumentos=[
                "commit",
                "-m",
                "Agrega el archivo base del conflicto"
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_commit.exitoso,
            resultado_commit.error
        )

        # Una rama con otra versión del archivo.
        resultado_rama = servicio_git.ejecutar_git(
            argumentos=[
                "checkout",
                "-b",
                "rama_otra"
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_rama.exitoso,
            resultado_rama.error
        )

        archivo_conflicto.write_text(
            "versión rama\n",
            encoding="utf-8"
        )

        servicio_git.ejecutar_git(
            argumentos=[
                "add",
                "--",
                archivo_conflicto.name
            ],
            ruta_repositorio=ruta_repositorio
        )

        servicio_git.ejecutar_git(
            argumentos=[
                "commit",
                "-m",
                "Cambio en la rama"
            ],
            ruta_repositorio=ruta_repositorio
        )

        # Volvemos a la rama principal y escribimos otra versión.
        resultado_vuelta = servicio_git.ejecutar_git(
            argumentos=[
                "checkout",
                "master"
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(
            resultado_vuelta.exitoso,
            resultado_vuelta.error
        )

        archivo_conflicto.write_text(
            "versión master\n",
            encoding="utf-8"
        )

        servicio_git.ejecutar_git(
            argumentos=[
                "add",
                "--",
                archivo_conflicto.name
            ],
            ruta_repositorio=ruta_repositorio
        )

        servicio_git.ejecutar_git(
            argumentos=[
                "commit",
                "-m",
                "Cambio en master"
            ],
            ruta_repositorio=ruta_repositorio
        )

        # El merge produce un conflicto real (UU en porcelain).
        resultado_merge = servicio_git.ejecutar_git(
            argumentos=[
                "merge",
                "rama_otra"
            ],
            ruta_repositorio=ruta_repositorio
        )

        self.assertFalse(
            resultado_merge.exitoso,
            "El merge debería haber quedado en conflicto."
        )

        cambios = servicio_git.obtener_cambios(
            ruta_repositorio
        )

        self.assertTrue(
            len(cambios.cambios) >= 1
        )

        self.assertTrue(
            cambios.cambios[0].en_conflicto,
            "El merge no produjo un estado UU estructurado."
        )

        return servicio_git, archivo_conflicto


# =====================================================================
# Bloque E: integración de reservas con staging/commit protegido
# (GG-PROMPT-039 §12.2 y §12.3)
# =====================================================================

MANIFIESTO_MODO_EQUIPO = ManifiestoProyecto(
    format_version=1,
    project_uuid="22222222-2222-4222-8222-222222222222",
    oracle_layout=(
        ReglaLayoutOracle(
            carpeta="Paquetes",
            tipo="PACKAGE",
            extension=".pls",
        ),
    ),
)

CLAVE_FINI004 = "PACKAGE|FINI004"
CLAVE_FINI005 = "PACKAGE|FINI005"
CLAVE_FINI009 = "PACKAGE|FINI009"
CLAVE_FINI011 = "PACKAGE|FINI011"


def _resultado_reserva(valida, motivo=""):
    return ResultadoValidacionReservaPropia(
        valida=valida,
        motivo=motivo,
    )


class ReservasPrueba:
    """
    Doble del ServicioReservas de Bloque D para integración.

    Solo expone validar_reserva_propia_fresca (la única API que
    Bloque E está autorizado a usar). Cualquier otro método
    (consultar/reservar/renovar/liberar/tomar_vencida o red)
    lanza AssertionError.
    """

    def __init__(self, resultados=None, cola=None, valida=False,
                 motivo="No hay una consulta previa verificada."):
        self.llamadas = []
        self.resultados = resultados or {}
        self.cola = cola or []
        self.valida = valida
        self.motivo = motivo

    def validar_reserva_propia_fresca(self, clave_objeto):
        self.llamadas.append(clave_objeto)
        if self.cola:
            return self.cola.pop(0)
        if clave_objeto in self.resultados:
            return self.resultados[clave_objeto]
        return ResultadoValidacionReservaPropia(
            valida=self.valida,
            motivo=self.motivo,
        )

    def __getattr__(self, nombre):
        if nombre.startswith("_"):
            raise AttributeError(nombre)
        raise AssertionError(
            f"El protector llamó a '{nombre}': prohibido en "
            "Bloque E (protección 100% local)."
        )


class ServicioGitEspiaComandos(ServicioGit):
    """Registra cada comando Git ejecutado."""

    def __init__(self, protector_reservas=None):
        super().__init__(protector_reservas=protector_reservas)
        self.comandos = []

    def _ejecutar_git_interno(
        self,
        argumentos,
        ruta_repositorio=None,
        tiempo_maximo=30
    ):
        self.comandos.append(list(argumentos))
        return super()._ejecutar_git_interno(
            argumentos,
            ruta_repositorio=ruta_repositorio,
            tiempo_maximo=tiempo_maximo,
        )


class ServicioGitStagedInestable(ServicioGitEspiaComandos):
    """Simula que el staged set cambia durante la validación."""

    def __init__(self, protector_reservas=None):
        super().__init__(protector_reservas=protector_reservas)
        self.lecturas_staged = 0

    def _leer_staged_set(self, ruta_repositorio):
        self.lecturas_staged += 1
        if self.lecturas_staged == 2:
            return (
                True,
                [("A", "Paquetes/OTRO.pls", "")],
                "",
            )
        return super()._leer_staged_set(ruta_repositorio)


class _BaseProteccionIntegracion(unittest.TestCase):
    """
    Repositorio temporal con un commit inicial que contiene un
    archivo ordinario y dos objetos Oracle (FINI004 y FINI005),
    más un archivo con apariencia Oracle no resoluble sin
    preparar (Sospechoso/algo.sql).
    """

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temporal.name)

        self.reservas = ReservasPrueba()
        self.protector = ServicioProteccionReservasGit(
            resolvedor_oracle=ServicioObjetosOracle(
                MANIFIESTO_MODO_EQUIPO
            ),
            servicio_reservas=self.reservas,
            project_uuid=MANIFIESTO_MODO_EQUIPO.project_uuid,
        )
        # Servicio SIN protector para montar el estado del fixture
        # (init/config/add/commit): nunca se demuestra el fixture
        # a traves del bypass que el Bloque E cierra (REV1 FIX 1).
        self.servicio_base = ServicioGit()
        self.servicio = ServicioGit(
            protector_reservas=self.protector
        )

        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["init"],
                ruta_repositorio=self.ruta
            ).exitoso
        )

        self.servicio_base.ejecutar_git(
            argumentos=["config", "user.name", "Usuario Prueba"],
            ruta_repositorio=self.ruta
        )
        self.servicio_base.ejecutar_git(
            argumentos=[
                "config",
                "user.email",
                "prueba@example.com"
            ],
            ruta_repositorio=self.ruta
        )

        (self.ruta / "archivo_base.txt").write_text(
            "SELECT 1;\n",
            encoding="utf-8"
        )

        paquetes = self.ruta / "Paquetes"
        paquetes.mkdir()
        (paquetes / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004;\n",
            encoding="utf-8"
        )
        (paquetes / "FINI005.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI005;\n",
            encoding="utf-8"
        )

        for ruta_archivo in (
            "archivo_base.txt",
            "Paquetes/FINI004.pls",
            "Paquetes/FINI005.pls",
        ):
            resultado = self.servicio_base.ejecutar_git(
                argumentos=["add", "--", ruta_archivo],
                ruta_repositorio=self.ruta
            )
            self.assertTrue(resultado.exitoso)

        resultado_commit = self.servicio_base.ejecutar_git(
            argumentos=[
                "commit",
                "-m",
                "Commit inicial de prueba"
            ],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado_commit.exitoso)

        sospechoso = self.ruta / "Sospechoso"
        sospechoso.mkdir()
        (sospechoso / "algo.sql").write_text(
            "SELECT 2;\n",
            encoding="utf-8"
        )

    def tearDown(self):
        self.temporal.cleanup()

    def hash_head(self):
        resultado = self.servicio_base.ejecutar_git(
            argumentos=["rev-parse", "HEAD"],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado.exitoso)
        return resultado.salida.strip()

    def staged_set(self):
        exitoso, entradas, _error = self.servicio._leer_staged_set(
            self.ruta
        )
        self.assertTrue(exitoso)
        return entradas


class PruebasProteccionStaging(_BaseProteccionIntegracion):
    """12.2.20-29: staging protegido sin bypass."""

    def test_sin_protector_staging_historico_sigue_funcionando(self):
        servicio_simple = ServicioGit()
        resultado = servicio_simple.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI004.pls"]
        )
        self.assertTrue(resultado.exitoso, resultado.error)

    def test_protector_permite_staging_con_reserva_valida(self):
        self.reservas.valida = True
        self.reservas.motivo = "Reserva propia fresca valida."
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v2;\n",
            encoding="utf-8"
        )
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI004.pls"]
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        estados = {
            entrada[1]: entrada[0]
            for entrada in self.staged_set()
        }
        self.assertEqual(
            estados.get("Paquetes/FINI004.pls"),
            "M"
        )

    def test_protector_bloquea_indice_sin_cambios_y_sin_add(self):
        servicio_espia = ServicioGitEspiaComandos(
            protector_reservas=self.protector
        )
        self.reservas.valida = False

        resultado = servicio_espia.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI004.pls"]
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("bloqueada", resultado.error)
        # El índice queda lógicamente sin cambios.
        self.assertEqual(self.staged_set(), [])
        # git add NO se ejecutó.
        for comando in servicio_espia.comandos:
            self.assertNotIn("add", comando)

    def test_ordinario_mas_oracle_valido_permitido(self):
        (self.ruta / "archivo_base.txt").write_text(
            "SELECT 12;\n",
            encoding="utf-8"
        )
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v2;\n",
            encoding="utf-8"
        )
        self.reservas.valida = True
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["archivo_base.txt", "Paquetes/FINI004.pls"]
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        rutas_staged = {
            entrada[1] for entrada in self.staged_set()
        }
        self.assertEqual(
            rutas_staged,
            {"archivo_base.txt", "Paquetes/FINI004.pls"}
        )

    def test_mixto_con_oracle_bloqueado_sin_staging_parcial(self):
        (self.ruta / "archivo_base.txt").write_text(
            "SELECT 13;\n",
            encoding="utf-8"
        )
        self.reservas.valida = False
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["archivo_base.txt", "Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado.exitoso)
        # Ni el archivo ordinario entró: no hay staging parcial.
        self.assertEqual(self.staged_set(), [])

    def test_delete_oracle_requiere_reserva(self):
        (self.ruta / "Paquetes" / "FINI004.pls").unlink()

        self.reservas.resultados = {
            CLAVE_FINI004: _resultado_reserva(
                False,
                "La reserva esta vencida."
            ),
        }
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn("vencida", resultado.error)

        self.reservas.resultados = {
            CLAVE_FINI004: _resultado_reserva(True, "ok"),
        }
        resultado_valido = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI004.pls"]
        )
        self.assertTrue(resultado_valido.exitoso)
        estados = {
            entrada[1]: entrada[0]
            for entrada in self.staged_set()
        }
        self.assertEqual(
            estados.get("Paquetes/FINI004.pls"),
            "D"
        )

    def test_rename_oracle_considera_ambos_lados(self):
        paquetes = self.ruta / "Paquetes"
        # Contenido idéntico para que Git detecte el renombrado.
        (paquetes / "FINI009.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004;\n",
            encoding="utf-8"
        )
        (paquetes / "FINI004.pls").unlink()

        self.reservas.valida = True
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI004.pls", "Paquetes/FINI009.pls"]
        )
        self.assertTrue(resultado.exitoso, resultado.error)

        renombres = [
            entrada for entrada in self.staged_set()
            if entrada[0] == "R"
        ]
        self.assertEqual(len(renombres), 1)
        self.assertEqual(renombres[0][1], "Paquetes/FINI009.pls")
        self.assertEqual(renombres[0][2], "Paquetes/FINI004.pls")

        # Actualizar preparados del destino: la protección debe
        # exigir también la reserva del lado origen, reutilizando
        # ruta_anterior del modelo existente.
        (paquetes / "FINI009.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004_v2;\n",
            encoding="utf-8"
        )
        self.reservas.llamadas.clear()
        self.reservas.valida = False
        self.reservas.resultados = {
            CLAVE_FINI009: _resultado_reserva(True, "ok"),
        }

        resultado_bloqueado = self.servicio.actualizar_archivos_preparados(
            self.ruta,
            ["Paquetes/FINI009.pls"]
        )
        self.assertFalse(resultado_bloqueado.exitoso)
        self.assertIn(CLAVE_FINI004, resultado_bloqueado.error)
        self.assertEqual(
            self.reservas.llamadas,
            [CLAVE_FINI009, CLAVE_FINI004]
        )

        self.reservas.resultados[CLAVE_FINI004] = _resultado_reserva(
            True, "ok"
        )
        resultado_ok = self.servicio.actualizar_archivos_preparados(
            self.ruta,
            ["Paquetes/FINI009.pls"]
        )
        self.assertTrue(resultado_ok.exitoso, resultado_ok.error)

    def test_todas_entradas_publicas_staging_cubiertas_sin_bypass(self):
        self.reservas.valida = False

        # agregar_archivos bloquea.
        resultado_add = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado_add.exitoso)

        # Preparar el archivo con un servicio sin protector y
        # modificarlo: actualizar_archivos_preparados también
        # bloquea (no existe bypass público).
        servicio_simple = ServicioGit()
        self.assertTrue(
            servicio_simple.agregar_archivos(
                self.ruta,
                ["Paquetes/FINI004.pls"]
            ).exitoso
        )
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE BODY FINI004;\n",
            encoding="utf-8"
        )
        resultado_actualizar = self.servicio.actualizar_archivos_preparados(
            self.ruta,
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado_actualizar.exitoso)

    def test_unstaging_mantiene_comportamiento_historico(self):
        servicio_simple = ServicioGit()
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v2;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            servicio_simple.agregar_archivos(
                self.ruta,
                ["Paquetes/FINI004.pls"]
            ).exitoso
        )

        # Las reservas deniegan todo; quitar de preparados NO
        # consulta reservas y conserva el comportamiento histórico.
        self.reservas.valida = False
        resultado = self.servicio.quitar_archivos_preparados(
            self.ruta,
            ["Paquetes/FINI004.pls"]
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertEqual(self.reservas.llamadas, [])
        self.assertEqual(self.staged_set(), [])


class PruebasProteccionCommit(_BaseProteccionIntegracion):
    """12.3.30-42: commit revalida el conjunto preparado REAL."""

    def test_sin_protector_commit_historico_sigue_funcionando(self):
        servicio_simple = ServicioGit()
        (self.ruta / "archivo_base.txt").write_text(
            "SELECT 11;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            servicio_simple.agregar_archivos(
                self.ruta,
                ["archivo_base.txt"]
            ).exitoso
        )
        resultado = servicio_simple.crear_commit(
            self.ruta,
            "Commit sin protector"
        )
        self.assertTrue(resultado.exitoso, resultado.error)

    def test_staged_ordinario_commit_permitido(self):
        (self.ruta / "archivo_base.txt").write_text(
            "SELECT 12;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio.agregar_archivos(
                self.ruta,
                ["archivo_base.txt"]
            ).exitoso
        )
        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit de archivo ordinario"
        )
        self.assertTrue(resultado.exitoso, resultado.error)

    def test_staged_oracle_reserva_valida_commit_permitido(self):
        self.reservas.valida = True
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v2;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio.agregar_archivos(
                self.ruta,
                ["Paquetes/FINI004.pls"]
            ).exitoso
        )
        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit de objeto Oracle con reserva"
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        # Staging y commit validaron la reserva.
        self.assertEqual(
            self.reservas.llamadas,
            [CLAVE_FINI004, CLAVE_FINI004]
        )

    def test_staged_oracle_sin_reserva_commit_bloqueado(self):
        servicio_simple = ServicioGit()
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v3;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            servicio_simple.agregar_archivos(
                self.ruta,
                ["Paquetes/FINI004.pls"]
            ).exitoso
        )

        self.reservas.valida = False
        hash_antes = self.hash_head()

        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit que debe bloquearse"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("bloqueada", resultado.error)
        self.assertEqual(self.hash_head(), hash_antes)

    def test_reserva_stale_tras_staging_commit_bloqueado(self):
        # La reserva era válida al hacer staging y quedó stale
        # antes del commit: el commit debe BLOQUEARSE.
        self.reservas.cola = [
            _resultado_reserva(True, "ok"),
            _resultado_reserva(
                False,
                "Verificacion con mas de 60 s de frescura."
            ),
        ]
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v4;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio.agregar_archivos(
                self.ruta,
                ["Paquetes/FINI004.pls"]
            ).exitoso
        )

        hash_antes = self.hash_head()
        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit con reserva stale"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("frescura", resultado.error)
        self.assertEqual(self.hash_head(), hash_antes)

    def test_margen_insuficiente_al_commit_bloqueado(self):
        self.reservas.cola = [
            _resultado_reserva(True, "ok"),
            _resultado_reserva(
                False,
                "Tiempo restante menor al margen minimo (300 s)."
            ),
        ]
        (self.ruta / "Paquetes" / "FINI005.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI005 v2;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio.agregar_archivos(
                self.ruta,
                ["Paquetes/FINI005.pls"]
            ).exitoso
        )
        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit con margen insuficiente"
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn("margen", resultado.error)

    def test_staged_externo_commit_igualmente_protegido(self):
        # El archivo Oracle fue preparado FUERA de GestorGit
        # (git add directo): el commit con protector se bloquea
        # igualmente porque revalida el conjunto preparado REAL.
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v5;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["add", "--", "Paquetes/FINI004.pls"],
                ruta_repositorio=self.ruta
            ).exitoso
        )

        self.reservas.valida = False
        hash_antes = self.hash_head()

        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit con staging externo"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("bloqueada", resultado.error)
        self.assertEqual(self.hash_head(), hash_antes)
        # El índice conserva la entrada preparada externa.
        estados = {
            entrada[1]: entrada[0]
            for entrada in self.staged_set()
        }
        self.assertEqual(
            estados.get("Paquetes/FINI004.pls"),
            "M"
        )

    def test_staged_mixto_uno_bloqueado_no_commit(self):
        (self.ruta / "archivo_base.txt").write_text(
            "SELECT 13;\n",
            encoding="utf-8"
        )
        (self.ruta / "Paquetes" / "FINI005.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI005 v3;\n",
            encoding="utf-8"
        )
        servicio_simple = ServicioGit()
        self.assertTrue(
            servicio_simple.agregar_archivos(
                self.ruta,
                ["archivo_base.txt", "Paquetes/FINI005.pls"]
            ).exitoso
        )

        self.reservas.resultados = {
            CLAVE_FINI004: _resultado_reserva(True, "ok"),
        }
        hash_antes = self.hash_head()
        staged_antes = self.staged_set()

        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit mixto que debe bloquearse"
        )

        self.assertFalse(resultado.exitoso)
        self.assertEqual(self.hash_head(), hash_antes)
        self.assertEqual(self.staged_set(), staged_antes)

    def test_rename_staged_origen_y_destino_protegidos(self):
        paquetes = self.ruta / "Paquetes"
        (paquetes / "FINI009.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004;\n",
            encoding="utf-8"
        )
        (paquetes / "FINI004.pls").unlink()

        servicio_simple = ServicioGit()
        self.assertTrue(
            servicio_simple.agregar_archivos(
                self.ruta,
                ["Paquetes/FINI004.pls", "Paquetes/FINI009.pls"]
            ).exitoso
        )
        renombres = [
            entrada for entrada in self.staged_set()
            if entrada[0] == "R"
        ]
        self.assertEqual(len(renombres), 1)

        # Solo el origen tiene reserva: el commit debe bloquearse
        # porque el DESTINO también está protegido.
        self.reservas.valida = False
        self.reservas.resultados = {
            CLAVE_FINI004: _resultado_reserva(True, "ok"),
        }
        hash_antes = self.hash_head()

        resultado_bloqueado = self.servicio.crear_commit(
            self.ruta,
            "Commit de renombrado bloqueado"
        )
        self.assertFalse(resultado_bloqueado.exitoso)
        self.assertIn(CLAVE_FINI009, resultado_bloqueado.error)
        self.assertEqual(self.hash_head(), hash_antes)

        # Con ambos lados con reserva: el commit funciona y
        # valida AMBAS claves (origen y destino).
        self.reservas.llamadas.clear()
        self.reservas.resultados[CLAVE_FINI009] = (
            _resultado_reserva(True, "ok")
        )
        resultado_ok = self.servicio.crear_commit(
            self.ruta,
            "Commit de renombrado permitido"
        )
        self.assertTrue(resultado_ok.exitoso, resultado_ok.error)
        self.assertNotEqual(self.hash_head(), hash_antes)
        self.assertEqual(
            sorted(self.reservas.llamadas),
            [CLAVE_FINI004, CLAVE_FINI009]
        )

    def test_staged_cambia_entre_snapshot_y_relectura_bloqueado(self):
        servicio_inestable = ServicioGitStagedInestable(
            protector_reservas=self.protector
        )
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v6;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["add", "--", "Paquetes/FINI004.pls"],
                ruta_repositorio=self.ruta
            ).exitoso
        )

        self.reservas.valida = True
        hash_antes = self.hash_head()

        resultado = servicio_inestable.crear_commit(
            self.ruta,
            "Commit con staged set cambiante"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("cambió", resultado.error)
        self.assertEqual(self.hash_head(), hash_antes)
        # El git commit NO se ejecutó.
        for comando in servicio_inestable.comandos:
            self.assertNotIn("commit", comando)

    def test_commit_bloqueado_no_altera_indice_ni_head(self):
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v7;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["add", "--", "Paquetes/FINI004.pls"],
                ruta_repositorio=self.ruta
            ).exitoso
        )

        self.reservas.valida = False
        hash_antes = self.hash_head()
        staged_antes = self.staged_set()

        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit bloqueado indice intacto"
        )

        self.assertFalse(resultado.exitoso)
        self.assertEqual(self.hash_head(), hash_antes)
        self.assertEqual(self.staged_set(), staged_antes)

    def test_no_ejecutar_git_commit_antes_de_proteccion_positiva(self):
        servicio_espia = ServicioGitEspiaComandos(
            protector_reservas=self.protector
        )
        (self.ruta / "Paquetes" / "FINI005.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI005 v4;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["add", "--", "Paquetes/FINI005.pls"],
                ruta_repositorio=self.ruta
            ).exitoso
        )

        self.reservas.valida = False
        resultado = servicio_espia.crear_commit(
            self.ruta,
            "Commit bloqueado con espia"
        )

        self.assertFalse(resultado.exitoso)
        for comando in servicio_espia.comandos:
            self.assertNotIn("commit", comando)

    def test_mensajes_de_bloqueo_controlados(self):
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v8;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["add", "--", "Paquetes/FINI004.pls"],
                ruta_repositorio=self.ruta
            ).exitoso
        )

        self.reservas.valida = False
        self.reservas.motivo = "No hay una consulta previa verificada."
        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit con mensaje controlado"
        )

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.codigo_salida, -1)
        self.assertIn("commit", resultado.error)
        self.assertIn("Modo Equipo Oracle", resultado.error)
        self.assertIn("Paquetes/FINI004.pls", resultado.error)
        self.assertIn(CLAVE_FINI004, resultado.error)
        self.assertIn("consulta previa", resultado.error)
        self.assertIn("reserva propia, verificada y fresca", resultado.error)
        # Sin tracebacks ni secretos en el mensaje normal.
        self.assertNotIn("Traceback", resultado.error)
        self.assertNotIn("token", resultado.error.lower())
        self.assertNotIn("password", resultado.error.lower())


class ProtectorFalsoResultado:
    """
    Protector falso que devuelve un resultado fijo o lanza una
    excepción: para probar el trato estricto de resultados no
    contractuales (REV1 FIX 3) y las barreras sin excepción cruda
    (REV1 FIX 4).
    """

    def __init__(self, resultado=None, excepcion=None):
        self.resultado = resultado
        self.excepcion = excepcion

    def proteger_staging(self, rutas):
        if self.excepcion is not None:
            raise self.excepcion
        return self.resultado

    def proteger_commit(self, rutas):
        if self.excepcion is not None:
            raise self.excepcion
        return self.resultado


class ServicioGitStagedSalidaFalsa(ServicioGit):
    """
    Sustituye la salida de la lectura del staged set para probar
    el parser fail-safe ante estados desconocidos o registros
    malformados (REV1 FIX 2).
    """

    def __init__(self, salida_staged, protector_reservas=None):
        super().__init__(protector_reservas=protector_reservas)
        self.salida_staged = salida_staged

    def _ejecutar_git_interno(
        self,
        argumentos,
        ruta_repositorio=None,
        tiempo_maximo=30
    ):
        if argumentos and argumentos[0] == "diff":
            return ResultadoComando(
                exitoso=True,
                codigo_salida=0,
                salida=self.salida_staged,
                error="",
                comando="diff (simulado)"
            )
        return super()._ejecutar_git_interno(
            argumentos,
            ruta_repositorio=ruta_repositorio,
            tiempo_maximo=tiempo_maximo,
        )


class PruebasCierreBypassPublico(_BaseProteccionIntegracion):
    """REV1 FIX 1: sin bypass público de staging/commit."""

    def test_add_directo_publico_bloqueado_sin_cambiar_indice(self):
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v2;\n",
            encoding="utf-8"
        )
        self.assertEqual(self.staged_set(), [])

        resultado = self.servicio.ejecutar_git(
            argumentos=[
                "add",
                "--",
                "Paquetes/FINI004.pls"
            ],
            ruta_repositorio=self.ruta
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("no es una consulta de solo lectura reconocida", resultado.error)
        # El índice no cambió.
        self.assertEqual(self.staged_set(), [])

    def test_commit_directo_publico_bloqueado_sin_cambiar_head(self):
        hash_antes = self.hash_head()

        resultado = self.servicio.ejecutar_git(
            argumentos=[
                "commit",
                "-m",
                "Commit por bypass"
            ],
            ruta_repositorio=self.ruta
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("no es una consulta de solo lectura reconocida", resultado.error)
        self.assertEqual(self.hash_head(), hash_antes)

    def test_otros_escritores_de_indice_bloqueados(self):
        for comando in (
            ["update-index", "--refresh"],
            ["apply"],
            ["read-tree", "HEAD"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )
            self.assertIn(
                "no es una consulta de solo lectura reconocida",
                resultado.error
            )

    def test_agregar_archivos_y_commit_con_reserva_valida_funcionan(self):
        # Las API protegidas siguen funcionando: usan el ejecutor
        # interno SOLO tras protección positiva.
        self.reservas.valida = True
        self.reservas.motivo = "Reserva propia fresca valida."
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v2;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio.agregar_archivos(
                self.ruta,
                ["Paquetes/FINI004.pls"]
            ).exitoso
        )
        hash_antes = self.hash_head()
        resultado = self.servicio.crear_commit(
            self.ruta,
            "Commit protegido permitido"
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertNotEqual(self.hash_head(), hash_antes)

    def test_sin_protector_ejecutor_publico_conserva_historico(self):
        # Sin protector, el ejecutor público sigue aceptando add y
        # commit directos (compatibilidad histórica).
        (self.ruta / "Paquetes" / "FINI005.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI005 v2;\n",
            encoding="utf-8"
        )
        resultado_add = self.servicio_base.ejecutar_git(
            argumentos=["add", "--", "Paquetes/FINI005.pls"],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado_add.exitoso, resultado_add.error)
        resultado_commit = self.servicio_base.ejecutar_git(
            argumentos=["commit", "-m", "Commit directo sin protector"],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(
            resultado_commit.exitoso,
            resultado_commit.error
        )


class PruebasCopiasReales(_BaseProteccionIntegracion):
    """REV1 FIX 2: copies reales con origen y destino protegidos."""

    def _preparar_copia_staged(self):
        contenido = (
            self.ruta / "Paquetes" / "FINI004.pls"
        ).read_text(encoding="utf-8")
        (self.ruta / "Paquetes" / "FINI009.pls").write_text(
            contenido,
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["add", "--", "Paquetes/FINI009.pls"],
                ruta_repositorio=self.ruta
            ).exitoso
        )

    def test_staged_set_identifica_copy_con_origen_y_destino(self):
        self._preparar_copia_staged()
        copias = [
            entrada for entrada in self.staged_set()
            if entrada[0] == "C"
        ]
        self.assertEqual(len(copias), 1)
        self.assertEqual(copias[0][1], "Paquetes/FINI009.pls")
        self.assertEqual(copias[0][2], "Paquetes/FINI004.pls")

    def test_copy_solo_reserva_destino_bloqueado(self):
        self._preparar_copia_staged()
        self.reservas.resultados = {
            CLAVE_FINI009: _resultado_reserva(True, "ok"),
        }
        hash_antes = self.hash_head()
        resultado = self.servicio.crear_commit(
            self.ruta,
            "Copy sin reserva del origen"
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn(CLAVE_FINI004, resultado.error)
        self.assertEqual(self.hash_head(), hash_antes)

    def test_copy_solo_reserva_origen_bloqueado(self):
        self._preparar_copia_staged()
        self.reservas.resultados = {
            CLAVE_FINI004: _resultado_reserva(True, "ok"),
        }
        hash_antes = self.hash_head()
        resultado = self.servicio.crear_commit(
            self.ruta,
            "Copy sin reserva del destino"
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn(CLAVE_FINI009, resultado.error)
        self.assertEqual(self.hash_head(), hash_antes)

    def test_copy_ambas_reservas_permitido(self):
        self._preparar_copia_staged()
        self.reservas.resultados = {
            CLAVE_FINI004: _resultado_reserva(True, "ok"),
            CLAVE_FINI009: _resultado_reserva(True, "ok"),
        }
        hash_antes = self.hash_head()
        resultado = self.servicio.crear_commit(
            self.ruta,
            "Copy con ambas reservas"
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertNotEqual(self.hash_head(), hash_antes)
        self.assertEqual(
            sorted(self.reservas.llamadas),
            [CLAVE_FINI004, CLAVE_FINI009]
        )

    def test_copy_destino_staging_sin_reserva_bloqueado(self):
        # El staging de una copy exige la reserva del objeto
        # destino; nunca se degrada a "archivo nuevo" sin reserva.
        contenido = (
            self.ruta / "Paquetes" / "FINI004.pls"
        ).read_text(encoding="utf-8")
        (self.ruta / "Paquetes" / "FINI009.pls").write_text(
            contenido,
            encoding="utf-8"
        )
        self.reservas.valida = False
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI009.pls"]
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn(CLAVE_FINI009, resultado.error)

    def test_estado_desconocido_en_staged_set_bloqueado(self):
        self._preparar_copia_staged()
        servicio_falso = ServicioGitStagedSalidaFalsa(
            "X\0Paquetes/FINI009.pls\0",
            protector_reservas=self.protector
        )
        resultado = servicio_falso.crear_commit(
            self.ruta,
            "Commit con estado desconocido"
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn("no reconocido", resultado.error)

    def test_copy_malformada_en_staged_set_bloqueada(self):
        self._preparar_copia_staged()
        servicio_falso = ServicioGitStagedSalidaFalsa(
            "C100\0Paquetes/FINI009.pls\0",
            protector_reservas=self.protector
        )
        resultado = servicio_falso.crear_commit(
            self.ruta,
            "Commit con copy malformada"
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn("sin sus dos rutas", resultado.error)


class PruebasResultadosProtectorNoContractuales(_BaseProteccionIntegracion):
    """REV1 FIX 3/4: trato estricto del resultado del protector."""

    def _agregar_debe_bloquearse(self, servicio):
        resultado = servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "bloqueada por seguridad",
            resultado.error
        )
        return resultado

    def test_protector_devuelve_none_bloqueado(self):
        servicio = ServicioGit(
            protector_reservas=ProtectorFalsoResultado(None)
        )
        self._agregar_debe_bloquearse(servicio)

    def test_protector_permitido_texto_bloqueado(self):
        servicio = ServicioGit(
            protector_reservas=ProtectorFalsoResultado(
                types.SimpleNamespace(
                    permitido="sí",
                    componer_mensaje=lambda: "x",
                )
            )
        )
        self._agregar_debe_bloquearse(servicio)

    def test_protector_permitido_entero_bloqueado(self):
        servicio = ServicioGit(
            protector_reservas=ProtectorFalsoResultado(
                types.SimpleNamespace(
                    permitido=1,
                    componer_mensaje=lambda: "x",
                )
            )
        )
        self._agregar_debe_bloquearse(servicio)

    def test_protector_bloqueo_sin_componer_mensaje_bloqueado(self):
        servicio = ServicioGit(
            protector_reservas=ProtectorFalsoResultado(
                types.SimpleNamespace(permitido=False)
            )
        )
        self._agregar_debe_bloquearse(servicio)

    def test_protector_bloqueo_mensaje_no_texto_bloqueado(self):
        servicio = ServicioGit(
            protector_reservas=ProtectorFalsoResultado(
                types.SimpleNamespace(
                    permitido=False,
                    componer_mensaje=lambda: 42,
                )
            )
        )
        self._agregar_debe_bloquearse(servicio)

    def test_excepcion_protector_sin_secreto_en_mensaje(self):
        secreto = "token-secreto-ficticio"
        servicio = ServicioGit(
            protector_reservas=ProtectorFalsoResultado(
                excepcion=RuntimeError(secreto)
            )
        )
        resultado = self._agregar_debe_bloquearse(servicio)
        self.assertNotIn(secreto, resultado.error)
        self.assertNotIn("Detalle técnico", resultado.error)

        hash_antes = self.hash_head()
        resultado_commit = servicio.crear_commit(
            self.ruta,
            "Commit con protector explotando"
        )
        self.assertFalse(resultado_commit.exitoso)
        self.assertNotIn(secreto, resultado_commit.error)
        self.assertEqual(self.hash_head(), hash_antes)

    def test_objeto_ajeno_permitido_true_bloqueado(self):
        # REV2 FIX C: un objeto ajeno con permitido=True no
        # autoriza nunca; solo el contrato real
        # (ResultadoProteccionReservasGit). Cero escritura Git.
        servicio = ServicioGit(
            protector_reservas=ProtectorFalsoResultado(
                types.SimpleNamespace(
                    permitido=True,
                    componer_mensaje=lambda: "autorizado",
                )
            )
        )
        self.assertEqual(self.staged_set(), [])
        resultado = self._agregar_debe_bloquearse(servicio)
        self.assertNotIn("autorizado", resultado.error)
        self.assertEqual(self.staged_set(), [])


class PruebasAllowlistLectura(_BaseProteccionIntegracion):
    """REV2 FIX A: allowlist de solo lectura sin lista negra evadible."""

    def test_rm_mv_restore_staged_checkout_reset_bloqueados(self):
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v2;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["add", "--", "Paquetes/FINI004.pls"],
                ruta_repositorio=self.ruta
            ).exitoso
        )
        hash_antes = self.hash_head()
        staged_antes = self.staged_set()

        for comando in (
            ["rm", "--cached", "--", "Paquetes/FINI004.pls"],
            ["mv", "Paquetes/FINI004.pls", "Paquetes/FINI010.pls"],
            [
                "restore",
                "--source=HEAD",
                "--staged",
                "--",
                "Paquetes/FINI004.pls",
            ],
            ["checkout", "HEAD", "--", "Paquetes/FINI004.pls"],
            ["reset", "HEAD", "--", "Paquetes/FINI004.pls"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )
            self.assertIn(
                "no es una consulta de solo lectura reconocida",
                resultado.error
            )

        self.assertEqual(self.hash_head(), hash_antes)
        self.assertEqual(self.staged_set(), staged_antes)

    def test_add_y_commit_directos_siguen_bloqueados(self):
        for comando in (
            ["add", "--", "Paquetes/FINI004.pls"],
            ["commit", "-m", "bypass"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(resultado.exitoso)

    def test_alias_add_y_commit_bloqueados(self):
        # Un alias Git no puede eludir la allowlist: el verbo que
        # llega al ejecutor es el nombre del alias (desconocido).
        # Nota: las claves de config Git no admiten "_" en la
        # variable, por eso los alias usan guion.
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["config", "alias.mialias-add", "add"],
                ruta_repositorio=self.ruta
            ).exitoso
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=[
                    "config",
                    "alias.mialias-commit",
                    "commit"
                ],
                ruta_repositorio=self.ruta
            ).exitoso
        )

        for comando in (
            ["mialias-add", "--", "Paquetes/FINI004.pls"],
            ["mialias-commit", "-m", "bypass por alias"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El alias {comando[0]} no fue bloqueado"
            )
        self.assertEqual(self.staged_set(), [])

    def test_consultas_read_only_funcionan_con_protector(self):
        consultas = (
            ["rev-parse", "--verify", "HEAD"],
            ["status", "--porcelain=v1", "-z"],
            [
                "diff",
                "--cached",
                "--name-status",
                "-z",
                "-C",
                "--find-copies-harder",
            ],
            ["config", "--get", "user.name"],
            [
                "for-each-ref",
                "--format=%(refname:short)",
                "refs/heads/"
            ],
            ["symbolic-ref", "--quiet", "--short", "HEAD"],
            ["remote"],
            ["show", "HEAD:Paquetes/FINI004.pls"],
            ["check-ref-format", "refs/heads/master"],
            ["log", "-1", "--format=%s"],
        )
        for comando in consultas:
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertTrue(
                resultado.exitoso,
                f"La consulta {comando} fallo: {resultado.error}"
            )

    def test_variantes_de_escritura_de_verbos_consulta_bloqueadas(self):
        for comando in (
            ["symbolic-ref", "HEAD", "refs/heads/otra"],
            ["remote", "add", "otro", "ruta/otro.git"],
            ["config", "user.name", "Otro"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )

    def test_restore_worktree_permitido_para_descarte(self):
        # El descarte de cambios sin preparar (restore --worktree)
        # es una operación legítima que no escribe el índice.
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v2;\n",
            encoding="utf-8"
        )
        resultado = self.servicio.ejecutar_git(
            argumentos=[
                "restore",
                "--worktree",
                "--",
                "Paquetes/FINI004.pls"
            ],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        # El working tree volvió al contenido de HEAD.
        self.assertEqual(
            (self.ruta / "Paquetes" / "FINI004.pls").read_text(
                encoding="utf-8"
            ),
            "CREATE OR REPLACE PACKAGE FINI004;\n"
        )

    def test_switch_bloqueado_consecuencia_documentada(self):
        # Consecuencia documentada de la allowlist (REV2 FIX A):
        # el cambio/creación de ramas por el ejecutor público
        # queda bloqueado con protector activo; su integración
        # protegida corresponde a Bloque F/G. Sin protector sigue
        # funcionando (comportamiento histórico).
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["switch", "-c", "rama_prueba"],
                ruta_repositorio=self.ruta
            ).exitoso
        )
        resultado = self.servicio.ejecutar_git(
            argumentos=["switch", "--no-guess", "master"],
            ruta_repositorio=self.ruta
        )
        self.assertFalse(resultado.exitoso)


class PruebasCopyProtegidaEnStaging(_BaseProteccionIntegracion):
    """REV2 FIX B: copy protegida en staging antes del primer write."""

    def _preparar_contenido_copia(self):
        contenido = (
            self.ruta / "Paquetes" / "FINI004.pls"
        ).read_text(encoding="utf-8")
        (self.ruta / "Paquetes" / "FINI009.pls").write_text(
            contenido,
            encoding="utf-8"
        )

    def _conteo_objetos(self):
        resultado = self.servicio_base.ejecutar_git(
            argumentos=["count-objects", "-v"],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado.exitoso)
        datos = {}
        for linea in resultado.salida.splitlines():
            if ":" in linea:
                clave, valor = linea.split(":", 1)
                if clave.strip() in ("count", "in-pack"):
                    datos[clave.strip()] = valor.strip()
        return datos

    def test_copy_solo_destino_reservado_bloqueada_antes_del_add(self):
        self._preparar_contenido_copia()
        self.reservas.resultados = {
            CLAVE_FINI009: _resultado_reserva(True, "ok"),
        }
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI009.pls"]
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn(CLAVE_FINI004, resultado.error)
        # El índice no cambió: el bloqueo ocurrió antes del add.
        self.assertEqual(self.staged_set(), [])

    def test_copy_solo_origen_reservado_bloqueada_antes_del_add(self):
        self._preparar_contenido_copia()
        self.reservas.resultados = {
            CLAVE_FINI004: _resultado_reserva(True, "ok"),
        }
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI009.pls"]
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn(CLAVE_FINI009, resultado.error)
        self.assertEqual(self.staged_set(), [])

    def test_copy_ambas_reservas_staging_permitido(self):
        self._preparar_contenido_copia()
        self.reservas.resultados = {
            CLAVE_FINI004: _resultado_reserva(True, "ok"),
            CLAVE_FINI009: _resultado_reserva(True, "ok"),
        }
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI009.pls"]
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        estados = {
            entrada[1]: entrada[0]
            for entrada in self.staged_set()
        }
        # Con detección de copies (-C --find-copies-harder) el
        # índice puede reportar la entrada como C (copy) o A.
        self.assertIn(
            estados.get("Paquetes/FINI009.pls"),
            ("A", "C")
        )
        # Origen y destino fueron validados.
        self.assertEqual(
            sorted(self.reservas.llamadas),
            [CLAVE_FINI004, CLAVE_FINI009]
        )

    def test_copy_origen_ambiguo_bloqueado(self):
        # FINI004 y FINI005 con contenido idéntico: una tercera
        # ruta con ese contenido no puede resolver su origen de
        # forma segura -> BLOQUEO.
        contenido = "CREATE OR REPLACE PACKAGE COMUNA;\n"
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            contenido, encoding="utf-8"
        )
        (self.ruta / "Paquetes" / "FINI005.pls").write_text(
            contenido, encoding="utf-8"
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=[
                    "add",
                    "--",
                    "Paquetes/FINI004.pls",
                    "Paquetes/FINI005.pls",
                ],
                ruta_repositorio=self.ruta
            ).exitoso
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["commit", "-m", "Contenido comun"],
                ruta_repositorio=self.ruta
            ).exitoso
        )

        (self.ruta / "Paquetes" / "FINI009.pls").write_text(
            contenido, encoding="utf-8"
        )
        self.reservas.valida = True
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI009.pls"]
        )
        self.assertFalse(resultado.exitoso)
        self.assertIn("ambiguo", resultado.error)
        self.assertEqual(self.staged_set(), [])

    def test_archivo_genuinamente_nuevo_solo_destino(self):
        # Contenido único: no hay origen del que copiar; basta la
        # reserva del objeto destino.
        (self.ruta / "Paquetes" / "FINI011.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI011_UNICO;\n",
            encoding="utf-8"
        )
        self.reservas.resultados = {
            CLAVE_FINI011: _resultado_reserva(True, "ok"),
        }
        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI011.pls"]
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertEqual(
            self.reservas.llamadas,
            [CLAVE_FINI011]
        )

    def test_bloqueo_no_modifica_indice_ni_objetos(self):
        self._preparar_contenido_copia()
        self.reservas.resultados = {
            CLAVE_FINI009: _resultado_reserva(True, "ok"),
        }
        objetos_antes = self._conteo_objetos()
        staged_antes = self.staged_set()

        resultado = self.servicio.agregar_archivos(
            self.ruta,
            ["Paquetes/FINI009.pls"]
        )
        self.assertFalse(resultado.exitoso)

        self.assertEqual(self.staged_set(), staged_antes)
        self.assertEqual(self._conteo_objetos(), objetos_antes)

    def test_commit_sigue_revalidando_ambos_lados_tras_staging(self):
        self._preparar_contenido_copia()
        self.reservas.resultados = {
            CLAVE_FINI004: _resultado_reserva(True, "ok"),
            CLAVE_FINI009: _resultado_reserva(True, "ok"),
        }
        self.assertTrue(
            self.servicio.agregar_archivos(
                self.ruta,
                ["Paquetes/FINI009.pls"]
            ).exitoso
        )

        # En el commit la reserva del origen quedó stale: bloquea.
        self.reservas.llamadas.clear()
        self.reservas.resultados = {
            CLAVE_FINI009: _resultado_reserva(True, "ok"),
        }
        hash_antes = self.hash_head()
        resultado_bloqueado = self.servicio.crear_commit(
            self.ruta,
            "Copy con origen stale"
        )
        self.assertFalse(resultado_bloqueado.exitoso)
        self.assertIn(CLAVE_FINI004, resultado_bloqueado.error)
        self.assertEqual(self.hash_head(), hash_antes)

        # Con ambas reservas vigentes: commit permitido.
        self.reservas.resultados[CLAVE_FINI004] = _resultado_reserva(
            True, "ok"
        )
        resultado_ok = self.servicio.crear_commit(
            self.ruta,
            "Copy con ambas reservas al commit"
        )
        self.assertTrue(resultado_ok.exitoso, resultado_ok.error)
        self.assertNotEqual(self.hash_head(), hash_antes)


class PruebasHardeningAllowlist(_BaseProteccionIntegracion):
    """REV3: gramática positiva por comando, default deny."""

    def test_symbolic_ref_delete_y_d_bloqueados(self):
        for comando in (
            ["symbolic-ref", "--delete", "refs/test"],
            ["symbolic-ref", "-d", "refs/test"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )
        # HEAD intacto.
        self.assertTrue(
            self.servicio.ejecutar_git(
                argumentos=["symbolic-ref", "--quiet", "--short", "HEAD"],
                ruta_repositorio=self.ruta
            ).exitoso
        )

    def test_symbolic_ref_forma_consulta_permitida(self):
        resultado = self.servicio.ejecutar_git(
            argumentos=["symbolic-ref", "--quiet", "--short", "HEAD"],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertEqual(resultado.salida.strip(), "master")

    def test_symbolic_ref_forma_con_nuevo_valor_bloqueada(self):
        resultado = self.servicio.ejecutar_git(
            argumentos=["symbolic-ref", "HEAD", "refs/heads/otra"],
            ruta_repositorio=self.ruta
        )
        self.assertFalse(resultado.exitoso)

    def test_remote_subcomandos_escritura_bloqueados(self):
        for comando in (
            ["remote", "update"],
            ["remote", "set-head", "origin", "-a"],
            ["remote", "rm", "origin"],
            ["remote", "remove", "origin"],
            ["remote", "add", "otro", "ruta/otro.git"],
            ["remote", "rename", "origin", "otro"],
            ["remote", "set-url", "origin", "ruta/otra.git"],
            ["remote", "set-branches", "origin", "x"],
            ["remote", "prune", "origin"],
            ["remote", "show", "origin"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )

    def test_remote_formas_de_lectura_permitidas(self):
        # Remoto local (ruta del propio repo temporal, sin red)
        # para poder consultar get-url.
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=[
                    "remote",
                    "add",
                    "origen",
                    str(self.ruta / "remoto_auxiliar.git"),
                ],
                ruta_repositorio=self.ruta
            ).exitoso
        )
        for comando in (
            ["remote"],
            ["remote", "-v"],
            ["remote", "--verbose"],
            ["remote", "get-url", "origen"],
            ["remote", "get-url", "--all", "origen"],
            ["remote", "get-url", "--push", "origen"],
            ["remote", "get-url", "--all", "--push", "origen"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertTrue(
                resultado.exitoso,
                f"La consulta {comando} fallo: {resultado.error}"
            )

    def test_config_forma_valida_permitida(self):
        resultado = self.servicio.ejecutar_git(
            argumentos=["config", "--get", "user.email"],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado.exitoso, resultado.error)

    def test_config_variantes_no_reconocidas_bloqueadas(self):
        for comando in (
            ["config", "--get-all", "user.name"],
            ["config", "--get-regexp", "user.*"],
            ["config", "user.name", "Otro"],
            ["config", "--get"],
            ["config", "--get", "user.name", "Otro"],
            ["config", "--get", "--get-all", "user.name"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )

    def test_opciones_con_efecto_lateral_bloqueadas(self):
        for comando in (
            ["diff", "--output=ruta_salida.txt"],
            ["diff", "--output", "ruta_salida.txt"],
            ["show", "--output=ruta_salida.txt", "HEAD:Paquetes/FINI004.pls"],
            ["log", "--output=ruta_salida.txt"],
            ["diff", "--ext-diff", "--", "Paquetes/FINI004.pls"],
            ["diff", "--textconv", "--", "Paquetes/FINI004.pls"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )
        self.assertFalse(
            (self.ruta / "ruta_salida.txt").exists(),
            "Se creó un archivo de salida pese al bloqueo"
        )

    def test_alias_add_y_commit_siguen_bloqueados(self):
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["config", "alias.mialias-add", "add"],
                ruta_repositorio=self.ruta
            ).exitoso
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["config", "alias.mialias-commit", "commit"],
                ruta_repositorio=self.ruta
            ).exitoso
        )
        for comando in (
            ["mialias-add", "--", "Paquetes/FINI004.pls"],
            ["mialias-commit", "-m", "bypass por alias"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(resultado.exitoso)

    def test_variante_no_reconocida_no_ejecuta_git(self):
        # Ante una variante no reconocida, no se ejecuta Git:
        # el espía del ejecutor interno no debe registrar nada.
        servicio_espia = ServicioGitEspiaComandos(
            protector_reservas=self.protector
        )
        comandos_bloqueados = (
            ["diff", "--output=ruta_salida.txt"],
            ["symbolic-ref", "--delete", "refs/test"],
            ["remote", "update"],
            ["config", "--get-all", "user.name"],
            ["mialias-add", "--", "Paquetes/FINI004.pls"],
        )
        for comando in comandos_bloqueados:
            resultado = servicio_espia.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(resultado.exitoso)

        self.assertEqual(servicio_espia.comandos, [])
        self.assertEqual(self.staged_set(), [])


class PruebasGramaticaDiff(_BaseProteccionIntegracion):
    """REV4: cierre de la gramática diff con diff.external real."""

    def setUp(self):
        super().setUp()

        # Directorio auxiliar FUERA del repositorio para el helper
        # y el marcador. El helper es un script sh (Git for Windows
        # ejecuta diff.external a traves de sh) con rutas de barras
        # forward.
        self.temporal_auxiliar = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal_auxiliar.cleanup)
        self.base_auxiliar = Path(self.temporal_auxiliar.name)
        self.ruta_helper = (
            self.base_auxiliar / "helper_external_diff.sh"
        )
        self.ruta_marcador = (
            self.base_auxiliar / "marcador_external_diff.txt"
        )
        marcador_sh = str(self.ruta_marcador).replace("\\", "/")
        helper_sh = str(self.ruta_helper).replace("\\", "/")
        self.ruta_helper.write_text(
            "#!/bin/sh\n"
            f'echo ejecutado > "{marcador_sh}"\n',
            encoding="utf-8",
        )

        # diff.external se configura LOCALMENTE en el repo temporal
        # mediante el servicio SIN protector (fixture). La ruta del
        # helper usa barras forward: el valor llega a sh sin
        # entrecomillar y las barras invertidas se perderian.
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=[
                    "config",
                    "diff.external",
                    helper_sh,
                ],
                ruta_repositorio=self.ruta
            ).exitoso
        )

        # Diferencia real en working tree y staging: se prepara la
        # versión v2 y después se modifica de nuevo el worktree,
        # de modo que `git diff` (worktree vs índice) y
        # `git diff --cached` (índice vs HEAD) produzcan patch.
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v2;\n",
            encoding="utf-8"
        )
        self.assertTrue(
            self.servicio_base.ejecutar_git(
                argumentos=["add", "--", "Paquetes/FINI004.pls"],
                ruta_repositorio=self.ruta
            ).exitoso
        )
        (self.ruta / "Paquetes" / "FINI004.pls").write_text(
            "CREATE OR REPLACE PACKAGE FINI004 v3;\n",
            encoding="utf-8"
        )
        self.assertFalse(self.ruta_marcador.exists())

    def test_control_positivo_helper_sin_protector(self):
        # Sin protector, un git diff productor de patch SÍ ejecuta
        # el diff.external configurado: control de que el marcador
        # funciona y los bloqueos siguientes no son vacuos.
        resultado = self.servicio_base.ejecutar_git(
            argumentos=["diff"],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertTrue(
            self.ruta_marcador.exists(),
            "El helper de diff.external no llego a ejecutarse"
        )

    def test_formas_patch_no_auditadas_bloqueadas_sin_helper(self):
        for comando in (
            ["diff"],
            ["diff", "--cached"],
            ["diff", "--unified=3"],
            ["diff", "--cached", "--unified=3"],
            ["diff", "--no-color"],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )
            self.assertIn(
                "no es una consulta de solo lectura reconocida",
                resultado.error
            )
        self.assertFalse(self.ruta_marcador.exists())

    def test_formas_parciales_staged_set_bloqueadas(self):
        for comando in (
            ["diff", "--cached", "--name-status", "-z"],
            ["diff", "--cached", "--name-status", "-z", "-C"],
            [
                "diff",
                "--cached",
                "--name-status",
                "-z",
                "--find-copies-harder",
            ],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )
        self.assertFalse(self.ruta_marcador.exists())

    def test_vista_segura_permitida_sin_ejecutar_helper(self):
        # Forma REAL auditada del visor de cambios locales.
        resultado = self.servicio.ejecutar_git(
            argumentos=[
                "--literal-pathspecs",
                "diff",
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--unified=3",
                "--",
                "Paquetes/FINI004.pls",
            ],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertFalse(
            self.ruta_marcador.exists(),
            "El helper externo se ejecuto pese a --no-ext-diff"
        )

    def test_vista_numstat_permitida_sin_ejecutar_helper(self):
        resultado = self.servicio.ejecutar_git(
            argumentos=[
                "--literal-pathspecs",
                "diff",
                "--numstat",
                "--no-ext-diff",
                "--no-textconv",
                "--",
                "Paquetes/FINI004.pls",
            ],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertFalse(self.ruta_marcador.exists())

    def test_vistas_malformadas_bloqueadas(self):
        for comando in (
            # Sin el modo de salida.
            [
                "--literal-pathspecs",
                "diff",
                "--no-ext-diff",
                "--",
                "Paquetes/FINI004.pls",
            ],
            # Sin las opciones obligatorias anti-external.
            [
                "--literal-pathspecs",
                "diff",
                "--unified=3",
                "--",
                "Paquetes/FINI004.pls",
            ],
            # --numstat y --unified=3 no coexisten.
            [
                "--literal-pathspecs",
                "diff",
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--numstat",
                "--unified=3",
                "--",
                "Paquetes/FINI004.pls",
            ],
        ):
            resultado = self.servicio.ejecutar_git(
                argumentos=comando,
                ruta_repositorio=self.ruta
            )
            self.assertFalse(
                resultado.exitoso,
                f"El comando {comando} no fue bloqueado"
            )
        self.assertFalse(self.ruta_marcador.exists())

    def test_staged_set_exacto_permitido_sin_ejecutar_helper(self):
        resultado = self.servicio.ejecutar_git(
            argumentos=[
                "diff",
                "--cached",
                "--name-status",
                "-z",
                "-C",
                "--find-copies-harder",
            ],
            ruta_repositorio=self.ruta
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertFalse(
            self.ruta_marcador.exists(),
            "El helper externo se ejecuto con name-status"
        )


if __name__ == "__main__":
    unittest.main()
