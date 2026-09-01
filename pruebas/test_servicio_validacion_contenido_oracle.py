"""
Pruebas del servicio de validación de contenido SQL ↔ archivo
Oracle (V1.2).

Cubren la política de decodificación conservadora, el aislamiento
de comentarios y literales, las formas DDL soportadas, la
normalización PACKAGE BODY, la tolerancia de schema y la
comparación case-insensitive contra la clave canónica.
"""

import unittest

from modelos_reservas import ClaveObjetoOracle
from servicio_validacion_contenido_oracle import (
    AMBIGUO,
    COINCIDE,
    NO_APLICA,
    NO_COINCIDE_NOMBRE,
    NO_COINCIDE_TIPO,
    NO_VERIFICABLE,
    ServicioValidacionContenidoOracle,
)


CLAVE_PROCEDURE = ClaveObjetoOracle(
    tipo="PROCEDURE",
    nombre="PR_CERRAR_CAJA",
)

CLAVE_PACKAGE = ClaveObjetoOracle(
    tipo="PACKAGE",
    nombre="FINI004",
)


class PruebasDeteccionProcedimientos(unittest.TestCase):
    """PROCEDURE: coincidencias y contradicciones básicas."""

    def setUp(self):
        self.servicio = ServicioValidacionContenidoOracle()

    def test_procedure_correcto_coincide(self):
        contenido = (
            "CREATE OR REPLACE PROCEDURE PR_CERRAR_CAJA IS\n"
            "BEGIN\nNULL;\nEND;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)
        self.assertEqual(resultado.tipo_detectado, "PROCEDURE")
        self.assertEqual(
            resultado.nombre_detectado, "PR_CERRAR_CAJA"
        )

    def test_procedure_sin_or_replace_coincide(self):
        contenido = b"CREATE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_procedure_nombre_incorrecto(self):
        contenido = b"CREATE PROCEDURE PR_ABRIR_CAJA IS NULL;\n"

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_COINCIDE_NOMBRE)
        self.assertIn("PR_ABRIR_CAJA", resultado.motivo)

    def test_procedure_tipo_incorrecto(self):
        contenido = b"CREATE FUNCTION PR_CERRAR_CAJA RETURN NUMBER IS NULL;\n"

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_COINCIDE_TIPO)

    def test_procedure_tipo_y_nombre_incorrectos(self):
        contenido = b"CREATE FUNCTION PR_OTRA_COSA RETURN NUMBER IS NULL;\n"

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_COINCIDE_TIPO)

    def test_schema_qualifier_tolerado_sin_cambiar_clave(self):
        contenido = (
            "CREATE OR REPLACE PROCEDURE MI_ESQUEMA.PR_CERRAR_CAJA "
            "IS NULL;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)
        self.assertEqual(
            resultado.nombre_detectado, "PR_CERRAR_CAJA"
        )

    def test_case_insensitive_coincide(self):
        contenido = (
            "create or replace procedure pr_cerrar_caja is null;"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)


class PruebasDeteccionOtrosTipos(unittest.TestCase):
    """FUNCTION, TABLE, VIEW, TRIGGER y SEQUENCE."""

    def setUp(self):
        self.servicio = ServicioValidacionContenidoOracle()

    def test_function_coincide(self):
        clave = ClaveObjetoOracle(tipo="FUNCTION", nombre="FN_IVA")
        contenido = (
            "CREATE OR REPLACE FUNCTION FN_IVA RETURN NUMBER IS\n"
            "BEGIN\nRETURN 0;\nEND;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_table_coincide(self):
        clave = ClaveObjetoOracle(tipo="TABLE", nombre="T_CLIENTES")
        contenido = (
            "CREATE TABLE T_CLIENTES (\n"
            "  ID NUMBER PRIMARY KEY\n"
            ");\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_view_coincide(self):
        clave = ClaveObjetoOracle(tipo="VIEW", nombre="VW_CLIENTES")
        contenido = (
            "CREATE OR REPLACE VIEW VW_CLIENTES AS\n"
            "SELECT 1 FROM DUAL;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_trigger_coincide(self):
        clave = ClaveObjetoOracle(tipo="TRIGGER", nombre="TR_AUDITA")
        contenido = (
            "CREATE OR REPLACE TRIGGER TR_AUDITA\n"
            "BEFORE INSERT ON T_CLIENTES\n"
            "BEGIN NULL; END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_sequence_coincide(self):
        clave = ClaveObjetoOracle(tipo="SEQUENCE", nombre="SEQ_CLI")
        contenido = (
            "CREATE SEQUENCE SEQ_CLI INCREMENT BY 1;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_editionable_y_noneditionable_tolerados(self):
        clave = ClaveObjetoOracle(tipo="PROCEDURE", nombre="PR_X")
        contenido_editionable = (
            "CREATE OR REPLACE EDITIONABLE PROCEDURE PR_X IS NULL;\n"
        ).encode("utf-8")
        contenido_noneditionable = (
            "CREATE OR REPLACE NONEDITIONABLE PROCEDURE PR_X IS NULL;\n"
        ).encode("utf-8")

        self.assertEqual(
            self.servicio.validar(clave, contenido_editionable).resultado,
            COINCIDE,
        )
        self.assertEqual(
            self.servicio.validar(
                clave, contenido_noneditionable
            ).resultado,
            COINCIDE,
        )

    def test_view_force_y_no_force_tolerados(self):
        clave = ClaveObjetoOracle(tipo="VIEW", nombre="VW_X")
        contenido_force = (
            "CREATE OR REPLACE FORCE VIEW VW_X AS SELECT 1 FROM DUAL;\n"
        ).encode("utf-8")
        contenido_no_force = (
            "CREATE OR REPLACE NO FORCE VIEW VW_X AS SELECT 1 FROM DUAL;\n"
        ).encode("utf-8")

        self.assertEqual(
            self.servicio.validar(clave, contenido_force).resultado,
            COINCIDE,
        )
        self.assertEqual(
            self.servicio.validar(clave, contenido_no_force).resultado,
            COINCIDE,
        )

    def test_table_global_temporary_tolerado(self):
        clave = ClaveObjetoOracle(tipo="TABLE", nombre="T_TMP")
        contenido = (
            "CREATE GLOBAL TEMPORARY TABLE T_TMP (ID NUMBER) "
            "ON COMMIT DELETE ROWS;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_materialized_view_no_se_detecta_como_view(self):
        """MATERIALIZED VIEW está fuera de alcance: no es VIEW."""

        clave = ClaveObjetoOracle(tipo="VIEW", nombre="MV_RESUMEN")
        contenido = (
            "CREATE MATERIALIZED VIEW MV_RESUMEN AS SELECT 1 FROM DUAL;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_create_type_no_soportado_no_inventa_identidad(self):
        clave = ClaveObjetoOracle(tipo="PROCEDURE", nombre="PR_X")
        contenido = (
            "CREATE OR REPLACE TYPE TP_X AS OBJECT (ID NUMBER);\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_create_index_no_soportado_no_inventa_identidad(self):
        clave = ClaveObjetoOracle(tipo="TABLE", nombre="T_X")
        contenido = (
            "CREATE UNIQUE INDEX IX_X ON T_X (ID);\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)


class PruebasDeteccionPackage(unittest.TestCase):
    """PACKAGE spec/body, spec+body y ambigüedades."""

    def setUp(self):
        self.servicio = ServicioValidacionContenidoOracle()

    def test_package_spec_coincide(self):
        contenido = (
            "CREATE OR REPLACE PACKAGE FINI004 IS\n"
            "PROCEDURE P1;\n"
            "END FINI004;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_package_body_normaliza_a_package(self):
        contenido = (
            "CREATE OR REPLACE PACKAGE BODY FINI004 IS\n"
            "PROCEDURE P1 IS BEGIN NULL; END;\n"
            "END FINI004;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)
        self.assertEqual(resultado.tipo_detectado, "PACKAGE")
        self.assertEqual(resultado.nombre_detectado, "FINI004")

    def test_package_spec_y_body_mismo_nombre_aceptado(self):
        contenido = (
            "CREATE OR REPLACE PACKAGE FINI004 IS\n"
            "PROCEDURE P1;\n"
            "END FINI004;\n"
            "CREATE OR REPLACE PACKAGE BODY FINI004 IS\n"
            "PROCEDURE P1 IS BEGIN NULL; END;\n"
            "END FINI004;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_package_nombres_diferentes_ambiguo(self):
        contenido = (
            "CREATE PACKAGE FINI004 IS END;\n"
            "CREATE PACKAGE BODY FINI009 IS END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

        self.assertEqual(resultado.resultado, AMBIGUO)
        self.assertIn("PACKAGE|FINI004", resultado.motivo)
        self.assertIn("PACKAGE|FINI009", resultado.motivo)

    def test_body_otro_nombre_ambiguo(self):
        contenido = (
            "CREATE PACKAGE FINI004 IS END;\n"
            "CREATE OR REPLACE PACKAGE BODY OTRO IS END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

        self.assertEqual(resultado.resultado, AMBIGUO)

    def test_package_con_procedure_interno_no_es_ambiguo(self):
        """El PROCEDURE del cuerpo no lleva CREATE: no cuenta."""

        contenido = (
            "CREATE OR REPLACE PACKAGE BODY FINI004 IS\n"
            "PROCEDURE P1 IS BEGIN NULL; END;\n"
            "END FINI004;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_procedure_y_package_ambiguo(self):
        contenido = (
            "CREATE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"
            "CREATE PACKAGE FINI004 IS END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, AMBIGUO)

    def test_misma_identidad_repetida_no_es_ambigua(self):
        contenido = (
            "CREATE TABLE T_CLIENTES (ID NUMBER);\n"
            "CREATE TABLE T_CLIENTES (ID NUMBER);\n"
        ).encode("utf-8")

        clave = ClaveObjetoOracle(tipo="TABLE", nombre="T_CLIENTES")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)


class PruebasReglasLexicas(unittest.TestCase):
    """Comentarios, literales, BOM y casos degenerados."""

    def setUp(self):
        self.servicio = ServicioValidacionContenidoOracle()

    def test_comentarios_antes_del_create_tolerados(self):
        contenido = (
            "-- Encabezado del objeto\n"
            "/* Bloque de\n   licencia */\n"
            "SET SERVEROUTPUT ON\n"
            "WHENEVER SQLERROR EXIT FAILURE\n"
            "CREATE OR REPLACE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_create_dentro_de_comentario_linea_no_detecta(self):
        contenido = (
            "-- CREATE PROCEDURE PR_FALSO\n"
            "CREATE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_create_dentro_de_comentario_bloque_no_detecta(self):
        contenido = (
            "/* CREATE PROCEDURE PR_FALSO */\n"
            "CREATE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_create_dentro_de_string_no_detecta(self):
        contenido = (
            "CREATE PROCEDURE PR_CERRAR_CAJA IS\n"
            "BEGIN\n"
            "  EXECUTE IMMEDIATE "
            "'CREATE PROCEDURE PR_FALSO IS NULL;';\n"
            "END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_comillas_escape_en_string(self):
        contenido = (
            "CREATE PROCEDURE PR_CERRAR_CAJA IS\n"
            "BEGIN\n"
            "  DBMS_OUTPUT.PUT_LINE('it''s CREATE PROCEDURE PR_FALSO');\n"
            "END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_bom_utf8_tolerado(self):
        cuerpo = (
            "CREATE OR REPLACE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"
        )

        contenido = b"\xef\xbb\xbf" + cuerpo.encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_bom_utf8_invalido_no_verificable(self):
        contenido = b"\xef\xbb\xbf" + b"\xff\xfe CREATE PROCEDURE X;\n"

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_windows_1252_tolerado(self):
        # 0xF3 es 'ó' en Windows-1252 y no es UTF-8 válido aquí.
        contenido = (
            b"-- Comentario con codificaci\xf3n Windows-1252\n"
            b"CREATE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"
        )

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_bytes_no_decodificables_no_verificable(self):
        # 0x81 y 0x9D no existen en Windows-1252 ni en UTF-8.
        contenido = b"\x81\x9d CREATE PROCEDURE PR_CERRAR_CAJA;\n"

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_bom_utf16_no_verificable(self):
        contenido = (
            "CREATE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"
        ).encode("utf-16")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_nul_bytes_no_verificable(self):
        contenido = b"CREATE\x00 PROCEDURE PR_CERRAR_CAJA;\n"

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_archivo_vacio_no_verificable(self):
        resultado = self.servicio.validar(CLAVE_PROCEDURE, b"")

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)
        self.assertIn("CREATE", resultado.motivo)

    def test_sin_create_soportado_no_verificable(self):
        contenido = b"SELECT 1 FROM DUAL;\n"

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_create_incompleto_sin_nombre_no_verificable(self):
        contenido = b"CREATE OR REPLACE PACKAGE BODY"

        resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_create_encabezado_nombrado_declara_identidad(self):
        """CREATE PACKAGE FINI004 al final: la identidad está."""

        contenido = b"CREATE OR REPLACE PACKAGE FINI004"

        resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_identificador_entrecomillado_no_verificable(self):
        contenido = (
            'CREATE PROCEDURE "Nombre Mixto" IS NULL;\n'
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_identificador_simple_con_comillas_finales_distinto(self):
        """PR_X entrecomillado NO equivale a PR_X sin comillas."""

        contenido = b'CREATE PROCEDURE "PR_CERRAR_CAJA" IS NULL;\n'

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_token_create_embebido_no_se_confunde(self):
        """1CREATE no produce un token CREATE falso."""

        contenido = b"1CREATE PROCEDURE PR_OTRA IS NULL;\n"

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)


class PruebasContratoResultado(unittest.TestCase):
    """Estados NO_APLICA, claves inválidas y entradas anómalas."""

    def setUp(self):
        self.servicio = ServicioValidacionContenidoOracle()

    def test_contenido_none_es_no_aplica(self):
        resultado = self.servicio.validar(CLAVE_PROCEDURE, None)

        self.assertEqual(resultado.resultado, NO_APLICA)
        self.assertEqual(resultado.tipo_ruta, "PROCEDURE")
        self.assertEqual(resultado.nombre_ruta, "PR_CERRAR_CAJA")

    def test_acepta_cadena_canonica(self):
        contenido = b"CREATE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"

        resultado = self.servicio.validar(
            "PROCEDURE|PR_CERRAR_CAJA", contenido
        )

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_clave_invalida_no_verificable(self):
        contenido = b"CREATE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"

        resultado = self.servicio.validar("sin-separador", contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_clave_none_no_verificable(self):
        resultado = self.servicio.validar(None, b"CREATE TABLE T;")

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_contenido_no_bytes_no_verificable(self):
        resultado = self.servicio.validar(
            CLAVE_PROCEDURE, "CREATE PROCEDURE PR_CERRAR_CAJA;"
        )

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_detectar_devuelve_identidades(self):
        contenido = (
            "CREATE OR REPLACE PROCEDURE PR_CERRAR_CAJA IS NULL;\n"
        ).encode("utf-8")

        deteccion = self.servicio.detectar(contenido)

        self.assertTrue(deteccion.exitoso)
        self.assertEqual(
            deteccion.identidades, ("PROCEDURE|PR_CERRAR_CAJA",)
        )

    def test_detectar_contenido_invalido(self):
        deteccion = self.servicio.detectar(b"\x81\x9d nada")

        self.assertFalse(deteccion.exitoso)
        self.assertEqual(deteccion.identidades, ())


# =====================================================================
# REV1 R1: literales alternativos Oracle (q-quote)
# =====================================================================


class PruebasQQuote(unittest.TestCase):
    """
    GG-PROMPT-055-REV1 R1: el contenido interno de q'...' nunca
    expone CREATE al detector; formas mal cerradas son
    NO_VERIFICABLE sin recuperación parcial.
    """

    def setUp(self):
        self.servicio = ServicioValidacionContenidoOracle()

    def test_q_quote_con_create_coincidente_falso_no_verificable(self):
        """Caso obligatorio A: SOLO q-quote con CREATE igual a la
        clave. Nunca COINCIDE."""

        contenido = (
            "BEGIN\n"
            "  x := q'[it's text CREATE OR REPLACE PROCEDURE "
            "PR_CERRAR_CAJA IS NULL;]';\n"
            "END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_ddl_real_mas_q_quote_con_create_falso_coincide(self):
        """Caso obligatorio B: el DDL real manda; el CREATE dentro
        del q-quote (de OTRO objeto) no cuenta."""

        contenido = (
            "CREATE OR REPLACE PROCEDURE PR_CERRAR_CAJA IS\n"
            "BEGIN\n"
            "  x := q'[it's text CREATE PROCEDURE PR_OTRO IS NULL;]';\n"
            "END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)
        self.assertEqual(resultado.nombre_detectado, "PR_CERRAR_CAJA")

    def test_q_quote_mal_cerrado_no_verificable(self):
        """Caso obligatorio C."""

        contenido = (
            "BEGIN\n"
            "  x := q'[it's text CREATE PROCEDURE PR_CERRAR_CAJA;\n"
            "END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)
        self.assertIn("sin cerrar", resultado.motivo)

    def test_q_quote_con_comentarios_y_comillas_internas(self):
        """Caso obligatorio D: contenido interno heterogéneo no
        afecta la identidad."""

        contenido = (
            "CREATE PROCEDURE PR_CERRAR_CAJA IS\n"
            "BEGIN\n"
            "  x := q'[v -- comentario /* bloque */ 'texto' "
            "CREATE PACKAGE OTRO IS NULL;]';\n"
            "END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_delimitadores_emparejados_reconocidos(self):
        """q'[' q'{' q'(' q'<' y Q mayúscula consumen igual."""

        for forma in (
            "q'[@X@]'",
            "q'{@X@}'",
            "q'(@X@)'",
            "q'<@X@>'",
            "Q'[@X@]'",
        ):
            literal = forma.replace("@X@", "it's CREATE PACKAGE OTRO;")
            contenido = (
                "CREATE PACKAGE FINI004 IS\n"
                "BEGIN x := " + literal + "; END;\n"
            ).encode("utf-8")

            resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

            self.assertEqual(
                resultado.resultado,
                COINCIDE,
                f"forma {forma}: {resultado.motivo}",
            )

    def test_delimitador_simple_reconocido(self):
        contenido = (
            "CREATE PACKAGE FINI004 IS\n"
            "BEGIN x := q'!it's CREATE PACKAGE OTRO!'; END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_nq_mayuscula_y_minuscula_reconocidas(self):
        for forma in ("nq'[x CREATE PACKAGE OTRO;]'", "NQ'[x]'"):
            contenido = (
                "CREATE PACKAGE FINI004 IS\n"
                "BEGIN x := " + forma + "; END;\n"
            ).encode("utf-8")

            resultado = self.servicio.validar(CLAVE_PACKAGE, contenido)

            self.assertEqual(resultado.resultado, COINCIDE)

    def test_identificador_terminado_en_q_no_es_q_quote(self):
        """mi_varq'hola' es identificador + literal normal: el
        contenido del literal se oculta igual (es un string)."""

        contenido = (
            "CREATE PROCEDURE PR_CERRAR_CAJA IS\n"
            "BEGIN x := mi_varq'CREATE PACKAGE OTRO'; END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_q_quote_con_delimitador_blanco_malformado(self):
        contenido = (
            "CREATE PROCEDURE PR_CERRAR_CAJA IS\n"
            "BEGIN x := q' texto'; END;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_string_normal_sin_cerrar_no_verificable(self):
        """La política fail-closed de literales también cubre el
        literal simple sin cerrar."""

        contenido = (
            "CREATE PROCEDURE PR_CERRAR_CAJA IS\n"
            "BEGIN x := 'sin cerrar;\n"
        ).encode("utf-8")

        resultado = self.servicio.validar(CLAVE_PROCEDURE, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)


# =====================================================================
# REV1 R2: gramática positiva de modificadores por tipo
# =====================================================================


class PruebasGramaticaModificadores(unittest.TestCase):
    """
    GG-PROMPT-055-REV1 R2: los modificadores SOLO valen para los
    tipos que los admiten; combinaciones cruzadas o imposibles
    hacen que la sentencia se ignore (sin otra sentencia válida,
    NO_VERIFICABLE).
    """

    def setUp(self):
        self.servicio = ServicioValidacionContenidoOracle()

    def test_force_procedure_ignorado(self):
        contenido = b"CREATE FORCE PROCEDURE PR_X IS NULL;\n"

        clave = ClaveObjetoOracle(tipo="PROCEDURE", nombre="PR_X")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_global_temporary_view_ignorado(self):
        contenido = (
            "CREATE GLOBAL TEMPORARY VIEW VW_X AS SELECT 1 "
            "FROM DUAL;\n"
        ).encode("utf-8")

        clave = ClaveObjetoOracle(tipo="VIEW", nombre="VW_X")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_no_force_sequence_ignorado(self):
        contenido = (
            "CREATE NO FORCE SEQUENCE SEQ_X START WITH 1;\n"
        ).encode("utf-8")

        clave = ClaveObjetoOracle(tipo="SEQUENCE", nombre="SEQ_X")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_no_solo_ignorado(self):
        contenido = b"CREATE NO PROCEDURE PR_X IS NULL;\n"

        clave = ClaveObjetoOracle(tipo="PROCEDURE", nombre="PR_X")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_force_duplicado_ignorado(self):
        contenido = (
            "CREATE FORCE FORCE VIEW VW_X AS SELECT 1;\n"
        ).encode("utf-8")

        clave = ClaveObjetoOracle(tipo="VIEW", nombre="VW_X")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_global_temporary_package_ignorado(self):
        contenido = b"CREATE GLOBAL TEMPORARY PACKAGE PKG_X;\n"

        clave = ClaveObjetoOracle(tipo="PACKAGE", nombre="PKG_X")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_editionable_table_ignorado(self):
        contenido = (
            "CREATE EDITIONABLE TABLE T_X (ID NUMBER);\n"
        ).encode("utf-8")

        clave = ClaveObjetoOracle(tipo="TABLE", nombre="T_X")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, NO_VERIFICABLE)

    def test_sentencia_invalida_no_tapa_sentencia_valida(self):
        """La sentencia con mods inválidos se ignora; una
        sentencia válida posterior sigue siendo la identidad."""

        contenido = (
            "CREATE FORCE PROCEDURE PR_X IS NULL;\n"
            "CREATE PROCEDURE PR_X IS NULL;\n"
        ).encode("utf-8")

        clave = ClaveObjetoOracle(tipo="PROCEDURE", nombre="PR_X")

        resultado = self.servicio.validar(clave, contenido)

        self.assertEqual(resultado.resultado, COINCIDE)

    def test_positivos_preservados(self):
        """Los positivos de 055 siguen aceptándose."""

        casos = [
            (
                ClaveObjetoOracle(tipo="VIEW", nombre="VW_X"),
                "CREATE OR REPLACE FORCE VIEW VW_X AS SELECT 1;\n",
            ),
            (
                ClaveObjetoOracle(tipo="VIEW", nombre="VW_X"),
                "CREATE OR REPLACE NO FORCE VIEW VW_X AS SELECT 1;\n",
            ),
            (
                ClaveObjetoOracle(tipo="VIEW", nombre="VW_X"),
                "CREATE OR REPLACE EDITIONABLE NO FORCE VIEW VW_X "
                "AS SELECT 1;\n",
            ),
            (
                ClaveObjetoOracle(tipo="TABLE", nombre="T_X"),
                "CREATE GLOBAL TEMPORARY TABLE T_X (ID NUMBER);\n",
            ),
            (
                ClaveObjetoOracle(tipo="PROCEDURE", nombre="PR_X"),
                "CREATE OR REPLACE NONEDITIONABLE PROCEDURE PR_X "
                "IS NULL;\n",
            ),
            (
                ClaveObjetoOracle(tipo="FUNCTION", nombre="FN_X"),
                "CREATE EDITIONABLE FUNCTION FN_X RETURN NUMBER "
                "IS NULL;\n",
            ),
        ]

        for clave, texto in casos:
            resultado = self.servicio.validar(
                clave, texto.encode("utf-8")
            )
            self.assertEqual(
                resultado.resultado,
                COINCIDE,
                f"{texto}: {resultado.motivo}",
            )


if __name__ == "__main__":
    unittest.main()
