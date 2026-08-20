# TRABAJO_ACTUAL.md

## Propósito

Este archivo coordina el trabajo en paralelo entre agentes.

Todo agente debe leerlo ANTES de modificar código.

No sustituye AGENTS.md ni CLAUDE.md.

## Estado del repositorio

HEAD observado al iniciar la etapa de las ramas:

3309be7 Agrega descarte seguro de cambios sin preparar

El HEAD actual debe consultarse siempre con:

git log -1 --oneline

Al iniciar la etapa de las ramas: working tree limpio,
master sincronizado con origin/master.

Históricos:

- c62b0a0 Agrega inspector de cambios locales;
- 014e3f7 Agrega persistencia y actualizacion segura de preparados
  (persistencia + actualización de preparados: commiteadas y con Push);
- 0e3840e Agrega visor de cambios de commits;
- fe5e49e Agrega historial con filtros y exportacion
  (línea base funcional validada; 65 pruebas OK en su momento).

Estado actual:

- etapa ramas locales: ETAPA VALIDADA - PRUEBA MANUAL EN
  WINDOWS EXITOSA (confirmada por el usuario);
- etapa descarte de cambios sin preparar: ETAPA VALIDADA -
  PRUEBA MANUAL EXITOSA en Windows (confirmada por el usuario);
- inspector de cambios locales: ETAPA VALIDADA MANUALMENTE
  (prueba manual EXITOSA confirmada por el usuario);
- corrección del error silencioso de git diff --numstat:
  commiteada en 634a295;
- 151 pruebas OK (123 + 28 de las ramas locales): dato
  HISTÓRICO del estado HASTA Ramas Locales V1, no el total
  actual del proyecto;
- Tooltips Didácticos V1 — Fase 2A: CERRADA;
- 13 tooltips P0/P1 validados;
- 58/58 pruebas específicas OK;
- 209/209 suite completa OK;
- revisión visual Windows final: EXITOSA;
- commits locales bc57772 y 82a32d1 (hijo del primero);
- SIN PUSH;
- Fase 2B: NO iniciada;
- config.json ignorado y no versionado;
- .opencode/ sigue sin versionar y NO debe incluirse
  automáticamente.

## Funcionalidades estables

- estado del repositorio;
- staging;
- commit local;
- Fetch;
- Push seguro;
- Pull exclusivamente --ff-only;
- tooltips y ayudas visuales;
- historial de commits;
- filtro por archivo;
- filtro Desde/Hasta;
- orden explícito por fecha descendente;
- cabecera Fecha ↓;
- exportación CSV;
- exportación TXT;
- configuración inicial de GitHub (primer remoto origin);
- primer Push seguro: si la rama remota ya existe puede configurar
  upstream; si hay que crearla, solo se permite con remoto vacío
  de otras ramas conocidas;
- detalle de cambios de un commit (solo lectura);
- persistencia del último repositorio (config.json);
- actualización de archivos preparados;
- inspector de cambios locales (solo lectura + descarte de
  cambios sin preparar).

## Histórico — cierre de la etapa de ramas locales

Estado: ETAPA VALIDADA - PRUEBA AUTOMATIZADA OK
(151 tests) - PRUEBA MANUAL EN WINDOWS EXITOSA -
COMMITEADA LOCALMENTE EN HEAD "Agrega selector seguro
de ramas locales" - SIN PUSH
(hash vigente: consultar git log -1 --oneline)

Agente: OpenCode
Tarea: Selector y creación segura de ramas locales (V1)
HEAD observado al iniciar la etapa: 3309be7 Agrega descarte
seguro de cambios sin preparar; working tree limpio;
master == origin/master; índice limpio confirmado con
git diff --cached --name-only sin salida.
Etapa terminada sin tocar: servicio_git.py, servicio_remoto_git.py,
servicio_descarte_cambios_git.py, modelos_cambios_locales.py,
servicio_cambios_locales_git.py.
NO se ejecutó sobre el repositorio real:
git add / git commit / git fetch / git pull / git push /
git reset / git restore / git checkout / git clean.
Los tests sí usaron Git (incluido git checkout --detach e init
--bare) dentro de carpetas temporales.

