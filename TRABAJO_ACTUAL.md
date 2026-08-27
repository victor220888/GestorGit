# TRABAJO_ACTUAL.md

## Propósito

Estado dinámico y compacto del trabajo ACTUAL de GestorGit.

Todo agente debe leer este archivo después de su archivo de configuración
(`AGENTS.md` o `CLAUDE.md`).

Para historia detallada usar Git y `seguimiento_prompts/`; NO cargarla por
defecto.

## Fuente de verdad

Git real manda siempre.

Último HEAD observado durante la auditoría final de GG-PROMPT-027-REV2:

```text
f4ac293 Cierra estado postcommit y actualiza onboarding de agentes
```

Snapshot auditado:

```text
rama: master
ahead: 11 respecto de origin/master
staging: vacío
.git/index.lock: inexistente
Push: NO autorizado
```

Cambios de implementación actualmente no comprometidos (Bloques A+B+C):

```text
 M modelos_configuracion.py
 M servicio_configuracion.py
 M pruebas/test_configuracion.py

?? modelos_reservas.py
?? servicio_manifiesto_proyecto.py
?? servicio_objetos_oracle.py
?? pruebas/test_modelos_reservas.py
?? pruebas/test_servicio_manifiesto_proyecto.py
?? pruebas/test_servicio_objetos_oracle.py

?? servicio_identidad_equipo.py
?? pruebas/test_servicio_identidad_equipo.py
?? pruebas/test_configuracion_modo_equipo.py

?? modelos_backend_reservas.py
?? servicio_backend_reservas.py
?? pruebas/test_servicio_backend_reservas.py
```

Estos datos son un snapshot; verificar Git de nuevo al iniciar cada tarea.

## Etapa actual

```text
Publicar rama local V1 -> CERRADA
Método/onboarding -> CERRADO Y AUDITADO
Modo Equipo Oracle V1 / arquitectura -> CERRADA Y APROBADA
Bloque A -> CERRADO
Bloque B -> CERRADO
Bloque C -> CERRADO TÉCNICAMENTE
Bloque D -> NO INICIADO
Push -> NO autorizado
```

Cierres registrados:

```text
GG-PROMPT-024-REV3 -> arquitectura Modo Equipo Oracle V1 aprobada
GG-PROMPT-025-REV1 -> Bloque A cerrado
GG-PROMPT-026-REV2 -> Bloque B cerrado
GG-PROMPT-027-REV2 -> Bloque C cerrado técnicamente
GG-PROMPT-028 -> cierre documental POST-027 aceptado
GG-PROMPT-029 -> auditoría de evidencias 026-REV2 aceptada
```

Los Bloques A+B+C continúan SIN COMMIT mientras Git lo confirme.

## Resultado final Bloque B (resumen)

Identidad técnica local `%APPDATA%\GestorGit\identidad_instalacion.json`
(format_version 1, id_cliente UUID4 canónico; la identidad corrupta no se
regenera automáticamente). Configuración local de equipo conserva claves
desconocidas y usa valores canónicos (TTL 1800 s, renovación 600 s, margen
mínimo 300 s, frescura 60 s, grace 600 s). `backend_reservas_url` sin
credenciales embebidas y solo HTTP/HTTPS sintácticamente válidos en V1. No
se realiza red en este bloque.

## Resultado final Bloque C (resumen)

Backend local Git bare de reservas:

```text
%APPDATA%\GestorGit\reservas\<project_uuid>\backend.git
origin -> backend_reservas_url
refspec -> +refs/heads/gestorgit-reservas/*:refs/remotes/origin/gestorgit-reservas/*
```

Invariantes de seguridad auditadas (REV1 + REV2): contención canónica de
ruta dentro de la base (H1), consulta fail-safe de remotes sin ambigüedad
(H2) y unicidad efectiva del destino de Push con
`git remote get-url --push --all origin` == [backend_reservas_url] (H3).
Cero red, cero Git global/system, cero dependencia de ServicioGit.

## Evidencia auditada del cierre 027

Registrada del resultado auditado `GG-PROMPT-027-REV2-RESULTADO.md` (no
re-ejecutada por este cierre documental):

```text
focal Bloque C -> 56/56 OK
regresión A    -> 148/148 OK
regresión B    -> 106/106 OK
suite completa -> 728/728 OK
py_compile     -> OK
git diff --check -> OK
H1/H2/H3       -> ACEPTADOS

## Evidencia histórica diferenciada

```text
POST-026 -> focal B 106 / regresión A 148 / suite 672
POST-027 -> focal C 56 / regresión A 148 / regresión B 106 / suite 728
```

Evidencia histórica documentada de los cierres previos; no son
constantes eternas: confirmar la suite real en cada nueva
implementación.
```

## Trazabilidad 026-REV2 (resuelta documentalmente)

`GG-PROMPT-026-REV2-RESULTADO.md` está PRESENTE como RECONSTRUCCIÓN
DOCUMENTAL POSTERIOR (generada por ChatGPT tras `GG-PROMPT-029`
ACEPTADO). NO es el archivo original: el original nunca estuvo
versionado por Git y no es recuperable byte a byte. La anomalía
física quedó resuelta documentalmente, preservando la limitación
histórica.

## Método vigente

Las operaciones Git PRODUCTIVAS soportadas por GestorGit las ejecuta
normalmente el USUARIO desde GestorGit:

```text
agente/ChatGPT audita -> usuario ejecuta en GestorGit -> agente/ChatGPT audita
```

Agentes y ChatGPT pueden realizar consultas Git de solo lectura.

Ninguna autorización anterior se hereda automáticamente a una tarea nueva.

## Administrativos fuera del versionado

Conocidos:

```text
.zcode/
CONTINUIDAD_CHATGPT.md
seguimiento_prompts/
GestorGit_plan_continuidad_y_modo_equipo.md
```

## Próximo paso

```text
AUDITORÍA PRE-STAGING A+B+C
```

Siguiente operación: auditoría previa de solo lectura del conjunto
A+B+C antes de cualquier cierre Git. Bloque D sigue NO INICIADO y no
se anuncia todavía un ID funcional para él. Staging/commit solo con
autorización expresa del propietario y ejecutados por el propietario
desde GestorGit.

## Seguridad

Hasta una autorización/tarea explícita:

- no `git add` ni staging por CLI;
- no commit;
- no Fetch/Pull/Push;
- no Merge/Rebase;
- no reset/clean;
- no force;
- no borrar locks;
- no modificar remotos reales;
- no modificar el repositorio Oracle productivo;
- ante incertidumbre material: BLOQUEAR Y EXPLICAR.
