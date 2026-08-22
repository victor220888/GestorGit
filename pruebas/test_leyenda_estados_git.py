"""
Pruebas de la leyenda / ayuda contextual de estados Git V1.

Verifican que principal.py contiene el diccionario
CONTENIDO_AYUDA_ESTADOS_GIT_V1 con los nueve bloques pedagógicos
esperados (modelo mental HEAD/índice/working tree, estados
concretos ?? / " M" / "M " / MM / conflicto, otros estados,
códigos XY e Inspector/acciones), que el contenido cumple las
reglas didácticas de la etapa y NO contiene las afirmaciones
prohibidas.

Además, unas pruebas con ast verifican el cableado estático de la
ventana: el botón "¿Qué significan estos estados?" está conectado
a abrir_ayuda_estados_git, la ventana es NO modal (sin
grab_set/wait_window), consume el diccionario centralizado (sin
textos pedagógicos inline en los métodos Tkinter), no agrega
llamadas nuevas a AyudaEmergente y los tooltips V1 siguen
intactos (37 = total HISTÓRICO al cerrar la Leyenda V1; 38 =
total ACTUAL después de la ayuda "publicar_rama" añadida por la
etapa posterior Publicar rama local).

Estas pruebas no dependen de un display gráfico real ni de mover
el ratón.
"""

import ast
import unittest
from pathlib import Path

import principal

CLAVES_ESPERADAS = (
    "modelo_head_indice_working_tree",
    "estado_no_rastreado",
    "estado_modificado_sin_preparar",
    "estado_modificado_preparado",
    "estado_preparado_y_vuelto_a_modificar",
    "estado_conflicto",
    "otros_estados",
    "codigos_xy",
    "inspector_y_acciones",
)

METODOS_VENTANA_AYUDA = (
    "abrir_ayuda_estados_git",
    "crear_ventana_ayuda_estados_git",
    "cerrar_ventana_ayuda_estados_git",
)


def texto(clave):
    """Devuelve el texto de una clave de la leyenda de estados."""

    return principal.CONTENIDO_AYUDA_ESTADOS_GIT_V1[clave]


def _arbol_principal():
    """Analiza principal.py con ast (sin depender de líneas fijas)."""

    ruta = Path(principal.__file__).resolve()
    return ast.parse(
        ruta.read_text(encoding="utf-8"),
        filename=str(ruta)
    )


def _metodo(arbol, nombre):
    """Devuelve el nodo FunctionDef con el nombre pedido."""

    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.FunctionDef)
            and nodo.name == nombre
        ):
            return nodo

    return None


def _llamadas_a(nombre, base=None):
    """
    Lista de nodos Call de 'nombre' dentro de 'base' (o todo).

    Reconoce AMBAS formas de llamada:

    - ast.Name:        AyudaEmergente(...)
    - ast.Attribute:   objeto.grab_set(), objeto.wait_window()

    La comparación es exacta por nombre (nodo.func.id para Name y
    nodo.func.attr para Attribute). No depende de líneas fijas:
    recorre el árbol sintáctico.
    """

    nodos = (
        ast.walk(base)
        if base is not None
        else ast.walk(_arbol_principal())
    )

    def nombre_llamada(nodo):
        if isinstance(nodo.func, ast.Name):
            return nodo.func.id
        if isinstance(nodo.func, ast.Attribute):
            return nodo.func.attr
        return None

    return [
        nodo
        for nodo in nodos
        if (
            isinstance(nodo, ast.Call)
            and nombre_llamada(nodo) == nombre
        )
    ]


class TestLeyendaDiccionario(unittest.TestCase):
    """Existencia, completitud y no vacíos del diccionario."""

    def test_existe_diccionario_centralizado(self):
        self.assertTrue(
            hasattr(principal, "CONTENIDO_AYUDA_ESTADOS_GIT_V1")
        )
        self.assertIsInstance(
            principal.CONTENIDO_AYUDA_ESTADOS_GIT_V1,
            dict
        )

    def test_contiene_exactamente_los_bloques_esperados(self):
        self.assertEqual(
            set(principal.CONTENIDO_AYUDA_ESTADOS_GIT_V1.keys()),
            set(CLAVES_ESPERADAS)
        )

    def test_ningun_bloque_vacio(self):
        for clave in CLAVES_ESPERADAS:
            self.assertTrue(
                texto(clave).strip(),
                f"El bloque '{clave}' está vacío."
            )


