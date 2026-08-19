"""
Pruebas del servicio de ramas locales.

Cubren:

- listado de ramas locales con la actual identificada;
- cambio a una rama local existente (git switch --no-guess);
- creación de una rama local desde HEAD (git switch -c);
- precondiciones conservadoras (repositorio limpio, sin
  index.lock, sin operaciones en curso, HEAD no separado);
- validación de nombres (propia + git check-ref-format);
- argumentos exactos de los comandos y ausencia de verbos
  destructivos o remotos.

Utilizan exclusivamente carpetas temporales y nunca tocan GitHub
ni los repositorios reales.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from modelos import (
    CambioArchivo,
    EstadoRepositorio,
    ResultadoCambios,
    ResultadoComando,
)
from servicio_git import ServicioGit
from servicio_ramas_git import ServicioRamasGit


class ServicioGitEspiaRamas:
    """
    Sustituto de ServicioGit para pruebas sin Git real.

    Registra las llamadas a ejecutar_git y devuelve respuestas
    configurables para que el flujo del servicio llegue a decidir
    los comandos productivos.
    """

    def __init__(
        self,
        rama_actual="master",
        refs_existentes=("master", "feature/prueba"),
        cambios=(),
        cambios_exitosos=True,
        operacion_en_curso="",
        git_dir=".git",
        switch_exitoso=True,
        switch_error="",
        salida_ramas="",
        secuencia_cambios=()
    ):
        self.rama_actual_espia = rama_actual
        self.refs_existentes = set(refs_existentes)
        self.cambios = list(cambios)
        self.cambios_exitosos = cambios_exitosos
        self.operacion_en_curso = operacion_en_curso
        self.git_dir = git_dir
        self.switch_exitoso = switch_exitoso
        self.switch_error = switch_error
        self.salida_ramas = salida_ramas
        # secuencia_cambios permite simular que el repositorio se
        # ensucia ENTRE dos llamadas a obtener_cambios: cada
        # elemento es una tupla (exitoso, lista_de_cambios) que se
        # consume en orden, una por llamada. Cuando la secuencia se
        # agota se usa el comportamiento fijo (cambios/
        # cambios_exitosos).
        self.secuencia_cambios = list(secuencia_cambios)
        self.llamadas_ejecutar_git = []
        self.llamadas_obtener_cambios = 0

    def analizar_repositorio(self, ruta_repositorio):
        return EstadoRepositorio(
            es_repositorio=True,
            ruta_raiz=str(ruta_repositorio),
            rama_actual=self.rama_actual_espia,
            tiene_commits=True,
            remotos=[],
            mensaje="Repositorio Git valido."
        )

    def detectar_operacion_en_curso(self, ruta_repositorio):
        return self.operacion_en_curso

    def obtener_cambios(self, ruta_repositorio):
        self.llamadas_obtener_cambios += 1

        if self.secuencia_cambios:
            exitoso, cambios = self.secuencia_cambios.pop(0)

            return ResultadoCambios(
                exitoso=exitoso,
                cambios=list(cambios)
            )

        return ResultadoCambios(
            exitoso=self.cambios_exitosos,
            cambios=list(self.cambios)
        )

    def ejecutar_git(
        self,
        argumentos,
        ruta_repositorio=None,
        tiempo_maximo=30
    ):
        self.llamadas_ejecutar_git.append(
            list(argumentos)
        )

        verbo = argumentos[0]

        if verbo == "symbolic-ref":
            if self.rama_actual_espia == "":
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=1,
                    salida="",
                    error="HEAD separado.",
                    comando=""
                )

            return ResultadoComando(
                exitoso=True,
                codigo_salida=0,
                salida=self.rama_actual_espia,
                error="",
                comando=""
            )

        if verbo == "rev-parse":
            if argumentos[1] == "--git-dir":
                return ResultadoComando(
                    exitoso=True,
                    codigo_salida=0,
                    salida=self.git_dir,
                    error="",
                    comando=""
                )

            referencia = argumentos[3]

            nombre_rama = referencia.removeprefix(
                "refs/heads/"
            )

            if (
                referencia.startswith("refs/heads/")
                and nombre_rama in self.refs_existentes
            ):
                return ResultadoComando(
                    exitoso=True,
                    codigo_salida=0,
                    salida=referencia,
                    error="",
                    comando=""
                )

            return ResultadoComando(
                exitoso=False,
                codigo_salida=1,
                salida="",
                error="",
                comando=""
            )

        if verbo == "for-each-ref":
            return ResultadoComando(
                exitoso=True,
                codigo_salida=0,
                salida=self.salida_ramas,
                error="",
                comando=""
            )

        if verbo == "check-ref-format":
            return ResultadoComando(
                exitoso=True,
                codigo_salida=0,
                salida="",
                error="",
                comando=""
            )

        if verbo == "switch":
            return ResultadoComando(
                exitoso=self.switch_exitoso,
                codigo_salida=(
                    0 if self.switch_exitoso else 1
                ),
                salida="",
                error=self.switch_error,
                comando=""
            )

        return ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando=""
        )


class TestRamasGit(unittest.TestCase):
    """
    Pruebas del servicio de ramas locales.
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

        self._configurar_identidad()

        self._escribir_archivo("archivo.txt", "contenido inicial")

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        self._ejecutar_git_repositorio(
            "commit",
            "-m",
            "Inicial"
        )

        self.servicio = ServicioRamasGit(
            ServicioGit()
        )

    def tearDown(self):
        self.temporal.cleanup()

    def _configurar_identidad(self):
        """
        Configura una identidad Git para los repositorios temporales.
        """

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "config",
            "user.name",
            "Usuario Ramas"
        )

        self._ejecutar_git(
            "-C",
            str(self.ruta_repositorio),
            "config",
            "user.email",
            "ramas@example.com"
        )

    def _ejecutar_git(self, *argumentos):
        """
        Ejecuta Git fuera del repositorio temporal.
        """

        return subprocess.run(
            ["git", *argumentos],
            check=True,
            capture_output=True,
            text=True
        )

    def _ejecutar_git_repositorio(self, *argumentos):
        """
        Ejecuta Git dentro del repositorio temporal.
        """

        return subprocess.run(
            ["git", *argumentos],
            cwd=self.ruta_repositorio,
            check=True,
            capture_output=True,
            text=True
        )

    def _escribir_archivo(self, ruta_relativa, contenido):
        """
        Escribe un archivo dentro del repositorio temporal.
        """

        ruta_archivo = (
            self.ruta_repositorio / ruta_relativa
        )

        ruta_archivo.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        ruta_archivo.write_text(
            contenido,
            encoding="utf-8"
        )

    def _hash_head(self):
        """
        Devuelve el hash actual de HEAD del repositorio temporal.
        """

        resultado = self._ejecutar_git_repositorio(
            "rev-parse",
            "HEAD"
        )

        return resultado.stdout.strip()

    def _crear_rama_con_git(self, nombre):
        """
        Crea una rama con Git real y cambia a ella.
        """

        self._ejecutar_git_repositorio(
            "switch",
            "-c",
            nombre
        )

    # =============================================================
    # Listado de ramas
    # =============================================================

    def test_lista_ramas_locales_e_identifica_actual(self):
        resultado = self.servicio.obtener_ramas_locales(
            self.ruta_repositorio
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(len(resultado.ramas), 1)
        self.assertEqual(resultado.ramas[0].nombre, "master")
        self.assertTrue(resultado.ramas[0].actual)

    def test_lista_varias_ramas_con_actual_primero(self):
        self._crear_rama_con_git("feature/prueba")
        self._crear_rama_con_git("fix/error-oracle")
        self._ejecutar_git_repositorio(
            "switch",
            "master"
        )

        resultado = self.servicio.obtener_ramas_locales(
            self.ruta_repositorio
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(len(resultado.ramas), 3)
        self.assertEqual(
            [rama.nombre for rama in resultado.ramas],
            ["master", "feature/prueba", "fix/error-oracle"]
        )
        self.assertTrue(resultado.ramas[0].actual)
        self.assertFalse(resultado.ramas[1].actual)
        self.assertFalse(resultado.ramas[2].actual)

    # =============================================================
    # Cambiar de rama
    # =============================================================

    def test_cambiar_a_rama_local_existente(self):
        self._crear_rama_con_git("feature/prueba")
        self._ejecutar_git_repositorio(
            "switch",
            "master"
        )

        resultado = self.servicio.cambiar_rama(
            self.ruta_repositorio,
            "feature/prueba"
        )

        self.assertTrue(resultado.exitoso)

        rama_actual = self._ejecutar_git_repositorio(
            "symbolic-ref",
            "--short",
            "HEAD"
        ).stdout.strip()

        self.assertEqual(rama_actual, "feature/prueba")

    def test_contenido_working_tree_cambia_con_el_switch(self):
        self._crear_rama_con_git("feature/prueba")

        self._escribir_archivo("archivo.txt", "contenido feature")

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        self._ejecutar_git_repositorio(
            "commit",
            "-m",
            "Cambio en feature"
        )

        self._ejecutar_git_repositorio(
            "switch",
            "master"
        )

        resultado = self.servicio.cambiar_rama(
            self.ruta_repositorio,
            "feature/prueba"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(
            (
                self.ruta_repositorio / "archivo.txt"
            ).read_text(encoding="utf-8"),
            "contenido feature"
        )

    def test_cambiar_a_la_rama_actual_se_bloquea(self):
        resultado = self.servicio.cambiar_rama(
            self.ruta_repositorio,
            "master"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("Ya se encuentra", resultado.error)

    def test_cambio_rechazado_si_rama_local_no_existe(self):
        resultado = self.servicio.cambiar_rama(
            self.ruta_repositorio,
            "rama-inexistente"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("no existe", resultado.error)

    # =============================================================
    # Crear rama
    # =============================================================

    def test_crear_rama_valida_desde_head_y_quedar_situado(self):
        resultado = self.servicio.crear_rama(
            self.ruta_repositorio,
            "feature/login"
        )

        self.assertTrue(resultado.exitoso)
        self.assertIn("local", resultado.mensaje)

        rama_actual = self._ejecutar_git_repositorio(
            "symbolic-ref",
            "--short",
            "HEAD"
        ).stdout.strip()

        self.assertEqual(rama_actual, "feature/login")

    def test_crear_rama_no_modifica_el_commit_desde_el_que_nace(self):
        hash_antes = self._hash_head()

        resultado = self.servicio.crear_rama(
            self.ruta_repositorio,
            "feature/login"
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(self._hash_head(), hash_antes)

        hash_rama_nueva = (
            self._ejecutar_git_repositorio(
                "rev-parse",
                "refs/heads/feature/login"
            ).stdout.strip()
        )

        self.assertEqual(hash_rama_nueva, hash_antes)

    def test_creacion_rechazada_si_la_rama_ya_existe(self):
        self._crear_rama_con_git("feature/prueba")
        self._ejecutar_git_repositorio(
            "switch",
            "master"
        )

        resultado = self.servicio.crear_rama(
            self.ruta_repositorio,
            "feature/prueba"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("ya existe", resultado.error)

        rama_actual = self._ejecutar_git_repositorio(
            "symbolic-ref",
            "--short",
            "HEAD"
        ).stdout.strip()

        # Seguir en master: la creación no cambió nada.
        self.assertEqual(rama_actual, "master")

    # =============================================================
    # Precondiciones conservadoras
    # =============================================================

    def test_tracked_modificado_sin_preparar_bloquea(self):
        self._escribir_archivo(
            "archivo.txt",
            "contenido modificado sin preparar"
        )

        resultado = self.servicio.crear_rama(
            self.ruta_repositorio,
            "feature/login"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("no está limpio", resultado.error)

        resultado_cambio = self.servicio.cambiar_rama(
            self.ruta_repositorio,
            "feature/login"
        )

        self.assertFalse(resultado_cambio.exitoso)
        self.assertIn("no está limpio", resultado_cambio.error)

    def test_cambio_preparado_bloquea(self):
        self._escribir_archivo(
            "archivo.txt",
            "contenido preparado"
        )

        self._ejecutar_git_repositorio(
            "add",
            "archivo.txt"
        )

        resultado = self.servicio.crear_rama(
            self.ruta_repositorio,
            "feature/login"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("no está limpio", resultado.error)

    def test_archivo_nuevo_untracked_bloquea(self):
        self._escribir_archivo(
            "archivo_nuevo.txt",
            "sin seguimiento"
        )

        resultado = self.servicio.crear_rama(
            self.ruta_repositorio,
            "feature/login"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("no está limpio", resultado.error)

    def test_repositorio_sin_commits_bloquea(self):
        ruta_sin_commits = (
            Path(self.temporal.name) / "repositorio_sin_commits"
        )

        self._ejecutar_git(
            "init",
            "--initial-branch=master",
            str(ruta_sin_commits)
        )

        self._configurar_identidad_repositorio_extra(
            ruta_sin_commits
        )

        resultado = self.servicio.crear_rama(
            ruta_sin_commits,
            "feature/login"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("no tiene commits", resultado.error)

        resultado_cambio = self.servicio.cambiar_rama(
            ruta_sin_commits,
            "master"
        )

        self.assertFalse(resultado_cambio.exitoso)
        self.assertIn("no tiene commits", resultado_cambio.error)

    def _configurar_identidad_repositorio_extra(self, ruta):
        """
        Configura la identidad en un repositorio temporal extra.
        """

        subprocess.run(
            ["git", "-C", str(ruta), "config",
             "user.name", "Usuario Ramas"],
            check=True,
            capture_output=True,
            text=True
        )

        subprocess.run(
            ["git", "-C", str(ruta), "config",
             "user.email", "ramas@example.com"],
            check=True,
            capture_output=True,
            text=True
        )

    def test_repositorio_sin_commits_no_se_marca_como_head_separado(
        self
    ):
        ruta_sin_commits = (
            Path(self.temporal.name) / "repositorio_sin_commits"
        )

        self._ejecutar_git(
            "init",
            "--initial-branch=master",
            str(ruta_sin_commits)
        )

        resultado = self.servicio.obtener_ramas_locales(
            ruta_sin_commits
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(resultado.ramas, [])
        self.assertFalse(resultado.tiene_commits)
        self.assertFalse(resultado.head_separado)
        self.assertIn("sin commits", resultado.mensaje)

    def test_head_separado_lista_pero_bloquea_operaciones(self):
        self._ejecutar_git_repositorio(
            "checkout",
            "--detach"
        )

        resultado_lista = (
            self.servicio.obtener_ramas_locales(
                self.ruta_repositorio
            )
        )

        self.assertTrue(resultado_lista.exitoso)
        self.assertEqual(len(resultado_lista.ramas), 1)
        self.assertFalse(resultado_lista.ramas[0].actual)
        self.assertTrue(resultado_lista.tiene_commits)
        self.assertTrue(resultado_lista.head_separado)
        self.assertIn("separado", resultado_lista.mensaje)

        resultado_cambio = self.servicio.cambiar_rama(
            self.ruta_repositorio,
            "master"
        )

        self.assertFalse(resultado_cambio.exitoso)
        self.assertIn("separado", resultado_cambio.error)

        resultado_crear = self.servicio.crear_rama(
            self.ruta_repositorio,
            "feature/login"
        )

        self.assertFalse(resultado_crear.exitoso)
        self.assertIn("separado", resultado_crear.error)

    def test_index_lock_bloquea_operaciones(self):
        ruta_index_lock = (
            self.ruta_repositorio / ".git" / "index.lock"
        )

        ruta_index_lock.write_text("", encoding="utf-8")

        try:
            resultado = self.servicio.crear_rama(
                self.ruta_repositorio,
                "feature/login"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("index.lock", resultado.error)
        finally:
            ruta_index_lock.unlink()

    def test_operacion_git_en_curso_bloquea(self):
        ruta_merge_head = (
            self.ruta_repositorio / ".git" / "MERGE_HEAD"
        )

        ruta_merge_head.write_text("", encoding="utf-8")

        try:
            resultado = self.servicio.crear_rama(
                self.ruta_repositorio,
                "feature/login"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("merge", resultado.error)
        finally:
            ruta_merge_head.unlink()

    def test_cambiar_rama_revalida_limpieza_justo_antes_del_switch(
        self
    ):
        # TOCTOU: entre la primera validación (limpio) y la
        # revalidación final, OTRA herramienta modifica un archivo.
        cambio_repentino = CambioArchivo(
            ruta="archivo.txt",
            estado_indice=" ",
            estado_trabajo="M",
            descripcion="Modificado",
            preparado=False
        )

        espia = ServicioGitEspiaRamas(
            rama_actual="master",
            refs_existentes=("master", "feature/prueba"),
            secuencia_cambios=[
                (True, []),
                (True, [cambio_repentino])
            ]
        )

        servicio = ServicioRamasGit(espia)

        resultado = servicio.cambiar_rama(
            "c:/repositorio",
            "feature/prueba"
        )

        self.assertFalse(resultado.exitoso)

        # El mensaje explica que el repositorio dejó de estar
        # limpio.
        self.assertIn("no está limpio", resultado.error)

        # La limpieza se consultó al menos dos veces (primera
        # validación + revalidación inmediatamente antes del
        # switch).
        self.assertGreaterEqual(
            espia.llamadas_obtener_cambios,
            2
        )

        # El switch NUNCA llegó a ejecutarse.
        for llamada in espia.llamadas_ejecutar_git:
            self.assertNotIn("switch", llamada)

    def test_crear_rama_revalida_limpieza_justo_antes_del_switch(
        self
    ):
        # Equivalente a la prueba anterior, pero con crear_rama:
        # feature/login no existe y el fallo aparece justo antes
        # del git switch -c productivo.
        cambio_repentino = CambioArchivo(
            ruta="archivo_nuevo.txt",
            estado_indice="?",
            estado_trabajo="?",
            descripcion="Nuevo",
            preparado=False
        )

        espia = ServicioGitEspiaRamas(
            rama_actual="master",
            refs_existentes=("master",),
            secuencia_cambios=[
                (True, []),
                (True, [cambio_repentino])
            ]
        )

        servicio = ServicioRamasGit(espia)

        resultado = servicio.crear_rama(
            "c:/repositorio",
            "feature/login"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("no está limpio", resultado.error)

        self.assertGreaterEqual(
            espia.llamadas_obtener_cambios,
            2
        )

        for llamada in espia.llamadas_ejecutar_git:
            self.assertNotIn("switch", llamada)

    def test_repositorio_no_valido_bloquea(self):
        ruta_no_repositorio = (
            Path(self.temporal.name) / "no_repositorio"
        )

        ruta_no_repositorio.mkdir()

        resultado = self.servicio.obtener_ramas_locales(
            ruta_no_repositorio
        )

        self.assertFalse(resultado.exitoso)

        resultado_cambio = self.servicio.cambiar_rama(
            ruta_no_repositorio,
            "master"
        )

        self.assertFalse(resultado_cambio.exitoso)

    # =============================================================
    # Validación de nombres
    # =============================================================

    def test_nombres_invalidos_se_rechazan(self):
        nombres_invalidos = [
            "",
            " rama",
            "rama ",
            "-rama",
            "HEAD",
            "@",
            "rama..mala",
            "rama.lock",
            "rama@{1}",
            "@{-1}",
        ]

        for nombre in nombres_invalidos:
            with self.subTest(nombre=nombre):
                resultado = self.servicio.crear_rama(
                    self.ruta_repositorio,
                    nombre
                )

                self.assertFalse(resultado.exitoso)

        # Seguir en master: ninguna creación llegó a ejecutarse.
        rama_actual = self._ejecutar_git_repositorio(
            "symbolic-ref",
            "--short",
            "HEAD"
        ).stdout.strip()

        self.assertEqual(rama_actual, "master")

    def test_nombre_con_nul_se_rechaza_sin_comando_productivo(self):
        espia = ServicioGitEspiaRamas(
            rama_actual="master",
            refs_existentes=("master",)
        )

        servicio = ServicioRamasGit(espia)

        resultado = servicio.crear_rama(
            "c:/repositorio",
            "rama\x00mala"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("NUL", resultado.error)

        for llamada in espia.llamadas_ejecutar_git:
            self.assertNotIn("switch", llamada)

    def test_nombres_validos_se_aceptan(self):
        for nombre in [
            "feature/login",
            "fix/error-oracle",
            "prueba_2026",
        ]:
            with self.subTest(nombre=nombre):
                resultado = self.servicio.crear_rama(
                    self.ruta_repositorio,
                    nombre
                )

                self.assertTrue(resultado.exitoso)

    # =============================================================
    # Argumentos exactos y seguridad de comandos
    # =============================================================

    def test_argumentos_exactos_del_switch_con_spy(self):
        espia = ServicioGitEspiaRamas(
            rama_actual="master",
            refs_existentes=("master", "feature/prueba")
        )

        servicio = ServicioRamasGit(espia)

        resultado = servicio.cambiar_rama(
            "c:/repositorio",
            "feature/prueba"
        )

        self.assertTrue(resultado.exitoso)

        self.assertIn(
            ["switch", "--no-guess", "feature/prueba"],
            espia.llamadas_ejecutar_git
        )

        self.assertIn(
            ["check-ref-format", "refs/heads/feature/prueba"],
            espia.llamadas_ejecutar_git
        )

        resultado_crear = servicio.crear_rama(
            "c:/repositorio",
            "feature/login"
        )

        self.assertTrue(resultado_crear.exitoso)

        self.assertIn(
            ["switch", "-c", "feature/login"],
            espia.llamadas_ejecutar_git
        )

    def test_nunca_ejecuta_verbos_prohibidos(self):
        espia = ServicioGitEspiaRamas(
            rama_actual="master",
            refs_existentes=("master", "feature/prueba")
        )

        servicio = ServicioRamasGit(espia)

        self.assertTrue(
            servicio.cambiar_rama(
                "c:/repositorio",
                "feature/prueba"
            ).exitoso
        )

        self.assertTrue(
            servicio.crear_rama(
                "c:/repositorio",
                "feature/login"
            ).exitoso
        )

        argumentos_planos = [
            argumento
            for llamada in espia.llamadas_ejecutar_git
            for argumento in llamada
        ]

        for verbo_prohibido in [
            "checkout",
            "reset",
            "restore",
            "clean",
            "merge",
            "rebase",
            "fetch",
            "pull",
            "push",
            "branch",
            "-D",
            "--force",
        ]:
            self.assertNotIn(
                verbo_prohibido,
                argumentos_planos
            )

    def test_error_de_obtener_cambios_bloquea(self):
        espia = ServicioGitEspiaRamas(
            rama_actual="master",
            refs_existentes=("master",),
            cambios_exitosos=False
        )

        servicio = ServicioRamasGit(espia)

        resultado = servicio.crear_rama(
            "c:/repositorio",
            "feature/login"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("No fue posible determinar", resultado.error)

        for llamada in espia.llamadas_ejecutar_git:
            self.assertNotIn("switch", llamada)

    def test_error_del_switch_se_expone(self):
        espia = ServicioGitEspiaRamas(
            rama_actual="master",
            refs_existentes=("master", "feature/prueba"),
            switch_exitoso=False,
            switch_error="No se pudo cambiar de rama"
        )

        servicio = ServicioRamasGit(espia)

        resultado = servicio.cambiar_rama(
            "c:/repositorio",
            "feature/prueba"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("No se pudo cambiar", resultado.error)

    # =============================================================
    # Remotos
    # =============================================================

    def test_crear_y_cambiar_rama_no_modifica_ningun_remoto(self):
        ruta_remoto = (
            Path(self.temporal.name) / "remoto.git"
        )

        self._ejecutar_git(
            "init",
            "--bare",
            str(ruta_remoto)
        )

        self._ejecutar_git_repositorio(
            "remote",
            "add",
            "origin",
            str(ruta_remoto)
        )

        resultado = self.servicio.crear_rama(
            self.ruta_repositorio,
            "feature/prueba"
        )

        self.assertTrue(resultado.exitoso)

        resultado_lista = self.servicio.obtener_ramas_locales(
            self.ruta_repositorio
        )

        self.assertTrue(resultado_lista.exitoso)
        self.assertEqual(
            [rama.nombre for rama in resultado_lista.ramas],
            ["feature/prueba", "master"]
        )

        remotos = self._ejecutar_git_repositorio(
            "remote"
        ).stdout.strip()

        self.assertEqual(remotos, "origin")

        referencias_remotas = (
            self._ejecutar_git_repositorio(
                "for-each-ref",
                "refs/remotes/origin/"
            ).stdout.strip()
        )

        # La rama nueva no se publicó y no se ejecutó Fetch.
        self.assertEqual(referencias_remotas, "")


if __name__ == "__main__":
    unittest.main()