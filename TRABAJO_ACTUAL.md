# TRABAJO_ACTUAL.md

## Propósito

Estado dinámico y compacto del trabajo ACTUAL de GestorGit.

Todo agente debe leer este archivo después de su archivo de configuración
(`AGENTS.md` o `CLAUDE.md`).

Para historia detallada usar Git y `seguimiento_prompts/`; NO cargarla por
defecto.

## Fuente de verdad

Git real manda siempre.

Último HEAD observado durante GG-PROMPT-039 (Bloque E):

```text
b0c2bbb Implementa backend remoto de reservas de Modo Equipo Oracle
```

Snapshot auditado:

```text
HEAD base observado -> b0c2bbb Implementa backend remoto de reservas de Modo Equipo Oracle
rama -> master
staging -> vacío
.git/index.lock: inexistente
Push -> NO autorizado
```

Cierre Git A+B+C:

```text
commit -> 971dbd4 Agrega base de reservas de Modo Equipo Oracle V1
padre -> f4ac293
rutas en commit -> 16/16 exactas
staging postcommit -> vacío
working tree funcional -> limpio
GG-PROMPT-031 -> auditoría pre-staging A+B+C ACEPTADA
GG-PROMPT-032 -> staged set exacto ACEPTADO
GG-PROMPT-033 -> auditoría postcommit ACEPTADA
```

Estos datos son un snapshot; verificar Git de nuevo al iniciar cada tarea.

## Etapa actual

```text
Publicar rama local V1 -> CERRADA
Método/onboarding -> CERRADO Y AUDITADO
Modo Equipo Oracle V1 / arquitectura -> CERRADA Y APROBADA
Bloque A -> CERRADO Y COMMITTEADO
Bloque B -> CERRADO Y COMMITTEADO
Bloque C -> CERRADO Y COMMITTEADO
Bloque D -> CERRADO Y COMMITTEADO (b0c2bbb)
Bloque E -> CERRADO Y COMMITTEADO (0d8042d)
Bloque F -> CERRADO Y COMMITTEADO (b547fae)
Bloque G -> IMPLEMENTADO, PENDIENTE DE AUDITORÍA CHATGPT
Bloque H -> NO iniciado
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
GG-PROMPT-030 -> cierre documental recuperación 026 aceptado
GG-PROMPT-031 -> auditoría pre-staging A+B+C ACEPTADA
GG-PROMPT-032 -> staged set exacto A+B+C ACEPTADO
GG-PROMPT-033 -> auditoría postcommit A+B+C ACEPTADA
commit -> 971dbd4 Agrega base de reservas de Modo Equipo Oracle V1
```

A+B+C CERRADOS Y COMMITTEADOS en 971dbd4.

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

## Resultado Bloque D (resumen, CERRADO Y COMMITTEADO en b0c2bbb)

Implementado sobre el working tree (SIN commit; HEAD base c3d5903).

Archivos del Bloque D:

```text
creados -> servicio_remoto_reservas.py
           servicio_reservas.py
           pruebas/test_servicio_remoto_reservas.py
           pruebas/test_servicio_reservas.py
modificados -> modelos_reservas.py
               pruebas/test_modelos_reservas.py
               METODO_TRABAJO_AGENTES.md (ADDENDUM-1)
               GUIA_TRABAJO_CON_AGENTES.md (ADDENDUM-1)
```

APIs principales:

```text
modelos_reservas: ClasificacionReservaObservada,
    EstadoReservaPersistido, ReservaPayloadV1, validar_payload_reserva,
    calcular_ref_reserva (sha256(project_uuid + "\0" + clave),
    sin truncar), parsear/formatear_timestamp_utc (RFC3339 V1 exacto)
ServicioRemotoReservas: fetch_reservas (refspec V1), leer_head_reserva,
    crear_commit_reserva (validación fail-safe ANTES de hash-object),
    publicar_reserva (Push normal, sin force)
ServicioReservas: consultar_reserva, reservar, renovar, liberar,
    tomar_vencida (las cuatro con operation_id opcional e
    idempotencia), validar_reserva_propia_fresca (100% local),
    debe_renovar; CoordinadorOperacionesRed (mutex atómico
    threading.Lock)
```

