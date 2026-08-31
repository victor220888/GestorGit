"""
Pruebas del ServicioManifiestoProyecto.

Utilizan repositorios Git temporales locales creados con
TemporaryDirectory. No tocan red ni el repositorio Oracle
productivo.

El manifiesto se lee desde HEAD:.gestorgit/proyecto.json,
no desde el working tree.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from servicio_git import ServicioGit
from servicio_manifiesto_proyecto import (
    ServicioManifiestoProyecto,
    RUTA_MANIFIESTO_PROYECTO,
    FORMAT_VERSION_SOPORTADO,
    _es_uuid4_canonico,
    _es_carpeta_valida,
    _es_extension_valida,
)


# UUID4 canonico usado en las pruebas.
UUID_VALIDO = "00000000-0000-4000-8000-000000000000"


class _RepoTemporal:
    """
    Helper para crear un repositorio Git temporal
    con commits y manifiestos.
    """

    def __init__(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temporal.name) / "repo"
        self.servicio_git = ServicioGit()

    def cleanup(self):
        self.temporal.cleanup()

    def _git(self, *argumentos):
        return subprocess.run(
            ["git", *argumentos],
            cwd=self.ruta,
            check=True,
            capture_output=True,
            text=True
        )

    def init(self):
        self.ruta.mkdir(parents=True, exist_ok=True)
        self._git("init", "--initial-branch=master")
        self._git("config", "user.name", "Prueba")
        self._git("config", "user.email", "prueba@example.com")

    def commit_manifiesto(self, contenido_json, nombre="manifiesto inicial"):
        """
        Crea el directorio .gestorgit, escribe proyecto.json,
        hace add y commit.
        """

        directorio = self.ruta / ".gestorgit"
        directorio.mkdir(parents=True, exist_ok=True)

        archivo = directorio / "proyecto.json"
        archivo.write_text(contenido_json, encoding="utf-8")

        self._git("add", ".")
        self._git("commit", "-m", nombre)

    def escribir_manifiesto_sin_commit(self, contenido_json):
        """
        Escribe proyecto.json en el working tree sin commit.
        Sirve para comprobar que el servicio lee HEAD y no
        el working tree.
        """

        directorio = self.ruta / ".gestorgit"
        directorio.mkdir(parents=True, exist_ok=True)

        archivo = directorio / "proyecto.json"
        archivo.write_text(contenido_json, encoding="utf-8")

    def commit_vacio(self, nombre="commit vacio"):
        """
        Crea un commit sin manifiesto.
        """

        archivo = self.ruta / "README.md"
        archivo.write_text("repo temporal\n", encoding="utf-8")

        self._git("add", "README.md")
        self._git("commit", "-m", nombre)

    def commit_manifiesto_bytes(self, contenido_bytes, nombre="manifiesto bytes"):
        """
        Crea el directorio .gestorgit, escribe proyecto.json con
        bytes crudos (no necesariamente UTF-8 valido), hace add y
        commit. Usado para probar el rechazo de manifiestos con
        bytes UTF-8 invalidos.
        """

        directorio = self.ruta / ".gestorgit"
        directorio.mkdir(parents=True, exist_ok=True)

        archivo = directorio / "proyecto.json"
        archivo.write_bytes(contenido_bytes)

        self._git("add", ".")
        self._git("commit", "-m", nombre)


def _manifiesto_valido(uuid_str=UUID_VALIDO, layout=None):
    """
    Construye un JSON de manifiesto valido.
    """

    if layout is None:
        layout = {
            "Paquetes": {
                "tipo": "PACKAGE",
                "extension": ".pls"
            }
        }

    return json.dumps(
        {
            "format_version": 1,
            "project_uuid": uuid_str,
            "oracle_layout": layout
        },
        ensure_ascii=False,
        indent=2
    )


class TestServicioManifiestoProyecto(unittest.TestCase):
    """
    Pruebas de carga y validacion del manifiesto.
    """

    def setUp(self):
        self.repo = _RepoTemporal()
        self.servicio = ServicioManifiestoProyecto(
            servicio_git=self.repo.servicio_git
        )

    def tearDown(self):
        self.repo.cleanup()

    # --- Caso 1: repo temporal con commit y manifiesto valido ---

    def test_manifiesto_valido_carga_desde_head(self):
        self.repo.init()
        self.repo.commit_manifiesto(_manifiesto_valido())

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertTrue(resultado.exitoso, resultado.mensaje)
        self.assertIsNotNone(resultado.manifiesto)
        self.assertEqual(resultado.manifiesto.format_version, 1)
        self.assertEqual(
            resultado.manifiesto.project_uuid,
            UUID_VALIDO
        )
        self.assertEqual(len(resultado.manifiesto.oracle_layout), 1)
        regla = resultado.manifiesto.oracle_layout[0]
        self.assertEqual(regla.carpeta, "Paquetes")
        self.assertEqual(regla.tipo, "PACKAGE")
        self.assertEqual(regla.extension, ".pls")

    # --- Caso 2: cargar desde HEAD ---

    def test_carga_desde_head_no_working_tree(self):
        """
        Modificar el manifiesto en working tree SIN commit y
        comprobar que el servicio sigue leyendo la version de HEAD.
        """

        self.repo.init()
        self.repo.commit_manifiesto(_manifiesto_valido())

        # Modificamos el working tree con un project_uuid distinto.
        manifiesto_modificado = _manifiesto_valido(
            uuid_str="11111111-1111-4111-8111-111111111111"
        )
        self.repo.escribir_manifiesto_sin_commit(manifiesto_modificado)

        # El servicio debe leer HEAD, no el working tree.
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertTrue(resultado.exitoso, resultado.mensaje)
        self.assertEqual(
            resultado.manifiesto.project_uuid,
            UUID_VALIDO
        )

    # --- Caso 4: repositorio invalido ---

    def test_repositorio_inexistente(self):
        ruta_inexistente = Path(self.repo.temporal.name) / "no-existe"

        resultado = self.servicio.leer_manifiesto_head(ruta_inexistente)

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)
        self.assertIn("no existe", resultado.mensaje.lower())

    def test_repositorio_no_git(self):
        carpeta = Path(self.repo.temporal.name) / "solo-carpeta"
        carpeta.mkdir()

        resultado = self.servicio.leer_manifiesto_head(carpeta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("repositorio", resultado.mensaje.lower())

    # --- Caso 5: HEAD inexistente ---

    def test_head_inexistente(self):
        self.repo.init()
        # Repo sin commits.
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("HEAD", resultado.mensaje)

    # --- Caso 6: manifiesto ausente en HEAD ---

    def test_manifiesto_ausente_en_head(self):
        self.repo.init()
        self.repo.commit_vacio()

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("no existe", resultado.mensaje.lower())

    # --- Caso 7: JSON invalido ---

    def test_json_invalido(self):
        self.repo.init()
        self.repo.commit_manifiesto("{esto no es json")

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("json", resultado.mensaje.lower())

    # --- Caso 8: claves JSON duplicadas ---

    def test_claves_duplicadas_raiz(self):
        contenido = (
            '{"format_version": 1, '
            '"format_version": 2, '
            '"project_uuid": "' + UUID_VALIDO + '", '
            '"oracle_layout": {"Paquetes": {"tipo": "PACKAGE", "extension": ".pls"}}}'
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("duplicad", resultado.mensaje.lower())

    def test_claves_duplicadas_anidadas(self):
        contenido = (
            '{"format_version": 1, '
            '"project_uuid": "' + UUID_VALIDO + '", '
            '"oracle_layout": {"Paquetes": '
            '{"tipo": "PACKAGE", "tipo": "PACKAGE", "extension": ".pls"}}}'
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("duplicad", resultado.mensaje.lower())

    # --- Caso 9: format_version ausente ---

    def test_format_version_ausente(self):
        contenido = json.dumps(
            {
                "project_uuid": UUID_VALIDO,
                "oracle_layout": {
                    "Paquetes": {
                        "tipo": "PACKAGE",
                        "extension": ".pls"
                    }
                }
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("format_version", resultado.mensaje.lower())

    # --- Caso 10: format_version=True (booleano) ---

    def test_format_version_booleano_rechazado(self):
        contenido = json.dumps(
            {
                "format_version": True,
                "project_uuid": UUID_VALIDO,
                "oracle_layout": {
                    "Paquetes": {
                        "tipo": "PACKAGE",
                        "extension": ".pls"
                    }
                }
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("format_version", resultado.mensaje.lower())
        self.assertIn("booleano", resultado.mensaje.lower())

    # --- Caso 11: version distinta de 1 ---

    def test_format_version_distinto_de_1(self):
        contenido = json.dumps(
            {
                "format_version": 2,
                "project_uuid": UUID_VALIDO,
                "oracle_layout": {
                    "Paquetes": {
                        "tipo": "PACKAGE",
                        "extension": ".pls"
                    }
                }
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("soportado", resultado.mensaje.lower())

    # --- Caso 12: UUID invalido ---

    def test_uuid_invalido(self):
        contenido = json.dumps(
            {
                "format_version": 1,
                "project_uuid": "no-es-un-uuid",
                "oracle_layout": {
                    "Paquetes": {
                        "tipo": "PACKAGE",
                        "extension": ".pls"
                    }
                }
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("uuid", resultado.mensaje.lower())

    # --- Caso 13: UUID que no es v4 ---

    def test_uuid_no_v4(self):
        # UUID v1 canonico.
        contenido = json.dumps(
            {
                "format_version": 1,
                "project_uuid": "12345678-1234-1122-8123-123456789abc",
                "oracle_layout": {
                    "Paquetes": {
                        "tipo": "PACKAGE",
                        "extension": ".pls"
                    }
                }
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("uuid", resultado.mensaje.lower())

    # --- Caso 14: UUID v4 no canonico ---

    def test_uuid_v4_no_canonico(self):
        # UUID v4 en mayusculas: no canonico (debe ser minusculas).
        uuid_con_letras = "ABCDEF01-1234-4123-8123-123456789ABC"
        contenido = json.dumps(
            {
                "format_version": 1,
                "project_uuid": uuid_con_letras,
                "oracle_layout": {
                    "Paquetes": {
                        "tipo": "PACKAGE",
                        "extension": ".pls"
                    }
                }
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("uuid", resultado.mensaje.lower())

    # --- Caso 15: layout ausente ---

    def test_layout_ausente(self):
        contenido = json.dumps(
            {
                "format_version": 1,
                "project_uuid": UUID_VALIDO
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("oracle_layout", resultado.mensaje.lower())

    # --- Caso 16: layout vacio ---

    def test_layout_vacio(self):
        contenido = json.dumps(
            {
                "format_version": 1,
                "project_uuid": UUID_VALIDO,
                "oracle_layout": {}
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("vacio", resultado.mensaje.lower())

    # --- Caso 17: carpeta invalida ---

    def test_carpeta_vacia(self):
        contenido = _manifiesto_valido(
            layout={"": {"tipo": "PACKAGE", "extension": ".pls"}}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    def test_carpeta_punto(self):
        contenido = _manifiesto_valido(
            layout={".": {"tipo": "PACKAGE", "extension": ".pls"}}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    def test_carpeta_punto_punto(self):
        contenido = _manifiesto_valido(
            layout={"..": {"tipo": "PACKAGE", "extension": ".pls"}}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    def test_carpeta_con_separador(self):
        contenido = _manifiesto_valido(
            layout={"Paquetes/Sub": {"tipo": "PACKAGE", "extension": ".pls"}}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    def test_carpeta_con_barra_invertida(self):
        contenido = _manifiesto_valido(
            layout={"Paquetes\\Sub": {"tipo": "PACKAGE", "extension": ".pls"}}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    # --- Caso 18: regla no objeto ---

    def test_regla_no_objeto(self):
        contenido = _manifiesto_valido(
            layout={"Paquetes": "no es un objeto"}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    # --- Caso 19: tipo distinto de los soportados en V1.1 ---

    def test_tipo_no_soportado(self):
        contenido = _manifiesto_valido(
            layout={"Tablas": {"tipo": "INDEX", "extension": ".sql"}}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("soportado", resultado.mensaje.lower())

    # --- Caso 20: extension distinta de .pls ---

    def test_extension_no_soportada(self):
        contenido = _manifiesto_valido(
            layout={"Paquetes": {"tipo": "PACKAGE", "extension": ".pks"}}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("extension", resultado.mensaje.lower())

    # --- Caso 21: dos carpetas que definen PACKAGE ---

    def test_dos_carpetas_mismo_tipo(self):
        contenido = _manifiesto_valido(
            layout={
                "Paquetes": {"tipo": "PACKAGE", "extension": ".pls"},
                "OtrosPaquetes": {"tipo": "PACKAGE", "extension": ".pls"}
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("tipo", resultado.mensaje.lower())

    # --- Caso 22: campos/estructura V1 no entendidos ---

    def test_campo_extra_en_regla_rechazado(self):
        contenido = _manifiesto_valido(
            layout={
                "Paquetes": {
                    "tipo": "PACKAGE",
                    "extension": ".pls",
                    "esquema": "ESQUEMA1"
                }
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    def test_campo_extra_en_raiz_rechazado(self):
        contenido = json.dumps(
            {
                "format_version": 1,
                "project_uuid": UUID_VALIDO,
                "oracle_layout": {
                    "Paquetes": {"tipo": "PACKAGE", "extension": ".pls"}
                },
                "campo_desconocido": "valor"
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        # V1 usa un parser estricto: cualquier campo no reconocido
        # en la raiz se rechaza de forma controlada.
        self.assertFalse(resultado.exitoso)
        self.assertIn("no reconocidos", resultado.mensaje.lower())

    # --- Caso: manifiesto vacio ---

    def test_manifiesto_vacio(self):
        self.repo.init()
        self.repo.commit_manifiesto("")

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIn("vacio", resultado.mensaje.lower())

    # --- Caso: raiz no es objeto ---

    def test_raiz_no_es_objeto(self):
        contenido = json.dumps([1, 2, 3])
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    # --- Caso: project_uuid vacio ---

    def test_project_uuid_vacio(self):
        contenido = json.dumps(
            {
                "format_version": 1,
                "project_uuid": "",
                "oracle_layout": {
                    "Paquetes": {"tipo": "PACKAGE", "extension": ".pls"}
                }
            }
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    # --- Caso: extension vacia ---

    def test_extension_vacia(self):
        contenido = _manifiesto_valido(
            layout={"Paquetes": {"tipo": "PACKAGE", "extension": ""}}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    # --- Caso: tipo vacio ---

    def test_tipo_vacio(self):
        contenido = _manifiesto_valido(
            layout={"Paquetes": {"tipo": "", "extension": ".pls"}}
        )
        self.repo.init()
        self.repo.commit_manifiesto(contenido)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)

    # --- Caso: ruta None ---

    def test_ruta_none(self):
        resultado = self.servicio.leer_manifiesto_head(None)

        self.assertFalse(resultado.exitoso)

    # --- Caso: ruta vacia ---

    def test_ruta_vacia(self):
        resultado = self.servicio.leer_manifiesto_head("")

        self.assertFalse(resultado.exitoso)


class TestHelpersManifiesto(unittest.TestCase):
    """
    Pruebas de las funciones helper de validacion.
    """

    def test_uuid4_canonico_valido(self):
        self.assertTrue(_es_uuid4_canonico(UUID_VALIDO))

    def test_uuid4_canonico_valido_aleatorio(self):
        import uuid as modulo_uuid
        u = str(modulo_uuid.uuid4())
        self.assertTrue(_es_uuid4_canonico(u))

    def test_uuid_no_es_uuid(self):
        self.assertFalse(_es_uuid4_canonico("no-es-un-uuid"))

    def test_uuid_v1_no_aceptado(self):
        # UUID v1 canonico.
        self.assertFalse(
            _es_uuid4_canonico("12345678-1234-1122-8123-123456789abc")
        )

    def test_uuid_mayusculas_no_canonico(self):
        # UUID v4 con letras reales para probar mayusculas.
        uuid_con_letras = "abcdef01-1234-4123-8123-123456789abc"
        self.assertFalse(_es_uuid4_canonico(uuid_con_letras.upper()))

    def test_uuid_none_no_aceptado(self):
        self.assertFalse(_es_uuid4_canonico(None))

    def test_uuid_entero_no_aceptado(self):
        self.assertFalse(_es_uuid4_canonico(42))

    def test_carpeta_valida_simple(self):
        self.assertTrue(_es_carpeta_valida("Paquetes"))

    def test_carpeta_vacia_rechazada(self):
        self.assertFalse(_es_carpeta_valida(""))

    def test_carpeta_punto_rechazada(self):
        self.assertFalse(_es_carpeta_valida("."))

    def test_carpeta_punto_punto_rechazada(self):
        self.assertFalse(_es_carpeta_valida(".."))

    def test_carpeta_con_barra_rechazada(self):
        self.assertFalse(_es_carpeta_valida("Paquetes/Sub"))

    def test_carpeta_con_barra_invertida_rechazada(self):
        self.assertFalse(_es_carpeta_valida("Paquetes\\Sub"))

    def test_carpeta_con_nul_rechazada(self):
        self.assertFalse(_es_carpeta_valida("Paquetes\x00"))

    def test_extension_valida_pls(self):
        self.assertTrue(_es_extension_valida(".pls"))

    def test_extension_sin_punto_rechazada(self):
        self.assertFalse(_es_extension_valida("pls"))

    def test_extension_vacia_rechazada(self):
        self.assertFalse(_es_extension_valida(""))

    def test_extension_solo_punto_rechazada(self):
        self.assertFalse(_es_extension_valida("."))

    def test_extension_no_alfanumerica(self):
        self.assertFalse(_es_extension_valida(".pls~"))


class TestManifiestoUTF8Invalido(unittest.TestCase):
    """
    R1-H1: un manifiesto cuyo blob contiene bytes UTF-8 invalidos
    no debe aceptarse.
    """

    def setUp(self):
        self.repo = _RepoTemporal()
        self.servicio = ServicioManifiestoProyecto(
            servicio_git=self.repo.servicio_git
        )

    def tearDown(self):
        self.repo.cleanup()

    def _manifiesto_valido_json(self):
        return json.dumps(
            {
                "format_version": 1,
                "project_uuid": UUID_VALIDO,
                "oracle_layout": {
                    "Paquetes": {
                        "tipo": "PACKAGE",
                        "extension": ".pls"
                    }
                }
            },
            ensure_ascii=False
        )

    def test_byte_ff_en_cadena_rechazado(self):
        """
        Un byte 0xFF dentro del nombre de carpeta provoca
        U+FFFD en la salida decodificada por Git y debe
        rechazarse de forma controlada.
        """

        self.repo.init()

        # Construimos un JSON donde el nombre de la carpeta
        # contiene un byte 0xFF, que no es UTF-8 valido.
        # La cadena JSON en si misma es valida como secuencia
        # de bytes, pero al decodificarla como UTF-8 el 0xFF
        # produce U+FFFD.
        contenido_bytes = (
            b'{"format_version": 1, '
            b'"project_uuid": "' + UUID_VALIDO.encode("ascii") + b'", '
            b'"oracle_layout": {"Paqu\xfftes": '
            b'{"tipo": "PACKAGE", "extension": ".pls"}}}'
        )

        self.repo.commit_manifiesto_bytes(contenido_bytes)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)
        self.assertIn("utf-8", resultado.mensaje.lower())

    def test_byte_ff_en_project_uuid_rechazado(self):
        """
        Un byte 0xFF dentro del project_uuid tambien debe
        rechazarse.
        """

        self.repo.init()

        contenido_bytes = (
            b'{"format_version": 1, '
            b'"project_uuid": "00000000-0000-4000-8000-0000000000\xff", '
            b'"oracle_layout": {"Paquetes": '
            b'{"tipo": "PACKAGE", "extension": ".pls"}}}'
        )

        self.repo.commit_manifiesto_bytes(contenido_bytes)

        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)


class TestRutaInvalidaControlada(unittest.TestCase):
    """
    R1-H2: ninguna ruta de repositorio invalida debe escapar
    como OSError/ValueError.
    """

    def setUp(self):
        self.servicio = ServicioManifiestoProyecto(
            servicio_git=ServicioGit()
        )

    def test_ruta_none_controlada(self):
        resultado = self.servicio.leer_manifiesto_head(None)

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)

    def test_ruta_entero_controlada(self):
        resultado = self.servicio.leer_manifiesto_head(12345)

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)

    def test_ruta_objeto_controlada(self):
        resultado = self.servicio.leer_manifiesto_head(object())

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)

    def test_ruta_con_bytes_controlada(self):
        resultado = self.servicio.leer_manifiesto_head(b"ruta")

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)

    def test_ruta_mock_lanza_oserror_controlada(self):
        """
        Simula con mock que Path.exists() lanza OSError y
        comprueba que el servicio devuelve un resultado
        controlado en lugar de dejar escapar la excepcion.
        """

        from unittest.mock import patch

        with patch(
            "servicio_manifiesto_proyecto.Path.exists",
            side_effect=OSError("Simulado")
        ):
            resultado = self.servicio.leer_manifiesto_head(
                "/ruta/inexistente/simulada"
            )

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)
        self.assertTrue(resultado.mensaje)

    def test_ruta_mock_lanza_valueerror_controlada(self):
        """
        Simula con mock que la construccion de Path lanza
        ValueError y comprueba que el servicio devuelve un
        resultado controlado.
        """

        from unittest.mock import patch

        with patch(
            "servicio_manifiesto_proyecto.Path",
            side_effect=ValueError("Simulado")
        ):
            resultado = self.servicio.leer_manifiesto_head(
                "/ruta/invalida/simulada"
            )

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)
        self.assertTrue(resultado.mensaje)




class TestManifiestoV11TiposAdicionales(unittest.TestCase):
    """
    Pruebas de V1.1: los 6 tipos Oracle adicionales
    (PROCEDURE, FUNCTION, TABLE, VIEW, TRIGGER, SEQUENCE)
    con extension .sql se aceptan en el manifiesto.
    """

    def setUp(self):
        self.repo = _RepoTemporal()
        self.servicio = ServicioManifiestoProyecto(
            servicio_git=self.repo.servicio_git
        )

    def tearDown(self):
        self.repo.cleanup()

    def _manifiesto_con_tipo(self, tipo, extension=".sql", carpeta=None):
        if carpeta is None:
            carpeta = tipo.capitalize() + "s"
        return _manifiesto_valido(
            layout={carpeta: {"tipo": tipo, "extension": extension}}
        )

    # --- PROCEDURE ---

    def test_procedure_sql_aceptado(self):
        self.repo.init()
        self.repo.commit_manifiesto(self._manifiesto_con_tipo("PROCEDURE"))
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertTrue(resultado.exitoso, resultado.mensaje)
        regla = resultado.manifiesto.oracle_layout[0]
        self.assertEqual(regla.tipo, "PROCEDURE")
        self.assertEqual(regla.extension, ".sql")

    # --- FUNCTION ---

    def test_function_sql_aceptado(self):
        self.repo.init()
        self.repo.commit_manifiesto(self._manifiesto_con_tipo("FUNCTION"))
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertTrue(resultado.exitoso, resultado.mensaje)
        regla = resultado.manifiesto.oracle_layout[0]
        self.assertEqual(regla.tipo, "FUNCTION")
        self.assertEqual(regla.extension, ".sql")

    # --- TABLE ---

    def test_table_sql_aceptado(self):
        self.repo.init()
        self.repo.commit_manifiesto(self._manifiesto_con_tipo("TABLE"))
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertTrue(resultado.exitoso, resultado.mensaje)
        regla = resultado.manifiesto.oracle_layout[0]
        self.assertEqual(regla.tipo, "TABLE")
        self.assertEqual(regla.extension, ".sql")

    # --- VIEW ---

    def test_view_sql_aceptado(self):
        self.repo.init()
        self.repo.commit_manifiesto(self._manifiesto_con_tipo("VIEW"))
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertTrue(resultado.exitoso, resultado.mensaje)
        regla = resultado.manifiesto.oracle_layout[0]
        self.assertEqual(regla.tipo, "VIEW")
        self.assertEqual(regla.extension, ".sql")

    # --- TRIGGER ---

    def test_trigger_sql_aceptado(self):
        self.repo.init()
        self.repo.commit_manifiesto(self._manifiesto_con_tipo("TRIGGER"))
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertTrue(resultado.exitoso, resultado.mensaje)
        regla = resultado.manifiesto.oracle_layout[0]
        self.assertEqual(regla.tipo, "TRIGGER")
        self.assertEqual(regla.extension, ".sql")

    # --- SEQUENCE ---

    def test_sequence_sql_aceptado(self):
        self.repo.init()
        self.repo.commit_manifiesto(self._manifiesto_con_tipo("SEQUENCE"))
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertTrue(resultado.exitoso, resultado.mensaje)
        regla = resultado.manifiesto.oracle_layout[0]
        self.assertEqual(regla.tipo, "SEQUENCE")
        self.assertEqual(regla.extension, ".sql")

    # --- PACKAGE retrocompatible ---

    def test_package_pls_retrocompatible(self):
        """PACKAGE -> .pls sigue funcionando igual que en V1."""
        self.repo.init()
        self.repo.commit_manifiesto(_manifiesto_valido())
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertTrue(resultado.exitoso, resultado.mensaje)
        regla = resultado.manifiesto.oracle_layout[0]
        self.assertEqual(regla.tipo, "PACKAGE")
        self.assertEqual(regla.extension, ".pls")

    # --- Extension incorrecta para tipo nuevo rechazada ---

    def test_procedure_con_extension_incorrecta_rechazada(self):
        self.repo.init()
        contenido = _manifiesto_valido(
            layout={"Procedimientos": {"tipo": "PROCEDURE", "extension": ".pls"}}
        )
        self.repo.commit_manifiesto(contenido)
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertFalse(resultado.exitoso)
        self.assertIn("extension", resultado.mensaje.lower())

    # --- Manifiesto con multiples tipos (PACKAGE + PROCEDURE) ---

    def test_multiples_tipos_en_mismo_manifiesto(self):
        layout = {
            "Paquetes": {"tipo": "PACKAGE", "extension": ".pls"},
            "Procedimientos": {"tipo": "PROCEDURE", "extension": ".sql"},
            "Vistas": {"tipo": "VIEW", "extension": ".sql"},
        }
        contenido = _manifiesto_valido(layout=layout)
        self.repo.init()
        self.repo.commit_manifiesto(contenido)
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertTrue(resultado.exitoso, resultado.mensaje)
        self.assertEqual(len(resultado.manifiesto.oracle_layout), 3)

    # --- INDEX no soportado (tipo fuera del catalogo) ---

    def test_index_no_soportado(self):
        self.repo.init()
        contenido = _manifiesto_valido(
            layout={"Indices": {"tipo": "INDEX", "extension": ".sql"}}
        )
        self.repo.commit_manifiesto(contenido)
        resultado = self.servicio.leer_manifiesto_head(self.repo.ruta)
        self.assertFalse(resultado.exitoso)
        self.assertIn("soportado", resultado.mensaje.lower())

if __name__ == "__main__":
    unittest.main()
