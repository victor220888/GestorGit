# TRABAJO_ACTUAL.md

## Propósito

Estado dinámico y compacto del trabajo ACTUAL de GestorGit.

Todo agente debe leer este archivo después de su archivo de configuración
(`AGENTS.md` o `CLAUDE.md`).

Para historia detallada usar Git y `seguimiento_prompts/`; NO cargarla por
defecto.

## Fuente de verdad

Git real manda siempre.

Snapshot de inicio de GG-PROMPT-055:

```text
HEAD -> e706061 Amplía tipos Oracle en Modo Equipo V1.1
HEAD completo -> e7060619c3f8d37fc735a30104300f3c435edb7e
rama -> master
staging -> vacío
.git/index.lock: inexistente
ahead -> 19 respecto de origin/master local conocido
Push -> NO autorizado
```

Estos datos son un snapshot; verificar Git de nuevo al iniciar cada tarea.

## Etapa actual

```text
Publicar rama local V1 -> CERRADA
Método/onboarding -> CERRADO Y AUDITADO
Modo Equipo Oracle V1 -> CERRADA Y COMMITTEADA (Bloque H: commit 3b06617)
Modo Equipo Oracle V1.1 -> CERRADA Y COMMITTEADA (commit e706061)
GG-PROMPT-053 -> ACEPTADO CON REV1
GG-PROMPT-053-REV1 -> ACEPTADO
GG-PROMPT-053-REV1-ADDENDUM-1 -> ACEPTADO
GG-PROMPT-054 -> CIERRE GIT INTEGRAL V1.1, ACEPTADO (commit e706061)
GG-PROMPT-055 -> ACEPTADO CON REV2
GG-PROMPT-055-REV1 -> NO ACEPTADO; corregido por REV2
GG-PROMPT-055-REV2 -> ACEPTADO
Modo Equipo Oracle V1.2 -> IMPLEMENTACIÓN ACEPTADA; PENDIENTE CIERRE GIT
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

Cierres registrados D-H:

```text
D -> commit b0c2bbb + auditoría postcommit 038 ACEPTADA
E -> commit 0d8042d + auditoría postcommit 041 ACEPTADA
F -> commit b547fae + auditoría postcommit 044 ACEPTADA
G -> GG-PROMPT-046-REV1 ACEPTADO + 047 ACEPTADO + 048 ACEPTADO
     + commit d1b2ed3
GG-PROMPT-049 -> análisis del Bloque H ACEPTADO
GG-PROMPT-050-REV2 -> ACEPTADO
GG-PROMPT-050 -> ACEPTADO CON REV2; Bloque H documental aceptado
GG-PROMPT-051 -> actualización post-aceptación de 050 ACEPTADO
GG-PROMPT-052 -> cierre Git del Bloque H ACEPTADO EN RECUPERACIÓN POSTCOMMIT
             commit -> 3b06617 Cierra documentación de Modo Equipo Oracle V1
