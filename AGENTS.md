# AGENTS.md

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
   - ejecutar `git status`;
   - leer la versión ACTUAL del archivo en el working tree;
   - no trabajar desde backups o copias generadas antiguas.

2. No reemplazar `principal.py` completo usando una versión anterior.
   Integrar siempre sobre la versión actual, porque varios agentes pueden
   haber agregado funcionalidades en paralelo.

3. Antes de entregar cambios:
   - ejecutar `git diff --stat`;
   - revisar `git diff` de cada archivo modificado;
   - comprobar que no desaparecieron funcionalidades existentes.

4. Si otro agente está trabajando en el mismo momento, evitar modificar
   los mismos archivos cuando sea posible. Si es inevitable, reconciliar
   explícitamente ambas versiones antes de reemplazar nada.

5. La fuente de verdad es, en este orden:
   - archivos actuales del working tree;
   - pruebas automatizadas;
   - `AGENTS.md` / `CLAUDE.md`;
   - backups antiguos solo como referencia.

6. Después de cualquier cambio funcional:
   - compilar módulos afectados;
   - ejecutar las 65 pruebas;
   - comprobar `git status`;
   - no hacer commit automáticamente salvo indicación del usuario.

7. El historial debe conservar estas características:
   - filtros por archivo y fechas;
   - orden explícito por fecha de commit descendente;
   - cabecera `Fecha ↓`;
   - exportación CSV y TXT de los commits visibles;
   - ninguna operación destructiva desde el historial.

## Arquitectura

- `modelos.py` — dataclasses: `ResultadoComando`, `EstadoRepositorio`, `CambioArchivo`, `ResultadoCambios`, `EstadoSincronizacion`.
- `servicio_git.py` — operaciones Git locales: localizar Git, ejecutar comandos, validar repositorios, rama y remotos, `status --porcelain`, staging, identidad, operaciones en curso, commits, hash actual.
- `servicio_remoto_git.py` — hereda de `ServicioGit`. Selección segura del remoto, Fetch, estado de sincronización, Push seguro, Pull con `--ff-only`.
- `modelos_historial.py` — modelos del historial: `CommitGit`, `ResultadoHistorial`, `ResultadoExportacion`.
- `servicio_historial_git.py` — solo lectura: consultas locales de `git log` con separadores de control. No ejecuta operaciones remotas ni modifica el repositorio.
- `servicio_exportacion_historial.py` — exporta el historial consultado a CSV (UTF-8 con BOM, `;` como separador, protección contra fórmulas Excel) o TXT con encabezado de repositorio y filtros. No ejecuta Git.
- `principal.py` — interfaz Tkinter: selección de repositorio, tabla de cambios, staging, commit, Fetch, Pull, Push, estado por enviar/por descargar, `threading` + `queue.Queue` para red.
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

Push se bloquea si hay cambios sin commit, conflictos, operación Git en curso, `index.lock`, detached HEAD, remoto adelantado o divergencia.

Pull se bloquea si hay cambios sin commit, commits por enviar, divergencia, falta de upstream, operación Git en curso o `index.lock`. Usa `git pull --ff-only`.

Ante incertidumbre: bloquear la operación y explicar el motivo.

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

## Exportación

Desde el historial se exportan los commits visibles a CSV o TXT mediante `ServicioExportacionHistorial` (sin ejecutar Git). CSV y TXT conservan el mismo orden de los commits visibles (más reciente primero). El CSV es compatible con Excel en Windows español (BOM + `;`); celdas con `=`, `+`, `-`, `@`, tabulación o CR se anteponen `'` contra fórmulas maliciosas.

## Pruebas

65 pruebas automatizadas en `pruebas/`. Ejecutar:

```powershell
python -m unittest discover -s .\pruebas -v
```

Resultado esperado:

```text
Ran 65 tests in ...
OK
```

Las pruebas nunca tocan GitHub ni el repositorio Oracle real; usan `tempfile.TemporaryDirectory()`.

## Validación habitual

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

Nota: PowerShell puede mostrar mojibake (p. ej. `aplicaciÃ³n`); Tkinter muestra los acentos correctamente.

## Siguiente etapa

- recordar el último repositorio seleccionado;
- persistir configuración en `config.json`;
- nunca guardar credenciales;
- eventualmente: detalles ampliados de un commit; selector/creación segura de ramas.

## Filosofía

```text
ver cambios -> preparar -> commit -> Fetch -> Pull si hace falta -> Push cuando sea seguro
```

Seguridad y comprensión primero; bloquear y explicar antes que ejecutar algo potencialmente destructivo.
