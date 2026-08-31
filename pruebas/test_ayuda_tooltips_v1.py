"""
Pruebas de los textos didácticos V1 (Fase 2A P0/P1 y Fase 2B P2/P3).

Estas pruebas NO dependen de un display gráfico real ni de mover el
ratón: verifican que el diccionario TEXTOS_AYUDA_GIT_V1 de
principal.py contiene los comandos Git reales y los conceptos
didácticos esperados, y que NO menciona operaciones prohibidas.

La interfaz consume los textos desde ese diccionario mediante
AyudaEmergente, por lo que probar el diccionario equivale a probar
el contenido de los tooltips. Además, unas pruebas con ast verifican
el cableado estático: toda llamada a AyudaEmergente en principal.py
debe consumir una clave del diccionario (sin textos literales
inline) y cada clave debe conectarse exactamente una vez.
"""

import ast
import unittest
from pathlib import Path

import principal


def texto(clave):
    """Devuelve el texto V1 de una clave del diccionario."""

    return principal.TEXTOS_AYUDA_GIT_V1[clave]


# Operaciones que NUNCA deben recomendarse como comando a ejecutar
# en los tooltips V1. Se buscan las formas completas (con 'git ...')
# para permitir mencionar legítimamente que GestorGit NO usa --force
# o --force-with-lease (esas menciones son didácticas y correctas).
OPERACIONES_PROHIBIDAS = (
    "git reset --hard",
    "git clean -fd",
    "git clean -f",
    "git branch -D",
    "git push --force",
    "git push --force-with-lease",
    "git merge",
    "git rebase",
    "git cherry-pick",
    "git checkout -- ",
)


