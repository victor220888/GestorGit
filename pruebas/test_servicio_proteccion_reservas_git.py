"""
Pruebas de ServicioProteccionReservasGit (Bloque E): protección
pura, 100% local, de staging/commit.

Estas pruebas NO crean repositorios Git: el resolvedor de objetos
Oracle es puro (manifiesto inyectado) y el servicio de reservas es
un doble de pruebas que solo expone validar_reserva_propia_fresca.
Ninguna prueba ejecuta red, Fetch, Push ni operaciones de escritura
de reservas.

Cobertura GG-PROMPT-039 §12.1 (casos 1-19).
"""

import types
import unittest
from unittest import mock

from modelos_reservas import (
    ManifiestoProyecto,
    ReglaLayoutOracle,
    ResultadoValidacionReservaPropia,
)
from servicio_objetos_oracle import ServicioObjetosOracle
from servicio_proteccion_reservas_git import (
    ResultadoProteccionReservasGit,
    ServicioProteccionReservasGit,
)
from servicio_reservas import ServicioReservas
from servicio_validacion_contenido_oracle import (
    ServicioValidacionContenidoOracle,
)


CLAVE_FINI004 = "PACKAGE|FINI004"
CLAVE_FINI005 = "PACKAGE|FINI005"
CLAVE_FINI006 = "PACKAGE|FINI006"
CLAVE_FINI007 = "PACKAGE|FINI007"


def _manifiesto():
    return ManifiestoProyecto(
        format_version=1,
        project_uuid="11111111-1111-4111-8111-111111111111",
        oracle_layout=(
            ReglaLayoutOracle(
                carpeta="Paquetes",
                tipo="PACKAGE",
                extension=".pls",
            ),
        ),
    )


class ReservasFalsas:
    """
    Doble del ServicioReservas de Bloque D.

    Solo implementa validar_reserva_propia_fresca (la única API
    autorizada por Bloque E). Cualquier otro acceso a métodos
    (consultar_reserva, fetch_reservas, reservar, renovar,
    liberar, tomar_vencida, ...) lanza AssertionError: si el
    protector los llamara, la prueba falla.
    """

    def __init__(self, resultados=None, valida=False, motivo=""):
        self.llamadas_validar = []
        self.resultados = resultados or {}
        self.valida = valida
        self.motivo = motivo

    def validar_reserva_propia_fresca(self, clave_objeto):
        self.llamadas_validar.append(clave_objeto)
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
            f"El protector no debe llamar a '{nombre}': la "
            "protección es 100% local y delega solo en "
            "validar_reserva_propia_fresca."
        )


def _resultado(valida, motivo=""):
    return ResultadoValidacionReservaPropia(
        valida=valida,
        motivo=motivo,
    )


class _BaseProteccion(unittest.TestCase):

    def setUp(self):
        self.reservas = ReservasFalsas(
            valida=True,
            motivo="Reserva propia fresca valida.",
        )
        self.protector = ServicioProteccionReservasGit(
            resolvedor_oracle=ServicioObjetosOracle(_manifiesto()),
            servicio_reservas=self.reservas,
            project_uuid="11111111-1111-4111-8111-111111111111",
        )


class TestCasosPermitidos(_BaseProteccion):
    """12.1.1-2: ruta ordinaria y Oracle con reserva fresca."""

    def test_ruta_ordinaria_permitida_sin_reserva(self):
        resultado = self.protector.proteger_staging(
            ["Lecturas/nota.txt"]
        )
        self.assertTrue(resultado.permitido, resultado.motivo)
        self.assertEqual(resultado.claves, ())
        self.assertFalse(resultado.requiere_reserva)
        # Una ruta ordinaria no consume ninguna validación.
        self.assertEqual(self.reservas.llamadas_validar, [])

    def test_oracle_con_reserva_propia_fresca_permitido(self):
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self.assertTrue(resultado.permitido, resultado.motivo)
        self.assertEqual(resultado.claves, (CLAVE_FINI004,))
        self.assertEqual(
            self.reservas.llamadas_validar, [CLAVE_FINI004]
        )

    def test_mensaje_permitido_vacio(self):
        resultado = self.protector.proteger_commit(
            ["Paquetes/FINI004.pls"]
        )
        self.assertTrue(resultado.permitido)
        self.assertEqual(resultado.componer_mensaje(), "")


