"""
Pruebas del Bloque F: integración GUI del Modo Equipo Oracle V1.

Siguen el patrón histórico de la GUI: AplicacionGit se construye
con __new__ (sin Tkinter real), se inyectan fakes/mocks y se
verifican contratos. No requieren red real ni backend real.

Cobertura GG-PROMPT-042 §18 (A-G).
"""

import ast
import queue
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import principal
from modelos import CambioArchivo, ResultadoCambios, ResultadoComando
from modelos_configuracion import ConfiguracionModoEquipo
from modelos_reservas import (
    ClasificacionReservaObservada,
    ManifiestoProyecto,
    ReglaLayoutOracle,
    ResultadoValidacionReservaPropia,
)
from servicio_objetos_oracle import ServicioObjetosOracle
from servicio_reservas import CoordinadorOperacionesRed


CLAVE_FINI004 = "PACKAGE|FINI004"


def _manifiesto(project_uuid=None):
    return ManifiestoProyecto(
        format_version=1,
        project_uuid=project_uuid or "33333333-3333-4333-8333-333333333333",
        oracle_layout=(
            ReglaLayoutOracle(
                carpeta="Paquetes",
                tipo="PACKAGE",
                extension=".pls",
            ),
        ),
    )


def _resultado_reserva(valida, motivo=""):
    return ResultadoValidacionReservaPropia(
        valida=valida,
        motivo=motivo,
    )


class VariableFalsa:
    """Sustituto mínimo de tk.StringVar."""

    def __init__(self, valor=""):
        self.valor = valor
        self.historial = []

    def get(self):
        return self.valor

    def set(self, valor):
        self.valor = valor
        self.historial.append(valor)


class VentanaFalsa:
    """Sustituto mínimo de la ventana Tkinter."""

    def update_idletasks(self):
        pass


class ConfiguracionFalsa:
    """Fake de ServicioConfiguracion (solo Modo Equipo)."""

    def __init__(self, resultado_carga):
        self.resultado_carga = resultado_carga
        self.llamadas_carga = 0
        self.ultima_guardada = None

    def cargar_configuracion_modo_equipo(self):
        self.llamadas_carga += 1
        return self.resultado_carga

    def guardar_configuracion_modo_equipo(self, config):
        self.ultima_guardada = config
        # Simula la recarga posterior: lo guardado es lo que la
        # próxima carga devuelve (como config.json real).
        self.resultado_carga = SimpleNamespace(
            exitoso=True,
            configuracion=config,
            mensaje="guardada",
        )
        return SimpleNamespace(
            exitoso=True,
            configuracion=config,
            mensaje="guardada",
        )


class IdentidadFalsa:
    def __init__(self, exitoso=True, id_cliente="id-cliente-1",
                 mensaje=""):
        self.resultado = SimpleNamespace(
            exitoso=exitoso,
            id_cliente=id_cliente,
            mensaje=mensaje,
        )
        self.llamadas = 0

    def obtener_o_crear_identidad(self):
        self.llamadas += 1
        return self.resultado


class ManifiestoFalso:
    def __init__(self, project_uuid, exitoso=True):
        self.resultado = SimpleNamespace(
            exitoso=exitoso,
            mensaje="" if exitoso else "sin manifiesto",
            manifiesto=_manifiesto(project_uuid) if exitoso else None,
        )
        self.project_uuid_actual = project_uuid

    def leer_manifiesto_head(self, ruta_repositorio):
        return self.resultado


class BackendFalso:
    def __init__(self, exitoso=True, ruta="C:/backend/backend.git"):
        self.resultado = SimpleNamespace(
            exitoso=exitoso,
            ruta_backend=ruta if exitoso else "",
            mensaje="" if exitoso else "backend fallo",
        )
        self.llamadas = 0
        self.urls_recibidas = []

    def preparar_backend_local(self, project_uuid, backend_reservas_url):
        self.llamadas += 1
        self.urls_recibidas.append(backend_reservas_url)
        return self.resultado


class ServicioGitFalso:
    """Fake del servicio Git histórico para los flujos F."""

    def __init__(self):
        self.ejecutar_git = mock.MagicMock(
            return_value=ResultadoComando(
                exitoso=True,
                codigo_salida=0,
                salida="usuario-prueba",
                error="",
                comando="git config --get user.name",
            )
        )

    def obtener_cambios(self, ruta_repositorio):
        return ResultadoCambios(exitoso=True, cambios=[])

    def obtener_hash_actual(self, ruta_repositorio):
        return ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="abc1234",
            error="",
            comando="git rev-parse --short HEAD",
        )

    def obtener_remoto_sincronizacion(self, ruta_repositorio):
        return ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="origin",
            error="",
            comando="git remote",
        )

    def ejecutar_fetch(self, ruta_repositorio, remoto):
        return ResultadoComando(
            exitoso=True,
            codigo_salida=0,
            salida="",
            error="",
            comando="git fetch",
        )

    def obtener_estado_sincronizacion(self, ruta_repositorio):
        return None


