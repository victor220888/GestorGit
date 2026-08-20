# CLAUDE.md

## Propósito

Este archivo conserva el contexto técnico y funcional del proyecto **Gestor Git** para que otro agente, asistente o desarrollador pueda continuar el trabajo sin depender del historial del chat.

Actualizar este archivo cada vez que se termine una etapa importante.

## Objetivo del proyecto

Gestor Git es una aplicación de escritorio sencilla, educativa y conservadora para trabajar con Git desde Windows, especialmente durante desarrollo Oracle/PLSQL.

Debe permitir:

- ver el estado de un repositorio;
- detectar archivos nuevos, modificados y eliminados;
- preparar archivos;
- quitar archivos del staging;
- crear commits locales;
- ejecutar Fetch;
- calcular commits por enviar y por descargar;
- hacer Push seguro;
- hacer Pull solo mediante fast-forward;
- enseñar conceptos de Git mediante textos explicativos y tooltips;
- evitar operaciones destructivas o ambiguas;
- mantener la interfaz responsiva durante operaciones de red.

## Entorno

Proyecto:

```text
D:\Mi Tierra - Desarrollos\Herramientas\GestorGit
```

Repositorio Oracle real:

```text
D:\Mi Tierra - Desarrollos\Git\Desarrollo-Mi-Tierra-S.A
```

Entorno virtual:

```text
D:\Mi Tierra - Desarrollos\Herramientas\GestorGit\.venv
```

Tecnologías:

- Windows
- PowerShell
- Python 3.11.5 64-bit
- Git 2.45.2.windows.1
- Tkinter/ttk
- biblioteca estándar de Python

## Convenciones

Mantener siempre:

- comentarios en español;
- variables en español;
- métodos en español;
- clases en español;
- identificadores Python sin tildes;
- interfaz en español;
- código simple;
- biblioteca estándar siempre que sea posible;
- Git real mediante `subprocess`;
- no usar GitPython;
- no usar `shell=True`;
- no guardar tokens ni credenciales;
- delegar HTTPS a Git/Git Credential Manager.

## Arquitectura

### `modelos.py`

Dataclasses actuales:

- `ResultadoComando`
- `EstadoRepositorio`
- `CambioArchivo`
- `ResultadoCambios`
- `EstadoSincronizacion`

### `servicio_git.py`

Operaciones Git locales:

- localizar Git;
- ejecutar comandos;
- validar repositorios;
- obtener rama y remotos;
- leer `status --porcelain`;
- preparar y quitar preparados;
- validar identidad;
- detectar operaciones en curso;
- crear commits;
- obtener hash actual.

### `servicio_remoto_git.py`

Hereda de `ServicioGit`.

Implementa:

- selección segura del remoto;
- Fetch;
- estado de sincronización;
- Push seguro;
- Pull seguro mediante `--ff-only`;
- configuración del primer remoto GitHub (`agregar_remoto_github`).

### `principal.py`

Interfaz Tkinter con:

- selección de repositorio;
- información local;
- tabla de cambios;
- staging;
- commit;
- Fetch;
- Pull;
- Push;
- botón `Configurar GitHub...` (primer remoto origin);
- estado por enviar/por descargar;
- historial con filtros y exportación;
- visor de cambios de un commit (solo lectura);
- inspector de cambios locales (inspección + descarte de cambios
  sin preparar);
- selector y creación segura de ramas locales;
- `threading` + `queue.Queue` para operaciones de red.

### `ayuda_interfaz.py`

Módulo de ayuda visual.

Contiene:

- `AyudaEmergente`;
- `configurar_estilos`.

No contiene lógica Git.

### `modelos_historial.py`

Modelos exclusivos de la funcionalidad de historial:

- `CommitGit`;
- `ResultadoHistorial`;
- `ResultadoExportacion`.

### `servicio_historial_git.py`

Servicio de solo lectura para consultar commits locales mediante `git log`.

Reutiliza la instancia existente de `ServicioRemotoGit`/`ServicioGit`, pero no ejecuta operaciones remotas ni modifica el repositorio.

### `modelos_cambios_locales.py`

Modelos del inspector de cambios locales:

- `DetalleCambioLocal` (ruta, descripcion, preparado,
  requiere_actualizar_preparado, diffs, conteos, binarios,
  nuevo_sin_preparar, en_conflicto, hash y mensaje del
  último commit);
- `ResultadoDetalleCambioLocal` (exitoso, detalle, error, mensaje).

### `servicio_cambios_locales_git.py`

`ServicioCambiosLocalesGit` consulta los cambios locales de UN
archivo en las dos zonas de Git:
working tree -> índice y índice -> HEAD.

- reutiliza un `ServicioGit` existente (la instancia de
  `ServicioRemotoGit` de la interfaz) para `ejecutar_git`,
  `analizar_repositorio` y `obtener_cambios`; no duplica
  subprocess y no usa `shell=True`;
- diffs con `--literal-pathspecs diff [--cached]
  --no-color --no-ext-diff --no-textconv --unified=3 -- <ruta>`;
- resúmenes con `--numstat`; `-` marca binario sin convertir
  texto a entero;
- `??` marca `nuevo_sin_preparar` sin leer el archivo;
- un archivo sin cambios pendientes devuelve un resultado
  normal con mensaje informativo;
- último commit local con `rev-parse --short HEAD` y
  `log -1 --format=%s`; sin commits no falla;
- validación propia `_validar_ruta_archivo` (vacía, absoluta,
  `..`, NUL) ANTES de construir/ejecutar cualquier comando:
  sin acoplamiento a métodos privados de `ServicioGit`;
- `servicio_git.py` NO se modifica.

### `servicio_descarte_cambios_git.py`

`ServicioDescarteCambiosGit` descarta los cambios SIN PREPARAR de
UN archivo: `git --literal-pathspecs restore --worktree -- <ruta>`.

- sin `--source` explícito, `git restore --worktree` restaura
  desde el ÍNDICE (no desde HEAD): en un caso MM el working tree
  vuelve a la versión preparada y el staging queda intacto;
- reutiliza un `ServicioGit` existente (`ejecutar_git`,
  `analizar_repositorio`, `obtener_cambios`); nunca duplica
  subprocess y nunca usa `shell=True`;
- validación propia de la ruta (None, vacía, solo espacios, NUL
  antes de construir `Path`, absoluta, `..`); los nombres que
  empiezan por guión o contienen caracteres especiales son
  válidos y se protegen con `--literal-pathspecs` y `--`;
- revalida el estado justo antes del restore (analizar +
  obtener_cambios) y busca el cambio por ruta explícita; si ya
  no existe bloquea con "El archivo ya no tiene cambios sin
  preparar.";
- regla de estados basada en `estado_indice` / `estado_trabajo`,
  nunca en la descripción: el working tree debe tener una
  diferencia real respecto del índice (" M", " D", MM, MD, AM
  y equivalentes);
- `??` se rechaza con mensaje educativo (nunca se borra el
  archivo del disco); los conflictos (DD, AU, UD, UA, DU, AA,
  UU) se bloquean con helper propio sin acoplarse a métodos
  privados de `ServicioGit`;
- devuelve `ResultadoComando`; no crea commits, no modifica HEAD,
  no toca Fetch/Pull/Push;
- `servicio_git.py` NO se modifica.

### `modelos_ramas.py`

`RamaLocal(nombre, actual)` y `ResultadoRamas(exitoso, ramas,
error, mensaje)` (con `field(default_factory=list)` en `ramas`).

### `servicio_ramas_git.py`

`ServicioRamasGit` trabaja SOLO con ramas locales:

- listar: `git for-each-ref --format=%(refname:short) refs/heads/`;
  orden: rama actual primero, resto alfabético;
- rama actual: `git symbolic-ref --quiet --short HEAD` (consulta
  estructurada; en detached HEAD falla y devuelve cadena vacía);
- validar nombre: reglas propias + `git check-ref-format
  refs/heads/<nombre>`;
- cambiar: `git switch --no-guess <nombre>` (existencia local
  comprobada antes con `rev-parse --verify --quiet
  refs/heads/<nombre>`);
- crear: `git switch -c <nombre>` (nace del HEAD actual, sin
  start-point); queda LOCAL y sin upstream;
- precondiciones revalidadas antes de cada operación (repositorio
  válido, commits, HEAD no separado, sin operación en curso, sin
  index.lock, working tree/staging/nuevos TOTALMENTE limpios con
  `exitoso=True` en `obtener_cambios`, sin conflictos);
- `servicio_git.py` NO se modifica; reutiliza la instancia
  existente y no duplica `subprocess.run`.

## Estado funcional validado

Flujo local probado:

```text
cambio -> preparar -> commit
```

Push real probado correctamente contra GitHub.

Pull probado de extremo a extremo con un remoto `bare` temporal y dos clones.

La GUI detectó un repositorio atrasado:

```text
Por enviar: 0
Por descargar: 1
```

habilitó Pull y terminó en:

```text
Por enviar: 0
Por descargar: 0
```

sin Merge ni Rebase automático.

## Repositorio Oracle real

Rama:

```text
master
```

Upstream:

```text
origin/master
```

Último estado confirmado:

```text
Your branch is up to date with 'origin/master'.
nothing to commit, working tree clean
```

Últimos commits conocidos:

```text
ef15096 Agrega paquete FINI004
4dcb2f7 Pimer commit, creación del archivo README.md
```

Remoto:

```text
origin
```

URL:

```text
https://github.com/victor220888/Desarrollo-Mi-Tierra-S.A..git
```

La URL contiene `..git`, pero el Push real funcionó. No modificarla automáticamente.

## Repositorio GestorGit

Como varios agentes pueden trabajar sobre el proyecto en paralelo, este documento
no debe asumir que un hash antiguo sigue siendo el `HEAD` actual.

