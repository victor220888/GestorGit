# Método de trabajo con agentes — GestorGit

## Objetivo

Mantener seguridad, trazabilidad y continuidad usando pocos tokens.

Este documento NO es de lectura obligatoria en cada tarea.
Se consulta al incorporar un agente, cambiar el método o resolver una duda de
coordinación.

## Puerta de entrada por agente

```text
Claude Code           -> CLAUDE.md + TRABAJO_ACTUAL.md
ZCode/OpenCode/otros  -> AGENTS.md + TRABAJO_ACTUAL.md
```

No hacer que un agente lea `AGENTS.md` Y `CLAUDE.md` normalmente.
Ambos contienen las mismas reglas críticas adaptadas a su herramienta.

Las reglas comunes deben permanecer coherentes.

## Separación de documentos

### Estables, poco frecuentes

`AGENTS.md` y `CLAUDE.md`:

- seguridad;
- convenciones;
- arquitectura mínima;
- roles;
- forma de validar/reportar.

NO guardan HEAD, número de tests, prompt activo ni historial de etapas.

`METODO_TRABAJO_AGENTES.md`:

- proceso de coordinación;
- formato de bitácora;
- política de tokens.

### Dinámico

`TRABAJO_ACTUAL.md`:

- tarea/etapa actual;
- último estado conocido;
- archivos implicados;
- pruebas actuales;
- decisiones vigentes;
- pendientes y siguiente paso.

Debe mantenerse CORTO. Cuando una etapa termina, sustituir su detalle por un
resumen breve.

### Histórico

`seguimiento_prompts/`:

- prompts exactos;
- REV / ADDENDUM;
- resultados;
- índice vivo `README.md`.

No se lee completo para programar una tarea nueva.

Git conserva además la historia versionada del proyecto.

## Roles

### Usuario

- decide objetivos y prioridades;
- guarda los archivos descargables;
- ejecuta pruebas manuales/visuales;
- ejecuta desde GestorGit las operaciones Git productivas que la
  aplicación soporta;
- autoriza staging, commit y Push;
- trae informes de agentes a ChatGPT.

### ChatGPT

- orquesta;
- diseña prompts;
- audita informes y archivos;
- genera `GG-PROMPT-XXX-RESULTADO.md`;
- decide con el usuario el siguiente paso.

### Agente programador

- lee su archivo de configuración + `TRABAJO_ACTUAL.md`;
- revisa Git real (auditoría de solo lectura);
- no sustituye a GestorGit por CLI en operaciones productivas soportadas,
  salvo excepción declarada de forma explícita en el prompt;
- ejecuta solo el alcance del prompt;
- prueba;
- informa;
- se detiene.

Un solo agente programador puede modificar el repositorio a la vez.

## Ciclo normal

```text
ChatGPT prepara GG-PROMPT-XXX
        ↓
usuario lo entrega al agente
        ↓
agente implementa / prueba / informa
        ↓
usuario trae el informe
        ↓
ChatGPT audita
        ↓
ChatGPT genera GG-PROMPT-XXX-RESULTADO
        ↓
prueba manual si corresponde
        ↓
cierre documental
        ↓
operación Git productiva soportada por GestorGit:
agente/ChatGPT audita
        ↓
usuario ejecuta en GestorGit (solo con autorización cuando aplique)
        ↓
agente/ChatGPT audita
```

Las operaciones productivas no soportadas por GestorGit, o las excepciones
por recuperación/diagnóstico, se declaran de forma explícita en el prompt y
requieren autorización expresa del usuario cuando implican escritura o red.

Un informe del agente no significa “tarea aceptada” hasta la auditoría.

## Patrón de ciclo de vida de una etapa

Patrón validado en la práctica (GG-PROMPT-001..016, etapa Publicar rama
local V1):

```text
incorporación del agente (solo lectura, sin reservas, informe de reconstrucción)
        ↓
análisis de la etapa futura (sin implementar nada)
        ↓
implementación con prompt: decisiones YA aprobadas, archivos autorizados
explícitos, comandos productivos exactos, pruebas enumeradas, prohibiciones
        ↓
ADDENDUM/REV del prompt si hace falta (PREVALECE sobre el prompt base)
        ↓
auditoría de ChatGPT → microcorrecciones mínimas (funcionales, visuales,
de estado GUI, pedagógicas o documentales), cada una con alcance propio
        ↓
prueba manual del usuario (batería funcional + retests visuales cortos;
el agente nunca ejecuta la GUI contra el repositorio real)
        ↓
cierre documental (TRABAJO_ACTUAL compacto; README solo si está desactualizado)
        ↓
microcorrección documental precommit si la auditoría la pide
        ↓
cierre del bloque documental:
auditoría pre-operación de solo lectura
        ↓
autorización explícita del usuario cuando aplique
        ↓
usuario ejecuta staging selectivo desde GestorGit (lista exacta)
        ↓
auditoría de solo lectura del staged set
        ↓
usuario crea UN commit local desde GestorGit
        ↓
auditoría postcommit de solo lectura
        ↓
cierre documental postcommit (+ registro de cambios de método estables)
```

