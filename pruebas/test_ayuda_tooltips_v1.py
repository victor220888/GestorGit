"""
Pruebas de los textos didácticos V1 (Fase 2A P0/P1).

Estas pruebas NO dependen de un display gráfico real ni de mover el
ratón: verifican que el diccionario TEXTOS_AYUDA_GIT_V1 de
principal.py contiene los comandos Git reales y los conceptos
didácticos esperados, y que NO menciona operaciones prohibidas.

La interfaz consume los textos desde ese diccionario mediante
AyudaEmergente, por lo que probar el diccionario equivale a probar
el contenido de los tooltips.
"""

import unittest

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


if __name__ == "__main__":
    unittest.main()