class TestLeyendaModeloMental(unittest.TestCase):
    """Nivel 1: HEAD, índice/staging y working tree."""

    def test_head_se_explica_como_referencia_al_commit_actual(self):
        t = texto("modelo_head_indice_working_tree")
        self.assertIn("apunta al commit actual", t)
        self.assertIn("la referencia de la versión ya confirmada", t)
        self.assertIn("historial local", t)

    def test_indice_no_se_presenta_como_carpeta_fisica(self):
        t = texto("modelo_head_indice_working_tree")
        self.assertIn("NO es una carpeta física del disco", t)
        self.assertIn(
            "no mueve destructivamente el archivo del disco",
            t
        )

    def test_working_tree_son_archivos_actuales_del_disco(self):
        t = texto("modelo_head_indice_working_tree")
        self.assertIn(
            "archivos actuales que tienes en el disco",
            t
        )
        self.assertIn("dentro del repositorio", t)

    def test_preparar_se_describe_como_copiar_registrar(self):
        t = texto("modelo_head_indice_working_tree")
        self.assertIn(
            "preparar copia/registra en el índice la versión "
            "actual del archivo",
            t
        )

    def test_no_se_dice_que_preparar_mueve_los_cambios(self):
        for clave in CLAVES_ESPERADAS:
            self.assertNotIn(
                "mueve los cambios",
                texto(clave),
                f"El bloque '{clave}' afirma que algo se mueve."
            )

    def test_no_se_dice_que_el_indice_se_lleva_cambios_al_historial(self):
        for clave in CLAVES_ESPERADAS:
            self.assertNotIn(
                "el índice se lleva los cambios al historial",
                texto(clave),
                f"El bloque '{clave}' usa la metáfora prohibida."
            )

    def test_commit_se_crea_desde_el_indice_y_head_avanza(self):
        t = texto("modelo_head_indice_working_tree")
        self.assertIn(
            "a partir del contenido preparado en el índice",
            t
        )
        self.assertIn("HEAD avanza al nuevo commit", t)

    def test_relaciones_working_tree_indice_head_presentes(self):
        t = texto("modelo_head_indice_working_tree")
        self.assertIn("Preparar / Actualizar preparados", t)
        self.assertIn("Crear commit", t)
        self.assertIn("HEAD avanza al nuevo commit", t)


