# GestorGit

GestorGit es una aplicación de escritorio para Windows, escrita en Python con Tkinter/ttk, orientada a aprender y utilizar Git de forma visual, pedagógica y conservadora, especialmente en contextos de desarrollo Oracle/PLSQL.

La aplicación no pretende ocultar Git: busca enseñar qué sucede en el working tree, el índice/staging, HEAD, las ramas y el remoto mientras el usuario realiza operaciones reales.

## Filosofía

```text
ver cambios
   ↓
comprender el estado
   ↓
preparar
   ↓
commit local
   ↓
Fetch
   ↓
Pull si hace falta y es seguro
   ↓
Push cuando corresponda
```

Ante incertidumbre, GestorGit debe bloquear la operación y explicar el motivo antes que ejecutar una acción potencialmente destructiva.

## Tecnologías

- Python 3.11.x
- Tkinter / ttk
- Git real mediante `subprocess`
- biblioteca estándar de Python
- Windows
- Git Credential Manager para autenticación HTTPS

No utiliza GitPython ni `shell=True`.

## Funcionalidades actuales

### Repositorio y estado local

- seleccionar un repositorio Git;
- recordar el último repositorio usado;
- mostrar rama actual;
- mostrar remoto/upstream;
- detectar si el repositorio tiene commits;
- listar archivos modificados, nuevos, eliminados, preparados o en conflicto;
- mostrar commits por enviar y por descargar según la información remota conocida localmente.

### Staging

- preparar archivos seleccionados;
- quitar archivos de preparados;
- actualizar archivos que fueron preparados y luego modificados otra vez;
- revalidar el estado antes de ejecutar operaciones productivas;
- tratar conflictos Git como estado especial.

### Commit local

- crear commits locales desde la interfaz;
- validar mensaje e identidad Git;
- bloquear commits cuando existen conflictos;
- bloquear commits cuando hay preparados desactualizados.

### Fetch

- consultar el remoto con `git fetch --prune`;
- actualizar las referencias remotas conocidas localmente;
- ejecutar la operación en hilo secundario para mantener la GUI responsiva.

### Pull seguro

- únicamente mediante `git pull --ff-only`;
- sin Merge automático;
- sin Rebase automático;
- bloqueos conservadores ante cambios locales, divergencia, falta de upstream, operaciones Git en curso o `index.lock`.

### Push seguro

- Push con comprobaciones previas;
- sin Force Push;
- exige condiciones seguras antes de publicar;
- protección especial para primer Push y creación de rama remota;
- configuración de upstream cuando corresponde.

### Configuración inicial de GitHub

- configurar el primer remoto `origin`;
- aceptar únicamente URL HTTPS de `github.com`;
- rechazar credenciales embebidas;
- no modificar silenciosamente remotos existentes;
- no almacenar PAT/token.

### Historial

- visualizar commits locales;
- filtros por archivo y fechas;
- orden explícito por fecha descendente;
- exportación CSV;
- exportación TXT;
- detalle de cambios de un commit en modo solo lectura;
- copiar diff al portapapeles.

### Inspector de cambios locales

Permite inspeccionar un archivo diferenciando:

- `Sin preparar`: working tree vs índice (`git diff`);
- `Preparados`: índice vs HEAD (`git diff --cached`).

Incluye:

- resumen de inserciones/eliminaciones;
- soporte de archivos nuevos;
- información del último commit;
- detección estructurada de conflictos;
- diffs seguros sin `ext-diff` ni `textconv`.

### Descartar cambios sin preparar

Acción destructiva controlada y explícita:

```text
git --literal-pathspecs restore --worktree -- <ruta>
```

Restaura desde el índice, por lo que en un estado `MM` conserva lo que ya estaba preparado.

Bloquea:

- archivos `??`;
- conflictos;
- operaciones remotas en curso;
- estados que ya no cumplen las precondiciones.

### Ramas locales V1

Ventana `Ramas locales - Gestor Git` para:

- listar ramas locales;
- identificar la rama actual;
- cambiar de rama con `git switch --no-guess`;
- crear una rama nueva con `git switch -c`;
- validar nombres de rama;
- bloquear cambios de rama con working tree/staging sucio, conflictos, `index.lock`, operaciones Git en curso, repositorio sin commits o HEAD separado.

Una rama nueva queda **LOCAL y sin upstream**.

### Publicar rama local V1

Acción explícita de la ventana de ramas para publicar la rama local ACTUAL:

