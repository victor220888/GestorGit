"""
Modelos de datos del backend local de reservas de Modo Equipo
Oracle V1.

Contiene el resultado estructurado de las operaciones locales
sobre el repositorio Git bare de reservas.

No modela reservas remotas, estados de objeto, TTL, payloads
ni commit-tree. Esos modelos viven en otros modulos de Modo
Equipo y se incorporaran en bloques posteriores.
"""

from dataclasses import dataclass


@dataclass
class ResultadoBackendReservas:
    """
    Resultado controlado de una operacion local del backend
    de reservas.

    Todos los errores previsibles (validacion de entradas, Git,
    sistema operativo, timeout) se representan como un resultado
    no exitoso con mensaje y error, sin propagar excepciones
    hacia la GUI o el orquestador.

    Atributos:
        exitoso: True si la operacion local se completo y se
            verifico. False en cualquier otro caso.
        ruta_backend: ruta absoluta canonica del repositorio
            bare de reservas cuando exitoso; cadena vacia en
            caso de error.
        mensaje: mensaje pedagogico para el usuario.
        error: detalle tecnico del error, sin secretos ni
            credenciales.
    """

    exitoso: bool
    ruta_backend: str = ""
    mensaje: str = ""
    error: str = ""
