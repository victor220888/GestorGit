# AGENTS.md

## Orden obligatorio de lectura antes de trabajar

1. AGENTS.md
2. TRABAJO_ACTUAL.md
3. CLAUDE.md cuando se necesite contexto histórico o técnico
4. Ejecutar:
   git status --short
   git log -1 --oneline

Nunca asumir que el HEAD indicado en la documentación sigue siendo actual.

## Propósito

Este archivo resume el contexto técnico y las reglas del proyecto **Gestor Git** para que un agente continúe el trabajo sin depender del historial del chat. El documento de referencia completo es `CLAUDE.md`; mantener ambos actualizados.

## Objetivo del proyecto

Aplicación de escritorio sencilla, educativa y conservadora para trabajar con Git desde Windows, orientada al desarrollo Oracle/PLSQL.

Capacidades esperadas:

- ver el estado de un repositorio;
- detectar archivos nuevos, modificados y eliminados;
- preparar y quitar archivos del staging;
- crear commits locales;
- Fetch;
- calcular commits por enviar y por descargar;
- Push seguro;
- Pull solo mediante fast-forward (`--ff-only`);
- configurar el primer remoto GitHub (origin) cuando no existen remotos;
- enseñar conceptos de Git con textos explicativos y tooltips;
- evitar operaciones destructivas o ambiguas;
- mantener la interfaz responsiva durante operaciones de red.

## Entorno

- Proyecto: `D:\Mi Tierra - Desarrollos\Herramientas\GestorGit`
- Repositorio Oracle real: `D:\Mi Tierra - Desarrollos\Git\Desarrollo-Mi-Tierra-S.A` (ramas `master`, upstream `origin/master`)
- Entorno virtual: `D:\Mi Tierra - Desarrollos\Herramientas\GestorGit\.venv`
- Windows, PowerShell, Python 3.11.5 64-bit, Git 2.45.2.windows.1, Tkinter/ttk, biblioteca estándar de Python

## Convenciones

- comentarios, variables, métodos, clases e interfaz en español;
- identificadores Python sin tildes;
- código simple;
- biblioteca estándar siempre que sea posible;
- Git real mediante `subprocess` (nunca GitPython, nunca `shell=True`);
- no guardar tokens ni credenciales;
- delegar HTTPS a Git/Git Credential Manager.

## Coordinación entre agentes

1. Antes de modificar cualquier archivo:
   - ejecutar `git status --short`;
   - ejecutar `git log -1 --oneline`;
   - leer SIEMPRE la versión actual del archivo antes de editarlo;
   - no trabajar desde backups o copias generadas antiguas.

2. Nunca reemplazar `principal.py` completo usando una copia antigua o un
   archivo generado en una sesión anterior.
   Integrar cambios mediante modificaciones pequeñas sobre la versión actual,
   porque varios agentes pueden haber agregado funcionalidades en paralelo.

3. Si otro agente está trabajando sobre el mismo archivo, no modificarlo
   en paralelo sin coordinar primero.

4. No normalizar saltos de línea ni reformatear todo un archivo durante
   un cambio funcional.

5. Mantener comentarios, variables, métodos y clases en español.

6. Antes de considerar terminado un cambio ejecutar:
   - `python -m unittest discover -s .\pruebas -v` (resultado esperado: `Ran 123 tests ... OK`);
   - `git diff --check`;
   - `git diff --cached --check` (puede mostrar avisos CR-at-EOL
     en líneas CRLF añadidas: causa conocida y documentada);
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

El historial debe conservar estas características:

- filtros por archivo y fechas;
- orden explícito por fecha de commit descendente;
- cabecera `Fecha ↓`;
- exportación CSV y TXT de los commits visibles;
- ninguna operación destructiva desde el historial.

## Arquitectura