class TestBloqueosPorReserva(_BaseProteccion):
    """12.1.3-10: bloqueos delegados en la política de Bloque D."""

    def setUp(self):
        super().setUp()
        # Por defecto este grupo prueba bloqueos: sin una reserva
        # propia verificada y fresca, la validación de Bloque D
        # devuelve valida=False.
        self.reservas.valida = False

    def _bloqueo_esperado(self, resultado, texto_motivo):
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.requiere_reserva)
        self.assertIn(texto_motivo, resultado.motivo)
        self.assertIn(texto_motivo, resultado.componer_mensaje())
        self.assertIn(
            "reserva propia, verificada y fresca",
            resultado.componer_mensaje(),
        )

    def test_oracle_sin_cache_bloqueado(self):
        self.reservas.motivo = "No hay una consulta previa verificada."
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self._bloqueo_esperado(resultado, "consulta previa")
        self.assertEqual(resultado.claves, (CLAVE_FINI004,))

    def test_reserva_ajena_bloqueado(self):
        self.reservas.motivo = "La reserva pertenece a otro id_cliente."
        resultado = self.protector.proteger_commit(
            ["Paquetes/FINI004.pls"]
        )
        self._bloqueo_esperado(resultado, "otro id_cliente")

    def test_reserva_vencida_bloqueado(self):
        self.reservas.motivo = "La reserva esta vencida."
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self._bloqueo_esperado(resultado, "vencida")

    def test_reserva_liberada_bloqueado(self):
        self.reservas.motivo = (
            "La ultima clasificacion no es RESERVADO_POR_MI."
        )
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self._bloqueo_esperado(resultado, "RESERVADO_POR_MI")

    def test_cache_fresca_expirada_bloqueado(self):
        self.reservas.motivo = (
            "Verificacion con mas de 60 s de frescura."
        )
        resultado = self.protector.proteger_commit(
            ["Paquetes/FINI004.pls"]
        )
        self._bloqueo_esperado(resultado, "frescura")

    def test_margen_insuficiente_bloqueado(self):
        self.reservas.motivo = (
            "Tiempo restante menor al margen minimo (300 s)."
        )
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self._bloqueo_esperado(resultado, "margen")

    def test_resultado_incierto_bloqueado(self):
        self.reservas.motivo = (
            "Resultado incierto; no se puede autorizar."
        )
        resultado = self.protector.proteger_commit(
            ["Paquetes/FINI004.pls"]
        )
        self._bloqueo_esperado(resultado, "incierto")

    def test_operacion_red_en_curso_bloqueado(self):
        self.reservas.motivo = (
            "Hay una operacion de reservas o de red en curso; "
            "validacion bloqueada."
        )
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self._bloqueo_esperado(resultado, "en curso")

    def test_validacion_lanza_excepcion_bloqueado(self):
        # Fail-safe: una excepción inesperada de la validación
        # BLOQUEA; nunca degrada a permitido.
        with mock.patch.object(
            self.reservas,
            "validar_reserva_propia_fresca",
            side_effect=RuntimeError("fallo interno"),
        ):
            resultado = self.protector.proteger_staging(
                ["Paquetes/FINI004.pls"]
            )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.requiere_reserva)
        self.assertIn("inesperada", resultado.motivo)


