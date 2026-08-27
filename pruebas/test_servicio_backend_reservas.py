"""
Pruebas del servicio del backend local de reservas de Modo
Equipo Oracle V1 (Bloque C).

Estas pruebas no tocan %APPDATA% real, no usan red, no tocan
el repositorio Oracle productivo y no modifican la
configuracion Git global ni system.

Usan TemporaryDirectory para la ruta base inyectada y ejecutan
Git real solo sobre el bare local temporal creado en cada caso.

Cobertura:

1.  APPDATA ausente -> error controlado.
2.  ruta base inyectada -> no usa APPDATA real.
3.  UUID4 canonico valido.
4.  UUID invalido / no-v4 / no canonico -> error.
5.  URL vacia -> error.
6.  URL con credenciales -> error.
7.  URL SSH / scp-like -> error.
8.  URL query / fragment -> error.
9.  URL con whitespace interno -> error.
10. URL con puerto invalido -> error.
11. URL https valida -> aceptada.
12. creacion de padres.
13. creacion de backend.git bare.
14. rev-parse --is-bare-repository == true.
15. origin configurado con URL exacta.
16. refspec exacto configurado.
17. ejecucion repetida idempotente.
18. actualizacion local de URL de origin sin red.
19. refspec no duplicado tras segunda ejecucion.
20. ruta backend.git existente como archivo -> error sin borrar.
21. directorio existente no Git -> error sin borrar.
22. repo Git no-bare en esa ruta -> error sin destruir.
23. git init --bare fallando -> error controlado.
24. timeout subprocess -> error controlado.
25. OSError subprocess -> error controlado.
26. Path OSError / ValueError -> error controlado.
27. ninguna llamada Fetch / Pull / Push.
28. ninguna modificacion de Git global / system.
29. ninguna escritura fuera de la ruta temporal inyectada.
30. H1-A: project path redirigido fuera de base -> error sin
    escrituras sobre el destino externo.
31. H1-B: backend.git redirigido fuera de base -> error sin
    cambios en origin/refspec del bare externo.
32. H2: fallo ambiguo de consulta de remotes -> error sin
    remote add/set-url/config posteriores.
33. H3: pushurl preexistente distinto -> normalizado a la URL
    esperada (get-url y get-url --push coinciden).
34. H3-B: idempotencia con destino de Push normalizado.
35. H3-C: pushurls heredados multiples -> sin exito si el
    destino efectivo de Push no es una unica URL.
36. H3-D: urls heredadas multiples sin pushurl -> exito con
    destino de Push unico (pushurl local desacopla).
37. H3-E: duplicados efectivos iguales -> exactamente una URL
    tras exito; duplicado global igual -> bloqueo controlado.
38. H3-F: idempotencia multi-scope (destino unico y refspec
    exacto).
"""

import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from servicio_backend_reservas import (
    REFSPEC_RESERVAS_V1,
    ResultadoBackendReservas,
    ServicioBackendReservas,
)


def _uuid4():
    """Genera un UUID v4 canonico en minusculas con guiones."""

    return str(uuid.uuid4())


def _url_valida():
    """URL https valida de backend de reservas."""

    return "https://git.example.com/reservas/backend.git"


def _otra_url_valida():
    """Segunda URL https valida para pruebas de actualizacion."""

    return "https://git.example.com:8443/reservas/otro.git"


