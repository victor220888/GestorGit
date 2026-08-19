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
- inspector de cambios locales (solo lectura);
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
  nuevo_sin_preparar, hash y mensaje del último commit);
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

Etapa: inspector de cambios locales (SOLO LECTURA).
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
- ninguna operación destructiva ni remota.

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

## Pruebas

El proyecto tiene actualmente **105 pruebas automatizadas**:

- 49 pruebas base de operaciones locales/remotas;
- 11 pruebas del historial;
- 5 pruebas de exportación;
- 7 pruebas de configuración inicial del remoto GitHub;
- 1 prueba del primer Push con remoto no vacío;
- 6 pruebas del detalle de cambios de un commit;
- 8 pruebas de la persistencia del último repositorio;
- 7 pruebas de la actualización de archivos preparados;
- 11 pruebas del inspector de cambios locales.

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
```

Resultado esperado:

```text
Ran 105 tests in ...
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
Ran 105 tests in ...
OK
```

Nota: ese total de 79 es HISTÓRICO, anterior a la etapa de
persistencia. El total de 94 (49 + 11 + 5 + 7 + 1 + 6 + 8 + 7
pruebas de la actualización de archivos preparados) es también
HISTÓRICO (commit 014e3f7). El total de 104 (94 + 10 pruebas del
inspector) fue el confirmado en el commit c62b0a0. El total ACTUAL
es 105 (104 + 1 prueba de regresión del error de --numstat).

Las 5 pruebas de exportación validan CSV, TXT, lista vacía, errores de escritura y protección contra fórmulas CSV. Fueron ejecutadas en aislamiento y pasaron correctamente.

Las 7 pruebas de configuración del remoto validan: creación de `origin`, URL vacía, HTTP, host distinto de GitHub, credenciales embebidas, repositorio con remoto existente y configuración sin contacto de red. Fueron ejecutadas en aislamiento y pasaron correctamente, sin tocar GitHub.

La prueba del primer Push con remoto no vacío valida el escenario peligroso (remoto con rama `main`, rama local `master`): el Push se rechaza, el mensaje menciona `origin/main` y `refs/heads/master` NO se crea en el remoto. Fue ejecutada en aislamiento y pasó correctamente.

Las 6 pruebas del detalle de un commit validan: archivo agregado visible en el parche, modificación con línea eliminada y agregada, repositorio sin cambios después de la consulta, rechazo de hashes inválidos sin ejecutar `git show`, rechazo de hash inexistente con error controlado y uso de `--no-ext-diff`/`--no-textconv`/`--no-color` sin comandos destructivos. Fueron ejecutadas en aislamiento y pasaron correctamente.

Las 8 pruebas de la persistencia validan: config.json inexistente (primer inicio), guardar y cargar un repositorio válido, JSON malformado sin excepción, ruta inexistente, carpeta sin `.git`, escritura que conserva únicamente `ruta_repositorio`, guardado inválido que no sobrescribe la configuración válida y rechazo de ruta que no es texto. Fueron ejecutadas en aislamiento y pasaron correctamente, usando únicamente `tempfile.TemporaryDirectory()`.

Las 7 pruebas de la actualización de archivos preparados validan: detección de un archivo preparado y modificado después con su versión actual completa en el índice, actualización de varios archivos de una sola operación, rechazo de un archivo que ya no está preparado, rechazo de un archivo sin cambios nuevos, el flujo completo de commit bloqueado hasta actualizar (el commit sigue funcionando normalmente después) y rechazo controlado de rutas con carácter NUL (\x00) antes de ejecutar git add. Fueron ejecutadas en aislamiento y pasaron correctamente. Las correcciones de portabilidad en Windows consisten en: comparación semántica de rutas mediante `Path.resolve()` en las pruebas de configuración, y lectura de `git diff` con `encoding="utf-8"` y `errors="replace"` en los helpers de prueba de actualización de preparados.

"Actualizar preparados" también fue validado MANUALMENTE en Windows con el caso real MM (archivos preparados y vueltos a modificar). Hechos confirmados visualmente: detección de los 4 archivos MM reales (AGENTS.md, CLAUDE.md, TRABAJO_ACTUAL.md y principal.py), columna Preparado con "Sí (hay cambios nuevos)", habilitación del botón solo con selección que lo requiere, confirmación que enumeró únicamente los 4 archivos que realmente necesitaban actualización (aunque la selección fuera más amplia), archivos que mantuvieron su estado preparado sin "vuelto a modificar" después de aceptar, botón deshabilitado cuando ninguno de los seleccionados requería actualización y ningún commit creado durante la prueba.

Las 11 pruebas del inspector de cambios locales validan: archivo modificado sin preparar (diff en `Sin preparar`, preparado vacío), archivo solamente preparado (a la inversa), caso MM con ambos diffs presentes y distintos, conteos de inserciones/eliminaciones mediante `--numstat`, archivo nuevo sin preparar con bandera educativa, archivo eliminado con diff visible, rechazo de ruta con NUL comprobando que no se ejecuta ningún comando (registro de llamadas vacío), ruta con globs/carácter inicial `-` tratada literalmente (`--literal-pathspecs` y `--`), argumentos seguros de todos los diffs interceptando `ejecutar_git()` con un spy (sin ejecutar Git real ni simulaciones especiales en el código de producción: `--no-color`, `--no-ext-diff`, `--no-textconv`, `--cached` solo en el preparado, sin comandos destructivos), consulta que deja el repositorio intacto (`git status` antes/después idéntico) y regresión del error de `--numstat`: cuando la llamada falla deliberadamente, `obtener_detalle()` devuelve `exitoso=False` con el mensaje controlado y NUNCA un detalle exitoso con 0 inserciones / 0 eliminaciones. Fueron ejecutadas en aislamiento y en la suite completa y pasaron correctamente.

Estado de la etapa inspector de cambios locales: ETAPA VALIDADA MANUALMENTE (prueba manual en Windows EXITOSA, confirmada por el usuario); el inspector forma parte de HEAD desde el commit c62b0a0, con Push confirmado (origin/master apunta a c62b0a0); los cambios de esta tarea de cierre documental y corrección de --numstat viven únicamente en el working tree actual.

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
Primer Push solo con remoto vacío de ramas
Detalle de cambios de un commit (solo lectura)
Persistencia del último repositorio (config.json)
Actualización de archivos preparados
Inspector de cambios locales (solo lectura)
105 pruebas OK
```