Antes de continuar cualquier sesión, obtener siempre el estado real con:

```powershell
git status
git log --oneline --decorate -8
```

Referencia histórica conocida antes de tooltips, historial y exportación:

```text
1e8fd1c Agrega pull seguro a la interfaz
```

Esa referencia es solamente histórica y **no debe usarse como fuente de verdad**
para decidir qué archivos reemplazar o qué cambios faltan.

La fuente de verdad es el working tree actual y su historial Git real.

Línea base funcional histórica (65 pruebas OK):

```text
fe5e49e Agrega historial con filtros y exportacion
```

Características de esa línea base:

- `fe5e49e` validado con **65 pruebas OK** (49 base + 11 historial + 5 exportación);
- `git diff --check` OK en esa línea base;
- `principal.py` integra filtros del historial;
- historial ordenado explícitamente por fecha de commit descendente;
- interfaz con cabecera `Fecha ↓`;
- exportación CSV y TXT integrada en la GUI;
- `modelos_historial.py` contiene `CommitGit`, `ResultadoHistorial` y `ResultadoExportacion`;
- `servicio_exportacion_historial.py` integrado;
- Push sigue siendo seguro y nunca forzado;
- Pull continúa exclusivamente con `--ff-only`.

La nueva etapa quedó confirmada en el commit:

```text
d12df38 Agrega configuracion inicial segura de GitHub
```

y la documentación posterior quedó confirmada en:

```text
235e261 Actualiza estado previo al primer Push de GestorGit
```

- **73 pruebas OK** (65 anteriores + 7 de configuración del remoto GitHub + 1 del primer Push con remoto no vacío);
- configuración inicial de GitHub integrada (`Configurar GitHub...`);
- primer Push endurecido: solamente crea la rama remota cuando el remoto está vacío de ramas;
- origin configurado mediante GestorGit; primer Push real VALIDADO.

Prueba manual real en Windows (resultado final confirmado por el
usuario; la prueba manual del visor de cambios también EXITOSA):

```text
Configurar GitHub -> exitoso
Fetch -> exitoso
Primer Push seguro -> exitoso
origin/master -> creado
Upstream -> configurado
Sincronización -> 0/0
Visor de cambios -> validado manualmente en Windows
```

El primer Push real de GestorGit ya fue ejecutado exitosamente:
repositorio sincronizado, Push sin force y Fetch posterior exitoso.
La etapa del visor de cambios de commits quedó VALIDADA en la
prueba manual: botón `Ver cambios...`, selección y doble clic,
datos del commit, diff, colores (agregado/eliminado/bloque/
encabezado), scroll vertical y horizontal y `Copiar diff`;
consultar commits no modifica el repositorio. La etapa del visor
quedó confirmada en el commit:

```text
0e3840e Agrega visor de cambios de commits
```

## Detalle de cambios de un commit

Flujo:

```text
Historial
    ↓
Seleccionar commit
    ↓
Ver cambios...
    ↓
git show de solo lectura
    ↓
diff visual
```

`obtener_cambios_commit(ruta, hash)` en `ServicioHistorialGit`:

- acepta únicamente hashes hexadecimales completos de 40 o 64
  caracteres; todo otro texto se rechaza antes de ejecutar Git;
- verifica el commit con `rev-parse --verify --quiet <hash>^{commit}`;
- obtiene el parche con
  `git show --format= --no-color --no-ext-diff --no-textconv --unified=3 <hash> --`;
- `--no-ext-diff` evita programas de diff externos;
- `--no-textconv` evita convertidores externos de atributos Git;
- nunca usa `shell=True`; no modifica el working tree; no accede
  al remoto; no ejecuta Fetch;
