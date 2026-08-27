"""
Pruebas del servicio de identidad de instalacion de Modo Equipo.

Estas pruebas no tocan %APPDATA% real, no usan Git ni red.
Usan carpetas temporales y rutas inyectadas.
"""

import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from servicio_identidad_equipo import ServicioIdentidadEquipo


def _uuid4_canonico():
    """Genera un UUID v4 canonico en minusculas con guiones."""

    return str(uuid.uuid4())


class TestServicioIdentidadEquipo(unittest.TestCase):
    """
    Pruebas de ServicioIdentidadEquipo.
    """

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta_temporal = Path(self.temporal.name)
        self.ruta_identidad = (
            self.ruta_temporal / "identidad_instalacion.json"
        )
        self.servicio = ServicioIdentidadEquipo(
            ruta_identidad=str(self.ruta_identidad)
        )

    def tearDown(self):
        self.temporal.cleanup()

    def _escribir_identidad(self, id_cliente, version=1):
        """Escribe un archivo de identidad valido."""

        self.ruta_identidad.parent.mkdir(
            parents=True,
            exist_ok=True
        )
        self.ruta_identidad.write_text(
            json.dumps(
                {
                    "format_version": version,
                    "id_cliente": id_cliente
                },
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    def _escribir_bytes_crudos(self, bytes_contenido):
        """Escribe bytes crudos en el archivo de identidad."""

        self.ruta_identidad.parent.mkdir(
            parents=True,
            exist_ok=True
        )
        self.ruta_identidad.write_bytes(bytes_contenido)

    def _leer_identidad(self):
        """Lee el archivo de identidad como dict."""

        return json.loads(
            self.ruta_identidad.read_text(encoding="utf-8")
        )

    # 1. ruta inyectada temporal

    def test_ruta_inyectada_temporal(self):
        """La ruta inyectada se usa sin tocar %APPDATA%."""

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertTrue(resultado.exitoso)
        self.assertTrue(self.ruta_identidad.exists())
        self.assertEqual(
            self.servicio.ruta_identidad,
            self.ruta_identidad
        )

    # 2. derivacion por defecto desde APPDATA mediante mock

    def test_derivacion_por_defecto_desde_appdata(self):
        """Sin ruta inyectada, se usa %APPDATA%\\GestorGit\\..."""

        appdata_temporal = self.ruta_temporal / "appdata"
        appdata_temporal.mkdir()

        with mock.patch.dict(
            os.environ,
            {"APPDATA": str(appdata_temporal)},
            clear=False
        ):
            # APPDATA podria estar definida o no en el entorno
            # de pruebas; aseguramos que solo existe la nuestra.
            with mock.patch.dict(
                os.environ,
                {"APPDATA": str(appdata_temporal)}
            ):
                servicio = ServicioIdentidadEquipo()
                self.assertEqual(
                    servicio.ruta_identidad,
                    appdata_temporal / "GestorGit" / "identidad_instalacion.json"
                )

                resultado = servicio.obtener_o_crear_identidad()
                self.assertTrue(resultado.exitoso)
                self.assertTrue(resultado.id_cliente)

    # 3. APPDATA ausente -> error controlado

    def test_appdata_ausente_error_controlado(self):
        """Sin APPDATA ni ruta inyectada, error controlado."""

        entorno_original = os.environ.copy()
        entorno_sin_appdata = {
            k: v for k, v in entorno_original.items()
            if k != "APPDATA"
        }
        try:
            os.environ.clear()
            os.environ.update(entorno_sin_appdata)

            servicio = ServicioIdentidadEquipo()

            self.assertIsNone(servicio.ruta_identidad)

            resultado = servicio.obtener_o_crear_identidad()

            self.assertFalse(resultado.exitoso)
            self.assertEqual(resultado.id_cliente, "")
            self.assertIn("APPDATA", resultado.mensaje)
        finally:
            os.environ.clear()
            os.environ.update(entorno_original)

    # 4. archivo ausente -> crea identidad

    def test_archivo_ausente_crea_identidad(self):
        """Si el archivo no existe, se crea un UUID v4."""

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertTrue(resultado.exitoso)
        self.assertTrue(resultado.id_cliente)
        self.assertTrue(self.ruta_identidad.exists())

    # 5. UUID generado es v4 canonico

    def test_uuid_generado_es_v4_canonico(self):
        """El id_cliente generado es un UUID v4 canonico."""

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertTrue(resultado.exitoso)
        u = uuid.UUID(resultado.id_cliente)
        self.assertEqual(u.version, 4)
        self.assertEqual(resultado.id_cliente, str(u))
        self.assertEqual(resultado.id_cliente, resultado.id_cliente.lower())
        self.assertEqual(len(resultado.id_cliente), 36)

    # 6. segunda lectura devuelve exactamente el mismo ID

    def test_segunda_lectura_mismo_id(self):
        """Una segunda lectura devuelve el mismo id_cliente."""

        r1 = self.servicio.obtener_o_crear_identidad()
        self.assertTrue(r1.exitoso)

        r2 = self.servicio.obtener_o_crear_identidad()
        self.assertTrue(r2.exitoso)

        self.assertEqual(r1.id_cliente, r2.id_cliente)

    # 7. dos instancias secuenciales obtienen el mismo ID

    def test_dos_instancias_mismo_id(self):
        """Dos instancias distintas del servicio, mismo archivo,
        mismo id_cliente."""

        r1 = self.servicio.obtener_o_crear_identidad()
        self.assertTrue(r1.exitoso)

        otro_servicio = ServicioIdentidadEquipo(
            ruta_identidad=str(self.ruta_identidad)
        )
        r2 = otro_servicio.obtener_o_crear_identidad()
        self.assertTrue(r2.exitoso)

        self.assertEqual(r1.id_cliente, r2.id_cliente)

    # 8. archivo valido existente no se reescribe

    def test_archivo_valido_no_se_reescribe(self):
        """Un archivo valido existente no se modifica al leer."""

        id_original = _uuid4_canonico()
        self._escribir_identidad(id_original)

        contenido_antes = self.ruta_identidad.read_bytes()
        mtime_antes = self.ruta_identidad.stat().st_mtime_ns

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertTrue(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, id_original)

        contenido_despues = self.ruta_identidad.read_bytes()
        mtime_despues = self.ruta_identidad.stat().st_mtime_ns

        self.assertEqual(contenido_antes, contenido_despues)
        self.assertEqual(mtime_antes, mtime_despues)

    # 9. JSON invalido -> error, no regeneracion

    def test_json_invalido_error_no_regeneracion(self):
        """JSON invalido: error controlado, archivo intacto."""

        contenido_invalido = b"{esto no es json"
        self._escribir_bytes_crudos(contenido_invalido)

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")
        self.assertIn("JSON", resultado.mensaje)

        self.assertEqual(
            self.ruta_identidad.read_bytes(),
            contenido_invalido
        )

    # 10. UTF-8 invalido -> error, no regeneracion

    def test_utf8_invalido_error_no_regeneracion(self):
        """UTF-8 invalido: error controlado, archivo intacto."""

        contenido_invalido = b'{"format_version": 1, "id_cliente": "\xff"}'
        self._escribir_bytes_crudos(contenido_invalido)

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

        self.assertEqual(
            self.ruta_identidad.read_bytes(),
            contenido_invalido
        )

    # 11. raiz no objeto

    def test_raiz_no_objeto_error(self):
        """Raiz JSON no es objeto: error controlado."""

        self._escribir_bytes_crudos(b"[1, 2, 3]")

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    # 12. campo extra -> error

    def test_campo_extra_error(self):
        """Campo adicional a format_version e id_cliente: error."""

        id_valido = _uuid4_canonico()
        self.ruta_identidad.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_identidad.write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "id_cliente": id_valido,
                    "campo_extra": "no permitido"
                }
            ),
            encoding="utf-8"
        )

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    # 13. campo faltante -> error

    def test_campo_faltante_error(self):
        """Falta id_cliente: error."""

        self.ruta_identidad.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_identidad.write_text(
            json.dumps({"format_version": 1}),
            encoding="utf-8"
        )

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    def test_campo_faltante_format_version_error(self):
        """Falta format_version: error."""

        id_valido = _uuid4_canonico()
        self.ruta_identidad.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_identidad.write_text(
            json.dumps({"id_cliente": id_valido}),
            encoding="utf-8"
        )

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    # 14. format_version=True -> error

    def test_format_version_bool_error(self):
        """format_version=True (bool) se rechaza como entero."""

        id_valido = _uuid4_canonico()
        self.ruta_identidad.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_identidad.write_text(
            json.dumps(
                {
                    "format_version": True,
                    "id_cliente": id_valido
                }
            ),
            encoding="utf-8"
        )

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    # 15. version distinta de 1 -> error

    def test_version_distinta_de_uno_error(self):
        """format_version=2: error."""

        id_valido = _uuid4_canonico()
        self._escribir_identidad(id_valido, version=2)

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    # 16. UUID invalido

    def test_uuid_invalido_error(self):
        """id_cliente no es un UUID: error."""

        self.ruta_identidad.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_identidad.write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "id_cliente": "no-es-un-uuid"
                }
            ),
            encoding="utf-8"
        )

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    # 17. UUID v1

    def test_uuid_v1_error(self):
        """id_cliente es UUID v1: error (se requiere v4)."""

        u = uuid.uuid1()
        self._escribir_identidad(str(u))

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    # 18. UUID v4 no canonico

    def test_uuid_v4_no_canonico_error(self):
        """UUID v4 en mayusculas: error (se requiere canonico
        en minusculas)."""

        u = uuid.uuid4()
        self._escribir_identidad(str(u).upper())

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    def test_uuid_v4_sin_guiones_error(self):
        """UUID v4 sin guiones: error (se requiere canonico
        con guiones)."""

        u = uuid.uuid4()
        self._escribir_identidad(u.hex)

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    # 19. claves duplicadas

    def test_claves_duplicadas_error(self):
        """Claves duplicadas en JSON: error."""

        id_valido = _uuid4_canonico()
        self.ruta_identidad.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_identidad.write_text(
            '{"format_version": 1, '
            '"id_cliente": "' + id_valido + '", '
            '"id_cliente": "' + _uuid4_canonico() + '"}',
            encoding="utf-8"
        )

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")

    # 20. fallo de creacion/escritura -> resultado controlado

    def test_fallo_creacion_directorio_invalido(self):
        """Si el padre es un archivo (no directorio), la creacion
        falla de forma controlada."""

        archivo = self.ruta_temporal / "archivo"
        archivo.write_text("datos", encoding="utf-8")

        ruta_invalida = archivo / "identidad_instalacion.json"
        servicio = ServicioIdentidadEquipo(
            ruta_identidad=str(ruta_invalida)
        )

        resultado = servicio.obtener_o_crear_identidad()

        self.assertFalse(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, "")
        self.assertTrue(resultado.mensaje)

    # 21. carrera simulada donde otro proceso crea primero

    def test_carrera_otro_proceso_crea_primero(self):
        """Si otro proceso crea el archivo entre la comprobacion
        y la escritura, se re-lee el archivo existente."""

        id_existente = _uuid4_canonico()
        self._escribir_identidad(id_existente)

        # Forzar que exists() devuelva False la primera vez
        # para que el servicio intente crear, pero open(..., 'x')
        # fallara con FileExistsError y se re-leera el existente.
        with mock.patch.object(
            Path,
            "exists",
            return_value=False
        ):
            resultado = self.servicio.obtener_o_crear_identidad()

        self.assertTrue(resultado.exitoso)
        self.assertEqual(resultado.id_cliente, id_existente)

    # 22. archivo no contiene alias/backend/email/token

    def test_archivo_no_contiene_datos_sensibles(self):
        """El archivo de identidad solo contiene format_version
        e id_cliente."""

        resultado = self.servicio.obtener_o_crear_identidad()
        self.assertTrue(resultado.exitoso)

        datos = self._leer_identidad()

        self.assertEqual(set(datos.keys()), {"format_version", "id_cliente"})
        self.assertNotIn("alias_equipo", datos)
        self.assertNotIn("backend_reservas_url", datos)
        self.assertNotIn("ruta_repositorio", datos)
        self.assertNotIn("hostname", datos)
        self.assertNotIn("user_name", datos)
        self.assertNotIn("correo", datos)
        self.assertNotIn("email", datos)
        self.assertNotIn("token", datos)
        self.assertNotIn("password", datos)
        self.assertNotIn("pat", datos)

    # 23. cero Git y cero red

    def test_cero_git_cero_red(self):
        """El servicio funciona sin Git y sin red en una
        carpeta temporal sin repositorio."""

        # Verificar que no hay .git en la carpeta temporal
        self.assertFalse((self.ruta_temporal / ".git").exists())

        resultado = self.servicio.obtener_o_crear_identidad()

        self.assertTrue(resultado.exitoso)
        self.assertTrue(resultado.id_cliente)


if __name__ == "__main__":
    unittest.main()
