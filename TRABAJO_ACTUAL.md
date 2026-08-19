# TRABAJO_ACTUAL.md

## Propósito

Este archivo coordina el trabajo en paralelo entre agentes.

Todo agente debe leerlo ANTES de modificar código.

No sustituye AGENTS.md ni CLAUDE.md.

## Estado del repositorio

HEAD observado al iniciar la etapa del descarte:

634a295 Corrige manejo de errores del inspector

El HEAD actual debe consultarse siempre con:

git log -1 --oneline

En el momento de iniciar la etapa: working tree limpio,
master sincronizado con origin/master.

Históricos:

- c62b0a0 Agrega inspector de cambios locales;
- 014e3f7 Agrega persistencia y actualizacion segura de preparados
  (persistencia + actualización de preparados: commiteadas y con Push);
- 0e3840e Agrega visor de cambios de commits;
- fe5e49e Agrega historial con filtros y exportacion
  (línea base funcional validada; 65 pruebas OK en su momento).

Estado actual:

- etapa descarte de cambios sin preparar: ETAPA VALIDADA -
  PRUEBA MANUAL EXITOSA en Windows (confirmada por el usuario);
- inspector de cambios locales: ETAPA VALIDADA MANUALMENTE
  (prueba manual EXITOSA confirmada por el usuario);
- corrección del error silencioso de git diff --numstat:
  commiteada en 634a295;
- 123 pruebas OK (105 + 17 del descarte + 1 del conflicto
  estructurado);
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
- primer Push solo con remoto vacío de ramas;
- detalle de cambios de un commit (solo lectura);
- persistencia del último repositorio (config.json);
- actualización de archivos preparados;
- inspector de cambios locales (solo lectura + descarte de
  cambios sin preparar).

## Trabajo actual

Estado: TAREA TERMINADA - SIN COMMIT

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