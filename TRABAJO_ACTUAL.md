# TRABAJO_ACTUAL.md

## Propósito

Este archivo coordina el trabajo en paralelo entre agentes.

Todo agente debe leerlo ANTES de modificar código.

No sustituye AGENTS.md ni CLAUDE.md.

## Estado del repositorio

Último HEAD conocido:

0e3840e Agrega visor de cambios de commits

Línea base funcional validada (histórica):

fe5e49e Agrega historial con filtros y exportacion

Validación funcional de esa línea base:

65 pruebas OK

Estado actual:

- etapa: ETAPA VALIDADA - PENDIENTE DE COMMIT;
- persistencia del último repositorio: VALIDADA (prueba manual
  en Windows EXITOSA con anterioridad);
- actualización de archivos preparados: VALIDADA MANUALMENTE en
  Windows con el caso real MM;
- validación de rechazo de ruta con carácter NUL: PRUEBA
  AUTOMATIZADA EXITOSA;
- correcciones de portabilidad de pruebas (comparación
  semántica de rutas mediante Path.resolve(), encoding UTF-8
  en subprocess de diff): EXITOSAS;
- 94 pruebas OK;
- config.json ignorado y no versionado;
- ambas funcionalidades (persistencia y actualización de
  preparados) todavía forman parte del working tree actual y
  todavía NO tienen commit;
- no hubo Push;
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
- actualización de archivos preparados.

## Trabajo actual

Estado: ETAPA VALIDADA - PENDIENTE DE COMMIT

Tarea: botón "Actualizar preparados" (OpenCode).

ADVERTENCIA ESPECIAL:

Esta tarea comenzó deliberadamente con un working tree/índice
NO limpio y AUTORIZADO por el usuario:

- CLAUDE.md y TRABAJO_ACTUAL.md estaban en el estado real
  "Modificado, preparado y vuelto a modificar" (MM);
- el índice contiene además los archivos preparados de la
  etapa de persistencia (aún NO commiteada);
- .opencode/ está sin versionar.

NO se ejecutó ni se ejecutará durante el desarrollo:

git reset / git restore / git checkout / git add / git commit / git push

El índice NO se modifica durante el desarrollo.

Descripción:

- detectar "preparado y vuelto a modificar" desde el estado
  estructurado de git status --porcelain;
- botón "Actualizar preparados" entre Preparar y Quitar;
- columna Preparado con "Sí (hay cambios nuevos)";
- equivale a volver a ejecutar git add sobre rutas explícitas;
- no deshace cambios; no crea commits.

ChatGPT:
- tarea: ninguna;
- archivos reservados: ninguno.

OpenCode:
- tarea: botón "Actualizar preparados";
- estado: ETAPA VALIDADA - PENDIENTE DE COMMIT;
- archivos que modificó:

  - modelos.py (campo requiere_actualizar_preparado);
  - servicio_git.py (detección + actualizar_archivos_preparados
    + mensaje educativo del commit);
  - principal.py (botón, columna, tooltip, confirmación);
  - pruebas/test_actualizacion_preparados.py (7 pruebas nuevas,
    archivo nuevo);
  - AGENTS.md;
  - CLAUDE.md;
  - TRABAJO_ACTUAL.md (este documento).

Resultados:

- HEAD inicial observado: 0e3840e;
- git status --short inicial (autorizado, sin limpiar):
  M AGENTS.md; MM CLAUDE.md; MM TRABAJO_ACTUAL.md;
  A modelos_configuracion.py; M principal.py;
  A pruebas/test_configuracion.py; A servicio_configuracion.py;
  ?? .opencode/
- 94 pruebas OK (python3 -m unittest discover -s ./pruebas);
- no se hizo commit ni push.

PRUEBA MANUAL EN WINDOWS: EXITOSA

Hechos confirmados visualmente con el repositorio de GestorGit:

- AGENTS.md, CLAUDE.md, TRABAJO_ACTUAL.md y principal.py fueron
  detectados como "Modificado, preparado y vuelto a modificar";
- la columna Preparado mostró "Sí (hay cambios nuevos)";
- al seleccionar esos archivos, "Actualizar preparados" se
  habilitó;
- la confirmación enumeró únicamente los 4 archivos que
  realmente necesitaban actualización, aunque hubiera una
  selección más amplia;
- después de aceptar: dejaron de mostrar "vuelto a modificar",
  continuaron preparados y la columna volvió a mostrar "Sí";
- cuando ninguno de los seleccionados requería actualización,
  "Actualizar preparados" quedó deshabilitado;
- no se creó ningún commit durante la prueba;
- 94 pruebas automatizadas OK.

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