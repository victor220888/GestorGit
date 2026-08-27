"""
Pruebas de la configuracion de Modo Equipo Oracle V1.

Cubren:

- carga de config.json con defaults V1;
- preservacion de claves desconocidas en escritura;
- validacion estricta de tipos y valores canonicos;
- validacion de backend_reservas_url;
- escritura atomica;
- no creacion de secretos.

No tocan config.json real, no usan red, no usan Git salvo
guardar_ultimo_repositorio que valida rutas con un repositorio
temporal.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modelos_configuracion import ConfiguracionModoEquipo
from servicio_configuracion import ServicioConfiguracion
from servicio_git import ServicioGit


# Valores canonicos V1 para reutilizar en las pruebas.
_TTL = 1800
_RENOVACION = 600
_MARGEN_MINIMO = 300
_FRESCURA = 60
_MARGEN_GRACIA = 600

_BACKEND_VALIDO = "https://github.com/organizacion/reservas.git"


def _config_v1_completa(**sobreescrituras):
    """Construye una ConfiguracionModoEquipo valida V1."""

    valores = {
        "modo_equipo_habilitado": False,
        "backend_reservas_url": "",
        "alias_equipo": "",
        "ttl_reservas_segundos": _TTL,
        "renovacion_reservas_segundos": _RENOVACION,
        "margen_minimo_reserva_segundos": _MARGEN_MINIMO,
        "frescura_reservas_segundos": _FRESCURA,
        "margen_gracia_vencimiento_segundos": _MARGEN_GRACIA,
    }
    valores.update(sobreescrituras)
    return ConfiguracionModoEquipo(**valores)


def _dict_v1_completo(**sobreescrituras):
    """Construye un dict de config.json con todas las claves V1."""

    datos = {
        "modo_equipo_habilitado": False,
        "backend_reservas_url": "",
        "alias_equipo": "",
        "ttl_reservas_segundos": _TTL,
        "renovacion_reservas_segundos": _RENOVACION,
        "margen_minimo_reserva_segundos": _MARGEN_MINIMO,
        "frescura_reservas_segundos": _FRESCURA,
        "margen_gracia_vencimiento_segundos": _MARGEN_GRACIA,
    }
    datos.update(sobreescrituras)
    return datos


class TestConfiguracionModoEquipo(unittest.TestCase):
    """
    Pruebas de carga, validacion y guardado de Modo Equipo.
    """

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta_temporal = Path(self.temporal.name)
        self.ruta_config = self.ruta_temporal / "config.json"
        self.servicio = ServicioConfiguracion(
            servicio_git=ServicioGit(),
            ruta_configuracion=str(self.ruta_config)
        )

    def tearDown(self):
        self.temporal.cleanup()

    def _escribir_config(self, datos):
        """Escribe config.json con un dict."""

        self.ruta_config.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_config.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _escribir_bytes(self, contenido):
        """Escribe bytes crudos en config.json."""

        self.ruta_config.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_config.write_bytes(contenido)

    def _escribir_json_crudo(self, texto):
        """Escribe texto JSON crudo (para claves duplicadas o
        JSON invalido)."""

        self.ruta_config.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_config.write_text(texto, encoding="utf-8")

    def _leer_config(self):
        """Lee config.json como dict."""

        return json.loads(
            self.ruta_config.read_text(encoding="utf-8")
        )

    def _ejecutar_git(self, *argumentos):
        """Ejecuta Git en la carpeta temporal."""

        return subprocess.run(
            ["git", *argumentos],
            cwd=self.ruta_temporal,
            check=True,
            capture_output=True,
            text=True
        )

    def _crear_repositorio_git(self, nombre="repositorio"):
        """Crea un repositorio Git vacio en la carpeta temporal."""

        ruta = self.ruta_temporal / nombre
        self._ejecutar_git(
            "init",
            "--initial-branch=master",
            str(ruta)
        )
        return ruta

    # 1. config inexistente -> defaults V1, modo deshabilitado

    def test_config_inexistente_defaults_v1(self):
        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)
        self.assertIsNotNone(resultado.configuracion)
        self.assertFalse(resultado.configuracion.modo_equipo_habilitado)
        self.assertEqual(resultado.configuracion.backend_reservas_url, "")
        self.assertEqual(resultado.configuracion.alias_equipo, "")
        self.assertEqual(resultado.configuracion.ttl_reservas_segundos, _TTL)
        self.assertEqual(
            resultado.configuracion.renovacion_reservas_segundos,
            _RENOVACION
        )
        self.assertEqual(
            resultado.configuracion.margen_minimo_reserva_segundos,
            _MARGEN_MINIMO
        )
        self.assertEqual(
            resultado.configuracion.frescura_reservas_segundos,
            _FRESCURA
        )
        self.assertEqual(
            resultado.configuracion.margen_gracia_vencimiento_segundos,
            _MARGEN_GRACIA
        )

    # 2. config legacy solo con ruta_repositorio -> defaults de equipo

    def test_config_legacy_solo_ruta_repositorio(self):
        self._escribir_config({"ruta_repositorio": "/alguna/ruta"})

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)
        self.assertFalse(resultado.configuracion.modo_equipo_habilitado)
        self.assertEqual(resultado.configuracion.backend_reservas_url, "")
        self.assertEqual(resultado.configuracion.ttl_reservas_segundos, _TTL)

    # 3. configuracion V1 completa valida

    def test_config_v1_completa_valida(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url=_BACKEND_VALIDO,
            alias_equipo="mi-equipo"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)
        self.assertTrue(resultado.configuracion.modo_equipo_habilitado)
        self.assertEqual(
            resultado.configuracion.backend_reservas_url,
            _BACKEND_VALIDO
        )
        self.assertEqual(resultado.configuracion.alias_equipo, "mi-equipo")

    # 4. modo habilitado con backend valido

    def test_modo_habilitado_backend_valido(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url=_BACKEND_VALIDO
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)

    # 5. modo habilitado y backend vacio -> error

    def test_modo_habilitado_backend_vacio_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url=""
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.configuracion)

    # 6. modo deshabilitado y backend vacio -> valido

    def test_modo_deshabilitado_backend_vacio_valido(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=False,
            backend_reservas_url=""
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)

    # 7. modo_equipo_habilitado=1 -> error

    def test_modo_habilitado_entero_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=1
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_modo_habilitado_cadena_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado="true"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 8. tiempos ausentes -> defaults

    def test_tiempos_ausentes_defaults(self):
        self._escribir_config({
            "modo_equipo_habilitado": False,
            "backend_reservas_url": "",
            "alias_equipo": ""
        })

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)
        self.assertEqual(resultado.configuracion.ttl_reservas_segundos, _TTL)
        self.assertEqual(
            resultado.configuracion.renovacion_reservas_segundos,
            _RENOVACION
        )

    # 9. cada tiempo canonico explicito -> valido

    def test_tiempos_canonicos_explicitos_validos(self):
        self._escribir_config(_dict_v1_completo(
            ttl_reservas_segundos=_TTL,
            renovacion_reservas_segundos=_RENOVACION,
            margen_minimo_reserva_segundos=_MARGEN_MINIMO,
            frescura_reservas_segundos=_FRESCURA,
            margen_gracia_vencimiento_segundos=_MARGEN_GRACIA
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)

    # 10. cada tiempo divergente -> error

    def test_ttl_divergente_error(self):
        self._escribir_config(_dict_v1_completo(
            ttl_reservas_segundos=3600
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_renovacion_divergente_error(self):
        self._escribir_config(_dict_v1_completo(
            renovacion_reservas_segundos=1200
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_margen_minimo_divergente_error(self):
        self._escribir_config(_dict_v1_completo(
            margen_minimo_reserva_segundos=600
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_frescura_divergente_error(self):
        self._escribir_config(_dict_v1_completo(
            frescura_reservas_segundos=120
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_margen_gracia_divergente_error(self):
        self._escribir_config(_dict_v1_completo(
            margen_gracia_vencimiento_segundos=1200
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 11. bool usado como tiempo -> error

    def test_tiempo_bool_error(self):
        self._escribir_config(_dict_v1_completo(
            ttl_reservas_segundos=True
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 12. alias vacio -> valido

    def test_alias_vacio_valido(self):
        self._escribir_config(_dict_v1_completo(
            alias_equipo=""
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)
        self.assertEqual(resultado.configuracion.alias_equipo, "")

    # 13. alias con espacios exteriores -> normalizacion al guardar

    def test_alias_espacios_normalizacion_al_guardar(self):
        config = _config_v1_completa(alias_equipo="  mi alias  ")

        resultado = self.servicio.guardar_configuracion_modo_equipo(config)

        self.assertTrue(resultado.exitoso)

        datos = self._leer_config()
        self.assertEqual(datos["alias_equipo"], "mi alias")

    # 14. alias con NUL/CR/LF -> error

    def test_alias_con_nul_error(self):
        self._escribir_config(_dict_v1_completo(
            alias_equipo="mi\0alias"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_alias_con_cr_error(self):
        self._escribir_config(_dict_v1_completo(
            alias_equipo="mi\ralias"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_alias_con_lf_error(self):
        self._escribir_config(_dict_v1_completo(
            alias_equipo="mi\nalias"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_alias_con_nul_al_guardar_error(self):
        config = _config_v1_completa(alias_equipo="mi\0alias")

        resultado = self.servicio.guardar_configuracion_modo_equipo(config)

        self.assertFalse(resultado.exitoso)

    # 15. backend HTTPS sin credenciales -> valido

    def test_backend_https_sin_credenciales_valido(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url=_BACKEND_VALIDO
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)

    # 16. backend con usuario:password@ -> error

    def test_backend_con_usuario_password_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url=(
                "https://usuario:password@host/repo.git"
            )
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 17. backend con token@ -> error

    def test_backend_con_token_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://token@host/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 18. backend ssh://usuario@host/... -> error

    def test_backend_ssh_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="ssh://usuario@host/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 19. backend scp-like usuario@host:ruta -> error

    def test_backend_scp_like_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="usuario@host:ruta/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 20. backend con query -> error

    def test_backend_con_query_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url=(
                "https://host/repo.git?foo=bar"
            )
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 21. backend con fragment -> error

    def test_backend_con_fragment_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://host/repo.git#seccion"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 22. backend con NUL/CR/LF -> error

    def test_backend_con_nul_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="ht\ntp://host/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_backend_con_cr_error(self):
        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="ht\rtp://host/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 23. guardar equipo preserva ruta_repositorio

    def test_guardar_equipo_preserva_ruta_repositorio(self):
        self._escribir_config({
            "ruta_repositorio": "/alguna/ruta/valida",
            "modo_equipo_habilitado": False
        })

        config = _config_v1_completa(
            modo_equipo_habilitado=True,
            backend_reservas_url=_BACKEND_VALIDO,
            alias_equipo="equipo-1"
        )

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertTrue(resultado.exitoso)

        datos = self._leer_config()
        self.assertEqual(datos["ruta_repositorio"], "/alguna/ruta/valida")
        self.assertTrue(datos["modo_equipo_habilitado"])
        self.assertEqual(datos["backend_reservas_url"], _BACKEND_VALIDO)

    # 24. guardar repositorio preserva configuracion de equipo

    def test_guardar_repositorio_preserva_config_equipo(self):
        repositorio = self._crear_repositorio_git()

        datos = _dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url=_BACKEND_VALIDO,
            alias_equipo="equipo-1"
        )
        datos["ruta_repositorio"] = str(repositorio)
        self._escribir_config(datos)

        resultado = self.servicio.guardar_ultimo_repositorio(
            str(repositorio)
        )

        self.assertTrue(resultado.exitoso)

        datos = self._leer_config()
        self.assertTrue(datos["modo_equipo_habilitado"])
        self.assertEqual(datos["backend_reservas_url"], _BACKEND_VALIDO)
        self.assertEqual(datos["alias_equipo"], "equipo-1")
        self.assertEqual(datos["ttl_reservas_segundos"], _TTL)

    # 25. guardar cualquiera preserva clave desconocida segura

    def test_guardar_equipo_preserva_clave_desconocida(self):
        self._escribir_config({
            "ruta_repositorio": "/alguna/ruta",
            "campo_futuro": {"version": 2}
        })

        config = _config_v1_completa()

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertTrue(resultado.exitoso)

        datos = self._leer_config()
        self.assertEqual(datos["campo_futuro"], {"version": 2})

    def test_guardar_repositorio_preserva_clave_desconocida(self):
        repositorio = self._crear_repositorio_git()

        self._escribir_config({
            "ruta_repositorio": str(repositorio),
            "campo_futuro": {"version": 2}
        })

        resultado = self.servicio.guardar_ultimo_repositorio(
            str(repositorio)
        )

        self.assertTrue(resultado.exitoso)

        datos = self._leer_config()
        self.assertEqual(datos["campo_futuro"], {"version": 2})

    # 26. JSON invalido existente -> guardar equipo NO sobrescribe

    def test_json_invalido_guardar_equipo_no_sobrescribe(self):
        contenido_invalido = b"{esto no es json"
        self._escribir_bytes(contenido_invalido)

        config = _config_v1_completa()
        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertFalse(resultado.exitoso)
        self.assertEqual(
            self.ruta_config.read_bytes(),
            contenido_invalido
        )

    def test_json_invalido_guardar_repositorio_no_sobrescribe(self):
        contenido_invalido = b"{esto no es json"
        self._escribir_bytes(contenido_invalido)

        resultado = self.servicio.guardar_ultimo_repositorio(
            str(self._crear_repositorio_git())
        )

        self.assertFalse(resultado.exitoso)
        self.assertEqual(
            self.ruta_config.read_bytes(),
            contenido_invalido
        )

    # 27. raiz no objeto -> error

    def test_raiz_no_objeto_error(self):
        self._escribir_json_crudo("[1, 2, 3]")

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 28. claves JSON duplicadas -> error

    def test_claves_duplicadas_error(self):
        self._escribir_json_crudo(
            '{"ttl_reservas_segundos": 1800, '
            '"ttl_reservas_segundos": 3600}'
        )

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 29. UTF-8 invalido -> error

    def test_utf8_invalido_error(self):
        self._escribir_bytes(b'{"modo_equipo_habilitado": false, \xff}')

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # 30. escritura atomica exitosa

    def test_escritura_atomica_exitosa(self):
        config = _config_v1_completa(
            modo_equipo_habilitado=True,
            backend_reservas_url=_BACKEND_VALIDO
        )

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertTrue(resultado.exitoso)
        self.assertTrue(self.ruta_config.exists())

        datos = self._leer_config()
        self.assertTrue(datos["modo_equipo_habilitado"])
        self.assertEqual(datos["backend_reservas_url"], _BACKEND_VALIDO)
        self.assertEqual(datos["ttl_reservas_segundos"], _TTL)

    # 31. fallo de escritura/reemplazo -> config anterior intacto

    def test_fallo_reemplazo_config_anterior_intacta(self):
        self._escribir_config(_dict_v1_completo(
            alias_equipo="antes"
        ))

        contenido_anterior = self.ruta_config.read_bytes()

        config = _config_v1_completa(alias_equipo="despues")

        with mock.patch(
            "servicio_configuracion.os.replace",
            side_effect=OSError("simulado")
        ):
            resultado = self.servicio.guardar_configuracion_modo_equipo(
                config
            )

        self.assertFalse(resultado.exitoso)
        self.assertEqual(
            self.ruta_config.read_bytes(),
            contenido_anterior
        )

    # 32. no se crean campos token/password/email

    def test_guardar_equipo_no_crea_secretos(self):
        config = _config_v1_completa()

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertTrue(resultado.exitoso)

        datos = self._leer_config()

        for clave in (
            "token",
            "pat",
            "password",
            "usuario",
            "remoto",
            "correo",
            "email",
            "user_name",
            "hostname"
        ):
            self.assertNotIn(clave, datos)

    def test_guardar_repositorio_no_crea_secretos(self):
        repositorio = self._crear_repositorio_git()

        resultado = self.servicio.guardar_ultimo_repositorio(
            str(repositorio)
        )

        self.assertTrue(resultado.exitoso)

        datos = self._leer_config()

        for clave in (
            "token",
            "pat",
            "password",
            "usuario",
            "remoto",
            "correo",
            "email",
            "user_name",
            "hostname"
        ):
            self.assertNotIn(clave, datos)

    # --- Casos adicionales de backend ---

    def test_backend_vacio_modo_deshabilitado_no_requerido(self):
        """Backend vacio con modo deshabilitado es valido."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=False,
            backend_reservas_url=""
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)

    def test_backend_https_punto_git_valido(self):
        """Backend HTTPS con .git es valido."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://gitlab.com/org/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)

    def test_backend_http_valido(self):
        """Backend HTTP (no HTTPS) es valido en V1."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="http://host.local/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)

    def test_backend_sin_esquema_error(self):
        """Backend sin esquema y sin @ es rechazado."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="host.local/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_backend_git_ssh_error(self):
        """Backend git+ssh:// es rechazado."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="git+ssh://host/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    # --- Casos adicionales de guardar ---

    def test_guardar_equipo_config_invalida_no_escribe(self):
        """Guardar una ConfiguracionModoEquipo con TTL divergente
        falla y no escribe."""

        self._escribir_config(_dict_v1_completo())

        config = _config_v1_completa(ttl_reservas_segundos=9999)

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertFalse(resultado.exitoso)

        # config.json no fue modificado
        datos = self._leer_config()
        self.assertEqual(datos["ttl_reservas_segundos"], _TTL)

    def test_guardar_equipo_config_modo_true_backend_vacio_error(self):
        """Guardar modo habilitado con backend vacio falla."""

        config = _config_v1_completa(
            modo_equipo_habilitado=True,
            backend_reservas_url=""
        )

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertFalse(resultado.exitoso)

    def test_guardar_equipo_alias_nul_error(self):
        """Guardar alias con NUL falla."""

        config = _config_v1_completa(alias_equipo="mi\0alias")

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertFalse(resultado.exitoso)

    def test_guardar_equipo_backend_con_credenciales_error(self):
        """Guardar backend con credenciales falla."""

        config = _config_v1_completa(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://user:pass@host/repo.git"
        )

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertFalse(resultado.exitoso)

    def test_guardar_equipo_preserva_desconocidas_y_ruta(self):
        """Guardar equipo preserva ruta_repositorio, desconocidas
        y actualiza solo las claves de Modo Equipo."""

        self._escribir_config({
            "ruta_repositorio": "/ruta/previa",
            "campo_futuro": {"version": 2},
            "otra_clave": 42
        })

        config = _config_v1_completa(
            modo_equipo_habilitado=True,
            backend_reservas_url=_BACKEND_VALIDO,
            alias_equipo="equipo"
        )

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertTrue(resultado.exitoso)

        datos = self._leer_config()
        self.assertEqual(datos["ruta_repositorio"], "/ruta/previa")
        self.assertEqual(datos["campo_futuro"], {"version": 2})
        self.assertEqual(datos["otra_clave"], 42)
        self.assertTrue(datos["modo_equipo_habilitado"])
        self.assertEqual(datos["backend_reservas_url"], _BACKEND_VALIDO)
        self.assertEqual(datos["alias_equipo"], "equipo")

    def test_cargar_equipo_alias_con_espacios_no_se_recorta(self):
        """Al cargar, alias no se recorta (solo al guardar)."""

        self._escribir_config(_dict_v1_completo(
            alias_equipo="  mi alias  "
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)
        self.assertEqual(resultado.configuracion.alias_equipo, "  mi alias  ")

    def test_cargar_equipo_backend_con_espacios_se_recorta_al_guardar(self):
        """Al guardar, backend con espacios se recorta."""

        config = _config_v1_completa(
            modo_equipo_habilitado=True,
            backend_reservas_url="  " + _BACKEND_VALIDO + "  "
        )

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertTrue(resultado.exitoso)
        self.assertEqual(
            resultado.configuracion.backend_reservas_url,
            _BACKEND_VALIDO
        )

        datos = self._leer_config()
        self.assertEqual(datos["backend_reservas_url"], _BACKEND_VALIDO)

    # --- REV1 H2: validacion sintactica estricta de backend ---

    def test_backend_puerto_no_numerico_error(self):
        """Un puerto no numerico se rechaza (urlparse no lo valida)."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://host:abc/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_backend_espacio_interno_en_host_error(self):
        """Un espacio interno dentro del host se rechaza."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://host /repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_backend_espacio_interno_en_ruta_error(self):
        """Un espacio interno dentro de la ruta se rechaza."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://host/repo git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_backend_query_vacio_error(self):
        """El delimitador de query se rechaza aunque este vacio."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://host/repo.git?"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_backend_fragment_vacio_error(self):
        """El delimitador de fragment se rechaza aunque este vacio."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://host/repo.git#"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertFalse(resultado.exitoso)

    def test_backend_puerto_numerico_valido(self):
        """Un puerto numerico valido (443) se acepta."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://host:443/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)

    def test_backend_https_simple_valido(self):
        """Una URL HTTPS normal sigue siendo valida."""

        self._escribir_config(_dict_v1_completo(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://host/repo.git"
        ))

        resultado = self.servicio.cargar_configuracion_modo_equipo()

        self.assertTrue(resultado.exitoso)

    def test_guardar_equipo_backend_puerto_no_numerico_error(self):
        """Guardar un backend con puerto no numerico falla y no
        escribe config.json."""

        self._escribir_config(_dict_v1_completo())

        config = _config_v1_completa(
            modo_equipo_habilitado=True,
            backend_reservas_url="https://host:abc/repo.git"
        )

        resultado = self.servicio.guardar_configuracion_modo_equipo(
            config
        )

        self.assertFalse(resultado.exitoso)

        datos = self._leer_config()
        self.assertEqual(datos["ttl_reservas_segundos"], _TTL)

    # --- REV1 H3: errores del sistema al inspeccionar config ---

    def test_inspeccion_config_oserror_error_controlado(self):
        """Path.exists() lanzando OSError produce un error
        controlado en cargar_configuracion_modo_equipo, sin
        propagar la excepcion."""

        with mock.patch.object(
            Path,
            "exists",
            side_effect=OSError("simulado")
        ):
            resultado = (
                self.servicio.cargar_configuracion_modo_equipo()
            )

        self.assertFalse(resultado.exitoso)
        self.assertTrue(resultado.error)

    def test_inspeccion_config_valueerror_error_controlado(self):
        """Path.exists() lanzando ValueError produce un error
        controlado en cargar_configuracion_modo_equipo, sin
        propagar la excepcion."""

        with mock.patch.object(
            Path,
            "exists",
            side_effect=ValueError("simulado")
        ):
            resultado = (
                self.servicio.cargar_configuracion_modo_equipo()
            )

        self.assertFalse(resultado.exitoso)
        self.assertTrue(resultado.error)

    # --- REV2 H1: read_text() con ValueError debe ser controlado ---

    def test_cargar_config_modo_equipo_read_text_valueerror_controlado(self):
        """Si config.json existe pero Path.read_text() lanza
        ValueError, cargar_configuracion_modo_equipo devuelve un
        error controlado sin propagar la excepcion."""

        self._escribir_config(_dict_v1_completo())

        with mock.patch.object(
            Path,
            "read_text",
            side_effect=ValueError("simulado-read")
        ):
            resultado = (
                self.servicio.cargar_configuracion_modo_equipo()
            )

        self.assertFalse(resultado.exitoso)
        self.assertTrue(resultado.error)
        self.assertIsNone(resultado.configuracion)


if __name__ == "__main__":
    unittest.main()
