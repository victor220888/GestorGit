"""
Pruebas del posicionamiento general de AyudaEmergente.

GG-PROMPT-010: un tooltip largo (p. ej. el de "Publicar rama
local...") podía desbordar por el borde inferior de la pantalla
porque la geometría se fijaba ANTES de conocer el tamaño requerido
del tooltip.

La lógica de posición vive en la función pura
calcular_posicion_ayuda, por lo que estas pruebas no necesitan un
display Tkinter real.
"""

import inspect
import unittest

import principal
import ayuda_interfaz
from ayuda_interfaz import calcular_posicion_ayuda


class PruebasCalcularPosicionAyuda(unittest.TestCase):
    """
    Casos de posición sin display: pantalla típica de Windows
    (1920x1080) y casos límite.
    """

    def test_tooltip_que_cabe_debajo_conserva_posicion_normal(self):
        x, y = calcular_posicion_ayuda(
            ancla_x=100,
            ancla_y=500,
            ancla_y_arriba=480,
            ancho=300,
            alto=200,
            pantalla_ancho=1920,
            pantalla_alto=1080
        )

        self.assertEqual(x, 100)
        self.assertEqual(y, 500)

    def test_tooltip_que_cabe_no_se_mueve_innecesariamente(self):
        casos = (
            # (ancla_x, ancla_y, ancla_y_arriba, ancho, alto)
            (10, 10, 5, 300, 200),
            (900, 400, 380, 500, 300),
            (1500, 100, 80, 400, 150),
        )

        for ancla_x, ancla_y, ancla_y_arriba, ancho, alto in casos:
            with self.subTest(ancla=(ancla_x, ancla_y)):
                x, y = calcular_posicion_ayuda(
                    ancla_x=ancla_x,
                    ancla_y=ancla_y,
                    ancla_y_arriba=ancla_y_arriba,
                    ancho=ancho,
                    alto=alto,
                    pantalla_ancho=1920,
                    pantalla_alto=1080
                )

                self.assertEqual(x, ancla_x)
                self.assertEqual(y, ancla_y)

    def test_desborde_inferior_recoloca_el_tooltip_arriba(self):
        # 950 + 300 desborda el borde inferior (1080 - 8): la
        # ayuda pasa arriba del ancla superior (480 - 300 = 180).
        x, y = calcular_posicion_ayuda(
            ancla_x=100,
            ancla_y=950,
            ancla_y_arriba=480,
            ancho=300,
            alto=300,
            pantalla_ancho=1920,
            pantalla_alto=1080
        )

        self.assertEqual(y, 180)
        self.assertEqual(x, 100)

    def test_desborde_derecho_desplaza_hacia_la_izquierda(self):
        x, y = calcular_posicion_ayuda(
            ancla_x=1700,
            ancla_y=100,
            ancla_y_arriba=80,
            ancho=380,
            alto=200,
            pantalla_ancho=1920,
            pantalla_alto=1080
        )

        self.assertEqual(x, 1920 - 8 - 380)
        self.assertEqual(y, 100)

    def test_coordenadas_resultantes_nunca_son_negativas(self):
        # Tooltip más grande que la pantalla: se recoloca arriba,
        # no cabe y queda fijado al margen superior; la X también
        # se fija al margen izquierdo.
        x, y = calcular_posicion_ayuda(
            ancla_x=0,
            ancla_y=590,
            ancla_y_arriba=20,
            ancho=900,
            alto=700,
            pantalla_ancho=800,
            pantalla_alto=600
        )

        self.assertGreaterEqual(x, 8)
        self.assertGreaterEqual(y, 8)

    def test_ajuste_conjunto_desborde_inferior_y_derecho(self):
        x, y = calcular_posicion_ayuda(
            ancla_x=1750,
            ancla_y=1000,
            ancla_y_arriba=900,
            ancho=400,
            alto=250,
            pantalla_ancho=1920,
            pantalla_alto=1080
        )

        self.assertEqual(x, 1920 - 8 - 400)
        self.assertEqual(y, 900 - 250)


class PruebaMostrarAyudaEmergente(unittest.TestCase):
    """
    Comprobaciones estáticas sobre AyudaEmergente.mostrar.
    """

    def test_la_geometria_se_fija_despues_de_conocer_el_tamano(self):
        fuente = inspect.getsource(
            ayuda_interfaz.AyudaEmergente.mostrar
        )

        self.assertIn("update_idletasks", fuente)
        self.assertIn("calcular_posicion_ayuda", fuente)
        self.assertIn("winfo_reqwidth", fuente)
        self.assertIn("winfo_reqheight", fuente)

        self.assertLess(
            fuente.index("update_idletasks"),
            fuente.index("wm_geometry"),
            "La geometría debe fijarse después de conocer el "
            "tamaño requerido del tooltip."
        )

    def test_el_texto_y_estilo_de_la_etiqueta_no_cambian(self):
        fuente = inspect.getsource(
            ayuda_interfaz.AyudaEmergente.mostrar
        )

        for marcador in (
            "wraplength=self.ancho_texto",
            '"#FFF8D8"',
            '"Segoe UI", 9'
        ):
            self.assertIn(marcador, fuente)


class PruebaTooltipsIntactos(unittest.TestCase):
    """
    La corrección de posición no toca contenidos ni cableado.
    """

    def test_contenido_publicar_rama_no_se_modifica(self):
        texto = principal.TEXTOS_AYUDA_GIT_V1["publicar_rama"]

        for fragmento in (
            "Publicar rama local...",
            "apunta únicamente a refs/heads/<rama>",
            "--set-upstream",
            "No usa --all, --tags, --mirror, --delete, --force ni"
        ):
            self.assertIn(fragmento, texto)

    def test_el_total_de_tooltips_sigue_siendo_38_mas_bloque_f(self):
        # GG-PROMPT-042: las 38 ayudas históricas se preservan
        # íntegras; el Bloque F suma las claves "modo_equipo_*".
        # El cableado completo (biyección llamadas <-> claves)
        # sigue vigilado por pruebas/test_ayuda_tooltips_v1.py,
        # que también corre dentro de la suite completa.
        claves_f = [
            clave
            for clave in principal.TEXTOS_AYUDA_GIT_V1
            if clave.startswith("modo_equipo")
        ]

        self.assertGreaterEqual(len(claves_f), 15)

        claves_historicas = [
            clave
            for clave in principal.TEXTOS_AYUDA_GIT_V1
            if not clave.startswith("modo_equipo")
        ]

        self.assertEqual(
            len(claves_historicas),
            38
        )

        # El cableado completo (biyección llamadas <-> claves)
        # sigue vigilado por pruebas/test_ayuda_tooltips_v1.py,
        # que también corre dentro de la suite completa.


if __name__ == "__main__":
    unittest.main()
