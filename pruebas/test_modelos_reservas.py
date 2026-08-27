"""
Pruebas de los modelos de Modo Equipo Oracle V1.

Estas pruebas son puramente locales y deterministas:
no tocan red, no tocan el repositorio Oracle productivo
ni crean repositorios Git.
"""

import unittest

from modelos_reservas import (
    ClaveObjetoOracle,
    ManifiestoProyecto,
    ReglaLayoutOracle,
    ResultadoManifiestoProyecto,
    ResultadoResolucionObjeto,
    ResultadoRenombradoObjeto,
    TIPOS_ORACLE_SOPORTADOS_V1,
    EXTENSIONES_ORACLE_SOPORTADAS_V1,
)


class TestClaveObjetoOracle(unittest.TestCase):
    """
    Pruebas de construccion y canonica de ClaveObjetoOracle.
    """

    def test_construccion_basica(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        self.assertEqual(clave.tipo, "PACKAGE")
        self.assertEqual(clave.nombre, "FINI004")

    def test_canonica_package_fini004(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        self.assertEqual(clave.canonica(), "PACKAGE|FINI004")

    def test_canonica_mayusculas(self):
        clave = ClaveObjetoOracle(tipo="package", nombre="fini004")

        self.assertEqual(clave.canonica(), "PACKAGE|FINI004")

    def test_str_devuelve_canonica(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        self.assertEqual(str(clave), "PACKAGE|FINI004")

    def test_igualdad_determinismo(self):
        clave1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        clave2 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        self.assertEqual(clave1, clave2)

    def test_desigualdad_por_nombre(self):
        clave1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        clave2 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI005")

        self.assertNotEqual(clave1, clave2)

    def test_desigualdad_por_tipo(self):
        clave1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        clave2 = ClaveObjetoOracle(tipo="PROCEDURE", nombre="FINI004")

        self.assertNotEqual(clave1, clave2)

    def test_es_inmutable(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        with self.assertRaises(Exception):
            clave.tipo = "PROCEDURE"

    def test_canonica_no_contiene_ruta_absoluta(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        canonica = clave.canonica()

        self.assertNotIn("\\", canonica)
        self.assertNotIn("/", canonica)
        self.assertNotIn(":", canonica)

    def test_canonica_no_contiene_extension(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")

        canonica = clave.canonica()

        self.assertNotIn(".pls", canonica)
        self.assertNotIn(".", canonica)


class TestReglaLayoutOracle(unittest.TestCase):
    """
    Pruebas de ReglaLayoutOracle.
    """

    def test_construccion_basica(self):
        regla = ReglaLayoutOracle(
            carpeta="Paquetes",
            tipo="PACKAGE",
            extension=".pls"
        )

        self.assertEqual(regla.carpeta, "Paquetes")
        self.assertEqual(regla.tipo, "PACKAGE")
        self.assertEqual(regla.extension, ".pls")

    def test_es_inmutable(self):
        regla = ReglaLayoutOracle(
            carpeta="Paquetes",
            tipo="PACKAGE",
            extension=".pls"
        )

        with self.assertRaises(Exception):
            regla.carpeta = "Otra"


class TestManifiestoProyecto(unittest.TestCase):
    """
    Pruebas de ManifiestoProyecto y reglas_por_carpeta.
    """

    def _manifiesto_valido(self):
        return ManifiestoProyecto(
            format_version=1,
            project_uuid="00000000-0000-4000-8000-000000000000",
            oracle_layout=(
                ReglaLayoutOracle(
                    carpeta="Paquetes",
                    tipo="PACKAGE",
                    extension=".pls"
                ),
            )
        )

    def test_construccion_basica(self):
        manifiesto = self._manifiesto_valido()

        self.assertEqual(manifiesto.format_version, 1)
        self.assertEqual(
            manifiesto.project_uuid,
            "00000000-0000-4000-8000-000000000000"
        )
        self.assertEqual(len(manifiesto.oracle_layout), 1)

    def test_reglas_por_carpeta(self):
        manifiesto = self._manifiesto_valido()
        reglas = manifiesto.reglas_por_carpeta()

        self.assertIn("Paquetes", reglas)
        self.assertEqual(reglas["Paquetes"].tipo, "PACKAGE")
        self.assertEqual(reglas["Paquetes"].extension, ".pls")


class TestResultadoManifiestoProyecto(unittest.TestCase):
    """
    Pruebas de ResultadoManifiestoProyecto.
    """

    def test_resultado_exitoso(self):
        manifiesto = ManifiestoProyecto(
            format_version=1,
            project_uuid="00000000-0000-4000-8000-000000000000",
            oracle_layout=(
                ReglaLayoutOracle(
                    carpeta="Paquetes",
                    tipo="PACKAGE",
                    extension=".pls"
                ),
            )
        )

        resultado = ResultadoManifiestoProyecto(
            exitoso=True,
            mensaje="OK",
            manifiesto=manifiesto
        )

        self.assertTrue(resultado.exitoso)
        self.assertIsNotNone(resultado.manifiesto)
        self.assertEqual(resultado.mensaje, "OK")

    def test_resultado_fallido_no_lanza(self):
        resultado = ResultadoManifiestoProyecto(
            exitoso=False,
            mensaje="Error controlado",
            manifiesto=None
        )

        self.assertFalse(resultado.exitoso)
        self.assertIsNone(resultado.manifiesto)
        self.assertIn("Error", resultado.mensaje)


class TestResultadoResolucionObjeto(unittest.TestCase):
    """
    Pruebas de los constructores estaticos de
    ResultadoResolucionObjeto.
    """

    def test_no_oracle(self):
        resultado = ResultadoResolucionObjeto.no_oracle("README")

        self.assertTrue(resultado.es_ruta_valida)
        self.assertFalse(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)

    def test_reservable(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        resultado = ResultadoResolucionObjeto.reservable(clave)

        self.assertTrue(resultado.es_ruta_valida)
        self.assertTrue(resultado.es_objeto_oracle)
        self.assertTrue(resultado.es_reservable)
        self.assertEqual(resultado.objeto, clave)

    def test_oracle_no_resoluble(self):
        resultado = ResultadoResolucionObjeto.oracle_no_resoluble(
            "No se puede resolver"
        )

        self.assertTrue(resultado.es_ruta_valida)
        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)
        self.assertIn("resolver", resultado.mensaje)

    def test_ruta_invalida(self):
        resultado = ResultadoResolucionObjeto.ruta_invalida(
            "Ruta absoluta"
        )

        self.assertFalse(resultado.es_ruta_valida)
        self.assertFalse(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)


class TestResultadoRenombradoObjeto(unittest.TestCase):
    """
    Pruebas de ResultadoRenombradoObjeto.
    """

    def test_renombrado_resoluble(self):
        clave1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        clave2 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI005")

        resultado = ResultadoRenombradoObjeto(
            es_resoluble=True,
            claves=[clave1, clave2]
        )

        self.assertTrue(resultado.es_resoluble)
        self.assertEqual(len(resultado.claves), 2)

    def test_renombrado_no_resoluble(self):
        resultado = ResultadoRenombradoObjeto(
            es_resoluble=False,
            rutas_no_resolvibles=["Paquetes/Sub/FINI004.pls"],
            mensaje="Rutas Oracle no resolubles"
        )

        self.assertFalse(resultado.es_resoluble)
        self.assertEqual(len(resultado.rutas_no_resolvibles), 1)


class TestConstantesV1(unittest.TestCase):
    """
    Pruebas de las constantes soportadas en V1.
    """

    def test_tipo_soportado_package(self):
        self.assertIn("PACKAGE", TIPOS_ORACLE_SOPORTADOS_V1)

    def test_extension_soportada_pls(self):
        self.assertEqual(
            EXTENSIONES_ORACLE_SOPORTADAS_V1["PACKAGE"],
            ".pls"
        )

    def test_no_hay_otros_tipos(self):
        self.assertEqual(len(TIPOS_ORACLE_SOPORTADOS_V1), 1)


if __name__ == "__main__":
    unittest.main()
