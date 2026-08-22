"""
Pruebas de la funcionalidad "Publicar rama local" V1.

Cubren el método ServicioRemotoGit.publicar_rama_local (Git real en
repositorios temporales con remotos bare, y un espía para argumentos
exactos y revalidaciones TOCTOU) y la integración de la interfaz
(sin Tk real, con dobles mínimos y mock de messagebox).

Las pruebas nunca tocan GitHub ni el repositorio real GestorGit:
todo ocurre dentro de tempfile.TemporaryDirectory().
"""

import ast
import inspect
import queue
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

import principal
from modelos import (
    CambioArchivo,
    EstadoRepositorio,
    EstadoSincronizacion,
    ResultadoCambios,
    ResultadoComando,
)
from servicio_remoto_git import ServicioRemotoGit


# =================================================================
# Espía de ServicioRemotoGit para Publicar rama local.
# =================================================================

class ServicioRemotoEspiaPublicar(ServicioRemotoGit):
    """
    Doble de ServicioRemotoGit para publicar_rama_local.

    Registra cada llamada a ejecutar_git y permite programar
    secuencias de resultados por consulta, de modo que el repositorio
    pueda "cambiar externamente" entre la primera validación, la
    segunda validación y el Push (escenarios TOCTOU), sin depender
    del sistema de archivos real.
    """

    def __init__(
        self,
        rama_actual="feature",
        remotos=("origin",),
        remoto_seguro="origin",
        tiene_commits=True,
        estados_repositorio=None,
        resultados_remoto=None,
        resultados_cambios=None,
        respuestas_upstream=None,
        respuestas_ls_remote=None,
        push_exitoso=True,
        push_error=""
    ):
        super().__init__()

        self.rama_actual = rama_actual
        self.remotos = list(remotos)
        self.remoto_seguro = remoto_seguro
        self.tiene_commits = tiene_commits

        self.estados_repositorio = estados_repositorio
        self.resultados_remoto = resultados_remoto
        self.resultados_cambios = resultados_cambios
        self.respuestas_upstream = respuestas_upstream
        self.respuestas_ls_remote = respuestas_ls_remote
        self.push_exitoso = push_exitoso
        self.push_error = push_error

        self.llamadas_ejecutar_git = []

        self.indice_estado = 0
        self.indice_remoto = 0
        self.indice_cambios = 0
        self.indice_upstream = 0
        self.indice_ls_remote = 0

    def _consumar(self, secuencia, indice, por_defecto):
        valor = por_defecto

        if secuencia is not None and indice < len(secuencia):
            valor = secuencia[indice]

        return valor, indice + 1

    def analizar_repositorio(self, ruta_repositorio):
        por_defecto = EstadoRepositorio(
            es_repositorio=True,
            ruta_raiz=ruta_repositorio,
            rama_actual=self.rama_actual,
            tiene_commits=self.tiene_commits,
            remotos=list(self.remotos)
        )

        estado, self.indice_estado = self._consumar(
            self.estados_repositorio,
            self.indice_estado,
            por_defecto
        )

        return estado

    def obtener_remoto_sincronizacion(self, ruta_repositorio):
        por_defecto = ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida=self.remoto_seguro,
            error="",
            comando=""
        )

        resultado, self.indice_remoto = self._consumar(
            self.resultados_remoto,
            self.indice_remoto,
            por_defecto
        )

        return resultado

    def obtener_cambios(self, ruta_repositorio):
        por_defecto = ResultadoCambios(
            exitoso=True,
            cambios=[]
        )

        resultado, self.indice_cambios = self._consumar(
            self.resultados_cambios,
            self.indice_cambios,
            por_defecto
        )

        return resultado

    def detectar_operacion_en_curso(self, ruta_repositorio):
        return ""

    def _obtener_ruta_git_interna(self, ruta_repositorio, nombre):
        return None

    def ejecutar_git(
        self,
        argumentos,
        ruta_repositorio=None,
        tiempo_maximo=30
    ):
        argumentos = list(argumentos)

        self.llamadas_ejecutar_git.append(argumentos)

        if argumentos[0] == "push":
            return ResultadoComando(
                exitoso=self.push_exitoso,
                codigo_salida=(
                    0
                    if self.push_exitoso
                    else 1
                ),
                salida="",
                error=self.push_error,
                comando=" ".join(argumentos)
            )

        if argumentos[0] == "ls-remote":
            exitoso, salida = self.respuestas_ls_remote[0]

            self.indice_ls_remote += 1

            return ResultadoComando(
                exitoso=exitoso,
                codigo_salida=(
                    0
                    if exitoso
                    else 128
                ),
                salida=(
                    salida
                    if exitoso
                    else ""
                ),
                error=(
                    ""
                    if exitoso
                    else "fallo de ls-remote simulado"
                ),
                comando=" ".join(argumentos)
            )

        if argumentos[0] == "for-each-ref":
            # Consulta estructurada del upstream de la rama
            # (_obtener_upstream_rama_actual).
            indice = min(
                self.indice_upstream,
                len(self.respuestas_upstream) - 1
            )

            exitoso, salida = self.respuestas_upstream[indice]

            self.indice_upstream += 1

            return ResultadoComando(
                exitoso=exitoso,
                codigo_salida=(
                    0
                    if exitoso
                    else 128
                ),
                salida=salida,
                error="",
                comando=" ".join(argumentos)
            )

        return ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando=" ".join(argumentos)
        )


class ServicioConConsultaDeCambiosRota(ServicioRemotoGit):
    """
    Simula un fallo de git status: obtener_cambios nunca es exitoso.

    Un error de consulta nunca debe interpretarse como un repositorio
    limpio.
    """

    def obtener_cambios(self, ruta_repositorio):
        return ResultadoCambios(
            exitoso=False,
            error="fallo simulado de git status"
        )


class ServicioConConflictoEstructural(ServicioRemotoGit):
    """
    Expone un cambio en conflicto con una descripción que NO dice
    "Conflicto": demuestra que la decisión usa el dato estructurado
    en_conflicto, nunca el texto localizado.
    """

    def obtener_cambios(self, ruta_repositorio):
        cambio = CambioArchivo(
            ruta="paquete/conflicto.sql",
            estado_indice="U",
            estado_trabajo="U",
            descripcion="Estado raro del merge",
            preparado=True,
            en_conflicto=True
        )

        return ResultadoCambios(
            exitoso=True,
            cambios=[cambio]
        )


# =================================================================
# Pruebas del servicio con Git real (repositorios temporales).
# =================================================================