GG-PROMPT-053 -> ACEPTADO CON REV1
GG-PROMPT-053-REV1 -> ACEPTADO
GG-PROMPT-053-REV1-ADDENDUM-1 -> ACEPTADO
GG-PROMPT-054 -> ACEPTADO; V1.1 CERRADO Y COMMITTEADO en e706061
```

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

Correcciones REV3 consolidadas: fórmula SHA-256 exacta con separador
NUL, TTL reutilizado de modelos_configuracion, validación fail-safe
del payload antes del primer comando Git de escritura, mutex con
concurrencia real (hilos + Barrier), idempotencia por operation_id
en las cuatro operaciones (payload incompatible -> NO_VERIFICABLE),
aislamiento Git de tests (GIT_CONFIG_GLOBAL temporal +
GIT_CONFIG_NOSYSTEM=1) y RFC3339 estricto.

Evidencia histórica del cierre (no constantes futuras):

```text
focal D conjunta -> 143/143 OK (modelos 59 + remoto 35 + máquina 49)
regresiones A/B/C -> 182/182, 106/106, 56/56 OK
suite completa -> 846/846 OK (728 previas + 118 nuevas)
commit -> b0c2bbb con auditorías 037/038 precommit/postcommit ACEPTADAS
```

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

Correcciones REV1/REV4 consolidadas: ejecutor interno para
escritores productivos, detección deliberada de copies en commit,
fail-safe estricto de resultados (valida EXACTAMENTE True) y
gramática diff cerrada en DOS FAMILIAS positivas exactas (staged
set exacto; vista de UNA ruta con --no-ext-diff/--no-textconv
obligatorios), con test REAL diff.external que demuestra el
bloqueo de formas no reconocidas. Copy y protector intactos;
convención CRLF homogénea preservada.

Evidencia histórica del cierre (no constantes futuras):

```text
focal E conjunta -> 141/141 OK (35 protección + 106 servicio_git)
regresión D -> 143/143 OK
suite completa -> 953/953 OK (846 previas + 107 nuevas)
commit -> 0d8042d con auditorías 040/041 precommit/postcommit ACEPTADAS
```

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

Pruebas del Bloque F: 47 nuevas (953 previas + 47 = 1000).

Correcciones REV1 consolidadas: B1 — import de
ServicioIdentidadEquipo corregido con prueba AST de arranque;
B2 — firma de configuración efectiva (8 dimensiones: url/alias/ttl/
renovación/margen/frescura/grace + habilitado): el contexto solo se
reutiliza si ruta + project_uuid + firma coinciden; cambiar alias o
backend URL reconstruye localmente ServicioReservas/protector/
servicio Git protegido y un fallo de reconstrucción es fail-closed
sin fallback; B3 — test del mutex con hilo FALSO (cero
"Exception in thread" y cero traceback asíncrono).

Evidencia histórica del cierre (no constantes futuras):

```text
focal REV1 (test_modo_equipo_gui) -> 51/51 OK
focal GUI F conjunta -> 318/318 OK
regresión D/E -> 284/284 OK
suite completa -> 1007/1007 OK (953 previas + pruebas F y REV1)
commit -> b547fae con auditorías 043/044 precommit/postcommit ACEPTADAS
```

## Resultado Bloque G (resumen, CERRADO Y COMMITTEADO en d1b2ed3)

Aviso pedagógico cancelable de reservas propias activas conocidas
antes de cambiar/crear rama, Pull, Push, publicar rama y descartar
cambios sin preparar. Fetch NO entra. Staging/commit/Quitar siguen
con las barreras E/F intactas.

```text
commit -> d1b2ed36ffb8745b2fe412a52a239e94823199c1
mensaje -> Advierte sobre reservas antes de operaciones Git
auditorías -> 047 precommit ACEPTADA + 048 postcommit ACEPTADA
```

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

Evidencia histórica del cierre (no constantes futuras):

```text
focal servicio_reservas -> 69/69 OK (49 previas + 20)
focal GUI -> 85/85 OK (51 previas + 34)
focal conjunta precommit -> 154/154 OK
"Exception in thread" / Traceback en focal GUI -> 0
regresión D/E/F -> 375/375 OK
suite completa heredada del árbol certificado -> 1061/1061 OK
commit -> d1b2ed36ffb8745b2fe412a52a239e94823199c1
```

## Resultado V1.2 (resumen, GG-PROMPT-055, ACEPTADO CON REV2)

Segunda evidencia de identidad para operaciones protegidas: el contenido
`CREATE...` del archivo debe concordar con la identidad `TIPO|NOMBRE`
resuelta por la ruta. Sin acceso a Oracle y sin cambios de catálogo
(V1.1 intacto: 7 tipos, `TIPO|NOMBRE` canónico).

```text
creados -> servicio_validacion_contenido_oracle.py
           pruebas/test_servicio_validacion_contenido_oracle.py