Correcciones REV3 aplicadas sobre el trabajo heredado: fórmula SHA-256
exacta con separador NUL, TTL reutilizado de modelos_configuracion
(sin 1800 mágico), validación fail-safe del payload antes del primer
comando Git de escritura, mutex con concurrencia real (hilos +
Barrier), idempotencia por operation_id reconocida en reintentos de
las cuatro operaciones (payload incompatible -> NO_VERIFICABLE),
aislamiento Git de tests desde antes del primer git init
(GIT_CONFIG_GLOBAL temporal + GIT_CONFIG_NOSYSTEM=1), RFC3339
estricto y docstring de modelos actualizado.

Validaciones ejecutadas (totales reales):

```text
py_compile focalizado -> OK
focal modelos -> 59/59 OK
focal remoto -> 35/35 OK
focal máquina/mutex -> 49/49 OK
focal D conjunta -> 143/143 OK
regresión A -> 182/182 OK
regresión B -> 106/106 OK
regresión C -> 56/56 OK
suite completa -> 846/846 OK
git diff --check / --cached --check -> limpios
staging -> vacío
```

Pruebas del Bloque D: 118 nuevas (728 previas + 118 = 846).

## Evidencia técnica del commit A+B+C (971dbd4)

Última validación real aplicable al contenido del commit, ejecutada en
GG-PROMPT-031 sobre el mismo árbol (sin cambios de contenido posteriores):

```text
py_compile A+B+C -> OK
Bloque A -> 148/148 OK
Bloque B -> 106/106 OK
Bloque C -> 56/56 OK
suite completa -> 728/728 OK
```

No son constantes eternas: confirmar la suite real en cada nueva
implementación.

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

## Resultado Bloque E (resumen, CERRADO Y COMMITTEADO en 0d8042d)

Implementado sobre el working tree (SIN commit; HEAD base b0c2bbb).

Archivos del Bloque E:

```text
creados -> servicio_proteccion_reservas_git.py
           pruebas/test_servicio_proteccion_reservas_git.py
modificados -> servicio_git.py
               pruebas/test_servicio_git.py
               TRABAJO_ACTUAL.md
```

Arquitectura:

```text
capa nueva -> ServicioProteccionReservasGit (sin Tkinter, sin Git
              propio, 100% local): rutas -> ServicioObjetosOracle
              (inyectado) -> validar_reserva_propia_fresca()
              (única API de Bloque D usada) -> PERMITIR/BLOQUEAR
staging protegido -> agregar_archivos y actualizar_archivos_preparados
              exigen protección ANTES del primer git add; renames
              incluyen el lado origen vía ruta_anterior; unstaging
              conserva comportamiento histórico
commit revalidado -> crear_commit lee el staged set REAL
              (git diff --cached --name-status -z -C
              --find-copies-harder, parser fail-safe A/M/D/T +
              R/C con ambas rutas), valida reservas y relee el
              staged set; si cambió, BLOQUEAR y pedir reintento
ejecutor público -> con protector, GRAMÁTICA POSITIVA POR
              COMANDO/CALL SITE con default deny; diff ->
              familias positivas exactas (staged set exacto de
              _leer_staged_set; vista de UNA ruta con
              --no-ext-diff/--no-textconv obligatorios), las
              formas patch exigen --no-ext-diff/--no-textconv y
              cualquier variante no reconocida BLOQUEA
              (aliases y --output/--ext-diff/--textconv
              incluidos)
copy en staging -> origen detectado ANTES del primer write con
              ls-tree -r -z HEAD + hash-object sin -w (solo
              lectura); copy inequívoca exige ambas reservas,
              copy ambigua o no determinable BLOQUEA
integración -> por inyección opcional (protector_reservas=None
              conserva el comportamiento histórico; Bloque F
              conectará la GUI)
```

Correcciones REV1 aplicadas (sobre la base 039, sin reiniciar):
ejecutor interno para escritores productivos, detección deliberada
de copies en commit, fail-safe estricto de resultados
(ResultadoValidacionReservaPropia con valida EXACTAMENTE True) y
barreras de mensajes sin excepción cruda. Fixtures montan estado
con servicio SIN protector.

