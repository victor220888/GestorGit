"""
Servicio de identidad tecnica de instalacion para Modo Equipo Oracle V1.

Mantiene un id_cliente estable y no humano en:

    %APPDATA%\\GestorGit\\identidad_instalacion.json

Responsabilidades:

- crear la identidad si no existe (UUID v4 canonico);
- devolver siempre el mismo id_cliente si ya existe y es valido;
- ante cualquier fallo (archivo corrupto, UUID invalido, esquema
  invalido, UTF-8 invalido, claves duplicadas), devolver un resultado
  controlado sin sobrescribir ni regenerar automaticamente;
- ante una carrera entre procesos, preferir la identidad ya creada.

El servicio NO ejecuta Git, NO hace red, NO lee user.email,
NO almacena correo ni token ni password, NO depende de Tkinter y
NO toca el repositorio Oracle.

La ruta es inyectable para pruebas; en produccion se deriva desde
APPDATA. Si APPDATA no esta definida, se devuelve un resultado
controlado sin inventar ninguna ubicacion alternativa.
"""

import json
import os
import uuid
from pathlib import Path

from modelos_configuracion import ResultadoIdentidadEquipo


# Esquema V1 del archivo de identidad.
_FORMAT_VERSION_IDENTIDAD = 1


def _detectar_claves_duplicadas(pairs):
    """
    Hook para json.loads que rechaza claves duplicadas
    en cualquier nivel del objeto JSON.
    """

    vistos = set()
    resultado = {}
    for clave, valor in pairs:
        if clave in vistos:
            raise ValueError(
                f"Clave duplicada en JSON: {clave!r}"
            )
        vistos.add(clave)
        resultado[clave] = valor
    return resultado


def _es_uuid4_canonico(texto):
    """
    Comprueba que texto sea un UUID v4 en representacion
    canonica: minusculas, con guiones, 36 caracteres.
    """

    if not isinstance(texto, str):
        return False
    try:
        u = uuid.UUID(texto)
    except (ValueError, AttributeError):
        return False
    if u.version != 4:
        return False
    return texto == str(u)


