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
- revisa Git real;
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
staging/commit solo con autorización
```

Un informe del agente no significa “tarea aceptada” hasta la auditoría.

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