class TestLeyendaEstadosConcretos(unittest.TestCase):
    """Nivel 2: ??, " M", "M ", MM y conflicto."""

    def test_estado_nuevo_no_rastreado(self):
        t = texto("estado_no_rastreado")
        self.assertIn('"??"', t)
        self.assertIn("NO RASTREADO", t)
        self.assertIn("no lo está rastreando", t)

    def test_archivo_nuevo_si_existe_en_working_tree(self):
        t = texto("estado_no_rastreado")
        self.assertIn("SÍ existe en el working tree", t)
        self.assertIn("working tree (disco)", t)
        self.assertIn("todavía no hay una versión preparada", t)
        self.assertIn("Preparar registra/copia su versión actual", t)

    def test_nuevo_no_dice_fuera_del_working_tree(self):
        for clave in CLAVES_ESPERADAS:
            self.assertNotIn(
                "fuera del working tree",
                texto(clave),
                f"El bloque '{clave}' contiene la afirmación "
                "prohibida."
            )

    def test_espacio_m_y_m_espacio_se_distinguen(self):
        t_sin_preparar = texto("estado_modificado_sin_preparar")
        t_preparado = texto("estado_modificado_preparado")

        self.assertIn('" M"', t_sin_preparar)
        self.assertIn("(espacio + M)", t_sin_preparar)
        self.assertIn("primera posición vacía", t_sin_preparar)
        self.assertIn("segunda posición M", t_sin_preparar)
        self.assertIn(
            "el índice coincide con HEAD para ese cambio",
            t_sin_preparar
        )
        self.assertIn("el working tree difiere del índice", t_sin_preparar)

        self.assertIn('"M "', t_preparado)
        self.assertIn("(M + espacio)", t_preparado)
        self.assertIn("primera posición M", t_preparado)
        self.assertIn("segunda posición vacía", t_preparado)
        self.assertIn("el índice difiere de HEAD", t_preparado)
        self.assertIn(
            "el working tree coincide con la versión preparada",
            t_preparado
        )

    def test_tabla_para_sin_preparar_y_preparado(self):
        t_sin_preparar = texto("estado_modificado_sin_preparar")
        t_preparado = texto("estado_modificado_preparado")
        self.assertIn("Estado = Modificado\n", t_sin_preparar)
        self.assertIn("Preparado = No", t_sin_preparar)
        self.assertIn("Estado = Modificado y preparado\n", t_preparado)
        self.assertIn("Preparado = Sí", t_preparado)

    def test_mm_explica_dos_versiones(self):
        t = texto("estado_preparado_y_vuelto_a_modificar")
        self.assertIn("dos versiones distintas", t)
        self.assertIn("la preparada (en el índice)", t)
        self.assertIn("la actual del disco (working tree)", t)
        self.assertIn("Preparado = Sí (hay cambios nuevos)", t)

    def test_mm_cambios_posteriores_no_entran_automaticamente(self):
        t = texto("estado_preparado_y_vuelto_a_modificar")
        self.assertIn(
            "el commit usaría la versión que está en el índice",
            t
        )
        self.assertIn("NO automáticamente", t)
        self.assertIn("Actualizar preparados", t)

    def test_mm_se_relaciona_con_ver_cambios_locales(self):
        t = texto("estado_preparado_y_vuelto_a_modificar")
        self.assertIn("Ver cambios locales...", t)

    def test_conflicto_muestra_no_aplica(self):
        t = texto("estado_conflicto")
        self.assertIn("Preparado = No aplica", t)
        self.assertIn("Estado = Conflicto", t)

    def test_conflicto_requiere_decision_humana(self):
        t = texto("estado_conflicto")
        self.assertIn("una persona decida", t)
        self.assertIn("NO elige una versión automáticamente", t)
        self.assertIn("bloquea el commit mientras exista el conflicto", t)

    def test_conflicto_no_es_preparado_ni_sin_preparar(self):
        t = texto("estado_conflicto")
        self.assertIn('"preparado" ni "sin preparar"', t)

    def test_conflicto_no_se_prepara_ni_se_quita_ni_se_actualiza(self):
        t = texto("estado_conflicto")
        self.assertIn("NO prepara normalmente el conflicto", t)
        self.assertIn("NO permite quitarlo de preparados", t)
        self.assertIn("NO lo actualiza con Actualizar preparados", t)

    def test_conflicto_enumera_siete_codigos_exactos(self):
        t = texto("estado_conflicto")
        self.assertIn("DD AU UD UA DU AA UU", t)

    def test_no_existe_afirmacion_generica_m_siempre(self):
        for clave in CLAVES_ESPERADAS:
            self.assertNotIn(
                "M siempre",
                texto(clave),
                f"El bloque '{clave}' afirma un significado "
                "único de M."
            )

    def test_letra_m_se_explica_como_dependiente_de_posicion(self):
        t = texto("codigos_xy")
        self.assertIn("sin conocer su posición, puede ser ambigua", t)
        self.assertIn("depende de su posición en XY", t)


