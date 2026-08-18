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
- Pull seguro mediante `--ff-only`.

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
- estado por enviar/por descargar;
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

Último estado estable confirmado:

```text
fe5e49e Agrega historial con filtros y exportacion
```

Estado validado de esa línea base:

- 65 pruebas automatizadas OK;
- `git diff --check` OK;
- `principal.py` integra filtros del historial;
- historial ordenado explícitamente por fecha de commit descendente;
- interfaz con cabecera `Fecha ↓`;
- exportación CSV y TXT integrada en la GUI;
- `modelos_historial.py` contiene `CommitGit`, `ResultadoHistorial` y `ResultadoExportacion`;
- `servicio_exportacion_historial.py` integrado;
- Push sigue siendo seguro y nunca forzado;
- Pull continúa exclusivamente con `--ff-only`.

## Pruebas

El proyecto tiene actualmente **65 pruebas automatizadas**:

- 49 pruebas base de operaciones locales/remotas;
- 11 pruebas del historial;
- 5 pruebas de exportación.

Archivos principales de pruebas:

```text
pruebas/test_servicio_git.py
pruebas/test_commit_git.py
pruebas/test_sincronizacion_git.py
pruebas/test_push_git.py
pruebas/test_pull_git.py
pruebas/test_historial_git.py
pruebas/test_exportacion_historial.py
```

Resultado esperado:

```text
Ran 65 tests in ...
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

El conjunto anterior tenía 49 pruebas fuera del historial. A las 11 pruebas del historial se agregan 5 pruebas de exportación. El total esperado es:

```text
65 pruebas
OK
```

Las 5 pruebas de exportación validan CSV, TXT, lista vacía, errores de escritura y protección contra fórmulas CSV. Fueron ejecutadas en aislamiento y pasaron correctamente.

## Estado consolidado de la etapa actual

La etapa de historial se considera funcionalmente integrada cuando están presentes:

```text
Historial de solo lectura
Filtros por archivo
Filtro Desde
Filtro Hasta
Orden Fecha ↓
Exportar CSV
Exportar TXT
65 pruebas OK
```

El historial se ordena explícitamente por fecha de commit descendente
(más reciente -> más antiguo), independientemente del orden topológico
devuelto por `git log`.

CSV y TXT exportan exactamente los commits visibles y conservan ese mismo orden.

## Funcionalidades posteriores

Después de estabilizar el historial con filtros y exportación:

1. recordar el último repositorio seleccionado;
2. persistir configuración en `config.json`;
3. nunca guardar credenciales;
4. eventualmente mostrar detalles ampliados de un commit;
5. eventualmente selector/creación segura de ramas.

## Validación habitual

Desde el proyecto:

```powershell
python -m py_compile .\modelos.py
python -m py_compile .\modelos_historial.py
python -m py_compile .\servicio_git.py
python -m py_compile .\servicio_remoto_git.py
python -m py_compile .\servicio_historial_git.py
python -m py_compile .\servicio_exportacion_historial.py
python -m py_compile .\principal.py
python -m py_compile .\ayuda_interfaz.py
python -m py_compile .\pruebas\test_historial_git.py
python -m py_compile .\pruebas\test_exportacion_historial.py
python -m unittest discover -s .\pruebas -v
git status
```

Después de integrar filtros y exportación, esperar:

```text
Ran 65 tests in ...
OK
```

Si el total no es 65, revisar que estén presentes tanto `pruebas/test_historial_git.py` como `pruebas/test_exportacion_historial.py`.

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
4. confirmar que las 65 pruebas pasan;
5. confirmar que tooltips/estética, historial, filtros, orden y exportación siguen presentes;
6. si la etapa actual está estable, continuar con persistencia del último repositorio seleccionado;
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
   - `python -m unittest discover -s .\pruebas -v` (resultado esperado: `Ran 65 tests ... OK`);
   - `git diff --check`;
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
