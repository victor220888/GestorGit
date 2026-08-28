"""
Pruebas de ServicioReservas (Bloque D): maquina de estados,
reconciliacion por operation_id y coordinador/mutex de red.

Usan TemporaryDirectory y repositorios Git bare LOCALES temporales
como remoto. No usan internet, no tocan APPDATA real, no tocan el
repositorio Oracle productivo y no modifican Git global/system.

Cobertura 16.3 (1-32) y 16.4 (mutex).

REV3 §9: mutex atomico probado con hilos reales (Barrier/Thread).
REV3 §10: reintentos completos con el MISMO operation_id para
reservar/renovar/liberar/tomar_vencida, reconocidos como exito
idempotente sin crear otro commit.
"""

import os
import subprocess
import tempfile
import threading
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from modelos_reservas import (
    ClasificacionReservaObservada,
    EstadoReservaPersistido,
    ReservaPayloadV1,
    ResultadoConsultaReserva,
    ahora_utc,
    calcular_ref_reserva,
    formatear_timestamp_utc,
)
from servicio_remoto_reservas import (
    REFSPEC_RESERVAS_V1,
    ResultadoLecturaReserva,
    ResultadoPublicacionReserva,
    ServicioRemotoReservas,
)
from servicio_reservas import (
    CoordinadorOperacionesRed,
    ServicioReservas,
)


def _uuid4():
    return str(uuid.uuid4())


def _proyecto_uuid():
    return _uuid4()


def _clave():
    return "PACKAGE|FINI004"


class _RelojFalso:
    """Reloj UTC inyectable y controlable para pruebas."""

    def __init__(self, inicio):
        self.tiempo = inicio

    def __call__(self):
        return self.tiempo

    def avanzar(self, segundos):
        self.tiempo = self.tiempo + timedelta(seconds=segundos)