class TestTextosTooltipsV1(unittest.TestCase):
    """Verifica los fragmentos y comandos esperados por tooltip."""

    # --- FETCH -----------------------------------------------------------

    def test_fetch_contiene_comando_real(self):
        t = texto("fetch")
        self.assertIn("git fetch --prune", t)

    def test_fetch_actualiza_refs_remotas(self):
        t = texto("fetch")
        self.assertIn("refs/remotes/", t)
        # Fetch no cambia ÚNICAMENTE refs remotas: también incorpora
        # datos/objetos de los commits obtenidos e información interna.
        self.assertIn("información interna del repositorio local", t)
        self.assertNotIn("Solo refs remotas locales", t)

    def test_fetch_no_cambia_working_tree_ni_head(self):
        t = texto("fetch")
        # En el texto la frase va en mitad de la oración
        # ("...rama local actual: no modifica HEAD...").
        self.assertIn("no modifica HEAD", t)
        self.assertIn("working tree", t)
        # Fetch trae commits al repositorio local pero NO los
        # integra en la rama local actual.
        self.assertIn("No integra esos commits en tu rama local", t)
        self.assertNotIn("no descarga commits a tu rama", t)

    def test_fetch_no_elimina_ramas_locales(self):
        t = texto("fetch")
        self.assertIn("no borra ramas del servidor", t)

    # --- PULL ------------------------------------------------------------

    def test_pull_contiene_comando_real(self):
        t = texto("pull")
        self.assertIn("git pull --ff-only", t)

    def test_pull_puede_actualizar_refs_remotas_locales(self):
        t = texto("pull")
        # El flujo de Pull (fetch interno + avance) puede actualizar
        # las refs LOCALES de seguimiento al obtener información del
        # remoto; Pull no modifica la rama del servidor y no hace Push.
        self.assertIn("refs/remotes/", t)
        self.assertIn("LOCALES", t)
        self.assertIn("no hace Push", t)
        self.assertIn("fast-forward", t)

    def test_pull_no_es_simplemente_fetch(self):
        t = texto("pull")
        self.assertIn("No es 'simplemente un Fetch'", t)

    def test_pull_no_crea_merge_ni_rebase(self):
        t = texto("pull")
        self.assertIn("No crea merge", t)
        self.assertIn("no ejecuta Rebase", t)

    # --- PUSH ------------------------------------------------------------

    def test_push_contiene_comando_real(self):
        t = texto("push")
        self.assertIn("git push --porcelain", t)

    def test_push_explica_set_upstream_y_rama_remota(self):
        t = texto("push")
        # El primer Push no exige siempre un remoto vacío: si la
        # rama remota con el mismo nombre YA EXISTE, GestorGit la
        # actualiza y configura el upstream. Solo cuando NO existe
        # y habría que CREARLA se exige remoto vacío de otras
        # ramas conocidas; si no puede verificarlo, bloquea.
        self.assertIn("--set-upstream", t)
        self.assertIn("primer Push", t)
        self.assertIn("YA EXISTE", t)
        self.assertIn("NO existe", t)
        self.assertIn("CREARLA", t)
        self.assertIn("vacío de otras ramas conocidas", t)
        self.assertNotIn(
            "El primer Push solo se permite si el remoto está vacío",
            t
        )

    def test_push_no_usa_force(self):
        t = texto("push")
        self.assertIn("--force", t)
        self.assertIn("NUNCA", t)
        self.assertIn("--force-with-lease", t)

    def test_push_no_crea_commit_ni_mueve_head_local(self):
        t = texto("push")
        self.assertIn("No crea commits", t)
        self.assertIn("no mueve HEAD local", t)

    # --- PREPARAR --------------------------------------------------------

    def test_preparar_contiene_comando_real(self):
        t = texto("preparar")
        self.assertIn("git --literal-pathspecs add --", t)

    def test_preparar_copia_al_indice_y_no_mueve_cambios(self):
        t = texto("preparar")
        # La formulación correcta es 'registra/copia en el índice la
        # versión actual': el working tree conserva los cambios y no
        # es un movimiento destructivo del working tree al índice.
        self.assertIn("Copia", t)
        self.assertIn("índice", t)
        self.assertIn("staging", t)
        self.assertIn("working tree", t)
        self.assertNotIn("mueve cambios del working tree al índice", t)

    def test_preparar_no_crea_commit_ni_push(self):
        t = texto("preparar")
        self.assertIn("No crea commit", t)
        self.assertIn("no hace Push", t)

    def test_preparar_explica_literal_pathspecs_y_doble_guion(self):
        t = texto("preparar")
        self.assertIn("--literal-pathspecs", t)
        self.assertIn("-- marca", t)

    def test_preparar_prohibe_add_punto_y_add_a(self):
        t = texto("preparar")
        # El texto prohíbe explícitamente 'git add .' y 'git add -A'.
        self.assertIn("git add .", t)
        self.assertIn("git add -A", t)
        self.assertIn("nunca", t)

    # --- ACTUALIZAR PREPARADOS -------------------------------------------

    def test_actualizar_preparados_contiene_comando_real(self):
        t = texto("actualizar_preparados")
        self.assertIn("git --literal-pathspecs add --", t)

    def test_actualizar_preparados_explica_diferencia_con_preparar(self):
        t = texto("actualizar_preparados")
        self.assertIn("preparados y", t)
        self.assertIn("modificados", t)
        self.assertIn("reemplazando", t)

    def test_actualizar_preparados_no_modifica_disco_ni_commit(self):
        t = texto("actualizar_preparados")
        self.assertIn("No modifica el archivo del disco", t)
        self.assertIn("no crea commit", t)

    def test_actualizar_preparados_revalida_estado(self):
        t = texto("actualizar_preparados")
        self.assertIn("revalida", t)

    # --- QUITAR DE PREPARADOS --------------------------------------------

    def test_quitar_contiene_comando_real_principal(self):
        t = texto("quitar_preparados")
        self.assertIn("git --literal-pathspecs restore --staged --", t)

    def test_quitar_contiene_variante_sin_commits(self):
        t = texto("quitar_preparados")
        self.assertIn("git --literal-pathspecs rm --cached --", t)

    def test_quitar_no_elimina_archivo_ni_descarta(self):
        t = texto("quitar_preparados")
        self.assertIn("NO elimina el archivo del disco", t)
        self.assertIn("NO descarta sus modificaciones", t)
        # Diferenciado explícitamente del descarte de working tree.
        self.assertIn("Descartar cambios sin preparar", t)

    def test_quitar_explica_staged_actua_sobre_indice(self):
        t = texto("quitar_preparados")
        self.assertIn("--staged actúa sobre el índice", t)

    # --- CREAR COMMIT ----------------------------------------------------

    def test_commit_contiene_comando_real(self):
        t = texto("commit")
        self.assertIn("git commit -m", t)

    def test_commit_explica_head_avanza(self):
        t = texto("commit")
        self.assertIn("HEAD", t)
        self.assertIn("avanza", t)

    def test_commit_no_dice_staging_se_vacia(self):
        t = texto("commit")
        # El tooltip correcto alinea el índice con el nuevo HEAD;
        # no afirma simplemente que 'el staging se vacía', y el
        # commit usa lo preparado sin incorporar automáticamente
        # los cambios del working tree no preparados.
        self.assertNotIn("staging se vacía", t)
        self.assertNotIn("se vacía", t)
        self.assertIn("alineado", t)
        self.assertIn("no incorpora automáticamente", t)
        self.assertIn("working tree", t)

    def test_commit_no_hace_push(self):
        t = texto("commit")
        self.assertIn("No hace Push", t)

    def test_commit_requiere_identidad(self):
        t = texto("commit")
        self.assertIn("identidad", t)

    # --- DESCARTAR CAMBIOS SIN PREPARAR ----------------------------------

    def test_descartar_contiene_comando_real(self):
        t = texto("descartar_sin_preparar")
        self.assertIn(
            "git --literal-pathspecs restore --worktree --",
            t
        )

    def test_descartar_restaura_desde_indice(self):
        t = texto("descartar_sin_preparar")
        self.assertIn("desde el ÍNDICE", t)
        self.assertIn("no desde HEAD", t)

    def test_descartar_no_usa_staged(self):
        t = texto("descartar_sin_preparar")
        self.assertIn("No usa --staged", t)

    def test_descartar_no_borra_archivos_nuevos(self):
        t = texto("descartar_sin_preparar")
        # La notación ?? es de git status: se explica para quien
        # todavía no conoce Git.
        self.assertIn("No borra archivos nuevos", t)
        self.assertIn("git clean", t)
        self.assertIn("marcados ?? por git status", t)

    def test_descartar_conserva_preparados_caso_mm(self):
        t = texto("descartar_sin_preparar")
        self.assertIn("cambios preparados se CONSERVAN", t)

    def test_descartar_no_hace_push(self):
        t = texto("descartar_sin_preparar")
        self.assertIn("no hace Push", t)

    # --- CAMBIAR RAMA -----------------------------------------------------

    def test_cambiar_rama_contiene_comando_real(self):
        t = texto("cambiar_rama")
        self.assertIn("git switch --no-guess", t)

    def test_cambiar_rama_explica_head(self):
        t = texto("cambiar_rama")
        self.assertIn("HEAD", t)

    def test_cambiar_rama_solo_ramas_locales(self):
        t = texto("cambiar_rama")
        self.assertIn("LOCAL", t)

    def test_cambiar_rama_no_publica_ni_hace_push(self):
        t = texto("cambiar_rama")
        self.assertIn("no hace Push", t)
        self.assertIn("no publica", t)

    def test_cambiar_rama_no_descarta_cambios(self):
        t = texto("cambiar_rama")
        self.assertIn("No descarta cambios", t)

    # --- CREAR RAMA ------------------------------------------------------

    def test_crear_rama_contiene_comando_real(self):
        t = texto("crear_rama")
        self.assertIn("git switch -c", t)

    def test_crear_rama_explica_head_actual(self):
        t = texto("crear_rama")
        self.assertIn("HEAD", t)
        self.assertIn("commit actual", t)

    def test_crear_rama_queda_local_sin_upstream(self):
        t = texto("crear_rama")
        self.assertIn("LOCAL", t)
        self.assertIn("No crea upstream", t)

    def test_crear_rama_no_hace_push_ni_publica(self):
        t = texto("crear_rama")
        self.assertIn("no hace Push", t)
        self.assertIn("no publica", t)

    # --- RAMAS (botón Ramas...) -------------------------------------------

    def test_ramas_contiene_comando_listado(self):
        t = texto("ramas")
        self.assertIn(
            "git for-each-ref --format=%(refname:short) refs/heads/",
            t
        )

    def test_ramas_contiene_symbolic_ref(self):
        t = texto("ramas")
        self.assertIn("git symbolic-ref", t)

    def test_ramas_es_solo_lectura(self):
        t = texto("ramas")
        self.assertIn("solo lectura", t)

    def test_ramas_no_hace_fetch_ni_push(self):
        t = texto("ramas")
        self.assertIn("No hace Fetch", t)
        self.assertIn("no hace Push", t)

    # --- CONFIGURAR GITHUB ------------------------------------------------

    def test_configurar_github_abre_flujo(self):
        t = texto("configurar_github")
        self.assertIn("flujo", t)

    def test_configurar_github_no_recibe_credenciales(self):
        t = texto("configurar_github")
        self.assertIn("credenciales", t)
        self.assertIn("contraseña", t)

    # --- AGREGAR ORIGIN ---------------------------------------------------

    def test_agregar_origin_contiene_comando_real(self):
        t = texto("agregar_origin")
        self.assertIn("git remote add origin", t)

    def test_agregar_origin_no_hace_fetch_ni_push(self):
        t = texto("agregar_origin")
        self.assertIn("No hace Fetch", t)
        self.assertIn("no hace Push", t)

    def test_agregar_origin_solo_modifica_config_local(self):
        t = texto("agregar_origin")
        self.assertIn(".git/config", t)

    def test_agregar_origin_no_modifica_working_tree_ni_head(self):
        t = texto("agregar_origin")
        self.assertIn("no modifica el working tree", t)
        self.assertIn("no modifica HEAD", t)


