# TRABAJO_ACTUAL.md

## Propósito

Este archivo coordina el trabajo en paralelo entre agentes.

Todo agente debe leerlo ANTES de modificar código.

No sustituye AGENTS.md ni CLAUDE.md.

## Estado del repositorio

Último HEAD conocido al crear este documento:

f92fe3c Actualiza documentacion para trabajo paralelo

Línea base funcional validada:

fe5e49e Agrega historial con filtros y exportacion

Validación funcional de esa línea base:

65 pruebas OK

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
- exportación TXT.

## Trabajo actual

Estado: TERMINADO - PENDIENTE DE REVISIÓN DEL USUARIO

Tarea: endurecer el primer Push (OpenCode).

Descripción:

- el primer Push (rama local sin upstream y sin existencia
  en el remoto) solamente se ejecuta cuando el remoto está
  vacío de ramas;
- tras el Fetch previo que ya realiza ejecutar_push_seguro(),
  se consultan las referencias remotas locales
  (git for-each-ref refs/remotes/<remoto>/);
- si existen otras ramas conocidas del remoto, se bloquea el
  Push indicando las ramas encontradas;
- si no es posible consultar las ramas, el Push se bloquea
  por incertidumbre;
- se agregó la prueba test_push_inicial_rechaza_remoto_con_otras_ramas
  (remoto con rama main, local en master, Push rechazado,
  refs/heads/master NO creada).

ChatGPT:
- tarea: ninguna;
- archivos reservados: ninguno.

OpenCode:
- tarea: endurecer primer Push (remoto debe estar vacío de ramas);
- estado: TERMINADO - PENDIENTE DE REVISIÓN DEL USUARIO;
- archivos modificados:

  - servicio_remoto_git.py (validación de otras ramas remotas);
  - pruebas/test_push_git.py (1 prueba nueva, total 73);
  - AGENTS.md;
  - CLAUDE.md;
  - TRABAJO_ACTUAL.md (este documento).

Resultados:

- 73 pruebas OK (72 anteriores + 1 nueva);
- primer Push real (origin GitHub, 15 commits por enviar)
  TODAVÍA NO realizado: espera la revisión del usuario;
- git diff --check (cambios no preparados) = limpio;
- git diff --cached --check (cambios preparados) = muestra
  avisos de trailing whitespace ÚNICAMENTE en líneas añadidas
  de servicio_remoto_git.py (350) y pruebas/test_push_git.py
  (128): causa conocida CR-at-EOL por los finales de línea
  CRLF de ambos archivos (servicio_remoto_git.py 1436/1436
  CRLF; test_push_git.py 865/865 CRLF), mantenidos por
  convención; no hay otros avisos y no hay mezcla de finales
  de línea;
- el índice NO está limpio de avisos (ver punto anterior);
- no hubo commit;
- no hubo Push;
- no se tocó ningún remoto real.

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