- `modelos.py` — dataclasses: `ResultadoComando`, `EstadoRepositorio`, `CambioArchivo`, `ResultadoCambios`, `EstadoSincronizacion`.
- `servicio_git.py` — operaciones Git locales: localizar Git, ejecutar comandos, validar repositorios, rama y remotos, `status --porcelain`, staging (incluida la actualización de archivos preparados con `actualizar_archivos_preparados`), identidad, operaciones en curso, commits, hash actual.
- `servicio_remoto_git.py` — hereda de `ServicioGit`. Selección segura del remoto, Fetch, estado de sincronización, Push seguro, Pull con `--ff-only`, configuración del primer remoto GitHub (`agregar_remoto_github`).
- `modelos_historial.py` — modelos del historial: `CommitGit`, `ResultadoHistorial`, `ResultadoExportacion`.
- `servicio_historial_git.py` — solo lectura: consultas locales de `git log` con separadores de control y parche de un commit (`obtener_cambios_commit`) con `git show`. No ejecuta operaciones remotas ni modifica el repositorio.
- `servicio_exportacion_historial.py` — exporta el historial consultado a CSV (UTF-8 con BOM, `;` como separador, protección contra fórmulas Excel) o TXT con encabezado de repositorio y filtros. No ejecuta Git.
- `modelos_configuracion.py` — dataclass `ResultadoConfiguracion`.
- `servicio_configuracion.py` — persistencia del último repositorio en `config.json`: carga validada y escritura conservadora (archivo temporal + `os.replace`). Nunca guarda credenciales ni ejecuta operaciones remotas.
- `modelos_cambios_locales.py` — modelos del inspector de cambios locales: `DetalleCambioLocal`, `ResultadoDetalleCambioLocal`.
- `servicio_cambios_locales_git.py` — solo lectura: diffs sin preparar y preparados de UN archivo (`--literal-pathspecs`, `--no-color`, `--no-ext-diff`, `--no-textconv`, `--unified=3`), resúmenes `--numstat`, último commit local. Reutiliza un `ServicioGit` existente; validación propia de la ruta relativa.
- `servicio_descarte_cambios_git.py` — descarta los cambios SIN PREPARAR de UN archivo con `git --literal-pathspecs restore --worktree -- <ruta>` (restaura desde el ÍNDICE, no desde HEAD). Conserva el staging, revalida el estado antes del restore y nunca ejecuta operaciones remotas.
- `principal.py` — interfaz Tkinter: selección de repositorio, tabla de cambios, staging (Preparar/Actualizar preparados/Quitar), commit, Fetch, Pull, Push, estado por enviar/por descargar, historial, visor de cambios de un commit, inspector de cambios locales (incluido el botón `Descartar cambios sin preparar...`), carga del último repositorio recordado al iniciar, `threading` + `queue.Queue` para red.
- `ayuda_interfaz.py` — ayuda visual: `AyudaEmergente` y `configurar_estilos`. Sin lógica Git.

## Seguridad

Nunca implementar automáticamente:

```text
git reset --hard
git clean -fd
git push --force
git push --force-with-lease
git branch -D
```

Prohibido sin confirmación explícita:

- borrar `index.lock`;
- resolver conflictos automáticamente;
- Merge o Rebase automáticos;
- elegir remoto al azar;
- guardar PAT/token.

Push se bloquea si hay cambios sin commit, conflictos, operación Git en curso, `index.lock`, detached HEAD, remoto adelantado o divergencia. El primer Push (rama local sin upstream y sin existencia en el remoto) solamente se ejecuta cuando el remoto está vacío de ramas: tras el Fetch previo se consultan las referencias locales del remoto con `git for-each-ref refs/remotes/<remoto>/` y, si existen otras ramas conocidas (o no es posible verificarlo), el Push se bloquea indicando las ramas encontradas.

Pull se bloquea si hay cambios sin commit, commits por enviar, divergencia, falta de upstream, operación Git en curso o `index.lock`. Usa `git pull --ff-only`.

Ante incertidumbre: bloquear la operación y explicar el motivo.