class TestTooltipsV1SinOperacionesProhibidas(unittest.TestCase):
    """Ningún tooltip V1 debe recomendar operaciones peligrosas."""

    def test_ningun_texto_contiene_operaciones_prohibidas(self):
        for clave, t in principal.TEXTOS_AYUDA_GIT_V1.items():
            for prohibida in OPERACIONES_PROHIBIDAS:
                self.assertNotIn(
                    prohibida,
                    t,
                    msg=(
                        f"El tooltip V1 '{clave}' menciona la "
                        f"operación prohibida '{prohibida}'."
                    )
                )


class TestTooltipsV1Completitud(unittest.TestCase):
    """Garantiza que las 13 claves P0/P1 existen."""

    CLAVES_ESPERADAS = {
        "fetch",
        "pull",
        "push",
        "preparar",
        "actualizar_preparados",
        "quitar_preparados",
        "commit",
        "descartar_sin_preparar",
        "cambiar_rama",
        "crear_rama",
        "ramas",
        "configurar_github",
        "agregar_origin",
    }

    def test_diccionario_tiene_todas_las_claves(self):
        faltantes = self.CLAVES_ESPERADAS - set(
            principal.TEXTOS_AYUDA_GIT_V1.keys()
        )

        self.assertEqual(
            faltantes,
            set(),
            f"Faltan claves V1: {faltantes}"
        )

    def test_ningun_texto_es_vacio(self):
        for clave, t in principal.TEXTOS_AYUDA_GIT_V1.items():
            self.assertIsInstance(t, str)
            self.assertTrue(
                t.strip(),
                f"El texto V1 '{clave}' está vacío."
            )


