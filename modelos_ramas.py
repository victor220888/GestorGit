"""
Modelos del selector de ramas locales.

Definen la información mínima que devuelven las consultas y
operaciones de ramas: una rama local con su nombre y si es la
rama actual, y el resultado genérico de una operación.
"""

from dataclasses import dataclass, field


@dataclass
class RamaLocal:
    """
    Representa una rama local del repositorio.

    Atributos:
        nombre: Nombre corto de la rama (p. ej. "master").
        actual: True cuando es la rama en la que se encuentra
            HEAD actualmente.
    """

    nombre: str
    actual: bool


@dataclass
class ResultadoRamas:
    """
    Contiene el resultado de consultar o modificar ramas locales.

    Atributos:
        exitoso: True cuando la operación se completó.
        ramas: Lista de ramas locales consultadas.
        error: Motivo del bloqueo cuando exitoso es False.
        mensaje: Aviso o explicación educativa adicional.
        tiene_commits: True cuando el repositorio tiene al menos
            un commit (False en un repositorio recién iniciado).
        head_separado: True cuando HEAD apunta directamente a un
            commit (detached) y el repositorio sí tiene commits.
            Nunca se infiere de una lista de ramas vacía: un
            repositorio sin commits no es un HEAD separado.
    """

    exitoso: bool
    ramas: list[RamaLocal] = field(default_factory=list)
    error: str = ""
    mensaje: str = ""
    tiene_commits: bool = True
    head_separado: bool = False