Correcciones REV4 aplicadas (sobre REV3, sin reiniciar): gramática
diff cerrada en DOS FAMILIAS positivas exactas — staged set exacto
(--cached --name-status -z -C --find-copies-harder, sin rutas) y
vista de UNA ruta (--no-ext-diff/--no-textconv obligatorios;
--no-color --unified=3 o --numstat según call sites reales;
--numstat y --unified=3 no coexisten). Formas parciales como
diff/diff --cached/diff --unified=3 quedan bloqueadas; test REAL
con diff.external (helper sh + marcador) demuestra que el helper
se ejecuta sin protector y NO se ejecuta en las formas seguras ni
en las bloqueadas. Copy y protector intactos. Convención CRLF
homogénea preservada; 0 whitespace real añadido.

Validaciones ejecutadas (totales reales):

```text
py_compile focalizado -> OK
focal E conjunta -> 141/141 OK (35 protección + 106 servicio_git)
regresión D -> 143/143 OK
suite completa -> 953/953 OK
staging -> vacío
```

Pruebas del Bloque E: 107 nuevas (846 previas + 107 = 953).

## Resultado Bloque F (resumen, CERRADO Y COMMITTEADO en b547fae)

Implementado sobre el working tree (HEAD base 0d8042d) y committeado
posteriormente por el propietario desde GestorGit:

```text
commit -> b547fae2948982faca9ec19e17ee3812c132b515
mensaje -> Integra Modo Equipo Oracle en la interfaz
auditorías -> 043 precommit ACEPTADA (6 SHA-256 exactos)
```
Integración GUI del Modo Equipo Oracle V1 en principal.py, sin
tocar los servicios D/E ni ayuda_interfaz.py.

```text
creados -> pruebas/test_modo_equipo_gui.py
modificados -> principal.py
               pruebas/test_ayuda_tooltips_v1.py (total 38+15 F)
               pruebas/test_leyenda_estados_git.py (ídem)
               pruebas/test_ayuda_emergente.py (ídem, misma regla
               de preservar 38 históricas)
               TRABAJO_ACTUAL.md
```

Arquitectura aplicada:

```text
estado Modo Equipo -> no_cargada / deshabilitado / bloqueado /
              listo (config.json + contexto por repositorio)
selector fail-closed -> Preparar / Actualizar preparados / Commit
              pasan por _resolver_servicio_escrituras: deshabilitado
              -> servicio histórico; listo -> servicio Git PROTEGIDO
              (ServicioRemotoGit con protector E, instancia SEPARADA,
              nunca mutando self.servicio_git); contexto inválido o
              config corrupta -> BLOQUEO sin fallback
contexto -> identidad (id_cliente) + manifiesto HEAD + project_uuid
              INMUTABLE por ruta + resolvedor + backend local (sin
              red) + ServicioReservas + protector
mutex único -> CoordinadorOperacionesRed compartido por reservas y
              Fetch/Pull/Push/Publicar (adquisición antes del hilo,
              liberación al procesar el resultado aunque sea obsoleto)
reservas GUI -> ventana Toplevel no modal con configuración, estado
              y acciones explícitas Consultar/Reservar/Renovar/
              Liberar/Tomar vencida; clave SIEMPRE vía
              ServicioObjetosOracle; worker Thread -> queue ->
              after, sin tocar Tkinter; resultados obsoletos por
              repo/project_uuid se ignoran
ayudas -> 15 claves "modo_equipo_*" nuevas en TEXTOS_AYUDA_GIT_V1
              (cada una conectada 1 vez); 38 históricas preservadas
automatismos -> cero: staging/commit no llaman red/reservas; sin
              scheduler ni auto-renovación
```

Validaciones ejecutadas (totales reales):

```text
py_compile focalizado -> OK
focal GUI F conjunta -> 301/301 OK
  (modo_equipo_gui 44 + commit_gui_conflicto 1 +
   publicar_rama_git 70 + ayuda_tooltips_v1 121 +
   leyenda_estados_git 65)
ayuda_emergente -> 10/10 OK
regresión D/E -> 284/284 OK
suite completa -> 1000/1000 OK
git diff --check -> 0 avisos reales
staging -> vacío
```

Pruebas del Bloque F: 47 nuevas (953 previas + 47 = 1000).

Correcciones REV1 aplicadas (sobre 042, sin reiniciar): B1 —
import faltante de ServicioIdentidadEquipo corregido y prueba
AST de arranque (__init__ sin globales sin resolver); B2 —
firma de configuración efectiva (url/alias/ttl/renovación/
margen/frescura/grace): el contexto solo se reutiliza si ruta +
project_uuid + firma coinciden; cambiar alias o backend URL
reconstruye localmente ServicioReservas/protector/servicio Git
protegido; fallo de reconstrucción -> bloqueado/fail-closed sin
fallback; firma reseteada al limpiar contexto; B3 — test del
mutex con hilo FALSO (sin hilos reales descontrolados, cero
"Exception in thread", cero traceback asíncrono). Verificación
de la focal limpia de stderr asíncrono.