class TestBloqueosPorResolucion(_BaseProteccion):
    """12.1.11-12: Oracle no resoluble y rutas inválidas."""

    def test_ruta_oracle_no_resoluble_bloqueado(self):
        # Extensión de la familia Oracle (.sql) con carpeta no
        # mapeada: nunca se interpreta como ruta ordinaria.
        resultado = self.protector.proteger_staging(
            ["Sospechoso/algo.sql"]
        )
        self.assertFalse(resultado.permitido)
        self.assertFalse(resultado.requiere_reserva)
        self.assertIn(
            "No puede determinarse TIPO|NOMBRE", resultado.motivo
        )
        self.assertEqual(self.reservas.llamadas_validar, [])

    def test_ruta_invalida_absoluta_bloqueado(self):
        resultado = self.protector.proteger_commit(
            ["C:/fuera/fini004.pls"]
        )
        self.assertFalse(resultado.permitido)
        self.assertIn("no es una ruta relativa", resultado.motivo)

    def test_ruta_invalida_puntos_bloqueado(self):
        resultado = self.protector.proteger_staging(
            ["../fuera/fini004.pls"]
        )
        self.assertFalse(resultado.permitido)

    def test_ruta_none_bloqueado(self):
        resultado = self.protector.proteger_staging([None])
        self.assertFalse(resultado.permitido)
        self.assertIn("conjunto de rutas", resultado.motivo)

    def test_conjunto_vacio_bloqueado(self):
        resultado = self.protector.proteger_commit([])
        self.assertFalse(resultado.permitido)
        self.assertIn("conjunto de rutas", resultado.motivo)


class TestDeduplicacionObjetos(_BaseProteccion):
    """12.1.13-15: deduplicación por clave canónica."""

    def test_varias_rutas_mismo_objeto_una_validacion(self):
        # Mismo objeto con distinto uso de mayúsculas/minúsculas
        # en el nombre de archivo: la clave canónica es la misma.
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls", "Paquetes/fini004.PLS"]
        )
        self.assertTrue(resultado.permitido, resultado.motivo)
        self.assertEqual(self.reservas.llamadas_validar, [CLAVE_FINI004])
        self.assertEqual(resultado.claves, (CLAVE_FINI004,))

    def test_varios_objetos_todos_validan(self):
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls", "Paquetes/FINI005.pls"]
        )
        self.assertTrue(resultado.permitido, resultado.motivo)
        self.assertEqual(
            self.reservas.llamadas_validar,
            [CLAVE_FINI004, CLAVE_FINI005],
        )
        self.assertEqual(
            resultado.claves, (CLAVE_FINI004, CLAVE_FINI005)
        )

    def test_un_objeto_falla_bloquea_operacion_completa(self):
        self.reservas.resultados = {
            CLAVE_FINI004: _resultado(True, "ok"),
            CLAVE_FINI005: _resultado(False, "La reserva esta vencida."),
        }
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls", "Paquetes/FINI005.pls"]
        )
        self.assertFalse(resultado.permitido)
        self.assertEqual(resultado.claves, (CLAVE_FINI005,))
        self.assertIn("vencida", resultado.motivo)
        # Ambos objetos fueron evaluados; el bloqueo es de la
        # operación completa.
        self.assertEqual(len(self.reservas.llamadas_validar), 2)


class TestRenamesProteccion(_BaseProteccion):
    """12.1.16-18: renombrados consideran ambos lados."""

    def test_rename_mismo_objeto_una_reserva(self):
        # Cambio de mayúsculas/minúsculas: origen y destino
        # resuelven al MISMO objeto canónico -> una sola validación.
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI006.pls", "Paquetes/fini006.PLS"]
        )
        self.assertTrue(resultado.permitido, resultado.motivo)
        self.assertEqual(self.reservas.llamadas_validar, [CLAVE_FINI006])

    def test_rename_entre_dos_objetos_dos_reservas(self):
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI006.pls", "Paquetes/FINI007.pls"]
        )
        self.assertTrue(resultado.permitido, resultado.motivo)
        self.assertEqual(
            self.reservas.llamadas_validar,
            [CLAVE_FINI006, CLAVE_FINI007],
        )

    def test_rename_un_lado_no_resoluble_bloqueado(self):
        resultado = self.protector.proteger_commit(
            ["Paquetes/FINI006.pls", "Sospechoso/algo.sql"]
        )
        self.assertFalse(resultado.permitido)
        self.assertIn(
            "No puede determinarse TIPO|NOMBRE", resultado.motivo
        )
        # La protección falla sin llamar a reservas.
        self.assertEqual(self.reservas.llamadas_validar, [])