- requiere un Fetch manual exitoso en la sesión;
- bloquea si la rama ya tiene upstream o si la rama remota homónima ya existe (verificado con `ls-remote --heads` justo antes de publicar);
- Push exacto `git push --porcelain --set-upstream <remoto> <rama>:refs/heads/<rama>`, sin force ni `--all/--tags/--mirror/--delete`;
- tras éxito o fallo se exige un Fetch nuevo;
- puede publicar una rama aunque no tenga commits exclusivos.

### Modo Equipo Oracle V1.1

Capa preventiva de colaboración para desarrollo Oracle/PLSQL que añade reservas de objetos compartidos sin sustituir a Git:

- manifiesto compartido y versionado `.gestorgit/proyecto.json` con `project_uuid` y layout Oracle compartido;
- `project_uuid` inmutable para la ruta del repositorio en V1;
- identidad técnica local `id_cliente` separada de la configuración transportable, en `%APPDATA%\GestorGit\identidad_instalacion.json`;
- backend Git dedicado de reservas con caché bare local por proyecto;
- acciones de reservas explícitas desde la GUI: consultar, reservar, renovar, liberar y tomar vencida;
- sin scheduler ni auto-renovación: staging/commit no reservan, renuevan ni liberan automáticamente;
- staging, actualización de preparados y commit de objetos Oracle reconocidos se protegen de forma fail-closed: con Modo Equipo habilitado exigen una reserva propia activa y verificada y un contexto válido, sin fallback degradante ante contexto inválido o backend no verificable;
- `CoordinadorOperacionesRed` actúa como mutex único compartido por las operaciones remotas Git y las operaciones de reservas;
- avisos pedagógicos cancelables de reservas propias conocidas antes de cambiar/crear rama, Pull, Push, publicar rama y descartar cambios sin preparar (Fetch queda fuera; el aviso es local y no reserva, renueva ni libera).

El layout Oracle se define en el manifiesto del proyecto. V1.1 admite 7 tipos Oracle:

```text
PACKAGE   -> .pls
PROCEDURE -> .sql
FUNCTION  -> .sql
TABLE     -> .sql
VIEW      -> .sql
TRIGGER   -> .sql
SEQUENCE  -> .sql
```

La identidad canónica sigue siendo `TIPO|NOMBRE`. `.pks`/`.pkb`, schemas, `TYPE`, `SYNONYM` y `MATERIALIZED VIEW` siguen fuera de alcance. Las rutas no resolubles de forma inequívoca bloquean la operación protegida con explicación.

### Modo Equipo Oracle V1.2 (validación SQL ↔ archivo)

Segunda evidencia de identidad, conservadora y 100% local (`servicio_validacion_contenido_oracle.py`):

- el contenido `CREATE...` del archivo debe concordar con la identidad `TIPO|NOMBRE` resuelta por la ruta; PACKAGE BODY se normaliza a `PACKAGE|NOMBRE` (un `.pls` con spec+body del mismo nombre se acepta; no habilita `.pks`/`.pkb`);
- Preparar y Actualizar preparados validan el contenido exacto del working tree que se va a stagear; Commit valida el contenido exacto YA PREPARADO en el índice (blob staged, OID revalidado tras la protección — REV1 R3), nunca el working tree (estados MM);
- el detector ignora `CREATE` dentro de comentarios (`--`, `/* */`), literales `'string'` y literales alternativos Oracle `q'...'`/`nq'...'` con cualquier delimitador (REV1 R1: el contenido interno de un q-quote nunca expone CREATE; formas mal cerradas son NO_VERIFICABLE); decodifica con política conservadora (BOM UTF-8, UTF-8, Windows-1252; sin `errors="replace"`);
- gramática positiva de modificadores por tipo (REV1 R2): `EDITIONABLE`/`NONEDITIONABLE` (tipos editables), `FORCE`/`NO FORCE` (solo VIEW), `GLOBAL TEMPORARY` (solo TABLE); combinaciones cruzadas o duplicadas no reconocidas NO verifican (no se inventa identidad); tolera `SCHEMA.OBJETO` comparando solo el objeto;
- resultados estructurados: `COINCIDE`, `NO_COINCIDE_NOMBRE`, `NO_COINCIDE_TIPO`, `AMBIGUO`, `NO_VERIFICABLE`, `NO_APLICA`; las eliminaciones/lados origen reciben `NO_APLICA` de forma EXPLÍCITA (REV1 R4): con validador activo, la ausencia de contenido BLOQUEA (fail-closed), nunca degrada silenciosamente a V1.1;
- fail-closed: contradicción, ambigüedad o contenido no verificable BLOQUEAN la operación protegida con explicación, sin degradar a la protección V1.1;
- la GUI muestra pedagógicamente (en la resolución de la ruta del objeto) la identidad por ruta, la identidad detectada en el SQL y el resultado; no renombra, no mueve ni reescribe nada;
- sigue sin acceso a Oracle: el desarrollador trae manualmente la versión vigente y la guarda con la convención correcta; funciona con archivos nuevos/untracked.