# =================================================================
# FASE 2B (P2/P3): 24 claves definidas en la tarea.
# =================================================================

CLAVES_2B_ESPERADAS = {
    # Acciones de la ventana principal (antes estaban inline).
    "seleccionar_repositorio",
    "actualizar_estado_local",
    "historial",
    "seleccionar_todo",
    "ver_cambios_locales",
    # Historial y exportaciones (antes estaban inline).
    "historial_filtro_archivo",
    "historial_fecha_desde",
    "historial_fecha_hasta",
    "historial_aplicar_filtros",
    "historial_limpiar_filtros",
    "historial_ver_cambios",
    "exportar_historial_csv",
    "exportar_historial_txt",
    "actualizar_historial",
    # Acciones secundarias nuevas.
    "actualizar_inspector",
    "actualizar_ramas",
    "copiar_diff_inspector",
    "copiar_diff_commit",
    # Conceptos de sincronización.
    "concepto_upstream",
    "concepto_rama_remota",
    "concepto_por_enviar",
    "concepto_por_descargar",
    "concepto_estado_sincronizacion",
    "concepto_ultima_consulta",
}

# Ayuda añadida POSTERIORMENTE al cierre de Tooltips Didácticos V1,
# para la etapa "Publicar rama local". V1 cerró con 37 claves
# (HISTÓRICO: 13 P0/P1 + 24 P2/P3); el total ACTUAL del diccionario
# es 38 por esta ayuda posterior.
CLAVES_PUBLICAR_ESPERADAS = {"publicar_rama"}

# Claves añadidas por el Bloque F (Modo Equipo Oracle V1). Cada
# una está conectada exactamente una vez a un widget real.
CLAVES_MODO_EQUIPO_ESPERADAS = {
    "modo_equipo_oracle",
    "modo_equipo_habilitado",
    "modo_equipo_backend_url",
    "modo_equipo_alias",
    "modo_equipo_guardar",
    "modo_equipo_estado_proyecto",
    "modo_equipo_ruta_objeto",
    "modo_equipo_usar_seleccion",
    "modo_equipo_clave_resuelta",
    "modo_equipo_consultar",
    "modo_equipo_reservar",
    "modo_equipo_renovar",
    "modo_equipo_liberar",
    "modo_equipo_tomar_vencida",
    "modo_equipo_acciones_red",
}

# Total ACTUAL de claves del diccionario:
# 13 (P0/P1) + 24 (P2/P3) + 1 (Publicar rama local)
# + 15 (Bloque F: Modo Equipo Oracle).
CLAVES_TOTALES_ESPERADAS = (
    38 + len(CLAVES_MODO_EQUIPO_ESPERADAS)
)


class TestTooltipsV2BCompletitud(unittest.TestCase):
    """Garantiza que las 24 claves 2B existen y no están vacías."""

    def test_son_exactamente_24_claves_2b(self):
        self.assertEqual(len(CLAVES_2B_ESPERADAS), 24)

    def test_todas_las_claves_2b_existen(self):
        faltantes = CLAVES_2B_ESPERADAS - set(
            principal.TEXTOS_AYUDA_GIT_V1.keys()
        )

        self.assertEqual(
            faltantes,
            set(),
            f"Faltan claves 2B: {faltantes}"
        )

    def test_ningun_texto_2b_es_vacio(self):
        for clave in CLAVES_2B_ESPERADAS:
            t = texto(clave)
            self.assertIsInstance(t, str)
            self.assertTrue(
                t.strip(),
                f"El texto 2B '{clave}' está vacío."
            )

    def test_diccionario_tiene_el_total_esperado_de_claves(self):
        self.assertEqual(
            len(principal.TEXTOS_AYUDA_GIT_V1),
            CLAVES_TOTALES_ESPERADAS
        )


class TestTooltipsV2BSeguridad(unittest.TestCase):
    """Los textos 2B tampoco recomiendan comandos destructivos.

    Se mantiene el criterio de OPERACIONES_PROHIBIDAS (comandos
    peligrosos completos); la prueba global de Fase 2A ya recorre
    TODO el diccionario, incluida la Fase 2B.
    """

    def test_ningun_texto_2b_contiene_operaciones_prohibidas(self):
        for clave in CLAVES_2B_ESPERADAS:
            t = texto(clave)
            for prohibida in OPERACIONES_PROHIBIDAS:
                self.assertNotIn(
                    prohibida,
                    t,
                    msg=(
                        f"El tooltip 2B '{clave}' menciona la "
                        f"operación prohibida '{prohibida}'."
                    )
                )


