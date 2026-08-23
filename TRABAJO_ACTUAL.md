# TRABAJO_ACTUAL.md

## Propósito

Estado dinámico y compacto del trabajo ACTUAL de GestorGit.

Todo agente debe leer este archivo después de su archivo de configuración
(`AGENTS.md` o `CLAUDE.md`).

Para historia detallada usar Git y `seguimiento_prompts/`; NO cargarla por
defecto.

## Fuente de verdad

Antes de trabajar consultar Git real.

HEAD conocido (creado por GG-PROMPT-015):

```text
7c603fd Agrega publicación segura de rama local V1
```

Rama: `master`. Ahead conocido: 9 respecto de `origin/master`.
Staging informado: vacío. `.git/index.lock`: inexistente.

Estos datos son referencia; verificar de nuevo.

## Etapa

```text
Publicar rama local V1 = CERRADA Y COMMIT LOCAL CREADO
Push = NO autorizado
```

GG-PROMPT-015 creó el commit local `7c603fd` con exactamente 12 archivos
(3 de código, 4 de pruebas, 5 de documentación). Quedaron FUERA, sin
versionar, los cuatro administrativos:

```text
.zcode/
CONTINUIDAD_CHATGPT.md
seguimiento_prompts/
GestorGit_plan_continuidad_y_modo_equipo.md
```

Pruebas finales de la etapa:

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

Desde ahora, las operaciones Git PRODUCTIVAS sobre GestorGit que la propia
aplicación soporta (staging/unstaging, commit, Fetch, Pull seguro, Push
seguro y operaciones de ramas soportadas) las ejecuta el USUARIO desde
GestorGit:

```text
agente/ChatGPT audita -> usuario ejecuta en GestorGit -> agente/ChatGPT audita
```

Los agentes no las ejecutan por CLI por defecto (excepción solo si el prompt
la declara de forma explícita y, con escritura o red, con autorización
expresa del usuario). Las consultas Git de solo lectura siguen siendo
obligatorias.

## Bloque documental de método/onboarding (candidato al commit)

GG-PROMPT-016 fue ACEPTADO por ChatGPT. La tarea directa del usuario
(memoria del método + onboarding) fue revisada por ChatGPT y se consolida
mediante GG-PROMPT-017-REV1 (mismo bloque).

Candidato al futuro commit local: exactamente SEIS archivos versionables:

```text
AGENTS.md
CLAUDE.md
METODO_TRABAJO_AGENTES.md
README.md
TRABAJO_ACTUAL.md
GUIA_TRABAJO_CON_AGENTES.md
```

Los cuatro administrativos conocidos siguen EXCLUIDOS:

```text
.zcode/
CONTINUIDAD_CHATGPT.md
seguimiento_prompts/
GestorGit_plan_continuidad_y_modo_equipo.md
```

No hay staging todavía. Una vez que ChatGPT acepte GG-PROMPT-017-REV1, el
cierre del bloque es:

```text
usuario prepara exactamente los 6 documentos desde GestorGit
        ↓
auditoría de solo lectura del staged set
        ↓
usuario crea UN commit local desde GestorGit
        ↓
auditoría postcommit de solo lectura
```

Push = NO autorizado.

## Reserva actual

No hay un agente programador ejecutando una modificación de código.

Siguiente trabajo previsto: auditoría de ChatGPT sobre GG-PROMPT-017-REV1
y, una vez aceptada, cierre del bloque documental de 6 archivos desde
GestorGit (ver la sección anterior). Push NO autorizado.

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

El repositorio temporal de las pruebas ya no es necesario para el cierre y
puede eliminarse manualmente cuando el usuario quiera.