class ServicioIdentidadEquipo:
    """
    Servicio de identidad tecnica de instalacion.

    Uso tipico:

        servicio = ServicioIdentidadEquipo()
        resultado = servicio.obtener_o_crear_identidad()
        if resultado.exitoso:
            id_cliente = resultado.id_cliente

    En pruebas se inyecta una ruta temporal:

        servicio = ServicioIdentidadEquipo(
            ruta_identidad=tmp / "identidad_instalacion.json"
        )
    """

    def __init__(self, ruta_identidad=None):
        """
        Crea el servicio.

        Si ruta_identidad es None, se deriva desde %APPDATA%:

            %APPDATA%\\GestorGit\\identidad_instalacion.json

        Si APPDATA no esta definida, el servicio queda en estado
        sin ruta y obtener_o_crear_identidad devolvera un
        resultado controlado, sin fallback silencioso.
        """

        if ruta_identidad is None:
            appdata = os.environ.get("APPDATA")
            if not appdata:
                self.ruta_identidad = None
                self._error_inicial = (
                    "La variable de entorno APPDATA no esta definida; "
                    "no se puede determinar la ruta de identidad."
                )
                return
            self.ruta_identidad = (
                Path(appdata) / "GestorGit" / "identidad_instalacion.json"
            )
        else:
            self.ruta_identidad = Path(ruta_identidad)
        self._error_inicial = None

    def obtener_o_crear_identidad(self):
        """
        Devuelve ResultadoIdentidadEquipo.

        - Si la identidad ya existe y es valida, devuelve el
          id_cliente persistido sin reescribir nada.
        - Si no existe, la crea con un UUID v4 canonico nuevo y
          devuelve exactamente el id_cliente persistido.
        - Si la identidad existe pero esta corrupta, devuelve un
          resultado no exitoso sin sobrescribir ni regenerar.
        - Si hubo una carrera y otro proceso creo el archivo,
          re-lee y valida el archivo existente.
        """

        if self.ruta_identidad is None:
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=self._error_inicial,
                error=self._error_inicial
            )

        try:
            if self.ruta_identidad.exists():
                return self._leer_y_validar()
            return self._crear_identidad_nueva()
        except OSError as error:
            mensaje = (
                f"Error de E/S al gestionar el archivo de identidad: "
                f"{error}"
            )
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=mensaje,
                error=str(error)
            )

    def _leer_y_validar(self):
        """
        Lee y valida el archivo de identidad existente.

        No comprueba exists(): debe ser llamado cuando se sabe
        que el archivo existe o para re-leer tras una carrera.
        """

        try:
            contenido = self.ruta_identidad.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    f"No fue posible leer el archivo de identidad: "
                    f"{error}"
                ),
                error=str(error)
            )

        if "\ufffd" in contenido:
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    "El archivo de identidad contiene texto que no "
                    "pudo decodificarse como UTF-8 valido."
                ),
                error="UTF-8 invalido"
            )

        try:
            datos = json.loads(
                contenido,
                object_pairs_hook=_detectar_claves_duplicadas
            )
        except (json.JSONDecodeError, ValueError) as error:
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    f"El archivo de identidad no contiene JSON valido: "
                    f"{error}"
                ),
                error=str(error)
            )

        if not isinstance(datos, dict):
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    "El archivo de identidad no es un objeto JSON."
                ),
                error="raiz no objeto"
            )

        claves = set(datos.keys())
        if claves != {"format_version", "id_cliente"}:
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    "El archivo de identidad debe contener "
                    "exactamente los campos format_version e id_cliente."
                ),
                error="esquema invalido"
            )

        format_version = datos["format_version"]
        if isinstance(format_version, bool) or not isinstance(
            format_version, int
        ):
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    "format_version debe ser un entero."
                ),
                error="format_version no entero"
            )
        if format_version != _FORMAT_VERSION_IDENTIDAD:
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    f"format_version no soportada: {format_version}. "
                    f"Se esperaba {_FORMAT_VERSION_IDENTIDAD}."
                ),
                error="format_version no soportada"
            )

        id_cliente = datos["id_cliente"]
        if not _es_uuid4_canonico(id_cliente):
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    "id_cliente no es un UUID v4 canonico valido."
                ),
                error="id_cliente invalido"
            )

        return ResultadoIdentidadEquipo(
            exitoso=True,
            id_cliente=id_cliente,
            mensaje="Identidad cargada."
        )

    def _crear_identidad_nueva(self):
        """
        Crea el archivo de identidad de forma conservadora ante
        una carrera entre procesos.

        Usa open(..., 'x') para creacion exclusiva. Si otro
        proceso crea el archivo entre la comprobacion y la
        escritura, se re-lee y valida el archivo existente.
        """

        try:
            self.ruta_identidad.parent.mkdir(
                parents=True,
                exist_ok=True
            )
        except OSError as error:
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    f"No fue posible crear la carpeta de identidad: "
                    f"{error}"
                ),
                error=str(error)
            )

        id_nuevo = str(uuid.uuid4())
        contenido = json.dumps(
            {
                "format_version": _FORMAT_VERSION_IDENTIDAD,
                "id_cliente": id_nuevo
            },
            ensure_ascii=False,
            indent=2
        )

        try:
            with open(
                self.ruta_identidad,
                "x",
                encoding="utf-8"
            ) as manejador:
                manejador.write(contenido)
        except FileExistsError:
            return self._leer_y_validar()
        except OSError as error:
            return ResultadoIdentidadEquipo(
                exitoso=False,
                mensaje=(
                    f"No fue posible crear el archivo de identidad: "
                    f"{error}"
                ),
                error=str(error)
            )

        # Re-leer para devolver exactamente el id_cliente persistido.
        return self._leer_y_validar()
