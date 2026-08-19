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
- actualización de archivos preparados;
- inspector de cambios locales (solo lectura).

## Trabajo actual

Estado: ETAPA IMPLEMENTADA - PRUEBA MANUAL PENDIENTE

Tarea: inspector de cambios locales (OpenCode).

HEAD inicial observado: 014e3f7 (working tree limpio).

NO se ejecutó durante el desarrollo:

git add / git reset / git restore / git checkout / git commit /
git fetch / git pull / git push

Descripción:

- ventana de SOLO LECTURA "Cambios locales - Gestor Git";
- botón "Ver cambios locales..." habilitado únicamente con
  exactamente UN archivo seleccionado;
- pestañas "Sin preparar" (git diff) y "Preparados"
  (git diff --cached);
- resúmenes con --numstat; binarios muestran "Archivo binario";
- archivos nuevos sin preparar (??): mensaje educativo;
- archivo sin cambios: "El archivo ya no tiene cambios locales
  pendientes."
- Actualizar solo consulta el estado LOCAL (sin Fetch);
- Copiar diff copia la pestaña activa;
- límite visual 500000 caracteres;
- ventana única; se cierra al cambiar de repositorio.

ChatGPT:
- tarea: ninguna;
- archivos reservados: ninguno.

OpenCode:
- tarea: inspector de cambios locales;
- estado: ETAPA IMPLEMENTADA - PRUEBA MANUAL PENDIENTE;
- archivos que creó/modificó:

  - modelos_cambios_locales.py (nuevo);
  - servicio_cambios_locales_git.py (nuevo);
  - pruebas/test_cambios_locales_git.py (nuevo, 10 pruebas);
  - principal.py (botón + ventana + integración);
  - AGENTS.md;
  - CLAUDE.md;
  - TRABAJO_ACTUAL.md (este documento).

Resultados:

- 104 pruebas OK en la suite completa
  (94 anteriores + 10 nuevas);
- py_compile de todos los módulos OK
  (principal.py incluido; el import requiere Tkinter,
  presente en Windows);
- git diff --check: SIN avisos;
- git diff --cached --check: sin avisos (no hay nada preparado);
- git status --short final:
  M AGENTS.md; M principal.py; M TRABAJO_ACTUAL.md;
  ?? modelos_cambios_locales.py; ?? servicio_cambios_locales_git.py;
  ?? pruebas/test_cambios_locales_git.py; ?? .opencode/ ;
- no se ejecutó git add ni commit;
- .opencode/ no se versiona.

PRUEBA MANUAL: PENDIENTE (esperando confirmación del usuario).

Caso recomendado:
1. Modificar temporalmente un archivo del repositorio GestorGit.
2. Actualizar GestorGit.
3. Seleccionarlo y abrir "Ver cambios locales...".
4. Confirmar: pestaña Sin preparar con diff; Preparados vacía.
5. Preparar el archivo desde la interfaz y comprobar que el diff
   pasa a la pestaña Preparados.
6. Modificar nuevamente el mismo archivo y confirmar el caso MM:
   Sin preparar -> cambios posteriores;
   Preparados -> versión ya preparada.
7. Probar Actualizar, Copiar diff y Cerrar.

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