"""
Pruebas del ServicioObjetosOracle y del calculo del ref
de reserva.

Estas pruebas son puramente locales y deterministas:
no tocan red ni el repositorio Oracle productivo.
"""

import unittest

from modelos_reservas import (
    ClaveObjetoOracle,
    ManifiestoProyecto,
    ReglaLayoutOracle,
)
from servicio_objetos_oracle import (
    ServicioObjetosOracle,
    calcular_ref_reserva,
    ref_reserva_completo,
)


# Manifiesto y UUID usados en las pruebas.
UUID_PROYECTO = "00000000-0000-4000-8000-000000000000"


def _manifiesto_prueba():
    return ManifiestoProyecto(
        format_version=1,
        project_uuid=UUID_PROYECTO,
        oracle_layout=(
            ReglaLayoutOracle(
                carpeta="Paquetes",
                tipo="PACKAGE",
                extension=".pls"
            ),
        )
    )


class TestServicioObjetosOracle(unittest.TestCase):
    """
    Pruebas de resolucion de rutas a objetos Oracle.
    """

    def setUp(self):
        self.manifiesto = _manifiesto_prueba()
        self.servicio = ServicioObjetosOracle(self.manifiesto)

    # --- 1. Paquetes/FINI004.pls -> PACKAGE|FINI004 ---

    def test_pls_en_paquetes_resuelve(self):
        resultado = self.servicio.resolver("Paquetes/FINI004.pls")

        self.assertTrue(resultado.es_ruta_valida)
        self.assertTrue(resultado.es_objeto_oracle)
        self.assertTrue(resultado.es_reservable)
        self.assertIsNotNone(resultado.objeto)
        self.assertEqual(resultado.objeto.tipo, "PACKAGE")
        self.assertEqual(resultado.objeto.nombre, "FINI004")
        self.assertEqual(resultado.objeto.canonica(), "PACKAGE|FINI004")

    # --- 2. nombre en minusculas -> mayusculas ---

    def test_nombre_minusculas_a_mayusculas(self):
        resultado = self.servicio.resolver("Paquetes/fini004.pls")

        self.assertTrue(resultado.es_reservable)
        self.assertEqual(resultado.objeto.nombre, "FINI004")
        self.assertEqual(resultado.objeto.canonica(), "PACKAGE|FINI004")

    # --- 3. README.md no Oracle ---

    def test_readme_no_es_oracle(self):
        resultado = self.servicio.resolver("README.md")

        self.assertTrue(resultado.es_ruta_valida)
        self.assertFalse(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)

    # --- 4. .csv y .txt no Oracle ---

    def test_csv_no_es_oracle(self):
        resultado = self.servicio.resolver("datos/exportacion.csv")

        self.assertTrue(resultado.es_ruta_valida)
        self.assertFalse(resultado.es_objeto_oracle)

    def test_txt_no_es_oracle(self):
        resultado = self.servicio.resolver("documentacion.txt")

        self.assertFalse(resultado.es_objeto_oracle)

    # --- 5. OtraCarpeta/FINI004.pls -> Oracle no resoluble ---

    def test_pls_en_carpeta_no_mapeada_no_resoluble(self):
        resultado = self.servicio.resolver("OtraCarpeta/FINI004.pls")

        self.assertTrue(resultado.es_ruta_valida)
        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)
        self.assertTrue(resultado.mensaje)

    # --- 6. Paquetes/FINI004.sql -> Oracle no resoluble ---

    def test_sql_en_paquetes_no_resoluble(self):
        resultado = self.servicio.resolver("Paquetes/FINI004.sql")

        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)

    # --- 7. .pks no soportado ---

    def test_pks_no_soportado(self):
        resultado = self.servicio.resolver("Paquetes/FINI004.pks")

        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)

    # --- 8. .pkb no soportado ---

    def test_pkb_no_soportado(self):
        resultado = self.servicio.resolver("Paquetes/FINI004.pkb")

        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)

    # --- 9. .sql no soportado ---

    def test_sql_en_carpeta_no_mapeada_no_resoluble(self):
        resultado = self.servicio.resolver("Procedimientos/PR_CERRAR.sql")

        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)

    # --- 10. Paquetes/Sub/FINI004.pls -> no resoluble (subcarpeta) ---

    def test_subcarpeta_no_resoluble(self):
        resultado = self.servicio.resolver("Paquetes/Sub/FINI004.pls")

        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)
        self.assertIn("subcarpeta", resultado.mensaje.lower())

    # --- 11. Paquetes/FINI004.~pls no se confunde con .pls ---

    def test_backup_tilde_pls_no_confunde(self):
        resultado = self.servicio.resolver("Paquetes/FINI004.~pls")

        # .~pls no es .pls, no es familia Oracle reconocida, y
        # aunque estuviera en carpeta mapeada, no resuelve.
        self.assertFalse(resultado.es_reservable)
        self.assertIsNone(resultado.objeto)

    def test_nombre_con_tilde_antes_extension_rechazado(self):
        # FINI004~.pls: nombre con ~ antes de la extension
        resultado = self.servicio.resolver("Paquetes/FINI004~.pls")

        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)

    # --- 12. identificador Oracle invalido ---

    def test_identificador_invalido_digitos_inicio(self):
        resultado = self.servicio.resolver("Paquetes/1FINI004.pls")

        self.assertTrue(resultado.es_objeto_oracle)
        self.assertFalse(resultado.es_reservable)

    def test_identificador_invalido_espacios(self):
        resultado = self.servicio.resolver("Paquetes/FINI 004.pls")

        self.assertFalse(resultado.es_reservable)

    def test_identificador_invalido_caracter_especial(self):
        resultado = self.servicio.resolver("Paquetes/FINI-004.pls")

        self.assertFalse(resultado.es_reservable)

    # --- 13. ruta absoluta -> invalida ---

    def test_ruta_absoluta_unix_invalida(self):
        resultado = self.servicio.resolver("/Paquetes/FINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    def test_ruta_absoluta_windows_invalida(self):
        resultado = self.servicio.resolver("C:/Paquetes/FINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    def test_ruta_con_unidad_windows_invalida(self):
        resultado = self.servicio.resolver("D:\\Paquetes\\FINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    # --- 14. .. -> invalida ---

    def test_ruta_con_punto_punto_invalida(self):
        resultado = self.servicio.resolver("../Paquetes/FINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    def test_ruta_con_doble_punto_intermedia_invalida(self):
        resultado = self.servicio.resolver("Paquetes/../FINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    # --- 15. backslash Windows normalizado de forma determinista ---

    def test_backslash_normalizado_determinista(self):
        resultado = self.servicio.resolver("Paquetes\\FINI004.pls")

        self.assertTrue(resultado.es_ruta_valida)
        self.assertTrue(resultado.es_reservable)
        self.assertEqual(resultado.objeto.canonica(), "PACKAGE|FINI004")

    def test_backslash_no_confunde_con_ruta_absoluta(self):
        # Rutas que empiezan con \ son absolutas en Windows.
        resultado = self.servicio.resolver("\\Paquetes\\FINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    # --- 16. rename de FINI004.pls a FINI005.pls devuelve ambas claves ---

    def test_rename_devuelve_ambas_claves(self):
        resultado = self.servicio.resolver_renombrado(
            "Paquetes/FINI005.pls",
            "Paquetes/FINI004.pls"
        )

        self.assertTrue(resultado.es_resoluble)
        self.assertEqual(len(resultado.claves), 2)
        claves_canonicas = [c.canonica() for c in resultado.claves]
        self.assertIn("PACKAGE|FINI004", claves_canonicas)
        self.assertIn("PACKAGE|FINI005", claves_canonicas)

    def test_rename_sin_duplicados_mismo_objeto(self):
        resultado = self.servicio.resolver_renombrado(
            "Paquetes/FINI004.pls",
            "Paquetes/FINI004.pls"
        )

        self.assertTrue(resultado.es_resoluble)
        self.assertEqual(len(resultado.claves), 1)
        self.assertEqual(resultado.claves[0].canonica(), "PACKAGE|FINI004")

    # --- 17. rename donde una ruta Oracle no es resoluble -> fail-safe ---

    def test_rename_una_ruta_no_resoluble(self):
        resultado = self.servicio.resolver_renombrado(
            "Paquetes/FINI005.pls",
            "Paquetes/Sub/FINI004.pls"
        )

        self.assertFalse(resultado.es_resoluble)
        self.assertGreater(len(resultado.rutas_no_resolvibles), 0)

    def test_rename_una_ruta_invalida(self):
        resultado = self.servicio.resolver_renombrado(
            "Paquetes/FINI005.pls",
            "../Paquetes/FINI004.pls"
        )

        self.assertFalse(resultado.es_resoluble)
        self.assertGreater(len(resultado.rutas_invalidas), 0)

    def test_rename_una_oracle_otra_no_oracle(self):
        resultado = self.servicio.resolver_renombrado(
            "Paquetes/FINI005.pls",
            "README.md"
        )

        # README.md no es Oracle, no bloquea; la ruta Oracle
        # se resuelve y la no Oracle se ignora.
        self.assertTrue(resultado.es_resoluble)
        self.assertEqual(len(resultado.claves), 1)
        self.assertEqual(resultado.claves[0].canonica(), "PACKAGE|FINI005")

    def test_rename_sin_ruta_anterior(self):
        resultado = self.servicio.resolver_renombrado(
            "Paquetes/FINI005.pls"
        )

        self.assertTrue(resultado.es_resoluble)
        self.assertEqual(len(resultado.claves), 1)

    # --- 18-21. Hash SHA-256 ---

    def test_hash_sha256_64_hex(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        h = calcular_ref_reserva(UUID_PROYECTO, clave)

        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_hash_cambia_con_project_uuid(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        h1 = calcular_ref_reserva(UUID_PROYECTO, clave)
        h2 = calcular_ref_reserva(
            "11111111-1111-4111-8111-111111111111",
            clave
        )

        self.assertNotEqual(h1, h2)

    def test_hash_cambia_con_clave(self):
        c1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        c2 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI005")
        h1 = calcular_ref_reserva(UUID_PROYECTO, c1)
        h2 = calcular_ref_reserva(UUID_PROYECTO, c2)

        self.assertNotEqual(h1, h2)

    def test_hash_determinista(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        h1 = calcular_ref_reserva(UUID_PROYECTO, clave)
        h2 = calcular_ref_reserva(UUID_PROYECTO, clave)

        self.assertEqual(h1, h2)

    def test_hash_cambia_con_tipo(self):
        c1 = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        c2 = ClaveObjetoOracle(tipo="PROCEDURE", nombre="FINI004")
        h1 = calcular_ref_reserva(UUID_PROYECTO, c1)
        h2 = calcular_ref_reserva(UUID_PROYECTO, c2)

        self.assertNotEqual(h1, h2)

    def test_hash_usa_separador_nul(self):
        """
        Verifica que el hash usa project_uuid + NUL + clave.
        """

        import hashlib

        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        esperado = hashlib.sha256(
            (UUID_PROYECTO + "\x00" + "PACKAGE|FINI004").encode("utf-8")
        ).hexdigest()

        self.assertEqual(calcular_ref_reserva(UUID_PROYECTO, clave), esperado)

    def test_hash_minusculas(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="fini004")
        h = calcular_ref_reserva(UUID_PROYECTO, clave)

        self.assertEqual(h, h.lower())

    # --- ref_reserva_completo ---

    def test_ref_reserva_completo(self):
        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="FINI004")
        h = calcular_ref_reserva(UUID_PROYECTO, clave)
        ref = ref_reserva_completo(h)

        self.assertTrue(ref.startswith("refs/heads/gestorgit-reservas/"))
        self.assertTrue(ref.endswith(h))

    def test_ref_reserva_completo_vacio_rechazado(self):
        with self.assertRaises(ValueError):
            ref_reserva_completo("")

    def test_ref_reserva_completo_none_rechazado(self):
        with self.assertRaises(ValueError):
            ref_reserva_completo(None)

    def test_ref_reserva_completo_int_rechazado(self):
        with self.assertRaises(ValueError):
            ref_reserva_completo(12345)

    def test_ref_reserva_completo_dotdot_evil_rechazado(self):
        with self.assertRaises(ValueError):
            ref_reserva_completo("../evil")

    def test_ref_reserva_completo_63_caracteres_rechazado(self):
        h = "a" * 63
        with self.assertRaises(ValueError):
            ref_reserva_completo(h)

    def test_ref_reserva_completo_65_caracteres_rechazado(self):
        h = "a" * 65
        with self.assertRaises(ValueError):
            ref_reserva_completo(h)

    def test_ref_reserva_completo_64_g_mayuscula_rechazado(self):
        h = "G" * 64
        with self.assertRaises(ValueError):
            ref_reserva_completo(h)

    def test_ref_reserva_completo_mayusculas_rechazado(self):
        h = "ABCDEF" + "0" * 58
        with self.assertRaises(ValueError):
            ref_reserva_completo(h)

    def test_ref_reserva_completo_con_barra_rechazado(self):
        h = "a" * 32 + "/" + "b" * 31
        with self.assertRaises(ValueError):
            ref_reserva_completo(h)

    def test_ref_reserva_completo_con_espacio_rechazado(self):
        h = "a" * 32 + " " + "b" * 31
        with self.assertRaises(ValueError):
            ref_reserva_completo(h)

    def test_ref_reserva_completo_no_hex_rechazado(self):
        h = "z" * 64
        with self.assertRaises(ValueError):
            ref_reserva_completo(h)

    def test_ref_reserva_completo_64_hex_minusculas_aceptado(self):
        h = "0123456789abcdef" * 4
        ref = ref_reserva_completo(h)

        self.assertEqual(
            ref,
            "refs/heads/gestorgit-reservas/" + h
        )

    # --- Casos adicionales ---

    def test_ruta_vacia_invalida(self):
        resultado = self.servicio.resolver("")

        self.assertFalse(resultado.es_ruta_valida)

    def test_ruta_none_invalida(self):
        resultado = self.servicio.resolver(None)

        self.assertFalse(resultado.es_ruta_valida)

    def test_ruta_con_nul_invalida(self):
        resultado = self.servicio.resolver("Paquetes\x00FINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    def test_ruta_con_cr_invalida(self):
        resultado = self.servicio.resolver("Paquetes\rFINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    def test_ruta_con_lf_invalida(self):
        resultado = self.servicio.resolver("Paquetes\nFINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    def test_ruta_doble_barra_invalida(self):
        resultado = self.servicio.resolver("Paquetes//FINI004.pls")

        self.assertFalse(resultado.es_ruta_valida)

    def test_nombre_vacio_antes_extension(self):
        resultado = self.servicio.resolver("Paquetes/.pls")

        self.assertFalse(resultado.es_reservable)

    def test_mayusculas_extension(self):
        # Las extensiones se comparan en minusculas.
        resultado = self.servicio.resolver("Paquetes/FINI004.PLS")

        # .PLS en minusculas es .pls, que coincide con el layout.
        # PurePosixPath().suffix devuelve .PLS, y lo convertimos
        # a minusculas con .lower().
        self.assertTrue(resultado.es_reservable)
        self.assertEqual(resultado.objeto.canonica(), "PACKAGE|FINI004")

    def test_nombre_con_guion_bajo(self):
        resultado = self.servicio.resolver("Paquetes/PKG_FINI004.pls")

        self.assertTrue(resultado.es_reservable)
        self.assertEqual(resultado.objeto.nombre, "PKG_FINI004")

    def test_nombre_con_dollar(self):
        resultado = self.servicio.resolver("Paquetes/PKG$1.pls")

        self.assertTrue(resultado.es_reservable)
        self.assertEqual(resultado.objeto.nombre, "PKG$1")

    def test_nombre_con_almohadilla(self):
        resultado = self.servicio.resolver("Paquetes/PKG#1.pls")

        self.assertTrue(resultado.es_reservable)
        self.assertEqual(resultado.objeto.nombre, "PKG#1")

    # --- Manifiesto None ---

    def test_manifiesto_none_lanza(self):
        with self.assertRaises(ValueError):
            ServicioObjetosOracle(None)


if __name__ == "__main__":
    unittest.main()
