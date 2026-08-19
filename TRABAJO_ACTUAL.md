# TRABAJO_ACTUAL.md

## Propósito

Este archivo coordina el trabajo en paralelo entre agentes.

Todo agente debe leerlo ANTES de modificar código.

No sustituye AGENTS.md ni CLAUDE.md.

## Estado del repositorio

HEAD observado al iniciar la corrección final:

c62b0a0 Agrega inspector de cambios locales

El HEAD actual debe consultarse siempre con:

git log -1 --oneline

El HEAD apunta a master y está sincronizado con origin/master
(Push confirmado por Git y por el usuario).

Históricos:

- 014e3f7 Agrega persistencia y actualizacion segura de preparados
  (persistencia + actualización de preparados: commiteadas y con Push);
- 0e3840e Agrega visor de cambios de commits;
- fe5e49e Agrega historial con filtros y exportacion
  (línea base funcional validada; 65 pruebas OK en su momento).

Estado actual:

- etapa inspector de cambios locales: ETAPA VALIDADA MANUALMENTE;
- prueba manual en Windows: EXITOSA (confirmada por el usuario);
- el inspector forma parte de HEAD (c62b0a0) y del remoto;
- corrección del error silencioso de git diff --numstat:
  pendiente de commit (vive en el working tree actual);
- 105 pruebas OK (104 anteriores + 1 de regresión de --numstat);
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
- inspector de cambios locales (solo lectura).

## Trabajo actual

Estado: TAREA TERMINADA - SIN COMMIT

Tarea: cierre documental del inspector + corrección de --numstat.

HEAD inicial observado: c62b0a0 (working tree limpio).
El inspector ya estaba commiteado y pusheado (origin/master = c62b0a0).

NO se ejecutó durante esta tarea:

git add / git reset / git restore / git checkout / git commit /
git fetch / git pull / git push

Trabajo realizado (documental):

- TRABAJO_ACTUAL.md, AGENTS.md y CLAUDE.md corregidos: cabeceras
  obsoletas eliminadas, HEAD real c62b0a0 documentado, 014e3f7
  y 0e3840e quedan como históricos;
- prueba manual del inspector: marcada EXITOSA en Windows con los
  casos confirmados por el usuario (sin preparar, preparado, MM,
  resúmenes, colores, scroll, Actualizar local, Copiar diff,
  habilitación con un archivo);
- persistencia y actualización de preparados: ya commiteadas
  (014e3f7); ya no figuran como pendientes;
- "Descartar cambios sin preparar": mencionado únicamente como
  posible etapa futura, no implementada.

Trabajo realizado (corrección funcional):

- servicio_cambios_locales_git.py: si git diff --numstat FALLA,
  obtener_detalle() devuelve ResultadoDetalleCambioLocal con
  exitoso=False y mensaje controlado; nunca 0 inserciones /
  0 eliminaciones falsos; _obtener_resumen() devuelve el error
  como resultado (patrón _convertir_fecha_iso del historial);
  un numstat exitoso y vacío sigue siendo legítimamente 0/0;
- prueba nueva en pruebas/test_cambios_locales_git.py:
  test_error_numstat_no_se_convierte_en_cero (ServicioGitEspia
  con fallar_numstat=True); el spy no ejecuta Git real;
- servicio_git.py NO se modificó.

Resultados:

- 105 pruebas OK en la suite completa
  (104 anteriores + 1 nueva de regresión);
- py_compile de todos los módulos OK;
- git diff --check: SIN avisos;
- git diff --cached --check: sin avisos (no hay nada preparado);
- git status --short final:
  M AGENTS.md; M CLAUDE.md; M TRABAJO_ACTUAL.md;
  M servicio_cambios_locales_git.py;
  M pruebas/test_cambios_locales_git.py;
- sin cambios en servicio_git.py (git diff -- servicio_git.py vacío);
- no se ejecutó git add ni commit.

PRUEBA MANUAL DEL INSPECTOR EN WINDOWS: EXITOSA.

Hechos confirmados visualmente por el usuario:

- archivo modificado sin preparar: la pestaña `Sin preparar`
  muestra el diff y `Preparados` muestra 0/0 con
  "No hay cambios preparados";
- archivo preparado: `Preparados` muestra el diff que entraría
  al commit;
- caso MM: "Modificado, preparado y vuelto a modificar",
  Preparado = "Sí (hay cambios nuevos)"; `Sin preparar` muestra
  únicamente los cambios posteriores al staging y `Preparados`
  conserva el diff previamente preparado; ambos diffs distintos;
- resúmenes de inserciones/eliminaciones visibles;
- colores + / - / @@ funcionan;
- scroll horizontal y vertical funcionan;
- `Actualizar` refresca únicamente el estado LOCAL;
- `Copiar diff` funciona;
- `Ver cambios locales...` se habilita con exactamente un archivo
  y se deshabilita con selección múltiple;
- la prueba temporal fue retirada y el staging de prueba quitado
  al finalizar.

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