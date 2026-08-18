# TRABAJO_ACTUAL.md

## Propósito

Este archivo coordina el trabajo en paralelo entre agentes.

Todo agente debe leerlo ANTES de modificar código.

No sustituye AGENTS.md ni CLAUDE.md.

## Estado del repositorio

Último HEAD conocido:

d12df38 Agrega configuracion inicial segura de GitHub

Línea base funcional validada (histórica):

fe5e49e Agrega historial con filtros y exportacion

Validación funcional de esa línea base:

65 pruebas OK

Estado actual:

- working tree limpio;
- 73 pruebas OK;
- origin configurado mediante GestorGit;
- primer Push real pendiente.

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
- primer Push solo con remoto vacío de ramas.

## Trabajo actual

Estado: COMMIT REALIZADO - PENDIENTE DE PRIMER PUSH REAL

La etapa de configuración inicial segura de GitHub, el
endurecimiento del primer Push (remoto vacío de ramas) y sus
pruebas quedaron integrados en el commit:

d12df38 Agrega configuracion inicial segura de GitHub

Prueba manual real en Windows (confirmada visualmente
por el usuario):

- origin fue configurado realmente mediante GestorGit
  (botón Configurar GitHub...);
- Fetch REAL contra GitHub fue exitoso;
- rama local: master;
- upstream: NO configurado;
- origin/master: todavía no existe;
- antes del último commit había 15 commits por enviar;
- se creó desde GestorGit el commit d12df38;
- después del commit:
  - repositorio limpio;
  - Por enviar: 16 commits;
  - Por descargar: 0 commits;
  - Push habilitado en la interfaz;
- el primer Push real TODAVÍA NO se ha ejecutado.

ChatGPT:
- tarea: ninguna;
- archivos reservados: ninguno.

OpenCode:
- tarea: ninguna;
- archivos reservados: ninguno.

## Próxima tarea propuesta

Persistencia del último repositorio seleccionado mediante config.json.

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