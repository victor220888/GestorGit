# Guía para el propietario — trabajar en GestorGit con agentes

## Para qué sirve este archivo

Explica el proceso de trabajo real de este proyecto a cualquier persona
(propietario o programador) que lo abra en esta máquina, y cómo colaborar
con los agentes de programación que ya conocen el método.

No sustituye a los otros documentos: es la puerta de entrada humana.

```text
este archivo          -> onboarding humano (usted está aquí)
AGENTS.md             -> reglas del agente ZCode/OpenCode/Autoclaw (se carga sola)
CLAUDE.md             -> reglas del agente Claude Code
TRABAJO_ACTUAL.md     -> estado dinámico del trabajo (leer SIEMPRE)
METODO_TRABAJO_AGENTES.md -> método extendido de coordinación
seguimiento_prompts/  -> historia exacta de prompts y resultados
Git                   -> fuente de verdad inapelable
```

## El proyecto en 60 segundos

GestorGit es una aplicación de escritorio (Python + Tkinter, Windows) para
aprender y usar Git de forma visual, pedagógica y conservadora, orientada al
desarrollo Oracle/PLSQL. Regla de oro del producto: ante incertidumbre,
BLOQUEAR la operación y explicarla antes que ejecutar algo potencialmente
destructivo.

## Quién hace qué

| Actor | Rol |
|---|---|
| Propietario (usted) | decide prioridades, ejecuta pruebas manuales, ejecuta las operaciones Git productivas desde GestorGit y autoriza staging/commit/Push |
| ChatGPT | orquestador: prepara el prompt y las indicaciones para ZCode, audita el informe del agente y genera el documento de resultado |
| Agente programador (ZCode, Claude Code, OpenCode, Autoclaw) | implementa SOLO el alcance autorizado de cada prompt, valida, informa compacto y se detiene |

Solo un agente programador modifica el repositorio a la vez.

## El ciclo de trabajo de una etapa