Invariantes que no se negocian:

- Git real manda sobre cualquier documento.
- Toda autorización es explícita, textual y NO se hereda entre tareas.
- Archivos autorizados/prohibidos declarados por tarea; reserva visible en
  `TRABAJO_ACTUAL.md` cuando corresponda. Si surge la necesidad de tocar
  un archivo no autorizado: DETENERSE y ampliar explícitamente el alcance
  ANTES de modificarlo; nunca se autoriza ni registra retrospectivamente
  una modificación no autorizada.
- Nunca `git add .` ni `git add -A`; el conjunto preparado se verifica
  exacto (sin faltantes ni extras) ANTES del commit.
- Contradicción material con Git o con el prompt: detenerse y reportar;
  no improvisar ni “arreglar” el estado por iniciativa propia.
- Cambio funcional: pruebas focalizadas + suite completa. Microcorrección:
  focalizadas. Tarea documental: comprobaciones de diff, sin suite.
- Los avisos CR-at-EOL históricos se documentan; no se normalizan archivos
  para silenciarlos.
- Desde GG-PROMPT-016, las operaciones Git productivas soportadas las
  ejecuta el usuario desde GestorGit; los agentes auditan antes/después
  (solo lectura) y no las sustituyen por CLI salvo excepción declarada.

Guía de onboarding para el propietario del proyecto (humano):
`GUIA_TRABAJO_CON_AGENTES.md`.

## Bitácora

ID global, secuencial, nunca reutilizado:

```text
GG-PROMPT-001
GG-PROMPT-002
...
```

El usuario administra físicamente las carpetas para ahorrar tokens.

ChatGPT genera:

- prompt;
- resultado auditado;
- actualización del índice cuando corresponda.

El agente NO administra la bitácora salvo instrucción puntual.

`seguimiento_prompts/README.md` se reemplaza por su versión más reciente.
Prompts/resultados históricos se conservan.

## Política para prompts cortos

Un prompt nuevo NO debe repetir todas las reglas de `AGENTS.md`/`CLAUDE.md`.

Debe contener solo:

1. ID, agente, tipo, etapa;
2. objetivo;
3. estado Git esperado relevante;
4. archivos autorizados/prohibidos;
5. requisitos ESPECÍFICOS de la tarea;
6. pruebas específicas;
7. estado final esperado;
8. formato de informe y “detente”.

Repetir reglas generales solo cuando sean especialmente relevantes para el
riesgo de esa tarea.

## Política para informes cortos

Por defecto el agente reporta:

1. Git inicial;
2. archivos tocados;
3. cambio;
4. pruebas focalizadas;
5. suite completa si se ejecutó;
6. diff/staging/lock;
7. remoto/commit sí-no;
8. pendientes.

No pegar salida `-v` completa cuando todo pasa.
Ante un fallo sí incluir el fragmento necesario.

## Política de pruebas para ahorrar tokens/tiempo

- Cambio funcional: focalizadas + suite completa antes de cierre.
- Microcorrección funcional: focalizadas + suite completa.
- Cambio SOLO documental: no ejecutar suite completa salvo riesgo o requisito
  explícito; usar comprobaciones documentales/diff.
- Prueba manual: no repetir baterías ya validadas si el código funcional no
  cambió; hacer retest focalizado.
- Ejecutar con `-v` si conviene, pero informar solo resumen cuando pasa.

La seguridad prevalece sobre el ahorro.

## Política de contexto

Un agente NO debe leer por defecto:

- todo `seguimiento_prompts/`;
- resultados históricos;
- `CONTINUIDAD_CHATGPT.md`;
- README de producto;
- el archivo de configuración del otro agente;
- documentación histórica archivada.

Leerlos solo si la tarea lo requiere.

## Actualización documental

Actualizar `AGENTS.md`/`CLAUDE.md` solo cuando cambie una regla ESTABLE:

- seguridad;
- arquitectura relevante;
- herramienta/entorno;
- coordinación;
- convención transversal.

Actualizar `TRABAJO_ACTUAL.md` cuando cambie el estado de la tarea.

Cuando `TRABAJO_ACTUAL.md` crezca demasiado:

1. conservar un archivo histórico fuera del flujo de lectura normal;
2. reducir `TRABAJO_ACTUAL.md` a la situación vigente;
3. no obligar a agentes a leer el histórico.

## Regla Git

Git real es la fuente de verdad.
La documentación orienta, nunca sustituye:

```text
git status
git log
git branch
staging
locks/operaciones en curso
```

Ante contradicción material: detenerse y reportar.
