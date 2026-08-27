"""
Modelos de datos de la configuracion de Gestor Git.

La configuracion local recuerda:

- el ultimo repositorio seleccionado por el usuario;
- los parametros del Modo Equipo Oracle V1.

Nunca guarda credenciales, tokens, contrasenias ni correos.
Si puede guardar la URL tecnica del backend de reservas, que se
almacena siempre sin credenciales embebidas: la autenticacion
queda delegada a Git y la informacion de Git Credential Manager
nunca se guarda aqui.

La identidad tecnica de instalacion (id_cliente) NO vive en
config.json: vive en su propio archivo gestionado por
ServicioIdentidadEquipo.
"""

from dataclasses import dataclass


# Valores canonicos aprobados para V1.
# Cualquier valor divergente en config.json debe ser rechazado
# de forma controlada en V1.
TTL_RESERVAS_SEGUNDOS_V1 = 1800
RENOVACION_RESERVAS_SEGUNDOS_V1 = 600
MARGEN_MINIMO_RESERVA_SEGUNDOS_V1 = 300
FRESCURA_RESERVAS_SEGUNDOS_V1 = 60
MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS_V1 = 600


@dataclass
class ResultadoConfiguracion:
    """
    Resultado de una operacion de lectura o escritura
    de la configuracion del ultimo repositorio.

    Mantiene compatibilidad con el modelo publico historico.
    """

    exitoso: bool
    ruta_repositorio: str = ""
    mensaje: str = ""
    error: str = ""


@dataclass
class ConfiguracionModoEquipo:
    """
    Configuracion local del Modo Equipo Oracle V1.

    Los valores temporales son canonicos en V1 y no admiten
    divergencia silenciosa: si config.json contiene un valor
    distinto, la carga falla de forma controlada.

    El backend_reservas_url es la URL del repositorio Git bare
    de reservas. En V1 solo se almacena y valida sintacticamente:
    no se realiza ninguna conexion.
    """

    modo_equipo_habilitado: bool = False
    backend_reservas_url: str = ""
    alias_equipo: str = ""
    ttl_reservas_segundos: int = TTL_RESERVAS_SEGUNDOS_V1
    renovacion_reservas_segundos: int = RENOVACION_RESERVAS_SEGUNDOS_V1
    margen_minimo_reserva_segundos: int = MARGEN_MINIMO_RESERVA_SEGUNDOS_V1
    frescura_reservas_segundos: int = FRESCURA_RESERVAS_SEGUNDOS_V1
    margen_gracia_vencimiento_segundos: int = (
        MARGEN_GRACIA_VENCIMIENTO_SEGUNDOS_V1
    )


@dataclass
class ResultadoConfiguracionModoEquipo:
    """
    Resultado controlado de cargar o guardar la configuracion
    de Modo Equipo.
    """

    exitoso: bool
    configuracion: ConfiguracionModoEquipo | None = None
    mensaje: str = ""
    error: str = ""


@dataclass
class ResultadoIdentidadEquipo:
    """
    Resultado controlado de obtener o crear la identidad
    tecnica de instalacion.

    La identidad es un UUID v4 canonico almacenado en
    %APPDATA%\\GestorGit\\identidad_instalacion.json.

    Nunca contiene alias, backend, correo, token ni
    informacion de repositorio.
    """

    exitoso: bool
    id_cliente: str = ""
    mensaje: str = ""
    error: str = ""