Patrón validado en la práctica (GG-PROMPT-001..016, etapa "Publicar rama
local V1"):

```text
1. incorporación del agente (solo lectura, sin reservas)
2. análisis de la etapa futura (sin implementar)
3. implementación con prompt: decisiones ya aprobadas, archivos
   autorizados explícitos, comandos productivos exactos, pruebas
   enumeradas, prohibiciones
4. ADDENDUM/REV del prompt si hace falta (prevalece sobre el base)
5. auditoría de ChatGPT → microcorrecciones mínimas, una por prompt,
   cada una con alcance propio
6. prueba manual del usuario (batería funcional + retests visuales cortos)
7. cierre documental (TRABAJO_ACTUAL compacto; README solo si aplica)
8. microcorrección documental precommit si la auditoría la pide
9. cierre del bloque documental: auditoría previa de solo lectura →
   autorización explícita suya cuando aplique → USTED ejecuta el staging
   selectivo desde GestorGit (lista exacta) → auditoría del staged set →
   USTED crea UN commit local desde GestorGit → auditoría postcommit
10. cierre documental postcommit
```

## Reglas de oro que usted debe hacer valer

- **Autorizaciones y ejecución**: ninguna operación productiva que requiera
  autorización se ejecuta sin una frase explícita suya en la tarea ACTUAL
  (p. ej. "AUTORIZO GG-PROMPT-XXX: ..."), y una autorización anterior no
  vale para la siguiente tarea. Aun con autorización, el flujo NORMAL para
  las operaciones soportadas es que USTED las ejecute desde GestorGit; que
  el agente las realice por CLI es solo una excepción declarada de forma
  expresa en el prompt y, si escribe o toca red, con su autorización
  expresa.
- **Nunca `git add .` ni `git add -A`**: siempre rutas explícitas y el
  conjunto preparado se verifica exacto antes del commit.
- **Operaciones productivas desde GestorGit** (desde GG-PROMPT-016): si
  GestorGit soporta la operación (staging, commit, Fetch, Pull/Push
  seguros, ramas), el flujo normal es que USTED la ejecute en la
  aplicación; los agentes solo auditan antes/después con comandos Git de
  solo lectura. Una excepción (recuperación, diagnóstico, operación no
  soportada) debe declararse explícitamente y, si escribe o toca red,
  requiere su autorización expresa.
- **Prohibiciones absolutas** (nunca automáticas): `reset --hard`,
  `clean -fd`, `push --force`, `push --force-with-lease`, `branch -D`,
  borrar `index.lock`, resolver conflictos automáticamente, Merge/Rebase
  automáticos, guardar tokens.
- **Git manda**: si un documento contradice a Git, se detiene el trabajo y
  se reporta; no se "corrige" el estado por iniciativa propia.

## Cómo encargar una tarea a un agente

Abra su agente (p. ej. ZCode) en la carpeta del proyecto: leerá
`AGENTS.md` automáticamente. Luego dé la tarea con esta plantilla mínima:

```text
Lee y ejecuta exactamente: <ruta del prompt GG-PROMPT-XXX>
[frase de autorización SOLO si el prompt la exige y usted decide darla]
Al terminar entrega el informe solicitado y detente.
```

Para tareas sin prompt formal, indique al menos: objetivo, archivos
autorizados, archivos prohibidos, validaciones esperadas y que se detenga
al informar. El agente debe leer `TRABAJO_ACTUAL.md` y verificar Git real
antes de tocar nada.

## Archivos obligatorios de cada GG-PROMPT

Cada tarea formal `GG-PROMPT-XXX` debe quedar documentada con **tres archivos**
dentro de la carpeta propia de esa tarea en `seguimiento_prompts/`:

```text
GG-PROMPT-XXX.md
INDICACIONES_ZCODE_GG-PROMPT-XXX.md
GG-PROMPT-XXX-RESULTADO.md
```

El flujo obligatorio es:

1. ChatGPT prepara `GG-PROMPT-XXX.md` con el alcance completo de la tarea.
2. ChatGPT prepara `INDICACIONES_ZCODE_GG-PROMPT-XXX.md` con la instrucción
   breve que el propietario entrega al agente.
3. El propietario entrega ambos archivos a ZCode/agente y recibe su informe.
4. El propietario trae ese informe a ChatGPT.
5. ChatGPT audita el informe y **solo después de aceptarlo o rechazarlo** genera
   `GG-PROMPT-XXX-RESULTADO.md`.
6. El propietario guarda el resultado junto al prompt y las indicaciones.
7. Solo entonces se decide y prepara el siguiente `GG-PROMPT`.

El archivo `-RESULTADO.md` no se sustituye por el informe del agente: contiene
el veredicto auditado de ChatGPT y forma parte obligatoria de la historia de la
tarea. Si existe una `REV`/`ADDENDUM`, debe conservarse también junto con los
archivos de la tarea correspondiente.

## Organización física de `seguimiento_prompts/`

El propietario mantiene la bitácora organizada físicamente **por carpetas**, una
por ID/tarea. La convención observada y vigente es:

```text
seguimiento_prompts/
├── 001_incorporacion_zcode/
├── 002_analisis_publicar_rama_local/
├── 003_implementacion_publicar_rama_local/
├── ...
├── 020_cierre_dinamico_postcommit/
├── 021_auditoria_staging_cierre_dinamico/
├── archivo/
└── README.md
```

Reglas de organización:

- cada ID numérico conserva su propia carpeta `NNN_descripcion_corta/`;
- el prompt, las indicaciones para ZCode y el resultado auditado se guardan dentro
  de esa carpeta, no sueltos en la raíz de `seguimiento_prompts/`;
- una `REV`/`ADDENDUM` del mismo ID se conserva en **la misma carpeta** del ID
  original, junto al archivo sustituido/obsoleto;
- un prompt obsoleto **no se borra**: queda en su carpeta como histórico;
- `seguimiento_prompts/README.md` permanece en la raíz como índice vivo y se
  reemplaza por su versión más reciente;
- `archivo/` y otros documentos administrativos/históricos de apoyo pueden quedar
  en la raíz cuando no pertenecen a un único GG-PROMPT.

Ejemplo para la situación actual:

```text
seguimiento_prompts/021_auditoria_staging_cierre_dinamico/
├── GG-PROMPT-021.md                         # OBSOLETO — NO EJECUTADO
├── INDICACIONES_ZCODE_GG-PROMPT-021.md
├── GG-PROMPT-021-REV1.md                    # versión vigente
├── INDICACIONES_ZCODE_GG-PROMPT-021-REV1.md
└── GG-PROMPT-021-REV1-RESULTADO.md          # se crea solo tras auditoría ChatGPT
```

Esta estructura física es parte de la continuidad del proyecto: una sesión futura
debe respetarla al generar archivos nuevos.

## Comandos habituales

```powershell
# ejecutar la aplicación
.\.venv\Scripts\python.exe principal.py

# suite completa de pruebas
.\.venv\Scripts\python.exe -m unittest discover -s .\pruebas -v

# verificaciones de higiene
git status --short
git diff --check
git diff --cached --name-only
git log -1 --oneline
```

Las pruebas nunca tocan GitHub ni repositorios reales: usan carpetas
temporales.

## Estado actual y siguiente paso

La fuente siempre es `TRABAJO_ACTUAL.md` y Git. Como referencia del
momento en que se redactó esta guía: "Publicar rama local V1" está cerrada
con commit local `7c603fd`, Push pendiente de su decisión, y las
operaciones productivas se hacen desde la propia aplicación.

## Preguntas rápidas

- **¿Por qué el agente no me hace el commit?** Porque desde
  GG-PROMPT-016 el flujo normal es que usted lo haga desde GestorGit; el
  agente audita antes/después. Excepciones: solo declaradas y autorizadas.
- **¿Puedo trabajar con dos agentes a la vez?** Solo uno modifica; el
  otro, como máximo, en modo solo lectura autorizado.
- **¿Dónde está la historia de decisiones?** En `seguimiento_prompts/`
  (prompts, REV/ADDENDUM y resultados) y en el historial Git.
- **¿El agente "recuerda" entre sesiones?** No hay memoria personal
  garantizada: cada sesión RECONSTRUYE el contexto desde los documentos
  vivos y Git (`AGENTS.md`/`CLAUDE.md` → `TRABAJO_ACTUAL.md` →
  `METODO_TRABAJO_AGENTES.md` cuando corresponde, más `git status` y
  `git log`). En ZCode de esta máquina `AGENTS.md` se carga
  automáticamente; con otra herramienta/agente confirme su mecanismo de
  entrada y, si no carga el archivo sola, indíquele que lo lea.
  `TRABAJO_ACTUAL.md` se lee siempre después del archivo de configuración
  del agente.