Etapa anterior del descarte (commiteada en 3309be7):

Estado (histórico): TAREA TERMINADA - COMMITEADA en 3309be7

Agente: OpenCode
Tarea: Cierre técnico "Descartar cambios sin preparar" -
  prueba manual EXITOSA + en_conflicto estructurado + defensa
  durante operación remota + correcciones documentales
HEAD observado al iniciar la etapa: 634a295 Corrige manejo de
errores del inspector (working tree con los cambios del descarte;
master == origin/master; ÍNDICE LIMPIO confirmado con
git diff --cached --name-only sin salida)

NO se ejecutó sobre el repositorio real:

git add / git reset / git restore / git checkout / git clean /
git commit / git fetch / git pull / git push

Los tests sí usaron git restore dentro de repositorios temporales.

Trabajo realizado:

- NUEVO servicio_descarte_cambios_git.py:
  ServicioDescarteCambiosGit.descartar_cambios_sin_preparar()
  ejecuta exactamente:
  [--literal-pathspecs, restore, --worktree, --, ruta]
  (restaura desde el ÍNDICE, no desde HEAD; sin --source);
  validación propia de ruta (None, vacía, espacios, NUL antes de
  Path, absoluta, ..); revalidación del estado justo antes del
  restore; ?? y conflictos bloqueados con mensajes educativos;
  regla por estado_indice/estado_trabajo; ResultadoComando;
  servicio_git.py NO se modificó (git diff vacío confirmado);
- NUEVO pruebas/test_descarte_cambios_git.py: 17 pruebas;
- principal.py: import + self.servicio_descarte_cambios
  (reutiliza self.servicio_git); atributo boton_descartar_sin_preparar;
  botón "Descartar cambios sin preparar..." en la ventana del
  Inspector (columna 0, junto a Actualizar/Copiar diff/Cerrar);
  tooltip educativo; habilitación solo en pestaña "Sin preparar"
  con cambios sin preparar reales (no ??, no conflicto);
  <<NotebookTabChanged>> reevalúa el botón; texto de advertencia
  de la ventana actualizado; al pulsar: consulta LOCAL fresca,
  confirmación fuerte (ruta literal, staging conservado),
  descarte, refresco de tabla principal + Inspector, mensaje de
  éxito, sin Fetch, sin cerrar la ventana;
- documentación: AGENTS.md (sección descarte + 122 pruebas),
  CLAUDE.md (sección completa + desglose 122), este documento.

REVISIÓN FINAL ANTES DE LA PRUEBA MANUAL (tarea posterior):

- corregido el estado inicial del botón: se crea con
  state=tk.DISABLED y se recalcula al final de
  crear_ventana_cambios_locales() con
  actualizar_estado_boton_descartar() (la primera llamada a
  actualizar_cambios_locales() ocurría antes de crear el botón y
  no tenía efecto); desde el primer frame: " M"/MM en "Sin
  preparar" habilitado, ?? / "M " / conflicto / pestaña
  "Preparados" deshabilitado;
- tooltip de "Ver cambios locales..." reescrito (consulta y
  visores de solo lectura; el descarte es acción separada con
  confirmación); docstring de crear_ventana_cambios_locales()
  cambiado a "ventana de inspección";
- documentación corregida: AGENTS.md/CLAUDE.md aclaran que las
  CONSULTAS/visores del Inspector son solo lectura y que el
  descarte es una acción destructiva separada; eliminada la
  referencia obsoleta "origin/master apunta a c62b0a0" / "los
  cambios de --numstat viven en el working tree" (ya commiteados
  en 634a295 con Push; c62b0a0 queda como histórico; los únicos
  cambios en el working tree son los del descarte);
- NUEVA prueba test_descarte_archivo_nuevo_preparado_y_modificado_am_conserva_staging
  (caso AM con Git real: restaura desde el ÍNDICE porque no hay
  versión en HEAD; comprueba diff --cached idéntico antes/después
  y el archivo sigue preparado como agregado "A ").

CIERRE TÉCNICO DESPUÉS DE LA PRUEBA MANUAL (tarea actual):

PRUEBA MANUAL EN WINDOWS: EXITOSA (confirmada por el usuario
después de retirar todos los archivos/líneas temporales;
git diff -- servicio_git.py final SIN salida).