class TestTooltipsV2BSemanticaActualizar(unittest.TestCase):
    """Los cuatro botones 'Actualizar' enseñan operaciones distintas."""

    def test_actualizar_estado_local_es_consulta_local(self):
        t = texto("actualizar_estado_local")
        self.assertIn("LOCAL", t)

    def test_actualizar_estado_local_no_equivale_a_fetch(self):
        t = texto("actualizar_estado_local")
        self.assertIn("No equivale a Fetch", t)
        self.assertIn("no consulta el remoto", t)
        self.assertIn("no descarga ni sube nada", t)

    def test_actualizar_historial_es_consulta_local(self):
        t = texto("actualizar_historial")
        self.assertIn("LOCAL", t)

    def test_actualizar_historial_no_equivale_a_fetch(self):
        t = texto("actualizar_historial")
        self.assertIn("No equivale a Fetch", t)
        self.assertIn("no consulta el remoto", t)

    def test_actualizar_inspector_es_consulta_local(self):
        t = texto("actualizar_inspector")
        self.assertIn("LOCALES", t)

    def test_actualizar_inspector_no_hace_fetch(self):
        t = texto("actualizar_inspector")
        self.assertIn("No hace Fetch", t)
        self.assertIn("no modifica el archivo", t)
        self.assertIn("ni los commits", t)

    def test_actualizar_ramas_lista_solo_ramas_locales(self):
        t = texto("actualizar_ramas")
        self.assertIn("ramas LOCALES", t)

    def test_actualizar_ramas_no_hace_fetch_ni_cambia_rama(self):
        t = texto("actualizar_ramas")
        self.assertIn("No hace Fetch", t)
        self.assertIn("no verás ramas nuevas del servidor", t)
        self.assertIn("Tampoco cambia de rama", t)

    def test_los_cuatro_actualizar_son_textos_distintos(self):
        textos = {
            texto("actualizar_estado_local"),
            texto("actualizar_historial"),
            texto("actualizar_inspector"),
            texto("actualizar_ramas"),
        }
        self.assertEqual(
            len(textos),
            4,
            "Los tooltips 'Actualizar' comparten un texto genérico."
        )


class TestTooltipsV2BExportaciones(unittest.TestCase):
    """CSV y TXT garantizan que exportar no modifica nada."""

    def test_exportar_csv_escribe_archivo_en_disco(self):
        t = texto("exportar_historial_csv")
        self.assertIn("archivo CSV", t)
        self.assertIn("disco", t)

    def test_exportar_csv_no_modifica_repositorio(self):
        t = texto("exportar_historial_csv")
        self.assertIn("no modifica el repositorio", t)
        self.assertIn("no cambia commits", t)

    def test_exportar_csv_no_consulta_remoto(self):
        self.assertIn(
            "no consulta el remoto",
            texto("exportar_historial_csv")
        )

    def test_exportar_txt_escribe_archivo_en_disco(self):
        t = texto("exportar_historial_txt")
        self.assertIn("archivo de", t)
        self.assertIn("disco", t)

    def test_exportar_txt_no_modifica_repositorio(self):
        t = texto("exportar_historial_txt")
        self.assertIn("no modifica el repositorio", t)
        self.assertIn("no cambia commits", t)

    def test_exportar_txt_no_consulta_remoto(self):
        self.assertIn(
            "no consulta el remoto",
            texto("exportar_historial_txt")
        )


class TestTooltipsV2BCopiarDiff(unittest.TestCase):
    """Copiar diff: portapapeles de solo lectura, sin tocar Git."""

    def test_copiar_diff_inspector_usa_portapapeles(self):
        self.assertIn(
            "portapapeles",
            texto("copiar_diff_inspector")
        )

    def test_copiar_diff_inspector_menciona_pestana_activa(self):
        t = texto("copiar_diff_inspector")
        self.assertIn("VISIBLE", t)
        self.assertIn("pestaña", t)

    def test_copiar_diff_inspector_no_modifica_nada(self):
        t = texto("copiar_diff_inspector")
        self.assertIn("No modifica archivos", t)
        self.assertIn("no prepara ni descarta", t)
        self.assertIn("no modifica Git", t)

    def test_copiar_diff_commit_usa_portapapeles(self):
        self.assertIn(
            "portapapeles",
            texto("copiar_diff_commit")
        )

    def test_copiar_diff_commit_menciona_el_commit(self):
        t = texto("copiar_diff_commit")
        self.assertIn("VISIBLE", t)
        self.assertIn("commit seleccionado", t)

    def test_copiar_diff_commit_no_modifica_repositorio(self):
        t = texto("copiar_diff_commit")
        self.assertIn("No copia ni ejecuta un commit", t)
        self.assertIn("no modifica el", t)
        self.assertIn("ni el historial", t)

    def test_copiar_diff_inspector_y_commit_son_textos_distintos(self):
        self.assertNotEqual(
            texto("copiar_diff_inspector"),
            texto("copiar_diff_commit")
        )


