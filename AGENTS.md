# AGENTS.md

## Propósito

Archivo de configuración para ZCode, OpenCode y otros agentes que consumen
`AGENTS.md`.

Debe ser suficiente para trabajar con seguridad sin leer `CLAUDE.md`.
Contiene reglas ESTABLES. El estado dinámico vive en `TRABAJO_ACTUAL.md`.

## Lectura obligatoria antes de trabajar

1. Leer `AGENTS.md`.
2. Leer `TRABAJO_ACTUAL.md`.
3. Consultar Git real:
   - `git status --short`
   - `git status -sb`
   - `git log -1 --oneline`
   - `git branch -vv`
   - `git diff --cached --name-only`
   - comprobar `.git/index.lock`
4. Leer la versión ACTUAL de cada archivo que se vaya a modificar.

No leer `CLAUDE.md`, `METODO_TRABAJO_AGENTES.md`, `README.md` ni
`seguimiento_prompts/` por defecto. Solo hacerlo si el prompt lo exige o
hace falta resolver una contradicción concreta.

Git manda sobre hashes, conteos de pruebas o estados escritos en documentos.

## Proyecto

GestorGit es una aplicación de escritorio educativa y conservadora para
trabajar con Git desde Windows, orientada especialmente a desarrollo
Oracle/PLSQL.

Entorno habitual:

- proyecto: `D:\Mi Tierra - Desarrollos\Herramientas\GestorGit`
- repositorio Oracle real:
  `D:\Mi Tierra - Desarrollos\Git\Desarrollo-Mi-Tierra-S.A`
- Python 3.11.x
- Git 2.45.x para Windows
- Tkinter/ttk
- biblioteca estándar
- Git real mediante `subprocess`

## Roles

- ChatGPT: orquestador, diseñador de prompts y auditor técnico.
- Agente programador activo: implementa SOLO el alcance autorizado.
- Usuario: decide prioridades, ejecuta pruebas manuales/visuales y autoriza
  staging, commit y Push.

Solo puede existir UN agente programador modificando el repositorio a la vez.
Otro agente solo puede actuar en paralelo si fue autorizado expresamente como
solo lectura.

El informe del agente es provisional hasta la revisión de ChatGPT y, cuando
corresponda, la prueba manual del usuario.

## Alcance y bitácora

- Ejecutar únicamente la tarea recibida.
- Modificar únicamente archivos autorizados.
- No iniciar la siguiente etapa por iniciativa propia.
- No administrar `seguimiento_prompts/`.
- No asignar IDs `GG-PROMPT`.
- No crear archivos `GG-PROMPT-XXX-RESULTADO.md` salvo instrucción expresa.
- Al terminar: validar, informar y DETENERSE.

`seguimiento_prompts/README.md` es un índice vivo.
Los prompts, REV, ADDENDUM y RESULTADO históricos se preservan.

## Convenciones

- interfaz, comentarios, variables, métodos y clases en español;
- identificadores Python sin tildes;
- código simple y conservador;
- biblioteca estándar cuando sea posible;
- nunca GitPython;
- nunca `shell=True`;
- nunca guardar credenciales, PAT o tokens;
- HTTPS y autenticación se delegan a Git/Git Credential Manager;
- cambios pequeños sobre archivos actuales;
- nunca reemplazar `principal.py` completo desde una copia antigua;
- no reformatear ni normalizar line endings masivamente.

## Arquitectura mínima

- `modelos.py`: resultados/estado/cambios/sincronización.
- `servicio_git.py`: operaciones Git locales, status, staging, commit,
  identidad, locks/operaciones en curso.
- `servicio_remoto_git.py`: Fetch, sincronización, Push/Pull seguros,
  configuración de remoto y publicación segura de rama local.
- `servicio_ramas_git.py`: listar/cambiar/crear ramas LOCALES.
- `servicio_historial_git.py`: historial y detalle de commit, solo lectura.
- `servicio_configuracion.py`: último repositorio local.
- `servicio_cambios_locales_git.py`: inspección de cambios.
- `servicio_descarte_cambios_git.py`: descarte controlado de cambios sin
  preparar preservando el índice.
- `principal.py`: GUI Tkinter y coordinación.
- `ayuda_interfaz.py`: ayuda visual, sin lógica Git.
- `pruebas/`: `unittest`.

Consultar `TRABAJO_ACTUAL.md` para el alcance funcional vigente y los archivos
de la tarea actual.

## Seguridad Git obligatoria

Nunca ejecutar automáticamente:

```text
git reset --hard
git clean -fd
git push --force
git push --force-with-lease
git branch -D
```

También está prohibido sin autorización explícita:

- borrar `.git/index.lock`;
- resolver conflictos automáticamente;
- Merge/Rebase automáticos;
- elegir un remoto al azar;
- almacenar credenciales;
- `git add .` o `git add -A` en cierres controlados.

Ante incertidumbre: BLOQUEAR y explicar.

No ejecutar sobre GestorGit `git add`, staging, commit, Fetch, Pull o Push
salvo autorización explícita de la tarea ACTUAL. Una autorización anterior
no se hereda.

## Reglas funcionales que no deben degradarse

- Pull únicamente con `--ff-only`.
- Push nunca forzado.
- Conflictos se representan mediante estado estructurado
  (`CambioArchivo.en_conflicto`), no por textos localizados.
- Rutas de staging explícitas; no `git add .`.
- Operaciones remotas mantienen la GUI responsiva:
  `Tkinter -> Thread -> Git -> queue.Queue -> after(...) -> Tkinter`.
- Nunca tocar widgets Tkinter desde un hilo secundario.
- Errores de consulta Git no se interpretan como estado seguro/limpio.
- `index.lock` se detecta y bloquea; nunca se elimina automáticamente.

## Pruebas y cierre de una tarea

Ejecutar las pruebas indicadas por el prompt.

Si el prompt pide suite completa:

```powershell
python -m unittest discover -s .\pruebas -v
```

No usar aquí un número fijo como “total esperado”; el total vigente está en
`TRABAJO_ACTUAL.md` y debe confirmarse por ejecución.

Validaciones habituales cuando correspondan:

```text
py_compile focalizado
tests focalizados
suite completa
git diff --check
git diff --cached --check
git diff --cached --name-only
git diff --stat
git status --short
```

## Informe final compacto

Salvo que el prompt pida otro formato, reportar SOLO:

1. estado Git inicial y anomalías;
2. archivos modificados;
3. cambio realizado;
4. pruebas focalizadas;
5. suite completa (total real) si se ejecutó;
6. `diff --check` / staging / lock;
7. operaciones remotas y commit: sí/no;
8. pendientes o hallazgos.

No pegar logs completos que hayan terminado correctamente.
Incluir salida extensa solo ante fallos o si el prompt la exige.

## Documentación dinámica

No añadir a este archivo:

- HEAD actual;
- `ahead/behind` actual;
- número actual de tests;
- prompt activo;
- lista temporal de archivos modificados;
- resultados detallados de una etapa.

Todo eso pertenece a `TRABAJO_ACTUAL.md`, Git o `seguimiento_prompts/`.

`METODO_TRABAJO_AGENTES.md` define el procedimiento extendido y se lee solo
en incorporación, cambio de método o cuando el prompt lo solicite.