class ReservasFalsasGUI:
    """
    Fake de ServicioReservas: solo registra la API pública
    explícita; cualquier intento de red/escritura no explícita
    falla la prueba.
    """

    def __init__(self):
        self.llamadas = []

    def _registrar(self, tipo, project_uuid, clave):
        self.llamadas.append((tipo, project_uuid, clave))
        return SimpleNamespace(
            exitoso=True,
            operacion=tipo,
            clasificacion=(
                ClasificacionReservaObservada.RESERVADO_POR_MI
            ),
            payload=SimpleNamespace(
                alias="equipo",
                hostname="pc-1",
                user_name="ana",
                id_cliente="id-cliente-1",
                vencimiento="2026-08-28T12:00:00Z",
            ),
            mensaje="ok",
            error="",
        )

    def consultar_reserva(self, project_uuid, clave):
        return self._registrar("consultar", project_uuid, clave)

    def reservar(self, project_uuid, clave):
        return self._registrar("reservar", project_uuid, clave)

    def renovar(self, project_uuid, clave):
        return self._registrar("renovar", project_uuid, clave)

    def liberar(self, project_uuid, clave):
        return self._registrar("liberar", project_uuid, clave)

    def tomar_vencida(self, project_uuid, clave):
        return self._registrar("tomar_vencida", project_uuid, clave)

    def __getattr__(self, nombre):
        if nombre.startswith("_"):
            raise AttributeError(nombre)
        raise AssertionError(
            f"Llamada inesperada a '{nombre}' desde la GUI F"
        )


class ServicioGitProtegidoFalso:
    def __init__(self):
        self.agregados = []
        self.actualizados = []
        self.commits = []

    def agregar_archivos(self, ruta_repositorio, rutas):
        self.agregados.append((ruta_repositorio, tuple(rutas)))
        return ResultadoComando(
            exitoso=True, codigo_salida=0, salida="",
            error="", comando="add",
        )

    def actualizar_archivos_preparados(self, ruta_repositorio, rutas):
        self.actualizados.append((ruta_repositorio, tuple(rutas)))
        return ResultadoComando(
            exitoso=True, codigo_salida=0, salida="",
            error="", comando="add",
        )

    def crear_commit(self, ruta_repositorio, mensaje):
        self.commits.append((ruta_repositorio, mensaje))
        return ResultadoComando(
            exitoso=True, codigo_salida=0, salida="",
            error="", comando="commit",
        )


def _aplicacion_base():
    """
    AplicacionGit por __new__ con el estado mínimo que ejercitan
    los flujos de Bloque F (patrón histórico de la GUI).
    """

    aplicacion = principal.AplicacionGit.__new__(
        principal.AplicacionGit
    )

    aplicacion.ruta_repositorio = "C:/repo/prueba"
    aplicacion.variable_estado = VariableFalsa("")
    aplicacion.ventana_principal = VentanaFalsa()
    aplicacion.operacion_remota_en_curso = False
    aplicacion.operacion_reservas_gui_en_curso = False
    aplicacion.ventana_modo_equipo = None
    aplicacion.coordinador_modo_equipo = CoordinadorOperacionesRed()
    aplicacion.modo_equipo_estado = "no_cargada"
    aplicacion.modo_equipo_mensaje = ""
    aplicacion.configuracion_modo_equipo = None
    aplicacion.id_cliente = ""
    aplicacion.project_uuid_activo = ""
    aplicacion.ruta_backend_reservas = ""
    aplicacion.ruta_repositorio_modo_equipo = ""
    aplicacion.resolvedor_oracle = None
    aplicacion.servicio_reservas = None
    aplicacion.protector_reservas = None
    aplicacion.servicio_git_protegido = None
    aplicacion.servicio_git = ServicioGitFalso()
    aplicacion.servicio_configuracion = ConfiguracionFalsa(
        SimpleNamespace(
            exitoso=True,
            configuracion=ConfiguracionModoEquipo(
                modo_equipo_habilitado=False,
                backend_reservas_url="C:/equipo/reservas.git",
                alias_equipo="equipo",
            ),
        )
    )
    aplicacion.servicio_identidad_equipo = IdentidadFalsa()
    aplicacion.servicio_manifiesto = ManifiestoFalso(
        "33333333-3333-4333-8333-333333333333"
    )
    aplicacion.servicio_backend_reservas = BackendFalso()

    return aplicacion


def _config_habilitada():
    return ConfiguracionModoEquipo(
        modo_equipo_habilitado=True,
        backend_reservas_url="C:/equipo/reservas.git",
        alias_equipo="equipo",
    )


class _BaseModoEquipo(unittest.TestCase):

    def setUp(self):
        self.aplicacion = _aplicacion_base()
        parche_messagebox = mock.patch.multiple(
            principal.messagebox,
            showinfo=mock.DEFAULT,
            showwarning=mock.DEFAULT,
            showerror=mock.DEFAULT,
            askyesno=mock.DEFAULT,
        )
        self.mocks_messagebox = parche_messagebox.start()
        self.addCleanup(parche_messagebox.stop)

    def _estado_listo(self, protegido):
        """
        Prepara el estado "listo" con configuración habilitada y
        el contexto ya construido para esta ruta con ESA
        configuración (el refresco del selector relee manifiesto y
        config y lo conserva: misma ruta, mismo project_uuid,
        misma firma).
        """

        config = _config_habilitada()

        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(exitoso=True, configuracion=config)
        )
        self.aplicacion.modo_equipo_estado = "listo"
        self.aplicacion.servicio_git_protegido = protegido
        self.aplicacion.servicio_reservas = ReservasFalsasGUI()
        self.aplicacion.ruta_repositorio_modo_equipo = (
            self.aplicacion.ruta_repositorio
        )
        self.aplicacion.project_uuid_activo = (
            self.aplicacion.servicio_manifiesto.project_uuid_actual
        )
        self.aplicacion.firma_configuracion_contexto = (
            principal.AplicacionGit._firma_configuracion(config)
        )