## Configuración inicial de GitHub

`agregar_remoto_github()` configura el PRIMER remoto de un repositorio local:

- permitido solamente cuando el repositorio NO tiene ningún remoto;
- nombre del remoto: `origin`;
- únicamente URLs HTTPS de `github.com` (`https://github.com/usuario/repositorio` o con `.git`);
- nunca credenciales embebidas en la URL (usuario, contraseña o token);
- nunca se modifica, sustituye ni elimina un remoto existente (sin `set-url`, `remove` ni `rename`);
- no ejecuta Fetch, no se conecta a Internet durante `remote add` y no duplica lógica de Push;
- sin API de GitHub, sin PAT/token, sin `gh` CLI.

El flujo enseñado es:

```text
Configurar GitHub
    ↓
Fetch
    ↓
Pull si hiciera falta
    ↓
Push seguro (configura upstream en el primer Push)
```

En la interfaz, el botón `Configurar GitHub...` está habilitado únicamente
cuando existe un repositorio válido sin remotos y no hay operación remota
en curso. La ventana educativa abre `https://github.com/new` en el navegador
(solo abre el navegador; no inicia sesión). Al confirmar `Agregar origin`,
la aplicación recarga el repositorio, exige un Fetch nuevo y deja Pull/Push
deshabilitados hasta que el Fetch sea exitoso.

## Hilos y Tkinter

Fetch, Pull y Push corren en hilos secundarios:

```text
Tkinter -> Thread -> Git -> queue.Queue -> after(...) -> Tkinter
```

Nunca modificar widgets Tkinter desde un hilo secundario.

## Historial

El historial se ordena explícitamente por fecha de commit descendente
(más reciente -> más antiguo), independientemente del orden topológico
devuelto por git log. La interfaz muestra "Fecha ↓". CSV y TXT conservan
el mismo orden visible.

Ventana independiente de solo lectura con columnas `Hash | Fecha ↓ | Autor | Mensaje`, hasta 100 commits. `ServicioHistorialGit` ordena explícitamente los commits por `fecha_iso` descendente (más reciente primero) después de interpretar la salida de `git log`. Filtros combinables (AND):

- `Archivo contiene` — pathspec literal (escapa globs), sin distinguir mayúsculas;
- `Desde` / `Hasta` — `dd/mm/aaaa` en la interfaz, `YYYY-MM-DD` internamente, inclusivos, bloquea rango invertido.

Botones: `Aplicar filtros`, `Limpiar`, `Actualizar historial`. Sin acciones destructivas (no hay Checkout, Reset, Revert, Merge, Rebase ni borrado de commits).

## Detalle de cambios de un commit

Desde el historial, el botón `Ver cambios...` (habilitado solo con un
commit seleccionado) abre la ventana única `Cambios del commit - Gestor Git`,
exclusivamente de SOLO LECTURA. No permite Checkout, Reset, Revert, Merge,
Rebase, restaurar/preparar archivos, crear commits ni ejecutar
Push/Pull/Fetch.

La consulta la realiza `ServicioHistorialGit.obtener_cambios_commit(ruta, hash)`:

- acepta únicamente hashes hexadecimales completos de 40 o 64 caracteres
  (verificados primero con `rev-parse --verify --quiet <hash>^{commit}`);
- usa `git show --format= --no-color --no-ext-diff --no-textconv --unified=3 <hash> --`;
- `--no-ext-diff` evita ejecutar programas de diff externos configurados
  en Git;
- `--no-textconv` evita ejecutar convertidores externos configurados
  en atributos Git;
- nunca utiliza `shell=True`;
- nunca modifica el working tree;
- nunca accede al remoto ni ejecuta Fetch;
- un commit sin cambios devuelve un resultado exitoso con salida vacía.