### Tooltips didácticos V1

- 53 tooltips centralizados en la V1 actual
  (38 históricos + 15 de Modo Equipo Oracle V1.1);
- explicaciones de operaciones, conceptos locales/remotos, staging, commit, Fetch, Pull, Push, historial, Inspector, ramas, sincronización y Modo Equipo Oracle;
- sin textos largos dispersos por la GUI.

### Leyenda/Ayuda contextual de estados Git V1

Botón:

```text
¿Qué significan estos estados?
```

Abre una ventana educativa única y no modal que explica:

- HEAD;
- índice/staging;
- working tree;
- `??`;
- `" M"`;
- `"M "`;
- `MM`;
- conflictos `DD AU UD UA DU AA UU`;
- códigos XY;
- otros estados A/D/R;
- relación entre Inspector y acciones de staging.

La ventana no ejecuta Git ni modifica el repositorio.

## Estado validado actual

```text
Publicar rama local V1 -> cerrada
Modo Equipo Oracle V1.1 -> ampliación de tipos Oracle (PROCEDURE, FUNCTION, TABLE, VIEW, TRIGGER, SEQUENCE)
Modo Equipo Oracle V1.2 -> validación de contenido SQL ↔ archivo (implementación auditada y aceptada; pendiente de cierre Git local)
Bloque H (documentación/cierre de la V1) -> documental
```

Modo Equipo Oracle V1 está implementada en bloques incrementales
auditados (modelos/objetos, identidad/configuración, backend local y
remoto de reservas, protección de staging/commit, GUI y avisos
pedagógicos); su cierre documental se realiza en el Bloque H. Las
operaciones Git productivas sobre el repositorio de desarrollo siguen
el modelo conservador ya documentado: el propietario las ejecuta
desde GestorGit y los agentes solo auditan en solo lectura. Push del
repositorio de desarrollo queda pendiente de una decisión/autorización
explícita del propietario.

> Importante: este bloque describe el estado de producto conocido al redactar el README. Antes de trabajar, ejecutar siempre `git status` y `git log -1 --oneline`.

## Próximo paso

La publicación segura de ramas locales y **Modo Equipo Oracle**
ya están implementadas en el producto; la V1 de colaboración de
equipo para desarrollo Oracle/PLSQL está funcionalmente cerrada en
sus bloques A-G (documentada como Bloque H). La V1.1 amplía los
tipos Oracle soportados de 1 a 7 (PACKAGE + 6 tipos .sql).

Las operaciones Git productivas que GestorGit soporta sobre su propio
repositorio (staging, commit, Fetch, Pull/Push seguros y ramas) se realizan
por el usuario desde la propia aplicación, con auditoría de solo lectura de
los agentes antes y después; los agentes no las sustituyen por CLI salvo
excepción declarada de forma explícita. Push del repositorio de desarrollo
no es una acción automática y sigue pendiente de decisión/autorización
explícita del propietario.

El estado de desarrollo vigente (etapa activa, archivos implicados y
siguiente paso interno) se consulta en `TRABAJO_ACTUAL.md` y en Git real.

## Arquitectura principal

### `principal.py`

Interfaz Tkinter y coordinación entre servicios.

### `servicio_git.py`

Operaciones Git locales:

- análisis del repositorio;
- status porcelain;
- staging;
- identidad;
- operaciones Git en curso;
- commit;
- hash actual.

### `servicio_remoto_git.py`

Operaciones remotas:

- Fetch;
- estado de sincronización;
- Push seguro;
- Pull `--ff-only`;
- configuración inicial de GitHub.

### `servicio_ramas_git.py`

Ramas locales:

- listar;
- validar nombres;
- cambiar;
- crear.

No publica ramas ni ejecuta Push.

### Modo Equipo Oracle (reservas)