class TestLeyendaOtrosEstadosYCodigosXY(unittest.TestCase):
    """Otros estados y parte avanzada XY."""

    def test_otros_estados_agregado_eliminado_renombrado(self):
        t = texto("otros_estados")
        self.assertIn("A = agregado", t)
        self.assertIn("D = eliminado", t)
        self.assertIn("R = renombrado", t)

    def test_otros_estados_explican_posiciones(self):
        t = texto("otros_estados")
        self.assertIn("primera posición: el índice comparado con HEAD", t)
        self.assertIn(
            "segunda posición: el working tree comparado con el índice",
            t
        )

    def test_no_se_afirma_deteccion_automatica_de_copias(self):
        for clave in CLAVES_ESPERADAS:
            self.assertNotIn(
                "detecta copias por defecto",
                texto(clave),
                f"El bloque '{clave}' afirma detección de copias."
            )

    def test_codigos_xy_definen_ambas_posiciones(self):
        t = texto("codigos_xy")
        self.assertIn("git status --porcelain", t)
        self.assertIn("X: estado del ÍNDICE respecto de HEAD", t)
        self.assertIn(
            "Y: estado del WORKING TREE respecto del índice",
            t
        )

    def test_codigos_xy_ejemplos_explicitos(self):
        t = texto("codigos_xy")
        self.assertIn('" M" = espacio + M', t)
        self.assertIn('"M " = M + espacio', t)
        self.assertIn('"MM" = M + M', t)
        self.assertIn('"??" = caso especial', t)


class TestLeyendaInspectorYAcciones(unittest.TestCase):
    """Relación con el Inspector y con las acciones."""

    def test_inspector_sin_preparar_working_tree_vs_indice(self):
        t = texto("inspector_y_acciones")
        self.assertIn('pestaña "Sin preparar"', t)
        self.assertIn("working tree comparado con el índice", t)
        self.assertIn("git diff", t)

    def test_inspector_preparados_indice_vs_head(self):
        t = texto("inspector_y_acciones")
        self.assertIn('pestaña "Preparados"', t)
        self.assertIn("índice comparado con HEAD", t)
        self.assertIn("git diff --cached", t)

    def test_inspector_mm_pestanas_con_diffs_diferentes(self):
        t = texto("inspector_y_acciones")
        self.assertIn("MM ambas pestañas pueden mostrar diffs", t)

    def test_recomendacion_ver_cambios_locales(self):
        t = texto("inspector_y_acciones")
        self.assertIn("usa Ver cambios locales...", t)
        self.assertIn("qué sigue fuera del índice", t)

    def test_quitar_de_preparados_no_promete_estado_final_unico(self):
        t = texto("inspector_y_acciones")
        self.assertIn("depende de cada caso", t)
        self.assertNotIn("siempre queda", t)
        self.assertNotIn("siempre quedará", t)
        self.assertIn("conserva el working tree", t)

    def test_preparar_actualizar_y_commit_breves(self):
        t = texto("inspector_y_acciones")
        self.assertIn("Preparar seleccionados: copia/registra", t)
        self.assertIn("Actualizar preparados: vuelve a copiar", t)
        self.assertIn(
            "Crear commit: crea el commit a partir de lo preparado",
            t
        )
        self.assertIn("no incorpora automáticamente", t)