class TestTooltipsV2BSincronizacion(unittest.TestCase):
    """Conceptos remotos: commits conocidos, nunca archivos ni en vivo."""

    def test_por_enviar_cuenta_commits_no_archivos(self):
        self.assertIn(
            "COMMITS, no archivos",
            texto("concepto_por_enviar")
        )

    def test_por_enviar_depende_de_informacion_remota_conocida(self):
        t = texto("concepto_por_enviar")
        self.assertIn("CONOCIDA", t)
        self.assertIn("un Fetch reciente actualiza esa referencia", t)

    def test_por_enviar_no_afirma_que_se_haya_hecho_push(self):
        self.assertIn(
            "No significa que se haya hecho Push",
            texto("concepto_por_enviar")
        )

    def test_por_descargar_cuenta_commits_no_archivos(self):
        self.assertIn(
            "COMMITS, no archivos",
            texto("concepto_por_descargar")
        )

    def test_por_descargar_depende_de_la_consulta_del_remoto(self):
        self.assertIn(
            "tras consultar el remoto (Fetch)",
            texto("concepto_por_descargar")
        )

    def test_por_descargar_no_afirma_pull_integrado(self):
        self.assertIn(
            "No significa que esos commits ya estén integrados con Pull",
            texto("concepto_por_descargar")
        )

    def test_upstream_no_afirma_estar_sincronizado(self):
        t = texto("concepto_upstream")
        self.assertIn(
            "tener upstream no significa estar sincronizado ahora mismo",
            t
        )

    def test_estado_sincronizacion_no_es_monitorizacion_tiempo_real(self):
        t = texto("concepto_estado_sincronizacion")
        self.assertIn("No es monitorización en tiempo real", t)
        self.assertIn("CONOCIDA", t)
        self.assertIn("última consulta", t)

    def test_ultima_consulta_no_vigila_continuamente(self):
        t = texto("concepto_ultima_consulta")
        self.assertIn("no vigila continuamente el servidor", t)

    def test_ultima_consulta_operacion_fallida_no_actualiza(self):
        self.assertIn(
            "Una operación fallida no significa que la información "
            "remota se haya actualizado",
            texto("concepto_ultima_consulta")
        )

    def test_ningun_concepto_afirma_estado_remoto_continuo(self):
        claves_conceptos_sincronizacion = {
            "concepto_upstream",
            "concepto_rama_remota",
            "concepto_por_enviar",
            "concepto_por_descargar",
            "concepto_estado_sincronizacion",
            "concepto_ultima_consulta",
        }
        frases_afirmativas_prohibidas = (
            "siempre actualizado",
            "en todo momento",
            "estado actual del servidor",
        )
        for clave in claves_conceptos_sincronizacion:
            t = texto(clave).lower()
            for frase in frases_afirmativas_prohibidas:
                self.assertNotIn(
                    frase,
                    t,
                    msg=(
                        f"El concepto '{clave}' afirma que Git "
                        f"conoce continuamente el remoto: '{frase}'."
                    )
                )


class TestTooltipsV2BFiltros(unittest.TestCase):
    """Los filtros del historial son consultas LOCALES."""

    def test_filtro_archivo_es_consulta_local(self):
        t = texto("historial_filtro_archivo")
        self.assertIn("git log LOCAL", t)
        self.assertIn("no consulta el remoto", t)

    def test_aplicar_filtros_es_consulta_local(self):
        t = texto("historial_aplicar_filtros")
        self.assertIn("LOCAL", t)
        self.assertIn("No consulta el remoto", t)

    def test_limpiar_filtros_no_cambia_commits(self):
        t = texto("historial_limpiar_filtros")
        self.assertIn("historial LOCAL", t)
        self.assertIn("No cambia commits", t)

    def test_fecha_desde_y_hasta_se_refieren_a_fecha_del_commit(self):
        for clave in ("historial_fecha_desde", "historial_fecha_hasta"):
            self.assertIn(
                "FECHA DEL COMMIT",
                texto(clave),
                f"La clave '{clave}' no aclara la fecha del commit."
            )


def obtener_claves_2b_usadas_en_llamadas_ayuda():
    """
    Analiza con ast las llamadas a AyudaEmergente de principal.py.

    Devuelve la lista de tuplas (linea, clave_1b_arg) donde clave es la
    clave TEXTOS_AYUDA_GIT_V1 usada como segundo argumento posicional;
    si el argumento no es un subscript del diccionario, clave es None.
    No depende de números de línea fijos: recorre el árbol sintáctico.
    """

    ruta = Path(principal.__file__).resolve()
    arbol = ast.parse(
        ruta.read_text(encoding="utf-8"),
        filename=str(ruta)
    )

    resultados = []

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue

        if not (
            isinstance(nodo.func, ast.Name)
            and nodo.func.id == "AyudaEmergente"
        ):
            continue

        if len(nodo.args) < 2:
            resultados.append((nodo.lineno, None))
            continue

        argumento_texto = nodo.args[1]

        clave = None

        if (
            isinstance(argumento_texto, ast.Subscript)
            and isinstance(argumento_texto.value, ast.Name)
            and argumento_texto.value.id == "TEXTOS_AYUDA_GIT_V1"
            and isinstance(argumento_texto.slice, ast.Constant)
            and isinstance(argumento_texto.slice.value, str)
        ):
            clave = argumento_texto.slice.value

        resultados.append((nodo.lineno, clave))

    return resultados