class PruebasPublicarRamaGit(unittest.TestCase):
    """
    Escenarios reales: repositorio local + remoto bare temporal.
    """

    def _configurar_identidad(self, servicio, ruta_repositorio):
        for clave, valor in (
            ("user.name", "Usuario Publicar"),
            ("user.email", "publicar@example.com")
        ):
            resultado = servicio.ejecutar_git(
                argumentos=["config", clave, valor],
                ruta_repositorio=ruta_repositorio
            )

            self.assertTrue(
                resultado.exitoso,
                f"No se pudo configurar {clave}."
            )

    def _crear_repositorio_local(self, ruta_base):
        ruta_local = ruta_base / "local"

        ruta_local.mkdir()

        servicio = ServicioRemotoGit()

        resultado = servicio.ejecutar_git(
            argumentos=["init", "-b", "master"],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(resultado.exitoso)

        self._configurar_identidad(servicio, ruta_local)

        (ruta_local / "archivo.sql").write_text(
            "SELECT 1;\n",
            encoding="utf-8"
        )

        resultado = servicio.ejecutar_git(
            argumentos=["add", "--", "archivo.sql"],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(resultado.exitoso)

        resultado = servicio.ejecutar_git(
            argumentos=["commit", "-m", "Inicial"],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(resultado.exitoso)

        return servicio, ruta_local

    def _crear_remoto_bare(self, servicio, ruta_base):
        ruta_remoto = ruta_base / "remoto.git"

        ruta_remoto.mkdir()

        resultado = servicio.ejecutar_git(
            argumentos=["init", "--bare", "-b", "master"],
            ruta_repositorio=ruta_remoto
        )

        self.assertTrue(resultado.exitoso)

        return ruta_remoto

    def _agregar_remoto(self, servicio, ruta_local, ruta_remoto):
        resultado = servicio.ejecutar_git(
            argumentos=[
                "remote",
                "add",
                "origin",
                str(ruta_remoto)
            ],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(resultado.exitoso)

    def _publicar_master(self, servicio, ruta_local):
        resultado = servicio.ejecutar_git(
            argumentos=[
                "push",
                "--porcelain",
                "--set-upstream",
                "origin",
                "master:refs/heads/master"
            ],
            ruta_repositorio=ruta_local,
            tiempo_maximo=60
        )

        self.assertTrue(
            resultado.exitoso,
            f"No se pudo preparar master en el remoto: {resultado.error}"
        )

    def _fetch(self, servicio, ruta_local):
        resultado = servicio.ejecutar_git(
            argumentos=["fetch", "--prune", "origin"],
            ruta_repositorio=ruta_local,
            tiempo_maximo=60
        )

        self.assertTrue(resultado.exitoso)

    def _crear_rama(self, servicio, ruta_local, nombre):
        resultado = servicio.ejecutar_git(
            argumentos=["switch", "-c", nombre],
            ruta_repositorio=ruta_local
        )

        self.assertTrue(resultado.exitoso)

    def _crear_escenario(
        self,
        ruta_base,
        con_master_en_remoto=True
    ):
        servicio, ruta_local = self._crear_repositorio_local(ruta_base)

        ruta_remoto = self._crear_remoto_bare(servicio, ruta_base)

        self._agregar_remoto(servicio, ruta_local, ruta_remoto)

        if con_master_en_remoto:
            self._publicar_master(servicio, ruta_local)
            self._fetch(servicio, ruta_local)

        return servicio, ruta_local, ruta_remoto

    def _hash_de_ref(self, servicio, ruta_repositorio, ref):
        resultado = servicio.ejecutar_git(
            argumentos=["rev-parse", ref],
            ruta_repositorio=ruta_repositorio
        )

        self.assertTrue(resultado.exitoso)

        return resultado.salida.strip()

    def _ref_existe(self, servicio, ruta_repositorio, ref):
        resultado = servicio.ejecutar_git(
            argumentos=["show-ref", "--verify", "--quiet", ref],
            ruta_repositorio=ruta_repositorio
        )

        return resultado.exitoso

    def _sembrar_rama_remota(
        self,
        servicio,
        ruta_base,
        ruta_remoto,
        nombre_rama,
        con_commit=False
    ):
        """Clona el bare y publica una rama desde el clon."""

        ruta_sembrador = ruta_base / "sembrador"

        resultado = servicio.ejecutar_git(
            argumentos=[
                "clone",
                str(ruta_remoto),
                str(ruta_sembrador)
            ],
            ruta_repositorio=ruta_base,
            tiempo_maximo=60
        )

        self.assertTrue(resultado.exitoso)

        self._configurar_identidad(servicio, ruta_sembrador)

        if con_commit:
            (ruta_sembrador / "sembrado.sql").write_text(
                "SELECT 'sembrado';\n",
                encoding="utf-8"
            )

            resultado = servicio.ejecutar_git(
                argumentos=["add", "--", "sembrado.sql"],
                ruta_repositorio=ruta_sembrador
            )

            self.assertTrue(resultado.exitoso)

            resultado = servicio.ejecutar_git(
                argumentos=["commit", "-m", "Sembrado"],
                ruta_repositorio=ruta_sembrador
            )

            self.assertTrue(resultado.exitoso)

        resultado = servicio.ejecutar_git(
            argumentos=["switch", "-c", nombre_rama],
            ruta_repositorio=ruta_sembrador
        )

        self.assertTrue(resultado.exitoso)

        resultado = servicio.ejecutar_git(
            argumentos=[
                "push",
                "--porcelain",
                "origin",
                f"{nombre_rama}:refs/heads/{nombre_rama}"
            ],
            ruta_repositorio=ruta_sembrador,
            tiempo_maximo=60
        )

        self.assertTrue(resultado.exitoso)

    # -------------------------------------------------------------
    # Publicación exitosa.
    # -------------------------------------------------------------

    def test_publica_rama_nueva_Aunque_el_remoto_tiene_master(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            self._crear_rama(servicio, ruta_local, "feature/login")

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/login"
            )

            self.assertTrue(
                resultado.exitoso,
                f"La publicación falló: {resultado.error}"
            )

            # La rama remota quedó creada en el hash de la rama local.
            hash_local = self._hash_de_ref(
                servicio,
                ruta_local,
                "refs/heads/feature/login"
            )

            hash_remota = self._hash_de_ref(
                servicio,
                ruta_remoto,
                "refs/heads/feature/login"
            )

            self.assertEqual(hash_local, hash_remota)

            # El upstream quedó configurado y la sincronización 0/0.
            estado = servicio.obtener_estado_sincronizacion(ruta_local)

            self.assertTrue(estado.exitoso)
            self.assertTrue(estado.upstream_configurado)
            self.assertEqual(estado.rama_remota, "origin/feature/login")
            self.assertEqual(estado.commits_por_subir, 0)
            self.assertEqual(estado.commits_por_bajar, 0)

    def test_master_y_otras_ramas_remotas_conservan_sus_hashes(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            hash_master_antes = self._hash_de_ref(
                servicio,
                ruta_remoto,
                "refs/heads/master"
            )

            self._sembrar_rama_remota(
                servicio,
                ruta_base,
                ruta_remoto,
                "release",
                con_commit=True
            )

            hash_release_antes = self._hash_de_ref(
                servicio,
                ruta_remoto,
                "refs/heads/release"
            )

            self._fetch(servicio, ruta_local)

            self._crear_rama(servicio, ruta_local, "feature/login")

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/login"
            )

            self.assertTrue(resultado.exitoso)

            self.assertEqual(
                self._hash_de_ref(
                    servicio,
                    ruta_remoto,
                    "refs/heads/master"
                ),
                hash_master_antes
            )

            self.assertEqual(
                self._hash_de_ref(
                    servicio,
                    ruta_remoto,
                    "refs/heads/release"
                ),
                hash_release_antes
            )

    def test_rama_sin_commits_exclusivos_se_puede_publicar(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            # La rama nueva apunta exactamente al mismo commit que
            # master: publicarla debe ser posible igualmente.
            self._crear_rama(servicio, ruta_local, "feature/sin-cambios")

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/sin-cambios"
            )

            self.assertTrue(resultado.exitoso)

            self.assertTrue(
                self._ref_existe(
                    servicio,
                    ruta_remoto,
                    "refs/heads/feature/sin-cambios"
                )
            )

    def test_no_se_ejecuta_push_forzado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, _ = self._crear_escenario(ruta_base)

            self._crear_rama(servicio, ruta_local, "feature/login")

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/login"
            )

            self.assertTrue(resultado.exitoso)
            self.assertNotIn("--force", resultado.comando)
            self.assertNotIn("-f", resultado.comando.split()[:-1])

    # -------------------------------------------------------------
    # Bloqueos con Git real.
    # -------------------------------------------------------------

    def test_upstream_ya_configurado_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            # master ya quedó con upstream al preparar el escenario.
            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "master"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("ya está vinculada", resultado.error)
            self.assertIn("Push", resultado.error)
            self.assertNotIn("--force", resultado.comando)

    def test_upstream_configurado_con_ref_ausente_bloquea(self):
        """GG-PROMPT-004: upstream configurado aunque la
        remote-tracking ref esté ausente (gone) debe bloquear.

        La consulta estructurada usa for-each-ref
        %(upstream:short), que refleja la configuración de la rama
        aunque rev-parse @{upstream} no resuelva."""

        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            self._crear_rama(servicio, ruta_local, "feature")

            # Upstream configurado SOLO en la configuración de la
            # rama: la remote-tracking ref origin/feature no existe
            # (nunca se publicó ni se trajo con Fetch).
            for argumentos in (
                ["config", "branch.feature.remote", "origin"],
                [
                    "config",
                    "branch.feature.merge",
                    "refs/heads/feature"
                ]
            ):
                resultado = servicio.ejecutar_git(
                    argumentos=argumentos,
                    ruta_repositorio=ruta_local
                )

                self.assertTrue(resultado.exitoso)

            # Documentación del punto ciego corregido: rev-parse
            # @{upstream} FALLA aunque el upstream siga configurado.
            rev_parse = servicio.ejecutar_git(
                argumentos=[
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{upstream}"
                ],
                ruta_repositorio=ruta_local
            )

            self.assertFalse(rev_parse.exitoso)

            consulta = servicio.ejecutar_git(
                argumentos=[
                    "for-each-ref",
                    "--format=%(upstream:short)",
                    "refs/heads/feature"
                ],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(consulta.exitoso)
            self.assertEqual(consulta.salida.strip(), "origin/feature")

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("ya está vinculada", resultado.error)
            self.assertIn("origin/feature", resultado.error)

            # No hubo Push: el remoto sigue sin la rama.
            self.assertFalse(
                self._ref_existe(
                    servicio,
                    ruta_remoto,
                    "refs/heads/feature"
                )
            )

    def test_rama_remota_homonima_existente_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            self._sembrar_rama_remota(
                servicio,
                ruta_base,
                ruta_remoto,
                "feature/login",
                con_commit=True
            )

            self._fetch(servicio, ruta_local)

            self._crear_rama(servicio, ruta_local, "feature/login")

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/login"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("ya existe", resultado.error)
            self.assertIn("No se realizó ninguna publicación", resultado.error)

            # La rama remota conservó el hash del sembrador y la
            # local NO quedó vinculada.
            hash_sembrada = self._hash_de_ref(
                servicio,
                ruta_remoto,
                "refs/heads/feature/login"
            )

            hash_local = self._hash_de_ref(
                servicio,
                ruta_local,
                "refs/heads/feature/login"
            )

            self.assertNotEqual(hash_sembrada, hash_local)

            consulta_upstream = servicio.ejecutar_git(
                argumentos=[
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{upstream}"
                ],
                ruta_repositorio=ruta_local
            )

            self.assertFalse(consulta_upstream.exitoso)

    def test_homonima_con_mismo_commit_tambien_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            # La rama remota homónima apunta al mismo commit que la
            # local: el bloqueo es SIEMPRE.
            self._sembrar_rama_remota(
                servicio,
                ruta_base,
                ruta_remoto,
                "feature/igual",
                con_commit=False
            )

            self._fetch(servicio, ruta_local)

            self._crear_rama(servicio, ruta_local, "feature/igual")

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/igual"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("ya existe", resultado.error)

    def test_homonima_bloquea_Aunque_la_ref_local_no_exista(self):
        """ADDENDUM 01: la decisión crítica usa ls-remote, no solo
        refs/remotes (que dependen del refspec de Fetch)."""

        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(
                    ruta_base,
                    con_master_en_remoto=False
                )
            )

            # Refspec limitado: Fetch solo materializa master.
            resultado = servicio.ejecutar_git(
                argumentos=[
                    "config",
                    "remote.origin.fetch",
                    "+refs/heads/master:refs/remotes/origin/master"
                ],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(resultado.exitoso)

            self._publicar_master(servicio, ruta_local)
            self._fetch(servicio, ruta_local)

            self._sembrar_rama_remota(
                servicio,
                ruta_base,
                ruta_remoto,
                "feature/oculta",
                con_commit=True
            )

            self._crear_rama(servicio, ruta_local, "feature/oculta")

            # Precondición: la referencia local NO existe.
            self.assertFalse(
                self._ref_existe(
                    servicio,
                    ruta_local,
                    "refs/remotes/origin/feature/oculta"
                )
            )

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/oculta"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("ya existe", resultado.error)

    def test_cero_remotos_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, _ = (
                self._crear_escenario(
                    ruta_base,
                    con_master_en_remoto=False
                )
            )

            # Se elimina el remoto agregado por el escenario.
            resultado = servicio.ejecutar_git(
                argumentos=["remote", "remove", "origin"],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(resultado.exitoso)

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "master"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("ningún remoto", resultado.error)

    def test_varios_remotos_sin_upstream_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(
                    ruta_base,
                    con_master_en_remoto=False
                )
            )

            resultado = servicio.ejecutar_git(
                argumentos=["remote", "add", "respaldo", str(ruta_remoto)],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(resultado.exitoso)

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "master"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("varios remotos", resultado.error)

    def test_working_tree_modificado_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            self._crear_rama(servicio, ruta_local, "feature/login")

            (ruta_local / "archivo.sql").write_text(
                "SELECT 2;\n",
                encoding="utf-8"
            )

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/login"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("no está limpio", resultado.error)

            self.assertFalse(
                self._ref_existe(
                    servicio,
                    ruta_remoto,
                    "refs/heads/feature/login"
                )
            )

    def test_staging_sucio_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            self._crear_rama(servicio, ruta_local, "feature/login")

            (ruta_local / "preparado.sql").write_text(
                "SELECT 3;\n",
                encoding="utf-8"
            )

            resultado = servicio.ejecutar_git(
                argumentos=["add", "--", "preparado.sql"],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(resultado.exitoso)

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/login"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("no está limpio", resultado.error)

    def test_archivo_nuevo_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, ruta_remoto = (
                self._crear_escenario(ruta_base)
            )

            self._crear_rama(servicio, ruta_local, "feature/login")

            (ruta_local / "nuevo.sql").write_text(
                "SELECT 4;\n",
                encoding="utf-8"
            )

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/login"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("no está limpio", resultado.error)

    def test_conflicto_real_uu_bloquea_con_en_conflicto(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, _ = self._crear_escenario(ruta_base)

            self._crear_rama(servicio, ruta_local, "feature/conflicto")

            (ruta_local / "archivo.sql").write_text(
                "SELECT 'feature';\n",
                encoding="utf-8"
            )

            resultado = servicio.ejecutar_git(
                argumentos=["add", "--", "archivo.sql"],
                ruta_repositorio=ruta_local
            )
            self.assertTrue(resultado.exitoso)

            resultado = servicio.ejecutar_git(
                argumentos=["commit", "-m", "Cambio feature"],
                ruta_repositorio=ruta_local
            )
            self.assertTrue(resultado.exitoso)

            resultado = servicio.ejecutar_git(
                argumentos=["switch", "master"],
                ruta_repositorio=ruta_local
            )
            self.assertTrue(resultado.exitoso)

            (ruta_local / "archivo.sql").write_text(
                "SELECT 'master';\n",
                encoding="utf-8"
            )

            resultado = servicio.ejecutar_git(
                argumentos=["add", "--", "archivo.sql"],
                ruta_repositorio=ruta_local
            )
            self.assertTrue(resultado.exitoso)

            resultado = servicio.ejecutar_git(
                argumentos=["commit", "-m", "Cambio master"],
                ruta_repositorio=ruta_local
            )
            self.assertTrue(resultado.exitoso)

            resultado = servicio.ejecutar_git(
                argumentos=["switch", "feature/conflicto"],
                ruta_repositorio=ruta_local
            )
            self.assertTrue(resultado.exitoso)

            # Merge con conflicto real (U U en archivo.sql).
            servicio.ejecutar_git(
                argumentos=["merge", "master"],
                ruta_repositorio=ruta_local
            )

            # Se retira MERGE_HEAD para aislar el bloqueo por
            # conflicto (el estado UU del índice permanece).
            (ruta_local / ".git" / "MERGE_HEAD").unlink()

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/conflicto"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("conflicto", resultado.error.lower())
            self.assertIn("archivo.sql", resultado.error)

    def test_index_lock_bloquea_y_no_se_borra(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, _ = self._crear_escenario(ruta_base)

            self._crear_rama(servicio, ruta_local, "feature/login")

            ruta_lock = ruta_local / ".git" / "index.lock"

            ruta_lock.write_text("", encoding="utf-8")

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/login"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("index.lock", resultado.error)

            # El bloqueo NUNCA se elimina automáticamente.
            self.assertTrue(ruta_lock.exists())

    def test_merge_head_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, _ = self._crear_escenario(ruta_base)

            self._crear_rama(servicio, ruta_local, "feature/login")

            (ruta_local / ".git" / "MERGE_HEAD").write_text(
                "0" * 40,
                encoding="utf-8"
            )

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "feature/login"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("no publicará", resultado.error)

    def test_detached_head_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, _ = self._crear_escenario(ruta_base)

            resultado = servicio.ejecutar_git(
                argumentos=["checkout", "--detach", "master"],
                ruta_repositorio=ruta_local
            )

            self.assertTrue(resultado.exitoso)

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "master"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("no está asociado a una rama", resultado.error)

    def test_repositorio_sin_commits_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            ruta_local = ruta_base / "local"
            ruta_local.mkdir()

            servicio = ServicioRemotoGit()

            resultado = servicio.ejecutar_git(
                argumentos=["init", "-b", "master"],
                ruta_repositorio=ruta_local
            )
            self.assertTrue(resultado.exitoso)

            ruta_remoto = self._crear_remoto_bare(servicio, ruta_base)
            self._agregar_remoto(servicio, ruta_local, ruta_remoto)

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "master"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("todavía no tiene commits", resultado.error)

    def test_fallo_de_consulta_de_cambios_bloquea(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio = ServicioConConsultaDeCambiosRota()

            ruta_local = ruta_base / "local"
            ruta_local.mkdir()

            resultado = servicio.ejecutar_git(
                argumentos=["init", "-b", "master"],
                ruta_repositorio=ruta_local
            )
            self.assertTrue(resultado.exitoso)

            self._configurar_identidad(servicio, ruta_local)

            (ruta_local / "archivo.sql").write_text(
                "SELECT 1;\n",
                encoding="utf-8"
            )

            for argumentos in (
                ["add", "--", "archivo.sql"],
                ["commit", "-m", "Inicial"]
            ):
                resultado = servicio.ejecutar_git(
                    argumentos=argumentos,
                    ruta_repositorio=ruta_local
                )
                self.assertTrue(resultado.exitoso)

            ruta_remoto = self._crear_remoto_bare(servicio, ruta_base)
            self._agregar_remoto(servicio, ruta_local, ruta_remoto)

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "master"
            )

            # Un error de consulta NUNCA significa limpio.
            self.assertFalse(resultado.exitoso)
            self.assertIn("No fue posible determinar", resultado.error)

    def test_conflicto_estructural_bloquea_sin_importar_la_descripcion(
        self
    ):
        """La decisión usa en_conflicto, no el texto de descripcion."""

        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio = ServicioConConflictoEstructural()

            ruta_local = ruta_base / "local"
            ruta_local.mkdir()

            resultado = servicio.ejecutar_git(
                argumentos=["init", "-b", "master"],
                ruta_repositorio=ruta_local
            )
            self.assertTrue(resultado.exitoso)

            self._configurar_identidad(servicio, ruta_local)

            (ruta_local / "archivo.sql").write_text(
                "SELECT 1;\n",
                encoding="utf-8"
            )

            for argumentos in (
                ["add", "--", "archivo.sql"],
                ["commit", "-m", "Inicial"]
            ):
                resultado = servicio.ejecutar_git(
                    argumentos=argumentos,
                    ruta_repositorio=ruta_local
                )
                self.assertTrue(resultado.exitoso)

            ruta_remoto = self._crear_remoto_bare(servicio, ruta_base)
            self._agregar_remoto(servicio, ruta_local, ruta_remoto)

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "master"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn("conflicto", resultado.error.lower())
            self.assertIn("paquete/conflicto.sql", resultado.error)
            self.assertIn("no elige", resultado.error)

    def test_fallo_de_consulta_remota_bloquea_sin_push(self):
        """ADDENDUM 01: un error de ls-remote bloquea; nunca se
        interpreta como ausencia de la rama."""

        with tempfile.TemporaryDirectory() as carpeta:
            ruta_base = Path(carpeta)

            servicio, ruta_local, _ = self._crear_escenario(
                ruta_base,
                con_master_en_remoto=False
            )

            # Remoto configurado pero inalcanzable: se reapunta
            # origin a una ruta que no existe (remove + add, sin
            # set-url, que GestorGit nunca ejecuta en producción).
            for argumentos_remoto in (
                ["remote", "remove", "origin"],
                [
                    "remote",
                    "add",
                    "origin",
                    str(ruta_base / "remoto_inexistente.git")
                ]
            ):
                resultado = servicio.ejecutar_git(
                    argumentos=argumentos_remoto,
                    ruta_repositorio=ruta_local
                )

                self.assertTrue(resultado.exitoso)

            resultado = servicio.publicar_rama_local(
                ruta_local,
                "origin",
                "master"
            )

            self.assertFalse(resultado.exitoso)
            self.assertIn(
                "No fue posible consultar el remoto",
                resultado.error
            )

    def test_datos_de_entrada_invalidos_bloquean(self):
        servicio = ServicioRemotoGit()

        for remoto, rama in (
            (None, "master"),
            ("", "master"),
            ("-origen", "master"),
            ("origin", None),
            ("origin", "   "),
            ("origin", "-rama")
        ):
            with self.subTest(remoto=remoto, rama=rama):
                resultado = servicio.publicar_rama_local(
                    "ruta/que/no/importa",
                    remoto,
                    rama
                )

                self.assertFalse(resultado.exitoso)
                self.assertTrue(resultado.error)


# =================================================================
# Pruebas del espía: argumentos exactos y segunda validación.
# =================================================================

class PruebasPublicarRamaEspia(unittest.TestCase):
    """
    Escenarios con el espía: comando productivo exacto y detección
    de cambios externos entre validaciones (TOCTOU).
    """

    def _espia_por_defecto(self, **parametros):
        parametros_completos = {
            "rama_actual": "feature",
            "remotos": ("origin",),
            "remoto_seguro": "origin",
            "respuestas_upstream": [(True, "")],
            "respuestas_ls_remote": [(True, "")],
        }

        parametros_completos.update(parametros)

        return ServicioRemotoEspiaPublicar(
            **parametros_completos
        )

    def _push_ejecutados(self, espia):
        return [
            llamada
            for llamada in espia.llamadas_ejecutar_git
            if llamada[0] == "push"
        ]

    def test_argumentos_exactos_del_push_productivo(self):
        espia = self._espia_por_defecto()

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertTrue(resultado.exitoso)

        self.assertIn(
            [
                "push",
                "--porcelain",
                "--set-upstream",
                "origin",
                "feature:refs/heads/feature"
            ],
            espia.llamadas_ejecutar_git
        )

    def test_argumentos_exactos_de_ls_remote(self):
        """ADDENDUM 01: consulta directa de solo lectura al remoto."""

        espia = self._espia_por_defecto()

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertTrue(resultado.exitoso)

        self.assertIn(
            ["ls-remote", "--heads", "origin", "refs/heads/feature"],
            espia.llamadas_ejecutar_git
        )

    def test_ausencia_de_opciones_prohibidas_en_el_push(self):
        espia = self._espia_por_defecto()

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertTrue(resultado.exitoso)

        for llamada in espia.llamadas_ejecutar_git:
            for prohibida in (
                "--force",
                "--force-with-lease",
                "-f",
                "--all",
                "--tags",
                "--mirror",
                "--delete",
                "--follow-tags"
            ):
                self.assertNotIn(
                    prohibida,
                    llamada,
                    f"Llamada {llamada} contiene '{prohibida}'."
                )

    def test_ausencia_de_set_url_remote_remove_y_remote_rename(self):
        """La publicación nunca modifica la configuración de remotos."""

        espia = self._espia_por_defecto()

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertTrue(resultado.exitoso)

        for llamada in espia.llamadas_ejecutar_git:
            if llamada[0] == "remote":
                for prohibido in ("set-url", "remove", "rename"):
                    self.assertNotIn(
                        prohibido,
                        llamada,
                        f"Llamada {llamada} contiene "
                        f"'remote {prohibido}'."
                    )

            if llamada[0] == "config":
                self.fail(
                    "La publicación no debe ejecutar git config: "
                    f"{llamada}"
                )

    def test_sin_fetch_automatico_dentro_del_servicio(self):
        """ADDENDUM 01: la consulta fresca la aporta ls-remote."""

        espia = self._espia_por_defecto()

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertTrue(resultado.exitoso)

        for llamada in espia.llamadas_ejecutar_git:
            self.assertNotIn("fetch", llamada)

    def test_fallo_de_push_devuelve_resultado_controlado(self):
        espia = self._espia_por_defecto(
            push_exitoso=False,
            push_error="rechazo simulado del remoto"
        )

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("rechazo simulado", resultado.error)

        # La consulta remota previa sí se ejecutó.
        self.assertEqual(len(self._push_ejecutados(espia)), 1)

    def test_rama_remota_homonima_detectada_por_ls_remote_bloquea(self):
        """ADDENDUM 01: ls-remote fresco detecta la rama aparecida
        inmediatamente antes del Push y bloquea."""

        espia = self._espia_por_defecto(
            respuestas_ls_remote=[
                (True, "abc123\trefs/heads/feature")
            ]
        )

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("ya existe", resultado.error)
        self.assertIn("No se realizó ninguna publicación", resultado.error)

        self.assertEqual(self._push_ejecutados(espia), [])

    def test_fallo_de_ls_remote_bloquea_sin_push(self):
        espia = self._espia_por_defecto(
            respuestas_ls_remote=[(False, "")]
        )

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("No fue posible consultar el remoto", resultado.error)

        self.assertEqual(self._push_ejecutados(espia), [])

    def test_segunda_validacion_detecta_working_tree_ensuciado(self):
        cambio = CambioArchivo(
            ruta="pendiente.sql",
            estado_indice=" ",
            estado_trabajo="M",
            descripcion="Modificado sin preparar",
            preparado=False,
            en_conflicto=False
        )

        espia = self._espia_por_defecto(
            resultados_cambios=[
                ResultadoCambios(exitoso=True, cambios=[]),
                ResultadoCambios(exitoso=True, cambios=[cambio])
            ]
        )

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("no está limpio", resultado.error)

        self.assertEqual(self._push_ejecutados(espia), [])

        # La consulta remota ni siquiera llegó a ejecutarse.
        llamadas_ls_remote = [
            llamada
            for llamada in espia.llamadas_ejecutar_git
            if llamada[0] == "ls-remote"
        ]

        self.assertEqual(llamadas_ls_remote, [])

    def test_segunda_validacion_detecta_cambio_externo_de_head(self):
        estado_primero = EstadoRepositorio(
            es_repositorio=True,
            ruta_raiz="repositorio",
            rama_actual="feature",
            tiene_commits=True,
            remotos=["origin"]
        )

        estado_segundo = EstadoRepositorio(
            es_repositorio=True,
            ruta_raiz="repositorio",
            rama_actual="otra-rama",
            tiene_commits=True,
            remotos=["origin"]
        )

        espia = self._espia_por_defecto(
            estados_repositorio=[estado_primero, estado_segundo]
        )

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("La rama actual cambió", resultado.error)

        self.assertEqual(self._push_ejecutados(espia), [])

    def test_fallo_de_consulta_de_upstream_bloquea_sin_remote_ni_push(
        self
    ):
        """Un error consultando el upstream NUNCA equivale a
        'sin upstream': bloquea antes de ls-remote y del Push."""

        espia = self._espia_por_defecto(
            respuestas_upstream=[(False, "")]
        )

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn(
            "No fue posible consultar el upstream",
            resultado.error
        )

        self.assertEqual(self._push_ejecutados(espia), [])

        llamadas_ls_remote = [
            llamada
            for llamada in espia.llamadas_ejecutar_git
            if llamada[0] == "ls-remote"
        ]

        self.assertEqual(llamadas_ls_remote, [])

    def test_segunda_validacion_detecta_upstream_aparecido(self):
        espia = self._espia_por_defecto(
            respuestas_upstream=[
                (True, ""),
                (True, "origin/feature")
            ]
        )

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("ya está vinculada", resultado.error)

        self.assertEqual(self._push_ejecutados(espia), [])

        # El bloqueo ocurre ANTES de la consulta remota.
        llamadas_ls_remote = [
            llamada
            for llamada in espia.llamadas_ejecutar_git
            if llamada[0] == "ls-remote"
        ]

        self.assertEqual(llamadas_ls_remote, [])

    def test_segunda_validacion_detecta_cambio_del_remoto_seguro(self):
        espia = self._espia_por_defecto(
            resultados_remoto=[
                ResultadoComando(
                    exitoso=True,
                    codigo_salida=0,
                    salida="origin",
                    error="",
                    comando=""
                ),
                ResultadoComando(
                    exitoso=True,
                    codigo_salida=0,
                    salida="respaldo",
                    error="",
                    comando=""
                )
            ]
        )

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("remoto determinable cambió", resultado.error)

        self.assertEqual(self._push_ejecutados(espia), [])

    def test_rama_esperada_distinta_bloquea_en_la_primera_validacion(self):
        espia = self._espia_por_defecto(rama_actual="master")

        resultado = espia.publicar_rama_local(
            "repositorio",
            "origin",
            "feature"
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("La rama actual cambió", resultado.error)

        self.assertEqual(self._push_ejecutados(espia), [])


# =================================================================
# Pruebas de la interfaz sin Tk real.
# =================================================================

class VariableDoble:
    """Doble mínima de variable Tkinter."""

    def __init__(self, valor=""):
        self.valor = valor
        self.valores_establecidos = []

    def get(self):
        return self.valor

    def set(self, valor):
        self.valor = valor
        self.valores_establecidos.append(valor)


class BotonDoble:
    """Doble mínima de botón ttk que registra su estado."""

    def __init__(self):
        self.estado = None
        self.configuraciones = []

    def config(self, **argumentos):
        if "state" in argumentos:
            self.estado = argumentos["state"]
            self.configuraciones.append(argumentos["state"])


class VentanaDoble:
    """Doble mínima de ventana Tk que siempre existe."""

    def winfo_exists(self):
        return True


class TablaDoble:
    """Doble mínima de tabla de ramas sin selección."""

    def selection(self):
        return ()


class ServicioPublicarDoble:
    """Doble del servicio para el hilo de publicación."""

    def __init__(self, exitoso=True, error=""):
        self.exitoso = exitoso
        self.error = error
        self.llamadas_publicar = 0
        self.llamadas_fetch = 0

    def publicar_rama_local(self, ruta, remoto, rama):
        self.llamadas_publicar += 1

        return ResultadoComando(
            exitoso=self.exitoso,
            codigo_salida=(
                0
                if self.exitoso
                else 1
            ),
            salida="",
            error=self.error,
            comando=""
        )

    def ejecutar_fetch(self, ruta, remoto):
        self.llamadas_fetch += 1

        return ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando=""
        )

    def obtener_estado_sincronizacion(self, ruta):
        return estado_sincronizacion_favorable()


class HiloDoble:
    """Doble de threading.Thread que no inicia ningún hilo real."""

    instancias = []

    def __init__(self, target=None, args=(), daemon=None):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.iniciado = False

        HiloDoble.instancias.append(self)

    def start(self):
        self.iniciado = True


def estado_sincronizacion_favorable():
    """Estado de sincronización favorable para publicar 'feature'."""

    return EstadoSincronizacion(
        exitoso=True,
        rama_local="feature",
        remoto="origin",
        rama_remota="origin/feature",
        upstream_configurado=False,
        rama_remota_existe=False
    )


class PruebaPublicarRamaGui(unittest.TestCase):
    """
    Pruebas de confirmación, hilo, cola y procesador sin Tk real.
    """

    def setUp(self):
        HiloDoble.instancias = []

    def _crear_aplicacion(self, **ajustes):
        aplicacion = principal.AplicacionGit.__new__(
            principal.AplicacionGit
        )

        aplicacion.ventana_ramas = VentanaDoble()
        aplicacion.tabla_ramas = TablaDoble()
        aplicacion.variable_estado_ramas = VariableDoble()
        aplicacion.variable_rama_actual_ventana = VariableDoble()
        aplicacion.variable_nueva_rama = VariableDoble()
        aplicacion.boton_cambiar_rama = BotonDoble()
        aplicacion.boton_crear_rama = BotonDoble()
        aplicacion.boton_actualizar_ramas = BotonDoble()
        aplicacion.boton_publicar_rama = BotonDoble()
        aplicacion.rama_actual_ventana_actual = "feature"

        aplicacion.ruta_repositorio = "C:/ruta/repo"
        aplicacion.remotos_repositorio = ["origin"]
        aplicacion.fetch_exitoso_en_sesion = True
        aplicacion.operacion_remota_en_curso = False

        aplicacion.estado_sincronizacion_actual = (
            EstadoSincronizacion(
                exitoso=True,
                rama_local="feature",
                remoto="origin",
                rama_remota="origin/feature",
                upstream_configurado=False,
                rama_remota_existe=False
            )
        )

        aplicacion.variable_estado = VariableDoble()
        aplicacion.variable_ultima_consulta = VariableDoble()

        # Variables que actualiza aplicar_estado_sincronizacion.
        aplicacion.variable_upstream = VariableDoble()
        aplicacion.variable_rama_remota = VariableDoble()
        aplicacion.variable_por_subir = VariableDoble()
        aplicacion.variable_por_bajar = VariableDoble()
        aplicacion.variable_estado_sincronizacion = VariableDoble()

        aplicacion.llamadas_controles = []
        aplicacion.actualizar_controles_operacion_remota = (
            lambda: aplicacion.llamadas_controles.append(1)
        )

        for nombre, valor in ajustes.items():
            setattr(aplicacion, nombre, valor)

        return aplicacion

    # -------------------------------------------------------------
    # Estado del botón.
    # -------------------------------------------------------------

    def test_boton_publicar_existe_en_la_ventana_de_ramas(self):
        codigo = inspect.getsource(
            principal.AplicacionGit.crear_ventana_ramas
        )

        self.assertIn("Publicar rama local...", codigo)
        self.assertIn("boton_publicar_rama", codigo)
        self.assertIn("confirmar_publicacion_rama", codigo)

    def test_confirmacion_de_creacion_menciona_publicar_rama(self):
        """La confirmación de Crear rama enseña el flujo actual:
        publicar es una acción posterior y explícita."""

        codigo = inspect.getsource(
            principal.AplicacionGit.confirmar_creacion_rama
        )

        self.assertIn("Publicar rama local", codigo)
        self.assertNotIn("hasta que se implemente", codigo)

    def test_boton_habilitado_condiciones_favorables(self):
        aplicacion = self._crear_aplicacion()

        aplicacion.actualizar_estado_botones_ventana_ramas()

        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.NORMAL
        )

    def test_boton_deshabilitado_sin_fetch_exitoso(self):
        aplicacion = self._crear_aplicacion(
            fetch_exitoso_en_sesion=False
        )

        aplicacion.actualizar_estado_botones_ventana_ramas()

        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.DISABLED
        )

    def test_boton_deshabilitado_con_upstream(self):
        estado = EstadoSincronizacion(
            exitoso=True,
            rama_local="feature",
            remoto="origin",
            rama_remota="origin/feature",
            upstream_configurado=True,
            rama_remota_existe=True
        )

        aplicacion = self._crear_aplicacion(
            estado_sincronizacion_actual=estado
        )

        aplicacion.actualizar_estado_botones_ventana_ramas()

        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.DISABLED
        )

    def test_boton_deshabilitado_con_rama_remota_conocida(self):
        estado = EstadoSincronizacion(
            exitoso=True,
            rama_local="feature",
            remoto="origin",
            rama_remota="origin/feature",
            upstream_configurado=False,
            rama_remota_existe=True
        )

        aplicacion = self._crear_aplicacion(
            estado_sincronizacion_actual=estado
        )

        aplicacion.actualizar_estado_botones_ventana_ramas()

        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.DISABLED
        )

    def test_boton_deshabilitado_durante_operacion_remota(self):
        aplicacion = self._crear_aplicacion(
            operacion_remota_en_curso=True
        )

        aplicacion.actualizar_estado_botones_ventana_ramas()

        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.DISABLED
        )

        self.assertEqual(
            aplicacion.boton_actualizar_ramas.estado,
            principal.tk.DISABLED
        )

        self.assertEqual(
            aplicacion.boton_cambiar_rama.estado,
            principal.tk.DISABLED
        )

        self.assertEqual(
            aplicacion.boton_crear_rama.estado,
            principal.tk.DISABLED
        )

    def test_boton_deshabilitado_con_varios_remotos(self):
        aplicacion = self._crear_aplicacion(
            remotos_repositorio=["origin", "respaldo"]
        )

        aplicacion.actualizar_estado_botones_ventana_ramas()

        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.DISABLED
        )

    # -------------------------------------------------------------
    # Confirmación.
    # -------------------------------------------------------------

    def test_confirmacion_contenido_y_parent_ventana_ramas(self):
        aplicacion = self._crear_aplicacion()

        with mock.patch.object(
            principal.threading,
            "Thread",
            HiloDoble
        ):
            with mock.patch.object(
                principal.messagebox,
                "askyesno",
                return_value=True
            ) as preguntar:
                aplicacion.confirmar_publicacion_rama()

        self.assertEqual(preguntar.call_count, 1)

        mensaje = preguntar.call_args.args[1]

        self.assertIn("feature", mensaje)
        self.assertIn("origin", mensaje)
        self.assertIn("refs/heads/feature", mensaje)
        self.assertIn("operación de red", mensaje)
        self.assertIn("volverá a consultar el remoto", mensaje)
        self.assertIn("upstream", mensaje)
        self.assertIn("Push forzado", mensaje)
        self.assertIn("¿Desea continuar?", mensaje)

        self.assertIs(
            preguntar.call_args.kwargs.get("parent"),
            aplicacion.ventana_ramas
        )

    def test_confirmar_cancelado_no_lanza_hilo_ni_operacion(self):
        aplicacion = self._crear_aplicacion()

        with mock.patch.object(
            principal.threading,
            "Thread",
            HiloDoble
        ):
            with mock.patch.object(
                principal.messagebox,
                "askyesno",
                return_value=False
            ):
                aplicacion.confirmar_publicacion_rama()

        self.assertEqual(HiloDoble.instancias, [])
        self.assertFalse(aplicacion.operacion_remota_en_curso)

    def test_confirmar_aceptado_bloquea_controles_y_lanza_hilo(self):
        aplicacion = self._crear_aplicacion()

        with mock.patch.object(
            principal.threading,
            "Thread",
            HiloDoble
        ):
            with mock.patch.object(
                principal.messagebox,
                "askyesno",
                return_value=True
            ):
                aplicacion.confirmar_publicacion_rama()

        self.assertTrue(aplicacion.operacion_remota_en_curso)
        self.assertEqual(aplicacion.llamadas_controles, [1])

        self.assertEqual(len(HiloDoble.instancias), 1)

        hilo = HiloDoble.instancias[0]

        self.assertEqual(hilo.target, aplicacion.trabajo_publicar_rama)
        self.assertEqual(
            hilo.args,
            ("C:/ruta/repo", "origin", "feature")
        )

    def test_confirmar_sin_fetch_muestra_aviso_y_no_lanza_hilo(self):
        aplicacion = self._crear_aplicacion(
            fetch_exitoso_en_sesion=False
        )

        with mock.patch.object(
            principal.threading,
            "Thread",
            HiloDoble
        ):
            with mock.patch.object(
                principal.messagebox,
                "askyesno",
                return_value=True
            ) as preguntar:
                with mock.patch.object(
                    principal.messagebox,
                    "showinfo"
                ) as informar:
                    aplicacion.confirmar_publicacion_rama()

        informar.assert_called_once()
        self.assertIsNone(preguntar.call_args)

        self.assertEqual(HiloDoble.instancias, [])

    # -------------------------------------------------------------
    # Hilo y cola.
    # -------------------------------------------------------------

    def _aplicacion_para_hilo(self, exitoso=True, error=""):
        aplicacion = self._crear_aplicacion()

        aplicacion.servicio_git = ServicioPublicarDoble(
            exitoso=exitoso,
            error=error
        )

        aplicacion.cola_resultados = queue.Queue()

        return aplicacion

    def test_trabajo_publicar_rama_solo_encola_con_tipo_propio(self):
        aplicacion = self._aplicacion_para_hilo()

        aplicacion.trabajo_publicar_rama(
            "C:/ruta/repo",
            "origin",
            "feature"
        )

        elemento = aplicacion.cola_resultados.get_nowait()

        self.assertEqual(elemento[0], "publicar_rama")
        self.assertNotEqual(elemento[0], "push")
        self.assertEqual(elemento[1], "C:/ruta/repo")
        self.assertEqual(elemento[2], "origin")
        self.assertEqual(elemento[3], "feature")
        self.assertTrue(elemento[4].exitoso)

        self.assertEqual(
            aplicacion.servicio_git.llamadas_publicar,
            1
        )

    def test_trabajo_publicar_rama_no_ejecuta_fetch_automatico(self):
        """ADDENDUM 01: sin Fetch automático después del Push."""

        aplicacion = self._aplicacion_para_hilo()

        aplicacion.trabajo_publicar_rama(
            "C:/ruta/repo",
            "origin",
            "feature"
        )

        self.assertEqual(
            aplicacion.servicio_git.llamadas_fetch,
            0
        )

    def test_trabajo_publicar_rama_no_toca_tkinter(self):
        codigo = inspect.getsource(
            principal.AplicacionGit.trabajo_publicar_rama
        )

        for prohibido in (
            "messagebox",
            ".config(",
            ".set(",
            "winfo_exists",
            "destroy("
        ):
            self.assertNotIn(
                prohibido,
                codigo,
                f"El hilo no debe tocar Tkinter: contiene "
                f"'{prohibido}'."
            )

    # -------------------------------------------------------------
    # Procesador del resultado.
    # -------------------------------------------------------------

    def _aplicacion_para_procesador(self):
        aplicacion = self._crear_aplicacion(
            operacion_remota_en_curso=True
        )

        aplicacion.llamadas_refrescar = []
        aplicacion.refrescar_despues_de_ramas = (
            lambda: aplicacion.llamadas_refrescar.append(1)
        )

        aplicacion.llamadas_estado_local = []
        aplicacion.cargar_estado_sincronizacion_local = (
            lambda: aplicacion.llamadas_estado_local.append(1)
        )

        aplicacion.llamadas_botones_sincronizacion = []
        aplicacion.actualizar_estado_botones_sincronizacion = (
            lambda: aplicacion.llamadas_botones_sincronizacion.append(1)
        )

        return aplicacion

    def test_exito_invalida_fetch_y_refresca_local(self):
        aplicacion = self._aplicacion_para_procesador()

        resultado = ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando=""
        )

        with mock.patch.object(
            principal.messagebox,
            "showinfo"
        ) as informar:
            aplicacion.procesar_resultado_publicar_rama(
                "C:/ruta/repo",
                "origin",
                "feature",
                resultado
            )

        self.assertFalse(aplicacion.operacion_remota_en_curso)
        self.assertFalse(aplicacion.fetch_exitoso_en_sesion)
        self.assertEqual(aplicacion.llamadas_refrescar, [1])

        informar.assert_called_once()

        mensaje = informar.call_args.args[1]

        self.assertIn("era solamente local", mensaje)
        self.assertIn("upstream", mensaje)
        self.assertIn("origin/feature", mensaje)
        self.assertIn("Push normal", mensaje)

    def test_exito_no_actualiza_estado_remoto_como_fresco(self):
        """ADDENDUM 01: sin Fetch posterior; el refresco es LOCAL."""

        aplicacion = self._aplicacion_para_procesador()

        resultado = ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando=""
        )

        with mock.patch.object(principal.messagebox, "showinfo"):
            aplicacion.procesar_resultado_publicar_rama(
                "C:/ruta/repo",
                "origin",
                "feature",
                resultado
            )

        # La última consulta explica que se exige Fetch manual nuevo.
        self.assertIn(
            "Fetch nuevamente",
            aplicacion.variable_ultima_consulta.valores_establecidos[-1]
        )

    def test_fallo_muestra_error_controlado_y_no_refresca_ramas(self):
        aplicacion = self._aplicacion_para_procesador()

        resultado = ResultadoComando(
            exitoso=False,
            codigo_salida=1,
            salida="",
            error="La rama remota 'feature' ya existe en 'origin'.",
            comando=""
        )

        with mock.patch.object(
            principal.messagebox,
            "showerror"
        ) as mostrar_error:
            aplicacion.procesar_resultado_publicar_rama(
                "C:/ruta/repo",
                "origin",
                "feature",
                resultado
            )

        mostrar_error.assert_called_once()
        self.assertIn(
            "ya existe",
            mostrar_error.call_args.args[1]
        )

        self.assertFalse(aplicacion.operacion_remota_en_curso)
        self.assertFalse(aplicacion.fetch_exitoso_en_sesion)
        self.assertEqual(aplicacion.llamadas_refrescar, [])
        self.assertEqual(aplicacion.llamadas_estado_local, [1])

    def test_procesador_descarta_resultado_si_cambio_repositorio(self):
        aplicacion = self._aplicacion_para_procesador()
        aplicacion.fetch_exitoso_en_sesion = True

        resultado = ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando=""
        )

        with mock.patch.object(principal.messagebox, "showinfo") as inf:
            aplicacion.procesar_resultado_publicar_rama(
                "C:/otra/ruta",
                "origin",
                "feature",
                resultado
            )

        inf.assert_not_called()
        self.assertEqual(aplicacion.llamadas_refrescar, [])
        self.assertTrue(aplicacion.fetch_exitoso_en_sesion)

    # -------------------------------------------------------------
    # Coherencia del botón Publicar tras Fetch/publicación (005).
    # -------------------------------------------------------------

    def _aplicacion_para_estado(self, **ajustes):
        aplicacion = self._crear_aplicacion(**ajustes)

        aplicacion.llamadas_botones_sincronizacion = []
        aplicacion.actualizar_estado_botones_sincronizacion = (
            lambda: aplicacion.llamadas_botones_sincronizacion.append(1)
        )

        return aplicacion

    def _resultado_exitoso(self):
        return ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando=""
        )

    def _resultado_fallido(self):
        return ResultadoComando(
            exitoso=False,
            codigo_salida=1,
            salida="",
            error="fallo simulado de red",
            comando=""
        )

    def test_fetch_exitoso_habilita_publicar_con_ventana_abierta(self):
        """Caso A: Fetch exitoso con la ventana abierta habilita
        Publicar sin cerrar/reabrir ni tocar otros controles."""

        aplicacion = self._aplicacion_para_estado(
            fetch_exitoso_en_sesion=False
        )

        aplicacion.procesar_resultado_fetch(
            "C:/ruta/repo",
            "origin",
            self._resultado_exitoso(),
            estado_sincronizacion_favorable()
        )

        self.assertTrue(aplicacion.fetch_exitoso_en_sesion)
        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.NORMAL
        )

    def test_fetch_fallido_deshabilita_publicar(self):
        """Caso B: un Fetch fallido tras uno previo exitoso deja el
        botón DISABLED, sin conservar el estado anterior."""

        aplicacion = self._aplicacion_para_estado()

        aplicacion.actualizar_estado_botones_ventana_ramas()

        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.NORMAL
        )

        with mock.patch.object(principal.messagebox, "showerror"):
            aplicacion.procesar_resultado_fetch(
                "C:/ruta/repo",
                "origin",
                self._resultado_fallido(),
                None
            )

        self.assertFalse(aplicacion.fetch_exitoso_en_sesion)
        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.DISABLED
        )

    def test_fetch_exitoso_sin_estado_no_reutiliza_estado_viejo(self):
        """Caso C: Fetch exitoso sin estado calculable NO debe dejar
        que un estado anterior favorable haga parecer publicable la
        rama."""

        aplicacion = self._aplicacion_para_estado()

        aplicacion.actualizar_estado_botones_ventana_ramas()

        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.NORMAL
        )

        aplicacion.procesar_resultado_fetch(
            "C:/ruta/repo",
            "origin",
            self._resultado_exitoso(),
            None
        )

        self.assertTrue(aplicacion.fetch_exitoso_en_sesion)
        self.assertIsNone(aplicacion.estado_sincronizacion_actual)
        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.DISABLED
        )

    def test_fetch_exitoso_con_sincronizacion_fallida_deshabilita(self):
        aplicacion = self._aplicacion_para_estado()

        estado_fallido = EstadoSincronizacion(
            exitoso=False,
            rama_local="feature",
            remoto="origin",
            error="No se pudo calcular el estado."
        )

        aplicacion.procesar_resultado_fetch(
            "C:/ruta/repo",
            "origin",
            self._resultado_exitoso(),
            estado_fallido
        )

        self.assertTrue(aplicacion.fetch_exitoso_en_sesion)
        self.assertIsNotNone(aplicacion.estado_sincronizacion_actual)
        self.assertFalse(
            aplicacion.estado_sincronizacion_actual.exitoso
        )
        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.DISABLED
        )

    def test_publicacion_fallida_deshabilita_publicar_sin_fetch(self):
        aplicacion = self._aplicacion_para_estado()
        aplicacion.servicio_git = ServicioPublicarDoble()

        aplicacion.actualizar_estado_botones_ventana_ramas()

        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.NORMAL
        )

        # La operación estaba en curso cuando llegó el resultado.
        aplicacion.operacion_remota_en_curso = True

        with mock.patch.object(principal.messagebox, "showerror"):
            aplicacion.procesar_resultado_publicar_rama(
                "C:/ruta/repo",
                "origin",
                "feature",
                self._resultado_fallido()
            )

        self.assertFalse(aplicacion.operacion_remota_en_curso)
        self.assertFalse(aplicacion.fetch_exitoso_en_sesion)
        self.assertEqual(
            aplicacion.boton_publicar_rama.estado,
            principal.tk.DISABLED
        )

        # Sin Fetch automático para compensar el fallo.
        self.assertEqual(
            aplicacion.servicio_git.llamadas_fetch,
            0
        )