- un commit sin cambios devuelve un resultado exitoso con salida
  vacía (la GUI muestra "Este commit no contiene cambios de
  archivos visibles.").

Ventana única `Cambios del commit - Gestor Git` (1100x700,
mínimo 850x500), de SOLO LECTURA: muestra advertencia, datos del
commit (Hash/Fecha/Autor/Correo/Mensaje) y el diff en `tk.Text`
monoespaciado (Consolas) con scroll vertical y horizontal y
`wrap=tk.NONE`. Colores con tags: `+` agregado (verde), `-`
eliminado (rojo), `@@` bloque (azul), `diff --git`/`---`/`+++`
encabezado técnico (gris). Límite visual de 500000 caracteres con
aviso `[Vista truncada: ...]`; la truncación es solo visual.
Botones: `Cerrar` y `Copiar diff` (portapapeles de Tkinter;
copia únicamente el diff visible, no los metadatos del commit).
Si ya existe una ventana de detalle se destruye y se recrea; al
cambiar de repositorio o cerrar el historial también se cierra.

## Persistencia del último repositorio

`ServicioConfiguracion` recuerda únicamente el último repositorio
seleccionado manualmente por el usuario. `config.json` vive junto
a los archivos Python (`Path(__file__).resolve().parent`), sin
depender del directorio desde el cual se ejecute la aplicación.

Flujo:

```text
Seleccionar repositorio
    ↓
validar con Git
    ↓
guardar ruta local en config.json
    ↓
cerrar GestorGit
    ↓
abrir GestorGit
    ↓
validar ruta guardada
    ↓
cargar estado LOCAL
    ↓
Fetch manual
```

Durante la carga automática se carga únicamente el estado LOCAL:
rama, remotos, commits, cambios y estado local de sincronización.
Fetch queda habilitado si hay remoto, pero Pull y Push quedan
deshabilitados hasta un Fetch manual exitoso. Se muestra el aviso:
"Repositorio recordado cargado. Pulse Fetch para consultar el
remoto."

Reglas:

- estructura permitida: `{"ruta_repositorio": "D:\\ruta\\al\\repositorio"}`;
- se guarda la raíz confirmada por Git (`analizar_repositorio()`),
  no el texto original;
- la lectura ignora claves JSON desconocidas; la escritura siempre
  vuelve a escribir únicamente `ruta_repositorio`;
- nunca se guardan usuario, correo, contraseña, PAT, token, URLs
  de remotos ni credenciales (Git Credential Manager queda intacto);
- un `config.json` inválido, con JSON malformado o con una ruta
  que ya no es repositorio, muestra un aviso en la barra de estado
  (sin messagebox modal) y no impide trabajar; no se borra
  automáticamente;
- la escritura es conservadora: primero se valida la ruta con Git,
  después se escribe un archivo temporal en la misma carpeta y se
  reemplaza con `os.replace`; nunca se sobrescribe una
  configuración válida con una ruta inválida; los errores de
  escritura limpian el temporal;
- se guarda únicamente tras una selección manual
  (`guardar_configuracion=True` en `cargar_repositorio()`); un
  fallo de guardado no impide trabajar (el repositorio permanece
  cargado);
- recuerda exactamente UN repositorio: el último seleccionado
  (sin listas, favoritos ni historial de rutas);
- `config.json` está ignorado por `.gitignore` y NO forma parte
  del repositorio.

La persistencia fue validada manualmente en Windows:

- la selección manual de GestorGit guardó la configuración;
- al cerrar y volver a abrir la aplicación, el repositorio se
  cargó automáticamente SIN ejecutar Fetch; Fetch quedó
  disponible y Pull/Push permanecieron deshabilitados hasta un
  Fetch manual exitoso;
- el cambio manual al repositorio Oracle también quedó recordado;
  al volver a seleccionar GestorGit, quedó nuevamente como último
  repositorio recordado;
- `config.json` funcionó realmente y NO aparece en Git porque
  está ignorado por `.gitignore`;
- no se guardan credenciales.

## Actualización de archivos preparados

Concepto: "archivo preparado y vuelto a modificar después".

Flujo:

```text
Preparar
    ↓
seguir editando archivo
    ↓
GestorGit detecta staging desactualizado
    ↓
Actualizar preparados
    ↓
índice contiene versión actual
    ↓
Commit permitido
```

`CambioArchivo.requiere_actualizar_preparado` es True únicamente
cuando el archivo está preparado Y además existen cambios
posteriores en el working tree. Se calcula desde el estado
estructurado de `git status --porcelain=v1 -z` (nunca buscando
textos en la descripción): p. ej. `MM`, `AM`, `MD` y `RM`.
No se marca `M<espacio>` (working tree coincide con el índice)
ni `<espacio>M` (todavía no preparado). Los conflictos
(`DD/AU/UD/UA/DU/AA/UU` mediante `_es_estado_conflicto`) nunca
son actualizables con este botón.

Interfaz:

- la columna Preparado muestra `Sí (hay cambios nuevos)` cuando
  el archivo requiere actualización (ancho 140);
- el botón `Actualizar preparados` queda entre `Preparar
  seleccionados` y `Quitar de preparados`;
- se habilita solo si hay selección con al menos un archivo que
  requiera actualización (`actualizar_estado_botones_archivos`,
  enlazado a `<<TreeviewSelect>>`);
- la confirmación advierte que la versión preparada anterior será
  reemplazada, que no se modifica el disco, que no se crea commit
  y que un staging parcial hecho con otra herramienta también se
  completa (GestorGit trabaja a nivel de ARCHIVO).

Servicio (`actualizar_archivos_preparados`):

- valida el repositorio y las rutas relativas con las mismas
  validaciones de pathspec de `agregar_archivos` (sin NUL, sin
  opciones Git, sin salir del repositorio);
- consulta `obtener_cambios()` NUEVAMENTE antes de ejecutar: cada
  archivo debe seguir preparado, con `requiere_actualizar_preparado
  == True` y sin conflictos; si un archivo cambió de estado, la
  operación se bloquea explicando cuál;
- ejecuta `git --literal-pathspecs add -- <ruta1> <ruta2> ...`
  únicamente sobre las rutas explícitas; nunca `git add .`,
  `git add -A`, `reset`, `restore` ni `checkout`; sin
  `shell=True`; no quita los archivos del staging antes;
- no deshace cambios, no modifica el working tree y no crea
  commits.

El commit se sigue bloqueando si algún archivo preparado fue
modificado después; el mensaje educativo menciona ahora
`Actualizar preparados` y `Quitar de preparados` como opciones.

## Inspector de cambios locales

Etapa: inspector de cambios locales. Las CONSULTAS y los visores
son de SOLO LECTURA; la ventana incorpora además la acción
destructiva controlada `Descartar cambios sin preparar...`
(sección siguiente, exclusiva de la pestaña `Sin preparar`).
VALIDADA MANUALMENTE en Windows.

Se agregó para que un caso real de la práctica
(`git diff --stat -- servicio_git.py` + `git diff --
servicio_git.py`) pueda entenderse desde GestorGit sin
PowerShell.

PRUEBA MANUAL EN WINDOWS: EXITOSA.

Hechos confirmados visualmente por el usuario:

- archivo modificado sin preparar: la pestaña `Sin preparar`
  muestra el diff y `Preparados` muestra el resumen 0/0 con
  "No hay cambios preparados";
- archivo preparado: `Preparados` muestra el diff que entraría
  al commit;
- caso MM: "Modificado, preparado y vuelto a modificar",
  Preparado = "Sí (hay cambios nuevos)"; `Sin preparar` muestra
  únicamente los cambios posteriores al staging y `Preparados`
  conserva el diff previamente preparado; ambos diffs son
  distintos;
- resúmenes de inserciones/eliminaciones visibles;
- colores `+` / `-` / `@@` funcionan;
- scroll horizontal y vertical funcionan;
- `Actualizar` dentro del Inspector refresca únicamente el
  estado LOCAL;
- `Copiar diff` funciona;
- `Ver cambios locales...` se habilita con exactamente un
  archivo y se deshabilita con selección múltiple;
- la prueba temporal fue retirada y el staging de prueba fue
  quitado al finalizar.

Flujo enseñado:

```text
Working tree
    ↓ Preparar
Staging (índice)
    ↓ Commit
HEAD
```

Ventana única `Cambios locales - Gestor Git`:

- botón `Ver cambios locales...` habilitado únicamente con
  exactamente UN archivo seleccionado;
- datos superiores: Repositorio, Archivo, Estado, Preparado
  (`Sí` / `No` / `Sí (hay cambios nuevos)`) y Último commit
  local (hash corto + mensaje);
- sin commits: mensaje educativo, sin fallar;
- `ttk.Notebook` con pestañas `Sin preparar` y `Preparados`;
- en el caso `MM` ambas pestañas pueden contener cambios
  distintos (es el objetivo didáctico principal);
- resumen por pestaña: `N inserciones · M eliminaciones`
  (con singulares `1 inserción` / `1 eliminación`) o
  `Archivo binario` cuando `--numstat` devuelve `-`;
- archivo nuevo sin preparar (`??`): mensaje educativo; Git
  aún no tiene versión anterior para comparar; no se lee el
  archivo ni se inventa un diff;
- archivo sin cambios pendientes: "El archivo ya no tiene
  cambios locales pendientes."; resultado normal, no error;
- `Actualizar`: consulta SOLO el estado LOCAL, sin Fetch;
- `Copiar diff`: copia el contenido visible de la pestaña
  activa al portapapeles;
- `Cerrar`: cierra la ventana;
- se destruye y recrea al abrir de nuevo (patrón de la ventana
  de detalle de commits); se cierra al cambiar de repositorio;
- visores `tk.Text` de solo lectura, `wrap=tk.NONE`, Consolas,
  colores idénticos al visor de commits (reutiliza el estático
  `_tag_para_linea_diff`, sin refactorizar el visor histórico);
- límite visual de 500000 caracteres con
  `[Vista truncada: ...]`; truncación solamente visual.

Seguridad:

- comandos siempre como listas de argumentos, nunca
  `shell=True`; `--` obligatorio antes del pathspec;
- `--literal-pathspecs` para tratar la ruta literalmente
  (nombres que empiezan por `-` o con caracteres especiales);
- `--no-ext-diff` y `--no-textconv` evitan programas externos
  configurados en Git;
- la validación de la ruta (vacía, absoluta, `..`, NUL) ocurre
  ANTES de construir/ejecutar cualquier diff; helper propio
  `_validar_ruta_archivo`, sin acoplarse a métodos privados de
  `ServicioGit`;
- `DetalleCambioLocal.en_conflicto` expone de forma estructurada
  si el par `estado_indice` + `estado_trabajo` corresponde a un
  conflicto (DD, AU, UD, UA, DU, AA, UU); se calcula con el
  helper propio `_calcular_en_conflicto`, nunca desde el texto
  localizado de `descripcion` (la GUI usa el booleano y ya no
  compara `descripcion == "Conflicto"`);
- `ServicioCambiosLocalesGit` no ejecuta ninguna operación
  destructiva ni remota; la acción explícita de descarte se
  delega exclusivamente a `ServicioDescarteCambiosGit` (la
  ventana del Inspector sí incorpora el botón
  `Descartar cambios sin preparar...`, descrito en su sección).

Corrección posterior (cierre documental):

- si `git diff --numstat` FALLA, `obtener_detalle()` devuelve
  `ResultadoDetalleCambioLocal(exitoso=False, error=<mensaje>)`;
  nunca informa 0 inserciones / 0 eliminaciones falsos;
  `_obtener_resumen()` devuelve la tupla
  (inserciones, eliminaciones, binario) solo cuando la consulta
  es exitosa y un resultado de error controlado cuando falla
  (patrón `_convertir_fecha_iso` de `ServicioHistorialGit`);
- un `--numstat` exitoso y realmente vacío sigue siendo
  legítimamente 0 inserciones / 0 eliminaciones;
- `servicio_git.py` no se modificó.

## Descarte de cambios sin preparar

Etapa: primera acción destructiva controlada de GestorGit, dentro
de la ventana del Inspector (`Cambios locales - Gestor Git`),
exclusiva de la pestaña `Sin preparar`.

Estado: ETAPA VALIDADA - PRUEBA MANUAL EN WINDOWS EXITOSA
(confirmada por el usuario).

Casos confirmados manualmente en Windows:

- caso A (archivo modificado sin preparar): el Inspector muestra
  el diff, Preparado = No, el botón queda habilitado en
  `Sin preparar` y deshabilitado en `Preparados`; la confirmación
  explícita aparece y el descarte funciona; el archivo vuelve a
  HEAD;
- caso B (MM): A preparada y B agregada después; estado
  "Modificado, preparado y vuelto a modificar", Preparado =
  "Sí (hay cambios nuevos)", `Preparados` muestra A y
  `Sin preparar` muestra B; el descarte elimina B únicamente, A
  permanece preparada, `git diff` vuelve a quedar vacío y
  `git diff --cached` conserva A;
- caso B extendido: quitar de preparados conserva A en el working
  tree; un segundo descarte elimina A y servicio_git.py vuelve
  exactamente a HEAD (`git diff -- servicio_git.py` sin salida);
- caso C (archivo nuevo ??): estado Nuevo, Preparado No, el botón
  de descarte deshabilitado desde el primer momento (también en
  `Preparados`) y el archivo NO fue eliminado (`Test-Path` =
  True): GestorGit no ejecuta borrados;
- caso D (archivo solamente preparado): `Sin preparar` vacío y el
  botón de descarte deshabilitado;
- caso E (actualización visual): después del descarte el Inspector
  se actualiza correctamente y cuando ya no quedan cambios muestra
  "El archivo ya no tiene cambios locales pendientes.";
- caso F (Fetch simultáneo): NO APLICABLE desde la GUI actual
  (con el Inspector abierto no fue posible interactuar con el
  botón Fetch de la ventana principal); se documenta como
  limitación, no como fallo ni prueba exitosa; la defensa en
  profundidad del código cubre el escenario.

Objetivo didáctico: restaurar UN archivo para que su working tree
vuelva a coincidir con la versión actualmente existente en el
índice (staging):

```text
HEAD
  ↓
Staging        = versión preparada      (se conserva)
  ↓
Working tree   = versión preparada      (cambios posteriores eliminados)
```

En un archivo " M" (sin preparar) el índice coincide con HEAD, por
lo que el archivo vuelve a la versión del índice/HEAD.

Comando productivo exacto (SIEMPRE lista de argumentos, nunca
`shell=True`):

```text
git --literal-pathspecs restore --worktree -- <ruta>
```

- sin `--source=HEAD`: restaura desde el ÍNDICE; fundamental para
  que en un caso MM el working tree vuelva a la versión preparada
  conservando el staging;
- prohibidos: `--staged`, `restore .`, `checkout`, `checkout --`,
  `reset`, `reset --hard`, `clean`, `add`, `rm`; nunca se borra
  un archivo nuevo (??) con `os.remove`, `unlink` ni `clean`.

Ventana e integración en `principal.py`:

- botón `Descartar cambios sin preparar...` junto a
  `Actualizar` / `Copiar diff` / `Cerrar` (columna 0);
- habilitado únicamente cuando: existe repositorio, la pestaña
  activa es `Sin preparar`, el archivo tiene cambios SIN PREPARAR
  reales, no es nuevo (??) y no está en conflicto; al cambiar de
  pestaña el botón queda deshabilitado
  (`<<NotebookTabChanged>>` -> `actualizar_estado_boton_descartar`);
- la decisión de conflicto usa el booleano estructurado
  `detalle.en_conflicto` de `DetalleCambioLocal` (calculado en
  `ServicioCambiosLocalesGit._calcular_en_conflicto` desde
  `estado_indice` + `estado_trabajo`); NUNCA se compara
  `descripcion == "Conflicto"` (texto localizado);
- defensa en profundidad durante operación remota: si
  `operacion_remota_en_curso` es True,
  `descartar_cambios_sin_preparar()` se bloquea al principio
  (mensaje controlado en la barra de estado, sin consulta ni
  confirmación destructiva, sin llamar al servicio) y
  `actualizar_controles_operacion_remota()` recalcula el botón
  de forma segura (`actualizar_estado_boton_descartar` tolera
  que el Inspector no exista); el caso F manual fue NO
  APLICABLE por la modalidad de las ventanas, por eso la GUI
  conserva esta defensa;
- al pulsarlo: consulta LOCAL fresca del detalle (sin Fetch),
  actualiza la vista, decide nuevamente si la operación sigue
  permitida y SOLO después muestra la confirmación;
- confirmación fuerte (`messagebox.askyesno` con icono de
  advertencia y `parent` de la ventana del Inspector) que cita la
  ruta literalmente, explica qué versión quedará (staging, o
  índice/HEAD si no hay preparados) y que los cambios preparados
  SE CONSERVAN; nunca lenguaje ambiguo;
- el servicio revalida el estado otra vez justo antes del restore;
- tras el éxito: se refresca la tabla principal (`cargar_cambios`)
  y el Inspector (`actualizar_cambios_locales`), NO se cierra la
  ventana, NO se hace Fetch y se muestra un mensaje breve de
  éxito ("Los cambios preparados se conservaron." cuando había
  preparados);
- caso MM esperado: queda `Modificado y preparado`, Preparado =
  `Sí`, `Sin preparar` vacía (0 inserciones · 0 eliminaciones ·
  "No hay cambios sin preparar.") y `Preparados` con EL MISMO
  diff de antes;
- caso " M": el Inspector maneja normalmente "El archivo ya no
  tiene cambios locales pendientes." y la fila desaparece;
- `Descartar cambios sin preparar...` nunca se agrega a la
  pantalla principal (solo al Inspector);
- el texto de advertencia de la ventana ahora indica que la única
  acción que modifica el working tree es este botón y que el
  staging se conserva.

Seguridad (servicio):

- validación de ruta antes de ejecutar Git: None, vacía, solo
  espacios, NUL (antes de construir `Path`), absoluta, `..`;
  nombres con guión inicial, `[`, `]`, `*`, `?` son válidos
  (seguridad mediante `--literal-pathspecs` y `--`);
- `??` -> mensaje educativo; el descarte de un archivo sin
  seguimiento significaría borrarlo del disco (FUERA de alcance);
- conflictos DD/AU/UD/UA/DU/AA/UU -> bloqueo con mensaje
  educativo (helper privado propio, sin `_es_estado_conflicto`
  de `ServicioGit`);
- la regla de estados se basa en `estado_indice` /
  `estado_trabajo`, nunca en `descripcion`; el working tree debe
  tener una diferencia real respecto del índice; funcionan
  " M", " D", MM, MD, AM y equivalentes;
- staging intacto: `git diff --cached -- <ruta>` antes y después
  del descarte son IDÉNTICOS (propiedad crítica verificada por
  pruebas);
- 100 % local: no Fetch/Pull/Push, no se altera
  `fetch_exitoso_en_sesion`, no se crean commits, no se modifica
  HEAD;
- `servicio_descarte_cambios_git.py` reutiliza el `ServicioGit`
  existente y NO modifica `servicio_git.py`; no se creó un modelo
  nuevo (`ResultadoComando` es suficiente).

## Selector y creación segura de ramas locales

Estado: ETAPA VALIDADA - PRUEBA MANUAL EN WINDOWS EXITOSA
(confirmada por el usuario).

Prueba ejecutada en repositorio temporal
`C:\Users\victo\AppData\Local\Temp\GestorGit-Prueba-Ramas-20260819-151113`
con rama `prueba-manual-ramas-victor`: creación desde master OK,
cambio a nueva rama OK, cambio a master BLOQUEADO correctamente
con `archivo.txt` modificado, limpieza solamente del cambio temporal,
regreso posterior a master OK, `git branch --show-current` -> master,
`git status --short` -> sin salida, ambas ramas apuntaban a
`f9f40c4`, `git remote -v` -> sin salida, rama NO publicada;
eliminación de ramas permanece fuera del alcance V1.

V1: SOLO ramas locales. Sin borrar, renombrar, publicar, upstream
automático, Merge, Rebase, Cherry-pick, Checkout, Reset, Force
Push ni Fetch/Pull/Push automáticos. Una rama nueva queda LOCAL
(no se publica y no tiene upstream) hasta la etapa posterior
"Publicar rama".

Comandos productivos exactos (siempre listas de argumentos vía
`ejecutar_git`, nunca `shell=True`):

```text
git for-each-ref --format=%(refname:short) refs/heads/
git check-ref-format refs/heads/<nombre>
git switch --no-guess <rama>
git switch -c <rama>      (nace del HEAD actual, sin start-point)
```

Arquitectura:

- `modelos_ramas.py`: `RamaLocal(nombre, actual)` y
  `ResultadoRamas(exitoso, ramas, error, mensaje)` con
  `field(default_factory=list)` en `ramas`;
- `servicio_ramas_git.py` - `ServicioRamasGit(servicio_git)`
  reutiliza la instancia existente: toda la Git pasa por su
  `ejecutar_git`; NO se modifica `servicio_git.py`, NO se duplica
  `subprocess.run`, 100 % local (nunca Fetch/Pull/Push);
- `principal.py`: botón `Ramas...` y ventana `Ramas locales -
  Gestor Git`.

Consultas:

- `obtener_ramas_locales(ruta)` valida el repositorio y lista
  SOLO `refs/heads/` con `for-each-ref`; la rama actual se
  determina de forma estructurada con
  `git symbolic-ref --quiet --short HEAD` (si HEAD está separado,
  la consulta falla y se obtiene la cadena vacía); orden: rama
  actual primero, resto alfabético; en detached HEAD listar
  sigue válido (ninguna rama marcada como actual, `mensaje` lo
  avisa) pero cambiar y crear quedan bloqueados.
- distinción estructurada explícita: un repositorio SIN COMMITS
  NO es un HEAD separado. `ResultadoRamas` expone
  `tiene_commits: bool = True` y `head_separado: bool = False`;
  `obtener_ramas_locales()` marca `head_separado=True`
  únicamente cuando hay commits y `symbolic-ref` falla; un
  repositorio sin commits devuelve `tiene_commits=False` y
  `head_separado=False` (con mensaje educativo "Repositorio sin
  commits todavía"). Nunca se infiere detached por el solo hecho
  de que la lista de ramas quede vacía o sin rama marcada como
  actual: ambos estados pueden impedir operaciones, pero por
  motivos distintos.
- la diferencia entre ramas locales (`refs/heads/...`) y remotas
  (`refs/remotes/...`) es explícita: la V1 muestra SOLO locales.

Validación de nombres (`_validar_nombre_rama`):

- reglas propias ANTES de cualquier comando Git: None, no-texto,
  vacío, solo espacios, espacios iniciales/finales, NUL, inicio
  `-`, `HEAD`, `@`, sintaxis `@{...}` (p. ej. `@{-1}`);
- después `git check-ref-format refs/heads/<nombre>` (un solo
  argumento; nunca se corrige el nombre silenciosamente, nunca se
  convierten minúsculas ni se quitan espacios);
- válidos ejemplares: `feature/login`, `fix/error-oracle`,
  `prueba_2026`; inválidos: `""`, `" rama"`, `"rama "`,
  `"-rama"`, `"HEAD"`, `"rama..mala"`, `"rama.lock"`,
  `"rama@{1}"`.

Precondiciones conservadoras (`_validar_precondiciones`),
revalidadas SIEMPRE antes de cambiar o crear (el servicio decide,
aunque la GUI haya confirmado):

- repositorio válido (`analizar_repositorio.es_repositorio`);
- existe al menos un commit (`tiene_commits`);
- HEAD no separado (`symbolic-ref` propia del servicio, no se
  depende de cómo `analizar_repositorio` represente el detached);
- sin operación Git en curso (`detectar_operacion_en_curso`:
  MERGE_HEAD/CHERRY_PICK_HEAD/REVERT_HEAD/rebase/sequencer);
- sin `index.lock` (chequeo propio: `git rev-parse --git-dir` y
  `Path(index.lock).exists()`; NUNCA se borra; si no puede
  verificarse, bloquea);
- working tree, staging y archivos nuevos (`??`) TOTALMENTE
  limpios: `obtener_cambios()` debe devolver `exitoso=True` y sin
  cambios; un error de consulta BLOQUEA (nunca se interpreta un
  error como "repositorio limpio");
- sin conflictos: helper privado propio `_calcular_en_conflicto`
  (DD/AU/UD/UA/DU/AA/UU), nunca texto localizado; mensaje
  educativo con conteo de archivos;
- SEGUNDA revalidación completa (`_validar_precondiciones`
  ejecutada OTRA vez) inmediatamente antes del `git switch`
  productivo, en `cambiar_rama()` y en `crear_rama()`: cualquier
  cambio local creado, modificado o preparado por otra herramienta
  entre la primera validación y el switch BLOQUEA la operación
  (defensa en profundidad, reduce la ventana TOCTOU; sin sleeps ni
  locks artificiales);
- cambiar: la rama existe LOCALMENTE
  (`rev-parse --verify --quiet refs/heads/<nombre>`, jamás
  adivinación) y no es la actual; crear: la rama NO existe aún;
- nunca se descartan cambios para permitir el switch.

Interfaz:

- botón `Ramas...` en "Información local" (columna 7, junto a
  `Historial...`); se habilita con repositorio válido y se
  deshabilita durante operaciones remotas
  (`actualizar_controles_operacion_remota`);
- ventana única `Ramas locales - Gestor Git` (se destruye y
  recrea al abrir de nuevo; Toplevel con `transient`, NO modal —
  sin `grab_set` ni `wait_window` —; protocolo
  `WM_DELETE_WINDOW`; se cierra al cambiar de repositorio y en
  `limpiar_repositorio`);
- contenido: texto educativo breve, "Rama actual", lista de ramas
  locales (la actual marcada con " (actual)"), entrada "Nueva
  rama", botones `Cambiar a seleccionada`, `Crear rama`,
  `Actualizar`, `Cerrar`; sin Eliminar/Renombrar/Merge/Rebase/
  Publicar/Push;
- `Cambiar a seleccionada` y `Crear rama` se recalculan con la
  selección, el texto de la entrada y `operacion_remota_en_curso`
  (`actualizar_estado_botones_ventana_ramas`, segura si la ventana
  no existe: si empieza Fetch/Pull/Push con la ventana abierta,
  los botones se deshabilitan también dentro de la ventana);
- confirmaciones explícitas (padre de la ventana) que NO afirman
  limpieza absoluta: "GestorGit realizará el cambio únicamente si
  el repositorio continúa limpio; el servicio volverá a
  comprobarlo antes de ejecutar git switch"; el cambio cita la
  rama actual y la nueva, la creación cita el nombre y que la
  rama NO se publicará ni tendrá upstream;
- tras cambiar o crear: se cierran historial, detalle de commit e
  Inspector (ventanas dependientes de la rama anterior), se
  recarga el estado LOCAL con `cargar_repositorio(...,
  reiniciar_fetch=True)` (actualiza etiqueta Rama, tabla de
  archivos y sincronización local; invalida
  `fetch_exitoso_en_sesion`, así Pull/Push quedan deshabilitados
  hasta un Fetch manual exitoso; Fetch sigue disponible si hay
  remoto) y la lista de la ventana se refresca; nunca Fetch
  automático;
- mensajes: tras cambiar, la barra de estado muestra
  "Ahora se encuentra en la rama local '<rama>'."; tras crear, un
  `showinfo` y la barra muestran "La rama se creó solamente en el
  repositorio local. Todavía no se publicó en el remoto.".

Rama nueva y Push:

- la lógica del primer Push NO se modifica: la protección actual
  queda intacta; una rama nueva (sin upstream) en un remoto con
  ramas conocidas bloquea el Push explicando el motivo;
- la publicación explícita de una rama nueva será la etapa
  posterior "Publicar rama" con sus propias confirmaciones.

Pruebas (`pruebas/test_ramas_git.py`, 28 pruebas):

- listado con la actual identificada y orden (actual primero);
- cambio a rama existente y contenido del working tree tras el
  switch;
- creación desde HEAD (queda situado, el commit de origen no
  cambia);
- rechazos: rama ya existente, rama local inexistente, M sin
  preparar, staged, `??`, repo sin commits, HEAD separado
  (listar OK, cambiar/crear bloqueados), index.lock,
  MERGE_HEAD, repo no válido;
- regresión: un repositorio SIN COMMITS se reporta con
  `tiene_commits=False` y `head_separado=False` (nunca se
  confunde con detached HEAD), mientras que un verdadero
  `checkout --detach` sí queda identificado con
  `head_separado=True` (ambas pruebas verifican los campos
  estructurados directamente);
- validación de nombres (10 inválidos con subTest + 3 válidos);
- NUL rechazado SIN ejecutar ningún `switch` (spy);
- argumentos exactos con spy
  (`["switch", "--no-guess", nombre]`,
  `["switch", "-c", nombre]`) y ausencia total de
  checkout/reset/restore/clean/merge/rebase/fetch/pull/push/
  branch/-D/--force;
- error de `obtener_cambios` bloquea (nunca se interpreta como
  limpio); error de `switch` expuesto;
- TOCTOU (spy con `secuencia_cambios`): el repositorio estaba
  limpio en la PRIMERA validación y aparece un cambio en la
  SEGUNDA, inmediatamente antes del productivo; tanto
  `cambiar_rama()` como `crear_rama()` devuelven
  `exitoso=False` con "no está limpio", `obtener_cambios()` se
  llamó al menos dos veces y NINGÚN `switch` llegó a ejecutarse;
- crear/cambiar NO modifica ningún remoto (remoto bare local:
  `git remote` intacto y `refs/remotes/origin/` vacío).

Nota del spy: `ServicioGitEspiaRamas` registra las llamadas y
responde `rev-parse --git-dir` con `".git"`, `symbolic-ref` con la
rama configurada y `rev-parse refs/heads/<nombre>` según un
conjunto de refs existentes. Admite además `secuencia_cambios`:
cada llamada a `obtener_cambios()` consume la siguiente tupla
`(exitoso, cambios)` de la secuencia (se usa el comportamiento fijo
cuando se agota), lo que permite simular que el repositorio se
ensucia ENTRE dos validaciones sin tocar el código productivo.

## Pruebas

El proyecto tiene actualmente **255 pruebas automatizadas**:

- 49 pruebas base de operaciones locales/remotas;
- 11 pruebas del historial;
- 5 pruebas de exportación;
- 7 pruebas de configuración inicial del remoto GitHub;
- 1 prueba del primer Push con remoto no vacío;
- 6 pruebas del detalle de cambios de un commit;
- 8 pruebas de la persistencia del último repositorio;
- 7 pruebas de la actualización de archivos preparados;
- 12 pruebas del inspector de cambios locales;
- 17 pruebas del descarte de cambios sin preparar;
- 28 pruebas de las ramas locales (123 anteriores + 28 nuevas);
- 104 pruebas de los tooltips didácticos V1 (
  58 de Fase 2A P0/P1 + 46 de Fase 2B P2/P3).

Archivos principales de pruebas:

```text
pruebas/test_servicio_git.py
pruebas/test_commit_git.py
pruebas/test_sincronizacion_git.py
pruebas/test_push_git.py
pruebas/test_pull_git.py
pruebas/test_historial_git.py
pruebas/test_exportacion_historial.py
pruebas/test_configuracion_remoto_git.py
pruebas/test_detalle_commit_git.py
pruebas/test_configuracion.py
pruebas/test_actualizacion_preparados.py
pruebas/test_cambios_locales_git.py
pruebas/test_descarte_cambios_git.py
pruebas/test_ramas_git.py
pruebas/test_ayuda_tooltips_v1.py
```

Resultado esperado:

```text
Ran 255 tests in ...
OK
```

Las pruebas no deben tocar GitHub ni el repositorio Oracle real.

Usar repositorios temporales locales con:

```python
tempfile.TemporaryDirectory()
```

Las pruebas del historial deben proteger especialmente:

- filtros por archivo;
- filtros Desde/Hasta inclusivos;
- combinación de filtros mediante AND;
- orden explícito por fecha de commit descendente;
- límite de resultados;
- fechas inválidas y rangos invertidos.

Las pruebas de exportación deben proteger:

- CSV con todos los campos;
- TXT con repositorio y filtros;
- rechazo de listas vacías;
- errores controlados de escritura;
- protección contra fórmulas al abrir CSV en hojas de cálculo.

## Reglas de seguridad

No implementar automáticamente:

```text
git reset --hard
git clean -fd
git push --force
git push --force-with-lease
git branch -D
```

No:

- borrar `index.lock` automáticamente;
- resolver conflictos automáticamente;
- hacer Merge automáticamente;
- hacer Rebase automáticamente;
- elegir un remoto al azar;
- guardar PAT/token.

Push debe bloquearse si hay cambios sin commit, conflictos, operación Git en curso, `index.lock`, detached HEAD, remoto adelantado o divergencia.

Pull debe bloquearse si hay cambios sin commit, commits locales por enviar, divergencia, falta de upstream, operación Git en curso o `index.lock`.

Pull usa:

```text
git pull --ff-only
```

## Configuración inicial de GitHub

Cuando un repositorio local todavía no tiene remotos, la interfaz ofrece
el botón `Configurar GitHub...` para conectar el primer remoto:

```text
repositorio local
    ↓
Configurar origin
    ↓
Fetch
    ↓
Push inicial seguro
    ↓
origin/master como upstream
```

Crear la cuenta y el repositorio vacío sigue ocurriendo en el navegador.
La aplicación solamente abre GitHub (`https://github.com/new`) y configura
la URL local. No inicia sesión, no recibe usuario/contraseña/PAT y no
utiliza la API de GitHub ni `gh` CLI.

`agregar_remoto_github()`:

- se permite únicamente cuando el repositorio NO tiene ningún remoto;
- crea el remoto `origin`;
- acepta únicamente URLs HTTPS de `github.com`
  (`https://github.com/usuario/repositorio` o con `.git`);
- rechaza credenciales embebidas en la URL (usuario, contraseña o token);
- nunca modifica, sustituye ni elimina un remoto existente
  (sin `set-url`, `remove` ni `rename`);
- ejecuta solamente `git remote add origin <url>` mediante `subprocess`
  sin `shell=True`; no ejecuta Fetch y no se conecta a Internet;
- no duplica la lógica de Push: el Push existente configura upstream
  en el primer envío.

Después de agregar origin la aplicación recarga el repositorio, exige un
Fetch nuevo y deja Pull/Push deshabilitados hasta que el Fetch sea exitoso.

## Hilos y Tkinter

Fetch, Pull y Push se ejecutan fuera del hilo principal.

Flujo:

```text
Tkinter
  -> Thread
  -> Git
  -> queue.Queue
  -> after(...)
  -> Tkinter
```

Nunca modificar widgets Tkinter desde un hilo secundario.

## Etapa de tooltips y estética

Esta etapa quedó implementada antes del historial:

- tooltips educativos en los botones principales;
- explicación visible de Fetch, Pull y Push;
- explicación de staging y commit;
- mensajes de estado resaltados por color;
- estilos diferenciados para acciones remotas;
- lógica Git original conservada.

Tooltips requeridos:

- Seleccionar...
- Actualizar
- Fetch
- Pull
- Push
- Seleccionar todo
- Preparar seleccionados
- Quitar de preparados
- Crear commit

Conceptos educativos:

### Fetch

Consulta el remoto y actualiza las referencias remotas locales. No modifica los archivos del working tree.

### Pull

Descarga commits remotos y actualiza la rama local. En esta aplicación solo se permite fast-forward.

### Push

Envía commits locales al remoto. Se ejecuta Fetch antes y nunca se usa Push forzado.

### Preparar

Equivale conceptualmente a `git add`. Pasa cambios al staging para el próximo commit.

### Quitar de preparados

Saca archivos del staging. No elimina los archivos ni descarta sus modificaciones.

### Commit

Crea una instantánea local de lo preparado. No la envía al remoto.

## Etapa actual: historial de commits de solo lectura con filtros y exportación

La primera versión del historial ya está funcionando visualmente y muestra correctamente los commits del repositorio local.

Archivos de esta funcionalidad:

```text
modelos_historial.py
servicio_historial_git.py
servicio_exportacion_historial.py
pruebas/test_historial_git.py
pruebas/test_exportacion_historial.py
```

`modelos_historial.py` contiene:

- `CommitGit`;
- `ResultadoHistorial`;
- `ResultadoExportacion`.

`servicio_historial_git.py` contiene `ServicioHistorialGit`, que reutiliza el `ServicioGit` ya existente y ejecuta únicamente consultas locales de `git log`.

La consulta usa separadores de control para evitar analizar `git log --oneline` por espacios.

La interfaz agrega el botón:

```text
Historial...
```

que abre una ventana independiente de solo lectura con las columnas:

```text
Hash | Fecha | Autor | Mensaje
```

La ventana muestra hasta 100 commits recientes.

### Filtros implementados

La ventana de historial ahora permite combinar tres filtros:

```text
Archivo contiene
Desde
Hasta
```

El filtro de archivo:

- acepta todo o parte del nombre o ruta;
- no distingue mayúsculas y minúsculas;
- se aplica mediante un pathspec Git construido por la aplicación;
- escapa caracteres especiales de glob para tratar la búsqueda como texto literal;
- puede encontrar, por ejemplo, `FINI004`, `.pls` o `Paquetes`.

Las fechas:

- se escriben en la interfaz como `dd/mm/aaaa`;
- son inclusivas;
- pueden usarse por separado o juntas;
- se convierten internamente a `YYYY-MM-DD` antes de consultar Git;
- bloquean rangos donde Desde sea posterior a Hasta.

Los filtros se combinan mediante AND. Por ejemplo:

```text
Archivo contiene: FINI004
Desde: 01/08/2026
Hasta: 31/08/2026
```

muestra solamente commits de agosto de 2026 que hayan modificado un archivo cuya ruta o nombre contenga `FINI004`.

La ventana incluye:

```text
Aplicar filtros
Limpiar
Actualizar historial
```

`Actualizar historial` conserva los filtros actuales. `Limpiar` vacía los filtros y vuelve a mostrar el historial completo.

El historial se actualiza automáticamente si está abierto después de crear un commit o después de un Pull exitoso.

No se agregaron acciones destructivas desde el historial. En particular, la ventana NO ofrece:

- Checkout;
- Reset;
- Revert;
- Merge;
- Rebase;
- eliminación de commits.


### Exportación implementada

La ventana de historial permite exportar **exactamente los commits visibles** después de aplicar los filtros actuales. No vuelve a ejecutar `git log` al exportar.

Botones:

```text
Exportar CSV
Exportar TXT
```

CSV:

- codificación `UTF-8 con BOM` para facilitar la apertura en Excel/Windows;
- separador `;`;
- columnas: Hash completo, Hash corto, Fecha ISO, Autor, Correo y Mensaje;
- protege valores que podrían interpretarse como fórmulas de hoja de cálculo (`=`, `+`, `-`, `@`, tabulación o retorno de carro).

TXT:

- formato legible por personas;
- incluye fecha/hora de generación;
- incluye ruta del repositorio;
- registra filtro de archivo, Desde y Hasta de la última consulta exitosa;
- incluye hash completo, hash corto, fecha, autor, correo y mensaje de cada commit.

La exportación solo escribe el archivo que el usuario elige mediante el diálogo Guardar como. No modifica Git ni el repositorio.

### Pruebas del historial

Ahora existen 11 pruebas específicas:

- repositorio sin commits;
- datos de un commit;
- orden más reciente primero;
- límite de resultados;
- rechazo de límite inválido;
- filtro parcial por nombre de archivo sin distinguir caso;
- filtro Desde inclusivo;
- filtro Hasta inclusivo;
- rango Desde/Hasta;
- combinación archivo + fechas;
- rechazo de fecha inválida y rango invertido.

Las 11 pruebas del historial fueron ejecutadas en aislamiento y pasaron correctamente.

El conjunto anterior tenía 49 pruebas fuera del historial. A las 11 pruebas del historial se agregan 5 pruebas de exportación, 7 pruebas de configuración del remoto GitHub, 1 prueba del primer Push con remoto no vacío y 6 pruebas del detalle de cambios de un commit. El total esperado en aquella etapa era:

```text
Ran 79 tests in ...
OK
```

Nota: ese total de 79 es HISTÓRICO, anterior a la etapa de
persistencia. El total de 94 (49 + 11 + 5 + 7 + 1 + 6 + 8 + 7
pruebas de la actualización de archivos preparados) es también
HISTÓRICO (commit 014e3f7). El total de 104 (94 + 10 pruebas del
inspector) fue el confirmado en el commit c62b0a0. El total de 105
(104 + 1 prueba de regresión del error de --numstat) fue el
confirmado en el commit 634a295. El total de 123
(105 + 17 pruebas del descarte + 1 prueba del conflicto
estructurado) fue el confirmado en el commit 3309be7. El total de
151 (123 + 28 de las ramas locales) corresponde al estado
consolidado HASTA Ramas Locales V1 y está integrado en el commit
local HEAD "Agrega selector seguro de ramas locales" (consultar
git log -1 --oneline para conocer el hash vigente; SIN PUSH). Las
58 pruebas adicionales pertenecen a Tooltips Didácticos V1 —
Fase 2A (P0/P1). La etapa está CERRADA: la prueba
visual Windows final fue EXITOSA y quedó commiteada localmente
en bc57772 (implementación) y 82a32d1 (microcorrección de Fetch
y primer Push, hijo de bc57772); SIN PUSH. Después, la Fase 2B
(P2/P3) añadió 46 pruebas más de tooltips (104 específicas) y una
microcorrección previa al cierre eliminó el test genérico
test_textos_2b_no_recomiendan_git_destructivo (contra
"git reset"/"git clean"): el total ACTUAL es 255
(209 anteriores + 46 de Fase 2B; 104/104 específicas de
tooltips OK y 255/255 suite completa OK). Fase 2B CERRADA:
PRUEBA MANUAL EN WINDOWS EXITOSA (confirmada por el usuario) y
cierre documentado en el commit "Cierra tooltips didacticos V1"
(hijo de 0413697; SIN PUSH).

Las 5 pruebas de exportación validan CSV, TXT, lista vacía, errores de escritura y protección contra fórmulas CSV. Fueron ejecutadas en aislamiento y pasaron correctamente.

Las 7 pruebas de configuración del remoto validan: creación de `origin`, URL vacía, HTTP, host distinto de GitHub, credenciales embebidas, repositorio con remoto existente y configuración sin contacto de red. Fueron ejecutadas en aislamiento y pasaron correctamente, sin tocar GitHub.

La prueba del primer Push con remoto no vacío valida el escenario peligroso (remoto con rama `main`, rama local `master`): el Push se rechaza, el mensaje menciona `origin/main` y `refs/heads/master` NO se crea en el remoto. Fue ejecutada en aislamiento y pasó correctamente.

Las 6 pruebas del detalle de un commit validan: archivo agregado visible en el parche, modificación con línea eliminada y agregada, repositorio sin cambios después de la consulta, rechazo de hashes inválidos sin ejecutar `git show`, rechazo de hash inexistente con error controlado y uso de `--no-ext-diff`/`--no-textconv`/`--no-color` sin comandos destructivos. Fueron ejecutadas en aislamiento y pasaron correctamente.

Las 8 pruebas de la persistencia validan: config.json inexistente (primer inicio), guardar y cargar un repositorio válido, JSON malformado sin excepción, ruta inexistente, carpeta sin `.git`, escritura que conserva únicamente `ruta_repositorio`, guardado inválido que no sobrescribe la configuración válida y rechazo de ruta que no es texto. Fueron ejecutadas en aislamiento y pasaron correctamente, usando únicamente `tempfile.TemporaryDirectory()`.

Las 7 pruebas de la actualización de archivos preparados validan: detección de un archivo preparado y modificado después con su versión actual completa en el índice, actualización de varios archivos de una sola operación, rechazo de un archivo que ya no está preparado, rechazo de un archivo sin cambios nuevos, el flujo completo de commit bloqueado hasta actualizar (el commit sigue funcionando normalmente después) y rechazo controlado de rutas con carácter NUL (\x00) antes de ejecutar git add. Fueron ejecutadas en aislamiento y pasaron correctamente. Las correcciones de portabilidad en Windows consisten en: comparación semántica de rutas mediante `Path.resolve()` en las pruebas de configuración, y lectura de `git diff` con `encoding="utf-8"` y `errors="replace"` en los helpers de prueba de actualización de preparados.

"Actualizar preparados" también fue validado MANUALMENTE en Windows con el caso real MM (archivos preparados y vueltos a modificar). Hechos confirmados visualmente: detección de los 4 archivos MM reales (AGENTS.md, CLAUDE.md, TRABAJO_ACTUAL.md y principal.py), columna Preparado con "Sí (hay cambios nuevos)", habilitación del botón solo con selección que lo requiere, confirmación que enumeró únicamente los 4 archivos que realmente necesitaban actualización (aunque la selección fuera más amplia), archivos que mantuvieron su estado preparado sin "vuelto a modificar" después de aceptar, botón deshabilitado cuando ninguno de los seleccionados requería actualización y ningún commit creado durante la prueba.

Las 12 pruebas del inspector de cambios locales validan: archivo modificado sin preparar (diff en `Sin preparar`, preparado vacío), archivo solamente preparado (a la inversa), caso MM con ambos diffs presentes y distintos, conteos de inserciones/eliminaciones mediante `--numstat`, archivo nuevo sin preparar con bandera educativa, archivo eliminado con diff visible, rechazo de ruta con NUL comprobando que no se ejecuta ningún comando (registro de llamadas vacío), ruta con globs/carácter inicial `-` tratada literalmente (`--literal-pathspecs` y `--`), argumentos seguros de todos los diffs interceptando `ejecutar_git()` con un spy (sin ejecutar Git real ni simulaciones especiales en el código de producción: `--no-color`, `--no-ext-diff`, `--no-textconv`, `--cached` solo en el preparado, sin comandos destructivos), consulta que deja el repositorio intacto (`git status` antes/después idéntico), regresión del error de `--numstat`: cuando la llamada falla deliberadamente, `obtener_detalle()` devuelve `exitoso=False` con el mensaje controlado y NUNCA un detalle exitoso con 0 inserciones / 0 eliminaciones; y conflicto expuesto de forma estructurada: con códigos UU y una `descripcion` que NO contiene la palabra "Conflicto", `detalle.en_conflicto` es True (el booleano procede de los códigos de git status, no del texto). Fueron ejecutadas en aislamiento y en la suite completa y pasaron correctamente.

Estado de la etapa inspector de cambios locales: ETAPA VALIDADA MANUALMENTE (prueba manual en Windows EXITOSA, confirmada por el usuario); el inspector forma parte de HEAD desde el commit c62b0a0 (referencia HISTÓRICA) y la corrección del error de --numstat forma parte del commit 634a295 (con Push confirmado; al iniciar la etapa del descarte master == origin/master == 634a295). La etapa "Ramas locales" V1 (con sus microcorrecciones: distinción sin commits / HEAD separado y segunda revalidación TOCTOU; total de 151 pruebas en su momento) quedó incorporada al commit local HEAD "Agrega selector seguro de ramas locales" (consultar git log -1 --oneline para el hash vigente; SIN PUSH). La etapa "Tooltips Didácticos V1 — Fase 2A" (P0/P1; 58 pruebas nuevas; total 209 en su momento, HISTÓRICO) está CERRADA: prueba visual Windows final EXITOSA, commits LOCALES bc57772 (implementación) y 82a32d1 (microcorrección de Fetch y primer Push, hijo de bc57772); SIN PUSH. La etapa del descarte y su cierre técnico ya viven en el commit 3309be7.

## Estado consolidado de la etapa actual

La etapa se considera funcionalmente integrada cuando están presentes:

```text
Historial de solo lectura
Filtros por archivo
Filtro Desde
Filtro Hasta
Orden Fecha ↓
Exportar CSV
Exportar TXT
Configurar GitHub (primer remoto origin)
Primer Push seguro: si la rama remota ya existe puede configurar
upstream; si hay que crearla, solo se permite con remoto vacío de
otras ramas conocidas
Detalle de cambios de un commit (solo lectura)
Persistencia del último repositorio (config.json)
Actualización de archivos preparados
Inspector de cambios locales (solo lectura + descarte de
cambios sin preparar)
Selector y creación segura de ramas LOCALES
Tooltips didácticos V1 (Fase 2A P0/P1 + Fase 2B P2/P3:
37 tooltips centralizados en TEXTOS_AYUDA_GIT_V1, 0 inline;
104 pruebas de tooltips)
255 pruebas OK
```

El historial se ordena explícitamente por fecha de commit descendente
(más reciente -> más antiguo), independientemente del orden topológico
devuelto por `git log`.

CSV y TXT exportan exactamente los commits visibles y conservan ese mismo orden.

## Funcionalidades posteriores

TOOLTIPS DIDÁCTICOS V1 — FASE 2A CERRADA (P0/P1). Esta
fase cubre únicamente los tooltips de las acciones Git más
críticas y de mayor riesgo, sin tocar la lógica Git productiva
ni los servicios. Los textos se almacenan en el diccionario
`TEXTOS_AYUDA_GIT_V1` de `principal.py` (no en un módulo nuevo)
para poder probarlos sin abrir una ventana Tkinter real.

Alcance P0/P1 (13 controles):
- `Fetch` (botón principal) — `git fetch --prune <remoto>`;
- `Pull` (botón principal) — `git pull --ff-only <remoto> <rama-remota>`;
- `Push` (botón principal) — `git push --porcelain [--set-upstream] ...`;
- `Preparar seleccionados` — `git --literal-pathspecs add -- <rutas>`;
- `Actualizar preparados` — `git --literal-pathspecs add -- <rutas>`;
- `Quitar de preparados` — `git --literal-pathspecs restore --staged --` (o `rm --cached` sin commits);
- `Crear commit` — `git commit -m "<mensaje>"`;
- `Descartar cambios sin preparar...` (inspector) — `git --literal-pathspecs restore --worktree -- <ruta>`;
- `Cambiar a seleccionada` (ventana de ramas) — `git switch --no-guess <rama>`;
- `Crear rama` (ventana de ramas) — `git switch -c <nombre>`;
- `Ramas...` (botón principal) — `git for-each-ref` + `git symbolic-ref`;
- `Configurar GitHub...` (botón principal) — flujo educativo, sin credenciales;
- `Agregar origin` (ventana de configuración) — `git remote add origin <url>`.

Cada tooltip didáctico enseña: COMANDO real -> CONCEPTO
(HEAD/working tree/índice/refs remotas) -> QUÉ CAMBIA -> NO HACE ->
REQUISITOS/SEGURIDAD. Los textos no mencionan `git reset --hard`,
`git clean`, `git push --force`, `git merge`, `git rebase` ni
`git cherry-pick` como operaciones a ejecutar (las menciones
legítimas de "no se usa --force" son didácticas y correctas).

Arquitectura de los textos: diccionario `TEXTOS_AYUDA_GIT_V1` en
`principal.py`, consumido por `AyudaEmergente` con `ancho_texto=620`
para los didácticos largos (P0/P1). `ayuda_interfaz.py` NO se
modificó (ya soportaba `ancho_texto` configurable y los textos
largos se renderizan legiblemente).

Pruebas de 2A: 58 pruebas nuevas en
`pruebas/test_ayuda_tooltips_v1.py` verifican fragmentos, comandos
reales y ausencia de operaciones prohibidas sin mover el ratón
(prueban el diccionario, equivalente a probar el contenido del
tooltip). Suite completa entonces: 209 tests OK (151 anteriores +
58 V1). PRUEBA MANUAL EN WINDOWS FINAL: EXITOSA (confirmada por el
usuario). Fase 2A CERRADA: commits LOCALES bc57772
(implementación) y 82a32d1 (microcorrección de Fetch y primer
Push, hijo de bc57772); SIN PUSH.

TOOLTIPS DIDÁCTICOS V1 — FASE 2B CERRADA (P2/P3). Esta
fase centralizó los 14 tooltips secundarios que seguían inline y
añadió 10 tooltips nuevos, todo en el mismo diccionario. Sin
cambios de lógica Git.

- 24 tooltips P2/P3 breves (ancho por defecto, sin
  `ancho_texto=620`): 14 tooltips secundarios existentes
  (5 de la ventana principal y 9 del historial) que estaban
  inline y se centralizaron; 4 ayudas de acciones nuevas
  (Actualizar del Inspector, Copiar diff del Inspector,
  Actualizar de la ventana de ramas, Copiar diff del detalle de
  commit); 6 conceptos de sincronización sobre las etiquetas del
  panel de sincronización (Upstream, Rama remota, Por enviar,
  Por descargar, Estado, Última consulta).
- TOTAL: 37 tooltips centralizados en `TEXTOS_AYUDA_GIT_V1`
  (13 P0/P1 + 24 P2/P3). NO quedan textos literales inline en
  llamadas a `AyudaEmergente`; cada clave se conecta EXACTAMENTE
  una vez (garantizado por pruebas estáticas con `ast`).
- Controles deliberadamente SIN tooltip (excluidos de 2B):
  Cerrar (detalle de commit, Inspector, ramas), Cancelar /
  Abrir GitHub (configuración), etiquetas Rama y "Tiene
  commits", entrada de ruta readonly, barra inferior y la tabla
  del historial.
- Conceptos didácticos importantes:
  - los cuatro botones "Actualizar" (estado local, historial,
    Inspector, ramas) tienen semánticas DISTINTAS y textos
    diferentes: todos son consultas LOCALES, no equivalen a
    Fetch y no consultan el remoto;
  - historial y filtros (archivo, Desde/Hasta) son consultas
    LOCALES de git log; Desde/Hasta filtran por FECHA DEL
    COMMIT;
  - CSV/TXT escriben informes en tu disco, no modifican el
    repositorio ni los commits y no consultan el remoto;
  - Copiar diff es solo portapapeles (pestaña activa en el
    Inspector; diff del commit seleccionado en el detalle);
  - Upstream (rama de seguimiento) NO implica estar
    sincronizado;
  - Rama remota es la rama de seguimiento CONOCIDA
    localmente (con "(no existe)" si falta), no una consulta en
    vivo al servidor;
  - Por enviar / Por descargar cuentan COMMITS, no archivos;
  - Estado de sincronización no es monitorización en tiempo
    real del servidor: compara con la información remota
    conocida localmente;
  - Última consulta refleja operaciones (Fetch/Pull/Push)
    EXITOSAS o FALLIDAS; una operación fallida no implica que la
    información remota se haya actualizado.
- Pruebas: 46 pruebas nuevas de 2B en
  `pruebas/test_ayuda_tooltips_v1.py` (104 específicas totales:
  58 de 2A + 46 de 2B). Suite completa: 255 tests OK
  (209 anteriores + 46 de 2B). MICROCORRECCIÓN previa al cierre:
  se eliminó el test genérico
  test_textos_2b_no_recomiendan_git_destructivo (prohibía
  "git reset"/"git clean" en todos los textos 2B): GestorGit
  puede mencionar legítimamente un comando peligroso para
  explicar que NO lo utiliza; la seguridad protege contra
  operaciones peligrosas CONCRETAS recomendadas
  (`OPERACIONES_PROHIBIDAS` con comandos completos, aplicada a
  TODO el diccionario), no contra su mención educativa.
- PRUEBA MANUAL EN WINDOWS: EXITOSA (confirmada por el
  usuario): ventana principal (Seleccionar, Actualizar,
  Historial, Seleccionar todo, Ver cambios locales), los 6
  conceptos de sincronización, Historial (filtros, Desde/Hasta,
  Aplicar, Limpiar, Ver cambios, CSV, TXT, Actualizar
  historial), detalle de commit (Copiar diff), Inspector
  (Actualizar y Copiar diff), Ramas (Actualizar); Cerrar/
  Cancelar/etc. sin nuevos tooltips; tabla de cambios sin
  tooltip general; tooltips P0/P1 anteriores sin regresión
  visual; acentos, tamaño, legibilidad, aparición/desaparición y
  comportamiento visual OK; ningún tooltip pegado, cortado o
  fuera de pantalla.
- Fase 2B NO cambió lógica Git: servicios Git y
  `ayuda_interfaz.py` INTACTOS.
- COMMIT del cierre: "Cierra tooltips didacticos V1" (hijo de
  0413697, SIN PUSH).

Etapas FUTURAS (documentadas, NO implementadas):

1. Leyenda/ayuda contextual de estados Git para la tabla de
   cambios que enseñe working tree, staging/índice, HEAD,
   `??`, `M`, `MM`, preparado, preparado y vuelto a modificar y
   conflictos (la tabla de cambios quedó deliberadamente SIN
   tooltip general en Fase 2B).
2. La funcionalidad "Publicar rama local" NO se cancela: queda
   documentada como etapa FUTURA separada, fuera del alcance
   actual, con sus propias confirmaciones de seguridad.

## Validación habitual

Desde el proyecto:

```powershell
python -m py_compile .\modelos.py
python -m py_compile .\modelos_historial.py
python -m py_compile .\modelos_configuracion.py
python -m py_compile .\servicio_git.py
python -m py_compile .\servicio_remoto_git.py
python -m py_compile .\servicio_historial_git.py
python -m py_compile .\servicio_exportacion_historial.py
python -m py_compile .\servicio_configuracion.py
python -m py_compile .\principal.py
python -m py_compile .\ayuda_interfaz.py
python -m py_compile .\pruebas\test_historial_git.py
python -m py_compile .\pruebas\test_exportacion_historial.py
python -m py_compile .\pruebas\test_configuracion_remoto_git.py
python -m py_compile .\pruebas\test_configuracion.py
python -m py_compile .\pruebas\test_detalle_commit_git.py
python -m py_compile .\pruebas\test_actualizacion_preparados.py
python -m py_compile .\modelos_cambios_locales.py
python -m py_compile .\servicio_cambios_locales_git.py
python -m py_compile .\servicio_descarte_cambios_git.py
python -m py_compile .\pruebas\test_cambios_locales_git.py
python -m py_compile .\pruebas\test_descarte_cambios_git.py
python -m unittest discover -s .\pruebas -v
git status
```

Después de integrar filtros, exportación, configuración de remoto, endurecimiento del primer Push, detalle de un commit, persistencia del último repositorio, actualización de archivos preparados, inspector de cambios locales, descarte de cambios sin preparar, ramas locales y tooltips didácticos V1 (Fase 2A + Fase 2B), esperar:

```text
Ran 255 tests in ...
OK
```

Si el total no es 255, revisar que estén presentes `pruebas/test_historial_git.py`,
`pruebas/test_exportacion_historial.py`,
`pruebas/test_configuracion_remoto_git.py`,
`pruebas/test_push_git.py`,
`pruebas/test_detalle_commit_git.py`,
`pruebas/test_configuracion.py`,
`pruebas/test_actualizacion_preparados.py`,
`pruebas/test_cambios_locales_git.py`,
`pruebas/test_descarte_cambios_git.py`,
`pruebas/test_ramas_git.py` y
`pruebas/test_ayuda_tooltips_v1.py`.

## Notas del entorno

PowerShell puede mostrar mojibake, por ejemplo:

```text
aplicaciÃ³n
```

Tkinter muestra correctamente los acentos. Es un problema de visualización de consola.

Existió accidentalmente:

```text
C:\Users\victo\.git
```

Se renombró a:

```text
C:\Users\victo\.git_respaldo_accidental_20260817
```

No eliminar ese respaldo automáticamente.

## Cómo continuar otra sesión

1. leer `CLAUDE.md`;
2. ejecutar:

```powershell
git status
git log --oneline --decorate -8
git diff --stat
python -m unittest discover -s .\pruebas -v
```

3. confirmar que cualquier cambio pendiente es conocido y esperado;
4. confirmar que las 255 pruebas pasan;
5. confirmar que tooltips/estética, historial, filtros, orden, exportación,
   configuración inicial de GitHub, detalle de cambios de un commit,
   persistencia del último repositorio, actualización de archivos
   preparados, inspector de cambios locales, descarte de cambios sin
   preparar y selector de ramas locales siguen presentes;
6. la etapa Tooltips Didácticos V1 está CERRADA (37 tooltips
   centralizados en TEXTOS_AYUDA_GIT_V1: 13 P0/P1 de Fase 2A +
   24 P2/P3 de Fase 2B; 104 pruebas específicas; 255 suite
   completa; 0 textos literales inline en llamadas a
   AyudaEmergente; prueba manual Windows de 2A EXITOSA con
   commits locales bc57772 y 82a32d1 SIN PUSH y prueba manual
   Windows de 2B EXITOSA commiteada en "Cierra tooltips
   didacticos V1", hijo de 0413697, SIN PUSH). Después de
   Tooltips V1, las etapas FUTURAS son: la leyenda/ayuda
   contextual de estados Git en la tabla de cambios (working
   tree, staging/índice, HEAD, ??, M, MM, preparado, preparado y
   vuelto a modificar, conflictos) y "Publicar rama local"
   (separada, con sus propias confirmaciones);
7. mantener todas las reglas de seguridad y coordinación entre agentes.

## Coordinación entre agentes

Este proyecto puede ser modificado por más de un agente en paralelo.

Reglas obligatorias:

1. Antes de modificar cualquier archivo:
   - ejecutar `git status --short`;
   - ejecutar `git log -1 --oneline`;
   - leer SIEMPRE la versión actual del archivo antes de editarlo;
   - no trabajar desde backups o copias generadas antiguas.

2. Nunca reemplazar `principal.py` completo utilizando una versión anterior.
   Integrar cambios mediante modificaciones pequeñas sobre la versión actual,
   porque otro agente puede haber agregado funcionalidades en paralelo.

3. Si otro agente está trabajando sobre el mismo archivo, no modificarlo
   en paralelo sin coordinar primero.

4. No normalizar saltos de línea ni reformatear todo un archivo durante
   un cambio funcional.

5. Mantener comentarios, variables, métodos y clases en español.

6. Antes de considerar terminado un cambio ejecutar:
   - `python -m unittest discover -s .\pruebas -v` (resultado esperado: `Ran 255 tests ... OK`);
   - `git diff --check`;
   - `git diff --cached --check`;
   - `git diff --stat`;
   - `git status --short`;
   - no hacer commit automáticamente salvo indicación del usuario.

7. Si una modificación reduce funcionalidades que ya están documentadas
   en `AGENTS.md` o `CLAUDE.md`, detenerse antes de reemplazar el archivo.

Línea base estable:

```text
fe5e49e Agrega historial con filtros y exportacion
```

`fe5e49e` es la línea base estable confirmada, pero después de nuevos commits
no debe asumirse que sigue siendo el HEAD actual. Siempre consultar Git
antes de trabajar.

El historial debe conservar siempre:
- filtros por archivo y fechas;
- orden explícito por fecha de commit descendente;
- cabecera `Fecha ↓`;
- exportación CSV y TXT de los commits visibles;
- detalle de cambios de un commit (solo lectura);
- ninguna operación destructiva desde la ventana de historial.

## Filosofía

El Gestor Git debe priorizar seguridad y comprensión:

```text
ver cambios
 -> preparar
 -> commit
 -> Fetch
 -> Pull si hace falta
 -> Push cuando sea seguro
```

Ante incertidumbre, bloquear la operación y explicar el motivo antes que ejecutar una acción potencialmente destructiva.


## Ajuste de orden del historial

El historial visible debe mostrarse por **fecha de commit descendente**:

```text
más reciente
    ↓
más antiguo
```

La consulta de Git puede devolver commits siguiendo restricciones del grafo,
por lo que `ServicioHistorialGit` ordena explícitamente los `CommitGit`
utilizando `fecha_iso` después de interpretar la salida.

La columna de la interfaz se muestra como:

```text
Fecha ↓
```

para indicar visualmente el orden descendente.

CSV y TXT deben conservar el mismo orden de los commits visibles.