class TestTooltipsV2BCableadoEstatico(unittest.TestCase):
    """Cableado con ast: sin textos inline y claves conectadas una vez."""

    @classmethod
    def setUpClass(cls):
        cls.llamadas = obtener_claves_2b_usadas_en_llamadas_ayuda()

    def test_ninguna_llamada_usa_texto_literal_inline(self):
        sin_clave = [
            (linea, clave)
            for linea, clave in self.llamadas
            if clave is None
        ]

        self.assertEqual(
            sin_clave,
            [],
            (
                "Hay llamadas a AyudaEmergente sin diccionario "
                f"(líneas {sin_clave}): quedan textos inline."
            )
        )

    def test_cantidad_de_llamadas_igual_a_claves_del_diccionario(self):
        self.assertEqual(
            len(self.llamadas),
            len(principal.TEXTOS_AYUDA_GIT_V1),
            (
                "El número de llamadas a AyudaEmergente debe coincidir "
                "con el número de claves del diccionario."
            )
        )

    def test_cada_clave_2b_esta_conectada_exactamente_una_vez(self):
        claves_uso = [
            clave
            for _, clave in self.llamadas
        ]

        for clave in CLAVES_2B_ESPERADAS:
            repeticiones = claves_uso.count(clave)
            self.assertEqual(
                repeticiones,
                1,
                (
                    f"La clave 2B '{clave}' está conectada "
                    f"{repeticiones} veces (debe ser 1)."
                )
            )

    def test_claves_usadas_biyectivas_con_el_diccionario(self):
        claves_usadas = {
            clave
            for _, clave in self.llamadas
        }

        self.assertEqual(
            claves_usadas,
            set(principal.TEXTOS_AYUDA_GIT_V1.keys()),
            "Las claves usadas en llamadas y el diccionario no coinciden."
        )


class TestTooltipsPublicarRama(unittest.TestCase):
    """Ayuda contextual de 'Publicar rama local...' (posterior a V1).

    V1 cerró con 37 claves; esta ayuda fue añadida después para la
    etapa Publicar rama local y debe cumplir las mismas reglas:
    comando real, sin operaciones prohibidas y sin texto inline.
    """

    def test_son_exactamente_1_clave_publicar(self):
        self.assertEqual(len(CLAVES_PUBLICAR_ESPERADAS), 1)

    def test_la_clave_publicar_existe_y_no_esta_vacia(self):
        self.assertIn(
            "publicar_rama",
            principal.TEXTOS_AYUDA_GIT_V1
        )

        self.assertTrue(texto("publicar_rama").strip())

    def test_el_total_es_la_suma_historica_mas_las_claves_nuevas(self):
        self.assertEqual(
            CLAVES_TOTALES_ESPERADAS,
            13 + len(CLAVES_2B_ESPERADAS)
            + len(CLAVES_PUBLICAR_ESPERADAS)
            + len(CLAVES_MODO_EQUIPO_ESPERADAS)
        )

    def test_explica_el_comando_real_con_set_upstream(self):
        t = texto("publicar_rama")

        self.assertIn("git push --porcelain", t)
        self.assertIn("--set-upstream", t)
        self.assertIn("refs/heads/", t)

    def test_explica_la_consulta_previa_con_ls_remote(self):
        t = texto("publicar_rama")

        self.assertIn("ls-remote", t)
        self.assertIn("--heads", t)

    def test_explica_upstream_y_publicacion(self):
        t = texto("publicar_rama")

        self.assertIn("upstream", t.lower())
        self.assertIn("vinculada", t)

    def test_no_recomienda_operaciones_prohibidas(self):
        t = texto("publicar_rama")

        for prohibida in OPERACIONES_PROHIBIDAS:
            self.assertNotIn(
                prohibida,
                t,
                msg=(
                    "El tooltip 'publicar_rama' menciona la "
                    f"operación prohibida '{prohibida}'."
                )
            )

    def test_explica_bloqueo_si_la_rama_ya_existe_o_tiene_upstream(self):
        t = texto("publicar_rama")

        self.assertIn("ya existe", t)
        self.assertIn("ya tiene", t)

    def test_explica_que_no_exige_commits_exclusivos(self):
        self.assertIn(
            "no tenga commits exclusivos",
            texto("publicar_rama")
        )

    def test_explica_refspec_de_destino_unico(self):
        t = texto("publicar_rama")

        self.assertIn("apunta únicamente", t)
        self.assertIn("refs/heads/", t)

    def test_enumera_las_opciones_que_no_se_usan(self):
        t = texto("publicar_rama")

        for opcion in (
            "--all",
            "--tags",
            "--mirror",
            "--delete",
            "--force",
            "--force-with-lease"
        ):
            self.assertIn(
                opcion,
                t,
                f"El tooltip debe enseñar que no usa {opcion}."
            )

    def test_no_promete_absolutamente_sobre_otras_refs_remotas(self):
        """GG-PROMPT-004: sin garantía absoluta de efectos externos
        del servidor; solo la garantía precisa del comando enviado."""

        t = texto("publicar_rama")

        self.assertNotIn("no modifica otras ramas", t)
        self.assertNotIn("otras referencias del remoto", t)