Validaciones REV1 (totales reales):

```text
py_compile -> OK
focal REV1 (test_modo_equipo_gui) -> 51/51 OK
focal GUI F conjunta -> 318/318 OK
regresión D/E -> 284/284 OK
suite completa -> 1007/1007 OK
git diff --check -> 0 avisos reales
staging -> vacío
```

## Resultado Bloque G (resumen, IMPLEMENTADO, PENDIENTE DE AUDITORÍA CHATGPT)

Implementado sobre el working tree (SIN commit; HEAD base b547fae).
Aviso pedagógico cancelable de reservas propias activas conocidas
antes de cambiar/crear rama, Pull, Push, publicar rama y descartar
cambios sin preparar. Fetch NO entra. Staging/commit/Quitar siguen
con las barreras E/F intactas.

```text
modificados -> servicio_reservas.py
              principal.py
              pruebas/test_servicio_reservas.py
              pruebas/test_modo_equipo_gui.py
              TRABAJO_ACTUAL.md
```

Arquitectura aplicada (diseño GG-PROMPT-045 ACEPTADO, precisiones
R1-R4):

```text
API local -> ServicioReservas.listar_reservas_propias_conocidas(
              project_uuid): 100% local, sin red, sin mutex, sin
              efectos secundarios; devuelve tupla de snapshots
              congelados ReservaPropiaConocida (project_uuid,
              clave_objeto, vencimiento, alias) ordenada por
              clave_objeto; NO expone _cache ni el payload
              almacenado; filtrado por project_uuid (R1)
criterio -> clasificacion RESERVADO_POR_MI + es_activa() +
              id_cliente propio + project_uuid solicitado +
              vencimiento parseable y no alcanzado; NO exige
              frescura/margen de staging/commit (R3)
fail-safe -> entrada defectuosa se ignora sin eliminar las demás;
              fallo global -> colección vacía; el aviso nunca es
              barrera de la operación Git
helper GUI -> _confirmar_aviso_reservas_propias(parent): refresca
              el contexto con el mecanismo F, exige estado listo +
              servicio_reservas + project_uuid_activo VIGENTES
              (nunca referencia anterior), llama la API local y
              muestra askyesno pedagógico; sin Modo Equipo listo
              o ante fallo informativo -> sin aviso y flujo
              histórico (True) (R4)
inserciones -> cambiar rama, crear rama, Pull, Push, publicar rama
              y descarte sin preparar: tras las validaciones
              históricas y ANTES de la confirmación histórica; en
              remotas siempre ANTES de adquirir el mutex de red;
              cancelar aborta la operación sin ejecutarla; los
              servicios Git especializados siguen agnósticos
texto -> N reservas conocidas en esta sesión + lista
              clave/vencimiento (máx. 5 + "... y N más") + no
              libera ni renueva + continuar no equivale a liberar
              + cancelar y gestionar desde Modo Equipo; sin
              depender de rama_local ni rutas (R2)
```

Pruebas del Bloque G: 54 nuevas (20 servicio + 34 GUI;
1007 previas + 54 = 1061).

Validaciones ejecutadas (totales reales):

```text
py_compile -> OK (4 archivos modificados)
focal servicio_reservas -> 69/69 OK (49 previas + 20)
focal modo_equipo_gui -> 85/85 OK (51 previas + 34)
"Exception in thread" / Traceback en focal GUI -> 0
regresión D/E/F -> 375/375 OK
suite completa -> 1061/1061 OK
git diff --check -> limpio
staging -> vacío
```

## Próximo paso

```text
AUDITORÍA CHATGPT GG-PROMPT-046 (BLOQUE G)
```

Bloque G está IMPLEMENTADO y validado técnicamente en el working
tree; NO está aceptado ni cerrado hasta la auditoría ChatGPT.
Después de F, el siguiente paso natural es la auditoría y, si
procede, el commit del Bloque G. Bloque H sigue NO iniciado.
Staging/commit solo con autorización expresa del propietario y
ejecutados por el propietario desde GestorGit.

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