El historial se ordena explícitamente por fecha de commit descendente
(más reciente -> más antiguo), independientemente del orden topológico
devuelto por `git log`.

CSV y TXT exportan exactamente los commits visibles y conservan ese mismo orden.

## Funcionalidades posteriores

- eventualmente selector/creación segura de ramas;
- posible etapa futura (NO implementada todavía):
  "Descartar cambios sin preparar" desde el inspector.

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
python -m py_compile .\pruebas\test_cambios_locales_git.py
python -m unittest discover -s .\pruebas -v
git status
```

Después de integrar filtros, exportación, configuración de remoto, endurecimiento del primer Push, detalle de un commit, persistencia del último repositorio, actualización de archivos preparados e inspector de cambios locales, esperar:

```text
Ran 105 tests in ...
OK
```

Si el total no es 105, revisar que estén presentes `pruebas/test_historial_git.py`,
`pruebas/test_exportacion_historial.py`,
`pruebas/test_configuracion_remoto_git.py`,
`pruebas/test_push_git.py`,
`pruebas/test_detalle_commit_git.py`,
`pruebas/test_configuracion.py`,
`pruebas/test_actualizacion_preparados.py` y
`pruebas/test_cambios_locales_git.py`.

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
4. confirmar que las 105 pruebas pasan;
5. confirmar que tooltips/estética, historial, filtros, orden, exportación,
   configuración inicial de GitHub, detalle de cambios de un commit,
   persistencia del último repositorio, actualización de archivos
   preparados e inspector de cambios locales siguen presentes;
6. si la etapa actual está estable, continuar con el selector/creación segura de ramas;
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
   - `python -m unittest discover -s .\pruebas -v` (resultado esperado: `Ran 105 tests ... OK`);
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
