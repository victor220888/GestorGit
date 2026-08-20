"""
Prueba focalizada de la GUI (sin Tk real) del bloqueo por
conflicto en crear_commit_desde_interfaz().

La instancia de AplicacionGit se construye con __new__ (no se
abre ninguna ventana Tkinter); se sustituyen únicamente
variable_mensaje_commit y servicio_git por dobles mínimos y se
interceptan las llamadas a messagebox con unittest.mock.

Escenario:
- Cambio A: preparado, sin conflicto;
- Cambio B: preparado y EN CONFLICTO, con descripcion que
  deliberadamente NO dice "Conflicto" (el bloqueo debe proceder
  del booleano estructurado en_conflicto, nunca del texto).

Debe demostrar:
- se muestra el aviso educativo de bloqueo (showwarning);
- NO se llama askyesno;
- NO se llama servicio_git.crear_commit().
"""

import unittest
from unittest import mock

from modelos import CambioArchivo, ResultadoCambios

import principal


class VariableMensajeCommitDoble:
    """
    Sustituye self.variable_mensaje_commit (StringVar real de
    Tkinter) por un doble mínimo con get().
    """

    def get(self):
        return "Mensaje de prueba"


class ServicioGitDoble:
    """
    Doble mínimo de ServicioGit para la GUI: solo responde la
    consulta de cambios (spy) y registra las llamadas a
    crear_commit.
    """

    def __init__(self, cambios):
        self.cambios = cambios
        self.llamadas_crear_commit = 0

    def obtener_cambios(self, ruta_repositorio):
        return ResultadoCambios(
            exitoso=True,
            cambios=self.cambios
        )

    def crear_commit(self, ruta_repositorio, mensaje):
        self.llamadas_crear_commit += 1
        return None


class PruebaCommitGuiConflicto(unittest.TestCase):
    """
    El botón Crear commit bloquea con un aviso educativo cuando
    existe cualquier conflicto en el índice, sin mostrar la
    confirmación ni ejecutar git commit.
    """

    def crear_aplicacion(self, servicio_git):
        aplicacion = principal.AplicacionGit.__new__(
            principal.AplicacionGit
        )

        aplicacion.ruta_repositorio = "C:/ruta/al/repositorio"
        aplicacion.variable_mensaje_commit = (
            VariableMensajeCommitDoble()
        )
        aplicacion.servicio_git = servicio_git

        return aplicacion

    def test_commit_bloquea_por_conflicto_sin_askyesno_sin_commit(self):
        cambios = [
            CambioArchivo(
                ruta="normal.sql",
                estado_indice="M",
                estado_trabajo=" ",
                descripcion="Modificado y preparado",
                preparado=True,
                en_conflicto=False
            ),
            CambioArchivo(
                ruta="conflicto.sql",
                estado_indice="U",
                estado_trabajo="U",
                descripcion="Deliberadamente distinta de Conflicto",
                preparado=True,
                en_conflicto=True
            ),
        ]

        servicio_doble = ServicioGitDoble(cambios)

        aplicacion = self.crear_aplicacion(
            servicio_doble
        )

        with mock.patch.object(
            principal.messagebox,
            "showwarning"
        ) as mostrar_aviso:
            with mock.patch.object(
                principal.messagebox,
                "askyesno"
            ) as preguntar:
                aplicacion.crear_commit_desde_interfaz()

        # Aviso educativo de bloqueo mostrado (una sola vez).
        mostrar_aviso.assert_called_once()

        texto_aviso = mostrar_aviso.call_args.args[1]

        self.assertIn(
            "conflicto.sql",
            texto_aviso
        )

        self.assertIn(
            "no elige",
            texto_aviso
        )

        # Sin confirmación y sin commit.
        preguntar.assert_not_called()

        self.assertEqual(
            servicio_doble.llamadas_crear_commit,
            0
        )


if __name__ == "__main__":
    unittest.main()