- `modelos_reservas.py`: modelos, validación y canon del payload V1 de reservas (fórmula de ref, timestamps RFC3339, clasificaciones).
- `servicio_manifiesto_proyecto.py`: lectura del manifiesto compartido versionado `.gestorgit/proyecto.json` (`project_uuid` y layout Oracle).
- `servicio_objetos_oracle.py`: resolución estricta de ruta Oracle a clave de objeto (`TIPO|NOMBRE`); las rutas no resolubles de forma inequívoca no se reservan; V1.1 soporta PACKAGE (.pls) y 6 tipos adicionales (.sql).
- `servicio_identidad_equipo.py`: `id_cliente` técnico local de la instalación (separado de la configuración transportable).
- `servicio_reservas.py`: máquina de estados y orquestación local de reservas (consultar/reservar/renovar/liberar/tomar vencida), validación local de reserva propia fresca y coordinador/mutex de operaciones de red.
- `servicio_remoto_reservas.py`: operaciones Git sobre el backend dedicado de reservas (fetch, lectura/validación de head, commits por plumbing, Push sin force).
- `servicio_proteccion_reservas_git.py`: barrera local fail-closed que exige reserva propia activa y verificada en staging/actualización de preparados/commit de objetos Oracle; con V1.2 exige además la concordancia contenido ↔ identidad cuando hay validador inyectado.
- `servicio_validacion_contenido_oracle.py`: V1.2 — detección conservadora del `CREATE...` declarado en el contenido (fuera de comentarios y literales) y comparación contra la identidad `TIPO|NOMBRE` de la ruta.

### Servicios auxiliares

- historial;
- exportación;
- configuración/persistencia;
- cambios locales;
- descarte seguro.

## Seguridad

Nunca debe implementarse automáticamente:

```text
git reset --hard
git clean -fd
git push --force
git push --force-with-lease
git branch -D
```

También se evita:

- borrar `index.lock` automáticamente;
- resolver conflictos automáticamente;
- Merge automático;
- Rebase automático;
- elegir un remoto al azar;
- guardar tokens/credenciales;
- usar `git add .` en cierres controlados.

## Pruebas

El proyecto usa `unittest`.

Validación habitual:

```powershell
python -m unittest discover -s .\pruebas -v
git diff --check
git diff --cached --check
git diff --stat
git status --short
```

Último cierre funcional certificado:

```text
Ran 1061 tests ...
OK
```

Este número es la evidencia histórica del último cierre funcional
certificado (árbol del Bloque G de Modo Equipo Oracle V1), no un total
fijo que futuros cambios deban exigir sin ejecutar la suite: el total
vigente se confirma por ejecución.

## Documentación para agentes

Claude Code:

- `CLAUDE.md`
- `TRABAJO_ACTUAL.md`
- Git real (`git status`, `git log`, staging, ramas)

ZCode / OpenCode / otros agentes compatibles:

- `AGENTS.md`
- `TRABAJO_ACTUAL.md`
- Git real (`git status`, `git log`, staging, ramas)

No leer `AGENTS.md` y `CLAUDE.md` a la vez por defecto.
`METODO_TRABAJO_AGENTES.md` es documentación estable de coordinación y se
consulta al incorporar un agente, cambiar el método o resolver una duda de
coordinación. La guía de onboarding para el propietario del proyecto
(humano) es `GUIA_TRABAJO_CON_AGENTES.md`.

## Seguimiento de prompts

A partir del 21/08/2026 los prompts operativos importantes se numeran:

```text
GG-PROMPT-001
GG-PROMPT-002
...
```

El usuario guarda los archivos en `seguimiento_prompts/` y ChatGPT genera los prompts y revisa los resultados.

## Estado del producto

GestorGit ya es un cliente Git educativo y conservador funcional para trabajo individual, incluyendo la publicación explícita y segura de ramas locales.

Además del flujo individual, GestorGit incorpora **Modo Equipo Oracle**: reservas preventivas de objetos Oracle con backend Git dedicado, protección fail-closed de staging/commit y avisos pedagógicos, manteniendo la filosofía de seguridad y comprensión. V1.1 soporta 7 tipos Oracle (PACKAGE, PROCEDURE, FUNCTION, TABLE, VIEW, TRIGGER, SEQUENCE). La V1.2 añade la validación de contenido SQL ↔ archivo (el `CREATE...` declarado debe concordar con la identidad de la ruta) para Preparar, Actualizar preparados y Commit.
