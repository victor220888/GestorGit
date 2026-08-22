# TRABAJO_ACTUAL.md

## Propósito

Estado dinámico y compacto del trabajo ACTUAL de GestorGit.

Todo agente debe leer este archivo después de su archivo de configuración
(`AGENTS.md` o `CLAUDE.md`).

Para historia detallada usar Git y `seguimiento_prompts/`; NO cargarla por
defecto.

## Fuente de verdad

Antes de trabajar consultar Git real.

Último HEAD informado al terminar GG-PROMPT-012 (cierre documental):

```text
4cd1ca5 Agrega leyenda contextual de estados Git V1
```

Rama informada:

```text
master
```

Relación conocida:

```text
ahead 8 respecto de origin/master
```

Staging informado: vacío.
`.git/index.lock`: inexistente.

Estos datos son referencia; verificar de nuevo.

## Etapa activa

```text
Publicar rama local V1 = CERRADA
```

Cierre documental: GG-PROMPT-012 (2026-08-21). Implementación,
auditorías/microcorrecciones, pruebas automáticas, prueba manual
A–F, retest visual de layout/texto y retest visual del tooltip:
todo OK.

Resumen del comportamiento cerrado:

- publica únicamente la rama local ACTUAL;
- requiere Fetch manual exitoso en la sesión;
- bloquea si ya existe upstream o si la rama remota homónima ya
  existe en el remoto;
- consulta `ls-remote --heads` fresca justo antes del Push;
- Push exacto con `--set-upstream` y una única ref de destino
  (`<rama>:refs/heads/<rama>`);
- nunca force / all / tags / mirror / delete;
- después de éxito o de fallo exige un Fetch nuevo;
- GUI no modal y trabajo remoto fuera del hilo Tkinter;
- tooltips reposicionados dentro de la pantalla (corrección
  general de `AyudaEmergente`).

Pruebas finales de la etapa:

```text
test_publicar_rama_git.py: 70 OK
test_ayuda_emergente.py: 10 OK
suite completa: 426 OK
prueba manual A-F: OK
retest visual final: OK
```

No usar 426 como constante eterna: confirmar el total real cuando
una tarea vuelva a ejecutar la suite.

```text
siguiente paso = revisión de staging / commit local
Push = NO autorizado
```

La historia completa de la etapa (GG-PROMPT-003..011) vive en
`seguimiento_prompts/` y en Git; no se duplica aquí.

## Working tree esperado antes del commit

Último `git status --short` informado por ZCode:

```text
 M AGENTS.md
 M CLAUDE.md
 M TRABAJO_ACTUAL.md
 M ayuda_interfaz.py
 M principal.py
 M pruebas/test_ayuda_tooltips_v1.py
 M pruebas/test_leyenda_estados_git.py
 M servicio_remoto_git.py
?? .zcode/
?? CONTINUIDAD_CHATGPT.md
?? GestorGit_plan_continuidad_y_modo_equipo.md
?? METODO_TRABAJO_AGENTES.md
?? README.md
?? pruebas/test_ayuda_emergente.py
?? pruebas/test_publicar_rama_git.py
?? seguimiento_prompts/
```

`AGENTS.md` y `CLAUDE.md` aparecen modificados por la compactación
documental del orquestador: es ESPERABLE y no es una anomalía.

No interpretar estos cambios documentales como anomalía si coinciden con esta
compactación.

## Archivos funcionales acumulados de la etapa

Cambios de implementación que se esperan antes del commit:

- `servicio_remoto_git.py`
- `principal.py`
- `ayuda_interfaz.py`
- `pruebas/test_publicar_rama_git.py`
- `pruebas/test_ayuda_emergente.py`
- `pruebas/test_ayuda_tooltips_v1.py`
- `pruebas/test_leyenda_estados_git.py`
- `TRABAJO_ACTUAL.md`

Documentación estable candidata a incluir en el commit local de la
etapa (esta clasificación NO autoriza staging por iniciativa del
agente):

- `AGENTS.md`
- `CLAUDE.md`
- `METODO_TRABAJO_AGENTES.md` (documentación estable de
  coordinación: proceso, bitácora y política de tokens; se consulta
  al incorporar un agente, cambiar el método o resolver una duda de
  coordinación)

Documentación de producto actualizada en el cierre y candidata a
incluir en el commit local de la etapa:

- `README.md` (menciona la funcionalidad visible
  `Publicar rama local...`; sin staging por iniciativa del agente:
  el commit requerirá autorización explícita del usuario)

Administrativos/no versionar automáticamente:

- `.zcode/`
- `CONTINUIDAD_CHATGPT.md`
- `seguimiento_prompts/`
- `GestorGit_plan_continuidad_y_modo_equipo.md`

No hacer staging de estos administrativos por iniciativa del agente.

## Reserva actual

No hay un agente programador ejecutando una modificación en este momento.

Siguiente trabajo previsto: prompt separado de COMMIT (revisión de
staging + commit local solo con autorización explícita; Push NO
autorizado).

Si después se abre una nueva tarea de código, el prompt deberá declarar sus
archivos autorizados.

## Deuda técnica fuera del alcance

Existen comprobaciones históricas en Push/Pull relacionadas con texto de
conflicto. No tocarlas por iniciativa propia: la funcionalidad actual tiene
otras defensas y cualquier corrección debe ser una tarea separada.

## Seguridad durante el cierre

Hasta autorización explícita:

- no `git add`;
- no commit;
- no Push;
- no reset/clean;
- no borrar locks;
- no modificar remotos reales.

El repositorio temporal de las pruebas ya no es necesario para el cierre y
puede eliminarse manualmente cuando el usuario quiera.
