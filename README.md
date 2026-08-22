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

### Tooltips didácticos V1

- 38 tooltips centralizados (37 de la V1 histórica + la ayuda de Publicar rama local);
- explicaciones de operaciones, conceptos locales/remotos, staging, commit, Fetch, Pull, Push, historial, Inspector, ramas y sincronización;
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

Última etapa cerrada:

```text
Publicar rama local V1
```

Implementada, validada manualmente en Windows (A–F, layout, texto y
tooltips) y cerrada documentalmente. El commit local de cierre está
pendiente de autorización; hasta entonces el HEAD sigue en:

```text
4cd1ca5 Agrega leyenda contextual de estados Git V1
```

Suite del último cierre validado:

```text
426 tests OK
```

> Importante: este bloque describe el estado conocido al redactar el README. Antes de trabajar, ejecutar siempre `git status` y `git log -1 --oneline`.

## Próximo paso

La publicación segura de ramas locales ya está implementada y validada.
El siguiente paso operativo es la revisión de staging y el commit local de
la etapa (solo con autorización explícita; Push no autorizado). La evolución
posterior prevista es avanzar hacia una visión de colaboración de equipo para
desarrollo Oracle/PLSQL sin perder la filosofía de seguridad y comprensión.

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

Último cierre validado:

```text
Ran 426 tests ...
OK
```

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
coordinación.

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

La evolución prevista es avanzar hacia una visión de colaboración de equipo para desarrollo Oracle/PLSQL sin perder la filosofía de seguridad y comprensión.