class TestCeroRed(_BaseProteccion):
    """12.1.19: ninguna API del protector ejecuta red."""

    def test_ninguna_api_ejecuta_red_ni_escritura_reservas(self):
        reservas_espia = mock.Mock(spec=ServicioReservas)
        # Primera llamada (staging FINI004) válida; segunda
        # (commit FINI005) inválida: permite comprobar ambos
        # caminos con el mismo espía.
        reservas_espia.validar_reserva_propia_fresca.side_effect = [
            _resultado(True, "ok"),
            _resultado(False, "No hay una consulta previa verificada."),
        ]

        protector = ServicioProteccionReservasGit(
            resolvedor_oracle=ServicioObjetosOracle(_manifiesto()),
            servicio_reservas=reservas_espia,
        )

        permitido = protector.proteger_staging(
            ["Lecturas/nota.txt", "Paquetes/FINI004.pls"]
        )
        bloqueado = protector.proteger_commit(
            ["Paquetes/FINI005.pls"]
        )

        self.assertTrue(permitido.permitido)
        self.assertFalse(bloqueado.permitido)

        # Ninguna API de ServicioReservas con efecto de red o de
        # escritura de reservas fue invocada (ServicioReservas hace
        # red exclusivamente a traves de estas operaciones).
        reservas_espia.consultar_reserva.assert_not_called()
        reservas_espia.reservar.assert_not_called()
        reservas_espia.renovar.assert_not_called()
        reservas_espia.liberar.assert_not_called()
        reservas_espia.tomar_vencida.assert_not_called()

        # La única API usada es la validación local.
        reservas_espia.validar_reserva_propia_fresca.assert_called_with(
            CLAVE_FINI005
        )


class TestResultadosMalformados(_BaseProteccion):
    """REV1 FIX 3: solo autoriza el resultado contractual estricto."""

    def test_valida_entero_bloqueado(self):
        # Tipo contractual pero valida=1 (truthy, no True):
        # BLOQUEADO; nunca se acepta truthiness.
        self.reservas.resultados = {
            CLAVE_FINI004: _resultado(1, "truthy pero no True")
        }
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.requiere_reserva)

    def test_valida_texto_bloqueado(self):
        self.reservas.resultados = {
            CLAVE_FINI004: _resultado("true", "texto truthy")
        }
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.requiere_reserva)

    def test_objeto_sin_atributo_valida_bloqueado(self):
        self.reservas.resultados = {
            CLAVE_FINI004: types.SimpleNamespace(motivo="sin valida")
        }
        resultado = self.protector.proteger_commit(
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado.permitido)
        self.assertIn("contractual", resultado.motivo)

    def test_objeto_inesperado_con_valida_verdadera_bloqueado(self):
        # Ni siquiera un objeto ajeno con valida=True autoriza:
        # debe ser el resultado contractual de Bloque D.
        self.reservas.resultados = {
            CLAVE_FINI004: types.SimpleNamespace(
                valida=True, motivo="ok"
            )
        }
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado.permitido)
        self.assertIn("contractual", resultado.motivo)

    def test_resultado_none_bloqueado(self):
        self.reservas.resultados = {CLAVE_FINI004: None}
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado.permitido)


