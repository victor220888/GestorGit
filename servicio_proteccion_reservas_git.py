"""
Capa de protección de reservas para staging/commit (Bloque E).

Coordina rutas Git -> resolución de objetos Oracle (lógica
existente de Bloque A) -> validación de reserva propia fresca
(lógica autoritativa de Bloque D) -> PERMITIR o BLOQUEAR con
explicación.

Esta capa:

- NO usa Tkinter ni diálogos;
- NO ejecuta comandos Git por sí misma (solo recibe rutas ya
  determinadas por la capa Git);
- NO lee configuración global ni APPDATA;
- NO duplica la política de reservas de Bloque D: delega
  exclusivamente en
  ServicioReservas.validar_reserva_propia_fresca();
- NO llama consultar_reserva, fetch_reservas, reservar, renovar,
  liberar ni tomar_vencida: la protección es 100% LOCAL, sin red,
  sin Fetch, sin renovación/reserva/liberación automáticas y sin
  Push;
- es fail-safe: ante cualquier resultado inesperado BLOQUEA, nunca
  degrada a permitido.

La integración con ServicioGit es por inyección opcional: sin
protector configurado el comportamiento histórico se conserva; con
protector configurado el staging y el commit pasan obligatoriamente
por aquí antes del primer comando Git de escritura.
"""

from dataclasses import dataclass

from modelos_reservas import (
    ResultadoResolucionObjeto,
    ResultadoValidacionReservaPropia,
)


@dataclass
class ResultadoProteccionReservasGit:
    """
    Resultado controlado de una protección de staging/commit.

    permitido:
        True solo si TODAS las rutas pueden operarse.
    operacion:
        "staging" o "commit".
    rutas:
        Rutas implicadas evaluadas (sin duplicados).
    claves:
        Claves canónicas de objetos Oracle que requirieron
        reserva y fueron validadas (vacías si no aplicó).
    motivo:
        Texto comprensible del bloqueo; vacío si permitido.
    requiere_reserva:
        True cuando el bloqueo se debe a una reserva propia
        ausente/no válida (y no a una ruta inválida o no
        resoluble).
    """

    permitido: bool
    operacion: str = ""
    rutas: tuple = ()
    claves: tuple = ()
    motivo: str = ""
    requiere_reserva: bool = False

    @staticmethod
    def permitir(operacion, rutas, claves):
        """Construye el resultado de operación permitida."""

        return ResultadoProteccionReservasGit(
            permitido=True,
            operacion=operacion,
            rutas=tuple(rutas),
            claves=tuple(claves),
            motivo="",
            requiere_reserva=False,
        )

    @staticmethod
    def bloquear(operacion, rutas, claves, motivo, requiere_reserva):
        """Construye el resultado de operación bloqueada."""

        return ResultadoProteccionReservasGit(
            permitido=False,
            operacion=operacion,
            rutas=tuple(rutas),
            claves=tuple(claves),
            motivo=motivo,
            requiere_reserva=requiere_reserva,
        )

    def componer_mensaje(self):
        """
        Compone el mensaje comprensible para la GUI futura.

        Sin tokens, credenciales, URLs con secretos, dumps
        internos ni tracebacks.
        """

        if self.permitido:
            return ""

        titulo = "staging" if self.operacion == "staging" else "commit"

        lineas = [
            f"La operación de {titulo} fue bloqueada por el "
            "Modo Equipo Oracle (reservas).",
        ]

        if self.rutas:
            lineas.append("")
            lineas.append("Rutas implicadas:")
            for ruta in self.rutas:
                lineas.append(f"- {ruta}")

        if self.claves:
            lineas.append("")
            lineas.append("Objetos Oracle implicados:")
            for clave in self.claves:
                lineas.append(f"- {clave}")

        if self.motivo:
            lineas.append("")
            lineas.append(f"Motivo: {self.motivo}")

        if self.requiere_reserva:
            lineas.append("")
            lineas.append(
                "Para operar sobre un objeto Oracle de Modo Equipo "
                "se requiere una reserva propia, verificada y "
                "fresca del objeto."
            )

        return "\n".join(lineas)