class PruebaVentanaRamasLayout(unittest.TestCase):
    """
    Pruebas estáticas del layout de la ventana de ramas.

    GG-PROMPT-007: el botón Publicar quedaba parcialmente recortado
    por el borde inferior. La tabla (fila 3) debe ser la zona que
    absorbe el redimensionamiento vertical, sin cambiar lógica ni
    semántica de habilitación.
    """

    def _arbol_metodo(self, nombre):
        fuente = inspect.getsource(
            getattr(principal.AplicacionGit, nombre)
        )

        # El código del método llega indentado: se dedenta antes de
        # parsearlo con ast.
        return ast.parse(textwrap.dedent(fuente))

    def test_la_fila_de_la_tabla_es_verticalmente_flexible(self):
        arbol = self._arbol_metodo("crear_ventana_ramas")

        fila_flexible = False

        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "rowconfigure"
                and nodo.args
                and isinstance(nodo.args[0], ast.Constant)
                and nodo.args[0].value == 3
            ):
                for palabra in nodo.keywords:
                    if (
                        palabra.arg == "weight"
                        and isinstance(palabra.value, ast.Constant)
                        and palabra.value.value == 1
                    ):
                        fila_flexible = True

        self.assertTrue(
            fila_flexible,
            "marco_ramas.rowconfigure(3, weight=1) debe hacer de la "
            "tabla la zona verticalmente flexible."
        )

        # La tabla conserva sticky="nsew" para llenar su fila.
        tabla_estirable = False

        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "grid"
                and isinstance(nodo.func.value, ast.Name)
                and nodo.func.value.id == "marco_tabla"
            ):
                for palabra in nodo.keywords:
                    if (
                        palabra.arg == "sticky"
                        and isinstance(palabra.value, ast.Constant)
                        and palabra.value.value == "nsew"
                    ):
                        tabla_estirable = True

        self.assertTrue(
            tabla_estirable,
            "marco_tabla debe conservar sticky='nsew'."
        )

    def test_boton_publicar_sigue_en_marco_acciones_con_su_comando(
        self
    ):
        arbol = self._arbol_metodo("crear_ventana_ramas")

        encontrada = False

        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Assign):
                continue

            objetivo = nodo.targets[0]

            if not (
                isinstance(objetivo, ast.Attribute)
                and objetivo.attr == "boton_publicar_rama"
            ):
                continue

            llamada = nodo.value

            if not (
                isinstance(llamada, ast.Call)
                and llamada.args
                and isinstance(llamada.args[0], ast.Name)
                and llamada.args[0].id == "marco_acciones"
            ):
                continue

            for palabra in llamada.keywords:
                if palabra.arg != "command":
                    continue

                valor = palabra.value

                if (
                    isinstance(valor, ast.Attribute)
                    and valor.attr == "confirmar_publicacion_rama"
                ):
                    encontrada = True

        self.assertTrue(
            encontrada,
            "boton_publicar_rama debe seguir en marco_acciones con "
            "command=self.confirmar_publicacion_rama."
        )

    def test_crear_ventana_ramas_sigue_sin_ser_modal(self):
        arbol = self._arbol_metodo("crear_ventana_ramas")

        prohibidas = []

        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in ("grab_set", "wait_window")
            ):
                prohibidas.append(nodo.func.attr)

        self.assertEqual(
            prohibidas,
            [],
            "La ventana de ramas debe seguir siendo NO modal."
        )

    def test_puede_publicar_rama_actual_conserva_su_semantica(self):
        fuente = inspect.getsource(
            principal.AplicacionGit.puede_publicar_rama_actual
        )

        for marcador in (
            "fetch_exitoso_en_sesion",
            "len(self.remotos_repositorio) != 1",
            "estado.rama_local != self.rama_actual_ventana_actual",
            "estado.upstream_configurado",
            "estado.rama_remota_existe",
        ):
            self.assertIn(
                marcador,
                fuente,
                f"La semántica de puede_publicar_rama_actual perdió "
                f"la condición '{marcador}'."
            )

        # La publicación nunca exige commits por enviar.
        self.assertNotIn("commits_por_subir", fuente)


