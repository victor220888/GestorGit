"""
Servicio de reservas de Modo Equipo Oracle V1 (Bloque D).

Maquina de estados y orquestacion de alto nivel sobre
ServicioRemotoReservas.

Responsabilidades:

- consultar / reservar / renovar / liberar / tomar_vencida;
- validacion local 100% de reserva propia fresca
  (validar_reserva_propia_fresca);
- politica determinista de renovacion (debe_renovar);
- listado local de reservas propias activas conocidas para avisos
  pedagogicos del Bloque G (listar_reservas_propias_conocidas);
- reconciliacion por operation_id tras Push no concluyente;
- coordinador unico de operaciones de red (mutex logico).

Este servicio:

- NO depende de Tkinter;
- NO modifica ServicioGit ni principal.py;
- NO usa red real (opera sobre el backend inyectado);
- admite inyeccion para pruebas: ServicioRemotoReservas, reloj UTC,
  hostname, user_name, generador de operation_id y coordinador.

Propiedad tecnica EXCLUSIVA por id_cliente. alias/hostname/user_name
son solo metadata humana/auditoria.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from modelos_configuracion import (
    FRESCURA_RESERVAS_SEGUNDOS_V1,
    MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS_V1,
    MARGEN_MINIMO_RESERVA_SEGUNDOS_V1,
    RENOVACION_RESERVAS_SEGUNDOS_V1,
    TTL_RESERVAS_SEGUNDOS_V1,
)
from modelos_reservas import (
    ClasificacionReservaObservada,
    EstadoReservaPersistido,
    ReservaPayloadV1,
    ResultadoConsultaReserva,
    ResultadoOperacionReserva,
    ResultadoValidacionReservaPropia,
    ahora_utc,
    formatear_timestamp_utc,
    parsear_timestamp_utc,
    _es_uuid4_canonico,
)


class CoordinadorOperacionesRed:
    """
    Coordinador unico de operaciones de red de Modo Equipo V1.

    Modela los dos flags aprobados:

        operacion_remota_en_curso
        operacion_reservas_en_curso

    Regla unica:

        si cualquiera esta True:
            no iniciar otra operacion de red

    La adquisicion y liberacion de flags es atomica mediante
    threading.Lock. Dos hilos no pueden adquirir
    simultaneamente.

    Debe poder usarse posteriormente desde principal.py para
    envolver Fetch/Pull/Push/Publicar sin modificar la logica
    interna de servicio_remoto_git.py.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.operacion_remota_en_curso = False
        self.operacion_reservas_en_curso = False

    def ocupado(self):
        """True si cualquiera de los dos flags esta activo."""
        with self._lock:
            return (
                self.operacion_remota_en_curso
                or self.operacion_reservas_en_curso
            )

    def intentar_iniciar_remota(self):
        """
        Intenta adquirir el mutex para una operacion remota
        generica (Fetch/Pull/Push/Publicar).

        La comprobacion de flags + marcado del nuevo flag es
        atomica dentro del lock.

        Devuelve True si lo adquiere; False si el mutex esta
        ocupado.
        """
        with self._lock:
            if (self.operacion_remota_en_curso
                    or self.operacion_reservas_en_curso):
                return False
            self.operacion_remota_en_curso = True
            return True

    def intentar_iniciar_reservas(self):
        """
        Intenta adquirir el mutex para una operacion de reservas.

        La comprobacion de flags + marcado del nuevo flag es
        atomica dentro del lock.

        Devuelve True si lo adquiere; False si el mutex esta
        ocupado.
        """
        with self._lock:
            if (self.operacion_remota_en_curso
                    or self.operacion_reservas_en_curso):
                return False
            self.operacion_reservas_en_curso = True
            return True

    def finalizar_remota(self):
        """Libera el flag de operacion remota generica."""
        with self._lock:
            self.operacion_remota_en_curso = False

    def finalizar_reservas(self):
        """Libera el flag de operacion de reservas."""
        with self._lock:
            self.operacion_reservas_en_curso = False


@dataclass
class _EstadoCacheReserva:
    """
    Ultimo estado verificado en memoria por objeto.

    Este cache NO autoriza un LIBRE: solo puede usarse para validar
    una reserva propia ya adquirida (validar_reserva_propia_fresca).
    """

    clasificacion: ClasificacionReservaObservada
    payload: ReservaPayloadV1 | None = None
    parent: str = ""
    verificacion: object = None


@dataclass(frozen=True)
class ReservaPropiaConocida:
    """
    Snapshot de solo lectura de una reserva PROPIA ACTIVA conocida
    localmente en esta sesion (Bloque G).

    Dato exclusivamente pedagogico: NO autoriza staging/commit y NO
    sustituye validar_reserva_propia_fresca. Campos minimos para el
    aviso; deliberadamente sin rama_local ni rutas porque el aviso
    no debe depender de ellos.
    """

    project_uuid: str
    clave_objeto: str
    vencimiento: str
    alias: str


