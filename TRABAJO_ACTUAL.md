# TRABAJO_ACTUAL.md

## Propósito

Este archivo coordina el trabajo en paralelo entre agentes.

Todo agente debe leerlo ANTES de modificar código.

No sustituye AGENTS.md ni CLAUDE.md.

## Estado del repositorio

Último HEAD conocido:

235e261 Actualiza estado previo al primer Push de GestorGit

Línea base funcional validada (histórica):

fe5e49e Agrega historial con filtros y exportacion

Validación funcional de esa línea base:

65 pruebas OK

Estado actual:

- etapa: VALIDADA - PENDIENTE DE COMMIT (visor de cambios de
  commits y primer Push real de GestorGit);
- primer Push real: exitoso, origin/master creado, upstream
  configurado, Por enviar 0, Por descargar 0, sin Push forzado;
- prueba manual del visor: EXITOSA en Windows;
- 79 pruebas OK;
- visor todavía sin commit (cambios preparados en el índice).

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
- detalle de cambios de un commit (solo lectura).

## Trabajo actual

Estado: ETAPA VALIDADA - PENDIENTE DE COMMIT

Tarea: visor de cambios de un commit (OpenCode).

Descripción:

- botón "Ver cambios..." en el historial, habilitado al
  seleccionar un commit;
- relación fila -> CommitGit sin volver a consultar el historial;
- ventana única "Cambios del commit" de solo lectura con datos
  del commit, advertencia y diff coloreado;
- git show con --no-ext-diff, --no-textconv, --no-color y
  verificación previa del hash (40 o 64 caracteres hexadecimales);
- límite visual de 500000 caracteres con aviso de truncación;
- botones Cerrar y Copiar diff;
- 6 pruebas nuevas (total: 79).

ChatGPT:
- tarea: ninguna;
- archivos reservados: ninguno.

OpenCode:
- tarea: visor de cambios de un commit;
- estado: ETAPA VALIDADA - PENDIENTE DE COMMIT;
- archivos modificados:

  - servicio_historial_git.py (obtener_cambios_commit + validación de hash);
  - principal.py (botón Ver cambios..., ventana de detalle, relación fila -> commit);
  - pruebas/test_detalle_commit_git.py (6 pruebas nuevas, archivo nuevo);
  - AGENTS.md;
  - CLAUDE.md;
  - TRABAJO_ACTUAL.md (este documento).

Resultados:

- 79 pruebas OK (73 anteriores + 6 nuevas);
- git diff --check (cambios no preparados) = limpio;
- prueba manual del visor EXITOSA en Windows, confirmada por el
  usuario: botón Ver cambios..., selección y doble clic, datos del
  commit, diff, colores de agregado/eliminado/bloque/encabezado,
  scroll vertical y horizontal, Copiar diff;
- consultar commits no produjo cambios en el repositorio;
- el primer Push real fue ejecutado y VALIDADO por el usuario;
- la etapa del visor sigue sin commit (cambios preparados
  en el índice);
- esta tarea no ejecutó Push ni operaciones remotas;
- no hubo operación destructiva.

## Próxima tarea propuesta

Persistencia segura del último repositorio seleccionado mediante config.json.

Todavía NO iniciada.

No guardar tokens, contraseñas ni credenciales.

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