class _BaseServicioReservas(unittest.TestCase):
    """Base con remoto local temporal y dos clientes."""

    TTL = 1800
    RENOVACION = 600
    MARGEN_MINIMO = 300
    FRESCURA = 60
    GRACE = 600

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.remoto = self.base / "remoto.git"
        self.backend = self.base / "backend.git"

        # Aislamiento de configuracion Git desde ANTES del primer
        # comando Git del test: GIT_CONFIG_GLOBAL temporal y
        # GIT_CONFIG_NOSYSTEM=1 activos en os.environ, de modo que
        # git init/remote add/config, los fixtures y TODAS las
        # llamadas al servicio hereden ese entorno aislado. Se
        # restaura al terminar la prueba.
        self.global_temp = self.base / "config_global_temporal"
        self.global_temp.write_text("", encoding="utf-8")
        parche_entorno = mock.patch.dict(
            os.environ,
            {
                "GIT_CONFIG_GLOBAL": str(self.global_temp),
                "GIT_CONFIG_NOSYSTEM": "1",
            },
        )
        parche_entorno.start()
        self.addCleanup(parche_entorno.stop)
        self.entorno = dict(os.environ)

        subprocess.run(
            ["git", "init", "--bare", str(self.remoto)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, shell=False, check=True,
            env=self.entorno,
        )
        subprocess.run(
            ["git", "init", "--bare", str(self.backend)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, shell=False, check=True,
            env=self.entorno,
        )
        subprocess.run(
            ["git", "-C", str(self.backend),
             "remote", "add", "origin", str(self.remoto)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, shell=False, check=True,
            env=self.entorno,
        )
        subprocess.run(
            ["git", "-C", str(self.backend),
             "config", "--replace-all",
             "remote.origin.fetch", REFSPEC_RESERVAS_V1],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, shell=False, check=True,
            env=self.entorno,
        )

        self.remoto_servicio = ServicioRemotoReservas(
            ruta_backend=str(self.backend)
        )
        self.id_a = _uuid4()
        self.id_b = _uuid4()
        self.inicio = datetime.now(timezone.utc).replace(microsecond=0)
        self.reloj = _RelojFalso(self.inicio)

        self.servicio_a = ServicioReservas(
            remoto=self.remoto_servicio,
            id_cliente=self.id_a,
            alias="equipo",
            hostname="pc-a",
            user_name="ana",
            reloj=self.reloj,
            ttl_segundos=self.TTL,
            renovacion_segundos=self.RENOVACION,
            margen_minimo_segundos=self.MARGEN_MINIMO,
            frescura_segundos=self.FRESCURA,
            margen_gracia_segundos=self.GRACE,
        )
        self.servicio_b = ServicioReservas(
            remoto=self.remoto_servicio,
            id_cliente=self.id_b,
            alias="equipo",
            hostname="pc-b",
            user_name="bruno",
            reloj=self.reloj,
            ttl_segundos=self.TTL,
            renovacion_segundos=self.RENOVACION,
            margen_minimo_segundos=self.MARGEN_MINIMO,
            frescura_segundos=self.FRESCURA,
            margen_gracia_segundos=self.GRACE,
        )

    def tearDown(self):
        self.temporal.cleanup()

    def _git_remoto(self, *argumentos):
        resultado = subprocess.run(
            ["git", "-C", str(self.remoto)] + list(argumentos),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, shell=False,
            env=self.entorno,
        )
        return resultado

    def _ref_heads(self, proyecto, clave):
        return (
            "refs/heads/gestorgit-reservas/"
            + calcular_ref_reserva(proyecto, clave)
        )

    def _payload_dict(
        self, proyecto, clave, estado="ACTIVA",
        id_cliente=None, operation_id=None, ahora=None,
    ):
        """Payload V1 valido como dict para montar lecturas."""

        if ahora is None:
            ahora = self.reloj()
        if estado == "LIBERADA":
            vencimiento = ahora
        else:
            vencimiento = ahora + timedelta(seconds=self.TTL)
        return {
            "format_version": 1,
            "operation_id": operation_id or _uuid4(),
            "project_uuid": proyecto,
            "clave_objeto": clave,
            "estado": estado,
            "id_cliente": id_cliente or _uuid4(),
            "alias": "equipo",
            "hostname": "pc-x",
            "user_name": "x",
            "inicio": formatear_timestamp_utc(ahora),
            "heartbeat": formatear_timestamp_utc(ahora),
            "vencimiento": formatear_timestamp_utc(vencimiento),
            "rama_local": "",
            "rutas": ["Paquetes/FINI004.pls"],
        }


class TestMaquinaReservas(_BaseServicioReservas):
    """16.3.1-3: reservar libre, consultar propia/ajena."""

    def test_reservar_objeto_libre(self):
        proyecto = _proyecto_uuid()
        resultado = self.servicio_a.reservar(proyecto, _clave())
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertEqual(resultado.operacion, "reservar")
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_MI,
        )
        # Ref creada en el remoto con 1 commit.
        salida = self._git_remoto(
            "show-ref", self._ref_heads(proyecto, _clave())
        )
        self.assertTrue(salida.stdout.strip())

    def test_consultar_propia_vigente(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        consulta = self.servicio_a.consultar_reserva(
            proyecto, _clave()
        )
        self.assertTrue(consulta.exitoso)
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_MI,
        )

    def test_consultar_ajena_vigente(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        consulta = self.servicio_b.consultar_reserva(
            proyecto, _clave()
        )
        self.assertTrue(consulta.exitoso)
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_OTRO,
        )


class TestCarrera(_BaseServicioReservas):
    """16.3.4-6: competencia entre dos clientes."""

    def test_dos_clientes_compiten_uno_gana(self):
        proyecto = _proyecto_uuid()
        resultado_a = self.servicio_a.reservar(proyecto, _clave())
        self.assertTrue(resultado_a.exitoso, resultado_a.error)

        # B ve la reserva ajena y queda bloqueado sin forzar.
        resultado_b = self.servicio_b.reservar(proyecto, _clave())
        self.assertFalse(resultado_b.exitoso)
        self.assertIs(
            resultado_b.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_OTRO,
        )
        self.assertIn("BLOQUEADO", resultado_b.mensaje)

    def test_perdedor_reconsulta_y_no_fuerza(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        # B: lectura previa simulada como LIBRE (no vio nada),
        # su push real falla (non-fast-forward) y reconsulta.
        real_leer = self.remoto_servicio.leer_head_reserva

        def leer_side(
            project_uuid, clave_objeto, id_cliente_local="",
            ttl_segundos=1800, ahora=None,
        ):
            if not hasattr(leer_side, "n"):
                leer_side.n = 0
            leer_side.n += 1
            if leer_side.n == 1:
                return ResultadoLecturaReserva(
                    exitoso=True,
                    clasificacion=ClasificacionReservaObservada.LIBRE,
                )
            return real_leer(
                project_uuid, clave_objeto, id_cliente_local,
                ttl_segundos, ahora,
            )

        with mock.patch.object(
            self.remoto_servicio, "leer_head_reserva",
            side_effect=leer_side,
        ):
            resultado_b = self.servicio_b.reservar(
                proyecto, _clave()
            )
        self.assertFalse(resultado_b.exitoso)
        # El perdedor no fuerza: el head real sigue siendo de A.
        consulta = self.servicio_b.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_OTRO,
        )

    def test_dos_clientes_reservan_objetos_distintos(self):
        proyecto = _proyecto_uuid()
        r1 = self.servicio_a.reservar(proyecto, "PACKAGE|FINI004")
        r2 = self.servicio_b.reservar(proyecto, "PACKAGE|FINI005")
        self.assertTrue(r1.exitoso, r1.error)
        self.assertTrue(r2.exitoso, r2.error)


class TestRenovar(_BaseServicioReservas):
    """16.3.7-9: renovar propia, ajena bloqueada, propia vencida."""

    def test_renovar_propia_vigente(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        consulta = self.servicio_a.consultar_reserva(
            proyecto, _clave()
        )
        inicio_original = consulta.payload.inicio
        self.reloj.avanzar(300)
        resultado = self.servicio_a.renovar(proyecto, _clave())
        self.assertTrue(resultado.exitoso, resultado.error)
        consulta2 = self.servicio_a.consultar_reserva(
            proyecto, _clave()
        )
        self.assertEqual(consulta2.payload.inicio, inicio_original)
        self.assertNotEqual(
            consulta2.payload.heartbeat, consulta.payload.heartbeat
        )

    def test_renovar_ajena_bloqueada(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        resultado = self.servicio_b.renovar(proyecto, _clave())
        self.assertFalse(resultado.exitoso)
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_OTRO,
        )

    def test_renovar_propia_vencida_bloqueada(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.reloj.avanzar(self.TTL + 100)  # vencida
        resultado = self.servicio_a.renovar(proyecto, _clave())
        self.assertFalse(resultado.exitoso)
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.VENCIDO_PROPIO,
        )
        self.assertIn("tomar_vencida", resultado.mensaje)


class TestLiberar(_BaseServicioReservas):
    """16.3.10-13: liberar, ajena bloqueada, ref conservada."""

    def test_liberar_propia(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        resultado = self.servicio_a.liberar(proyecto, _clave())
        self.assertTrue(resultado.exitoso, resultado.error)
        # Ref sigue existiendo con estado LIBERADA.
        salida = self._git_remoto(
            "show-ref", self._ref_heads(proyecto, _clave())
        )
        self.assertTrue(salida.stdout.strip())
        consulta = self.servicio_b.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.LIBRE,
        )
        self.assertIsNotNone(consulta.payload)
        self.assertTrue(consulta.payload.es_liberada())

    def test_liberar_ajena_bloqueada(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        resultado = self.servicio_b.liberar(proyecto, _clave())
        self.assertFalse(resultado.exitoso)
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_OTRO,
        )

    def test_ref_liberada_sigue_existiendo(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.servicio_a.liberar(proyecto, _clave())
        salida = self._git_remoto(
            "for-each-ref",
            "refs/heads/gestorgit-reservas/"
            + calcular_ref_reserva(proyecto, _clave()),
        )
        self.assertTrue(salida.stdout.strip())

    def test_reservar_despues_de_liberada(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.servicio_a.liberar(proyecto, _clave())
        resultado = self.servicio_b.reservar(proyecto, _clave())
        self.assertTrue(resultado.exitoso, resultado.error)
        consulta = self.servicio_b.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_MI,
        )


class TestTomarVencida(_BaseServicioReservas):
    """16.3.14-16: grace y toma de vencidas."""

    def test_tomar_vencida_antes_de_grace_bloqueada(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.reloj.avanzar(self.TTL + 100)  # vencida pero < grace
        resultado = self.servicio_b.tomar_vencida(
            proyecto, _clave()
        )
        self.assertFalse(resultado.exitoso)
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.VENCIDO_AJENO,
        )
        self.assertIn("gracia", resultado.mensaje)

    def test_tomar_vencida_despues_de_grace_exito(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.reloj.avanzar(self.TTL + self.GRACE + 100)
        resultado = self.servicio_b.tomar_vencida(
            proyecto, _clave()
        )
        self.assertTrue(resultado.exitoso, resultado.error)
        consulta = self.servicio_b.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_MI,
        )

    def test_vencida_propia_tampoco_autoriza(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.reloj.avanzar(self.TTL + self.GRACE + 100)
        # La reserva vencida propia no autoriza la validacion local.
        validacion = self.servicio_a.validar_reserva_propia_fresca(
            _clave()
        )
        self.assertFalse(validacion.valida)


class TestPropiedad(_BaseServicioReservas):
    """16.3.17-18: propiedad por id_cliente exclusivamente."""

    def test_mismo_alias_distinto_id_clientes_distintos(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        # B tiene el mismo alias pero distinto id_cliente.
        consulta = self.servicio_b.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_OTRO,
        )

    def test_mismo_id_cliente_alias_distinto_mismo_propietario(self):
        proyecto = _proyecto_uuid()
        servicio_b_mismo_id = ServicioReservas(
            remoto=self.remoto_servicio,
            id_cliente=self.id_a,  # mismo id_cliente
            alias="otro-alias",
            hostname="pc-otro",
            user_name="otro",
            reloj=self.reloj,
            ttl_segundos=self.TTL,
        )
        self.servicio_a.reservar(proyecto, _clave())
        consulta = servicio_b_mismo_id.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_MI,
        )


class TestReconciliacion(_BaseServicioReservas):
    """16.3.19-23: idempotencia y reconciliacion por operation_id."""

    def test_reintento_mismo_operation_id_idempotente(self):
        proyecto = _proyecto_uuid()
        op_fijo = _uuid4()
        servicio_fijo = ServicioReservas(
            remoto=self.remoto_servicio,
            id_cliente=self.id_a,
            alias="equipo",
            hostname="pc-a",
            user_name="ana",
            reloj=self.reloj,
            operation_id_proveedor=lambda: op_fijo,
            ttl_segundos=self.TTL,
        )
        r1 = servicio_fijo.reservar(proyecto, _clave())
        self.assertTrue(r1.exitoso, r1.error)
        # Reintento con el mismo operation_id: el estado ya es
        # RESERVADO_POR_MI y no se crea un commit nuevo.
        r2 = servicio_fijo.reservar(proyecto, _clave())
        self.assertTrue(r2.exitoso, r2.error)
        salida = self._git_remoto(
            "rev-list", "--count",
            self._ref_heads(proyecto, _clave()),
        )
        self.assertEqual(salida.stdout.strip(), "1")

    def test_push_aplicado_pero_error_simulado_reconciliado(self):
        proyecto = _proyecto_uuid()
        real_publicar = self.remoto_servicio.publicar_reserva

        def publicar_falso(oid, project_uuid, clave):
            real_publicar(oid, project_uuid, clave)  # aplica
            return ResultadoPublicacionReserva(
                exitoso=False, oid=oid,
                mensaje="simulado", error="simulado",
            )

        with mock.patch.object(
            self.remoto_servicio, "publicar_reserva",
            side_effect=publicar_falso,
        ):
            resultado = self.servicio_a.reservar(
                proyecto, _clave()
            )
        self.assertTrue(resultado.exitoso, resultado.error)
        self.assertIn("reconciliado", resultado.mensaje)

    def test_push_fallido_otro_head_carrera_perdida(self):
        proyecto = _proyecto_uuid()
        # A reserva primero.
        self.servicio_a.reservar(proyecto, _clave())
        # B con lectura previa LIBRE y push fallido real.
        real_leer = self.remoto_servicio.leer_head_reserva

        def leer_side(
            project_uuid, clave_objeto, id_cliente_local="",
            ttl_segundos=1800, ahora=None,
        ):
            if not hasattr(leer_side, "n"):
                leer_side.n = 0
            leer_side.n += 1
            if leer_side.n == 1:
                return ResultadoLecturaReserva(
                    exitoso=True,
                    clasificacion=ClasificacionReservaObservada.LIBRE,
                )
            return real_leer(
                project_uuid, clave_objeto, id_cliente_local,
                ttl_segundos, ahora,
            )

        with mock.patch.object(
            self.remoto_servicio, "leer_head_reserva",
            side_effect=leer_side,
        ):
            resultado = self.servicio_b.reservar(
                proyecto, _clave()
            )
        self.assertFalse(resultado.exitoso)
        self.assertIn("carrera perdida", resultado.mensaje)

    def test_push_fallido_fetch_imposible_resultado_incierto(self):
        proyecto = _proyecto_uuid()
        with mock.patch.object(
            self.remoto_servicio, "publicar_reserva",
            return_value=ResultadoPublicacionReserva(
                exitoso=False, oid="x",
                mensaje="fallo", error="fallo",
            ),
        ):
            with mock.patch.object(
                self.remoto_servicio, "fetch_reservas",
                side_effect=[(True, "ok"), (False, "fetch imposible")],
            ):
                resultado = self.servicio_a.reservar(
                    proyecto, _clave()
                )
        self.assertFalse(resultado.exitoso)
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.RESULTADO_INCIERTO,
        )

    def test_operation_id_coincidente_payload_incompatible(self):
        proyecto = _proyecto_uuid()
        op_fijo = _uuid4()
        # Payload con el mismo operation_id pero clave_objeto distinta.
        payload_incompatible = ReservaPayloadV1(
            format_version=1,
            operation_id=op_fijo,
            project_uuid=proyecto,
            clave_objeto="PACKAGE|OTRO",
            estado=EstadoReservaPersistido.ACTIVA,
            id_cliente=self.id_a,
            alias="equipo",
            hostname="pc-a",
            user_name="ana",
            inicio=formatear_timestamp_utc(self.reloj()),
            heartbeat=formatear_timestamp_utc(self.reloj()),
            vencimiento=formatear_timestamp_utc(
                self.reloj() + timedelta(seconds=self.TTL)
            ),
            rama_local="",
            rutas=(),
        )
        real_leer = self.remoto_servicio.leer_head_reserva

        def leer_side(
            project_uuid, clave_objeto, id_cliente_local="",
            ttl_segundos=1800, ahora=None,
        ):
            if not hasattr(leer_side, "n"):
                leer_side.n = 0
            leer_side.n += 1
            if leer_side.n == 1:
                return ResultadoLecturaReserva(
                    exitoso=True,
                    clasificacion=ClasificacionReservaObservada.LIBRE,
                )
            return ResultadoLecturaReserva(
                exitoso=True,
                clasificacion=(
                    ClasificacionReservaObservada.RESERVADO_POR_MI
                ),
                head_existe=True,
                payload=payload_incompatible,
                parent="x",
            )

        servicio_op = ServicioReservas(
            remoto=self.remoto_servicio,
            id_cliente=self.id_a,
            alias="equipo",
            hostname="pc-a",
            user_name="ana",
            reloj=self.reloj,
            operation_id_proveedor=lambda: op_fijo,
            ttl_segundos=self.TTL,
        )
        with mock.patch.object(
            self.remoto_servicio, "leer_head_reserva",
            side_effect=leer_side,
        ):
            resultado = servicio_op.reservar(proyecto, _clave())
        self.assertFalse(resultado.exitoso)
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )


class TestBackendNoVerificable(_BaseServicioReservas):
    """16.3.24: backend no verificable nunca es LIBRE."""

    def test_fetch_fallido_consulta_no_verificable(self):
        proyecto = _proyecto_uuid()
        with mock.patch.object(
            self.remoto_servicio, "fetch_reservas",
            return_value=(False, "fetch fallo"),
        ):
            consulta = self.servicio_a.consultar_reserva(
                proyecto, _clave()
            )
        self.assertFalse(consulta.exitoso)
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )

    def test_head_corrupto_nunca_libre(self):
        proyecto = _proyecto_uuid()
        with mock.patch.object(
            self.remoto_servicio, "leer_head_reserva",
            return_value=ResultadoLecturaReserva(
                exitoso=False,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                mensaje="corrupto",
                error="corrupto",
            ),
        ):
            consulta = self.servicio_a.consultar_reserva(
                proyecto, _clave()
            )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )


class TestValidacionLocal(_BaseServicioReservas):
    """16.3.25-31: cache, frescura, margen, incierto, mutex."""

    def _reservar_propia(self, proyecto):
        resultado = self.servicio_a.reservar(proyecto, _clave())
        self.assertTrue(resultado.exitoso, resultado.error)

    def test_cache_libre_nunca_autoriza(self):
        proyecto = _proyecto_uuid()
        consulta = self.servicio_a.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.LIBRE,
        )
        validacion = self.servicio_a.validar_reserva_propia_fresca(
            _clave()
        )
        self.assertFalse(validacion.valida)

    def test_propia_fresca_valida(self):
        proyecto = _proyecto_uuid()
        self._reservar_propia(proyecto)
        validacion = self.servicio_a.validar_reserva_propia_fresca(
            _clave()
        )
        self.assertTrue(validacion.valida, validacion.motivo)
        self.assertGreaterEqual(validacion.tiempo_restante, self.MARGEN_MINIMO)

    def test_cache_mas_de_60s_bloqueada(self):
        proyecto = _proyecto_uuid()
        self._reservar_propia(proyecto)
        self.reloj.avanzar(120)  # > frescura 60 s
        validacion = self.servicio_a.validar_reserva_propia_fresca(
            _clave()
        )
        self.assertFalse(validacion.valida)
        self.assertIn("frescura", validacion.motivo)

    def test_margen_menor_300s_bloqueada(self):
        proyecto = _proyecto_uuid()
        self._reservar_propia(proyecto)
        # Deja restante 250 s (< margen 300 s), aun fresca.
        self.reloj.avanzar(self.TTL - 250)
        validacion = self.servicio_a.validar_reserva_propia_fresca(
            _clave()
        )
        self.assertFalse(validacion.valida)
        self.assertIn("margen", validacion.motivo)

    def test_reserva_vencida_bloqueada(self):
        proyecto = _proyecto_uuid()
        self._reservar_propia(proyecto)
        self.reloj.avanzar(self.TTL + 1)
        validacion = self.servicio_a.validar_reserva_propia_fresca(
            _clave()
        )
        self.assertFalse(validacion.valida)
        self.assertIn("vencida", validacion.motivo)

    def test_resultado_incierto_bloqueada(self):
        proyecto = _proyecto_uuid()
        self._reservar_propia(proyecto)
        self.servicio_a._cache[_clave()] = type(
            self.servicio_a._cache[_clave()]
        )(
            clasificacion=(
                ClasificacionReservaObservada.RESULTADO_INCIERTO
            ),
            payload=None,
            parent="",
            verificacion=self.reloj(),
        )
        validacion = self.servicio_a.validar_reserva_propia_fresca(
            _clave()
        )
        self.assertFalse(validacion.valida)

    def test_operacion_en_curso_bloquea_validacion(self):
        proyecto = _proyecto_uuid()
        self._reservar_propia(proyecto)
        self.servicio_a.coordinador.operacion_reservas_en_curso = True
        try:
            validacion = (
                self.servicio_a.validar_reserva_propia_fresca(
                    _clave()
                )
            )
        finally:
            self.servicio_a.coordinador.operacion_reservas_en_curso = False
        self.assertFalse(validacion.valida)