Casos confirmados por el usuario:

- caso A (archivo modificado sin preparar): diff visible,
  Preparado = No, botón habilitado en "Sin preparar" y
  deshabilitado en "Preparados", confirmación explícita,
  descarte correcto, archivo vuelve a HEAD;
- caso B (MM): A preparada y B agregada después; estado
  "Modificado, preparado y vuelto a modificar"; Preparado =
  "Sí (hay cambios nuevos)"; Preparados muestra A y Sin
  preparar muestra B; el descarte elimina B, A permanece
  preparada, git diff vuelve a quedar vacío y
  git diff --cached conserva A; después: quitar de preparados
  conserva A en el working tree, un segundo descarte elimina A
  y servicio_git.py vuelve exactamente a HEAD;
- caso C (archivo nuevo ??): estado Nuevo, Preparado No,
  mensaje educativo, botón deshabilitado desde el primer momento
  (también en "Preparados"); Test-Path confirmó True: GestorGit
  no eliminó el archivo;
- caso D (solamente preparado): Sin preparar vacío y botón
  deshabilitado;
- caso E (actualización visual): el Inspector refresca
  correctamente y muestra "El archivo ya no tiene cambios
  locales pendientes." cuando ya no quedan cambios;
- caso F (Fetch simultáneo): NO APLICABLE desde la GUI actual
  (con el Inspector abierto no fue posible interactuar con
  Fetch); documentado como limitación y cubierto por defensa
  en profundidad, no como fallo ni prueba exitosa.

Trabajo realizado en el cierre:

- modelos_cambios_locales.py: NUEVO campo estructurado
  DetalleCambioLocal.en_conflicto (bool, default False);
- servicio_cambios_locales_git.py: helper privado propio
  _calcular_en_conflicto(estado_indice, estado_trabajo) con los
  códigos DD/AU/UD/UA/DU/AA/UU (sin acoplarse a métodos privados
  de ServicioGit); el detalle lo calcula al construirse;
- principal.py: eliminadas TODAS las comparaciones de seguridad
  contra descripcion == "Conflicto" -> ahora detalle.en_conflicto
  en actualizar_estado_boton_descartar() y en
  descartar_cambios_sin_preparar();
- principal.py: defensa en profundidad durante operación remota:
  descartar_cambios_sin_preparar() se bloquea al principio si
  operacion_remota_en_curso (mensaje controlado, sin consulta ni
  confirmación, sin llamar al servicio);
  actualizar_controles_operacion_remota() recalcula también
  actualizar_estado_boton_descartar() de forma segura (el botón
  tolera que el Inspector no exista);
- prueba NUEVA test_conflicto_se_expone_de_forma_estructurada en
  pruebas/test_cambios_locales_git.py (spy controlado UU con
  descripcion que no dice "Conflicto": en_conflicto == True,
  demostrando que el booleano procede de los códigos Git);
- pruebas/test_descarte_cambios_git.py: docstring actualizado
  (agrega AM a la lista de casos);
- CLAUDE.md: corregido el bloque HISTÓRICO que decía 122 ->
  "Ran 79 tests in ... OK" (49 + 11 + 5 + 7 + 1 + 6 = 79);
- sin cambios en servicio_git.py ni servicio_descarte_cambios_git.py.

Resultados:

- 123 pruebas OK en la suite completa (122 anteriores + 1 del
  conflicto estructurado); pruebas del descarte: 17 OK;
  inspector: 12 OK;
- py_compile de TODOS los módulos OK;
- git diff --check: SIN avisos;
- git diff --cached --check: sin avisos (nada preparado);
- git status --short final:
  M AGENTS.md;
  M CLAUDE.md;
  M TRABAJO_ACTUAL.md;
  M modelos_cambios_locales.py;
  M principal.py;
  M pruebas/test_cambios_locales_git.py;
  M servicio_cambios_locales_git.py;
  ?? pruebas/test_descarte_cambios_git.py (nuevo);
  ?? servicio_descarte_cambios_git.py (nuevo);
  (estado observado antes del commit; no es un HEAD futuro);