La ventana muestra datos del commit, advertencia de solo lectura y el diff
coloreado (agregado, eliminado, bloque `@@`, encabezado técnico). Límite
visual de 500000 caracteres; si el diff lo supera, se muestra solo el
comienzo con el aviso `[Vista truncada: ...]`. La truncación es solamente
visual y nunca modifica el repositorio. Botones: `Cerrar` y `Copiar diff`
(portapapeles de Tkinter). Ventana única: si ya existe una abierta, se
destruye y se recrea con el commit solicitado; al cambiar de repositorio
o cerrar el historial, la ventana de detalle también se cierra.

## Exportación

Desde el historial se exportan los commits visibles a CSV o TXT mediante `ServicioExportacionHistorial` (sin ejecutar Git). CSV y TXT conservan el mismo orden de los commits visibles (más reciente primero). El CSV es compatible con Excel en Windows español (BOM + `;`); celdas con `=`, `+`, `-`, `@`, tabulación o CR se anteponen `'` contra fórmulas maliciosas.

## Persistencia del último repositorio

`ServicioConfiguracion` recuerda únicamente el último repositorio
seleccionado manualmente por el usuario.

- `config.json` vive junto a los archivos Python
  (`Path(__file__).resolve().parent / "config.json"`), sin depender
  del directorio desde el cual se ejecute la aplicación;
- estructura permitida:
  `{"ruta_repositorio": "D:\\ruta\\al\\repositorio"}`;
- nunca guarda usuario, correo, contraseña, PAT, token, URLs de
  remotos ni credenciales (Git Credential Manager queda intacto);
- al iniciar se carga el estado LOCAL del repositorio recordado:
  sin Fetch, Pull ni Push automáticos; Pull/Push quedan
  deshabilitados hasta un Fetch manual exitoso;
- un `config.json` inválido o con una ruta que ya no es repositorio
  muestra un aviso en la barra de estado y no impide trabajar;
  no se borra automáticamente;
- la escritura es conservadora: primero se valida la ruta con Git,
  después se escribe un archivo temporal en la misma carpeta y se
  reemplaza con `os.replace`; nunca se sobrescribe una configuración
  válida con una ruta inválida;
- `config.json` está ignorado por `.gitignore` y no forma parte
  del repositorio.

## Actualización de archivos preparados

Concepto: "archivo preparado y vuelto a modificar después".

- se detecta desde el estado estructurado de
  `git status --porcelain` (nunca buscando textos en la
  descripción): `CambioArchivo.requiere_actualizar_preparado`
  es True cuando el archivo está preparado y además existen
  cambios posteriores en el working tree (p. ej. `MM`, `AM`,
  `MD`, `RM`); los conflictos nunca son actualizables;
- lo mismo se muestra en la columna Preparado como
  `Sí (hay cambios nuevos)`;
- el botón `Actualizar preparados` (entre Preparar y Quitar)
  vuelve a ejecutar `git add -- <rutas explícitas>` con
  `--literal-pathspecs` sobre la versión actual; nunca
  `git add .` ni `git add -A`;
- el servicio (`actualizar_archivos_preparados`) validar el
  estado nuevamente antes de ejecutar: cada archivo debe seguir
  preparado, con cambios nuevos fuera del índice y sin conflictos;
  si no, bloquea con mensaje explicando el archivo;
- no deshace cambios, no modifica el working tree, no quita
  archivos del staging y no crea commits;
- GestorGit trabaja a nivel de ARCHIVO: si se preparó solo parte
  de un archivo con otra herramienta, la actualización incluye
  la versión actual completa (la confirmación lo advierte);
- el commit se sigue bloqueando si algún preparado fue
  modificado después, con mensaje educativo que menciona
  `Actualizar preparados`.

Existen 7 pruebas específicas de esta funcionalidad:

- detección de archivo preparado y modificado después;
- actualización que incluye la versión actual completa en el índice;
- actualización múltiple de archivos;
- rechazo de archivo que ya no está preparado;
- rechazo de archivo sin cambios nuevos;
- commit bloqueado hasta actualizar preparados;
- rechazo controlado de rutas con carácter NUL (\x00) antes
  de ejecutar git add.

