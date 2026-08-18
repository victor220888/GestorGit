import csv
import tempfile
import unittest
from pathlib import Path

from modelos_historial import CommitGit
from servicio_exportacion_historial import ServicioExportacionHistorial


class PruebasExportacionHistorial(unittest.TestCase):
    """
    Pruebas de exportación del historial a CSV y TXT.
    """

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta_temporal = Path(self.temporal.name)
        self.servicio = ServicioExportacionHistorial()

        self.commits = [
            CommitGit(
                hash_completo="abcdef1234567890",
                hash_corto="abcdef1",
                fecha_iso="2026-08-18T09:15:00-03:00",
                autor="Víctor Román",
                correo="victor@example.com",
                mensaje="Agrega paquete FINI004"
            ),
            CommitGit(
                hash_completo="1234567890abcdef",
                hash_corto="1234567",
                fecha_iso="2026-08-17T08:10:00-03:00",
                autor="Otro Usuario",
                correo="otro@example.com",
                mensaje="Actualiza consulta"
            )
        ]

    def tearDown(self):
        self.temporal.cleanup()

    def test_exportar_csv_crea_archivo_con_todos_los_campos(self):
        """CSV debe conservar hashes, autor, correo y mensaje."""

        ruta = self.ruta_temporal / "historial.csv"

        resultado = self.servicio.exportar_csv(
            str(ruta),
            self.commits
        )

        self.assertTrue(resultado.exitoso)
        self.assertTrue(ruta.exists())

        with ruta.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as archivo:
            filas = list(
                csv.reader(
                    archivo,
                    delimiter=";"
                )
            )

        self.assertEqual(
            [
                "Hash completo",
                "Hash corto",
                "Fecha ISO",
                "Autor",
                "Correo",
                "Mensaje"
            ],
            filas[0]
        )
        self.assertEqual("Víctor Román", filas[1][3])
        self.assertEqual("Agrega paquete FINI004", filas[1][5])
        self.assertEqual(3, len(filas))

    def test_exportar_txt_incluye_repositorio_filtros_y_commits(self):
        """TXT debe documentar la consulta que fue exportada."""

        ruta = self.ruta_temporal / "historial.txt"

        resultado = self.servicio.exportar_txt(
            str(ruta),
            self.commits,
            ruta_repositorio=r"D:\Proyecto",
            filtro_archivo="FINI004",
            fecha_desde="01/08/2026",
            fecha_hasta="31/08/2026"
        )

        self.assertTrue(resultado.exitoso)

        contenido = ruta.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn("Repositorio: D:\\Proyecto", contenido)
        self.assertIn("Filtro de archivo: FINI004", contenido)
        self.assertIn("Desde: 01/08/2026", contenido)
        self.assertIn("Hasta: 31/08/2026", contenido)
        self.assertIn("abcdef1234567890", contenido)
        self.assertIn("Agrega paquete FINI004", contenido)

    def test_exportacion_rechaza_lista_vacia(self):
        """No se debe crear un archivo cuando no hay resultados visibles."""

        ruta = self.ruta_temporal / "vacio.csv"

        resultado = self.servicio.exportar_csv(
            str(ruta),
            []
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("No hay commits", resultado.error)
        self.assertFalse(ruta.exists())

    def test_csv_protege_contra_formulas_de_hoja_de_calculo(self):
        """Mensajes que parecen fórmulas deben exportarse como texto."""

        commit = CommitGit(
            hash_completo="abcdef",
            hash_corto="abc",
            fecha_iso="2026-08-18T09:15:00-03:00",
            autor="Usuario",
            correo="usuario@example.com",
            mensaje='=HYPERLINK("https://example.com")'
        )

        ruta = self.ruta_temporal / "seguro.csv"

        resultado = self.servicio.exportar_csv(
            str(ruta),
            [commit]
        )

        self.assertTrue(resultado.exitoso)

        with ruta.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as archivo:
            filas = list(
                csv.reader(
                    archivo,
                    delimiter=";"
                )
            )

        self.assertTrue(
            filas[1][5].startswith("'=")
        )

    def test_exportacion_informa_error_de_ruta(self):
        """Una carpeta inexistente debe devolver un error controlado."""

        ruta = (
            self.ruta_temporal
            / "carpeta_que_no_existe"
            / "historial.txt"
        )

        resultado = self.servicio.exportar_txt(
            str(ruta),
            self.commits
        )

        self.assertFalse(resultado.exitoso)
        self.assertIn("No fue posible escribir", resultado.error)


if __name__ == "__main__":
    unittest.main()