- git diff -- servicio_git.py: VACÍO (sin cambios);
- config.json intacto;
- no se ejecutó add/commit/fetch/pull/push.

PRUEBA MANUAL EN WINDOWS: EXITOSA (confirmada por el usuario;
todos los archivos/líneas temporales fueron retirados y
git diff -- servicio_git.py quedó SIN salida).

La historia completa de la prueba manual (casos A-F con su
procedimiento y resultados) quedó registrada en la sección
"CIERRE TÉCNICO DESPUÉS DE LA PRUEBA MANUAL".

Tarea NUEVA: ninguna pendiente dentro de esta etapa.

## ETAPA RAMAS LOCALES (selector y creación segura, V1)

Trabajo realizado:

- NUEVO modelos_ramas.py: RamaLocal(nombre, actual) y
  ResultadoRamas(exitoso, ramas, error, mensaje) con
  field(default_factory=list) en ramas;
- NUEVO servicio_ramas_git.py (ServicioRamasGit reutiliza la
  instancia existente de ServicioGit/ServicioRemotoGit):
  - listar SOLO refs locales:
    git for-each-ref --format=%(refname:short) refs/heads/
    (rama actual primero, resto alfabético);
  - rama actual consulta propia y estructurada:
    git symbolic-ref --quiet --short HEAD (vacía en detached;
    listar sigue válido, cambiar/crear bloquean);
  - validar nombre: reglas propias (None, vacío, solo espacios,
    espacios iniciales/finales, NUL, inicio -, HEAD, @, @{...})
    + git check-ref-format refs/heads/<nombre>; sin corregir
    silenciosamente;
  - cambiar: git switch --no-guess <rama> (existencia local
    previa con rev-parse --verify --quiet refs/heads/<rama>);
  - crear: git switch -c <rama> (desde HEAD actual, sin
    start-point); mensaje: "La rama se creó solamente en el
    repositorio local. Todavía no se publicó en el remoto.";
  - precondiciones revalidadas siempre: repo válido, tiene
    commits, HEAD no separado, sin operación Git en curso
    (detectar_operacion_en_curso), sin index.lock (chequeo
    propio con rev-parse --git-dir; nunca se borra), working
    tree/staging/nuevos ?? TOTALMENTE limpios (obtener_cambios
    con exitoso=True; un error de consulta BLOQUEA y nunca se
    interpreta como limpio), sin conflictos (helper propio
    DD/AU/UD/UA/DU/AA/UU); nunca se descartan cambios;
  - sin changes en servicio_git.py ni subprocess duplicado;
- NUEVO pruebas/test_ramas_git.py: 25 pruebas OK (Git real en
  TemporaryDirectory + spy ServicioGitEspiaRamas): listado con
  actual, varias ramas, switch y working tree, creación desde
  HEAD sin mover el commit origen, rechazos (ya existe, no
  existe, M, staged, ??, sin commits, detached, index.lock,
  MERGE_HEAD, repo no válido), nombres inválidos (10) y válidos
  (3), NUL sin ejecutar switch, argumentos exactos
  (["switch", "--no-guess", x] y ["switch", "-c", x]), verbos
  prohibidos ausentes, error de obtener_cambios bloquea, error
  de switch expuesto, remotos intactos con bare local;