Las pruebas de portabilidad en Windows normalizan rutas mediante
`Path.resolve()` en lugar de comparación de strings, y los
subprocess que leen diff con acentos usan `encoding="utf-8"`
y `errors="replace"`.

## Inspector de cambios locales

Ventana de inspección de cambios locales que enseña qué cambió en
UN archivo antes de prepararlo, después de prepararlo, o en ambos
lugares a la vez. Las CONSULTAS y los visores son de SOLO LECTURA,
pero la ventana incorpora además una acción destructiva controlada
y separada: `Descartar cambios sin preparar...` (sección
siguiente), exclusiva de la pestaña `Sin preparar`.
`ServicioCambiosLocalesGit` reutiliza el `ServicioGit` existente;
`servicio_git.py` no se modifica.

PRUEBA MANUAL EN WINDOWS: EXITOSA (confirmada por el usuario).

Casos confirmados visualmente:

- archivo modificado sin preparar: la pestaña `Sin preparar`
  muestra el diff y `Preparados` queda vacía;
- archivo preparado: `Preparados` muestra el diff que entraría
  al commit;
- caso MM ("Modificado, preparado y vuelto a modificar" con
  Preparado = "Sí (hay cambios nuevos)"): la pestaña
  `Sin preparar` muestra únicamente los cambios posteriores al
  staging y `Preparados` conserva el diff previamente preparado;
  ambos diffs son distintos;
- resúmenes de inserciones/eliminaciones visibles;
- colores `+` / `-` / `@@` funcionan;
- scroll horizontal y vertical funcionan;
- `Actualizar` refresca únicamente el estado LOCAL;
- `Copiar diff` funciona;
- `Ver cambios locales...` se habilita con exactamente un archivo
  y se deshabilita con selección múltiple.

Resto del comportamiento:

- el botón `Ver cambios locales...` está habilitado únicamente con
  exactamente UN archivo seleccionado en la tabla de cambios;
- ventana única `Cambios locales - Gestor Git` (se destruye y recrea
  al abrir de nuevo; se cierra al cambiar de repositorio);
- la consulta NO prepara ni quita archivos, no crea commits, no
  ejecuta Fetch/Pull/Push y nunca modifica el repositorio; la
  única acción que modifica el working tree es el botón
  `Descartar cambios sin preparar...` (sección siguiente);
- pestañas `Sin preparar` (working tree -> índice, equivale a
  `git diff`) y `Preparados` (índice -> HEAD, equivale a
  `git diff --cached`); en el caso `MM` ambas pueden contener
  cambios distintos;
- comandos conceptuales para el diff sin preparar:

  ```text
  git --literal-pathspecs diff --no-color --no-ext-diff
      --no-textconv --unified=3 -- <ruta>
  ```

  y con `--cached` insertado después de `diff` para el preparado;
  siempre listas de argumentos, nunca `shell=True`, siempre `--`
  antes del pathspec;
- resúmenes de inserciones/eliminaciones mediante `--numstat`
  (nunca interpretando texto localizado de `--stat`); un binario
  devuelve `-` y se muestra `Archivo binario` sin convertir el
  texto a entero;
- si `--numstat` FALLA, la consulta devuelve un error controlado
  (nunca 0 inserciones / 0 eliminaciones falsos);
- un archivo nuevo sin preparar (`??`) no inventa diffs ni lee el
  archivo: muestra un mensaje educativo explicando que Git aún no
  tiene versión anterior para comparar;
- un archivo que ya no tiene cambios devuelve "El archivo ya no
  tiene cambios locales pendientes." (resultado normal, no error);
  el botón `Actualizar` solo consulta el estado LOCAL;