class ServicioProteccionReservasGit:
    """
    Protector 100% local de staging/commit para Modo Equipo
    Oracle V1.

    Uso tipico:

        resolvedor = ServicioObjetosOracle(manifiesto_valido)
        protector = ServicioProteccionReservasGit(
            resolvedor_oracle=resolvedor,
            servicio_reservas=servicio_reservas,
            project_uuid=project_uuid,
        )

        resultado = protector.proteger_staging(rutas)
        if not resultado.permitido:
            ...

    Dependencias inyectadas:

    resolvedor_oracle:
        Objeto con resolver(ruta) -> ResultadoResolucionObjeto
        (ServicioObjetosOracle de Bloque A). Determina si una
        ruta es ordinaria, un objeto Oracle reservable, un
        Oracle no resoluble o una ruta inválida.
    servicio_reservas:
        Objeto con validar_reserva_propia_fresca(clave_objeto)
        -> ResultadoValidacionReservaPropia (ServicioReservas de
        Bloque D). Única fuente autoritativa de la política de
        reservas; aquí NO se reimplementa.
    project_uuid:
        Contexto V1 del proyecto; informativo para esta capa.
    """

    def __init__(
        self,
        resolvedor_oracle,
        servicio_reservas,
        project_uuid="",
    ):
        if resolvedor_oracle is None or not callable(
            getattr(resolvedor_oracle, "resolver", None)
        ):
            raise ValueError(
                "El protector requiere un resolvedor de objetos "
                "Oracle con método resolver(ruta)."
            )

        if servicio_reservas is None or not callable(
            getattr(
                servicio_reservas,
                "validar_reserva_propia_fresca",
                None,
            )
        ):
            raise ValueError(
                "El protector requiere un servicio de reservas con "
                "método validar_reserva_propia_fresca(clave_objeto)."
            )

        self.resolvedor_oracle = resolvedor_oracle
        self.servicio_reservas = servicio_reservas
        self.project_uuid = project_uuid

    # -- API pública ------------------------------------------------

    def proteger_staging(self, rutas_involucradas):
        """
        Protege un staging (git add) sobre las rutas involucradas.

        El conjunto recibido debe incluir AMBOS lados de un
        renombrado/copiado cuando existan (la capa Git los
        determina con el modelo existente ruta_anterior o con una
        consulta de solo lectura).

        Devuelve ResultadoProteccionReservasGit; nunca lanza
        excepciones previsibles.
        """

        return self._proteger("staging", rutas_involucradas)

    def proteger_commit(self, rutas_staged):
        """
        Protege un commit sobre el conjunto preparado REAL.

        El conjunto recibido debe provenir de una lectura del
        índice inmediatamente previa al commit e incluir ambos
        lados de renombrados/copias.

        Devuelve ResultadoProteccionReservasGit; nunca lanza
        excepciones previsibles.
        """

        return self._proteger("commit", rutas_staged)

    # -- Núcleo -----------------------------------------------------

    def _proteger(self, operacion, rutas):
        """
        Núcleo común de protección.

        Para cada ruta:

        - no Oracle -> permitida sin reserva;
        - objeto Oracle reservable -> validar_reserva_propia_fresca
          una única vez por clave canónica (deduplicación);
        - Oracle no resoluble / ambiguo -> BLOQUEAR;
        - ruta inválida -> BLOQUEAR.

        Cualquier ruta que falle BLOQUEA la operación completa:
        nunca se permite una operación parcial.
        """

        try:
            return self._proteger_interna(operacion, rutas)
        except Exception:
            # Fail-safe estricto (REV1 FIX 4): el motivo nunca
            # incluye str(error), tracebacks ni detalle técnico.
            return ResultadoProteccionReservasGit.bloquear(
                operacion=operacion,
                rutas=(),
                claves=(),
                motivo=(
                    "La protección de reservas falló de forma "
                    "inesperada; la operación queda bloqueada por "
                    "seguridad."
                ),
                requiere_reserva=False,
            )

    def _proteger_interna(self, operacion, rutas):
        """Implementación de la protección (sin barrera final)."""

        rutas_evaluadas = self._normalizar_rutas(rutas)

        if rutas_evaluadas is None:
            return ResultadoProteccionReservasGit.bloquear(
                operacion=operacion,
                rutas=(),
                claves=(),
                motivo=(
                    "No se recibió un conjunto de rutas válido "
                    "para la protección de reservas."
                ),
                requiere_reserva=False,
            )

        claves_requeridas = []
        rutas_oracle = []
        rutas_por_clave = {}

        for ruta in rutas_evaluadas:
            resultado = self.resolvedor_oracle.resolver(ruta)

            if not isinstance(resultado, ResultadoResolucionObjeto):
                return ResultadoProteccionReservasGit.bloquear(
                    operacion=operacion,
                    rutas=(ruta,),
                    claves=(),
                    motivo=(
                        "La resolución de la ruta no devolvió un "
                        "resultado seguro; la operación queda "
                        "bloqueada."
                    ),
                    requiere_reserva=False,
                )

            if not resultado.es_ruta_valida:
                return ResultadoProteccionReservasGit.bloquear(
                    operacion=operacion,
                    rutas=(ruta,),
                    claves=(),
                    motivo=(
                        resultado.mensaje
                        or "La ruta no es una ruta relativa válida."
                    ),
                    requiere_reserva=False,
                )

            if not resultado.es_objeto_oracle:
                # Ruta ordinaria no Oracle: no requiere reserva.
                continue

            if not resultado.es_reservable or resultado.objeto is None:
                # Naturaleza Oracle pero resolución insegura:
                # nunca se interpreta como ruta ordinaria.
                rutas_oracle.append(ruta)
                return ResultadoProteccionReservasGit.bloquear(
                    operacion=operacion,
                    rutas=tuple(rutas_oracle),
                    claves=(),
                    motivo=(
                        resultado.mensaje
                        or (
                            "La ruta tiene apariencia Oracle pero "
                            "no puede resolverse de forma segura "
                            "en V1."
                        )
                    ),
                    requiere_reserva=False,
                )

            clave_canonica = resultado.objeto.canonica()

            if clave_canonica not in claves_requeridas:
                claves_requeridas.append(clave_canonica)
                rutas_por_clave[clave_canonica] = []

            if ruta not in rutas_por_clave[clave_canonica]:
                rutas_por_clave[clave_canonica].append(ruta)

            if ruta not in rutas_oracle:
                rutas_oracle.append(ruta)

        for clave_canonica in claves_requeridas:
            bloqueo = self._validar_reserva(
                operacion,
                clave_canonica,
                rutas_por_clave[clave_canonica],
            )
            if bloqueo is not None:
                return bloqueo

        return ResultadoProteccionReservasGit.permitir(
            operacion=operacion,
            rutas=rutas_evaluadas,
            claves=claves_requeridas,
        )

    def _validar_reserva(self, operacion, clave_canonica, rutas_clave):
        """
        Valida una reserva propia fresca delegando en Bloque D.

        Fail-safe estricto (REV1 FIX 3): solo autoriza un
        ResultadoValidacionReservaPropia contractual con
        valida EXACTAMENTE True. Un objeto inesperado, un
        atributo ausente, valida="true", valida=1, etc.
        BLOQUEAN; nunca se acepta truthiness.

        Devuelve None si la reserva es válida o un resultado de
        bloqueo (con las rutas implicadas) en caso contrario.
        """

        try:
            resultado_reserva = (
                self.servicio_reservas.validar_reserva_propia_fresca(
                    clave_canonica
                )
            )
        except Exception:
            return ResultadoProteccionReservasGit.bloquear(
                operacion=operacion,
                rutas=tuple(rutas_clave),
                claves=(clave_canonica,),
                motivo=(
                    "La validación de la reserva falló de forma "
                    "inesperada; la operación queda bloqueada por "
                    "seguridad."
                ),
                requiere_reserva=True,
            )

        if not isinstance(
            resultado_reserva, ResultadoValidacionReservaPropia
        ):
            return ResultadoProteccionReservasGit.bloquear(
                operacion=operacion,
                rutas=tuple(rutas_clave),
                claves=(clave_canonica,),
                motivo=(
                    "La validación de la reserva no devolvió el "
                    "resultado contractual esperado; la operación "
                    "queda bloqueada por seguridad."
                ),
                requiere_reserva=True,
            )

        if resultado_reserva.valida is not True:
            motivo = resultado_reserva.motivo or (
                "No existe una reserva propia verificada y fresca "
                "para este objeto."
            )

            return ResultadoProteccionReservasGit.bloquear(
                operacion=operacion,
                rutas=tuple(rutas_clave),
                claves=(clave_canonica,),
                motivo=motivo,
                requiere_reserva=True,
            )

        return None

    @staticmethod
    def _normalizar_rutas(rutas):
        """
        Normaliza y deduplica las rutas recibidas.

        Devuelve una tupla de strings sin duplicados o None si la
        entrada no es una colección válida. Las rutas no string,
        vacías o con NUL invalidan TODO el conjunto (fail-safe).
        """

        if rutas is None:
            return None

        if isinstance(rutas, str):
            rutas = (rutas,)

        try:
            iterador = iter(rutas)
        except TypeError:
            return None

        rutas_normales = []

        for ruta in iterador:
            if not isinstance(ruta, str):
                return None
            if not ruta or ruta.isspace():
                return None
            if "\x00" in ruta:
                return None
            if ruta not in rutas_normales:
                rutas_normales.append(ruta)

        if not rutas_normales:
            return None

        return tuple(rutas_normales)
