"""
Servicio de persistencia de la configuración de Gestor Git.

Guarda y recupera únicamente la ruta local del último
repositorio seleccionado por el usuario (config.json).

Nunca guarda credenciales, tokens, contraseñas, correos,
URLs de remotos ni información de Git Credential Manager.

Este servicio no ejecuta operaciones remotas ni usa shell=True.
"""

import json
import os
from pathlib import Path

from modelos_configuracion import ResultadoConfiguracion
from servicio_git import ServicioGit

# Caracteres que no pueden aparecer en una ruta guardada.
_CARACTERES_NO_VALIDOS = ("\x00", "\r", "\n")


class ServicioConfiguracion:
    """
    Lee y escribe config.json para recordar el último
    repositorio seleccionado.

    La escritura es conservadora: primero se escribe un archivo
    temporal en la misma carpeta y después se reemplaza el
    config.json mediante os.replace, evitando dejar un JSON
    parcialmente escrito si la aplicación se interrumpe.
    """

    def __init__(
        self,
        servicio_git=None,
        ruta_configuracion=None
    ):
        """
        Crea el servicio de configuración.

        Si no se indican, crea un ServicioGit nuevo y usa
        config.json junto a los archivos de la aplicación,
        sin depender del directorio desde el cual se ejecute
        la aplicación.
        """

        if servicio_git is None:
            servicio_git = ServicioGit()

        self.servicio_git = servicio_git

        if ruta_configuracion is None:
            ruta_configuracion = (
                Path(__file__).resolve().parent / "config.json"
            )

        self.ruta_configuracion = Path(
            ruta_configuracion
        )

    def _resultado_error(self, mensaje):
        """
        Construye un resultado de error controlado.
        """

        return ResultadoConfiguracion(
            exitoso=False,
            mensaje=mensaje,
            error=mensaje
        )

    def _validar_ruta_guardada(self, ruta_repositorio):
        """
        Valida una ruta guardada y devuelve la raíz confirmada
        por Git.

        Solamente se aceptan rutas de texto, sin NUL, CR o LF,
        que existan, sean directorios y repositorios Git válidos.
        """

        if not isinstance(ruta_repositorio, str):
            return self._resultado_error(
                "La ruta guardada no es texto."
            )

        if any(
            caracter in ruta_repositorio
            for caracter in _CARACTERES_NO_VALIDOS
        ):
            return self._resultado_error(
                "La ruta guardada contiene caracteres no válidos."
            )

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return self._resultado_error(
                estado.mensaje
            )

        return ResultadoConfiguracion(
            exitoso=True,
            ruta_repositorio=estado.ruta_raiz,
            mensaje="Repositorio recordado válido."
        )

    def cargar_ultimo_repositorio(self):
        """
        Devuelve la ruta del último repositorio seleccionado.

        Si config.json no existe, el resultado es exitoso con
        ruta vacía: corresponde a un primer inicio normal.

        Las claves JSON desconocidas se ignoran: la escritura
        siempre vuelve a escribir únicamente ruta_repositorio.
        """

        if not self.ruta_configuracion.exists():
            return ResultadoConfiguracion(
                exitoso=True,
                ruta_repositorio="",
                mensaje="No hay configuración guardada."
            )

        try:
            contenido = self.ruta_configuracion.read_text(
                encoding="utf-8"
            )
        except (OSError, UnicodeDecodeError) as error:
            return self._resultado_error(
                f"No fue posible leer config.json: {error}"
            )

        try:
            datos = json.loads(contenido)
        except json.JSONDecodeError:
            return self._resultado_error(
                "config.json no contiene JSON válido."
            )

        if not isinstance(datos, dict):
            return self._resultado_error(
                "El contenido de config.json no es un objeto JSON."
            )

        ruta_guardada = datos.get("ruta_repositorio")

        return self._validar_ruta_guardada(
            ruta_guardada
        )

    def guardar_ultimo_repositorio(self, ruta_repositorio):
        """
        Guarda la ruta raíz del último repositorio seleccionado.

        La ruta se valida con Git antes de escribir: si es
        inválida no se altera la configuración existente.
        """

        resultado_validacion = self._validar_ruta_guardada(
            ruta_repositorio
        )

        if not resultado_validacion.exitoso:
            return resultado_validacion

        ruta_validada = resultado_validacion.ruta_repositorio

        contenido = json.dumps(
            {
                "ruta_repositorio": ruta_validada
            },
            ensure_ascii=False,
            indent=2
        )

        ruta_temporal = self.ruta_configuracion.with_name(
            self.ruta_configuracion.name + ".tmp"
        )

        try:
            self.ruta_configuracion.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            ruta_temporal.write_text(
                contenido,
                encoding="utf-8"
            )

            os.replace(
                ruta_temporal,
                self.ruta_configuracion
            )
        except OSError as error:
            try:
                if ruta_temporal.exists():
                    ruta_temporal.unlink()
            except OSError:
                pass

            return self._resultado_error(
                f"No fue posible guardar config.json: {error}"
            )

        return ResultadoConfiguracion(
            exitoso=True,
            ruta_repositorio=ruta_validada,
            mensaje="Configuración guardada."
        )