- `Copiar diff` copia el contenido visible de la pestaña activa;
- la ruta debe ser relativa al repositorio: se rechazan controladas
  ruta vacía, ruta absoluta, `..` y NUL antes de construir/ejecutar
  cualquier diff (validación propia del servicio, sin acoplarse a
  métodos privados de `ServicioGit`);
- límite visual de 500000 caracteres con aviso
  `[Vista truncada: ...]`; la truncación es solo visual;
- visor `tk.Text` de solo lectura, `wrap=tk.NONE`, fuente Consolas,
  colores como el visor de cambios de commits; reutiliza
  `_tag_para_linea_diff` sin refactorizar el visor histórico;
- hay 12 pruebas específicas en
  `pruebas/test_cambios_locales_git.py` (archivo, modificación,
  MM, numstat, error de numstat, archivo nuevo, eliminado, NUL,
  pathspecs literales, argumentos seguros interceptando
  `ejecutar_git()` con un spy, no-modificación del repositorio y
  conflicto expuesto de forma estructurada con `en_conflicto`).

## Descarte de cambios sin preparar

Operación explícita y controlada dentro de la ventana del Inspector
(`Cambios locales - Gestor Git`), exclusiva de la pestaña
`Sin preparar`. PRUEBA MANUAL EN WINDOWS: EXITOSA (confirmada por
el usuario).

Casos confirmados manualmente en Windows:

- caso A (archivo modificado sin preparar): el Inspector muestra
  el diff, Preparado = No, el botón queda habilitado en
  `Sin preparar` y deshabilitado en `Preparados`; tras la
  confirmación el descarte funciona y el archivo vuelve a HEAD;
- caso B (MM): A preparada y B agregada después; estado
  "Modificado, preparado y vuelto a modificar", Preparado =
  "Sí (hay cambios nuevos)", `Preparados` muestra A y
  `Sin preparar` muestra B; el descarte elimina B, A permanece
  preparada, `git diff` vuelve a quedar vacío y `git diff --cached`
  conserva A; después, quitar de preparados conserva A en el
  working tree, un segundo descarte elimina A y servicio_git.py
  vuelve exactamente a HEAD;
- caso C (archivo nuevo ??): estado Nuevo, Preparado No, mensaje
  educativo, botón de descarte deshabilitado desde el primer
  momento (también en `Preparados`); `Test-Path` confirmó que el
  archivo sigue existiendo: GestorGit no lo eliminó;
- caso D (archivo solamente preparado): `Sin preparar` vacío y el
  botón de descarte deshabilitado;
- caso E (actualización visual): tras el descarte el Inspector se
  actualiza correctamente y, cuando ya no quedan cambios, muestra
  "El archivo ya no tiene cambios locales pendientes.";
- caso F (Fetch simultáneo): NO APLICABLE desde la GUI actual
  (con el Inspector abierto no fue posible interactuar con Fetch
  de la ventana principal); documentado como limitación, no como
  fallo ni prueba exitosa.

Comportamiento:

- botón `Descartar cambios sin preparar...` junto a
  `Actualizar` / `Copiar diff` / `Cerrar`;
- se habilita únicamente cuando la pestaña activa es
  `Sin preparar`, el archivo inspeccionado tiene cambios SIN
  PREPARAR reales, no es nuevo (??) y no está en conflicto;
  al cambiar de pestaña el botón queda deshabilitado;
- antes de la confirmación se vuelve a consultar el estado LOCAL
  del archivo (sin Fetch) y la vista se actualiza; el servicio
  revalida otra vez justo antes del restore;
- confirmación fuerte con messagebox que cita explícitamente la
  ruta y explica qué versión quedará (staging, o índice/HEAD si
  no hay preparados) y que los cambios preparados SE CONSERVAN;
- comando productivo exacto:

  ```text
  git --literal-pathspecs restore --worktree -- <ruta>
  ```

  construido SIEMPRE como lista de argumentos (nunca
  `shell=True`); sin `--source`: restaura desde el ÍNDICE, no
  desde HEAD; nunca `--staged`, `git restore .`, `checkout`,
  `reset`, `clean`, `add`, `rm`;