modificados -> servicio_proteccion_reservas_git.py
               servicio_git.py
               principal.py
               pruebas/test_servicio_proteccion_reservas_git.py
               pruebas/test_servicio_git.py
               pruebas/test_modo_equipo_gui.py
               README.md
               TRABAJO_ACTUAL.md
```

Arquitectura aplicada:

```text
validador -> ServicioValidacionContenidoOracle (puro, sin filesystem
              ni Git ni red): detectar(bytes) -> DeteccionContenidoOracle
              y validar(clave, bytes) -> ResultadoValidacionContenido
              con estados COINCIDE / NO_COINCIDE_NOMBRE /
              NO_COINCIDE_TIPO / AMBIGUO / NO_VERIFICABLE / NO_APLICA
léxico -> solo CREATE soportados FUERA de -- , /* */ y 'strings'
              (con escape ''); formas CREATE [OR REPLACE]
              [EDITIONABLE|NONEDITIONABLE], FORCE/NO FORCE (VIEW),
              GLOBAL TEMPORARY (TABLE); PACKAGE BODY -> PACKAGE|nombre
              (spec+body mismo nombre aceptado); SCHEMA.OBJETO
              tolerado comparando solo el objeto; identificadores
              entrecomillados -> NO_VERIFICABLE; cualquier otra
              construcción se ignora sin inventar identidad
decodificación -> BOM UTF-8 -> utf-8-sig estricto; si no, UTF-8
              estricto y luego Windows-1252 estricto; sin
              errors="replace"; UTF-16/NUL/ilegible -> NO_VERIFICABLE
protector -> validador_contenido inyectable (constructor) y
              contenido_por_ruta opcional en proteger_staging/
              proteger_commit; resultado con bloqueo_contenido=True
              y mensaje pedagógico propio; sin validador inyectado
              conserva semántica V1.1 (los dobles históricos de
              pruebas no se rompen)
staging -> Preparar y Actualizar preparados validan los bytes
              EXACTOS del working tree que se van a stagear;
              archivo ausente (eliminación/lado origen) -> NO_APLICA;
              fallo de lectura -> BLOQUEO
commit -> crear_commit valida el blob EXACTO ya preparado en el
              índice (ls-files --stage -z + cat-file blob vía
              ejecutor binario _ejecutar_git_bytes, solo lectura);
              el working tree NO participa; eliminación (D) ->
              NO_APLICA; la barrera histórica MM (pedir Actualizar
              preparados) se conserva ANTES de la validación
GUI -> _resumen_validacion_contenido_objeto compone el resumen
              pedagógico (Ruta / Identidad por ruta / Identidad
              detectada en SQL / Validación) al resolver la clave;
              solo lectura: no renombra, no mueve, no reescribe
              SQL; contexto Modo Equipo se construye solo con
              validador disponible (fail-closed, sin fallback V1.1)
```

Pruebas V1.2: 51 validador + 16 protector + 16 servicio_git + 6 GUI.

Evidencia (no constantes eternas):

```text
py_compile 8 archivos -> OK
focal conjunta 4 módulos -> 333/333 OK
suite completa (discover -s pruebas) -> 1200/1200 OK (~155 s;
              1111 previas + 89 nuevas V1.2)
diff --check -> con convención efímera cr-at-eol: OK (archivos
              históricos CRLF preservados; sin core.whitespace
              persistido)
staging -> vacío
commit V1.2 -> NO
Push -> NO autorizado
```

## Resultado V1.2 REV1 (resumen, GG-PROMPT-055-REV1, NO ACEPTADO; corregido por REV2)

Corrección conservadora de los 4 bloqueos de auditoría, sin ampliar
el alcance funcional de V1.2:

```text
R1 q-quote -> el limpiador léxico reconoce q'...' / Q'...' /
    nq'...' / NQ'...' (delimitadores emparejados [], {}, (), <>
    o simple de un carácter); el contenido interno NUNCA se
    expone al detector de CREATE; formas mal cerradas o
    delimitador no interpretable -> NO_VERIFICABLE (fail-closed,
    sin recuperación parcial); un literal simple sin cerrar
    también pasa a NO_VERIFICABLE (antes consumía el resto)