class TestLeyendaCableadoEstatico(unittest.TestCase):
    """Cableado con ast: botón, ventana única, NO modal, tooltips
    V1 intactos (37 HISTÓRICO al cerrar la Leyenda; 38 ACTUAL tras
    la ayuda posterior de Publicar rama local)."""

    @classmethod
    def setUpClass(cls):
        cls.arbol = _arbol_principal()
        cls.metodo_crear = _metodo(
            cls.arbol,
            "crear_ventana_ayuda_estados_git"
        )
        cls.metodo_abrir = _metodo(
            cls.arbol,
            "abrir_ayuda_estados_git"
        )
        cls.metodo_cerrar = _metodo(
            cls.arbol,
            "cerrar_ventana_ayuda_estados_git"
        )

    @classmethod
    def _nodos_boton_ayuda(cls):
        botones = []

        for nodo in ast.walk(cls.arbol):
            if not isinstance(nodo, ast.Call):
                continue
            if not (
                isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in ("Button", "Label")
            ):
                continue

            texto_boton = None

            for palabra in nodo.keywords:
                if palabra.arg == "text" and isinstance(
                    palabra.value, ast.Constant
                ):
                    texto_boton = palabra.value.value

            if texto_boton == "¿Qué significan estos estados?":
                botones.append(nodo)

        return botones

    def test_boton_conectado_a_abrir_ayuda_estados_git(self):
        botones = self._nodos_boton_ayuda()
        self.assertEqual(len(botones), 1)

        comando = None

        for palabra in botones[0].keywords:
            if palabra.arg == "command":
                comando = palabra.value

        self.assertIsNotNone(comando)
        self.assertIsInstance(comando, ast.Attribute)
        self.assertEqual(
            comando.attr,
            "abrir_ayuda_estados_git"
        )

    def test_ventana_usa_diccionario_centralizado(self):
        self.assertIsNotNone(self.metodo_crear)

        subscripts = [
            nodo
            for nodo in ast.walk(self.metodo_crear)
            if (
                isinstance(nodo, ast.Subscript)
                and isinstance(nodo.value, ast.Name)
                and nodo.value.id == "CONTENIDO_AYUDA_ESTADOS_GIT_V1"
            )
        ]

        self.assertGreaterEqual(
            len(subscripts),
            1,
            "La ventana no consulta el diccionario centralizado."
        )

        claves_en_metodo = {
            nodo.value
            for nodo in ast.walk(self.metodo_crear)
            if (
                isinstance(nodo, ast.Constant)
                and isinstance(nodo.value, str)
                and nodo.value in CLAVES_ESPERADAS
            )
        }

        self.assertEqual(
            claves_en_metodo,
            set(CLAVES_ESPERADAS),
            "La ventana no consume todos los bloques del diccionario."
        )

    def test_no_existe_texto_pedagogico_inline_en_la_ventana(self):
        self.assertIsNotNone(self.metodo_crear)

        cuerpo = self.metodo_crear.body
        docstring = None

        if (
            cuerpo
            and isinstance(cuerpo[0], ast.Expr)
            and isinstance(cuerpo[0].value, ast.Constant)
        ):
            docstring = cuerpo[0].value

        constantes_largas = []

        for nodo in ast.walk(self.metodo_crear):
            if not isinstance(nodo, ast.Constant):
                continue
            if nodo is docstring:
                continue
            if not isinstance(nodo.value, str):
                continue
            if len(nodo.value) > 120:
                constantes_largas.append(nodo.value[:40])
            if (
                "MODELO MENTAL" in nodo.value
                or "ESTADO:" in nodo.value
            ):
                constantes_largas.append(nodo.value[:40])

        self.assertEqual(
            constantes_largas,
            [],
            "Hay textos pedagógicos inline en el método Tkinter."
        )

    def test_ventana_no_modal_sin_grab_set(self):
        for nombre in METODOS_VENTANA_AYUDA:
            metodo = _metodo(self.arbol, nombre)
            self.assertIsNotNone(metodo)
            llamadas = _llamadas_a("grab_set", metodo)
            self.assertEqual(
                llamadas,
                [],
                f"'{nombre}' usa grab_set (ventana modal)."
            )

    def test_ventana_no_modal_sin_wait_window(self):
        for nombre in METODOS_VENTANA_AYUDA:
            metodo = _metodo(self.arbol, nombre)
            self.assertIsNotNone(metodo)
            llamadas = _llamadas_a("wait_window", metodo)
            self.assertEqual(
                llamadas,
                [],
                f"'{nombre}' usa wait_window (ventana modal)."
            )

    def test_tooltips_existentes_siguen_siendo_38(self):
        # HISTÓRICO: al cerrar la Leyenda V1 el diccionario tenía
        # 37 claves; la clave 38 ("publicar_rama") fue añadida
        # POSTERIORMENTE por la etapa "Publicar rama local". Esta
        # prueba sigue garantizando que la Leyenda no añadió
        # ninguna clave propia.
        self.assertEqual(
            len(principal.TEXTOS_AYUDA_GIT_V1),
            38
        )

    def test_leyenda_y_tooltips_son_diccionarios_independientes(self):
        self.assertSetEqual(
            set(principal.CONTENIDO_AYUDA_ESTADOS_GIT_V1.keys())
            & set(principal.TEXTOS_AYUDA_GIT_V1.keys()),
            set()
        )

    def test_no_se_agregan_llamadas_nuevas_a_ayuda_emergente(self):
        # HISTÓRICO: al cerrar la Leyenda V1 había 37 llamadas; la
        # llamada 38 (publicar_rama) pertenece a la etapa posterior
        # "Publicar rama local". El total exacto se sigue vigilando
        # para que la Leyenda no haya añadido llamadas propias.
        total = _llamadas_a("AyudaEmergente")
        self.assertEqual(
            len(total),
            38,
            "Las llamadas a AyudaEmergente deben seguir siendo 38."
        )

    def test_metodos_de_la_ayuda_no_usan_ayuda_emergente(self):
        for nombre in METODOS_VENTANA_AYUDA:
            metodo = _metodo(self.arbol, nombre)
            self.assertIsNotNone(metodo)
            llamadas = _llamadas_a("AyudaEmergente", metodo)
            self.assertEqual(
                llamadas,
                [],
                f"'{nombre}' agrega un tooltip nuevo."
            )


