import tempfile
import unittest
from pathlib import Path

from modelos import CambioArchivo, ResultadoCambios, ResultadoComando
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

    def ejecutar_git(self, argumentos, ruta_repositorio):
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

        return super().ejecutar_git(
            argumentos,
            ruta_repositorio
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


if __name__ == "__main__":
    unittest.main()