class TestMensajesSinExcepcionCruda(_BaseProteccion):
    """REV1 FIX 4: barreras sin str(error)/tracebacks/detalle técnico."""

    def test_excepcion_de_validacion_sin_detalle_tecnico(self):
        secreto = "token-secreto-ficticio"
        with mock.patch.object(
            self.reservas,
            "validar_reserva_propia_fresca",
            side_effect=RuntimeError(secreto),
        ):
            resultado = self.protector.proteger_staging(
                ["Paquetes/FINI004.pls"]
            )
        self.assertFalse(resultado.permitido)
        self.assertIn("inesperada", resultado.motivo)
        self.assertNotIn(secreto, resultado.motivo)
        self.assertNotIn(secreto, resultado.componer_mensaje())
        self.assertNotIn("Detalle técnico", resultado.motivo)

    def test_excepcion_del_resolvedor_sin_detalle_tecnico(self):
        secreto = "token-secreto-ficticio"

        class ResolvedorExplosivo:
            def resolver(self, ruta):
                raise RuntimeError(secreto)

        protector = ServicioProteccionReservasGit(
            resolvedor_oracle=ResolvedorExplosivo(),
            servicio_reservas=self.reservas,
        )
        resultado = protector.proteger_commit(
            ["Paquetes/FINI004.pls"]
        )
        self.assertFalse(resultado.permitido)
        self.assertNotIn(secreto, resultado.motivo)
        self.assertNotIn(secreto, resultado.componer_mensaje())


class TestConstructor(_BaseProteccion):
    """Dependencias inyectadas obligatorias."""

    def test_sin_resolvedor_rechazado(self):
        with self.assertRaises(ValueError):
            ServicioProteccionReservasGit(
                resolvedor_oracle=None,
                servicio_reservas=self.reservas,
            )

    def test_sin_servicio_reservas_rechazado(self):
        with self.assertRaises(ValueError):
            ServicioProteccionReservasGit(
                resolvedor_oracle=ServicioObjetosOracle(_manifiesto()),
                servicio_reservas=None,
            )

    def test_servicio_reservas_sin_api_validar_rechazado(self):
        class SinValidar:
            pass

        with self.assertRaises(ValueError):
            ServicioProteccionReservasGit(
                resolvedor_oracle=ServicioObjetosOracle(_manifiesto()),
                servicio_reservas=SinValidar(),
            )

    def test_resultado_estructura(self):
        resultado = ResultadoProteccionReservasGit.bloquear(
            operacion="staging",
            rutas=("Paquetes/FINI004.pls",),
            claves=(CLAVE_FINI004,),
            motivo="prueba",
            requiere_reserva=True,
        )
        self.assertFalse(resultado.permitido)
        self.assertEqual(resultado.operacion, "staging")
        self.assertIn("prueba", resultado.componer_mensaje())
        self.assertIn("PACKAGE|FINI004", resultado.componer_mensaje())


# =====================================================================
# Integración V1.1 (GG-PROMPT-053-REV1): tipos Oracle .sql
# =====================================================================


def _manifiesto_v11():
    """
    Manifiesto V1.1 con PACKAGE + 6 tipos .sql.
    """

    return ManifiestoProyecto(
        format_version=1,
        project_uuid="11111111-1111-4111-8111-111111111111",
        oracle_layout=(
            ReglaLayoutOracle(
                carpeta="Paquetes",
                tipo="PACKAGE",
                extension=".pls",
            ),
            ReglaLayoutOracle(
                carpeta="Procedimientos",
                tipo="PROCEDURE",
                extension=".sql",
            ),
            ReglaLayoutOracle(
                carpeta="Funciones",
                tipo="FUNCTION",
                extension=".sql",
            ),
            ReglaLayoutOracle(
                carpeta="Tablas",
                tipo="TABLE",
                extension=".sql",
            ),
            ReglaLayoutOracle(
                carpeta="Vistas",
                tipo="VIEW",
                extension=".sql",
            ),
            ReglaLayoutOracle(
                carpeta="Triggers",
                tipo="TRIGGER",
                extension=".sql",
            ),
            ReglaLayoutOracle(
                carpeta="Secuencias",
                tipo="SEQUENCE",
                extension=".sql",
            ),
        ),
    )


CLAVE_PROCEDURE_PR_CERRAR = "PROCEDURE|PR_CERRAR"
CLAVE_VIEW_VW_CLIENTES = "VIEW|VW_CLIENTES"
CLAVE_TABLE_CLIENTES = "TABLE|CLIENTES"