class TestLlamadasHelper(unittest.TestCase):
    """
    Prueba focalizada del propio helper _llamadas_a.

    Construye un árbol AST artificial (sin tocar principal.py) con
    llamadas de método (ast.Attribute) y llamadas simples (ast.Name)
    para demostrar que el helper reconoce ambas formas y no
    confunde métodos con nombres distintos.
    """

    SNIPPET = (
        "obj.grab_set()\n"
        "obj.wait_window()\n"
        "AyudaEmergente(obj, \"texto\")\n"
        "obj.lift()\n"
    )

    @classmethod
    def setUpClass(cls):
        cls.arbol = ast.parse(cls.SNIPPET)

    def test_detecta_grab_set_como_attribute(self):
        llamadas = _llamadas_a("grab_set", self.arbol)
        self.assertEqual(len(llamadas), 1)
        self.assertIsInstance(
            llamadas[0].func,
            ast.Attribute
        )

    def test_detecta_wait_window_como_attribute(self):
        llamadas = _llamadas_a("wait_window", self.arbol)
        self.assertEqual(len(llamadas), 1)
        self.assertIsInstance(
            llamadas[0].func,
            ast.Attribute
        )

    def test_detecta_ayuda_emergente_como_name(self):
        llamadas = _llamadas_a("AyudaEmergente", self.arbol)
        self.assertEqual(len(llamadas), 1)
        self.assertIsInstance(
            llamadas[0].func,
            ast.Name
        )

    def test_no_confunde_otro_metodo(self):
        self.assertEqual(
            _llamadas_a("deiconify", self.arbol),
            []
        )