- un archivo nuevo (??) se rechaza con mensaje educativo: nunca
  se ejecuta `os.remove`, `Path.unlink` ni `git clean`;
- los conflictos se bloquean (DD, AU, UD, UA, DU, AA, UU) con
  mensaje educativo; la decisión usa el booleano estructurado
  `detalle.en_conflicto` de `DetalleCambioLocal` (calculado en
  `ServicioCambiosLocalesGit._calcular_en_conflicto` desde
  `estado_indice` + `estado_trabajo`, nunca desde el texto
  localizado de `descripcion`); `ServicioDescarteCambiosGit`
  conserva además su revalidación estructurada propia antes del
  restore;
- la regla de los estados permitidos se basa en
  `estado_indice` / `estado_trabajo` (nunca en `descripcion`):
  el working tree debe tener una diferencia real respecto del
  índice; funcionan " M", " D", MM, MD, AM y equivalentes;
- `ServicioDescarteCambiosGit` reutiliza el `ServicioGit`
  existente, tiene validación propia de la ruta (None, vacía,
  espacios, NUL antes de construir `Path`, absoluta, `..`) y
  nunca duplica `subprocess.run`;
- si hay una operación remota en curso (Fetch/Pull/Push), el
  botón de descarte queda deshabilitado y
  `descartar_cambios_sin_preparar()` se bloquea al principio con
  un mensaje controlado, sin consulta ni confirmación previas
  (defensa en profundidad, independiente de la modalidad de las
  ventanas); `actualizar_controles_operacion_remota()` recalcula
  el botón de forma segura cuando el Inspector no existe;
- después del restore: se refresca la tabla principal y el
  Inspector, no se cierra la ventana, no se hace Fetch y se
  muestra un mensaje breve de éxito; si el archivo ya no tiene
  cambios, el Inspector maneja normalmente "El archivo ya no
  tiene cambios locales pendientes." y la fila desaparece;
- caso MM esperado: tras el descarte el archivo queda
  `Modificado y preparado` con Preparado = `Sí`, `Sin preparar`
  vacía (0 inserciones · 0 eliminaciones) y `Preparados`
  conservando exactamente su diff;
- staging intacto: `git diff --cached -- <ruta>` antes y después
  del descarte son IDÉNTICOS;
- no Fetch/Pull/Push; no se altera `fetch_exitoso_en_sesion`;
  no se crean commits ni se modifica HEAD;
- hay 17 pruebas específicas en
  `pruebas/test_descarte_cambios_git.py` (" M", MM, " D", MD,
  AM sin versión en HEAD (restaura desde el índice), ?? con y
  sin spy, solamente preparado con y sin spy, NUL,
  ruta absoluta, `..`, guion/caracteres especiales literales,
  argumentos exactos del restore, verbos prohibidos —se
  identifica el VERBO real, un archivo llamado `reset` solo
  aparece como pathspec—, otro archivo sin seleccionar conserva
  cambios y conflicto UU).

## Pruebas

123 pruebas automatizadas en `pruebas/`. Ejecutar:

```powershell
python -m unittest discover -s .\pruebas -v
```

Resultado esperado:

```text
Ran 123 tests in ...
OK
```

Las pruebas nunca tocan GitHub ni el repositorio Oracle real; usan `tempfile.TemporaryDirectory()`.

## Validación habitual

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

Nota: PowerShell puede mostrar mojibake (p. ej. `aplicaciÃ³n`); Tkinter muestra los acentos correctamente.

## Siguiente etapa

- eventualmente: selector/creación segura de ramas.

## Filosofía

```text
ver cambios -> preparar -> commit -> Fetch -> Pull si hace falta -> Push cuando sea seguro
```

Seguridad y comprensión primero; bloquear y explicar antes que ejecutar algo potencialmente destructivo.