R2 gramática positiva -> se elimina la bolsa global de
    modificadores; tras CREATE [OR REPLACE] solo se aceptan
    secuencias EXACTAS por tipo: EDITIONABLE/NONEDITIONABLE
    (PACKAGE, PROCEDURE, FUNCTION, TRIGGER, VIEW), FORCE y
    NO FORCE (solo VIEW, incl. EDITIONABLE + [NO] FORCE),
    GLOBAL TEMPORARY (solo TABLE); SEQUENCE sin modificadores;
    combinaciones cruzadas o duplicadas -> sentencia ignorada

R3 revalidación OID -> _proteger_commit_con_relectura conserva
    oids_por_ruta (etapa 0) tras validar contenido y reservas,
    relee el staged set Y los OIDs (_releer_oids_staged) y
    compara AMBOS; un blob diferente con staged set idéntico
    BLOQUEA; prueba ServicioGitStagedOIDInestable demuestra el
    caso

R4 fail-closed del protector -> con validador V1.2 activo:
    contenido_por_ruta=None BLOQUEA (antes significaba V1.1);
    ruta Oracle esperada ausente del mapeo BLOQUEA; None explícito
    en el mapeo = eliminación/lado origen DEMOSTRADO -> NO_APLICA;
    _obtener_contenido_working_tree/_obtener_contenido_staged
    insertan TODAS las rutas Oracle reservables (bytes o None);
    compatibilidad V1.1 SOLO con validador_contenido is None
```

Pruebas REV1 (conteo corregido en REV2): validador 51 -> 70 = +19;
protector 58 -> 59 = +1 neto (2 reemplazados por 3); servicio_git
131 -> 132 = +1; GUI 93 -> 93 = +0; total 1200 -> 1221 = +21 neto.

Evidencia REV1 (no constantes eternas):

```text
py_compile 8 archivos -> OK
focal validador -> 70/70 OK
focal protector -> 59/59 OK
focal servicio_git -> 132/132 OK
focal GUI -> 93/93 OK
suite completa (discover -s pruebas) -> 1221/1221 OK (~147 s;
              1200 previas de 055 + 21 nuevas REV1)
diff --check -> con convención efímera cr-at-eol: OK
staging -> vacío
commit V1.2 -> NO
Push -> NO autorizado
```

## Resultado V1.2 REV2 (resumen, GG-PROMPT-055-REV2, ACEPTADO)

Corrección acotada: los renames/copias que Git representa como R/C
quedan compatibles con la validación V1.2 (R1-R4 sin rediseñar).

```text
defecto -> _obtener_contenido_staged ignoraba ruta_anterior; con R4
    activo el lado origen Oracle quedaba ausente del mapeo y
    BLOQUEABA incorrectamente todo R/C
regla -> para cada entrada staged R/C: destino Oracle -> bytes
    staged + OID (validación SQL ↔ identidad del DESTINO); origen
    Oracle -> None EXPLÍCITO (NO_APLICA de contenido; su reserva
    SIGUE siendo obligatoria vía la ruta involucrada); nunca se
    lee el working tree para suplir el origen; el origen nunca
    entra en oids_por_ruta; si una entrada propia del origen
    aporta contenido real (copia con origen también modificado),
    ese contenido gana sobre el None estructural
docstring -> contrato exacto corregido en el protector:
    contenido_por_ruta is None -> BLOQUEAR; ruta Oracle ausente
    del dict -> BLOQUEAR; dict[ruta] is None -> NO_APLICA
    explícito; dict[ruta] is bytes -> validar