class TestLeyendaAjusteVisual(unittest.TestCase):
    """
    Microajuste visual de la ventana de ayuda de estados Git.

    Verifica la jerarquía tipográfica (tags titulo_seccion,
    subtitulo y codigo_git) y que el contenido pedagógico del
    diccionario NO cambió: la microetapa es solo visual.
    """

    @classmethod
    def setUpClass(cls):
        cls.arbol = _arbol_principal()
        cls.metodo_crear = _metodo(
            cls.arbol,
            "crear_ventana_ayuda_estados_git"
        )
        cls.metodo_helper = _metodo(
            cls.arbol,
            "_aplicar_tags_ayuda_estados_git"
        )

    @classmethod
    def _tags_config(cls, arbol_nodo):
        """Devuelve {nombre_tag: {font: ..., spacing1: ..., ...}}."""

        configs = {}

        for nodo in ast.walk(arbol_nodo):
            if not isinstance(nodo, ast.Call):
                continue
            if not (
                isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "tag_configure"
            ):
                continue
            if not nodo.args:
                continue
            nombre = None
            if isinstance(nodo.args[0], ast.Constant):
                nombre = nodo.args[0].value
            if not isinstance(nombre, str):
                continue

            extras = {}
            for palabra in nodo.keywords:
                if palabra.arg == "font" and isinstance(
                    palabra.value, ast.Tuple
                ):
                    extras["font"] = tuple(
                        e.value
                        for e in palabra.value.elts
                        if isinstance(e, ast.Constant)
                    )
                if palabra.arg in ("spacing1", "spacing3"):
                    if isinstance(palabra.value, ast.Constant):
                        extras[palabra.arg] = palabra.value.value
                if palabra.arg in ("foreground", "background"):
                    extras[palabra.arg] = (
                        palabra.value.value
                        if isinstance(palabra.value, ast.Constant)
                        else "<no-constant>"
                    )

            configs[nombre] = extras

        return configs

    def test_existen_los_tres_tags(self):
        tags = self._tags_config(self.metodo_crear)
        self.assertIn("titulo_seccion", tags)
        self.assertIn("subtitulo", tags)
        self.assertIn("codigo_git", tags)

    def test_titulo_seccion_fuente_y_espaciado(self):
        tags = self._tags_config(self.metodo_crear)
        cfg = tags["titulo_seccion"]
        self.assertEqual(cfg["font"], ("Segoe UI", 11, "bold"))
        self.assertEqual(cfg.get("spacing1"), 6)
        self.assertEqual(cfg.get("spacing3"), 6)

    def test_subtitulo_fuente(self):
        tags = self._tags_config(self.metodo_crear)
        self.assertEqual(tags["subtitulo"]["font"], ("Segoe UI", 10, "bold"))

    def test_codigo_git_fuente_consolas_bold(self):
        tags = self._tags_config(self.metodo_crear)
        self.assertEqual(tags["codigo_git"]["font"], ("Consolas", 10, "bold"))

    def test_tags_sin_colores(self):
        tags = self._tags_config(self.metodo_crear)
        for nombre in ("titulo_seccion", "subtitulo", "codigo_git"):
            self.assertNotIn(
                "foreground",
                tags[nombre],
                f"El tag {nombre} define foreground."
            )
            self.assertNotIn(
                "background",
                tags[nombre],
                f"El tag {nombre} define background."
            )

    def test_constante_subtitulos_ayuda_estados(self):
        self.assertEqual(
            principal._SUBTITULOS_AYUDA_ESTADOS,
            (
                "HEAD",
                "Índice / staging",
                "Working tree",
                "Ver cambios locales...",
                "Acciones:",
            )
        )

    def test_constante_lineas_codigo_git_ayuda(self):
        self.assertEqual(
            principal._LINEAS_CODIGO_GIT_AYUDA,
            (
                'Git XY: "??"',
                'Git XY: " M"',
                'Git XY: "M "',
                'Git XY: "MM"',
                '" M" = espacio + M (segunda posición: working tree modificado)',
                '"M " = M + espacio (primera posición: índice modificado)',
                '"MM" = M + M (modificado en el índice y vuelto a modificar)',
                '"??" = caso especial: archivo no rastreado',
            )
        )

    def test_cuatro_codigos_principales_son_disjuntos(self):
        codigos = principal._LINEAS_CODIGO_GIT_AYUDA
        self.assertIn('Git XY: "??"', codigos)
        self.assertIn('Git XY: " M"', codigos)
        self.assertIn('Git XY: "M "', codigos)
        self.assertIn('Git XY: "MM"', codigos)
        # Distinguen espacio+M de M+espacio: no son el mismo texto.
        self.assertNotIn('" M"', ['Git XY: "M "'])
        # Distinción estructural: los dos literales coexisten sin
        # confundirse (uno lleva espacio antes de M, otro después).
        self.assertNotEqual(
            'Git XY: " M"',
            'Git XY: "M "'
        )

    def test_helper_aplicar_tags_existe_y_se_llama(self):
        self.assertIsNotNone(self.metodo_helper)
        llamadas = [
            nodo
            for nodo in ast.walk(self.metodo_crear)
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "_aplicar_tags_ayuda_estados_git"
            )
        ]
        self.assertGreaterEqual(
            len(llamadas),
            1,
            "crear_ventana no invoca al helper de tags."
        )

    def test_helper_compara_lineas_exactas_con_las_constantes(self):
        self.assertIsNotNone(self.metodo_helper)

        strip_en_asignacion = False
        subt_en_in = False
        codigos_en_in = False

        for nodo in ast.walk(self.metodo_helper):
            if isinstance(nodo, ast.Assign):
                for sub in ast.walk(nodo.value):
                    if (
                        isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "strip"
                    ):
                        strip_en_asignacion = True
            if isinstance(nodo, ast.Compare) and nodo.ops:
                if isinstance(nodo.ops[0], ast.In):
                    comparator = nodo.comparators[0]
                    left = nodo.left
                    if (
                        isinstance(comparator, ast.Name)
                        and comparator.id == "_SUBTITULOS_AYUDA_ESTADOS"
                    ):
                        subt_en_in = True
                    if (
                        isinstance(comparator, ast.Name)
                        and comparator.id == "_LINEAS_CODIGO_GIT_AYUDA"
                    ):
                        codigos_en_in = True
                    if (
                        isinstance(left, ast.Name)
                        and left.id == "texto_linea"
                    ):
                        pass

        self.assertTrue(
            strip_en_asignacion,
            "El helper asigna texto_linea = linea.strip()."
        )
        self.assertTrue(
            subt_en_in,
            "El helper compara contra _SUBTITULOS_AYUDA_ESTADOS."
        )
        self.assertTrue(
            codigos_en_in,
            "El helper compara contra _LINEAS_CODIGO_GIT_AYUDA."
        )

    def test_helper_no_busca_letra_M_generic(self):
        self.assertIsNotNone(self.metodo_helper)

        for nodo in ast.walk(self.metodo_helper):
            if not isinstance(nodo, ast.Compare):
                continue
            if not nodo.ops:
                continue
            if not isinstance(nodo.ops[0], ast.In):
                continue
            comparator = nodo.comparators[0]
            if (
                isinstance(comparator, ast.Constant)
                and isinstance(comparator.value, str)
                and comparator.value.strip() == "M"
            ):
                self.fail(
                    "El helper busca 'M' suelta para aplicar codigo_git."
                )

    def test_bucle_secciones_aplica_titulo_seccion_sobre_primera_linea(self):
        self.assertIsNotNone(self.metodo_crear)

        for_nodo = None
        for nodo in ast.walk(self.metodo_crear):
            if isinstance(nodo, ast.For):
                for_nodo = nodo
                break

        self.assertIsNotNone(for_nodo, "Falta el bucle de secciones.")
        self.assertIsInstance(for_nodo.iter, ast.Name)
        self.assertEqual(for_nodo.iter.id, "secciones_ayuda")

        claves = []
        if isinstance(for_nodo.iter, ast.Name):
            pass

        tag_add_titulo = False
        usa_end_1c = False
        usa_lineend = False

        for nodo in ast.walk(for_nodo):
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "tag_add"
                and nodo.args
                and isinstance(nodo.args[0], ast.Constant)
                and nodo.args[0].value == "titulo_seccion"
            ):
                tag_add_titulo = True
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "index"
                and nodo.args
                and isinstance(nodo.args[0], ast.Constant)
                and nodo.args[0].value == "end-1c"
            ):
                usa_end_1c = True
            if isinstance(nodo, ast.Constant) and isinstance(
                nodo.value, str
            ) and nodo.value.endswith("lineend"):
                usa_lineend = True

        self.assertTrue(tag_add_titulo, "Falta tag_add('titulo_seccion').")
        self.assertTrue(usa_end_1c, "No usa index('end-1c').")
        self.assertTrue(usa_lineend, "No usa 'lineend'.")

    def test_secciones_ayuda_sigue_con_las_nueve_claves(self):
        self.assertEqual(
            set(principal.CONTENIDO_AYUDA_ESTADOS_GIT_V1.keys()),
            set(CLAVES_ESPERADAS)
        )

    def test_estado_final_sigue_disabled(self):
        self.assertIsNotNone(self.metodo_crear)

        encontrados = []
        for nodo in ast.walk(self.metodo_crear):
            if not (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "configure"
            ):
                continue
            for palabra in nodo.keywords:
                if palabra.arg != "state":
                    continue
                val = None
                if isinstance(palabra.value, ast.Attribute):
                    val = palabra.value.attr
                elif isinstance(palabra.value, ast.Name):
                    val = palabra.value.id
                encontrados.append(val)

        self.assertIn("DISABLED", encontrados)

    def test_grab_set_y_wait_window_ausentes_en_metodos_de_ayuda(self):
        for nombre in METODOS_VENTANA_AYUDA:
            metodo = _metodo(self.arbol, nombre)
            self.assertIsNotNone(metodo)
            self.assertEqual(_llamadas_a("grab_set", metodo), [])
            self.assertEqual(_llamadas_a("wait_window", metodo), [])


if __name__ == "__main__":
    unittest.main()