class TestDebeRenovar(_BaseServicioReservas):
    """16.3.32: politica determinista de renovacion."""

    def test_debe_renovar_antes_y_despues_de_600s(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.servicio_a.consultar_reserva(proyecto, _clave())
        # Al inicio quedan 1800 s > 600 s: no renovar.
        self.assertFalse(self.servicio_a.debe_renovar(_clave()))
        # Con 500 s restantes (< 600 s): renovar.
        self.reloj.avanzar(self.TTL - 500)
        self.assertTrue(self.servicio_a.debe_renovar(_clave()))

    def test_debe_renovar_falso_sin_reserva(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.consultar_reserva(proyecto, _clave())
        self.assertFalse(self.servicio_a.debe_renovar(_clave()))


class TestMutexRed(_BaseServicioReservas):
    """16.4: coordinador/mutex de red."""

    def test_reservas_vs_reservas(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.coordinador.operacion_reservas_en_curso = True
        try:
            with mock.patch.object(
                self.remoto_servicio, "fetch_reservas",
                side_effect=AssertionError("no debe ejecutar Git"),
            ) as fetch:
                resultado = self.servicio_a.reservar(
                    proyecto, _clave()
                )
                fetch.assert_not_called()
        finally:
            self.servicio_a.coordinador.operacion_reservas_en_curso = False
        self.assertFalse(resultado.exitoso)
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.OPERACION_EN_CURSO,
        )

    def test_remota_vs_reservas(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.coordinador.operacion_remota_en_curso = True
        try:
            with mock.patch.object(
                self.remoto_servicio, "fetch_reservas",
                side_effect=AssertionError("no debe ejecutar Git"),
            ) as fetch:
                consulta = self.servicio_a.consultar_reserva(
                    proyecto, _clave()
                )
                fetch.assert_not_called()
        finally:
            self.servicio_a.coordinador.operacion_remota_en_curso = False
        self.assertFalse(consulta.exitoso)
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.OPERACION_EN_CURSO,
        )

    def test_reservas_vs_remota(self):
        coordinador = CoordinadorOperacionesRed()
        coordinador.operacion_reservas_en_curso = True
        self.assertFalse(coordinador.intentar_iniciar_remota())
        coordinador.finalizar_reservas()
        self.assertTrue(coordinador.intentar_iniciar_remota())
        coordinador.finalizar_remota()

    def test_liberacion_flag_tras_exito(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.assertFalse(
            self.servicio_a.coordinador.operacion_reservas_en_curso
        )

    def test_liberacion_flag_tras_error(self):
        proyecto = _proyecto_uuid()
        with mock.patch.object(
            self.remoto_servicio, "fetch_reservas",
            return_value=(False, "fallo"),
        ):
            self.servicio_a.consultar_reserva(proyecto, _clave())
        self.assertFalse(
            self.servicio_a.coordinador.operacion_reservas_en_curso
        )

    def test_liberacion_flag_tras_excepcion(self):
        proyecto = _proyecto_uuid()
        with mock.patch.object(
            self.remoto_servicio, "fetch_reservas",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                self.servicio_a.consultar_reserva(
                    proyecto, _clave()
                )
        self.assertFalse(
            self.servicio_a.coordinador.operacion_reservas_en_curso
        )


class TestIdempotenciaReintentos(_BaseServicioReservas):
    """REV3 §10: reintentos completos con el MISMO operation_id.

    El segundo intento del mismo intento logico reconoce que ya fue
    aplicado: no incrementa el numero de commits, no cambia el
    propietario y no publica un nuevo estado.
    """

    def _conteo_commits(self, proyecto, clave):
        salida = self._git_remoto(
            "rev-list", "--count",
            self._ref_heads(proyecto, clave),
        )
        return salida.stdout.strip()

    def test_reintento_reservar_mismo_operation_id(self):
        proyecto = _proyecto_uuid()
        op = _uuid4()
        r1 = self.servicio_a.reservar(
            proyecto, _clave(), operation_id=op
        )
        self.assertTrue(r1.exitoso, r1.error)
        self.assertEqual(
            self._conteo_commits(proyecto, _clave()), "1"
        )
        r2 = self.servicio_a.reservar(
            proyecto, _clave(), operation_id=op
        )
        self.assertTrue(r2.exitoso, r2.error)
        self.assertEqual(r2.operacion, "idempotencia")
        self.assertEqual(
            self._conteo_commits(proyecto, _clave()), "1"
        )
        consulta = self.servicio_a.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_MI,
        )
        self.assertEqual(consulta.payload.operation_id, op)

    def test_reintento_renovar_mismo_operation_id(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.reloj.avanzar(100)
        op = _uuid4()
        r1 = self.servicio_a.renovar(
            proyecto, _clave(), operation_id=op
        )
        self.assertTrue(r1.exitoso, r1.error)
        self.assertEqual(
            self._conteo_commits(proyecto, _clave()), "2"
        )
        self.reloj.avanzar(100)
        r2 = self.servicio_a.renovar(
            proyecto, _clave(), operation_id=op
        )
        self.assertTrue(r2.exitoso, r2.error)
        self.assertEqual(r2.operacion, "idempotencia")
        self.assertEqual(
            self._conteo_commits(proyecto, _clave()), "2"
        )
        consulta = self.servicio_a.consultar_reserva(
            proyecto, _clave()
        )
        self.assertEqual(consulta.payload.operation_id, op)
        self.assertEqual(consulta.payload.id_cliente, self.id_a)

    def test_reintento_liberar_mismo_operation_id(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        op = _uuid4()
        r1 = self.servicio_a.liberar(
            proyecto, _clave(), operation_id=op
        )
        self.assertTrue(r1.exitoso, r1.error)
        self.assertEqual(
            self._conteo_commits(proyecto, _clave()), "2"
        )
        # Reintento: el head ya es LIBERADA (funcionalmente LIBRE);
        # debe reconocer la operacion aplicada, no fallar.
        r2 = self.servicio_a.liberar(
            proyecto, _clave(), operation_id=op
        )
        self.assertTrue(r2.exitoso, r2.error)
        self.assertEqual(r2.operacion, "idempotencia")
        self.assertEqual(
            self._conteo_commits(proyecto, _clave()), "2"
        )
        consulta = self.servicio_b.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.LIBRE,
        )
        self.assertTrue(consulta.payload.es_liberada())
        self.assertEqual(consulta.payload.operation_id, op)

    def test_reintento_tomar_vencida_mismo_operation_id(self):
        proyecto = _proyecto_uuid()
        self.servicio_a.reservar(proyecto, _clave())
        self.reloj.avanzar(self.TTL + self.GRACE + 100)
        op = _uuid4()
        r1 = self.servicio_b.tomar_vencida(
            proyecto, _clave(), operation_id=op
        )
        self.assertTrue(r1.exitoso, r1.error)
        self.assertEqual(
            self._conteo_commits(proyecto, _clave()), "2"
        )
        # Reintento: el head ya es la nueva ACTIVA propia; debe
        # reconocer la operacion aplicada, no fallar.
        r2 = self.servicio_b.tomar_vencida(
            proyecto, _clave(), operation_id=op
        )
        self.assertTrue(r2.exitoso, r2.error)
        self.assertEqual(r2.operacion, "idempotencia")
        self.assertEqual(
            self._conteo_commits(proyecto, _clave()), "2"
        )
        consulta = self.servicio_b.consultar_reserva(
            proyecto, _clave()
        )
        self.assertIs(
            consulta.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_MI,
        )
        self.assertEqual(consulta.payload.operation_id, op)
        self.assertEqual(consulta.payload.id_cliente, self.id_b)

    def test_mismo_operation_id_payload_incompatible_no_verificable(
        self,
    ):
        # Reutilizar el operation_id de la reserva ACTIVA como
        # operation_id de la liberacion: payload incompatible con
        # la intencion -> NO_VERIFICABLE y ningun commit nuevo.
        proyecto = _proyecto_uuid()
        op_reserva = _uuid4()
        self.servicio_a.reservar(
            proyecto, _clave(), operation_id=op_reserva
        )
        resultado = self.servicio_a.liberar(
            proyecto, _clave(), operation_id=op_reserva
        )
        self.assertFalse(resultado.exitoso)
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )
        self.assertEqual(
            self._conteo_commits(proyecto, _clave()), "1"
        )

    def test_operation_id_proporcionado_invalido_bloqueado(self):
        proyecto = _proyecto_uuid()
        resultado = self.servicio_a.reservar(
            proyecto, _clave(), operation_id="no-es-uuid"
        )
        self.assertFalse(resultado.exitoso)
        self.assertIs(
            resultado.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )
        salida = self._git_remoto(
            "show-ref", self._ref_heads(proyecto, _clave())
        )
        self.assertFalse(salida.stdout.strip())


class TestMutexConcurrenciaReal(unittest.TestCase):
    """REV3 §9: adquisicion atomica del coordinador con hilos reales.

    La comprobacion de flags + el marcado del nuevo flag deben ser
    atomicos: dos hilos liberados simultaneamente no pueden ganar
    ambos.
    """

    def test_dos_reservas_simultaneas_exactamente_una_gana(self):
        coordinador = CoordinadorOperacionesRed()
        barrera = threading.Barrier(2)
        ganadores = []
        candado = threading.Lock()

        def intento_reservas():
            barrera.wait(timeout=10)
            if coordinador.intentar_iniciar_reservas():
                with candado:
                    ganadores.append("reservas")

        hilos = [
            threading.Thread(target=intento_reservas)
            for _ in range(2)
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=10)
        self.assertEqual(len(ganadores), 1)
        self.assertEqual(ganadores[0], "reservas")
        self.assertTrue(coordinador.ocupado())
        coordinador.finalizar_reservas()
        self.assertFalse(coordinador.ocupado())

    def test_remota_vs_reservas_simultaneas_exactamente_una_gana(self):
        coordinador = CoordinadorOperacionesRed()
        barrera = threading.Barrier(2)
        ganadores = []
        candado = threading.Lock()

        def intento_remota():
            barrera.wait(timeout=10)
            if coordinador.intentar_iniciar_remota():
                with candado:
                    ganadores.append("remota")

        def intento_reservas():
            barrera.wait(timeout=10)
            if coordinador.intentar_iniciar_reservas():
                with candado:
                    ganadores.append("reservas")

        hilos = [
            threading.Thread(target=intento_remota),
            threading.Thread(target=intento_reservas),
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=10)
        self.assertEqual(len(ganadores), 1)
        self.assertIn(ganadores[0], ("remota", "reservas"))
        coordinador.finalizar_remota()
        coordinador.finalizar_reservas()
        self.assertFalse(coordinador.ocupado())

    def test_flag_se_libera_correctamente_con_uso_repetido(self):
        coordinador = CoordinadorOperacionesRed()
        for _ in range(25):
            self.assertTrue(coordinador.intentar_iniciar_remota())
            self.assertFalse(coordinador.intentar_iniciar_reservas())
            self.assertFalse(coordinador.intentar_iniciar_remota())
            coordinador.finalizar_remota()
            self.assertFalse(coordinador.ocupado())
            self.assertTrue(coordinador.intentar_iniciar_reservas())
            coordinador.finalizar_reservas()
            self.assertFalse(coordinador.ocupado())


if __name__ == "__main__":
    unittest.main()