```

Pruebas REV2 (+6 en test_servicio_git, repositorios temporales
REALES con detección R/C afirmada antes de evaluar):

```text
R Oracle->Oracle -> permitido (destino bytes+OID, origen None sin
    OID, reservas de AMBOS lados exigidas)
C Oracle->Oracle -> permitido (mismo contrato)
R Oracle->ordinario -> permitido con reserva del origen
R ordinario->Oracle -> destino valida su contenido staged
R reserva origen inválida -> BLOQUEA por reserva
R SQL destino contradictorio -> BLOQUEA por contenido
R3 preservada -> PruebasCommitRevalidacionOID intacta; el origen
    None no necesita OID
```

Evidencia REV2 (no constantes eternas):

```text
py_compile -> OK
focal conjunta 4 módulos -> 360/360 OK
suite completa -> 1227/1227 OK
staging -> vacío
commit V1.2 -> NO
Push -> NO autorizado
```

## Próximo paso

```text
CIERRE GIT INTEGRAL V1.2 (GG-PROMPT-056)
staging -> vacío
commit V1.2 -> NO
Push -> NO autorizado
```

GG-PROMPT-054 cerró el ciclo Git V1.1: commit e706061 (Amplía tipos Oracle
en Modo Equipo V1.1) con suite 1111/1111 OK. GG-PROMPT-055 implementa la
segunda evidencia de identidad: el contenido CREATE... del archivo debe
coincidir con la identidad TIPO|NOMBRE resuelta por la ruta, para
Preparar, Actualizar preparados y Commit (este último contra el contenido
exacto del índice, no del working tree). GG-PROMPT-055-REV1 cierra
conservadoramente los 4 bloqueos de auditoría: q-quote, gramática
positiva de modificadores, revalidación OID del commit y contrato
fail-closed de contenido ausente.

Catálogo V1.1 (V1.2 no añade tipos):

```text
PACKAGE -> .pls
PROCEDURE/FUNCTION/TABLE/VIEW/TRIGGER/SEQUENCE -> .sql
```

Versionados modificados por 053 + REV1:
  modelos_reservas.py (catálogos)
  servicio_manifiesto_proyecto.py (docstring)
  servicio_objetos_oracle.py (comentario)
  principal.py (textos pedagógicos + tooltips reparados)
  pruebas/test_modelos_reservas.py (especificación exacta V1.1)
  pruebas/test_servicio_manifiesto_proyecto.py
  pruebas/test_servicio_objetos_oracle.py
  pruebas/test_servicio_proteccion_reservas_git.py (integración .sql)
  pruebas/test_servicio_git.py (staging/commit .sql end-to-end)
  pruebas/test_modo_equipo_gui.py (resolución .sql headless)
  pruebas/test_ayuda_tooltips_v1.py (regresiones tooltips V1.1)
  README.md
  TRABAJO_ACTUAL.md
`seguimiento_prompts/README.md` → administrativo, FUERA del commit.

Evidencia real REV1:

```text
py_compile 11 archivos -> OK
focal test_modelos_reservas -> 60/60 OK
focal test_servicio_manifiesto_proyecto -> 72/72 OK
focal test_servicio_objetos_oracle -> 73/73 OK
focal test_servicio_proteccion_reservas_git -> 42/42 OK
focal test_servicio_git -> 115/115 OK
focal test_ayuda_tooltips_v1 -> 130/130 OK
focal test_modo_equipo_gui -> 87/87 OK
suite completa discovery -s pruebas -t . -> 1111/1111 OK (369.5s)
```

Nota EOL: test_servicio_git.py está históricamente versionado en CRLF
en HEAD (convención histórica del archivo); las líneas V1.1 añadidas mantienen
esa convención. Su validación se hizo de forma efímera con
git -c core.whitespace=cr-at-eol; NO queda core.whitespace persistido
en la configuración local.

Staging → vacío. Commit V1.1 → NO realizado. Push → NO autorizado.

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
