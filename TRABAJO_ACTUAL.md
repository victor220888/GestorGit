# TRABAJO_ACTUAL.md

## Propósito

Estado dinámico y compacto del trabajo ACTUAL de GestorGit.

Todo agente debe leer este archivo después de su archivo de configuración
(`AGENTS.md` o `CLAUDE.md`).

Para historia detallada usar Git y `seguimiento_prompts/`; NO cargarla por
defecto.

## Fuente de verdad

Antes de trabajar consultar Git real.

Commit auditado que cerró el bloque documental de método/onboarding:

```text
89e5672 Documenta método y onboarding de agentes
```

`89e5672` identifica ese cierre auditado; NO es una constante: después de
commits futuros el HEAD real se consulta con `git log`, nunca se asume.

Snapshot observado en la auditoría de GG-PROMPT-019:

```text
rama: master
ahead: 10 respecto de origin/master
staging: vacío
working tree versionado: limpio
.git/index.lock: inexistente
```

Estos datos son referencia; verificar de nuevo en cada tarea.

## Etapa

```text
Publicar rama local V1 = CERRADA (commit funcional 7c603fd, auditado)
Bloque método/onboarding = CERRADO Y AUDITADO (commit 89e5672)
Push = NO autorizado
```

GG-PROMPT-015 creó `7c603fd` con exactamente 12 archivos (3 de código, 4 de
pruebas, 5 de documentación). GG-PROMPT-018 auditó el staged set y
GG-PROMPT-019 auditó el commit `89e5672` (exactamente 6 documentos de
método/onboarding); ambas auditorías aceptadas por ChatGPT.

Pruebas finales de la etapa funcional:

```text
test_publicar_rama_git.py: 70 OK
test_ayuda_emergente.py: 10 OK
suite completa: 426 OK
prueba manual A-F: OK
retest visual final: OK
```

No usar 426 como constante eterna: confirmar el total real cuando una tarea
vuelva a ejecutar la suite.

## Decisión vigente de método (GG-PROMPT-016 = ACEPTADO)

Las operaciones Git PRODUCTIVAS sobre GestorGit que la propia aplicación
soporta (staging/unstaging, commit, Fetch, Pull seguro, Push seguro y
operaciones de ramas soportadas) las ejecuta el USUARIO desde GestorGit:

```text
agente/ChatGPT audita -> usuario ejecuta en GestorGit -> agente/ChatGPT audita
```

Los agentes no las ejecutan por CLI por defecto (excepción solo si el prompt
la declara de forma explícita y, con escritura o red, con autorización
expresa del usuario). Las consultas Git de solo lectura siguen siendo
obligatorias.

## Administrativos fuera del versionado

```text
.zcode/
CONTINUIDAD_CHATGPT.md
seguimiento_prompts/
GestorGit_plan_continuidad_y_modo_equipo.md
```

## Reserva actual

No hay tarea de código activa.

Push sigue NO autorizado. El próximo trabajo funcional o la eventual
publicación remota se decidirán con una tarea/autorización nueva; no iniciar
ninguna de esas acciones por iniciativa propia.

Si se abre una nueva tarea de código, el prompt deberá declarar sus archivos
autorizados.

## Deuda técnica fuera del alcance

Existen comprobaciones históricas en Push/Pull relacionadas con texto de
conflicto. No tocarlas por iniciativa propia: la funcionalidad actual tiene
otras defensas y cualquier corrección debe ser una tarea separada.

## Seguridad

Hasta autorización explícita:

- no `git add` ni staging por CLI;
- no commit;
- no Fetch/Pull/Push;
- no reset/clean;
- no borrar locks;
- no modificar remotos reales.