class TestSelectorEscrituras(_BaseModoEquipo):
    """§18.A: selección fail-closed del servicio productivo."""

    def test_deshabilitado_usa_servicio_historico(self):
        self.aplicacion.modo_equipo_estado = "deshabilitado"
        servicio, bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIs(servicio, self.aplicacion.servicio_git)
        self.assertEqual(bloqueo, "")

    def test_habilitado_listo_usa_servicio_protegido(self):
        protegido = ServicioGitProtegidoFalso()
        self._estado_listo(protegido)
        servicio, bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIs(servicio, protegido)
        self.assertEqual(bloqueo, "")
        self.assertIsNot(servicio, self.aplicacion.servicio_git)

    def test_habilitado_bloqueado_no_devuelve_historico(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion.servicio_identidad_equipo = IdentidadFalsa(
            exitoso=False, mensaje="identidad corrupta"
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "bloqueado")
        servicio, bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIsNone(servicio)
        self.assertIn("identidad", bloqueo)

    def test_configuracion_corrupta_no_se_acepta_como_deshabilitado(
        self,
    ):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=False,
                configuracion=None,
                mensaje="config.json corrupto",
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(
            self.aplicacion.modo_equipo_estado,
            "no_cargada",
        )
        servicio, bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIsNone(servicio)
        self.assertIn("bloqueados", bloqueo)

    def test_worker_de_reservas_pendiente_bloquea_escrituras(self):
        self.aplicacion.modo_equipo_estado = "listo"
        self.aplicacion.operacion_reservas_gui_en_curso = True
        servicio, bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIsNone(servicio)
        self.assertIn("reservas", bloqueo)


class TestContextoModoEquipo(_BaseModoEquipo):
    """§18.C: construcción y ciclo de vida del contexto."""

    def test_deshabilitado_no_crea_backend_ni_identidad(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=ConfiguracionModoEquipo(
                    modo_equipo_habilitado=False,
                ),
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(
            self.aplicacion.modo_equipo_estado,
            "deshabilitado",
        )
        self.assertEqual(
            self.aplicacion.servicio_backend_reservas.llamadas,
            0,
        )
        self.assertEqual(
            self.aplicacion.servicio_identidad_equipo.llamadas,
            0,
        )

    def test_habilitado_construye_contexto_completo(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")
        self.assertEqual(
            self.aplicacion.project_uuid_activo,
            "33333333-3333-4333-8333-333333333333",
        )
        self.assertEqual(
            self.aplicacion.id_cliente, "id-cliente-1"
        )
        self.assertIsNotNone(self.aplicacion.resolvedor_oracle)
        self.assertIsNotNone(self.aplicacion.servicio_reservas)
        self.assertIsNotNone(self.aplicacion.protector_reservas)
        self.assertIsNotNone(self.aplicacion.servicio_git_protegido)
        # El manifiesto se obtuvo por la API de HEAD (fake), no del
        # working tree.
        self.assertEqual(
            self.aplicacion.servicio_manifiesto.project_uuid_actual,
            "33333333-3333-4333-8333-333333333333",
        )

    def test_fallo_identidad_bloquea_sin_degradar(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion.servicio_identidad_equipo = IdentidadFalsa(
            exitoso=False, mensaje="identidad corrupta"
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "bloqueado")
        servicio, _bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIsNone(servicio)

    def test_fallo_manifiesto_bloquea_sin_degradar(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion.servicio_manifiesto = ManifiestoFalso(
            "x", exitoso=False
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "bloqueado")
        servicio, _bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIsNone(servicio)

    def test_fallo_backend_bloquea_sin_degradar(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion.servicio_backend_reservas = BackendFalso(
            exitoso=False
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "bloqueado")
        servicio, _bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIsNone(servicio)

    def test_project_uuid_inmutable_en_misma_ruta(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")

        # El manifiesto ahora reporta OTRO project_uuid en la MISMA
        # ruta: el contexto se bloquea, no se cambia de backend.
        nuevo_uuid = "44444444-4444-4444-8444-444444444444"
        self.aplicacion.servicio_manifiesto = ManifiestoFalso(
            nuevo_uuid
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "bloqueado")
        self.assertIn(
            "INMUTABLE", self.aplicacion.modo_equipo_mensaje
        )
        servicio, _bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIsNone(servicio)

    def test_cambio_de_repo_permite_nuevo_contexto(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")

        # Seleccionan otra ruta: el contexto se limpia y puede
        # construirse uno nuevo para el proyecto de esa ruta.
        self.aplicacion._limpiar_contexto_modo_equipo()
        self.assertEqual(self.aplicacion.project_uuid_activo, "")
        self.assertIsNone(self.aplicacion.servicio_git_protegido)
        self.assertIsNone(
            self.aplicacion.firma_configuracion_contexto
        )

        self.aplicacion.ruta_repositorio = "C:/repo/otro"
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")

    def test_limpiar_contexto_no_deja_referencias(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.aplicacion._limpiar_contexto_modo_equipo()
        self.assertEqual(self.aplicacion.project_uuid_activo, "")
        self.assertIsNone(self.aplicacion.servicio_reservas)
        self.assertIsNone(self.aplicacion.protector_reservas)
        self.assertIsNone(self.aplicacion.servicio_git_protegido)
        self.assertIsNone(self.aplicacion.resolvedor_oracle)
        # El coordinador de red sobrevive (es de sesión completa).
        self.assertIsNotNone(self.aplicacion.coordinador_modo_equipo)

    def test_pull_exitoso_refresca_contexto(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion.variable_ultima_consulta = VariableFalsa("")
        self.aplicacion._refrescar_estado_modo_equipo()
        carga_previa = (
            self.aplicacion.servicio_configuracion.llamadas_carga
        )

        self.aplicacion.cargar_cambios = lambda: None
        self.aplicacion.actualizar_historial_si_abierto = (
            lambda: None
        )
        self.aplicacion.cargar_estado_sincronizacion_local = (
            lambda: None
        )
        self.aplicacion.actualizar_controles_operacion_remota = (
            lambda: None
        )

        resultado_pull = ResultadoComando(
            exitoso=True, codigo_salida=0, salida="",
            error="", comando="pull",
        )
        self.aplicacion.procesar_resultado_pull(
            self.aplicacion.ruta_repositorio,
            resultado_pull,
            None,
            None,
        )

        self.assertGreater(
            self.aplicacion.servicio_configuracion.llamadas_carga,
            carga_previa,
            "El Pull exitoso debe refrescar el contexto de HEAD"
        )


class TestFlujosStagingCommit(_BaseModoEquipo):
    """§18.B: staging/commit vía selector, sin red automática."""

    def _cambio(self, ruta, preparado=False):
        return CambioArchivo(
            ruta=ruta,
            estado_indice="M" if preparado else " ",
            estado_trabajo="M",
            descripcion="prueba",
            preparado=preparado,
            ruta_anterior="",
            requiere_actualizar_preparado=False,
            en_conflicto=False,
        )

    def test_preparar_usa_selector_y_no_llama_red(self):
        protegido = ServicioGitProtegidoFalso()
        self._estado_listo(protegido)

        tabla = mock.MagicMock()
        tabla.selection.return_value = ("fila-1",)
        self.aplicacion.tabla_cambios = tabla
        self.aplicacion.cambios_por_elemento = {
            "fila-1": self._cambio("Paquetes/FINI004.pls"),
        }
        self.aplicacion.cargar_cambios = lambda: None
        self.aplicacion.variable_mensaje_commit = VariableFalsa("")

        self.mocks_messagebox["askyesno"].return_value = True

        self.aplicacion.preparar_seleccionados()

        self.assertEqual(len(protegido.agregados), 1)
        self.assertEqual(
            protegido.agregados[0][1],
            ("Paquetes/FINI004.pls",),
        )
        self.assertEqual(self.aplicacion.servicio_reservas.llamadas, [])

    def test_preparar_bloqueado_no_escribe(self):
        # Contexto habilitado pero que falla al construirse:
        # el selector BLOQUEA y no ejecuta ningún Git.
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion.servicio_identidad_equipo = IdentidadFalsa(
            exitoso=False, mensaje="identidad corrupta"
        )

        tabla = mock.MagicMock()
        tabla.selection.return_value = ("fila-1",)
        self.aplicacion.tabla_cambios = tabla
        self.aplicacion.cambios_por_elemento = {
            "fila-1": self._cambio("Paquetes/FINI004.pls"),
        }
        self.aplicacion.cargar_cambios = lambda: None

        self.mocks_messagebox["askyesno"].return_value = True

        self.aplicacion.preparar_seleccionados()

        self.mocks_messagebox["showwarning"].assert_called()
        # No hay servicio que escribir: nada ejecutado.
        self.assertEqual(
            self.aplicacion.servicio_git.ejecutar_git.call_count,
            0,
        )

    def test_actualizar_usa_selector_y_no_llama_red(self):
        protegido = ServicioGitProtegidoFalso()
        self._estado_listo(protegido)

        cambio = self._cambio("Paquetes/FINI004.pls", preparado=True)
        cambio.requiere_actualizar_preparado = True

        tabla = mock.MagicMock()
        tabla.selection.return_value = ("fila-1",)
        self.aplicacion.tabla_cambios = tabla
        self.aplicacion.cambios_por_elemento = {"fila-1": cambio}
        self.aplicacion.cargar_cambios = lambda: None

        self.mocks_messagebox["askyesno"].return_value = True

        self.aplicacion.actualizar_preparados_seleccionados()

        self.assertEqual(len(protegido.actualizados), 1)
        self.assertEqual(self.aplicacion.servicio_reservas.llamadas, [])

    def test_commit_usa_selector_revalida_y_no_llama_red(self):
        protegido = ServicioGitProtegidoFalso()
        self._estado_listo(protegido)

        cambio = self._cambio("Paquetes/FINI004.pls", preparado=True)
        self.aplicacion.servicio_git.obtener_cambios = mock.MagicMock(
            return_value=ResultadoCambios(
                exitoso=True, cambios=[cambio]
            )
        )
        self.aplicacion.variable_mensaje_commit = VariableFalsa(
            "commit con protección"
        )
        self.aplicacion.cargar_cambios = lambda: None
        self.aplicacion.cargar_repositorio = mock.MagicMock()

        self.mocks_messagebox["askyesno"].return_value = True

        self.aplicacion.crear_commit_desde_interfaz()

        self.assertEqual(len(protegido.commits), 1)
        self.assertEqual(
            protegido.commits[0][1], "commit con protección"
        )
        self.assertEqual(self.aplicacion.servicio_reservas.llamadas, [])
        # El ciclo histórico post-commit se conserva.
        self.aplicacion.cargar_repositorio.assert_called_once()

    def test_commit_conflicto_sigue_bloqueando_antes_del_selector(
        self,
    ):
        # La protección histórica de conflictos (pre-selector) se
        # conserva intacta.
        cambio_conflicto = self._cambio("a.sql")
        cambio_conflicto.en_conflicto = True
        cambio_conflicto.preparado = True
        self.aplicacion.servicio_git.obtener_cambios = mock.MagicMock(
            return_value=ResultadoCambios(
                exitoso=True, cambios=[cambio_conflicto]
            )
        )
        self.aplicacion.variable_mensaje_commit = VariableFalsa("x")
        self.aplicacion.cargar_cambios = lambda: None

        protegido = ServicioGitProtegidoFalso()
        self.aplicacion.servicio_git_protegido = protegido
        self.aplicacion.modo_equipo_estado = "listo"
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )

        self.aplicacion.crear_commit_desde_interfaz()

        self.mocks_messagebox["showwarning"].assert_called()
        self.assertEqual(protegido.commits, [])

    def test_quitar_preparados_conserva_flujo_historico(self):
        cambio = self._cambio("a.sql", preparado=True)
        tabla = mock.MagicMock()
        tabla.selection.return_value = ("fila-1",)
        self.aplicacion.tabla_cambios = tabla
        self.aplicacion.cambios_por_elemento = {"fila-1": cambio}
        self.aplicacion.cargar_cambios = lambda: None

        self.aplicacion.servicio_git.quitar_archivos_preparados = (
            mock.MagicMock(
                return_value=ResultadoComando(
                    exitoso=True, codigo_salida=0, salida="",
                    error="", comando="restore",
                )
            )
        )

        self.mocks_messagebox["askyesno"].return_value = True

        self.aplicacion.quitar_preparados_seleccionados()

        self.aplicacion.servicio_git.quitar_archivos_preparados.\
            assert_called_once()
        # Unstaging no pasa por el selector ni pide reservas.
        self.assertEqual(self.aplicacion.servicio_reservas, None)


class TestAccionesReservasGUI(_BaseModoEquipo):
    """§18.D: acciones explícitas de reservas desde la GUI."""

    def _contexto_listo(self):
        config = _config_habilitada()

        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(exitoso=True, configuracion=config)
        )
        self.aplicacion.modo_equipo_estado = "listo"
        self.aplicacion.ruta_repositorio_modo_equipo = (
            self.aplicacion.ruta_repositorio
        )
        self.aplicacion.project_uuid_activo = (
            self.aplicacion.servicio_manifiesto.project_uuid_actual
        )
        self.aplicacion.firma_configuracion_contexto = (
            principal.AplicacionGit._firma_configuracion(config)
        )
        self.aplicacion.servicio_reservas = ReservasFalsasGUI()
        self.aplicacion.resolvedor_oracle = ServicioObjetosOracle(
            _manifiesto()
        )
        self.aplicacion.variable_modo_equipo_ruta_objeto = (
            VariableFalsa("Paquetes/FINI004.pls")
        )
        self.aplicacion.variable_modo_equipo_clave = VariableFalsa("")
        self.aplicacion.variable_modo_equipo_clasificacion = (
            VariableFalsa("")
        )
        self.aplicacion.variable_modo_equipo_propietario = (
            VariableFalsa("")
        )
        self.aplicacion.variable_modo_equipo_vencimiento = (
            VariableFalsa("")
        )
        self.aplicacion.botones_acciones_reservas = []

    def test_ruta_ordinaria_no_es_reservable(self):
        self._contexto_listo()
        self.aplicacion.variable_modo_equipo_ruta_objeto = VariableFalsa(
            "Lecturas/nota.txt"
        )
        clave = self.aplicacion._resolver_clave_objeto_desde_gui()
        self.assertIsNone(clave)
        self.mocks_messagebox["showinfo"].assert_called()

    def test_ruta_oracle_no_resoluble_bloquea(self):
        self._contexto_listo()
        self.aplicacion.variable_modo_equipo_ruta_objeto = VariableFalsa(
            "Sospechoso/algo.sql"
        )
        clave = self.aplicacion._resolver_clave_objeto_desde_gui()
        self.assertIsNone(clave)
        self.mocks_messagebox["showwarning"].assert_called()

    def test_ruta_oracle_valida_resuelve_clave(self):
        self._contexto_listo()
        clave = self.aplicacion._resolver_clave_objeto_desde_gui()
        self.assertEqual(clave, CLAVE_FINI004)
        self.assertEqual(
            self.aplicacion.variable_modo_equipo_clave.get(),
            CLAVE_FINI004,
        )

    def _iniciar_y_procesar(self, tipo):
        self._contexto_listo()
        self.aplicacion.cola_resultados = queue.Queue()
        self.aplicacion.iniciar_accion_reserva(tipo)
        self.assertTrue(
            self.aplicacion.operacion_reservas_gui_en_curso
        )
        elemento = self.aplicacion.cola_resultados.get(timeout=10)
        self.assertEqual(elemento[0], "modo_equipo_reserva")
        self.aplicacion.procesar_resultado_reserva(*elemento[1:])
        return elemento

    def test_consultar_llama_a_consultar_reserva(self):
        elemento = self._iniciar_y_procesar("consultar")
        self.assertEqual(
            self.aplicacion.servicio_reservas.llamadas[0],
            ("consultar", self.aplicacion.project_uuid_activo,
             CLAVE_FINI004),
        )
        self.assertIn("RESERVADO_POR_MI",
                      self.aplicacion.variable_modo_equipo_clasificacion.get())

    def test_reservar_llama_a_reservar(self):
        self._iniciar_y_procesar("reservar")
        self.assertEqual(
            self.aplicacion.servicio_reservas.llamadas[0][0],
            "reservar",
        )

    def test_renovar_llama_a_renovar(self):
        self._iniciar_y_procesar("renovar")
        self.assertEqual(
            self.aplicacion.servicio_reservas.llamadas[0][0],
            "renovar",
        )

    def test_liberar_llama_a_liberar(self):
        self._iniciar_y_procesar("liberar")
        self.assertEqual(
            self.aplicacion.servicio_reservas.llamadas[0][0],
            "liberar",
        )

    def test_tomar_vencida_llama_a_tomar_vencida(self):
        self._iniciar_y_procesar("tomar_vencida")
        self.assertEqual(
            self.aplicacion.servicio_reservas.llamadas[0][0],
            "tomar_vencida",
        )

    def test_no_decision_de_propiedad_por_metadata(self):
        # Las acciones pasan proyecto+clave al servicio D: la GUI
        # nunca decide propiedad por alias/hostname/user_name.
        self._iniciar_y_procesar("reservar")
        for llamada in self.aplicacion.servicio_reservas.llamadas:
            self.assertEqual(len(llamada), 3)
            _tipo, project_uuid, clave = llamada
            self.assertTrue(project_uuid)
            self.assertEqual(clave, CLAVE_FINI004)

    def test_doble_inicio_de_operacion_bloqueado(self):
        self._contexto_listo()
        self.aplicacion.cola_resultados = queue.Queue()
        self.aplicacion.iniciar_accion_reserva("consultar")
        self.assertTrue(
            self.aplicacion.operacion_reservas_gui_en_curso
        )
        self.aplicacion.iniciar_accion_reserva("reservar")
        # Solo la primera operación llegó al servicio/cola.
        self.assertEqual(
            self.aplicacion.cola_resultados.qsize(), 1
        )
        self.mocks_messagebox["showinfo"].assert_called()

    def test_resultado_obsoleto_no_actualiza_gui(self):
        self._contexto_listo()
        self.aplicacion.operacion_reservas_gui_en_curso = True
        clasificacion_antes = (
            self.aplicacion.variable_modo_equipo_clasificacion.get()
        )
        self.aplicacion.procesar_resultado_reserva(
            "consultar",
            "C:/repo/OTRO",
            self.aplicacion.project_uuid_activo,
            CLAVE_FINI004,
            "Paquetes/FINI004.pls",
            SimpleNamespace(
                exitoso=True,
                clasificacion=(
                    ClasificacionReservaObservada.LIBRE
                ),
                payload=None,
                mensaje="",
                error="",
            ),
        )
        # El flag se libera siempre.
        self.assertFalse(
            self.aplicacion.operacion_reservas_gui_en_curso
        )
        # La GUI vigente no se toca.
        self.assertEqual(
            self.aplicacion.variable_modo_equipo_clasificacion.get(),
            clasificacion_antes,
        )


class TestMutexRedCompartido(_BaseModoEquipo):
    """§18.E: mutex único entre reservas y operaciones remotas."""

    def test_reservas_pendientes_impiden_remota(self):
        coordinador = self.aplicacion.coordinador_modo_equipo
        coordinador.operacion_reservas_en_curso = True
        try:
            self.assertFalse(
                self.aplicacion._adquirir_mutex_red_para_remota()
            )
        finally:
            coordinador.finalizar_reservas()

    def test_remota_adquirida_impide_otros(self):
        coordinador = self.aplicacion.coordinador_modo_equipo
        self.assertTrue(
            self.aplicacion._adquirir_mutex_red_para_remota()
        )
        try:
            self.assertFalse(coordinador.intentar_iniciar_reservas())
            self.assertFalse(coordinador.intentar_iniciar_remota())
        finally:
            self.aplicacion._liberar_mutex_red_de_remota()
        self.assertFalse(coordinador.ocupado())

    def test_liberacion_aun_con_resultado_obsoleto(self):
        coordinador = self.aplicacion.coordinador_modo_equipo
        self.assertTrue(coordinador.intentar_iniciar_remota())

        self.aplicacion.actualizar_controles_operacion_remota = (
            lambda: None
        )
        self.aplicacion.cargar_estado_sincronizacion_local = (
            lambda: None
        )

        resultado = ResultadoComando(
            exitoso=True, codigo_salida=0, salida="",
            error="", comando="fetch",
        )
        self.aplicacion.procesar_resultado_fetch(
            "C:/repo/obsoleto",
            "origin",
            resultado,
            None,
        )
        self.assertFalse(coordinador.ocupado())

    def test_iniciar_fetch_adquiere_mutex_sin_hilo_real(self):
        # REV1 B3: no se ejecuta trabajo_fetch en un hilo real
        # (evita excepciones asíncronas fuera del control de
        # unittest). Se verifica que el mutex se adquiere, que se
        # crea y arranca el hilo con el trabajo correcto y que
        # nada corre de forma descontrolada.
        self.aplicacion.variable_ultima_consulta = VariableFalsa("")
        self.aplicacion.actualizar_controles_operacion_remota = (
            lambda: None
        )

        creados = []

        class HiloFalso:
            def __init__(self, target, args, daemon=None):
                creados.append(
                    {"target": target, "args": args, "daemon": daemon}
                )

            def start(self):
                creados.append("start")

        with mock.patch.object(
            principal, "threading", SimpleNamespace(Thread=HiloFalso)
        ):
            self.aplicacion.iniciar_fetch()

        hilos = [c for c in creados if isinstance(c, dict)]
        arranques = [c for c in creados if c == "start"]

        self.assertEqual(len(hilos), 1)
        self.assertEqual(len(arranques), 1)
        # Los bound methods se comparan por igualdad (self+func),
        # no por identidad.
        self.assertEqual(
            hilos[0]["target"], self.aplicacion.trabajo_fetch
        )
        self.assertEqual(
            hilos[0]["args"],
            ("C:/repo/prueba", "origin"),
        )
        self.assertTrue(hilos[0]["daemon"])

        # El mutex quedó adquirido en el punto esperado y se
        # libera al procesar el resultado.
        self.assertTrue(
            self.aplicacion.coordinador_modo_equipo.ocupado()
        )
        self.aplicacion._liberar_mutex_red_de_remota()
        self.assertFalse(
            self.aplicacion.coordinador_modo_equipo.ocupado()
        )
        # El trabajo real del hilo nunca corrió: la cola queda
        # vacía y no hay efectos de Fetch.
        self.assertFalse(hasattr(self.aplicacion, "cola_resultados"))

    def test_sin_modo_equipo_no_hay_mutex(self):
        aplicacion = _aplicacion_base()
        del aplicacion.coordinador_modo_equipo
        self.assertTrue(
            aplicacion._adquirir_mutex_red_para_remota()
        )


class TestAyudasModoEquipo(_BaseModoEquipo):
    """§18.F: ayudas nuevas cableadas y históricas preservadas."""

    CLAVES_F = tuple(
        clave for clave in principal.TEXTOS_AYUDA_GIT_V1
        if clave.startswith("modo_equipo")
    )

    def test_claves_f_existen_y_no_estan_vacias(self):
        self.assertGreaterEqual(len(self.CLAVES_F), 15)
        for clave in self.CLAVES_F:
            texto = principal.TEXTOS_AYUDA_GIT_V1[clave]
            self.assertTrue(texto.strip(), f"Vacía: {clave}")

    def test_historicas_38_siguen_presentes(self):
        historicas = [
            clave for clave in principal.TEXTOS_AYUDA_GIT_V1
            if not clave.startswith("modo_equipo")
        ]
        self.assertEqual(len(historicas), 38)

    def test_cada_clave_f_explica_red_o_no_automatismo(self):
        for clave in (
            "modo_equipo_consultar",
            "modo_equipo_reservar",
            "modo_equipo_renovar",
            "modo_equipo_liberar",
            "modo_equipo_tomar_vencida",
            "modo_equipo_acciones_red",
        ):
            self.assertIn(
                "red",
                principal.TEXTOS_AYUDA_GIT_V1[clave],
                f"La ayuda '{clave}' debe aclarar el uso de red",
            )

    def test_ayuda_interfaz_intacta(self):
        ruta = Path(principal.__file__).parent / "ayuda_interfaz.py"
        contenido = ruta.read_text(encoding="utf-8")
        self.assertNotIn("modo_equipo", contenido)


class TestAutomatismosProhibidos(_BaseModoEquipo):
    """§18.G: cero automatismos de red desde staging/commit."""

    @classmethod
    def setUpClass(cls):
        ruta = Path(principal.__file__).resolve()
        cls.arbol = ast.parse(
            ruta.read_text(encoding="utf-8"),
            filename=str(ruta),
        )
        cls.metodos_f = (
            "preparar_seleccionados",
            "actualizar_preparados_seleccionados",
            "crear_commit_desde_interfaz",
        )

    def _metodo(self, nombre):
        for nodo in ast.walk(self.arbol):
            if (
                isinstance(nodo, ast.FunctionDef)
                and nodo.name == nombre
            ):
                return nodo
        self.fail(f"No se encontró el método {nombre}")

    def test_staging_commit_no_llaman_reservas_ni_fetch(self):
        prohibidos = (
            "consultar_reserva",
            "reservar",
            "renovar",
            "liberar",
            "tomar_vencida",
            "iniciar_fetch",
            "iniciar_pull",
            "iniciar_push",
            "ejecutar_fetch",
        )
        for nombre in self.metodos_f:
            metodo = self._metodo(nombre)
            for nodo in ast.walk(metodo):
                if not isinstance(nodo, ast.Call):
                    continue
                nombre_llamada = getattr(nodo.func, "attr", None) or (
                    getattr(nodo.func, "id", None)
                )
                self.assertNotIn(
                    nombre_llamada,
                    prohibidos,
                    f"{nombre} llama a {nombre_llamada}",
                )

    def test_no_existe_scheduler_ni_auto_renew(self):
        # debe_renovar permanece disponible en Bloque D pero la GUI
        # no lo invoca y no existe scheduler/background de F.
        fuente = Path(principal.__file__).read_text(encoding="utf-8")
        self.assertNotIn("debe_renovar", fuente)
        self.assertNotIn("after_loop", fuente)
        self.assertNotIn("scheduler", fuente)

    def test_no_auto_liberacion_tras_commit(self):
        metodo = self._metodo("crear_commit_desde_interfaz")
        for nodo in ast.walk(metodo):
            if not isinstance(nodo, ast.Call):
                continue
            nombre_llamada = getattr(nodo.func, "attr", None) or (
                getattr(nodo.func, "id", None)
            )
            self.assertNotEqual(nombre_llamada, "liberar")

    def test_instancia_historica_nunca_mutada(self):
        # El diseño usa una instancia separada; no existe mutación
        # temporal de self.servicio_git.protector_reservas.
        fuente = Path(principal.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "servicio_git.protector_reservas", fuente
        )


class TestArranqueRealB1(unittest.TestCase):
    """REV1 B1: import de ServicioIdentidadEquipo y arranque real."""

    def test_servicio_identidad_equipo_importado(self):
        self.assertTrue(
            hasattr(principal, "ServicioIdentidadEquipo")
        )
        self.assertEqual(
            principal.ServicioIdentidadEquipo.__module__,
            "servicio_identidad_equipo",
        )

    def test_init_sin_globales_sin_resolver(self):
        """
        Detecta dependencias globales F sin resolver en
        AplicacionGit.__init__ (el fallo B1 era un NameError en el
        arranque real, invisible con el patrón __new__).

        Todo nombre cargado en __init__ debe resolverse como
        local del método, builtin o atributo del módulo.
        """

        ruta = Path(principal.__file__).resolve()
        arbol = ast.parse(
            ruta.read_text(encoding="utf-8"),
            filename=str(ruta),
        )

        clase = next(
            nodo for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.ClassDef)
            and nodo.name == "AplicacionGit"
        )
        init = next(
            nodo for nodo in ast.walk(clase)
            if isinstance(nodo, ast.FunctionDef)
            and nodo.name == "__init__"
        )

        asignados = {"self"}
        cargados = set()

        # Los parámetros del método son locales.
        for argumento in list(init.args.args) + list(init.args.kwonlyargs):
            asignados.add(argumento.arg)

        for nodo in ast.walk(init):
            if isinstance(nodo, ast.Name):
                if isinstance(nodo.ctx, ast.Store):
                    asignados.add(nodo.id)
                elif isinstance(nodo.ctx, ast.Load):
                    cargados.add(nodo.id)

        import builtins

        sin_resolver = sorted(
            nombre
            for nombre in cargados - asignados
            if not hasattr(principal, nombre)
            and not hasattr(builtins, nombre)
        )

        self.assertEqual(
            sin_resolver,
            [],
            "Nombres globales sin resolver en __init__: "
            f"{sin_resolver}"
        )


class TestInvalidacionPorConfiguracion(_BaseModoEquipo):
    """REV1 B2: cambio de configuración reconstruye el contexto."""

    def test_alias_cambia_reconstruye_servicio_reservas(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")

        reservas_anterior = self.aplicacion.servicio_reservas
        protegido_anterior = self.aplicacion.servicio_git_protegido

        config_nueva = _config_habilitada()
        config_nueva.alias_equipo = "nuevo"

        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True, configuracion=config_nueva
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()

        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")
        self.assertIsNot(
            self.aplicacion.servicio_reservas, reservas_anterior
        )
        self.assertEqual(
            self.aplicacion.servicio_reservas.alias, "nuevo"
        )
        self.assertIsNot(
            self.aplicacion.servicio_git_protegido,
            protegido_anterior,
        )

    def test_backend_url_cambia_reprepara_backend(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        protegido_anterior = self.aplicacion.servicio_git_protegido

        config_nueva = _config_habilitada()
        config_nueva.backend_reservas_url = "URL_B/equipo/reservas.git"

        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True, configuracion=config_nueva
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()

        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")
        self.assertGreaterEqual(
            self.aplicacion.servicio_backend_reservas.llamadas, 2
        )
        self.assertIn(
            "URL_B/equipo/reservas.git",
            self.aplicacion.servicio_backend_reservas.urls_recibidas,
        )
        self.assertIsNot(
            self.aplicacion.servicio_git_protegido,
            protegido_anterior,
        )

    def test_reconstruccion_fallida_fail_closed(self):
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")

        # Cambio de configuración Y backend que falla al
        # reconstruir: fail-closed, sin servicio histórico ni
        # servicio protegido anterior.
        config_nueva = _config_habilitada()
        config_nueva.alias_equipo = "nuevo"

        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True, configuracion=config_nueva
            )
        )
        self.aplicacion.servicio_backend_reservas = BackendFalso(
            exitoso=False
        )
        self.aplicacion._refrescar_estado_modo_equipo()

        self.assertEqual(self.aplicacion.modo_equipo_estado, "bloqueado")

        servicio, bloqueo = (
            self.aplicacion._resolver_servicio_escrituras()
        )
        self.assertIsNone(servicio)
        self.assertIsNot(servicio, self.aplicacion.servicio_git)
        self.assertIsNot(
            servicio, self.aplicacion.servicio_git_protegido
        )
        self.assertTrue(bloqueo)

    def test_guardado_gui_vuelve_efectiva_la_configuracion(self):
        # Contexto inicial listo con alias "equipo" y URL_A.
        self.aplicacion.servicio_configuracion = ConfiguracionFalsa(
            SimpleNamespace(
                exitoso=True,
                configuracion=_config_habilitada(),
            )
        )
        self.aplicacion._refrescar_estado_modo_equipo()
        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")

        # Campos de la ventana con la configuración NUEVA.
        self.aplicacion.variable_modo_equipo_habilitado = (
            VariableFalsa(True)
        )
        self.aplicacion.variable_modo_equipo_backend_url = (
            VariableFalsa("URL_B/equipo/reservas.git")
        )
        self.aplicacion.variable_modo_equipo_alias = VariableFalsa(
            "nuevo"
        )

        self.aplicacion.guardar_configuracion_modo_equipo_desde_gui()

        # Guardar usó ServicioConfiguracion.
        guardada = self.aplicacion.servicio_configuracion.ultima_guardada
        self.assertIsNotNone(guardada)
        self.assertEqual(guardada.alias_equipo, "nuevo")
        self.assertEqual(
            guardada.backend_reservas_url,
            "URL_B/equipo/reservas.git",
        )

        # La configuración guardada quedó EFECTIVA en el contexto.
        self.assertEqual(self.aplicacion.modo_equipo_estado, "listo")
        self.assertEqual(
            self.aplicacion.servicio_reservas.alias, "nuevo"
        )
        self.assertIn(
            "URL_B/equipo/reservas.git",
            self.aplicacion.servicio_backend_reservas.urls_recibidas,
        )
        self.mocks_messagebox["showinfo"].assert_called()

    def test_firma_cubre_todas_las_dimensiones(self):
        config_base = _config_habilitada()

        campos = (
            "backend_reservas_url",
            "alias_equipo",
            "ttl_reservas_segundos",
            "renovacion_reservas_segundos",
            "margen_minimo_reserva_segundos",
            "frescura_reservas_segundos",
            "margen_gracia_vencimiento_segundos",
        )

        for campo in campos:
            variante = _config_habilitada()
            setattr(
                variante,
                campo,
                getattr(variante, campo) + "-x"
                if isinstance(getattr(variante, campo), str)
                else getattr(variante, campo) + 1
            )
            self.assertNotEqual(
                principal.AplicacionGit._firma_configuracion(
                    config_base
                ),
                principal.AplicacionGit._firma_configuracion(
                    variante
                ),
                f"La firma no detecta cambios en {campo}",
            )


if __name__ == "__main__":
    unittest.main()