class TestIntegracionTiposSqlV11(unittest.TestCase):
    """
    GG-PROMPT-053-REV1: la barrera de protección no está acoplada
    a PACKAGE; los tipos .sql pasan por el mismo fail-closed vía
    ServicioObjetosOracle (manifiesto V1.1 real, no claves
    inventadas).
    """

    def setUp(self):
        self.reservas = ReservasFalsas(
            valida=True,
            motivo="Reserva propia fresca valida.",
        )
        self.protector = ServicioProteccionReservasGit(
            resolvedor_oracle=ServicioObjetosOracle(_manifiesto_v11()),
            servicio_reservas=self.reservas,
            project_uuid="11111111-1111-4111-8111-111111111111",
        )

    def test_procedure_sql_resuelve_y_exige_reserva(self):
        # La clave llega al servicio de reservas como
        # PROCEDURE|PR_CERRAR: el resolvedor V1.1 la produjo.
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"]
        )
        self.assertTrue(resultado.permitido)
        self.assertEqual(
            [str(c) for c in resultado.claves],
            [CLAVE_PROCEDURE_PR_CERRAR],
        )
        self.assertEqual(
            [str(c) for c in self.reservas.llamadas_validar],
            [CLAVE_PROCEDURE_PR_CERRAR],
        )

    def test_view_sql_segunda_clave_distinta_exige_reserva(self):
        resultado = self.protector.proteger_staging(
            ["Vistas/VW_CLIENTES.sql"]
        )
        self.assertTrue(resultado.permitido)
        self.assertEqual(
            [str(c) for c in resultado.claves],
            [CLAVE_VIEW_VW_CLIENTES],
        )

    def test_tipos_distintos_mismo_nombre_claves_distintas(self):
        # TABLE|CLIENTES y VIEW|CLIENTES... el manifiesto mapea
        # Tablas/ y Vistas/ a tipos distintos.
        r1 = self.protector.proteger_staging(
            ["Tablas/CLIENTES.sql"]
        )
        r2 = self.protector.proteger_staging(
            ["Vistas/CLIENTES.sql"]
        )
        self.assertTrue(r1.permitido)
        self.assertTrue(r2.permitido)
        claves = {str(c) for c in r1.claves} | {str(c) for c in r2.claves}
        self.assertEqual(claves, {CLAVE_TABLE_CLIENTES, "VIEW|CLIENTES"})

    def test_procedure_sql_sin_reserva_bloqueado_fail_closed(self):
        self.reservas.valida = False
        self.reservas.motivo = "Sin reserva propia activa."
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"]
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.requiere_reserva)
        self.assertIn(CLAVE_PROCEDURE_PR_CERRAR, resultado.componer_mensaje())

    def test_view_sql_con_reserva_valida_permitida(self):
        resultado = self.protector.proteger_commit(
            ["Vistas/VW_CLIENTES.sql"]
        )
        self.assertTrue(resultado.permitido)
        self.assertEqual(
            [str(c) for c in self.reservas.llamadas_validar],
            [CLAVE_VIEW_VW_CLIENTES],
        )

    def test_procedure_package_mixto_dos_reservas(self):
        # Un .sql y un .pls en la misma operacion: dos claves
        # distintas, dos validaciones.
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql", "Paquetes/FINI004.pls"]
        )
        self.assertTrue(resultado.permitido)
        self.assertEqual(len(resultado.claves), 2)
        self.assertEqual(
            sorted(str(c) for c in resultado.claves),
            sorted([CLAVE_PROCEDURE_PR_CERRAR, CLAVE_FINI004]),
        )

    def test_pls_en_carpeta_procedure_bloqueado(self):
        # Extensión incorrecta para la carpeta mapeada:
        # Oracle no resoluble -> fail-closed.
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.pls"]
        )
        self.assertFalse(resultado.permitido)


# =====================================================================
# V1.2 (GG-PROMPT-055): validación de contenido SQL ↔ archivo
# =====================================================================


