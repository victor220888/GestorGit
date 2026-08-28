"""
Pruebas de los modelos de Modo Equipo Oracle V1.

Estas pruebas son puramente locales y deterministas:
no tocan red, no tocan el repositorio Oracle productivo
ni crean repositorios Git.
"""

import unittest

from modelos_reservas import (
    ClaveObjetoOracle,
    ManifiestoProyecto,
    ReglaLayoutOracle,
    ResultadoManifiestoProyecto,
    ResultadoResolucionObjeto,
    ResultadoRenombradoObjeto,
    TIPOS_ORACLE_SOPORTADOS_V1,
    EXTENSIONES_ORACLE_SOPORTADAS_V1,
    ClasificacionReservaObservada,
    EstadoReservaPersistido,
    calcular_ref_reserva,
    validar_payload_reserva,
)
from servicio_remoto_reservas import _rechazar_claves_duplicadas


class TestClaveObjetoOracle(unittest.TestCase):
    """
    Pruebas de construccion y canonica de ClaveObjetoOracle.
    """

    def test_construccion_basica(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        self.assertEqual(clave.tipo, "PACKAGE")
        self.assertEqual(clave.nombre, "FINI004")

    def test_canonica_package_fini004(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        self.assertEqual(clave.canonica(), "PACKAGE|FINI004")

    def test_canonica_mayusculas(self):
        clave = ClaveObjetoOracle(tipo="package", nombre="fini004")

        self.assertEqual(clave.canonica(), "PACKAGE|FINI004")

    def test_str_devuelve_canonica(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        self.assertEqual(str(clave), "PACKAGE|FINI004")

    def test_igualdad_determinismo(self):
        clave1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        clave2 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        self.assertEqual(clave1, clave2)

    def test_desigualdad_por_nombre(self):
        clave1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        clave2 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI005")

        self.assertNotEqual(clave1, clave2)

    def test_desigualdad_por_tipo(self):
        clave1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        clave2 = ClaveObjetoOracle(tipo="PROCEDURE", nombre="FINI004")

        self.assertNotEqual(clave1, clave2)

    def test_es_inmutable(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        with self.assertRaises(Exception):
            clave.tipo = "PROCEDURE"

    def test_canonica_no_contiene_ruta_absoluta(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        canonica = clave.canonica()

        self.assertNotIn("\\", canonica)
        self.assertNotIn("/", canonica)
        self.assertNotIn(":", canonica)

    def test_canonica_no_contiene_extension(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        canonica = clave.canonica()

        self.assertNotIn(".pls", canonica)
        self.assertNotIn(".", canonica)


class TestReglaLayoutOracle(unittest.TestCase):
    """
    Pruebas de ReglaLayoutOracle.
    """

    def test_construccion_basica(self):
        regla = ReglaLayoutOracle(
            carpeta="Paquetes",
            tipo="PACKAGE",
            extension=".pls"
        )

        self.assertEqual(regla.carpeta, "Paquetes")
        self.assertEqual(regla.tipo, "PACKAGE")
        self.assertEqual(regla.extension, ".pls")

    def test_es_inmutable(self):
        regla = ReglaLayoutOracle(
            carpeta="Paquetes",
            tipo="PACKAGE",
            extension=".pls"
        )

        with self.assertRaises(Exception):
            regla.carpeta = "Otra"


class TestManifiestoProyecto(unittest.TestCase):
    """
    Pruebas de ManifiestoProyecto y reglas_por_carpeta.
    """

    def _manifiesto_valido(self):
        return ManifiestoProyecto(
            format_version=1,
            project_uuid="00000000-0000-4000-8000-000000000000",
            oracle_layout=(
                ReglaLayoutOracle(
                    carpeta="Paquetes",
                    tipo="PACKAGE",
                    extension=".pls"
                ),
            )
        )

    def test_construccion_basica(self):
        manifiesto = self._manifiesto_valido()

        self.assertEqual(manifiesto.format_version, 1)
        self.assertEqual(
            manifiesto.project_uuid,
            "00000000-0000-4000-8000-000000000000"
        )
        self.assertEqual(len(manifiesto.oracle_layout), 1)

    def test_reglas_por_carpeta(self):
        manifiesto = self._manifiesto_valido()
        reglas = manifiesto.reglas_por_carpeta()

        self.assertIn("Paquetes", reglas)
        self.assertEqual(reglas["Paquetes"].tipo, "PACKAGE")
        self.assertEqual(reglas["Paquetes"].extension, ".pls")


class TestResultadoManifiestoProyecto(unittest.TestCase):
    """
    Pruebas de ResultadoManifiestoProyecto.
    """

    def test_resultado_exitoso(self):
        manifiesto = ManifiestoProyecto(
            format_version=1,
            project_uuid="00000000-0000-4000-8000-000000000000",
            oracle_layout=(
                ReglaLayoutOracle(
                    carpeta="Paquetes",
                    tipo="PACKAGE",
                    extension=".pls"
                ),
            )
        )

        resultado = ResultadoManifiestoProyecto(
            exitoso=True,
            mensaje="OK",
            manifiesto=manifiesto
        )

        self.assertTrue(resultado.exitoso)
        self.assertIsNotNone(resultado.manifiesto)
        self.assertEqual(resultado.mensaje, "OK")

    def test_resultado_fallido_no_lanza(self):
        resultado = ResultadoManifiestoProyecto(
            exitoso=False,
            mensaje="Error controlado",
            manifiesto=None
        )

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)
        self.assertIn("Error", resultado.mensaje)


class TestResultadoResolucionObjeto(unittest.TestCase):
    """
    Pruebas de los constructores estaticos de
    ResultadoResolucionObjeto.
    """

    def test_no_oracle(self):
        resultado = ResultadoResolucionObjeto.no_oracle("README")

        self.assertTrue(resultado.es_ruta_valida)
        self.assertFalse(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)

    def test_reservable(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        resultado = ResultadoResolucionObjeto.reservable(clave)

        self.assertTrue(resultado.es_ruta_valida)
        self.assertTrue(resultado.es_objeto_oracle)
        self.assertTrue(resultado.es_reservable)
        self.assertEqual(resultado.objeto, clave)

    def test_oracle_no_resoluble(self):
        resultado = ResultadoResolucionObjeto.oracle_no_resoluble(
            "No se puede resolver"
        )

        self.assertTrue(resultado.es_ruta_valida)
        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)
        self.assertIn("resolver", resultado.mensaje)

    def test_ruta_invalida(self):
        resultado = ResultadoResolucionObjeto.ruta_invalida(
            "Ruta absoluta"
        )

        self.assertFalse(resultado.es_ruta_valida)
        self.assertFalse(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)


class TestResultadoRenombradoObjeto(unittest.TestCase):
    """
    Pruebas de ResultadoRenombradoObjeto.
    """

    def test_renombrado_resoluble(self):
        clave1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        clave2 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI005")

        resultado = ResultadoRenombradoObjeto(
            es_resoluble=True,
            claves=[clave1, clave2]
        )

        self.assertTrue(resultado.es_resoluble)
        self.assertEqual(len(resultado.claves), 2)

    def test_renombrado_no_resoluble(self):
        resultado = ResultadoRenombradoObjeto(
            es_resoluble=False,
            rutas_no_resolvibles=["Paquetes/Sub/FINI004.pls"],
            mensaje="Rutas Oracle no resolubles"
        )

        self.assertFalse(resultado.es_resoluble)
        self.assertEqual(len(resultado.rutas_no_resolvibles), 1)


class TestConstantesV1(unittest.TestCase):
    """
    Pruebas de las constantes soportadas en V1.
    """

    def test_tipo_soportado_package(self):
        self.assertIn("PACKAGE", TIPOS_ORACLE_SOPORTADOS_V1)

    def test_extension_soportada_pls(self):
        self.assertEqual(
            EXTENSIONES_ORACLE_SOPORTADAS_V1["PACKAGE"],
            ".pls"
        )

    def test_no_hay_otros_tipos(self):
        self.assertEqual(len(TIPOS_ORACLE_SOPORTADOS_V1), 1)


# =====================================================================
# Modelos remotos de reservas (Bloque D)
# =====================================================================


def _uuid4():
    """UUID v4 canonico para pruebas."""

    import uuid

    return str(uuid.uuid4())


def _payload_valido(estado="ACTIVA", ahora=None, ttl=1800):
    """Construye un dict payload V1 valido."""

    import datetime as dt

    if ahora is None:
        ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    if estado == "LIBERADA":
        heartbeat = ahora
        vencimiento = ahora
    else:
        heartbeat = ahora
        vencimiento = ahora + dt.timedelta(seconds=ttl)
    return {
        "format_version": 1,
        "operation_id": _uuid4(),
        "project_uuid": _uuid4(),
        "clave_objeto": "PACKAGE|FINI004",
        "estado": estado,
        "id_cliente": _uuid4(),
        "alias": "equipo",
        "hostname": "pc-1",
        "user_name": "ana",
        "inicio": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "heartbeat": heartbeat.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "vencimiento": vencimiento.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rama_local": "",
        "rutas": ["Paquetes/FINI004.pls"],
    }


class TestEstadosPersistidos(unittest.TestCase):
    """16.1.1 estados persistidos admitidos."""

    def test_activa_y_liberada(self):
        self.assertEqual(
            EstadoReservaPersistido.ACTIVA.value, "ACTIVA"
        )
        self.assertEqual(
            EstadoReservaPersistido.LIBERADA.value, "LIBERADA"
        )

    def test_no_existe_vencida_persistida(self):
        with self.assertRaises(AttributeError):
            EstadoReservaPersistido.VENCIDA  # noqa: B018


class TestClasificacionesObservadas(unittest.TestCase):
    """16.1.2 clasificaciones."""

    def test_todas_las_clasificaciones(self):
        valores = {c.value for c in ClasificacionReservaObservada}
        self.assertEqual(
            valores,
            {
                "LIBRE",
                "RESERVADO_POR_MI",
                "RESERVADO_POR_OTRO",
                "VENCIDO_PROPIO",
                "VENCIDO_AJENO",
                "NO_VERIFICABLE",
                "RESULTADO_INCIERTO",
                "OPERACION_EN_CURSO",
            },
        )


class TestUUID4Canonico(unittest.TestCase):
    """16.1.3 UUID4 canonicos."""

    def test_uuid_valido(self):
        from modelos_reservas import _es_uuid4_canonico

        self.assertTrue(_es_uuid4_canonico(_uuid4()))

    def test_uuid_invalido(self):
        from modelos_reservas import _es_uuid4_canonico

        self.assertFalse(_es_uuid4_canonico("no-es-uuid"))
        self.assertFalse(_es_uuid4_canonico(_uuid4().upper()))
        self.assertFalse(_es_uuid4_canonico(_uuid4().replace("-", "")))
        self.assertFalse(_es_uuid4_canonico(123))


class TestEsquemaExacto(unittest.TestCase):
    """16.1.4 esquema exacto / 16.1.5 faltantes / 16.1.6 extra."""

    def test_payload_valido(self):
        ok, payload, mensaje = validar_payload_reserva(
            _payload_valido()
        )
        self.assertTrue(ok, mensaje)
        self.assertIsNotNone(payload)

    def test_claves_faltantes(self):
        datos = _payload_valido()
        del datos["rutas"]
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIsNone(payload)
        self.assertIn("faltantes", mensaje)

    def test_claves_extra(self):
        datos = _payload_valido()
        datos["clave_extra"] = True
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIsNone(payload)
        self.assertIn("extra", mensaje)


class TestClavesDuplicadas(unittest.TestCase):
    """16.1.7 claves JSON duplicadas."""

    def test_duplicadas_rechazadas(self):
        import json

        datos = _payload_valido()
        contenido = json.dumps(datos, sort_keys=True)
        # Duplicar la clave "estado" al final.
        duplicado = contenido[:-1] + ',"estado":"ACTIVA"}'
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            json.loads(
                duplicado,
                object_pairs_hook=_rechazar_claves_duplicadas,
            )


class TestEstadoInvalido(unittest.TestCase):
    """16.1.8 estado invalido."""

    def test_estado_no_soportado(self):
        datos = _payload_valido()
        datos["estado"] = "VENCIDA"
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIn("estado", mensaje)


class TestProjectUuidIncorrecto(unittest.TestCase):
    """16.1.9 project_uuid incorrecto."""

    def test_no_coincide_con_consulta(self):
        datos = _payload_valido()
        esperado = datos["project_uuid"]
        datos["project_uuid"] = _uuid4()
        ok, payload, mensaje = validar_payload_reserva(
            datos, project_uuid_esperado=esperado
        )
        self.assertFalse(ok)
        self.assertIn("project_uuid", mensaje)


class TestClaveObjetoIncorrecta(unittest.TestCase):
    """16.1.10 clave_objeto incorrecta."""

    def test_no_coincide_con_consulta(self):
        datos = _payload_valido()
        ok, payload, mensaje = validar_payload_reserva(
            datos, clave_objeto_esperada="PACKAGE|OTRO"
        )
        self.assertFalse(ok)
        self.assertIn("clave_objeto", mensaje)


class TestIdClienteInvalido(unittest.TestCase):
    """16.1.11 id_cliente invalido."""

    def test_id_cliente_no_uuid(self):
        datos = _payload_valido()
        datos["id_cliente"] = "ana"
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIn("id_cliente", mensaje)


class TestOperationIdInvalido(unittest.TestCase):
    """16.1.12 operation_id invalido."""

    def test_operation_id_no_uuid(self):
        datos = _payload_valido()
        datos["operation_id"] = "op-1"
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIn("operation_id", mensaje)


class TestTimestampsInvalidos(unittest.TestCase):
    """16.1.13 timestamps invalidos."""

    def test_formato_no_rfc3339(self):
        datos = _payload_valido()
        datos["inicio"] = "2026-08-27 10:00:00"
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIn("Timestamp", mensaje)

    def test_con_microsegundos(self):
        datos = _payload_valido()
        datos["heartbeat"] = "2026-08-27T10:00:00.123Z"
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)


class TestRFC3339Estricto(unittest.TestCase):
    """REV3 §12: RFC3339 V1 EXACTO YYYY-MM-DDTHH:MM:SSZ.

    parsear_timestamp_utc no acepta variantes relajadas que
    strptime pudiera tolerar: validación léxica exacta + parseo
    semántico.
    """

    def test_formato_valido(self):
        from modelos_reservas import (
            formatear_timestamp_utc,
            parsear_timestamp_utc,
        )

        texto = "2026-08-27T10:00:00Z"
        instante = parsear_timestamp_utc(texto)
        self.assertIsNotNone(instante)
        # Ida y vuelta exacta y timezone UTC.
        self.assertEqual(
            formatear_timestamp_utc(instante), texto
        )

    def test_variantes_relajadas_rechazadas(self):
        from modelos_reservas import parsear_timestamp_utc

        variantes = (
            "2026-08-27T10:00:00z",       # z minúscula
            "2026-08-27t10:00:00Z",       # t minúscula
            "2026-08-27T10:00:00+00:00",  # offset en vez de Z
            "2026-08-27 10:00:00Z",       # espacio en vez de T
            "2026-08-27T1:00:00Z",        # hora sin cero inicial
            "2026-8-27T10:00:00Z",        # mes sin cero inicial
            "2026-08-27T10:00Z",          # sin segundos
            "2026-08-27T10:00:00.123Z",   # microsegundos
            "2026-08-27T10:00:00",        # sin Z
            "2026-13-27T10:00:00Z",       # mes imposible
            "2026-08-27T25:00:00Z",       # hora imposible
            "",                           # vacío
        )
        for texto in variantes:
            self.assertIsNone(
                parsear_timestamp_utc(texto), texto
            )


class TestRelacionTemporalActiva(unittest.TestCase):
    """16.1.14 relacion temporal ACTIVA invalida."""

    def test_vencimiento_antes_de_heartbeat(self):
        import datetime as dt

        ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        datos = _payload_valido(estado="ACTIVA", ahora=ahora)
        datos["heartbeat"] = (
            ahora + dt.timedelta(seconds=2000)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        datos["vencimiento"] = (
            ahora + dt.timedelta(seconds=1000)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIn("ACTIVA", mensaje)

    def test_ttl_distinto(self):
        datos = _payload_valido(estado="ACTIVA", ttl=1800)
        datos["vencimiento"] = datos["heartbeat"]  # ttl 0
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIn("vencimiento - heartbeat", mensaje)


class TestRelacionTemporalLiberada(unittest.TestCase):
    """16.1.15 relacion temporal LIBERADA invalida."""

    def test_vencimiento_distinto_de_heartbeat(self):
        import datetime as dt

        ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        datos = _payload_valido(estado="LIBERADA", ahora=ahora)
        datos["vencimiento"] = (
            ahora + dt.timedelta(seconds=10)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIn("LIBERADA", mensaje)


class TestRutasValidas(unittest.TestCase):
    """16.1.16 rutas absolutas / '..' / duplicadas / NUL-CR-LF."""

    def test_ruta_absoluta(self):
        datos = _payload_valido()
        datos["rutas"] = ["C:/absoluta/FINI004.pls"]
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)

    def test_ruta_con_puntos(self):
        datos = _payload_valido()
        datos["rutas"] = ["../fuera.pls"]
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)

    def test_ruta_duplicada(self):
        datos = _payload_valido()
        datos["rutas"] = ["a.pls", "a.pls"]
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIn("duplicados", mensaje)

    def test_ruta_con_nul_cr_lf(self):
        datos = _payload_valido()
        datos["rutas"] = ["a\nb.pls"]
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)

    def test_orden_determinista(self):
        datos = _payload_valido()
        datos["rutas"] = ["b.pls", "a.pls"]
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertFalse(ok)
        self.assertIn("orden", mensaje)


class TestSerializacionDeterminista(unittest.TestCase):
    """16.1.17 serializacion determinista."""

    def test_serializacion_estable(self):
        datos = _payload_valido()
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertTrue(ok, mensaje)
        s1 = payload.serializar()
        s2 = payload.serializar()
        self.assertEqual(s1, s2)
        self.assertTrue(s1.endswith("\n"))
        self.assertIn('"format_version":1', s1)
        self.assertNotIn('"format_version": 1', s1)

    def test_orden_sort_keys(self):
        datos = _payload_valido()
        ok, payload, mensaje = validar_payload_reserva(datos)
        self.assertTrue(ok, mensaje)
        import json

        obj = json.loads(payload.serializar())
        self.assertEqual(list(obj.keys()), sorted(obj.keys()))


class TestAusenciaSecretos(unittest.TestCase):
    """16.1.18 ausencia de user.email/token/password."""

    def test_no_hay_campos_secretos(self):
        datos = _payload_valido()
        for secreto in (
            "user.email",
            "password",
            "token",
            "PAT",
            "backend",
            "APPDATA",
        ):
            self.assertNotIn(secreto, datos)

    def test_serializacion_sin_secretos(self):
        ok, payload, mensaje = validar_payload_reserva(
            _payload_valido()
        )
        self.assertTrue(ok, mensaje)
        s = payload.serializar()
        self.assertNotIn("password", s)
        self.assertNotIn("token", s)
        self.assertNotIn("user.email", s)
        self.assertNotIn("@", s.split("hostname")[0])  # no emails


class TestRefSha256(unittest.TestCase):
    """Ref SHA-256 completo, determinista y sensible a entradas."""

    def test_formula_exacta_con_separador_nul(self):
        """REV3 §6: fórmula EXACTA de la arquitectura.

            sha256(project_uuid + "\\0" + clave_objeto).hexdigest()

        Guarda adicional: el separador NO es ':' (fórmula
        incorrecta detectada por la auditoría REV3).
        """
        import hashlib

        project_uuid = "33333333-3333-4333-8333-333333333333"
        clave = "PACKAGE|FINI004"
        esperado = hashlib.sha256(
            (project_uuid + "\0" + clave).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            calcular_ref_reserva(project_uuid, clave),
            esperado,
        )
        variante_dos_puntos = hashlib.sha256(
            (project_uuid + ":" + clave).encode("utf-8")
        ).hexdigest()
        self.assertNotEqual(
            calcular_ref_reserva(project_uuid, clave),
            variante_dos_puntos,
        )

    def test_ref_determinista(self):
        r1 = calcular_ref_reserva(
            "11111111-1111-4111-8111-111111111111",
            "PACKAGE|FINI004",
        )
        r2 = calcular_ref_reserva(
            "11111111-1111-4111-8111-111111111111",
            "PACKAGE|FINI004",
        )
        self.assertEqual(r1, r2)
        self.assertEqual(len(r1), 64)

    def test_ref_cambia_con_project_uuid(self):
        r1 = calcular_ref_reserva(
            "11111111-1111-4111-8111-111111111111",
            "PACKAGE|FINI004",
        )
        r2 = calcular_ref_reserva(
            "22222222-2222-4222-8222-222222222222",
            "PACKAGE|FINI004",
        )
        self.assertNotEqual(r1, r2)

    def test_ref_cambia_con_clave(self):
        r1 = calcular_ref_reserva(
            "11111111-1111-4111-8111-111111111111",
            "PACKAGE|FINI004",
        )
        r2 = calcular_ref_reserva(
            "11111111-1111-4111-8111-111111111111",
            "PACKAGE|FINI005",
        )
        self.assertNotEqual(r1, r2)


if __name__ == "__main__":
    unittest.main()