class TestServicioBackendReservas(unittest.TestCase):
    """
    Pruebas de ServicioBackendReservas.
    """

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta_base = Path(self.temporal.name) / "reservas"
        self.project_uuid = _uuid4()
        self.url = _url_valida()
        self.servicio = ServicioBackendReservas(
            ruta_base=str(self.ruta_base)
        )

    def tearDown(self):
        self.temporal.cleanup()

    # -- Helpers --------------------------------------------------

    def _ruta_backend(self):
        """Ruta esperada del backend para el project_uuid de setUp."""

        return self.ruta_base / self.project_uuid / "backend.git"

    def _git(self, *argumentos):
        """Ejecuta git sobre el backend temporal y devuelve stdout."""

        ruta = str(self._ruta_backend())
        resultado = subprocess.run(
            ["git", "-C", ruta] + list(argumentos),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False
        )
        if resultado.returncode != 0:
            raise RuntimeError(
                f"git {argumentos} fallo: {resultado.stderr}"
            )
        return resultado.stdout.rstrip("\r\n")

    def _preparar(self, url=None, project_uuid=None):
        """Prepara el backend con los valores por defecto de setUp."""

        return self.servicio.preparar_backend_local(
            project_uuid if project_uuid is not None else self.project_uuid,
            url if url is not None else self.url
        )

    def _git_en(self, ruta, *argumentos):
        """Ejecuta git en una ruta arbitraria y devuelve stdout."""

        resultado = subprocess.run(
            ["git", "-C", str(ruta)] + list(argumentos),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False
        )
        if resultado.returncode != 0:
            raise RuntimeError(
                f"git {argumentos} en {ruta} fallo: {resultado.stderr}"
            )
        return resultado.stdout.rstrip("\r\n")

    def _git_en_opcional(self, ruta, *argumentos):
        """
        Ejecuta git en una ruta arbitraria y devuelve stdout,
        o cadena vacia si el comando falla.
        """

        resultado = subprocess.run(
            ["git", "-C", str(ruta)] + list(argumentos),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False
        )
        if resultado.returncode != 0:
            return ""
        return resultado.stdout.rstrip("\r\n")

    def _crear_enlace_directorio(self, enlace, destino):
        """
        Crea un enlace de directorio (junction o symlink) de
        forma determinista.

        Devuelve True si el enlace quedo creado y False si la
        plataforma no lo permite.
        """

        try:
            subprocess.run(
                ["cmd", "/c", "mklink", "/J",
                 str(enlace), str(destino)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                shell=False
            )
            if Path(enlace).exists():
                return True
        except (OSError, subprocess.SubprocessError):
            pass

        try:
            os.symlink(
                str(destino), str(enlace),
                target_is_directory=True
            )
            return True
        except (OSError, NotImplementedError):
            return False

    def _config_global_temporal(self, contenido):
        """
        Crea un archivo de configuracion Git global
        TEMPORAL y devuelve su ruta. Nunca toca la
        configuracion global/system real.
        """

        archivo = (
            Path(self.temporal.name) / "config_global_temporal"
        )
        archivo.write_text(contenido, encoding="utf-8")
        return archivo

    def _aislar_git_scopes(self, archivo_global):
        """
        Devuelve el entorno que aísla los scopes Git para
        una prueba: GIT_CONFIG_GLOBAL apunta al archivo
        temporal y GIT_CONFIG_NOSYSTEM desactiva el scope
        system. No modifica la configuracion real.
        """

        return {
            "GIT_CONFIG_GLOBAL": str(archivo_global),
            "GIT_CONFIG_NOSYSTEM": "1",
        }

    # -- 1. APPDATA ausente --------------------------------------

    def test_appdata_ausente_devuelve_error(self):
        entorno = dict(os.environ)
        entorno.pop("APPDATA", None)
        with mock.patch.dict(os.environ, entorno, clear=True):
            servicio = ServicioBackendReservas()
            self.assertIsNone(servicio.ruta_base)
            resultado = servicio.preparar_backend_local(
                self.project_uuid, self.url
            )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")
        self.assertIn("APPDATA", resultado.mensaje)

    # -- 2. ruta base inyectada no usa APPDATA --------------------

    def test_ruta_base_inyectada_no_usa_appdata(self):
        appdata_falso = self.ruta_base.parent / "appdata_falso"
        appdata_falso.mkdir(parents=True, exist_ok=True)

        entorno = dict(os.environ)
        entorno["APPDATA"] = str(appdata_falso)
        with mock.patch.dict(os.environ, entorno, clear=True):
            servicio = ServicioBackendReservas(
                ruta_base=str(self.ruta_base)
            )
            resultado = servicio.preparar_backend_local(
                self.project_uuid, self.url
            )

        self.assertTrue(resultado.exitoso, msg=resultado.error)
        self.assertTrue(self._ruta_backend().is_dir())
        self.assertTrue(resultado.ruta_backend.startswith(
            str(self._ruta_backend().resolve())
        ))
        self.assertFalse(
            str(self._ruta_backend()).startswith(str(appdata_falso))
        )

    # -- 3. UUID4 canonico valido --------------------------------

    def test_uuid4_canonico_valido(self):
        resultado = self._preparar()
        self.assertTrue(resultado.exitoso, msg=resultado.error)
        self.assertTrue(self._ruta_backend().is_dir())

    def test_uuid4_otro_valido_distinto(self):
        otro_uuid = _uuid4()
        self.assertNotEqual(otro_uuid, self.project_uuid)
        resultado = self.servicio.preparar_backend_local(
            otro_uuid, self.url
        )
        self.assertTrue(resultado.exitoso, msg=resultado.error)
        self.assertTrue(
            (self.ruta_base / otro_uuid / "backend.git").is_dir()
        )

    # -- 4. UUID invalido / no-v4 / no canonico -------------------

    def test_uuid_vacio_error(self):
        resultado = self.servicio.preparar_backend_local("", self.url)
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_uuid_no_string_error(self):
        resultado = self.servicio.preparar_backend_local(12345, self.url)
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_uuid_no_v4_error(self):
        uuid_v1 = "12345678-1234-1234-8123-123456789abc"
        resultado = self.servicio.preparar_backend_local(
            uuid_v1, self.url
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_uuid_no_canonico_mayusculas_error(self):
        uuid_mayus = str(uuid.uuid4()).upper()
        resultado = self.servicio.preparar_backend_local(
            uuid_mayus, self.url
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_uuid_no_canonico_sin_guiones_error(self):
        uuid_sin_guiones = str(uuid.uuid4()).replace("-", "")
        resultado = self.servicio.preparar_backend_local(
            uuid_sin_guiones, self.url
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_uuid_con_caracteres_de_ruta_error(self):
        resultado = self.servicio.preparar_backend_local(
            "../escape", self.url
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 5. URL vacia ---------------------------------------------

    def test_url_vacia_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid, ""
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_url_solo_espacios_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid, "   "
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 6. URL con credenciales ----------------------------------

    def test_url_con_credenciales_usuario_password_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "https://usuario:password@git.example.com/reservas.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_url_con_credenciales_token_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "https://token@git.example.com/reservas.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 7. URL SSH / scp-like ------------------------------------

    def test_url_ssh_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "ssh://git@example.com/reservas.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_url_git_ssh_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "git+ssh://git@example.com/reservas.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_url_scp_like_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "git@example.com:reservas.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_url_sin_esquema_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "git.example.com/reservas.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 8. URL query / fragment ----------------------------------

    def test_url_con_query_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "https://git.example.com/reservas.git?rama=main"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_url_con_fragment_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "https://git.example.com/reservas.git#seccion"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 9. URL con whitespace interno ----------------------------

    def test_url_con_espacio_interno_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "https://git.example.com/res ervas/backend.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_url_con_tab_interno_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "https://git.example.com/\treservas/backend.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 10. URL con puerto invalido ------------------------------

    def test_url_puerto_no_numerico_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "https://git.example.com:abc/reservas/backend.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    def test_url_puerto_fuera_de_rango_error(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "https://git.example.com:99999/reservas/backend.git"
        )
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 11. URL https valida -------------------------------------

    def test_url_https_valida_aceptada(self):
        resultado = self._preparar()
        self.assertTrue(resultado.exitoso, msg=resultado.error)
        self.assertTrue(self._ruta_backend().is_dir())

    def test_url_http_valida_aceptada(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "http://git.example.com/reservas/backend.git"
        )
        self.assertTrue(resultado.exitoso, msg=resultado.error)

    def test_url_https_con_puerto_valido_aceptada(self):
        resultado = self.servicio.preparar_backend_local(
            self.project_uuid,
            "https://git.example.com:8443/reservas/backend.git"
        )
        self.assertTrue(resultado.exitoso, msg=resultado.error)

    # -- 12. creacion de padres -----------------------------------

    def test_creacion_de_padres(self):
        self.assertFalse(self.ruta_base.exists())
        resultado = self._preparar()
        self.assertTrue(resultado.exitoso, msg=resultado.error)
        self.assertTrue(self.ruta_base.is_dir())
        self.assertTrue((self.ruta_base / self.project_uuid).is_dir())

    # -- 13. creacion de backend.git bare -------------------------

    def test_creacion_backend_git_bare(self):
        resultado = self._preparar()
        self.assertTrue(resultado.exitoso, msg=resultado.error)
        ruta = self._ruta_backend()
        self.assertTrue(ruta.is_dir())
        self.assertTrue((ruta / "HEAD").exists())
        self.assertTrue((ruta / "objects").is_dir())
        self.assertTrue((ruta / "refs").is_dir())
        self.assertTrue((ruta / "config").exists())

    # -- 14. rev-parse --is-bare-repository == true ---------------

    def test_es_repositorio_bare(self):
        self._preparar()
        salida = self._git("rev-parse", "--is-bare-repository")
        self.assertEqual(salida, "true")

    # -- 15. origin configurado con URL exacta --------------------

    def test_origin_configurado_url_exacta(self):
        self._preparar()
        url_git = self._git("remote", "get-url", "origin")
        self.assertEqual(url_git, self.url)

    # -- 16. refspec exacto configurado ---------------------------

    def test_refspec_exacto_configurado(self):
        self._preparar()
        refspec_git = self._git("config", "--get", "remote.origin.fetch")
        self.assertEqual(refspec_git, REFSPEC_RESERVAS_V1)

    # -- 17. ejecucion repetida idempotente -----------------------

    def test_ejecucion_repetida_idempotente(self):
        resultado1 = self._preparar()
        self.assertTrue(resultado1.exitoso, msg=resultado1.error)
        resultado2 = self._preparar()
        self.assertTrue(resultado2.exitoso, msg=resultado2.error)
        self.assertEqual(resultado1.ruta_backend, resultado2.ruta_backend)

        url_git = self._git("remote", "get-url", "origin")
        self.assertEqual(url_git, self.url)
        refspec_git = self._git("config", "--get", "remote.origin.fetch")
        self.assertEqual(refspec_git, REFSPEC_RESERVAS_V1)
        es_bare = self._git("rev-parse", "--is-bare-repository")
        self.assertEqual(es_bare, "true")

    # -- 18. actualizacion local de URL de origin -----------------

    def test_actualizacion_url_origin_sin_red(self):
        self._preparar()
        url_inicial = self._git("remote", "get-url", "origin")
        self.assertEqual(url_inicial, self.url)

        nueva_url = _otra_url_valida()
        resultado2 = self.servicio.preparar_backend_local(
            self.project_uuid, nueva_url
        )
        self.assertTrue(resultado2.exitoso, msg=resultado2.error)

        url_final = self._git("remote", "get-url", "origin")
        self.assertEqual(url_final, nueva_url)
        self.assertNotEqual(url_final, url_inicial)

    # -- 19. refspec no duplicado tras segunda ejecucion ----------

    def test_refspec_no_duplicado(self):
        self._preparar()
        self._preparar()
        salida = self._git("config", "--get-all", "remote.origin.fetch")
        lineas = [l for l in salida.splitlines() if l.strip()]
        self.assertEqual(len(lineas), 1)
        self.assertEqual(lineas[0], REFSPEC_RESERVAS_V1)

    # -- 20. backend.git como archivo -> error sin borrar ----------

    def test_backend_git_archivo_error_sin_borrar(self):
        ruta = self._ruta_backend()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("no soy un repo")

        resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertTrue(ruta.is_file())
        self.assertEqual(ruta.read_text(), "no soy un repo")

    # -- 21. directorio existente no Git -> error sin borrar ------

    def test_directorio_no_git_error_sin_borrar(self):
        ruta = self._ruta_backend()
        ruta.mkdir(parents=True, exist_ok=True)
        (ruta / "archivo.txt").write_text("contenido")

        resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertTrue(ruta.is_dir())
        self.assertTrue((ruta / "archivo.txt").exists())

    # -- 22. repo Git no-bare -> error sin destruir ---------------

    def test_repo_no_bare_error_sin_destruir(self):
        ruta = self._ruta_backend()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "init", str(ruta)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
            check=True
        )

        resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertTrue(ruta.is_dir())
        self.assertTrue((ruta / ".git").is_dir())

        es_bare = subprocess.run(
            ["git", "-C", str(ruta),
             "rev-parse", "--is-bare-repository"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False
        )
        self.assertEqual(es_bare.stdout.strip(), "false")

    # -- 23. git init --bare fallando -> error controlado ----------

    def test_git_init_bare_fallando_error_controlado(self):
        resultado_falso = subprocess.CompletedProcess(
            args=["git", "init", "--bare"],
            returncode=1,
            stdout="",
            stderr="init fallido simulado"
        )
        with mock.patch(
            "servicio_backend_reservas.subprocess.run",
            return_value=resultado_falso
        ):
            resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 24. timeout subprocess -> error controlado ---------------

    def test_timeout_subprocess_error_controlado(self):
        with mock.patch(
            "servicio_backend_reservas.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                cmd=["git"], timeout=1
            )
        ):
            resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 25. OSError subprocess -> error controlado ---------------

    def test_oserror_subprocess_error_controlado(self):
        with mock.patch(
            "servicio_backend_reservas.subprocess.run",
            side_effect=OSError("error de E/S simulado")
        ):
            resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 26. Path OSError / ValueError -> error controlado --------

    def test_path_oserror_en_mkdir_error_controlado(self):
        ruta_base = self.ruta_base
        ruta_base.mkdir(parents=True, exist_ok=True)
        (ruta_base / self.project_uuid).write_text("soy un archivo")

        resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertTrue(
            (ruta_base / self.project_uuid).is_file()
        )

    def test_path_value_error_error_controlado(self):
        with mock.patch.object(
            Path,
            "mkdir",
            side_effect=ValueError("ruta invalida simulada")
        ):
            resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")

    # -- 27. ninguna llamada Fetch / Pull / Push ------------------

    def test_ninguna_llamada_fetch_pull_push(self):
        """
        Verifica que el servicio no ejecute los subcomandos de red
        fetch, pull ni push.

        Se examinan tokens exactos de cada comando, no substrings:
        la clave de configuracion `remote.origin.fetch` contiene
        la palabra `fetch` pero NO es un subcomando de Git y esta
        explicitamente permitida por la seccion 11 del prompt.
        """

        subcomandos_prohibidos = {"fetch", "pull", "push"}
        grabador = mock.MagicMock(wraps=subprocess.run)
        with mock.patch(
            "servicio_backend_reservas.subprocess.run",
            new=grabador
        ):
            resultado = self._preparar()
            self.assertTrue(resultado.exitoso, msg=resultado.error)

        self.assertGreater(grabador.call_count, 0)

        for llamada in grabador.call_args_list:
            argumentos = llamada.args
            if not argumentos:
                continue
            comando = argumentos[0]
            if not isinstance(comando, (list, tuple)):
                continue
            tokens_minuscula = [
                str(parte).lower() for parte in comando
            ]
            for i, token in enumerate(tokens_minuscula):
                if i == 0:
                    continue
                self.assertNotIn(
                    token, subcomandos_prohibidos,
                    msg=(
                        f"Se detecto un subcomando de red prohibido "
                        f"({token!r}) en el comando: {comando!r}"
                    )
                )

    # -- 28. ninguna modificacion de Git global / system ----------

    def test_ninguna_modificacion_git_global_system(self):
        grabador = mock.MagicMock(wraps=subprocess.run)
        with mock.patch(
            "servicio_backend_reservas.subprocess.run",
            new=grabador
        ):
            resultado = self._preparar()
            self.assertTrue(resultado.exitoso, msg=resultado.error)

        for llamada in grabador.call_args_list:
            argumentos = llamada.args
            if not argumentos:
                continue
            comando = argumentos[0]
            if isinstance(comando, (list, tuple)):
                texto = " ".join(str(a) for a in comando)
            else:
                texto = str(comando)
            texto_minuscula = texto.lower()
            self.assertNotIn("--global", texto_minuscula)
            self.assertNotIn("--system", texto_minuscula)

    # -- 29. ninguna escritura fuera de la ruta inyectada ---------

    def test_ninguna_escritura_fuera_de_ruta_inyectada(self):
        appdata_falso = self.ruta_base.parent / "appdata_aislado"
        appdata_falso.mkdir(parents=True, exist_ok=True)

        entorno = dict(os.environ)
        entorno["APPDATA"] = str(appdata_falso)
        with mock.patch.dict(os.environ, entorno, clear=True):
            servicio = ServicioBackendReservas(
                ruta_base=str(self.ruta_base)
            )
            resultado = servicio.preparar_backend_local(
                self.project_uuid, self.url
            )
            self.assertTrue(resultado.exitoso, msg=resultado.error)

        self.assertTrue(self._ruta_backend().is_dir())

        gestorgit_en_appdata = appdata_falso / "GestorGit"
        self.assertFalse(
            gestorgit_en_appdata.exists(),
            msg=(
                "No debio crearse nada bajo APPDATA real. "
                f"Contenido de {appdata_falso}: "
                f"{list(appdata_falso.iterdir())}"
            )
        )

        ruta_resuelta = Path(resultado.ruta_backend).resolve()
        ruta_base_resuelta = self.ruta_base.resolve()
        self.assertTrue(
            str(ruta_resuelta).startswith(str(ruta_base_resuelta)),
            msg=(
                f"La ruta del backend ({ruta_resuelta}) no esta "
                f"dentro de la ruta base inyectada "
                f"({ruta_base_resuelta})."
            )
        )

        contenidos = list(self.ruta_base.iterdir())
        self.assertEqual(
            len(contenidos), 1,
            msg=(
                f"Solo debe existir el directorio del proyecto bajo "
                f"la ruta base. Contenido: {contenidos}"
            )
        )
        self.assertEqual(contenidos[0].name, self.project_uuid)


    # -- 30. H1-A: project path redirigido fuera de base ---------

    def test_h1a_proyecto_redirigido_fuera_de_base(self):
        """
        <base>/<project_uuid> es un junction a un directorio
        externo con un bare valido dentro. La preparacion debe
        fallar sin escribir sobre el destino externo.
        """

        base = self.ruta_base
        fuera = base.parent / "fuera_h1a"
        bare_fuera = fuera / "backend.git"
        bare_fuera.mkdir(parents=True)
        self._git_en(bare_fuera, "init", "--bare")

        config_previo = (bare_fuera / "config").read_bytes()

        base.mkdir(parents=True)
        enlace = base / self.project_uuid
        if not self._crear_enlace_directorio(enlace, fuera):
            self.skipTest(
                "La plataforma no permite crear enlaces de "
                "directorio (junction/symlink)."
            )

        resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")
        self.assertIn("fuera de la ruta base", resultado.mensaje)

        config_posterior = (bare_fuera / "config").read_bytes()
        self.assertEqual(
            config_previo, config_posterior,
            msg="El bare externo no debe modificarse."
        )
        self.assertEqual(
            self._git_en_opcional(
                bare_fuera, "remote", "get-url", "origin"
            ),
            "",
            msg="No debe existir origin en el bare externo."
        )

    def test_h1a_resolucion_escape_mock_determinista(self):
        """
        Fallback deterministico sin enlaces reales: simula que
        la resolucion de la ruta del proyecto escapa de la base.
        """

        base_real = self.ruta_base.resolve()
        ruta_fuera = (
            self.ruta_base.parent / "fuera_mock" / self.project_uuid
        )

        def _resolve_falso(ruta, *args, **kwargs):
            if ruta == self.ruta_base:
                return base_real
            return ruta_fuera

        with mock.patch.object(Path, "resolve", _resolve_falso):
            resultado = self._preparar()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")
        self.assertIn("fuera de la ruta base", resultado.mensaje)

    # -- 31. H1-B: backend.git redirigido fuera de base ---------

    def test_h1b_backend_git_redirigido_fuera_de_base(self):
        """
        <base>/<project_uuid>/backend.git es un junction a un
        bare externo. La preparacion debe fallar sin modificar
        origin/refspec del bare externo.
        """

        base = self.ruta_base
        fuera = base.parent / "fuera_h1b"
        bare_fuera = fuera / "backend.git"
        bare_fuera.mkdir(parents=True)
        self._git_en(bare_fuera, "init", "--bare")
        self._git_en(
            bare_fuera, "remote", "add", "origin",
            "https://old.example/externo.git"
        )
        config_previo = (bare_fuera / "config").read_bytes()

        (base / self.project_uuid).mkdir(parents=True)
        enlace = base / self.project_uuid / "backend.git"
        if not self._crear_enlace_directorio(enlace, bare_fuera):
            self.skipTest(
                "La plataforma no permite crear enlaces de "
                "directorio (junction/symlink)."
            )

        resultado = self._preparar()
        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.ruta_backend, "")
        self.assertIn("fuera de la ruta base", resultado.mensaje)

        config_posterior = (bare_fuera / "config").read_bytes()
        self.assertEqual(
            config_previo, config_posterior,
            msg="El bare externo no debe modificarse."
        )
        self.assertEqual(
            self._git_en_opcional(
                bare_fuera, "remote", "get-url", "origin"
            ),
            "https://old.example/externo.git",
            msg="El origin del bare externo no debe cambiar."
        )

    # -- 32. H2: fallo ambiguo de consulta de remotes ----------

    def test_h2_fallo_consulta_remotes_no_configura_origin(self):
        """
        Si la consulta usada para decidir si origin existe falla
        (timeout/OSError), la preparacion debe fallar sin
        ejecutar remote add, remote set-url ni git config
        posteriores.
        """

        resultado = self._preparar()
        self.assertTrue(resultado.exitoso, msg=resultado.error)

        grabadas = []
        metodo_real = ServicioBackendReservas._ejecutar_git

        def _ejecutar_git_falso(
            instancia, argumentos, tiempo_maximo=None
        ):
            grabadas.append(list(argumentos))
            if argumentos[2] == "remote" and len(argumentos) == 3:
                return (
                    False,
                    "",
                    "timeout simulado al consultar remotes",
                    -1
                )
            return metodo_real(
                instancia, argumentos, tiempo_maximo
            )

        with mock.patch.object(
            ServicioBackendReservas,
            "_ejecutar_git",
            _ejecutar_git_falso
        ):
            resultado2 = self.servicio.preparar_backend_local(
                self.project_uuid, self.url
            )

        self.assertFalse(resultado2.exitoso)
        self.assertEqual(resultado2.ruta_backend, "")

        for comando in grabadas:
            if comando[2] == "remote" and len(comando) > 3:
                self.fail(
                    "Se ejecuto una escritura de remote tras un "
                    f"fallo ambiguo: {comando}"
                )
            if comando[2] == "config":
                self.fail(
                    "Se ejecuto git config tras un fallo ambiguo "
                    f"de consulta: {comando}"
                )

    # -- 33. H3: pushurl preexistente distinto -----------------

    def test_h3_pushurl_preexistente_distinto_normalizado(self):
        """
        Un pushurl preexistente distinto no debe desviar el
        destino efectivo de Push: tras preparar, tanto
        `remote get-url origin` como `remote get-url --push
        origin` deben ser la URL esperada.
        """

        ruta = self._ruta_backend()
        ruta.parent.mkdir(parents=True)
        self._git_en(ruta.parent, "init", "--bare", ruta.name)
        self._git_en(
            ruta, "remote", "add", "origin",
            "https://old.example/reservas.git"
        )
        self._git_en(
            ruta, "config", "remote.origin.pushurl",
            "https://wrong.example/otro.git"
        )

        resultado = self._preparar()
        self.assertTrue(resultado.exitoso, msg=resultado.error)

        url_origin = self._git("remote", "get-url", "origin")
        url_push = self._git(
            "remote", "get-url", "--push", "origin"
        )
        self.assertEqual(url_origin, self.url)
        self.assertEqual(url_push, self.url)

        pushurls = [
            linea
            for linea in self._git(
                "config", "--get-all", "remote.origin.pushurl"
            ).splitlines()
            if linea.strip()
        ]
        self.assertEqual(pushurls, [self.url])

    # -- 34. H3-B: idempotencia con destino de Push normalizado -

    def test_h3b_idempotencia_destino_push_normalizado(self):
        resultado1 = self._preparar()
        self.assertTrue(resultado1.exitoso, msg=resultado1.error)
        resultado2 = self._preparar()
        self.assertTrue(resultado2.exitoso, msg=resultado2.error)

        self.assertEqual(
            resultado1.ruta_backend, resultado2.ruta_backend
        )
        self.assertEqual(
            self._git("remote", "get-url", "origin"), self.url
        )
        self.assertEqual(
            self._git("remote", "get-url", "--push", "origin"),
            self.url
        )

        refspecs = [
            linea
            for linea in self._git(
                "config", "--get-all", "remote.origin.fetch"
            ).splitlines()
            if linea.strip()
        ]
        self.assertEqual(refspecs, [REFSPEC_RESERVAS_V1])

        pushurls = [
            linea
            for linea in self._git_en_opcional(
                self._ruta_backend(),
                "config", "--get-all", "remote.origin.pushurl"
            ).splitlines()
            if linea.strip()
        ]
        self.assertLessEqual(len(pushurls), 1)
        if pushurls:
            self.assertEqual(pushurls, [self.url])

    # -- 35. H3-C: pushurls heredados multiples -----------

    def test_h3c_pushurls_heredados_multiples_sin_exito(self):
        """
        Configuracion global TEMPORAL con dos pushurl (la
        primera la URL esperada, la segunda no autorizada).
        La preparacion NO puede devolver exito mientras el
        destino efectivo de Push tenga mas de una URL; el
        archivo global temporal no debe modificarse.
        """

        ruta = self._ruta_backend()
        ruta.parent.mkdir(parents=True)
        self._git_en(ruta.parent, "init", "--bare", ruta.name)
        self._git_en(ruta, "remote", "add", "origin", self.url)

        global_temporal = self._config_global_temporal(
            "[remote \"origin\"]\n"
            f"    pushurl = {self.url}\n"
            "    pushurl = https://evil.example/otro.git\n"
        )
        bytes_previos = global_temporal.read_bytes()

        with mock.patch.dict(
            os.environ, self._aislar_git_scopes(global_temporal)
        ):
            resultado = self._preparar()
            self.assertFalse(resultado.exitoso)
            self.assertIn("Push", resultado.mensaje)
            destinos = [
                linea
                for linea in self._git(
                    "remote", "get-url", "--push", "--all",
                    "origin"
                ).splitlines()
                if linea.strip()
            ]

        self.assertGreater(len(destinos), 1)
        self.assertEqual(
            global_temporal.read_bytes(), bytes_previos,
            msg="El archivo global temporal no debe modificarse."
        )

    # -- 36. H3-D: urls heredadas multiples sin pushurl ----

    def test_h3d_urls_heredadas_multiples_sin_pushurl(self):
        """
        Configuracion global TEMPORAL con multiples
        remote.origin.url y sin pushurl. El pushurl local
        exacto debe desacoplar el Push de esa multiplicidad:
        tras exito, `get-url --push --all origin` debe ser
        exactamente [URL esperada].
        """

        ruta = self._ruta_backend()
        ruta.parent.mkdir(parents=True)
        self._git_en(ruta.parent, "init", "--bare", ruta.name)
        self._git_en(ruta, "remote", "add", "origin", self.url)

        global_temporal = self._config_global_temporal(
            "[remote \"origin\"]\n"
            f"    url = {self.url}\n"
            "    url = https://evil.example/otro.git\n"
        )

        with mock.patch.dict(
            os.environ, self._aislar_git_scopes(global_temporal)
        ):
            resultado = self._preparar()
            self.assertTrue(resultado.exitoso, msg=resultado.error)
            destinos = [
                linea
                for linea in self._git(
                    "remote", "get-url", "--push", "--all",
                    "origin"
                ).splitlines()
                if linea.strip()
            ]

        self.assertEqual(destinos, [self.url])

    # -- 37. H3-E: duplicados efectivos iguales ------------

    def test_h3e_duplicados_efectivos_iguales(self):
        """
        Duplicados locales de pushurl iguales a la URL
        esperada: la preparacion debe colapsarlos y dejar
        exactamente un destino efectivo (no aceptar multiples
        solo porque coinciden). Un duplicado heredado IGUAL
        en scope global no puede declararse exito.
        """

        ruta = self._ruta_backend()
        ruta.parent.mkdir(parents=True)
        self._git_en(ruta.parent, "init", "--bare", ruta.name)
        self._git_en(ruta, "remote", "add", "origin", self.url)
        self._git_en(
            ruta, "config", "--add",
            "remote.origin.pushurl", self.url
        )
        self._git_en(
            ruta, "config", "--add",
            "remote.origin.pushurl", self.url
        )

        resultado = self._preparar()
        self.assertTrue(resultado.exitoso, msg=resultado.error)

        destinos = [
            linea
            for linea in self._git(
                "remote", "get-url", "--push", "--all",
                "origin"
            ).splitlines()
            if linea.strip()
        ]
        self.assertEqual(destinos, [self.url])

        # Duplicado heredado IGUAL en scope global: debe
        # bloquearse (mas de un destino efectivo).
        otro_uuid = _uuid4()
        ruta2 = self.ruta_base / otro_uuid / "backend.git"
        ruta2.parent.mkdir(parents=True)
        self._git_en(ruta2.parent, "init", "--bare", ruta2.name)
        self._git_en(ruta2, "remote", "add", "origin", self.url)

        global_temporal = self._config_global_temporal(
            "[remote \"origin\"]\n"
            f"    pushurl = {self.url}\n"
        )

        with mock.patch.dict(
            os.environ, self._aislar_git_scopes(global_temporal)
        ):
            resultado2 = self.servicio.preparar_backend_local(
                otro_uuid, self.url
            )
            self.assertFalse(resultado2.exitoso)
            self.assertIn("Push", resultado2.mensaje)

    # -- 38. H3-F: idempotencia multi-scope ----------------

    def test_h3f_idempotencia_multi_scope(self):
        """
        Ejecutar dos veces con configuracion temporal
        compatible: destino efectivo de Push unico y estable,
        refspec exacto unico, sin deriva.
        """

        ruta = self._ruta_backend()
        ruta.parent.mkdir(parents=True)
        self._git_en(ruta.parent, "init", "--bare", ruta.name)
        self._git_en(ruta, "remote", "add", "origin", self.url)

        global_temporal = self._config_global_temporal(
            "[remote \"origin\"]\n"
            f"    url = {self.url}\n"
        )

        with mock.patch.dict(
            os.environ, self._aislar_git_scopes(global_temporal)
        ):
            resultado1 = self._preparar()
            self.assertTrue(resultado1.exitoso, msg=resultado1.error)
            destinos1 = [
                linea
                for linea in self._git(
                    "remote", "get-url", "--push", "--all",
                    "origin"
                ).splitlines()
                if linea.strip()
            ]
            refspecs1 = [
                linea
                for linea in self._git(
                    "config", "--get-all", "remote.origin.fetch"
                ).splitlines()
                if linea.strip()
            ]

            resultado2 = self._preparar()
            self.assertTrue(resultado2.exitoso, msg=resultado2.error)
            destinos2 = [
                linea
                for linea in self._git(
                    "remote", "get-url", "--push", "--all",
                    "origin"
                ).splitlines()
                if linea.strip()
            ]
            refspecs2 = [
                linea
                for linea in self._git(
                    "config", "--get-all", "remote.origin.fetch"
                ).splitlines()
                if linea.strip()
            ]

        self.assertEqual(destinos1, [self.url])
        self.assertEqual(destinos2, [self.url])
        self.assertEqual(refspecs1, [REFSPEC_RESERVAS_V1])
        self.assertEqual(refspecs2, [REFSPEC_RESERVAS_V1])
        self.assertEqual(
            resultado1.ruta_backend, resultado2.ruta_backend
        )


if __name__ == "__main__":
    unittest.main()