def _manifiesto_v12():
    return ManifiestoProyecto(
        format_version=1,
        project_uuid="44444444-4444-4444-8444-444444444444",
        oracle_layout=(
            ReglaLayoutOracle(
                carpeta="Paquetes",
                tipo="PACKAGE",
                extension=".pls",
            ),
            ReglaLayoutOracle(
                carpeta="Procedimientos",
                tipo="PROCEDURE",
                extension=".sql",
            ),
        ),
    )


class _BaseProteccionV12(unittest.TestCase):
    """
    Protector con la segunda evidencia V1.2 inyectada: el
    contenido debe concordar con la identidad de la ruta además
    de la reserva. Reservas válidas por defecto.
    """

    def setUp(self):
        self.reservas = ReservasFalsas(
            valida=True,
            motivo="Reserva propia fresca valida.",
        )
        self.validador = ServicioValidacionContenidoOracle()
        self.protector = ServicioProteccionReservasGit(
            resolvedor_oracle=ServicioObjetosOracle(
                _manifiesto_v12()
            ),
            servicio_reservas=self.reservas,
            project_uuid="44444444-4444-4444-8444-444444444444",
            validador_contenido=self.validador,
        )


class TestProteccionContenidoV12(_BaseProteccionV12):
    """Concordancia contenido ↔ ruta en staging/commit."""

    def test_contenido_correcto_y_reserva_valida_permitido(self):
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": (
                    b"CREATE OR REPLACE PROCEDURE PR_CERRAR "
                    b"IS NULL;\n"
                )
            },
        )
        self.assertTrue(resultado.permitido, resultado.motivo)
        self.assertFalse(resultado.bloqueo_contenido)

    def test_nombre_incorrecto_bloqueado_por_contenido(self):
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": (
                    b"CREATE PROCEDURE PR_ABRIR IS NULL;\n"
                )
            },
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)
        self.assertFalse(resultado.requiere_reserva)
        self.assertIn("no coincide", resultado.motivo)

    def test_tipo_incorrecto_bloqueado_por_contenido(self):
        resultado = self.protector.proteger_commit(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": (
                    b"CREATE FUNCTION PR_CERRAR RETURN NUMBER "
                    b"IS NULL;\n"
                )
            },
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)
        self.assertIn("tipo", resultado.motivo)

    def test_ambiguo_bloqueado_por_contenido(self):
        resultado = self.protector.proteger_staging(
            ["Paquetes/FINI004.pls"],
            contenido_por_ruta={
                "Paquetes/FINI004.pls": (
                    b"CREATE PACKAGE FINI004 IS END;\n"
                    b"CREATE PACKAGE OTRO IS END;\n"
                )
            },
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)

    def test_no_verificable_bloqueado_por_contenido(self):
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": b"SELECT 1;\n"
            },
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)

    def test_eliminacion_origen_explicito_no_aplica(self):
        """None explícito en el mapeo de una ruta Oracle recibe
        NO_APLICA (eliminación/lado origen demostrado)."""

        resultado = self.protector.proteger_commit(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": None
            },
        )
        self.assertTrue(resultado.permitido, resultado.motivo)

    def test_ruta_oracle_ausente_del_mapeo_bloqueado(self):
        """Con validador activo, una ruta Oracle reservable que no
        aparece en el mapeo BLOQUEA (fail-closed REV1 R4)."""

        resultado = self.protector.proteger_commit(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={},
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)
        self.assertIn("No fue suministrado", resultado.motivo)

    def test_contenido_por_ruta_none_bloqueado(self):
        """contenido_por_ruta=None con validador activo BLOQUEA
        (fail-closed REV1 R4)."""

        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)
        self.assertIn("no fue suministrado", resultado.motivo.lower())

    def test_contenido_no_bytes_bloqueado(self):
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": "texto suelto"
            },
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)

    def test_mapeo_no_diccionario_bloqueado(self):
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta=[
                ("Procedimientos/PR_CERRAR.sql", b"x")
            ],
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)

    def test_validador_resultado_no_contractual_bloqueado(self):
        protector = ServicioProteccionReservasGit(
            resolvedor_oracle=ServicioObjetosOracle(
                _manifiesto_v12()
            ),
            servicio_reservas=self.reservas,
            project_uuid="44444444-4444-4444-8444-444444444444",
            validador_contenido=types.SimpleNamespace(
                validar=lambda clave, contenido: "ok"
            ),
        )

        resultado = protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": b"CREATE X;"
            },
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)

    def test_validador_con_excepcion_bloqueado_sin_detalle(self):
        secreto = "token-ficticio-123"

        class ValidadorQueExplota:
            def validar(self, clave, contenido):
                raise RuntimeError(secreto)

        protector = ServicioProteccionReservasGit(
            resolvedor_oracle=ServicioObjetosOracle(
                _manifiesto_v12()
            ),
            servicio_reservas=self.reservas,
            project_uuid="44444444-4444-4444-8444-444444444444",
            validador_contenido=ValidadorQueExplota(),
        )

        resultado = protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": b"CREATE X;"
            },
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.bloqueo_contenido)
        self.assertNotIn(secreto, resultado.componer_mensaje())

    def test_ruta_ordinaria_ignora_mapeo(self):
        """Una ruta no Oracle con contenido en el mapeo no
        participa de la validación de contenido."""

        resultado = self.protector.proteger_staging(
            ["Lecturas/nota.txt"],
            contenido_por_ruta={
                "Lecturas/nota.txt": b"CREATE PROCEDURE X;"
            },
        )
        self.assertTrue(resultado.permitido, resultado.motivo)

    def test_reserva_y_contenido_se_validan_ambas(self):
        """Contenido correcto pero reserva inválida: bloqueo por
        reserva (la validación de contenido no la sustituye)."""

        self.reservas.valida = False
        self.reservas.motivo = "Sin reserva propia activa."

        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": (
                    b"CREATE PROCEDURE PR_CERRAR IS NULL;\n"
                )
            },
        )
        self.assertFalse(resultado.permitido)
        self.assertTrue(resultado.requiere_reserva)
        self.assertFalse(resultado.bloqueo_contenido)

    def test_sin_validador_inyectado_semantica_v11(self):
        """Sin validador el protector conserva V1.1: un contenido
        contradictorio NO bloquea si la reserva es válida."""

        protector_v11 = ServicioProteccionReservasGit(
            resolvedor_oracle=ServicioObjetosOracle(
                _manifiesto_v12()
            ),
            servicio_reservas=self.reservas,
            project_uuid="44444444-4444-4444-8444-444444444444",
        )

        resultado = protector_v11.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": (
                    b"CREATE PROCEDURE PR_ABRIR IS NULL;\n"
                )
            },
        )
        self.assertTrue(resultado.permitido, resultado.motivo)

    def test_constructor_rechaza_validador_sin_validar(self):
        with self.assertRaises(ValueError):
            ServicioProteccionReservasGit(
                resolvedor_oracle=ServicioObjetosOracle(
                    _manifiesto_v12()
                ),
                servicio_reservas=self.reservas,
                project_uuid="x",
                validador_contenido=types.SimpleNamespace(),
            )

    def test_mensaje_bloqueo_contenido_pedagogico(self):
        resultado = self.protector.proteger_staging(
            ["Procedimientos/PR_CERRAR.sql"],
            contenido_por_ruta={
                "Procedimientos/PR_CERRAR.sql": (
                    b"CREATE PROCEDURE PR_ABRIR IS NULL;\n"
                )
            },
        )

        mensaje = resultado.componer_mensaje()

        self.assertIn("validación de contenido", mensaje)
        self.assertIn("Procedimientos/PR_CERRAR.sql", mensaje)
        self.assertIn("PROCEDURE|PR_CERRAR", mensaje)
        self.assertNotIn("Traceback", mensaje)


if __name__ == "__main__":
    unittest.main()