class TestTooltipsPublicarRamaCableado(unittest.TestCase):
    """Cableado estático de la clave añadida para Publicar rama."""

    @classmethod
    def setUpClass(cls):
        cls.llamadas = obtener_claves_2b_usadas_en_llamadas_ayuda()

    def test_la_clave_publicar_esta_conectada_exactamente_una_vez(self):
        claves_uso = [
            clave
            for _, clave in self.llamadas
        ]

        self.assertEqual(
            claves_uso.count("publicar_rama"),
            1,
            "La clave 'publicar_rama' debe conectarse exactamente "
            "una vez en una llamada a AyudaEmergente."
        )

    def test_el_total_de_llamadas_cubre_las_claves(self):
        self.assertEqual(
            len(self.llamadas),
            CLAVES_TOTALES_ESPERADAS
        )

    def test_las_38_claves_historicas_siguen_presentes(self):
        # GG-PROMPT-042: las 38 ayudas históricas (13 P0/P1 + 24
        # P2/P3 + publicar_rama) se preservan íntegras; las nuevas
        # del Bloque F se suman sin sustituirlas.
        claves_actuales = set(principal.TEXTOS_AYUDA_GIT_V1.keys())

        self.assertEqual(
            len(claves_actuales - CLAVES_MODO_EQUIPO_ESPERADAS),
            38,
        )
        self.assertTrue(
            CLAVES_MODO_EQUIPO_ESPERADAS <= claves_actuales
        )

    def test_cada_clave_esta_conectada_exactamente_una_vez(self):
        claves_uso = [clave for _, clave in self.llamadas]

        self.assertEqual(len(claves_uso), len(set(claves_uso)))

        self.assertEqual(
            set(claves_uso),
            set(principal.TEXTOS_AYUDA_GIT_V1.keys()),
        )

    def test_las_claves_modo_equipo_estan_conectadas(self):
        claves_uso = [clave for _, clave in self.llamadas]

        for clave in CLAVES_MODO_EQUIPO_ESPERADAS:
            self.assertEqual(
                claves_uso.count(clave),
                1,
                f"La clave '{clave}' debe conectarse una sola vez.",
            )


class TestTooltipsV11Corregidos(unittest.TestCase):
    """
    GG-PROMPT-053-REV1: regresiones de los dos tooltips reparados.
    No cambia el número de claves: la REV corrige contenido.
    """

    def test_ruta_objeto_contiene_ejemplo_sql(self):
        t = texto("modo_equipo_ruta_objeto")
        self.assertIn("Procedimientos/PR_CERRAR.sql", t)

    def test_ruta_objeto_contiene_clave_procedure(self):
        t = texto("modo_equipo_ruta_objeto")
        self.assertIn("PROCEDURE|...", t)

    def test_ruta_objeto_conserva_frase_final(self):
        t = texto("modo_equipo_ruta_objeto")
        self.assertIn("puede escribir la ruta relativa conocida", t)

    def test_ruta_objeto_no_duplica_servicio(self):
        t = texto("modo_equipo_ruta_objeto")
        self.assertEqual(t.count("ServicioObjetosOracle"), 1)

    def test_ruta_objeto_no_truncado(self):
        t = texto("modo_equipo_ruta_objeto")
        self.assertTrue(t.rstrip().endswith("conocida."))

    def test_clave_resuelta_contiene_procedure(self):
        t = texto("modo_equipo_clave_resuelta")
        self.assertIn("PROCEDURE|PR_CERRAR", t)

    def test_clave_resuelta_conserva_frase_seguridad(self):
        t = texto("modo_equipo_clave_resuelta")
        self.assertIn(
            "Si la ruta no es un objeto Oracle resoluble de forma segura",
            t,
        )

    def test_clave_resuelta_no_duplica_frase(self):
        t = texto("modo_equipo_clave_resuelta")
        self.assertEqual(t.count("de la ruta indicada"), 1)

    def test_numero_de_claves_sigue_siendo_53(self):
        self.assertEqual(
            len(principal.TEXTOS_AYUDA_GIT_V1),
            CLAVES_TOTALES_ESPERADAS,
        )


if __name__ == "__main__":
    unittest.main()