- principal.py: import + self.servicio_ramas (reutiliza
  self.servicio_git); botón "Ramas..." en Información local
  (columna 7, junto a Historial...; se deshabilita durante
  operaciones remotas y sin repositorio); ventana única
  "Ramas locales - Gestor Git" (transient, se destruye y recrea,
  se cierra al cambiar de repositorio y en limpiar_repositorio):
  texto educativo, rama actual, tabla de ramas con "(actual)",
  entrada "Nueva rama", botones Cambiar a seleccionada / Crear
  rama / Actualizar / Cerrar; sin Eliminar/Renombrar/Merge/
  Rebase/Publicar/Push; guard en confirmaciones si
  operacion_remota_en_curso (mensaje controlado); durante
  Fetch/Pull/Push los botones de la ventana se deshabilitan
  (actualizar_estado_botones_ventana_ramas, segura sin ventana);
  confirmaciones que NO afirman limpieza absoluta ("...continúa
  limpio; el servicio volverá a comprobarlo antes de ejecutar
  git switch"); tras cambiar o crear: cerrar historial, detalle
  e Inspector, cargar_repositorio(reiniciar_fetch=True) y
  refresco de la lista; nunca Fetch automático;
- Push intacto: la rama nueva queda LOCAL sin upstream; la
  protección del primer Push no cambia; "Publicar rama" será una
  etapa posterior con sus propias confirmaciones.

MICROCORRECCIÓN ANTES DE LA PRUEBA MANUAL (histórico, aplicada):

- ResultadoRamas nuevo campo estructurado: tiene_commits
  (default True) y head_separado (default False);
- obtener_ramas_locales() distingue: con commits y symbolic-ref
  fallida -> head_separado=True (mensaje detached); sin commits
  -> tiene_commits=False y head_separado=False (mensaje
  "Repositorio sin commits todavía..."); nunca se infiere
  detached de una lista de ramas vacía o sin rama actual;
- GUI (cargar_lista_ramas): "Repositorio sin commits todavía"
  frente a "HEAD separado (no se encuentra en ninguna rama)";
  fallback "No determinada";
- NUEVA prueba test_repositorio_sin_commits_no_se_marca_como_
  head_separado (resultado exitoso, ramas vacías,
  tiene_commits False, head_separado False); la prueba del
  verdadero checkout --detach ahora también comprueba
  tiene_commits True y head_separado True;
- sin cambios en servicio_git.py; sin Fetch; sin commits
  automáticos; prueba manual sigue PENDIENTE.

CIERRE TÉCNICO ANTES DE LA PRUEBA MANUAL (tarea actual):

- SEGUNDA revalidación de precondiciones: cambiar_rama() y
  crear_rama() conservan la primera _validar_precondiciones()
  y ejecutan OTRA _validar_precondiciones(ruta_repositorio)
  INMEDIATAMENTE antes del ejecutar_git() productivo que
  contiene "switch" (tras todas las demás comprobaciones de
  existencia/rama actual); si falla, devuelven
  ResultadoRamas(exitoso=False, error=...) sin ejecutar el
  switch; sin sleeps ni locks artificiales (defensa TOCTOU);
- spy: ServicioGitEspiaRamas acepta secuencia_cambios (tuplas
  (exitoso, cambios) consumidas una por llamada a
  obtener_cambios) y cuenta llamadas_obtener_cambios; el spy
  se adaptó al servicio, no al revés;
- DOS NUEVAS pruebas: test_cambiar_rama_revalida_limpieza_
  justo_antes_del_switch y test_crear_rama_revalida_limpieza_
  justo_antes_del_switch: primera consulta limpia, segunda con
  cambio (tracked M en una, ?? en la otra), exitoso=False con
  "no está limpio", obtener_cambios llamado >= 2 veces y
  ningún switch ejecutado;
- principal.py: docstring de crear_ventana_ramas corregido
  ("Crea la ventana de ramas locales."); la ventana es NO
  MODAL (Toplevel + transient sin grab_set ni wait_window) y
  así queda documentado;
- documentación: AGENTS.md (ventana no modal + doble
  revalidación), CLAUDE.md (funcionalidad en la lista de
  principal.py, "si Empieza" -> "si empieza", ventana no modal,
  doble revalidación en precondiciones, spy con secuencias) y
  este documento; encabezado corregido: "HEAD observado al
  iniciar la etapa de las ramas:";

Validación:

- pruebas de ramas: Ran 28 tests OK (26 + 2 TOCTOU);
- suite completa: Ran 151 tests OK (123 + 28 de las ramas);
- py_compile modelos_ramas.py, servicio_ramas_git.py,
  principal.py y pruebas/test_ramas_git.py: OK;
- git diff --check: SIN avisos;
- git diff --cached --check: sin avisos (nada preparado);
- git diff --cached --name-only: sin salida (índice limpio);
- git status --short final:
  M AGENTS.md;
  M CLAUDE.md;
  M TRABAJO_ACTUAL.md;
  M principal.py;
  ?? modelos_ramas.py (nuevo);
  ?? servicio_ramas_git.py (nuevo);
  ?? pruebas/test_ramas_git.py (nuevo);
  (estado observado antes del commit; no es un HEAD futuro);
- git diff -- servicio_git.py: VACÍO (sin cambios);
- config.json intacto;
- no se ejecutó add/commit/fetch/pull/push.

PRUEBA MANUAL EN WINDOWS: EXITOSA (confirmada por el usuario).
Prueba ejecutada en repositorio temporal
`C:\Users\victo\AppData\Local\Temp\GestorGit-Prueba-Ramas-20260819-151113`
con rama `prueba-manual-ramas-victor`: creación desde master OK,
cambio a nueva rama OK, cambio a master BLOQUEADO correctamente
con `archivo.txt` modificado, limpieza solamente del cambio temporal,
regreso posterior a master OK, `git branch --show-current` -> master,
`git status --short` -> sin salida, ambas ramas apuntaban a
`f9f40c4`, `git remote -v` -> sin salida, rama NO publicada;
eliminación de ramas permanece fuera del alcance V1.

Tarea NUEVA: ninguna pendiente dentro de esta etapa. La
publicación de una rama local sigue siendo una etapa FUTURA
separada. SIGUIENTE ETAPA INMEDIATA decidida por el usuario:
Tooltips Didácticos V1 (interfaz -> comando Git real ->
significado -> consecuencia -> riesgo); NO iniciada.

## ETAPA TOOLTIPS DIDÁCTICOS V1 — FASE 2A (P0/P1)

Tarea: Tooltips Didácticos V1 — Fase 2A (prioridades P0/P1) —
implementación y microcierre documental final.

Estado:

FASE CERRADA
PRUEBAS ESPECÍFICAS: 58/58 OK
SUITE COMPLETA: 209/209 OK
PRUEBA MANUAL WINDOWS FINAL DE LOS 4 TOOLTIPS CORREGIDOS
(Fetch, Push, Crear commit, Descartar cambios sin preparar...):
EXITOSA (confirmada por el usuario)
LOS 13 TOOLTIPS P0/P1 QUEDAN VALIDADOS
COMMITS LOCALES: bc57772 y 82a32d1 (hijo del primero)
SIN PUSH

Archivos funcionales:

- principal.py — diccionario TEXTOS_AYUDA_GIT_V1 con las 13
  claves P0/P1, consumido por AyudaEmergente;
- pruebas/test_ayuda_tooltips_v1.py — NUEVO, 58 pruebas.

Documentación:

- AGENTS.md
- CLAUDE.md
- TRABAJO_ACTUAL.md (este documento)

ayuda_interfaz.py:

INTACTO (los textos largos se renderizan con ancho_texto=620).

Servicios Git:

INTACTOS (servicio_git.py, servicio_remoto_git.py,
servicio_ramas_git.py, servicio_descarte_cambios_git.py y
servicio_cambios_locales_git.py sin cambios).

Fase 2B (tooltips P2/P3):

NO iniciada.

Publicar rama local:

FUTURA y separada.

HEAD observado al iniciar la etapa: eece381 Agrega selector
seguro de ramas locales; índice limpio.

Cierre de la fase (ambos commits LOCALES, NO hubo Push):

- bc57772 Mejora tooltips didacticos de Git — implementación y
  documentación de los 13 tooltips P0/P1;
- 82a32d1 Corrige precision didactica de Fetch y primer Push —
  HIJO de bc57772; microcorrecciones residuales de Fetch
  (``Qué cambia`` deja de afirmar ``Solo refs remotas locales``)
  y de primer Push (distingue rama remota existente de creación
  de rama remota nueva).

Detalles de implementación:

- 4 tooltips NUEVOS: Ramas..., Cambiar a seleccionada, Crear
  rama, Agregar origin;
- 9 tooltips REESCRITOS: Fetch, Pull, Push, Configurar GitHub...,
  Preparar seleccionados, Actualizar preparados, Quitar de
  preparados, Crear commit, Descartar cambios sin preparar...;
- cada texto enseña: comando Git real -> concepto (HEAD/working
  tree/índice/refs) -> qué cambia -> no hace -> requisitos/
  seguridad; sin operaciones prohibidas;
- microcorrecciones didácticas de este cierre: Pull explica que
  el flujo puede actualizar las refs LOCALES de seguimiento
  refs/remotes/... al obtener información del remoto (antes
  afirmaba "no modifica refs remotas"); Preparar explica que
  "registra/copia en el índice la versión actual de los archivos
  seleccionados" y que el working tree conserva sus cambios
  (antes decía "Preparar mueve cambios del working tree al
  índice");
- pruebas: 2 pruebas sustituidas por 2 nuevas que protegen esas
  correcciones (pull con refs/remotes y no hace Push; preparar
  con copia al índice y ausencia de la frase incorrecta),
  manteniendo el total en 58;
- NO se ejecutó sobre el repositorio real:
  git add / git commit / git fetch / git pull / git push /
  git reset / git restore / git checkout / git clean.

MICROCORRECCIÓN DIDÁCTICA DE TEXTOS (solo tooltips, SIN lógica):

- Fetch: eliminada la frase "no descarga commits a tu rama"
  (inducía a creer que Fetch no descarga); ahora explica que
  Fetch trae al repositorio local información y commits nuevos
  del remoto y actualiza refs/remotes/..., pero NO los integra
  en la rama local actual (no modifica HEAD, working tree ni
  índice, no crea merge);
- Push: eliminada "El primer Push solo se permite si el remoto
  está vacío de ramas conocidas". Lógica real verificada en
  servicio_remoto_git.py (ejecutar_push_seguro +
  _calcular_sin_upstream): si la rama remota YA EXISTE, el
  primer Push la actualiza y configura upstream con
  --set-upstream; solo si NO existe y habría que CREARLA se
  exige remoto vacío de otras ramas conocidas, y se bloquea si
  no puede verificarse;
- Commit: "no toca el working tree" -> "no incorpora
  automáticamente los cambios del working tree que no estén
  preparados" (usa lo preparado);
- Descartar: "archivos nuevos (??)" -> "archivos nuevos/no
  rastreados (marcados ?? por git status)";
- pruebas: test_push_explica_set_upstream_solo_primer_push
  renombrada a test_push_explica_set_upstream_y_rama_remota;
  asserts ampliados en fetch/commit/descartar; total mantenido
  en 58; suite completa 209;
- NO se modificó lógica Git; ayuda_interfaz.py y servicios
  INTACTOS; ambos commits (bc57772 y 82a32d1) son locales y
  SIN Push; revisión visual Windows final de los 4 tooltips:
  EXITOSA.

## Regla para reservar archivos

Antes de comenzar una tarea, el agente debe actualizar esta sección indicando:

Agente:
Tarea:
Archivos que modificará:
Estado: EN CURSO
Fecha/hora de inicio:

Ejemplo:

OpenCode:
Tarea: persistencia del último repositorio
Archivos:
- servicio_configuracion.py
- pruebas/test_configuracion.py
Estado: EN CURSO

Reserva activa:

SIN TAREA ACTIVA — Tooltips Didácticos V1 — Fase 2A: TERMINADA
(cierre documentado arriba: commits locales bc57772 y 82a32d1,
PRUEBA MANUAL WINDOWS EXITOSA, SIN PUSH).
Siguiente etapa: Tooltips Didácticos V1 — Fase 2B (NO iniciada).

Mientras una tarea figure EN CURSO, el otro agente NO debe modificar esos
archivos sin coordinación explícita.

## Al terminar una tarea

El agente debe:

1. ejecutar las pruebas;
2. ejecutar git diff --check (no preparados) y
   git diff --cached --check (preparados); distinguir ambos
   resultados y documentar la causa de cualquier aviso
   (p. ej. CR-at-EOL en archivos CRLF) sin afirmar que el
   índice está limpio si el segundo muestra avisos;
3. informar los archivos modificados;
4. actualizar este documento;
5. cambiar Estado a TERMINADO o SIN TAREA ACTIVA;
6. no hacer commit automáticamente salvo que el usuario lo solicite.

## Regla fundamental

AGENTS.md define las reglas.
TRABAJO_ACTUAL.md define quién está trabajando en qué.
CLAUDE.md conserva el contexto completo.
Git define la realidad actual.

No reemplazar archivos completos usando backups antiguos.
No trabajar sobre un archivo reservado por el otro agente.