class ServicioReservas:
    """
    Servicio de alto nivel de reservas remotas.

    Uso tipico:

        servicio = ServicioReservas(
            remoto=servicio_remoto,
            id_cliente=id_cliente,
            alias=alias,
            hostname=hostname,
            user_name=user_name,
        )
        consulta = servicio.consultar_reserva(
            project_uuid, clave_objeto
        )
        operacion = servicio.reservar(project_uuid, clave_objeto)

    En pruebas se inyecta:

        remoto -> ServicioRemotoReservas sobre un bare temporal;
        reloj -> callable que devuelve datetime UTC (determinismo);
        operation_id_proveedor -> callable UUID4 (idempotencia);
        coordinador -> CoordinadorOperacionesRed compartido.
    """

    def __init__(
        self,
        remoto,
        id_cliente="",
        alias="",
        hostname="",
        user_name="",
        reloj=None,
        operation_id_proveedor=None,
        coordinador=None,
        ttl_segundos=TTL_RESERVAS_SEGUNDOS_V1,
        renovacion_segundos=RENOVACION_RESERVAS_SEGUNDOS_V1,
        margen_minimo_segundos=MARGEN_MINIMO_RESERVA_SEGUNDOS_V1,
        frescura_segundos=FRESCURA_RESERVAS_SEGUNDOS_V1,
        margen_gracia_segundos=MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS_V1,
    ):
        self.remoto = remoto
        self.id_cliente = id_cliente
        self.alias = alias
        self.hostname = hostname
        self.user_name = user_name
        self.reloj = reloj if reloj is not None else ahora_utc
        self.operation_id_proveedor = (
            operation_id_proveedor
            if operation_id_proveedor is not None
            else (lambda: str(uuid.uuid4()))
        )
        self.coordinador = (
            coordinador if coordinador is not None
            else CoordinadorOperacionesRed()
        )
        self.ttl_segundos = ttl_segundos
        self.renovacion_segundos = renovacion_segundos
        self.margen_minimo_segundos = margen_minimo_segundos
        self.frescura_segundos = frescura_segundos
        self.margen_gracia_segundos = margen_gracia_segundos
        self._cache: dict[str, _EstadoCacheReserva] = {}

    # -- Helpers internos ----------------------------------------

    def _ahora(self):
        """Instante actual UTC segun el reloj inyectado."""

        instante = self.reloj()
        if instante.tzinfo is None:
            # Fail-safe: un reloj naive no debe producir timestamps
            # naive. Se fuerza UTC.
            instante = instante.replace(tzinfo=timezone.utc)
        return instante

    def _nuevo_operation_id(self):
        """Genera un operation_id UUID4 canonico."""

        return str(self.operation_id_proveedor())

    def _clave_cache(self, clave_objeto):
        """Clave de cache por objeto (clave canonica)."""

        return clave_objeto

    def _guardar_cache(
        self, clave_objeto, clasificacion, payload, parent
    ):
        """Guarda el ultimo estado verificado en memoria."""

        self._cache[self._clave_cache(clave_objeto)] = (
            _EstadoCacheReserva(
                clasificacion=clasificacion,
                payload=payload,
                parent=parent,
                verificacion=self._ahora(),
            )
        )

    def _bloqueado_por_mutex(self):
        """Construye el resultado de consulta cuando el mutex esta ocupado."""

        return ResultadoConsultaReserva(
            exitoso=False,
            clasificacion=(
                ClasificacionReservaObservada.OPERACION_EN_CURSO
            ),
            mensaje=(
                "Ya hay una operacion de red en curso; "
                "no se inicia otra."
            ),
            error="mutex de red ocupado",
        )

    def _lectura_remota(self, project_uuid, clave_objeto):
        """
        Ejecuta Fetch + lectura/validacion del head.

        Requiere que el mutex de reservas YA este adquirido.

        Devuelve (clasificacion, payload, parent, mensaje, error).
        Nunca devuelve LIBRE ante backend no verificable.
        """

        ok_fetch, mensaje_fetch = self.remoto.fetch_reservas()
        if not ok_fetch:
            return (
                ClasificacionReservaObservada.NO_VERIFICABLE,
                None,
                "",
                mensaje_fetch,
                mensaje_fetch,
            )

        lectura = self.remoto.leer_head_reserva(
            project_uuid,
            clave_objeto,
            id_cliente_local=self.id_cliente,
            ttl_segundos=self.ttl_segundos,
            ahora=self._ahora(),
        )
        if not lectura.exitoso:
            return (
                ClasificacionReservaObservada.NO_VERIFICABLE,
                None,
                "",
                lectura.mensaje,
                lectura.error,
            )
        return (
            lectura.clasificacion,
            lectura.payload,
            lectura.parent,
            lectura.mensaje,
            lectura.error,
        )

    # -- Helpers de idempotencia ----------------------------------

    def _resolver_operation_id(self, operation_id):
        """Resuelve el operation_id: si es None genera uno nuevo.
        Si se proporciona, valida que sea UUID4 canonico."""
        if operation_id is None:
            return self._nuevo_operation_id()
        if not _es_uuid4_canonico(operation_id):
            return None
        return operation_id

    def _idempotencia_de_lectura(
        self,
        clasificacion,
        payload,
        parent,
        project_uuid,
        clave_objeto,
        operation_id,
        estado_esperado,
        id_cliente_esperado,
    ):
        """Reconoce un reintento logico ya aplicado en el head leido.

        Si el head ya contiene ese mismo operation_id:

        - intencion compatible (project_uuid, clave_objeto,
          estado/intencion e id_cliente esperados) -> exito
          idempotente, SIN crear otro commit;
        - payload incompatible -> NO_VERIFICABLE, BLOQUEAR.

        Si el head no contiene ese operation_id devuelve None y el
        flujo normal de la operacion continua.
        """
        if payload is None or payload.operation_id != operation_id:
            return None
        if self._payload_coincide_intencion(
            payload,
            project_uuid,
            clave_objeto,
            estado_esperado,
            id_cliente_esperado,
        ):
            self._guardar_cache(
                clave_objeto, clasificacion, payload, parent
            )
            return ResultadoOperacionReserva(
                exitoso=True,
                operacion="idempotencia",
                clasificacion=clasificacion,
                operation_id=operation_id,
                parent=parent,
                mensaje=(
                    "Exito idempotente: el operation_id ya fue "
                    "aplicado en el head remoto."
                ),
            )
        return ResultadoOperacionReserva(
            exitoso=False,
            operacion="idempotencia",
            clasificacion=ClasificacionReservaObservada.NO_VERIFICABLE,
            operation_id=operation_id,
            parent=parent,
            mensaje=(
                "operation_id coincidente con payload "
                "incompatible; no se reconoce como aplicado."
            ),
            error="payload incompatible",
        )

    # -- Consultar -------------------------------------------------

    def consultar_reserva(self, project_uuid, clave_objeto):
        """
        Consulta el estado remoto verificado de un objeto.

        Flujo obligatorio:

            adquirir coordinador de red
            Fetch
            leer/validar head
            clasificar
            actualizar cache local verificada
            liberar coordinador en finally

        Si el Fetch falla: NO_VERIFICABLE. Nunca devuelve LIBRE
        ante backend no verificable.
        """

        if self.coordinador.ocupado():
            return self._bloqueado_por_mutex()
        if not self.coordinador.intentar_iniciar_reservas():
            return self._bloqueado_por_mutex()

        try:
            clasificacion, payload, parent, mensaje, error = (
                self._lectura_remota(project_uuid, clave_objeto)
            )
            self._guardar_cache(
                clave_objeto, clasificacion, payload, parent
            )
            return ResultadoConsultaReserva(
                exitoso=(
                    clasificacion
                    is not ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                clasificacion=clasificacion,
                payload=payload,
                parent=parent,
                mensaje=mensaje,
                error=error,
            )
        finally:
            self.coordinador.finalizar_reservas()

    # -- Reconciliacion -------------------------------------------

    def _reconciliar(
        self,
        project_uuid,
        clave_objeto,
        operation_id,
        estado_esperado,
        id_cliente_esperado,
        oid_publicado,
    ):
        """
        Reconcilia un Push no concluyente.

        Requiere que el mutex de reservas YA este adquirido.

        Secuencia:

        1. intentar Fetch;
        2. releer el head;
        3. si el head contiene el mismo operation_id y el payload
           coincide con la operacion esperada: exito reconciliado;
        4. si el head avanzo a otra operacion: carrera perdida,
           reevaluar estado real;
        5. si el remoto no puede verificarse: RESULTADO_INCIERTO.

        Devuelve (clasificacion_resultado, exitoso, mensaje, error).
        """

        ok_fetch, mensaje_fetch = self.remoto.fetch_reservas()
        if not ok_fetch:
            return (
                ClasificacionReservaObservada.RESULTADO_INCIERTO,
                False,
                "Push no concluyente y Fetch imposible; "
                "resultado incierto.",
                mensaje_fetch,
            )

        lectura = self.remoto.leer_head_reserva(
            project_uuid,
            clave_objeto,
            id_cliente_local=self.id_cliente,
            ttl_segundos=self.ttl_segundos,
            ahora=self._ahora(),
        )
        if not lectura.exitoso:
            return (
                ClasificacionReservaObservada.RESULTADO_INCIERTO,
                False,
                "Push no concluyente y head no verificable; "
                "resultado incierto.",
                lectura.error,
            )

        payload = lectura.payload
        if payload is not None and payload.operation_id == operation_id:
            # Mismo operation_id: debe coincidir la intencion.
            if self._payload_coincide_intencion(
                payload,
                project_uuid,
                clave_objeto,
                estado_esperado,
                id_cliente_esperado,
            ):
                return (
                    lectura.clasificacion,
                    True,
                    "Push reconciliado por operation_id.",
                    "",
                )
            return (
                ClasificacionReservaObservada.NO_VERIFICABLE,
                False,
                "operation_id coincidente con payload "
                "incompatible; no se reconcilia como exito.",
                "payload incompatible",
            )

        # Otro commit gano (o no hay payload): carrera perdida.
        return (
            lectura.clasificacion,
            False,
            "El head avanzo a otra operacion; carrera perdida. "
            "Reevaluar estado real.",
            "",
        )

    def _payload_coincide_intencion(
        self,
        payload,
        project_uuid,
        clave_objeto,
        estado_esperado,
        id_cliente_esperado,
    ):
        """Comprueba que el payload coincide con la intencion."""

        return (
            payload.project_uuid == project_uuid
            and payload.clave_objeto == clave_objeto
            and payload.estado is estado_esperado
            and payload.id_cliente == id_cliente_esperado
        )

    def _publicar_y_reconciliar(
        self,
        project_uuid,
        clave_objeto,
        payload,
        parent,
        operacion,
        operation_id,
        estado_esperado,
        id_cliente_esperado,
    ):
        """
        Crea el commit tecnico, lo publica y reconcilia si es
        necesario.

        Requiere que el mutex de reservas YA este adquirido.

        Devuelve ResultadoOperacionReserva.
        """

        ok_commit, oid, mensaje_commit, error_commit = (
            self.remoto.crear_commit_reserva(payload, parent)
        )
        if not ok_commit:
            return ResultadoOperacionReserva(
                exitoso=False,
                operacion=operacion,
                clasificacion=(
                    ClasificacionReservaObservada.NO_VERIFICABLE
                ),
                operation_id=operation_id,
                parent=parent,
                mensaje=mensaje_commit,
                error=error_commit,
            )

        publicacion = self.remoto.publicar_reserva(
            oid, project_uuid, clave_objeto
        )
        if publicacion.exitoso:
            # Verificacion suficiente posterior al Push.
            ok_fetch, mensaje_fetch = self.remoto.fetch_reservas()
            if not ok_fetch:
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion=operacion,
                    clasificacion=(
                        ClasificacionReservaObservada.RESULTADO_INCIERTO
                    ),
                    operation_id=operation_id,
                    parent=parent,
                    oid_publicado=oid,
                    mensaje=(
                        "Push exitoso pero sin verificacion "
                        "posterior posible; resultado incierto."
                    ),
                    error=mensaje_fetch,
                )
            lectura = self.remoto.leer_head_reserva(
                project_uuid,
                clave_objeto,
                id_cliente_local=self.id_cliente,
                ttl_segundos=self.ttl_segundos,
                ahora=self._ahora(),
            )
            if (
                lectura.exitoso
                and lectura.payload is not None
                and lectura.payload.operation_id == operation_id
            ):
                if self._payload_coincide_intencion(
                    lectura.payload,
                    project_uuid,
                    clave_objeto,
                    estado_esperado,
                    id_cliente_esperado,
                ):
                    self._guardar_cache(
                        clave_objeto,
                        lectura.clasificacion,
                        lectura.payload,
                        lectura.parent,
                    )
                    return ResultadoOperacionReserva(
                        exitoso=True,
                        operacion=operacion,
                        clasificacion=lectura.clasificacion,
                        operation_id=operation_id,
                        parent=parent,
                        oid_publicado=oid,
                        mensaje=(
                            "Reserva publicada y verificada "
                            "en el remoto."
                        ),
                    )
                # operation_id coincide pero payload incompatible
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion=operacion,
                    clasificacion=(
                        ClasificacionReservaObservada.NO_VERIFICABLE
                    ),
                    operation_id=operation_id,
                    parent=parent,
                    oid_publicado=oid,
                    mensaje=(
                        "operation_id coincidente pero payload "
                        "incompatible en head tras push."
                    ),
                    error="payload incompatible tras push",
                )
            return ResultadoOperacionReserva(
                exitoso=False,
                operacion=operacion,
                clasificacion=(
                    ClasificacionReservaObservada.RESULTADO_INCIERTO
                ),
                operation_id=operation_id,
                parent=parent,
                oid_publicado=oid,
                mensaje=(
                    "Push exitoso pero el head remoto no coincide "
                    "con la operacion; resultado incierto."
                ),
                error="head incoherente tras push",
            )

        # Push no exitoso: reconciliar.
        clasificacion, exitoso, mensaje, error = self._reconciliar(
            project_uuid,
            clave_objeto,
            operation_id,
            estado_esperado,
            id_cliente_esperado,
            oid,
        )
        if exitoso:
            self._guardar_cache(
                clave_objeto, clasificacion, payload, parent
            )
        return ResultadoOperacionReserva(
            exitoso=exitoso,
            operacion=operacion,
            clasificacion=clasificacion,
            operation_id=operation_id,
            parent=parent,
            oid_publicado=oid,
            mensaje=mensaje,
            error=error,
        )

    # -- Reservar --------------------------------------------------

    def reservar(self, project_uuid, clave_objeto, rutas=(), operation_id=None):
        """
        Reserva un objeto.

        Si operation_id se proporciona, se valida como UUID4
        canonico y se reutiliza exactamente. Si ya existe en el
        head con la intencion correcta, se devuelve exito
        idempotente sin crear otro commit.
        """

        if self.coordinador.ocupado():
            return self._operacion_bloqueada("reservar")
        if not self.coordinador.intentar_iniciar_reservas():
            return self._operacion_bloqueada("reservar")

        try:
            clasificacion, payload, parent, mensaje, error = (
                self._lectura_remota(project_uuid, clave_objeto)
            )

            if clasificacion is (
                ClasificacionReservaObservada.NO_VERIFICABLE
            ):
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="reservar",
                    clasificacion=clasificacion,
                    mensaje=mensaje,
                    error=error,
                )

            # Resolver/validar operation_id y reconocer reintentos
            # ya aplicados ANTES de las ramas de clasificacion: el
            # mismo intento logico no debe crear un segundo commit.
            op_id = self._resolver_operation_id(operation_id)
            if op_id is None:
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="reservar",
                    clasificacion=ClasificacionReservaObservada.NO_VERIFICABLE,
                    mensaje="operation_id proporcionado no es UUID4 canonico.",
                    error="operation_id invalido",
                )
            reconocido = self._idempotencia_de_lectura(
                clasificacion, payload, parent,
                project_uuid, clave_objeto, op_id,
                EstadoReservaPersistido.ACTIVA, self.id_cliente,
            )
            if reconocido is not None:
                return reconocido

            if clasificacion is (
                ClasificacionReservaObservada.RESERVADO_POR_MI
            ):
                self._guardar_cache(
                    clave_objeto, clasificacion, payload, parent
                )
                return ResultadoOperacionReserva(
                    exitoso=True,
                    operacion="reservar",
                    clasificacion=clasificacion,
                    parent=parent,
                    mensaje=(
                        "El objeto ya esta reservado por este "
                        "cliente; no se necesita ninguna accion."
                    ),
                )

            if clasificacion is (
                ClasificacionReservaObservada.RESERVADO_POR_OTRO
            ):
                self._guardar_cache(
                    clave_objeto, clasificacion, payload, parent
                )
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="reservar",
                    clasificacion=clasificacion,
                    parent=parent,
                    mensaje=(
                        "El objeto esta reservado por otro "
                        "miembro del equipo; BLOQUEADO."
                    ),
                )

            if clasificacion in (
                ClasificacionReservaObservada.VENCIDO_PROPIO,
                ClasificacionReservaObservada.VENCIDO_AJENO,
            ):
                self._guardar_cache(
                    clave_objeto, clasificacion, payload, parent
                )
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="reservar",
                    clasificacion=clasificacion,
                    parent=parent,
                    mensaje=(
                        "La reserva previa esta vencida; no se "
                        "usa reservar(): use tomar_vencida()."
                    ),
                )

            # LIBRE: usar el operation_id ya resuelto y verificado.
            ahora = self._ahora()
            vencimiento = ahora + timedelta(seconds=self.ttl_segundos)
            rutas_ordenadas = tuple(sorted(set(rutas)))
            payload_nuevo = ReservaPayloadV1(
                format_version=1,
                operation_id=op_id,
                project_uuid=project_uuid,
                clave_objeto=clave_objeto,
                estado=EstadoReservaPersistido.ACTIVA,
                id_cliente=self.id_cliente,
                alias=self.alias,
                hostname=self.hostname,
                user_name=self.user_name,
                inicio=formatear_timestamp_utc(ahora),
                heartbeat=formatear_timestamp_utc(ahora),
                vencimiento=formatear_timestamp_utc(vencimiento),
                rama_local="",
                rutas=rutas_ordenadas,
            )

            return self._publicar_y_reconciliar(
                project_uuid,
                clave_objeto,
                payload_nuevo,
                parent,
                "reservar",
                op_id,
                EstadoReservaPersistido.ACTIVA,
                self.id_cliente,
            )
        finally:
            self.coordinador.finalizar_reservas()

    # -- Renovar ---------------------------------------------------

    def renovar(self, project_uuid, clave_objeto, operation_id=None):
        """
        Renueva una reserva propia ACTIVA todavia no vencida.

        Si operation_id se proporciona, se valida y reutiliza.
        """

        if self.coordinador.ocupado():
            return self._operacion_bloqueada("renovar")
        if not self.coordinador.intentar_iniciar_reservas():
            return self._operacion_bloqueada("renovar")

        try:
            clasificacion, payload, parent, mensaje, error = (
                self._lectura_remota(project_uuid, clave_objeto)
            )

            if clasificacion is (
                ClasificacionReservaObservada.NO_VERIFICABLE
            ):
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="renovar",
                    clasificacion=clasificacion,
                    mensaje=mensaje,
                    error=error,
                )

            # Resolver/validar operation_id y reconocer reintentos
            # ya aplicados ANTES de las ramas de clasificacion.
            op_id = self._resolver_operation_id(operation_id)
            if op_id is None:
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="renovar",
                    clasificacion=ClasificacionReservaObservada.NO_VERIFICABLE,
                    mensaje="operation_id no es UUID4 canonico.",
                    error="operation_id invalido",
                )
            reconocido = self._idempotencia_de_lectura(
                clasificacion, payload, parent,
                project_uuid, clave_objeto, op_id,
                EstadoReservaPersistido.ACTIVA, self.id_cliente,
            )
            if reconocido is not None:
                return reconocido

            if clasificacion is (
                ClasificacionReservaObservada.RESERVADO_POR_MI
            ):
                ahora = self._ahora()
                vencimiento = ahora + timedelta(seconds=self.ttl_segundos)
                payload_nuevo = ReservaPayloadV1(
                    format_version=1,
                    operation_id=op_id,
                    project_uuid=project_uuid,
                    clave_objeto=clave_objeto,
                    estado=EstadoReservaPersistido.ACTIVA,
                    id_cliente=self.id_cliente,
                    alias=self.alias,
                    hostname=self.hostname,
                    user_name=self.user_name,
                    inicio=payload.inicio,
                    heartbeat=formatear_timestamp_utc(ahora),
                    vencimiento=formatear_timestamp_utc(vencimiento),
                    rama_local=payload.rama_local,
                    rutas=payload.rutas,
                )
                return self._publicar_y_reconciliar(
                    project_uuid,
                    clave_objeto,
                    payload_nuevo,
                    parent,
                    "renovar",
                    op_id,
                    EstadoReservaPersistido.ACTIVA,
                    self.id_cliente,
                )

            if clasificacion is (
                ClasificacionReservaObservada.VENCIDO_PROPIO
            ):
                self._guardar_cache(
                    clave_objeto, clasificacion, payload, parent
                )
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="renovar",
                    clasificacion=clasificacion,
                    parent=parent,
                    mensaje=(
                        "Una reserva propia vencida no se renueva: "
                        "use tomar_vencida()."
                    ),
                )

            self._guardar_cache(
                clave_objeto, clasificacion, payload, parent
            )
            return ResultadoOperacionReserva(
                exitoso=False,
                operacion="renovar",
                clasificacion=clasificacion,
                parent=parent,
                mensaje=(
                    "Solo puede renovarse una reserva propia "
                    "ACTIVA vigente."
                ),
            )
        finally:
            self.coordinador.finalizar_reservas()

    # -- Liberar ---------------------------------------------------

    def liberar(self, project_uuid, clave_objeto, operation_id=None):
        """
        Libera una reserva propia ACTIVA.

        Si operation_id se proporciona, se valida y reutiliza.
        """

        if self.coordinador.ocupado():
            return self._operacion_bloqueada("liberar")
        if not self.coordinador.intentar_iniciar_reservas():
            return self._operacion_bloqueada("liberar")

        try:
            clasificacion, payload, parent, mensaje, error = (
                self._lectura_remota(project_uuid, clave_objeto)
            )

            if clasificacion is (
                ClasificacionReservaObservada.NO_VERIFICABLE
            ):
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="liberar",
                    clasificacion=clasificacion,
                    mensaje=mensaje,
                    error=error,
                )

            # Resolver/validar operation_id y reconocer reintentos
            # ya aplicados ANTES de las ramas de clasificacion: un
            # reintento de liberar debe reconocer la LIBERADA ya
            # publicada en el head (clasificada como LIBRE).
            op_id = self._resolver_operation_id(operation_id)
            if op_id is None:
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="liberar",
                    clasificacion=ClasificacionReservaObservada.NO_VERIFICABLE,
                    mensaje="operation_id no es UUID4 canonico.",
                    error="operation_id invalido",
                )
            reconocido = self._idempotencia_de_lectura(
                clasificacion, payload, parent,
                project_uuid, clave_objeto, op_id,
                EstadoReservaPersistido.LIBERADA, self.id_cliente,
            )
            if reconocido is not None:
                return reconocido

            if clasificacion is (
                ClasificacionReservaObservada.RESERVADO_POR_MI
            ):
                ahora = self._ahora()
                payload_nuevo = ReservaPayloadV1(
                    format_version=1,
                    operation_id=op_id,
                    project_uuid=project_uuid,
                    clave_objeto=clave_objeto,
                    estado=EstadoReservaPersistido.LIBERADA,
                    id_cliente=self.id_cliente,
                    alias=self.alias,
                    hostname=self.hostname,
                    user_name=self.user_name,
                    inicio=payload.inicio,
                    heartbeat=formatear_timestamp_utc(ahora),
                    vencimiento=formatear_timestamp_utc(ahora),
                    rama_local=payload.rama_local,
                    rutas=payload.rutas,
                )
                return self._publicar_y_reconciliar(
                    project_uuid,
                    clave_objeto,
                    payload_nuevo,
                    parent,
                    "liberar",
                    op_id,
                    EstadoReservaPersistido.LIBERADA,
                    self.id_cliente,
                )

            self._guardar_cache(
                clave_objeto, clasificacion, payload, parent
            )
            return ResultadoOperacionReserva(
                exitoso=False,
                operacion="liberar",
                clasificacion=clasificacion,
                parent=parent,
                mensaje=(
                    "Solo puede liberarse una reserva propia "
                    "ACTIVA vigente."
                ),
            )
        finally:
            self.coordinador.finalizar_reservas()

    # -- Tomar vencida ---------------------------------------------

    def tomar_vencida(self, project_uuid, clave_objeto, operation_id=None):
        """
        Toma una reserva vencida (propia o ajena).

        Si operation_id se proporciona, se valida y reutiliza.
        """

        if self.coordinador.ocupado():
            return self._operacion_bloqueada("tomar_vencida")
        if not self.coordinador.intentar_iniciar_reservas():
            return self._operacion_bloqueada("tomar_vencida")

        try:
            clasificacion, payload, parent, mensaje, error = (
                self._lectura_remota(project_uuid, clave_objeto)
            )

            if clasificacion is (
                ClasificacionReservaObservada.NO_VERIFICABLE
            ):
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="tomar_vencida",
                    clasificacion=clasificacion,
                    mensaje=mensaje,
                    error=error,
                )

            # Resolver/validar operation_id y reconocer reintentos
            # ya aplicados ANTES de las ramas de clasificacion: un
            # reintento de tomar_vencida debe reconocer la nueva
            # ACTIVA propia ya publicada en el head.
            op_id = self._resolver_operation_id(operation_id)
            if op_id is None:
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="tomar_vencida",
                    clasificacion=ClasificacionReservaObservada.NO_VERIFICABLE,
                    mensaje="operation_id no es UUID4 canonico.",
                    error="operation_id invalido",
                )
            reconocido = self._idempotencia_de_lectura(
                clasificacion, payload, parent,
                project_uuid, clave_objeto, op_id,
                EstadoReservaPersistido.ACTIVA, self.id_cliente,
            )
            if reconocido is not None:
                return reconocido

            if clasificacion not in (
                ClasificacionReservaObservada.VENCIDO_PROPIO,
                ClasificacionReservaObservada.VENCIDO_AJENO,
            ):
                self._guardar_cache(
                    clave_objeto, clasificacion, payload, parent
                )
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="tomar_vencida",
                    clasificacion=clasificacion,
                    parent=parent,
                    mensaje=(
                        "No hay una reserva vencida que tomar."
                    ),
                )

            vencimiento = parsear_timestamp_utc(payload.vencimiento)
            ahora = self._ahora()
            if vencimiento is None:
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="tomar_vencida",
                    clasificacion=(
                        ClasificacionReservaObservada.NO_VERIFICABLE
                    ),
                    mensaje="Vencimiento del payload invalido.",
                )

            grace = timedelta(seconds=self.margen_gracia_segundos)
            if ahora < vencimiento + grace:
                self._guardar_cache(
                    clave_objeto, clasificacion, payload, parent
                )
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="tomar_vencida",
                    clasificacion=clasificacion,
                    parent=parent,
                    mensaje=(
                        "La reserva esta vencida pero aun dentro "
                        "del margen de gracia; BLOQUEADO."
                    ),
                )

            op_id = self._resolver_operation_id(operation_id)
            if op_id is None:
                return ResultadoOperacionReserva(
                    exitoso=False,
                    operacion="tomar_vencida",
                    clasificacion=ClasificacionReservaObservada.NO_VERIFICABLE,
                    mensaje="operation_id no es UUID4 canonico.",
                    error="operation_id invalido",
                )
            vencimiento_nuevo = ahora + timedelta(
                seconds=self.ttl_segundos
            )
            payload_nuevo = ReservaPayloadV1(
                format_version=1,
                operation_id=op_id,
                project_uuid=project_uuid,
                clave_objeto=clave_objeto,
                estado=EstadoReservaPersistido.ACTIVA,
                id_cliente=self.id_cliente,
                alias=self.alias,
                hostname=self.hostname,
                user_name=self.user_name,
                inicio=formatear_timestamp_utc(ahora),
                heartbeat=formatear_timestamp_utc(ahora),
                vencimiento=formatear_timestamp_utc(vencimiento_nuevo),
                rama_local="",
                rutas=(),
            )
            return self._publicar_y_reconciliar(
                project_uuid,
                clave_objeto,
                payload_nuevo,
                parent,
                "tomar_vencida",
                op_id,
                EstadoReservaPersistido.ACTIVA,
                self.id_cliente,
            )
        finally:
            self.coordinador.finalizar_reservas()

    # -- Validacion local 100% -------------------------------------

    def validar_reserva_propia_fresca(self, clave_objeto):
        """
        Valida localmente, SIN red, que existe una reserva propia
        fresca.

        Solo devuelve autorizacion positiva si TODO se cumple:

            ultima consulta valida
            estado ACTIVA
            id_cliente == local
            clasificacion RESERVADO_POR_MI
            edad de verificacion <= frescura (60 s)
            reserva no vencida
            tiempo restante >= margen minimo (300 s)
            resultado no incierto
            no hay operacion de reservas en curso

        Nunca hace Fetch. El cache nunca autoriza un LIBRE.
        """

        if (
            self.coordinador.ocupado()
            or self.coordinador.operacion_reservas_en_curso
        ):
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo=(
                    "Hay una operacion de reservas o de red "
                    "en curso; validacion bloqueada."
                ),
            )

        estado_cache = self._cache.get(
            self._clave_cache(clave_objeto)
        )
        if estado_cache is None:
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo="No hay una consulta previa verificada.",
            )

        if (
            estado_cache.clasificacion
            is ClasificacionReservaObservada.RESULTADO_INCIERTO
        ):
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo="Resultado incierto; no se puede autorizar.",
            )

        if (
            estado_cache.clasificacion
            is not ClasificacionReservaObservada.RESERVADO_POR_MI
        ):
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo=(
                    "La ultima clasificacion no es "
                    "RESERVADO_POR_MI."
                ),
            )

        payload = estado_cache.payload
        if payload is None or not payload.es_activa():
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo="La reserva no esta ACTIVA.",
            )

        if payload.id_cliente != self.id_cliente:
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo="La reserva pertenece a otro id_cliente.",
            )

        ahora = self._ahora()

        vencimiento = parsear_timestamp_utc(payload.vencimiento)
        if vencimiento is None:
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo="Vencimiento del payload invalido.",
            )
        if ahora >= vencimiento:
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo="La reserva esta vencida.",
            )

        restante = (vencimiento - ahora).total_seconds()
        if restante < self.margen_minimo_segundos:
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo=(
                    "Tiempo restante menor al margen minimo "
                    f"({self.margen_minimo_segundos} s)."
                ),
                tiempo_restante=int(restante),
            )

        verificacion = estado_cache.verificacion
        edad = 0
        if verificacion is not None:
            try:
                edad = (ahora - verificacion).total_seconds()
            except TypeError:
                edad = self.frescura_segundos + 1
        if edad > self.frescura_segundos:
            return ResultadoValidacionReservaPropia(
                valida=False,
                motivo=(
                    f"Verificacion con mas de {self.frescura_segundos} s "
                    "de frescura."
                ),
                edad_verificacion=int(edad),
            )

        return ResultadoValidacionReservaPropia(
            valida=True,
            motivo="Reserva propia fresca valida.",
            tiempo_restante=int(restante),
            edad_verificacion=int(edad),
        )

    # -- Politica de renovacion ------------------------------------

    def debe_renovar(self, clave_objeto):
        """
        Consulta local determinista: devuelve True si la reserva
        propia verificada necesita renovacion segun:

            RENOVACION_RESERVAS_SEGUNDOS_V1 = 600

        No crea scheduler ni thread: es solo politica para la GUI
        futura. No hace red.
        """

        estado_cache = self._cache.get(
            self._clave_cache(clave_objeto)
        )
        if estado_cache is None:
            return False
        if (
            estado_cache.clasificacion
            is not ClasificacionReservaObservada.RESERVADO_POR_MI
        ):
            return False
        payload = estado_cache.payload
        if payload is None or not payload.es_activa():
            return False
        if payload.id_cliente != self.id_cliente:
            return False

        vencimiento = parsear_timestamp_utc(payload.vencimiento)
        if vencimiento is None:
            return False
        ahora = self._ahora()
        if ahora >= vencimiento:
            return False
        restante = (vencimiento - ahora).total_seconds()
        return restante <= self.renovacion_segundos

    # -- Aviso pedagogico de reservas propias (Bloque G) -----------

    def listar_reservas_propias_conocidas(self, project_uuid):
        """
        Lista snapshots de solo lectura de reservas PROPIAS ACTIVAS
        conocidas localmente en esta sesion (Bloque G).

        100% local: sin red, sin coordinador/mutex, sin efectos
        secundarios y sin modificar el cache. Una entrada cuenta
        unicamente si TODO se cumple:

            clasificacion RESERVADO_POR_MI
            payload existe y es_activa()
            payload.id_cliente == id_cliente local
            payload.project_uuid == project_uuid solicitado
            vencimiento parseable y todavia no alcanzado

        No exige la frescura ni el margen minimo de staging/commit:
        eso es autorizacion (validar_reserva_propia_fresca); esto
        es SOLO un aviso pedagogico y nunca autoriza nada.

        Robustez: cada entrada se procesa de forma independiente;
        una entrada defectuosa se ignora sin eliminar las demas.
        Cualquier fallo global inesperado devuelve una coleccion
        vacia para que el aviso nunca se convierta en barrera de
        la operacion Git.

        Devuelve una tupla ordenada de forma determinista por
        clave_objeto. No devuelve _EstadoCacheReserva, el cache ni
        el ReservaPayloadV1 almacenado.
        """

        if not project_uuid:
            return ()

        reservas = []
        try:
            for clave_objeto in sorted(self._cache):
                estado = self._cache.get(clave_objeto)
                snapshot = self._snapshot_reserva_propia_conocida(
                    project_uuid, clave_objeto, estado
                )
                if snapshot is not None:
                    reservas.append(snapshot)
        except Exception:
            # Fail-safe del aviso: una falla inesperada del helper
            # informativo no debe bloquear la operacion Git.
            return ()
        return tuple(reservas)

    def _snapshot_reserva_propia_conocida(
        self, project_uuid, clave_objeto, estado
    ):
        """
        Construye el snapshot de una entrada del cache si cualifica
        como reserva propia activa conocida; si no, None.

        Aisla cada entrada: una entrada defectuosa no afecta a las
        demas ni propaga excepciones a la GUI.
        """

        try:
            if estado is None:
                return None
            if (
                estado.clasificacion
                is not ClasificacionReservaObservada.RESERVADO_POR_MI
            ):
                return None
            payload = estado.payload
            if payload is None:
                return None
            if not payload.es_activa():
                return None
            if payload.id_cliente != self.id_cliente:
                return None
            if payload.project_uuid != project_uuid:
                return None
            vencimiento = parsear_timestamp_utc(payload.vencimiento)
            if vencimiento is None:
                return None
            if self._ahora() >= vencimiento:
                return None
            return ReservaPropiaConocida(
                project_uuid=payload.project_uuid,
                clave_objeto=clave_objeto,
                vencimiento=payload.vencimiento,
                alias=payload.alias,
            )
        except Exception:
            # Entrada defectuosa: se ignora sin eliminar las demas.
            return None

    # -- Helper de operacion bloqueada -----------------------------

    def _operacion_bloqueada(self, operacion):
        """Resultado de operacion cuando el mutex esta ocupado."""

        return ResultadoOperacionReserva(
            exitoso=False,
            operacion=operacion,
            clasificacion=(
                ClasificacionReservaObservada.OPERACION_EN_CURSO
            ),
            mensaje=(
                "Ya hay una operacion de red en curso; "
                "no se inicia otra."
            ),
            error="mutex de red ocupado",
        )