class PruebaTextoEducativoRamas(unittest.TestCase):
    """
    Pruebas estáticas del texto educativo superior de la ventana
    de ramas.

    GG-PROMPT-008: la frase histórica "No se ejecuta Fetch, Pull,
    Push, Merge ni Rebase desde esta ventana" quedó obsoleta al
    existir "Publicar rama local..." en la propia ventana.
    """

    @classmethod
    def setUpClass(cls):
        cls.fuente = inspect.getsource(
            principal.AplicacionGit.crear_ventana_ramas
        )

    def test_el_texto_menciona_publicar_rama_local(self):
        self.assertIn(
            "Publicar rama local...",
            self.fuente
        )

    def test_explica_publicar_como_accion_remota_con_push(self):
        self.assertIn("REMOTA", self.fuente)
        self.assertIn("consulta el remoto", self.fuente)
        self.assertIn("puede ejecutar", self.fuente)
        self.assertIn("Push", self.fuente)

    def test_la_frase_obsoleta_ya_no_existe(self):
        self.assertNotIn(
            "No se ejecuta Fetch, Pull, Push",
            self.fuente
        )

        self.assertNotIn(
            "Rebase desde esta ventana",
            self.fuente
        )

    def test_conserva_sin_fetch_automatico_pull_merge_rebase(self):
        self.assertIn(
            "No hace Fetch automático, Pull, Merge",
            self.fuente
        )

    def test_el_layout_de_007_sigue_protegido(self):
        self.assertIn("580x560", self.fuente)
        self.assertIn("480", self.fuente)
        self.assertIn("380", self.fuente)
        self.assertIn("rowconfigure", self.fuente)


if __name__ == "__main__":
    unittest.main()
