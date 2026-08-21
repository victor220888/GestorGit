import queue
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from ayuda_interfaz import AyudaEmergente, configurar_estilos
from servicio_cambios_locales_git import ServicioCambiosLocalesGit
from servicio_configuracion import ServicioConfiguracion
from servicio_descarte_cambios_git import ServicioDescarteCambiosGit
from servicio_exportacion_historial import ServicioExportacionHistorial
from servicio_historial_git import ServicioHistorialGit
from servicio_ramas_git import ServicioRamasGit
from servicio_remoto_git import ServicioRemotoGit


# Textos didácticos V1 para las acciones Git más críticas.
#
# Cada texto enseña, de forma compacta:
#   - el comando Git real que ejecuta el servicio subyacente;
#   - el concepto (HEAD / working tree / índice / refs remotas);
#   - qué cambia y qué NO cambia;
#   - requisitos o bloqueos de seguridad.
#
# Los textos se almacenan aquí (en lugar de inline) para poder
# probarlos sin abrir una ventana Tkinter real: las pruebas en
# pruebas/test_ayuda_tooltips_v1.py verifican que contienen los
# fragmentos y comandos esperados y que NO mencionan operaciones
# prohibidas (git reset --hard, git clean, git push --force, etc.).
# La interfaz los consume desde este diccionario mediante
# AyudaEmergente; ayuda_interfaz.py NO se modificó (sus textos ya
# admiten ancho configurable y no necesitan cambios).
#
# El diccionario agrupa hoy dos conjuntos:
#   - Fase 2A (P0/P1): 13 textos largos que enseñan comando Git real
#     -> concepto -> qué cambia -> no hace -> seguridad;
#   - Fase 2B (P2/P3): 24 textos breves de acciones secundarias y
#     conceptos de sincronización (ventana principal, historial,
#     Inspector, ramas, detalle de commit y etiquetas de estado).
#
# Todos los tooltips de la interfaz viven aquí; no queda ningún
# texto literal de tooltip inline en las llamadas a AyudaEmergente.

TEXTOS_AYUDA_GIT_V1 = {
    "fetch": (
        "Fetch\n\n"
        "Comando:\n"
        "git fetch --prune <remoto>\n\n"
        "Qué hace:\n"
        "Consulta el remoto y trae a tu repositorio local la "
        "información y los commits nuevos que todavía no tienes, "
        "actualizando las referencias locales de seguimiento "
        "(refs/remotes/...).\n\n"
        "Concepto:\n"
        "Las refs remotas son la memoria de GestorGit sobre lo que "
        "existe en el remoto; no son los archivos del working tree.\n\n"
        "Qué cambia:\n"
        "Actualiza información interna del repositorio local, "
        "incluidas las referencias de seguimiento remoto "
        "(refs/remotes/...) y los datos de los commits obtenidos. "
        "--prune elimina refs remotas obsoletas en tu carpeta .git "
        "(no borra ramas del servidor ni ramas locales).\n\n"
        "No hace:\n"
        "No integra esos commits en tu rama local actual: no "
        "modifica HEAD, no toca el working tree ni el índice y "
        "no crea merge.\n\n"
        "Requisitos / seguridad:\n"
        "Requiere remoto configurado y conexión. Sin Fetch previo, "
        "Pull y Push permanecen deshabilitados."
    ),
    "pull": (
        "Pull\n\n"
        "Comando:\n"
        "git pull --ff-only <remoto> <rama-remota>\n\n"
        "Qué hace:\n"
        "Descarga commits remotos pendientes y avanza la rama local "
        "mediante fast-forward.\n\n"
        "Concepto:\n"
        "--ff-only permite ÚNICAMENTE avance fast-forward: la rama "
        "local avanza sobre los commits nuevos del remoto.\n\n"
        "Qué cambia:\n"
        "HEAD avanza al nuevo commit y el working tree se actualiza "
        "con los archivos de ese commit.\n\n"
        "No hace:\n"
        "No crea merge automático, no ejecuta Rebase y no hace Push: "
        "el flujo de Pull no modifica la rama del servidor. Sí puede "
        "actualizar las refs LOCALES de seguimiento (refs/remotes/...)\n"
        "al obtener información del remoto, igual que Fetch: son "
        "memoria local sobre el remoto, no los archivos. No es "
        "'simplemente un Fetch': Fetch no toca HEAD y Pull sí.\n\n"
        "Requisitos / seguridad:\n"
        "Requiere repositorio limpio, upstream configurado, sin "
        "commits por enviar, sin divergencia ni operación Git en "
        "curso. GestorGit consulta el remoto antes de descargar."
    ),
    "push": (
        "Push\n\n"
        "Comando:\n"
        "git push --porcelain <remoto> <rama-local>:refs/heads/<rama-remota>\n\n"
        "Primer Push (sin upstream):\n"
        "git push --porcelain --set-upstream <remoto> <rama-local>:refs/heads/<rama-local>\n\n"
        "Qué hace:\n"
        "Envía al remoto los commits que existen únicamente en tu "
        "rama local.\n\n"
        "Concepto:\n"
        "--set-upstream aparece SOLO en el primer Push permitido "
        "para vincular la rama local con la remota; --porcelain da "
        "una salida estable que GestorGit interpreta.\n\n"
        "Primer Push (sin upstream):\n"
        "Si la rama remota con el mismo nombre YA EXISTE, "
        "GestorGit puede actualizarla y configurar el upstream "
        "con --set-upstream. Si NO existe, GestorGit tendría que "
        "CREARLA: esa creación automática solo se permite cuando "
        "el remoto está vacío de otras ramas conocidas; si no "
        "puede verificarlo, bloquea el Push.\n\n"
        "Qué cambia:\n"
        "Crea o actualiza refs/heads/ en el remoto y, en el primer "
        "Push, configura el upstream local.\n\n"
        "No hace:\n"
        "No crea commits, no mueve HEAD local y NUNCA usa --force ni "
        "--force-with-lease.\n\n"
        "Requisitos / seguridad:\n"
        "Repositorio limpio, sin conflictos, sin divergencia y sin "
        "commits remotos pendientes. GestorGit ejecuta Fetch previo "
        "y vuelve a comprobar la sincronización antes de enviar."
    ),
    "preparar": (
        "Preparar seleccionados\n\n"
        "Comando:\n"
        "git --literal-pathspecs add -- <rutas>\n\n"
        "Qué hace:\n"
        "Copia la versión actual de los archivos seleccionados al "
        "índice/staging para que entren en el próximo commit.\n\n"
        "Concepto:\n"
        "Working tree -> Índice -> Commit -> HEAD.\n"
        "Preparar registra/copia en el índice la versión actual de "
        "los archivos seleccionados: el working tree conserva sus\n"
        "cambios, no es un movimiento destructivo.\n\n"
        "Qué cambia:\n"
        "Solo el índice (staging).\n\n"
        "No hace:\n"
        "No crea commit, no mueve HEAD, no hace Push, no descarta "
        "los cambios del working tree.\n\n"
        "Requisitos / seguridad:\n"
        "--literal-pathspecs trata la ruta literalmente; -- marca "
        "el final de las opciones y protege rutas que podrían "
        "parecer opciones Git. GestorGit usa rutas explícitas: "
        "nunca git add . ni git add -A."
    ),
    "actualizar_preparados": (
        "Actualizar preparados\n\n"
        "Comando:\n"
        "git --literal-pathspecs add -- <rutas>\n\n"
        "Qué hace:\n"
        "Repite git add sobre archivos que ya estaban preparados y "
        "fueron modificados de nuevo después (estado 'preparado y "
        "vuelto a modificar').\n\n"
        "Concepto:\n"
        "Vuelve a copiar la versión actual completa al índice, "
        "reemplazando la versión preparada anterior.\n\n"
        "Qué cambia:\n"
        "Solo el índice: la versión preparada queda alineada con el "
        "working tree.\n\n"
        "No hace:\n"
        "No modifica el archivo del disco, no descarta cambios, no "
        "crea commit ni hace Push.\n\n"
        "Requisitos / seguridad:\n"
        "GestorGit revalida el estado de cada archivo antes de "
        "ejecutar: solo actualiza archivos que siguen preparados, "
        "con cambios nuevos fuera del índice y sin conflicto."
    ),
    "quitar_preparados": (
        "Quitar de preparados\n\n"
        "Comando:\n"
        "git --literal-pathspecs restore --staged -- <rutas>\n\n"
        "Sin commits previos (primer commit):\n"
        "git --literal-pathspecs rm --cached -- <rutas>\n\n"
        "Qué hace:\n"
        "Saca los archivos seleccionados del índice/staging.\n\n"
        "Concepto:\n"
        "--staged actúa sobre el índice, no sobre el working tree.\n\n"
        "Qué cambia:\n"
        "Solo el índice: el archivo deja de prepararse para el "
        "próximo commit.\n\n"
        "No hace:\n"
        "NO elimina el archivo del disco, NO descarta sus "
        "modificaciones del working tree y NO es equivalente a "
        "Descartar cambios sin preparar.\n\n"
        "Requisitos / seguridad:\n"
        "Rutas explícitas con --literal-pathspecs y --."
    ),
    "commit": (
        "Crear commit\n\n"
        "Comando:\n"
        "git commit -m \"<mensaje>\"\n\n"
        "Qué hace:\n"
        "Crea un nuevo commit con los archivos que están en el "
        "índice y avanza la rama/HEAD a ese commit.\n\n"
        "Concepto:\n"
        "El commit queda en la rama local. Para los archivos "
        "incluidos, el índice queda alineado con el nuevo HEAD.\n\n"
        "Qué cambia:\n"
        "Crea un commit nuevo y mueve HEAD (y la rama actual) a él. "
        "El índice no se borra: queda alineado con el nuevo HEAD.\n\n"
        "No hace:\n"
        "No hace Push y no publica nada en el remoto. El commit "
        "usa lo que está preparado: no incorpora automáticamente "
        "los cambios del working tree que no estén preparados.\n\n"
        "Requisitos / seguridad:\n"
        "Requiere identidad Git válida (user.name y user.email). "
        "GestorGit bloquea el commit si hay conflictos, operación "
        "Git en curso o archivos preparados modificados después "
        "(usa Actualizar preparados primero)."
    ),
    "descartar_sin_preparar": (
        "Descartar cambios sin preparar...\n\n"
        "Comando:\n"
        "git --literal-pathspecs restore --worktree -- <ruta>\n\n"
        "Qué hace:\n"
        "Operación DESTRUCTIVA: descarta únicamente los cambios SIN "
        "PREPARAR de un archivo, restaurando el working tree desde "
        "el índice.\n\n"
        "Concepto:\n"
        "Sin --source, git restore restaura desde el ÍNDICE (no "
        "desde HEAD). Si el archivo estaba preparado (caso MM), los "
        "cambios preparados se CONSERVAN; solo se pierden los "
        "cambios posteriores no preparados.\n\n"
        "Qué cambia:\n"
        "El working tree del archivo seleccionado.\n\n"
        "No hace:\n"
        "No usa --staged, no crea commit, no hace Push y no toca el "
        "índice. No borra archivos nuevos/no rastreados (marcados ?? "
        "por git status) y no ejecuta git clean.\n\n"
        "Requisitos / seguridad:\n"
        "Solo disponible en la pestaña 'Sin preparar' con cambios "
        "reales y sin conflictos. Pide confirmación explícita. "
        "Bloqueado durante operaciones remotas en curso."
    ),
    "cambiar_rama": (
        "Cambiar a seleccionada\n\n"
        "Comando:\n"
        "git switch --no-guess <rama>\n\n"
        "Qué hace:\n"
        "Cambia HEAD a otra rama LOCAL existente y actualiza el "
        "working tree para reflejarla.\n\n"
        "Concepto:\n"
        "--no-guess impide que Git adivine o cree seguimiento de "
        "una rama remota. GestorGit solo trabaja con ramas locales.\n\n"
        "Qué cambia:\n"
        "HEAD y, normalmente, el contenido del working tree.\n\n"
        "No hace:\n"
        "No descarta cambios, no hace Fetch, no hace Pull, no hace "
        "Push, no publica ni crea ramas.\n\n"
        "Requisitos / seguridad:\n"
        "Requiere repositorio completamente limpio (sin cambios, sin "
        "preparados, sin archivos nuevos). El servicio vuelve a "
        "comprobarlo justo antes de ejecutar git switch."
    ),
    "crear_rama": (
        "Crear rama\n\n"
        "Comando:\n"
        "git switch -c <nombre>\n\n"
        "Qué hace:\n"
        "Crea una rama LOCAL nueva y cambia HEAD a ella.\n\n"
        "Concepto:\n"
        "-c crea la rama y mueve HEAD en un mismo paso. Nace del "
        "commit actual (HEAD), sin start-point distinto. Aparece "
        "una nueva refs/heads/<nombre>; los archivos suelen quedar "
        "iguales porque se parte del mismo commit.\n\n"
        "Qué cambia:\n"
        "Crea refs/heads/<nombre> y mueve HEAD a ella.\n\n"
        "No hace:\n"
        "No crea upstream, no hace Push, no publica la rama en el "
        "remoto y no toca los commits existentes.\n\n"
        "Requisitos / seguridad:\n"
        "Requiere repositorio limpio. El nombre se valida con "
        "git check-ref-format antes de crearla."
    ),
    "ramas": (
        "Ramas...\n\n"
        "Comando:\n"
        "git for-each-ref --format=%(refname:short) refs/heads/\n"
        "git symbolic-ref --quiet --short HEAD\n\n"
        "Qué hace:\n"
        "Abre la gestión de ramas LOCALES. Listar ramas es solo "
        "lectura y no consulta el remoto.\n\n"
        "Concepto:\n"
        "refs/heads/ son las ramas locales. symbolic-ref determina "
        "la rama actual (o HEAD separado).\n\n"
        "Qué cambia:\n"
        "Nada: solo consulta local.\n\n"
        "No hace:\n"
        "No hace Fetch, no hace Pull, no hace Push, no publica ramas "
        "y no cambia de rama al abrir la ventana.\n\n"
        "Requisitos / seguridad:\n"
        "Operación de solo lectura. Cambiar o crear rama tienen sus "
        "propios tooltips y confirmaciones."
    ),
    "configurar_github": (
        "Configurar GitHub...\n\n"
        "Qué hace:\n"
        "Abre el flujo educativo para configurar el PRIMER remoto "
        "origin de este repositorio local.\n\n"
        "Concepto:\n"
        "Un remoto es una URL asociada a tu repositorio local en "
        ".git/config.\n\n"
        "Qué cambia:\n"
        "Todavía nada: este botón abre una ventana. La configuración "
        "real se hace con Agregar origin (git remote add).\n\n"
        "No hace:\n"
        "No crea la cuenta ni el repositorio en GitHub. Puede abrir "
        "github.com/new en el navegador. GestorGit no recibe ni guarda "
        "credenciales (usuario, contraseña ni PAT).\n\n"
        "Requisitos / seguridad:\n"
        "Solo disponible si el repositorio no tiene NINGÚN remoto "
        "configurado."
    ),
    "agregar_origin": (
        "Agregar origin\n\n"
        "Comando:\n"
        "git remote add origin <url>\n\n"
        "Qué hace:\n"
        "Registra origin como remoto del repositorio local.\n\n"
        "Concepto:\n"
        "Solo modifica .git/config; no conecta con Internet durante "
        "el comando.\n\n"
        "Qué cambia:\n"
        "Agrega una entrada de remoto en .git/config.\n\n"
        "No hace:\n"
        "No hace Fetch, no hace Push, no modifica el working tree, "
        "no modifica HEAD y no sustituye ni elimina remotos "
        "existentes.\n\n"
        "Requisitos / seguridad:\n"
        "Solo si no existe ningún remoto. Solo URL HTTPS de "
        "github.com válida, sin credenciales embebidas. Después de "
        "Agregar origin debes ejecutar Fetch manualmente."
    ),

    # =============================================================
    # FASE 2B (P2/P3): textos breves y concisos
    # =============================================================

    "seleccionar_repositorio": (
        "Seleccionar repositorio\n\n"
        "Elige una carpeta que contenga un repositorio Git.\n\n"
        "La aplicación solamente analizará esa carpeta. "
        "Seleccionarla no modifica archivos ni ejecuta Fetch, "
        "Pull o Push."
    ),
    "actualizar_estado_local": (
        "Actualizar estado local\n\n"
        "Vuelve a leer el estado LOCAL del repositorio "
        "desde tu disco.\n\n"
        "No equivale a Fetch: no consulta el remoto, "
        "no descarga ni sube nada."
    ),
    "historial": (
        "Historial de commits\n\n"
        "Muestra los commits más recientes del historial LOCAL.\n\n"
        "Es una consulta de SOLO LECTURA: abrirla no modifica "
        "archivos, ramas, commits ni el repositorio remoto.\n\n"
        "También permite filtrar y exportar los resultados "
        "visibles a CSV o TXT."
    ),
    "seleccionar_todo": (
        "Seleccionar todo\n\n"
        "Selecciona todas las filas visibles de la tabla.\n\n"
        "Solo cambia la selección visual: no prepara nada "
        "por sí mismo.\n\n"
        "Esa selección será la entrada de acciones como "
        "Preparar, Actualizar preparados o Quitar de "
        "preparados según proceda."
    ),
    "ver_cambios_locales": (
        "Ver cambios locales...\n\n"
        "Abre una ventana para inspeccionar los cambios "
        "del archivo seleccionado.\n\n"
        "Consultar, Actualizar y Copiar diff son operaciones "
        "de solo lectura.\n\n"
        "Desde la pestaña 'Sin preparar' existe una acción "
        "separada: 'Descartar cambios sin preparar...', que "
        "puede eliminar cambios del working tree después de "
        "una confirmación explícita.\n\n"
        "La pestaña 'Sin preparar' muestra los cambios todavía "
        "no preparados (working tree -> índice).\n\n"
        "La pestaña 'Preparados' muestra los cambios ya "
        "listos para el commit (índice -> HEAD).\n\n"
        "Útil para entender el flujo:\n"
        "Working tree -> Preparar -> Staging -> Commit -> HEAD.\n\n"
        "No ejecuta Fetch, Pull ni Push."
    ),
    "historial_filtro_archivo": (
        "Filtro por archivo\n\n"
        "Escribe todo o parte del nombre de un archivo.\n\n"
        "Por ejemplo: FINI004, .pls o Paquetes.\n\n"
        "La búsqueda no distingue mayúsculas de minúsculas "
        "y solamente muestra commits que modificaron archivos "
        "cuyo nombre o ruta contiene ese texto.\n\n"
        "Vuelve a consultar git log LOCAL: no consulta el remoto."
    ),
    "historial_fecha_desde": (
        "Fecha Desde\n\n"
        "Muestra commits a partir de esta fecha, "
        "incluyéndola.\n\n"
        "Se refiere a la FECHA DEL COMMIT.\n\n"
        "Formato: dd/mm/aaaa.\n"
        "Puedes dejarla vacía."
    ),
    "historial_fecha_hasta": (
        "Fecha Hasta\n\n"
        "Muestra commits hasta esta fecha, "
        "incluyéndola.\n\n"
        "Se refiere a la FECHA DEL COMMIT.\n\n"
        "Formato: dd/mm/aaaa.\n"
        "Puedes dejarla vacía."
    ),
    "historial_aplicar_filtros": (
        "Aplicar filtros\n\n"
        "Consulta nuevamente el historial LOCAL utilizando "
        "el archivo y las fechas indicadas.\n\n"
        "Los filtros se combinan: si completas varios, "
        "el commit debe cumplirlos todos.\n\n"
        "No consulta el remoto."
    ),
    "historial_limpiar_filtros": (
        "Limpiar filtros\n\n"
        "Vacía Archivo, Desde y Hasta y vuelve a mostrar "
        "el historial LOCAL sin filtros.\n\n"
        "No cambia commits: solo modifica la vista."
    ),
    "historial_ver_cambios": (
        "Ver cambios...\n\n"
        "Muestra los cambios de archivos introducidos "
        "por el commit seleccionado (consulta local).\n\n"
        "Es una vista de SOLO LECTURA: no hace checkout, "
        "reset ni restauración. No modifica archivos, "
        "commits ni ramas y no consulta el remoto."
    ),
    "exportar_historial_csv": (
        "Exportar CSV\n\n"
        "Guarda exactamente los commits visibles en un archivo CSV "
        "en tu disco.\n\n"
        "Incluye hash completo, hash corto, fecha ISO, autor, correo "
        "y mensaje.\n\n"
        "Se utiliza UTF-8 y un formato amigable para Excel en Windows.\n\n"
        "Escribe un archivo de informe: no modifica el repositorio, "
        "no cambia commits y no consulta el remoto."
    ),
    "exportar_historial_txt": (
        "Exportar TXT\n\n"
        "Guarda exactamente los commits visibles en un archivo de "
        "texto en tu disco.\n\n"
        "Además deja registrados el repositorio y los filtros "
        "aplicados para facilitar análisis o documentación posterior.\n\n"
        "Escribe un archivo de informe: no modifica el repositorio, "
        "no cambia commits y no consulta el remoto."
    ),
    "actualizar_historial": (
        "Actualizar historial\n\n"
        "Vuelve a ejecutar la consulta de git log LOCAL "
        "conservando los filtros actuales.\n\n"
        "No equivale a Fetch y no consulta el remoto."
    ),
    "actualizar_inspector": (
        "Actualizar\n\n"
        "Vuelve a consultar el estado y los diffs LOCALES "
        "del archivo inspeccionado.\n\n"
        "No hace Fetch, no modifica el archivo, "
        "el staging ni los commits."
    ),
    "actualizar_ramas": (
        "Actualizar\n\n"
        "Vuelve a listar las ramas LOCALES del repositorio.\n\n"
        "No hace Fetch: no verás ramas nuevas del servidor. "
        "Tampoco cambia de rama."
    ),
    "copiar_diff_inspector": (
        "Copiar diff\n\n"
        "Copia al portapapeles el diff VISIBLE de la pestaña "
        "activa (Sin preparar o Preparados).\n\n"
        "No modifica archivos: no prepara ni descarta "
        "y no modifica Git."
    ),
    "copiar_diff_commit": (
        "Copiar diff\n\n"
        "Copia al portapapeles el diff VISIBLE mostrado "
        "para el commit seleccionado.\n\n"
        "No copia ni ejecuta un commit: no modifica el "
        "working tree, el staging ni el historial."
    ),
    "concepto_upstream": (
        "Upstream\n\n"
        "Es la rama de seguimiento asociada a la rama local "
        "(habitual: origin/master).\n\n"
        "Sirve como referencia para comparar Pull/Push.\n\n"
        "La etiqueta solo indica si está CONFIGURADO o no: "
        "tener upstream no significa estar sincronizado ahora mismo."
    ),
    "concepto_rama_remota": (
        "Rama remota\n\n"
        "Es la rama de seguimiento que Git conoce localmente "
        "(p. ej. origin/master).\n\n"
        "Fetch actualiza esa información al consultar el remoto.\n\n"
        "No es una consulta en vivo al servidor. "
        "Si la rama no existe, se indica '(no existe)'."
    ),
    "concepto_por_enviar": (
        "Por enviar\n\n"
        "Cuenta COMMITS, no archivos.\n\n"
        "Son commits de la rama local que la referencia "
        "upstream CONOCIDA no contiene.\n\n"
        "Depende de la información remota conocida localmente: "
        "un Fetch reciente actualiza esa referencia.\n\n"
        "No significa que se haya hecho Push."
    ),
    "concepto_por_descargar": (
        "Por descargar\n\n"
        "Cuenta COMMITS, no archivos.\n\n"
        "Son commits conocidos en la rama de seguimiento remota "
        "que la rama local aún no contiene.\n\n"
        "Se calcula con la información conocida tras consultar "
        "el remoto (Fetch).\n\n"
        "No significa que esos commits ya estén integrados con Pull."
    ),
    "concepto_estado_sincronizacion": (
        "Estado de sincronización\n\n"
        "Describe la comparación entre la rama LOCAL y la "
        "referencia remota CONOCIDA (por enviar / por descargar).\n\n"
        "No es monitorización en tiempo real del servidor: "
        "se calcula con la información de la última consulta."
    ),
    "concepto_ultima_consulta": (
        "Última consulta\n\n"
        "Muestra el último estado conocido relacionado con una "
        "consulta u operación remota.\n\n"
        "GestorGit no vigila continuamente el servidor: la "
        "información remota se actualiza al ejecutar Fetch "
        "(y en el flujo actual, también Pull o Push).\n\n"
        "Una operación fallida no significa que la información "
        "remota se haya actualizado."
    ),
}


# =============================================================
# CONTENIDO_AYUDA_ESTADOS_GIT_V1
#
# Leyenda / ayuda contextual de los estados Git de la tabla de
# cambios. NO son tooltips: es el contenido de la ventana
# educativa "Estados Git - Gestor Git" que se abre con el botón
# "¿Qué significan estos estados?".
#
# Estructura pedagógica: primero el MODELO MENTAL (HEAD, índice/
# staging y working tree), después los estados concretos que
# muestra la tabla (??, " M", "M ", MM y conflicto), después
# otros estados y la parte avanzada de códigos XY, y al final la
# relación con el Inspector y con las acciones de staging.
#
# Todos los textos de la ventana proceden de este diccionario;
# no quedan textos educativos inline en los métodos Tkinter.
# =============================================================

CONTENIDO_AYUDA_ESTADOS_GIT_V1 = {
    # ---------------------------------------------------------
    # NIVEL 1 - MODELO MENTAL: HEAD, índice/staging y working tree
    # ---------------------------------------------------------
    "modelo_head_indice_working_tree": (
        "MODELO MENTAL: HEAD, ÍNDICE Y WORKING TREE\n\n"
        "Antes de interpretar los estados de la tabla conviene "
        "tener claro el modelo de tres lugares en el que trabaja "
        "Git.\n\n"
        "HEAD\n"
        "- apunta al commit actual;\n"
        "- representa la referencia de la versión ya confirmada "
        "en el historial local.\n\n"
        "Índice / staging\n"
        "- contiene la versión preparada para el próximo commit;\n"
        "- NO es una carpeta física del disco;\n"
        "- preparar no mueve destructivamente el archivo del "
        "disco: preparar copia/registra en el índice la versión "
        "actual del archivo.\n\n"
        "Working tree\n"
        "- son los archivos actuales que tienes en el disco "
        "dentro del repositorio.\n\n"
        "Las relaciones:\n\n"
        "Working tree\n"
        "  -> Preparar / Actualizar preparados\n"
        "Índice / staging\n\n"
        "Índice / staging\n"
        "  -> Crear commit\n"
        "nuevo commit\n"
        "  -> HEAD avanza al nuevo commit\n\n"
        "Git crea el commit a partir del contenido preparado en "
        "el índice; HEAD avanza al nuevo commit."
    ),
    # ---------------------------------------------------------
    # NIVEL 2 - ESTADOS CONCRETOS: ?? (nuevo / no rastreado)
    # ---------------------------------------------------------
    "estado_no_rastreado": (
        "ESTADO: NUEVO / NO RASTREADO (??)\n\n"
        "Git XY: \"??\"\n\n"
        "- el archivo SÍ existe en el working tree (disco);\n"
        "- Git todavía no lo está rastreando;\n"
        "- todavía no hay una versión preparada de ese archivo "
        "en el índice;\n"
        "- Preparar registra/copia su versión actual en el "
        "índice."
    ),
    # ---------------------------------------------------------
    # NIVEL 2 - " M" (modificado sin preparar)
    # ---------------------------------------------------------
    "estado_modificado_sin_preparar": (
        "ESTADO: MODIFICADO SIN PREPARAR (\" M\")\n\n"
        "Git XY: \" M\"\n"
        "(espacio + M)\n\n"
        "- primera posición vacía;\n"
        "- segunda posición M;\n"
        "- el índice coincide con HEAD para ese cambio;\n"
        "- el working tree difiere del índice.\n\n"
        "En la tabla GestorGit suele mostrarse:\n"
        "Estado = Modificado\n"
        "Preparado = No"
    ),
    # ---------------------------------------------------------
    # NIVEL 2 - "M " (modificado y preparado)
    # ---------------------------------------------------------
    "estado_modificado_preparado": (
        "ESTADO: MODIFICADO Y PREPARADO (\"M \")\n\n"
        "Git XY: \"M \"\n"
        "(M + espacio)\n\n"
        "- primera posición M;\n"
        "- segunda posición vacía;\n"
        "- el índice difiere de HEAD;\n"
        "- el working tree coincide con la versión preparada.\n\n"
        "En la tabla GestorGit suele mostrarse:\n"
        "Estado = Modificado y preparado\n"
        "Preparado = Sí"
    ),
    # ---------------------------------------------------------
    # NIVEL 2 - MM (preparado y vuelto a modificar)
    # ---------------------------------------------------------
    "estado_preparado_y_vuelto_a_modificar": (
        "ESTADO: MODIFICADO, PREPARADO Y VUELTO A MODIFICAR (MM)\n\n"
        "Git XY: \"MM\"\n\n"
        "- el índice ya contiene una versión preparada;\n"
        "- después el archivo volvió a modificarse en el working "
        "tree;\n"
        "- hay dos versiones distintas relevantes:\n"
        "  - la preparada (en el índice);\n"
        "  - la actual del disco (working tree).\n\n"
        "En la tabla GestorGit suele mostrarse:\n"
        "Estado = Modificado, preparado y vuelto a modificar\n"
        "Preparado = Sí (hay cambios nuevos)\n\n"
        "Punto importante: si se pudiera crear el commit en ese "
        "momento, el commit usaría la versión que está en el "
        "índice, NO automáticamente los cambios posteriores del "
        "working tree. GestorGit bloquea ese flujo normal y "
        "ofrece Actualizar preparados para copiar la versión "
        "actual completa nuevamente al índice. También puedes "
        "usar Ver cambios locales... para comparar ambas "
        "versiones."
    ),
    # ---------------------------------------------------------
    # NIVEL 2 - CONFLICTO (estado especial)
    # ---------------------------------------------------------
    "estado_conflicto": (
        "ESTADO ESPECIAL: CONFLICTO\n\n"
        "Un conflicto es un estado ESPECIAL: no es simplemente "
        "\"preparado\" ni \"sin preparar\".\n\n"
        "En la tabla GestorGit se muestra:\n"
        "Estado = Conflicto\n"
        "Preparado = No aplica\n\n"
        "Git necesita que una persona decida cómo resolver el "
        "contenido del archivo.\n\n"
        "GestorGit:\n"
        "- NO elige una versión automáticamente;\n"
        "- NO prepara normalmente el conflicto;\n"
        "- NO permite quitarlo de preparados;\n"
        "- NO lo actualiza con Actualizar preparados;\n"
        "- bloquea el commit mientras exista el conflicto.\n\n"
        "En Git un conflicto puede representarse con los códigos "
        "DD AU UD UA DU AA UU; GestorGit no resuelve conflictos: "
        "la decisión queda en manos de una persona."
    ),
    # ---------------------------------------------------------
    # OTROS ESTADOS
    # ---------------------------------------------------------
    "otros_estados": (
        "OTROS ESTADOS DE GIT\n\n"
        "Git también puede representar:\n"
        "A = agregado (nuevo y ya rastreado)\n"
        "D = eliminado\n"
        "R = renombrado\n\n"
        "La POSICIÓN sigue importando:\n"
        "- primera posición: el índice comparado con HEAD;\n"
        "- segunda posición: el working tree comparado con el "
        "índice.\n\n"
        "Esta ayuda no pretende ser una lista exhaustiva de los "
        "códigos de git status --porcelain: el objetivo es "
        "comprender el modelo."
    ),
    # ---------------------------------------------------------
    # PARTE AVANZADA: CÓDIGOS XY
    # ---------------------------------------------------------
    "codigos_xy": (
        "PARTE AVANZADA: CÓDIGOS XY\n\n"
        "git status --porcelain usa dos posiciones:\n\n"
        "XY\n\n"
        "X: estado del ÍNDICE respecto de HEAD.\n"
        "Y: estado del WORKING TREE respecto del índice.\n\n"
        "Ejemplos explícitos:\n"
        "\" M\" = espacio + M (segunda posición: working tree "
        "modificado)\n"
        "\"M \" = M + espacio (primera posición: índice "
        "modificado)\n"
        "\"MM\" = M + M (modificado en el índice y vuelto a "
        "modificar)\n"
        "\"??\" = caso especial: archivo no rastreado\n\n"
        "La letra M, sin conocer su posición, puede ser ambigua: "
        "M puede indicar cambios preparados o sin preparar según "
        "dónde aparezca. No existe un significado único de M: "
        "depende de su posición en XY."
    ),
    # ---------------------------------------------------------
    # RELACIÓN CON EL INSPECTOR Y CON LAS ACCIONES
    # ---------------------------------------------------------
    "inspector_y_acciones": (
        "RELACIÓN CON EL INSPECTOR Y LAS ACCIONES\n\n"
        "Ver cambios locales...\n"
        "- pestaña \"Sin preparar\": working tree comparado con "
        "el índice (conceptualmente git diff);\n"
        "- pestaña \"Preparados\": índice comparado con HEAD "
        "(conceptualmente git diff --cached).\n\n"
        "En el caso MM ambas pestañas pueden mostrar diffs "
        "diferentes: una para lo preparado y otra para lo que "
        "cambió después.\n\n"
        "Recomendación: selecciona un archivo y usa Ver cambios "
        "locales... para ver qué está preparado y qué sigue "
        "fuera del índice.\n\n"
        "Acciones:\n"
        "- Preparar seleccionados: copia/registra la versión "
        "actual en el índice.\n"
        "- Actualizar preparados: vuelve a copiar la versión "
        "actual cuando el archivo ya estaba preparado y cambió "
        "después.\n"
        "- Quitar de preparados: modifica el índice para dejar de "
        "preparar ese cambio y conserva el working tree; el "
        "estado final de la tabla depende de cada caso.\n"
        "- Crear commit: crea el commit a partir de lo preparado; "
        "no incorpora automáticamente los cambios posteriores no "
        "preparados."
    ),
}


# Subtítulos cortos del contenido que se resaltan en negrita en la
# ventana de ayuda de estados. La comparación es por igualdad
# exacta de la línea completa (line.strip()), nunca por substring.
_SUBTITULOS_AYUDA_ESTADOS = (
    "HEAD",
    "Índice / staging",
    "Working tree",
    "Ver cambios locales...",
    "Acciones:",
)

# Líneas de códigos Git que se muestran en Consolas bold. Los
# patrones son COMPLETOS y EXACTOS (no regex de "M") para que
# " M" y "M " se distingan sin ambigüedad y para no formatear
# una letra M cualquiera.
_LINEAS_CODIGO_GIT_AYUDA = (
    'Git XY: "??"',
    'Git XY: " M"',
    'Git XY: "M "',
    'Git XY: "MM"',
    '" M" = espacio + M (segunda posición: working tree modificado)',
    '"M " = M + espacio (primera posición: índice modificado)',
    '"MM" = M + M (modificado en el índice y vuelto a modificar)',
    '"??" = caso especial: archivo no rastreado',
)


class AplicacionGit:
    """
    Ventana principal de la aplicación Gestor Git.

    Las operaciones locales y remotas pasan por ServicioRemotoGit.

    Las operaciones de red se ejecutan en hilos secundarios
    para evitar que la interfaz de Tkinter se congele.
    """

    def __init__(self, ventana_principal):
        # Ventana principal de Tkinter.
        self.ventana_principal = ventana_principal

        # Configuramos la apariencia visual antes de crear
        # los controles de la aplicación.
        self.estilos = configurar_estilos(
            self.ventana_principal
        )

        # Servicio que contiene las operaciones locales,
        # Fetch, Pull y Push.
        self.servicio_git = ServicioRemotoGit()

        # Servicio que recuerda el último repositorio seleccionado.
        # Guarda únicamente la ruta local en config.json y nunca
        # credenciales; la carga automática no ejecuta Fetch.
        self.servicio_configuracion = ServicioConfiguracion(
            self.servicio_git
        )

        # Servicio independiente de solo lectura para consultar
        # el historial de commits. Reutiliza el mismo ServicioGit.
        self.servicio_historial = ServicioHistorialGit(
            self.servicio_git
        )

        # Servicio que guarda una copia del historial visible en CSV o TXT.
        # No ejecuta Git y no modifica el repositorio.
        self.servicio_exportacion_historial = ServicioExportacionHistorial()

        # Servicio de solo lectura para inspeccionar los cambios
        # locales de un archivo (working tree / índice / HEAD).
        # No ejecuta operaciones remotas ni modifica el repositorio.
        self.servicio_cambios_locales = ServicioCambiosLocalesGit(
            self.servicio_git
        )

        # Servicio que descarta los cambios SIN PREPARAR de un
        # archivo (git restore --worktree desde el índice).
        # 100 % local: conserva el staging y no toca el remoto.
        self.servicio_descarte_cambios = ServicioDescarteCambiosGit(
            self.servicio_git
        )

        # Servicio de ramas LOCALES: listar, identificar la rama
        # actual, cambiar a una rama existente y crear una rama
        # desde HEAD. 100 % local: nunca Fetch/Pull/Push y una
        # rama nueva queda sin publicar y sin upstream.
        self.servicio_ramas = ServicioRamasGit(
            self.servicio_git
        )

        # La ventana de historial se crea únicamente cuando el usuario
        # la solicita y se reutiliza mientras permanezca abierta.
        self.ventana_historial = None
        self.tabla_historial = None
        self.variable_estado_historial = None
        self.variable_filtro_archivo_historial = None
        self.variable_fecha_desde_historial = None
        self.variable_fecha_hasta_historial = None
        self.boton_exportar_csv_historial = None
        self.boton_exportar_txt_historial = None

        # Relaciona las filas visibles del historial con su CommitGit.
        # La ventana de detalle utiliza esta relación y no vuelve
        # a consultar el historial.
        self.commits_historial_por_elemento = {}

        # Botón que muestra los cambios del commit seleccionado.
        self.boton_ver_cambios_historial = None

        # Ventana única con los cambios de un commit (solo lectura).
        self.ventana_detalle_commit = None
        self.texto_detalle_commit = None

        # Ventana única del inspector de cambios locales
        # (solo lectura). Se cierra al cambiar de repositorio.
        self.ventana_cambios_locales = None
        self.notebook_cambios_locales = None
        self.marco_sin_preparar_locales = None
        self.marco_preparados_locales = None
        self.texto_sin_preparar_locales = None
        self.texto_preparados_locales = None
        self.variable_resumen_sin_preparar = None
        self.variable_resumen_preparados = None
        self.variable_estado_inspector = None
        self.variable_preparado_inspector = None
        self.variable_commit_inspector = None
        self.detalle_cambio_local_actual = None
        self.ruta_archivo_inspector = ""

        # Botón destructivo controlado del Inspector: descarta los
        # cambios sin preparar de UN archivo conservando el staging.
        self.boton_descartar_sin_preparar = None

        # Ventana única de ramas locales. Se cierra al cambiar de
        # repositorio y no ejecuta operaciones remotas.
        self.ventana_ramas = None
        self.tabla_ramas = None
        self.variable_estado_ramas = None
        self.variable_rama_actual_ventana = None
        self.variable_nueva_rama = None
        self.entrada_nueva_rama = None
        self.boton_cambiar_rama = None
        self.boton_crear_rama = None
        self.rama_actual_ventana_actual = ""

        # Ventana única de la leyenda de estados Git (ventana
        # educativa de SOLO TEXTO). NO modal: la ventana principal
        # sigue siendo usable. Solo muestra conceptos generales:
        # no ejecuta Git ni consulta el repositorio, por lo que
        # permanece disponible incluso sin repositorio.
        self.ventana_ayuda_estados_git = None
        self.texto_ayuda_estados_git = None

        # Límite visual del diff mostrado en la ventana de detalle.
        # La truncación es solamente visual: no modifica el repositorio.
        self.limite_caracteres_detalle = 500000

        # La ventana de configuración de GitHub se crea únicamente
        # cuando el usuario la solicita y se reutiliza mientras
        # permanezca abierta.
        self.ventana_configuracion_github = None
        self.variable_url_github = None

        # Conserva exactamente los commits que se están mostrando.
        # Las exportaciones usan esta lista y no vuelven a ejecutar git log.
        self.commits_historial_actual = []

        # Conserva los filtros de la última consulta exitosa para que
        # el TXT documente exactamente qué información fue exportada.
        self.filtros_historial_aplicados = {
            "archivo": "",
            "desde": "",
            "hasta": ""
        }

        # Repositorio actualmente seleccionado.
        self.ruta_repositorio = ""

        # Lista de remotos del repositorio seleccionado.
        self.remotos_repositorio = []

        # Relaciona las filas visuales con CambioArchivo.
        self.cambios_por_elemento = {}

        # Indica si existen cambios pendientes de commit.
        self.hay_cambios_pendientes = False

        # Guarda el último EstadoSincronizacion calculado.
        self.estado_sincronizacion_actual = None

        # Pull y Push solamente se habilitan después
        # de un Fetch exitoso durante la sesión actual.
        self.fetch_exitoso_en_sesion = False

        # Los hilos secundarios devolverán resultados
        # mediante esta cola.
        self.cola_resultados = queue.Queue()

        # Evita ejecutar varias operaciones remotas simultáneamente.
        self.operacion_remota_en_curso = False

        self.configurar_ventana()
        self.crear_interfaz()
        self.verificar_git()
        self.cargar_repositorio_recordado()

        # Tkinter revisará periódicamente la cola
        # de resultados de los hilos.
        self.ventana_principal.after(
            100,
            self.procesar_cola_resultados
        )

    def configurar_ventana(self):
        """
        Configura las propiedades generales de la ventana.
        """

        self.ventana_principal.title(
            "Gestor Git"
        )

        self.ventana_principal.geometry(
            "1180x900"
        )

        self.ventana_principal.minsize(
            950,
            720
        )

    def crear_interfaz(self):
        """
        Crea todos los controles visibles.
        """

        marco_principal = ttk.Frame(
            self.ventana_principal,
            padding=15
        )

        marco_principal.pack(
            fill=tk.BOTH,
            expand=True
        )

        marco_principal.columnconfigure(
            0,
            weight=1
        )

        # La tabla ocupará el espacio vertical sobrante.
        marco_principal.rowconfigure(
            5,
            weight=1
        )

        # ---------------------------------------------------------
        # Título
        # ---------------------------------------------------------

        marco_titulo = ttk.Frame(
            marco_principal
        )

        marco_titulo.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 15)
        )

        etiqueta_titulo = ttk.Label(
            marco_titulo,
            text="Gestor Git",
            style="Titulo.TLabel"
        )

        etiqueta_titulo.pack(
            anchor="w"
        )

        etiqueta_subtitulo = ttk.Label(
            marco_titulo,
            text=(
                "Gestiona tus cambios paso a paso y aprende "
                "qué hace cada operación de Git."
            ),
            style="Subtitulo.TLabel"
        )

        etiqueta_subtitulo.pack(
            anchor="w",
            pady=(2, 0)
        )

        # ---------------------------------------------------------
        # Repositorio
        # ---------------------------------------------------------

        marco_repositorio = ttk.LabelFrame(
            marco_principal,
            text="Repositorio",
            padding=10
        )

        marco_repositorio.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        marco_repositorio.columnconfigure(
            0,
            weight=1
        )

        self.variable_ruta = tk.StringVar(
            value="Ningún repositorio seleccionado"
        )

        entrada_ruta = ttk.Entry(
            marco_repositorio,
            textvariable=self.variable_ruta,
            state="readonly"
        )

        entrada_ruta.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 10)
        )

        self.boton_seleccionar = ttk.Button(
            marco_repositorio,
            text="Seleccionar...",
            command=self.seleccionar_repositorio,
            style="Accion.TButton"
        )

        self.boton_seleccionar.grid(
            row=0,
            column=1
        )

        self.boton_actualizar = ttk.Button(
            marco_repositorio,
            text="Actualizar",
            command=self.actualizar_repositorio,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_actualizar.grid(
            row=0,
            column=2,
            padx=(10, 0)
        )

        # ---------------------------------------------------------
        # Información local
        # ---------------------------------------------------------

        marco_informacion = ttk.LabelFrame(
            marco_principal,
            text="Información local",
            padding=10
        )

        marco_informacion.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        self.variable_rama = tk.StringVar(
            value="-"
        )

        self.variable_remoto = tk.StringVar(
            value="-"
        )

        self.variable_commits = tk.StringVar(
            value="-"
        )

        ttk.Label(
            marco_informacion,
            text="Rama:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_informacion,
            textvariable=self.variable_rama
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 30)
        )

        ttk.Label(
            marco_informacion,
            text="Remoto(s):"
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_informacion,
            textvariable=self.variable_remoto
        ).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(0, 30)
        )

        ttk.Label(
            marco_informacion,
            text="Tiene commits:"
        ).grid(
            row=0,
            column=4,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_informacion,
            textvariable=self.variable_commits
        ).grid(
            row=0,
            column=5,
            sticky="w"
        )

        self.boton_historial = ttk.Button(
            marco_informacion,
            text="Historial...",
            command=self.abrir_historial,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_historial.grid(
            row=0,
            column=6,
            sticky="e",
            padx=(30, 0)
        )

        self.boton_ramas = ttk.Button(
            marco_informacion,
            text="Ramas...",
            command=self.abrir_ventana_ramas,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_ramas.grid(
            row=0,
            column=7,
            sticky="e",
            padx=(10, 0)
        )

        AyudaEmergente(
            self.boton_ramas,
            TEXTOS_AYUDA_GIT_V1["ramas"],
            ancho_texto=620
        )

        # ---------------------------------------------------------
        # Sincronización remota
        # ---------------------------------------------------------

        marco_sincronizacion = ttk.LabelFrame(
            marco_principal,
            text="Sincronización remota",
            padding=10
        )

        marco_sincronizacion.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        marco_sincronizacion.columnconfigure(
            7,
            weight=1
        )

        self.variable_upstream = tk.StringVar(
            value="-"
        )

        self.variable_rama_remota = tk.StringVar(
            value="-"
        )

        self.variable_por_subir = tk.StringVar(
            value="-"
        )

        self.variable_por_bajar = tk.StringVar(
            value="-"
        )

        self.variable_estado_sincronizacion = tk.StringVar(
            value="Seleccione un repositorio."
        )

        self.variable_ultima_consulta = tk.StringVar(
            value="Todavía no se ejecutó Fetch en esta sesión."
        )

        self.etiqueta_upstream = ttk.Label(
            marco_sincronizacion,
            text="Upstream:"
        )

        self.etiqueta_upstream.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_upstream
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 25)
        )

        self.etiqueta_rama_remota = ttk.Label(
            marco_sincronizacion,
            text="Rama remota:"
        )

        self.etiqueta_rama_remota.grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_rama_remota
        ).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(0, 25)
        )

        self.etiqueta_por_enviar = ttk.Label(
            marco_sincronizacion,
            text="Por enviar:"
        )

        self.etiqueta_por_enviar.grid(
            row=0,
            column=4,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_por_subir
        ).grid(
            row=0,
            column=5,
            sticky="w",
            padx=(0, 25)
        )

        self.etiqueta_por_descargar = ttk.Label(
            marco_sincronizacion,
            text="Por descargar:"
        )

        self.etiqueta_por_descargar.grid(
            row=0,
            column=6,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_por_bajar
        ).grid(
            row=0,
            column=7,
            sticky="w"
        )

        self.etiqueta_estado = ttk.Label(
            marco_sincronizacion,
            text="Estado:"
        )

        self.etiqueta_estado.grid(
            row=1,
            column=0,
            sticky="nw",
            padx=(0, 5),
            pady=(8, 0)
        )

        self.etiqueta_estado_sincronizacion = ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_estado_sincronizacion,
            wraplength=650,
            style="EstadoSincronizacion.TLabel"
        )

        self.etiqueta_estado_sincronizacion.grid(
            row=1,
            column=1,
            columnspan=5,
            sticky="ew",
            pady=(8, 10)
        )

        # ---------------------------------------------------------
        # Botones remotos
        # ---------------------------------------------------------

        marco_botones_remotos = ttk.Frame(
            marco_sincronizacion
        )

        marco_botones_remotos.grid(
            row=1,
            column=6,
            columnspan=2,
            sticky="e",
            pady=(8, 0)
        )

        self.boton_fetch = ttk.Button(
            marco_botones_remotos,
            text="Fetch",
            command=self.iniciar_fetch,
            state=tk.DISABLED,
            style="Fetch.TButton"
        )

        self.boton_fetch.pack(
            side=tk.LEFT
        )

        self.boton_pull = ttk.Button(
            marco_botones_remotos,
            text="Pull",
            command=self.iniciar_pull,
            state=tk.DISABLED,
            style="Pull.TButton"
        )

        self.boton_pull.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_push = ttk.Button(
            marco_botones_remotos,
            text="Push",
            command=self.iniciar_push,
            state=tk.DISABLED,
            style="Push.TButton"
        )

        self.boton_push.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_configurar_github = ttk.Button(
            marco_botones_remotos,
            text="Configurar GitHub...",
            command=self.abrir_configuracion_github,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_configurar_github.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.etiqueta_ultima_consulta = ttk.Label(
            marco_sincronizacion,
            textvariable=self.variable_ultima_consulta
        )

        self.etiqueta_ultima_consulta.grid(
            row=2,
            column=0,
            columnspan=8,
            sticky="w",
            pady=(8, 0)
        )

        etiqueta_guia_git = ttk.Label(
            marco_sincronizacion,
            text=(
                "Guía rápida:  "
                "Fetch = consultar cambios del remoto sin modificar tus archivos.   "
                "Pull = descargar commits remotos mediante fast-forward.   "
                "Push = enviar tus commits locales al remoto."
            ),
            style="AyudaVisible.TLabel",
            wraplength=1050
        )

        etiqueta_guia_git.grid(
            row=3,
            column=0,
            columnspan=8,
            sticky="ew",
            pady=(10, 0)
        )

        # ---------------------------------------------------------
        # Archivos con cambios
        # ---------------------------------------------------------

        marco_titulo_cambios = ttk.Frame(
            marco_principal
        )

        marco_titulo_cambios.grid(
            row=4,
            column=0,
            sticky="w",
            pady=(5, 5)
        )

        etiqueta_cambios = ttk.Label(
            marco_titulo_cambios,
            text="Archivos con cambios:",
            font=("Segoe UI", 10, "bold")
        )

        etiqueta_cambios.grid(
            row=0,
            column=0,
            sticky="w"
        )

        # Botón de la leyenda de estados Git: abre una ventana
        # educativa independiente y NO modal. Disponible siempre,
        # incluso sin repositorio, porque explica conceptos
        # generales (no ejecuta Git ni consulta el repositorio).
        boton_ayuda_estados_git = ttk.Button(
            marco_titulo_cambios,
            text="¿Qué significan estos estados?",
            command=self.abrir_ayuda_estados_git,
            style="Accion.TButton"
        )

        boton_ayuda_estados_git.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(12, 0)
        )

        marco_tabla = ttk.Frame(
            marco_principal
        )

        marco_tabla.grid(
            row=5,
            column=0,
            sticky="nsew"
        )

        marco_tabla.columnconfigure(
            0,
            weight=1
        )

        marco_tabla.rowconfigure(
            0,
            weight=1
        )

        columnas = (
            "estado",
            "preparado",
            "archivo"
        )

        self.tabla_cambios = ttk.Treeview(
            marco_tabla,
            columns=columnas,
            show="headings",
            selectmode="extended"
        )

        self.tabla_cambios.heading(
            "estado",
            text="Estado"
        )

        self.tabla_cambios.heading(
            "preparado",
            text="Preparado"
        )

        self.tabla_cambios.heading(
            "archivo",
            text="Archivo"
        )

        self.tabla_cambios.column(
            "estado",
            width=280,
            minwidth=180
        )

        self.tabla_cambios.column(
            "preparado",
            width=140,
            minwidth=110,
            anchor="center"
        )

        self.tabla_cambios.column(
            "archivo",
            width=650,
            minwidth=250
        )

        self.tabla_cambios.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        barra_vertical = ttk.Scrollbar(
            marco_tabla,
            orient=tk.VERTICAL,
            command=self.tabla_cambios.yview
        )

        barra_vertical.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.tabla_cambios.configure(
            yscrollcommand=barra_vertical.set
        )

        barra_horizontal = ttk.Scrollbar(
            marco_tabla,
            orient=tk.HORIZONTAL,
            command=self.tabla_cambios.xview
        )

        barra_horizontal.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        self.tabla_cambios.configure(
            xscrollcommand=barra_horizontal.set
        )

        # Actualiza los botones de archivos según la selección.
        self.tabla_cambios.bind(
            "<<TreeviewSelect>>",
            self.actualizar_estado_botones_archivos
        )

        # ---------------------------------------------------------
        # Acciones sobre archivos
        # ---------------------------------------------------------

        marco_acciones = ttk.Frame(
            marco_principal
        )

        marco_acciones.grid(
            row=6,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        self.boton_seleccionar_todo = ttk.Button(
            marco_acciones,
            text="Seleccionar todo",
            command=self.seleccionar_todos_los_cambios,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_seleccionar_todo.pack(
            side=tk.LEFT
        )

        self.boton_preparar = ttk.Button(
            marco_acciones,
            text="Preparar seleccionados",
            command=self.preparar_seleccionados,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_preparar.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_actualizar_preparados = ttk.Button(
            marco_acciones,
            text="Actualizar preparados",
            command=self.actualizar_preparados_seleccionados,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_actualizar_preparados.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_quitar_preparados = ttk.Button(
            marco_acciones,
            text="Quitar de preparados",
            command=self.quitar_preparados_seleccionados,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_quitar_preparados.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.boton_ver_cambios_locales = ttk.Button(
            marco_acciones,
            text="Ver cambios locales...",
            command=self.abrir_cambios_locales,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_ver_cambios_locales.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        # ---------------------------------------------------------
        # Crear commit
        # ---------------------------------------------------------

        marco_commit = ttk.LabelFrame(
            marco_principal,
            text="Crear commit",
            padding=10
        )

        marco_commit.grid(
            row=7,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        marco_commit.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            marco_commit,
            text="Mensaje:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10)
        )

        self.variable_mensaje_commit = tk.StringVar()

        self.entrada_mensaje_commit = ttk.Entry(
            marco_commit,
            textvariable=self.variable_mensaje_commit
        )

        self.entrada_mensaje_commit.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 10)
        )

        self.boton_crear_commit = ttk.Button(
            marco_commit,
            text="Crear commit",
            command=self.crear_commit_desde_interfaz,
            state=tk.DISABLED,
            style="Commit.TButton"
        )

        self.boton_crear_commit.grid(
            row=0,
            column=2
        )

        ttk.Label(
            marco_commit,
            text=(
                "El commit se guardará solamente en el repositorio local. "
                "Utilice Push para enviarlo al remoto."
            )
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 0)
        )

        # ---------------------------------------------------------
        # Barra de estado
        # ---------------------------------------------------------

        self.variable_estado = tk.StringVar(
            value="Listo."
        )

        self.etiqueta_estado = tk.Label(
            marco_principal,
            textvariable=self.variable_estado,
            anchor="w",
            padx=10,
            pady=7,
            background="#E2E8F0",
            foreground="#334155",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold")
        )

        self.etiqueta_estado.grid(
            row=8,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        # Cuando cambia el texto de estado actualizamos
        # automáticamente su apariencia.
        self.variable_estado.trace_add(
            "write",
            self.actualizar_apariencia_estado
        )

        self.actualizar_apariencia_estado()
        self.configurar_ayudas()

    def configurar_ayudas(self):
        """
        Agrega explicaciones educativas a los controles principales.

        Guardamos las ayudas en una lista para mantener
        sus objetos disponibles durante toda la aplicación.
        """

        self.ayudas_emergentes = [
            AyudaEmergente(
                self.boton_seleccionar,
                TEXTOS_AYUDA_GIT_V1["seleccionar_repositorio"]
            ),

            AyudaEmergente(
                self.boton_actualizar,
                TEXTOS_AYUDA_GIT_V1["actualizar_estado_local"]
            ),

            AyudaEmergente(
                self.boton_historial,
                TEXTOS_AYUDA_GIT_V1["historial"]
            ),

            AyudaEmergente(
                self.boton_fetch,
                TEXTOS_AYUDA_GIT_V1["fetch"],
                ancho_texto=620
            ),

            AyudaEmergente(
                self.boton_pull,
                TEXTOS_AYUDA_GIT_V1["pull"],
                ancho_texto=620
            ),

            AyudaEmergente(
                self.boton_push,
                TEXTOS_AYUDA_GIT_V1["push"],
                ancho_texto=620
            ),

            AyudaEmergente(
                self.boton_configurar_github,
                TEXTOS_AYUDA_GIT_V1["configurar_github"],
                ancho_texto=620
            ),

            AyudaEmergente(
                self.boton_seleccionar_todo,
                TEXTOS_AYUDA_GIT_V1["seleccionar_todo"]
            ),

            AyudaEmergente(
                self.boton_preparar,
                TEXTOS_AYUDA_GIT_V1["preparar"],
                ancho_texto=620
            ),

            AyudaEmergente(
                self.boton_actualizar_preparados,
                TEXTOS_AYUDA_GIT_V1["actualizar_preparados"],
                ancho_texto=620
            ),

            AyudaEmergente(
                self.boton_quitar_preparados,
                TEXTOS_AYUDA_GIT_V1["quitar_preparados"],
                ancho_texto=620
            ),

            AyudaEmergente(
                self.boton_ver_cambios_locales,
                TEXTOS_AYUDA_GIT_V1["ver_cambios_locales"]
            ),

            AyudaEmergente(
                self.boton_crear_commit,
                TEXTOS_AYUDA_GIT_V1["commit"],
                ancho_texto=620
            )
        ]

        # Conceptos de sincronización: las etiquetas existen desde
        # el __init__, por lo que aquí solo se agregan las ayudas.
        self.ayudas_conceptos_sincronizacion = [
            AyudaEmergente(
                self.etiqueta_upstream,
                TEXTOS_AYUDA_GIT_V1["concepto_upstream"]
            ),
            AyudaEmergente(
                self.etiqueta_rama_remota,
                TEXTOS_AYUDA_GIT_V1["concepto_rama_remota"]
            ),
            AyudaEmergente(
                self.etiqueta_por_enviar,
                TEXTOS_AYUDA_GIT_V1["concepto_por_enviar"]
            ),
            AyudaEmergente(
                self.etiqueta_por_descargar,
                TEXTOS_AYUDA_GIT_V1["concepto_por_descargar"]
            ),
            AyudaEmergente(
                self.etiqueta_estado,
                TEXTOS_AYUDA_GIT_V1["concepto_estado_sincronizacion"]
            ),
            AyudaEmergente(
                self.etiqueta_ultima_consulta,
                TEXTOS_AYUDA_GIT_V1["concepto_ultima_consulta"]
            )
        ]

    def actualizar_apariencia_estado(
        self,
        *_argumentos
    ):
        """
        Cambia el color de la barra inferior según
        el tipo de mensaje mostrado.

        Los mensajes de éxito se evalúan antes que
        las advertencias para evitar que frases como
        "No hay cambios pendientes" aparezcan en amarillo.
        """

        texto = (
            self.variable_estado.get().lower()
        )

        # Estado neutro.
        fondo = "#E2E8F0"
        texto_color = "#334155"

        palabras_error = (
            "error",
            "falló",
            "no realizado",
            "no fue posible",
            "conflicto",
            "bloqueado"
        )

        palabras_proceso = (
            "consultando",
            "analizando",
            "en curso",
            "preparando",
            "creando",
            "verificando"
        )

        palabras_exito = (
            "completado",
            "correctamente",
            "repositorio limpio",
            "sincronizada",
            "git disponible"
        )

        palabras_advertencia = (
            "pendiente",
            "diverg",
            "por descargar",
            "por enviar"
        )

        if any(
            palabra in texto
            for palabra in palabras_error
        ):
            fondo = "#FEE2E2"
            texto_color = "#991B1B"

        elif any(
            palabra in texto
            for palabra in palabras_proceso
        ):
            fondo = "#DBEAFE"
            texto_color = "#1E40AF"

        elif any(
            palabra in texto
            for palabra in palabras_exito
        ):
            fondo = "#DCFCE7"
            texto_color = "#166534"

        elif any(
            palabra in texto
            for palabra in palabras_advertencia
        ):
            fondo = "#FEF3C7"
            texto_color = "#92400E"

        self.etiqueta_estado.config(
            background=fondo,
            foreground=texto_color
        )

    def verificar_git(self):
        """
        Verifica que git.exe esté disponible.
        """

        if self.servicio_git.git_disponible():
            resultado = self.servicio_git.obtener_version()

            if resultado.exitoso:
                self.variable_estado.set(
                    f"Git disponible: {resultado.salida}"
                )
            else:
                self.variable_estado.set(
                    "Git fue encontrado, pero no pudo ejecutarse."
                )

            return

        self.variable_estado.set(
            "Git no fue encontrado."
        )

        self.boton_seleccionar.config(
            state=tk.DISABLED
        )

        messagebox.showerror(
            "Git no disponible",
            (
                "No fue posible encontrar git.exe.\n\n"
                "Verifique que Git esté instalado y disponible "
                "en el PATH de Windows."
            )
        )

    def seleccionar_repositorio(self):
        """
        Permite seleccionar un repositorio.
        """

        if self.operacion_remota_en_curso:
            return

        ruta_seleccionada = filedialog.askdirectory(
            title="Seleccionar repositorio Git"
        )

        if not ruta_seleccionada:
            return

        self.cargar_repositorio(
            ruta_seleccionada,
            reiniciar_fetch=True,
            guardar_configuracion=True
        )

    def cargar_repositorio_recordado(self):
        """
        Carga automáticamente el último repositorio seleccionado.

        Solamente carga el estado LOCAL del repositorio:
        no ejecuta Fetch, Pull ni Push.
        """

        if not self.servicio_git.git_disponible():
            return

        resultado = (
            self.servicio_configuracion.cargar_ultimo_repositorio()
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No se pudo cargar el repositorio recordado. "
                "Seleccione un repositorio manualmente."
            )

            return

        if not resultado.ruta_repositorio:
            return

        self.cargar_repositorio(
            resultado.ruta_repositorio
        )

        self.variable_estado.set(
            "Repositorio recordado cargado. "
            "Pulse Fetch para consultar el remoto."
        )

    def cargar_repositorio(
        self,
        ruta_repositorio,
        reiniciar_fetch=False,
        guardar_configuracion=False
    ):
        """
        Valida y carga un repositorio.

        Cuando reiniciar_fetch es True se exige un nuevo Fetch
        antes de habilitar Pull o Push.

        Cuando guardar_configuracion es True se recuerda la ruta
        en config.json para el próximo inicio; un fallo de
        guardado no impide seguir trabajando.
        """

        self.variable_estado.set(
            "Analizando repositorio..."
        )

        self.ventana_principal.update_idletasks()

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            self.limpiar_repositorio()

            messagebox.showwarning(
                "Repositorio no válido",
                estado.mensaje
            )

            self.variable_estado.set(
                estado.mensaje
            )

            return

        ruta_anterior = self.ruta_repositorio

        if (
            ruta_anterior
            and ruta_anterior != estado.ruta_raiz
        ):
            self.cerrar_historial()
            self.cerrar_configuracion_github()
            self.cerrar_detalle_commit()
            self.cerrar_cambios_locales()
            self.cerrar_ventana_ramas()

        self.ruta_repositorio = estado.ruta_raiz

        self.remotos_repositorio = list(
            estado.remotos
        )

        if (
            reiniciar_fetch
            or ruta_anterior != self.ruta_repositorio
        ):
            self.fetch_exitoso_en_sesion = False

        self.variable_ruta.set(
            estado.ruta_raiz
        )

        self.variable_rama.set(
            estado.rama_actual
            if estado.rama_actual
            else "No determinada"
        )

        self.variable_remoto.set(
            ", ".join(estado.remotos)
            if estado.remotos
            else "Sin remoto"
        )

        self.variable_commits.set(
            "Sí"
            if estado.tiene_commits
            else "No"
        )

        self.boton_actualizar.config(
            state=tk.NORMAL
        )

        self.boton_historial.config(
            state=tk.NORMAL
        )

        self.boton_ramas.config(
            state=tk.NORMAL
        )

        self.boton_fetch.config(
            state=(
                tk.NORMAL
                if estado.remotos
                else tk.DISABLED
            )
        )

        self.boton_configurar_github.config(
            state=(
                tk.NORMAL
                if not estado.remotos
                else tk.DISABLED
            )
        )

        if not self.fetch_exitoso_en_sesion:
            self.variable_ultima_consulta.set(
                "Información local. Pulse Fetch para consultar el remoto."
            )

        self.cargar_cambios()

        # Esta consulta no accede a Internet.
        self.cargar_estado_sincronizacion_local()

        self.actualizar_historial_si_abierto()

        if guardar_configuracion:
            resultado_guardado = (
                self.servicio_configuracion.guardar_ultimo_repositorio(
                    self.ruta_repositorio
                )
            )

            if not resultado_guardado.exitoso:
                self.variable_estado.set(
                    "El repositorio fue cargado, pero no fue posible "
                    "recordarlo para el próximo inicio."
                )

    def cargar_cambios(self):
        """
        Consulta y muestra los archivos pendientes.
        """

        self.limpiar_tabla()

        if not self.ruta_repositorio:
            return

        resultado = self.servicio_git.obtener_cambios(
            self.ruta_repositorio
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible consultar los cambios."
            )

            self.hay_cambios_pendientes = True

            self.deshabilitar_botones_de_archivos()

            self.actualizar_estado_botones_sincronizacion()

            messagebox.showerror(
                "Error al consultar Git",
                resultado.error
            )

            return

        for cambio in resultado.cambios:
            if cambio.en_conflicto:
                # Un conflicto no es "preparado" ni "sin
                # preparar": es un estado especial que bloquea
                # las acciones de staging.
                texto_preparado = "No aplica"
            elif not cambio.preparado:
                texto_preparado = "No"
            elif cambio.requiere_actualizar_preparado:
                texto_preparado = "Sí (hay cambios nuevos)"
            else:
                texto_preparado = "Sí"

            identificador = self.tabla_cambios.insert(
                "",
                tk.END,
                values=(
                    cambio.descripcion,
                    texto_preparado,
                    cambio.ruta
                )
            )

            self.cambios_por_elemento[
                identificador
            ] = cambio

        cantidad = len(
            resultado.cambios
        )

        self.hay_cambios_pendientes = (
            cantidad > 0
        )

        self.actualizar_estado_botones_archivos()

        self.actualizar_estado_botones_sincronizacion()

        if cantidad == 0:
            self.variable_estado.set(
                "Repositorio limpio. No hay cambios pendientes."
            )

        elif cantidad == 1:
            self.variable_estado.set(
                "1 archivo con cambios pendientes."
            )

        else:
            self.variable_estado.set(
                f"{cantidad} archivos con cambios pendientes."
            )

    def cargar_estado_sincronizacion_local(self):
        """
        Muestra el estado utilizando únicamente
        las referencias disponibles localmente.

        No realiza conexión de red.
        """

        if not self.ruta_repositorio:
            self.limpiar_estado_sincronizacion()
            return

        estado = self.servicio_git.obtener_estado_sincronizacion(
            self.ruta_repositorio
        )

        self.aplicar_estado_sincronizacion(
            estado
        )

    def aplicar_estado_sincronizacion(
        self,
        estado
    ):
        """
        Copia EstadoSincronizacion a la interfaz.
        """

        self.estado_sincronizacion_actual = estado

        if not estado.exitoso:
            self.variable_upstream.set("-")
            self.variable_rama_remota.set("-")
            self.variable_por_subir.set("-")
            self.variable_por_bajar.set("-")

            self.variable_estado_sincronizacion.set(
                estado.error
            )

            self.actualizar_estado_botones_sincronizacion()

            return

        self.variable_upstream.set(
            "Configurado"
            if estado.upstream_configurado
            else "No configurado"
        )

        texto_rama_remota = (
            estado.rama_remota
        )

        if not estado.rama_remota_existe:
            texto_rama_remota += (
                " (no existe)"
            )

        self.variable_rama_remota.set(
            texto_rama_remota
        )

        self.variable_por_subir.set(
            str(
                estado.commits_por_subir
            )
        )

        self.variable_por_bajar.set(
            str(
                estado.commits_por_bajar
            )
        )

        self.variable_estado_sincronizacion.set(
            estado.mensaje
        )

        self.actualizar_estado_botones_sincronizacion()

    def actualizar_repositorio(self):
        """
        Vuelve a consultar el repositorio seleccionado.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        self.cargar_repositorio(
            self.ruta_repositorio,
            reiniciar_fetch=False
        )

    # =============================================================
    # RAMAS LOCALES
    # =============================================================

    def abrir_ventana_ramas(self):
        """
        Abre la ventana única de ramas locales.

        Si ya existe una abierta, se destruye y se recrea.
        Todos los chequeos son locales: nunca Fetch/Pull/Push.
        """

        if not self.ruta_repositorio:
            return

        if (
            self.ventana_ramas is not None
            and self.ventana_ramas.winfo_exists()
        ):
            self.cerrar_ventana_ramas()

        self.crear_ventana_ramas()

    def crear_ventana_ramas(self):
        """
        Crea la ventana de ramas locales.
        """

        self.ventana_ramas = tk.Toplevel(
            self.ventana_principal
        )

        self.ventana_ramas.title(
            "Ramas locales - Gestor Git"
        )

        self.ventana_ramas.geometry(
            "580x520"
        )

        self.ventana_ramas.minsize(
            480,
            380
        )

        self.ventana_ramas.transient(
            self.ventana_principal
        )

        self.ventana_ramas.protocol(
            "WM_DELETE_WINDOW",
            self.cerrar_ventana_ramas
        )

        marco_ramas = ttk.Frame(
            self.ventana_ramas,
            padding=15
        )

        marco_ramas.pack(
            fill=tk.BOTH,
            expand=True
        )

        marco_ramas.columnconfigure(
            0,
            weight=1
        )

        ttk.Label(
            marco_ramas,
            text=(
                "GestorGit trabaja con ramas LOCALES.\n\n"
                "Cambiar de rama actualiza los archivos del "
                "working tree. Solo es posible cuando el "
                "repositorio está completamente limpio (sin "
                "cambios, sin archivos preparados y sin archivos "
                "nuevos).\n\n"
                "Crear una rama la crea DESDE el commit actual "
                "y GestorGit cambia a ella. La rama nueva "
                "SOLO vive en este repositorio local: no se "
                "publica en GitHub ni recibe upstream.\n\n"
                "No se ejecuta Fetch, Pull, Push, Merge ni "
                "Rebase desde esta ventana."
            ),
            wraplength=540,
            justify="left"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 10)
        )

        ttk.Label(
            marco_ramas,
            text="Rama actual:"
        ).grid(
            row=1,
            column=0,
            sticky="w"
        )

        self.variable_rama_actual_ventana = tk.StringVar(
            value="Consultando..."
        )

        ttk.Label(
            marco_ramas,
            textvariable=self.variable_rama_actual_ventana
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(0, 8)
        )

        marco_tabla = ttk.Frame(
            marco_ramas
        )

        marco_tabla.grid(
            row=3,
            column=0,
            sticky="nsew"
        )

        marco_tabla.columnconfigure(
            0,
            weight=1
        )

        marco_tabla.rowconfigure(
            0,
            weight=1
        )

        self.tabla_ramas = ttk.Treeview(
            marco_tabla,
            columns=("rama",),
            show="headings",
            selectmode="browse",
            height=7
        )

        self.tabla_ramas.heading(
            "rama",
            text="Rama local"
        )

        self.tabla_ramas.column(
            "rama",
            anchor="w",
            width=420
        )

        self.tabla_ramas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        desplazamiento_ramas = ttk.Scrollbar(
            marco_tabla,
            orient="vertical",
            command=self.tabla_ramas.yview
        )

        desplazamiento_ramas.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.tabla_ramas.configure(
            yscrollcommand=desplazamiento_ramas.set
        )

        self.tabla_ramas.bind(
            "<<TreeviewSelect>>",
            self.actualizar_estado_botones_ventana_ramas
        )

        self.variable_estado_ramas = tk.StringVar(
            value=""
        )

        ttk.Label(
            marco_ramas,
            textvariable=self.variable_estado_ramas,
            wraplength=540,
            justify="left"
        ).grid(
            row=4,
            column=0,
            sticky="w",
            pady=(6, 0)
        )

        marco_nueva = ttk.Frame(
            marco_ramas
        )

        marco_nueva.grid(
            row=5,
            column=0,
            sticky="ew",
            pady=(12, 0)
        )

        marco_nueva.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            marco_nueva,
            text="Nueva rama:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 6)
        )

        self.variable_nueva_rama = tk.StringVar(
            value=""
        )

        self.entrada_nueva_rama = ttk.Entry(
            marco_nueva,
            textvariable=self.variable_nueva_rama
        )

        self.entrada_nueva_rama.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 8)
        )

        self.boton_crear_rama = ttk.Button(
            marco_nueva,
            text="Crear rama",
            command=self.confirmar_creacion_rama,
            state=tk.DISABLED
        )

        self.boton_crear_rama.grid(
            row=0,
            column=2,
            sticky="e"
        )

        AyudaEmergente(
            self.boton_crear_rama,
            TEXTOS_AYUDA_GIT_V1["crear_rama"],
            ancho_texto=620
        )

        self.variable_nueva_rama.trace_add(
            "write",
            lambda *_cambios: (
                self.actualizar_estado_botones_ventana_ramas()
            )
        )

        marco_acciones = ttk.Frame(
            marco_ramas
        )

        marco_acciones.grid(
            row=6,
            column=0,
            sticky="ew",
            pady=(12, 0)
        )

        self.boton_cambiar_rama = ttk.Button(
            marco_acciones,
            text="Cambiar a seleccionada",
            command=self.confirmar_cambio_rama,
            state=tk.DISABLED
        )

        self.boton_cambiar_rama.grid(
            row=0,
            column=0,
            sticky="w"
        )

        AyudaEmergente(
            self.boton_cambiar_rama,
            TEXTOS_AYUDA_GIT_V1["cambiar_rama"],
            ancho_texto=620
        )

        self.boton_actualizar_ramas = ttk.Button(
            marco_acciones,
            text="Actualizar",
            command=self.cargar_lista_ramas
        )

        self.boton_actualizar_ramas.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(10, 0)
        )

        AyudaEmergente(
            self.boton_actualizar_ramas,
            TEXTOS_AYUDA_GIT_V1["actualizar_ramas"]
        )

        ttk.Button(
            marco_acciones,
            text="Cerrar",
            command=self.cerrar_ventana_ramas
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(10, 0)
        )

        self.cargar_lista_ramas()

    def cargar_lista_ramas(self):
        """
        Consulta las ramas locales y refresca la ventana.

        Consulta 100 % local: nunca Fetch ni Internet.
        """

        if not self.ruta_repositorio:
            return

        if (
            self.ventana_ramas is None
            or not self.ventana_ramas.winfo_exists()
        ):
            return

        resultado = self.servicio_ramas.obtener_ramas_locales(
            self.ruta_repositorio
        )

        self.tabla_ramas.delete(
            *self.tabla_ramas.get_children()
        )

        self.variable_estado_ramas.set(
            ""
        )

        if not resultado.exitoso:
            self.variable_estado_ramas.set(
                resultado.error
            )

            self.rama_actual_ventana_actual = ""

            self.variable_rama_actual_ventana.set(
                "No determinada"
            )

            self.actualizar_estado_botones_ventana_ramas()

            return

        rama_actual = ""

        for rama in resultado.ramas:
            texto = rama.nombre

            if rama.actual:
                texto += "  (actual)"
                rama_actual = rama.nombre

            self.tabla_ramas.insert(
                "",
                tk.END,
                iid=rama.nombre,
                values=(texto,)
            )

        self.rama_actual_ventana_actual = rama_actual

        if rama_actual:
            self.variable_rama_actual_ventana.set(
                rama_actual
            )
        elif not resultado.tiene_commits:
            self.variable_rama_actual_ventana.set(
                "Repositorio sin commits todavía"
            )
        elif resultado.head_separado:
            self.variable_rama_actual_ventana.set(
                "HEAD separado (no se encuentra en ninguna rama)"
            )
        else:
            self.variable_rama_actual_ventana.set(
                "No determinada"
            )

        if resultado.mensaje:
            self.variable_estado_ramas.set(
                resultado.mensaje
            )

        self.actualizar_estado_botones_ventana_ramas()

    def actualizar_estado_botones_ventana_ramas(self, _evento=None):
        """
        Habilita Cambiar/Crear según la selección, el texto de
        la entrada y las operaciones remotas en curso.

        Segura si la ventana de ramas no existe.
        """

        if (
            self.ventana_ramas is None
            or not self.ventana_ramas.winfo_exists()
        ):
            return

        if self.operacion_remota_en_curso:
            self.boton_cambiar_rama.config(
                state=tk.DISABLED
            )

            self.boton_crear_rama.config(
                state=tk.DISABLED
            )

            return

        seleccion = self.tabla_ramas.selection()

        puede_cambiar = False

        if seleccion:
            nombre_seleccionada = seleccion[0]

            puede_cambiar = (
                nombre_seleccionada
                and nombre_seleccionada
                != self.rama_actual_ventana_actual
            )

        self.boton_cambiar_rama.config(
            state=(
                tk.NORMAL
                if puede_cambiar
                else tk.DISABLED
            )
        )

        tiene_nombre = bool(
            self.variable_nueva_rama.get()
        )

        self.boton_crear_rama.config(
            state=(
                tk.NORMAL
                if tiene_nombre
                else tk.DISABLED
            )
        )

    def confirmar_cambio_rama(self):
        """
        Confirma y ejecuta el cambio a la rama seleccionada.
        """

        if self.operacion_remota_en_curso:
            self.variable_estado.set(
                "Espere a que termine la operación remota en "
                "curso antes de cambiar de rama."
            )

            return

        if not self.ruta_repositorio:
            return

        seleccion = self.tabla_ramas.selection()

        if not seleccion:
            return

        nombre_rama = seleccion[0]

        rama_actual_mostrada = (
            self.rama_actual_ventana_actual
            or "HEAD separado"
        )

        confirmado = messagebox.askyesno(
            "Cambiar de rama",
            (
                "Cambiar de rama actualizará los archivos del "
                "working tree para que coincidan con la rama "
                "seleccionada.\n\n"
                f"Rama actual: {rama_actual_mostrada}\n"
                f"Nueva rama: {nombre_rama}\n\n"
                "GestorGit realizará el cambio únicamente si el "
                "repositorio continúa limpio; el servicio volverá "
                "a comprobarlo antes de ejecutar git switch.\n\n"
                "No se ejecutará Fetch, Pull, Push, Merge ni "
                "Rebase."
            ),
            parent=self.ventana_ramas
        )

        if not confirmado:
            return

        resultado = self.servicio_ramas.cambiar_rama(
            self.ruta_repositorio,
            nombre_rama
        )

        if not resultado.exitoso:
            messagebox.showerror(
                "Cambio de rama bloqueado",
                resultado.error,
                parent=self.ventana_ramas
            )

            self.cargar_lista_ramas()

            return

        self.refrescar_despues_de_ramas()

        self.variable_estado.set(
            resultado.mensaje
        )

    def confirmar_creacion_rama(self):
        """
        Confirma y ejecuta la creación de una rama local.
        """

        if self.operacion_remota_en_curso:
            self.variable_estado.set(
                "Espere a que termine la operación remota en "
                "curso antes de crear una rama."
            )

            return

        if not self.ruta_repositorio:
            return

        nombre_rama = self.variable_nueva_rama.get()

        if not nombre_rama:
            return

        confirmado = messagebox.askyesno(
            "Crear rama local",
            (
                "Se creará la rama local:\n\n"
                f"{nombre_rama}\n\n"
                "desde el commit actual y GestorGit cambiará "
                "a ella.\n\n"
                "La rama NO se publicará en GitHub y no tendrá "
                "upstream hasta que se implemente o ejecute "
                "explícitamente la publicación de ramas.\n\n"
                "GestorGit realizará la creación únicamente si "
                "el repositorio continúa limpio; el servicio "
                "volverá a comprobarlo antes de ejecutar "
                "git switch."
            ),
            parent=self.ventana_ramas
        )

        if not confirmado:
            return

        resultado = self.servicio_ramas.crear_rama(
            self.ruta_repositorio,
            nombre_rama
        )

        if not resultado.exitoso:
            messagebox.showerror(
                "Creación de rama bloqueada",
                resultado.error,
                parent=self.ventana_ramas
            )

            self.cargar_lista_ramas()

            return

        self.variable_nueva_rama.set("")

        self.refrescar_despues_de_ramas()

        messagebox.showinfo(
            "Rama local creada",
            resultado.mensaje,
            parent=self.ventana_ramas
        )

        self.variable_estado.set(
            resultado.mensaje
        )

    def refrescar_despues_de_ramas(self):
        """
        Recarga el estado LOCAL tras cambiar o crear una rama.

        Cierra las ventanas auxiliares que podrían contener
        información de la rama anterior, exige un Fetch nuevo
        (el contexto remoto pudo cambiar) y recarga la lista.
        Nunca ejecuta Fetch automáticamente.
        """

        self.cerrar_historial()
        self.cerrar_detalle_commit()
        self.cerrar_cambios_locales()

        self.cargar_repositorio(
            self.ruta_repositorio,
            reiniciar_fetch=True
        )

        self.cargar_lista_ramas()

    def cerrar_ventana_ramas(self):
        """
        Cierra la ventana de ramas y libera sus referencias.
        """

        ventana = self.ventana_ramas

        self.ventana_ramas = None
        self.tabla_ramas = None
        self.variable_estado_ramas = None
        self.variable_rama_actual_ventana = None
        self.variable_nueva_rama = None
        self.entrada_nueva_rama = None
        self.boton_cambiar_rama = None
        self.boton_crear_rama = None
        self.rama_actual_ventana_actual = ""

        if (
            ventana is not None
            and ventana.winfo_exists()
        ):
            ventana.destroy()

    # =============================================================
    # AYUDA DE ESTADOS GIT (leyenda contextual de la tabla)
    # =============================================================

    def abrir_ayuda_estados_git(self):
        """
        Abre la ventana única de la leyenda de estados Git.

        Si ya existe una abierta, la trae al frente en lugar de
        crear copias sucesivas. La ventana es NO modal: la
        ventana principal sigue siendo usable mientras
        permanezca abierta.

        Solo muestra texto: nunca ejecuta Git, no consulta el
        repositorio, no ejecuta Fetch/Pull/Push y no modifica el
        working tree, el índice ni HEAD.
        """

        if (
            self.ventana_ayuda_estados_git is not None
            and self.ventana_ayuda_estados_git.winfo_exists()
        ):
            self.ventana_ayuda_estados_git.deiconify()
            self.ventana_ayuda_estados_git.lift()
            self.ventana_ayuda_estados_git.focus_force()
            return

        self.crear_ventana_ayuda_estados_git()

    def crear_ventana_ayuda_estados_git(self):
        """
        Crea la ventana educativa de los estados de la tabla.

        tk.Text de solo lectura con wrap por palabras, scroll
        vertical, seleccionable y redimensionable. Todo el
        contenido procede de CONTENIDO_AYUDA_ESTADOS_GIT_V1.
        """

        self.ventana_ayuda_estados_git = tk.Toplevel(
            self.ventana_principal
        )

        self.ventana_ayuda_estados_git.title(
            "Estados Git - Gestor Git"
        )

        self.ventana_ayuda_estados_git.geometry(
            "820x680"
        )

        self.ventana_ayuda_estados_git.minsize(
            600,
            400
        )

        self.ventana_ayuda_estados_git.transient(
            self.ventana_principal
        )

        self.ventana_ayuda_estados_git.protocol(
            "WM_DELETE_WINDOW",
            self.cerrar_ventana_ayuda_estados_git
        )

        marco_ayuda = ttk.Frame(
            self.ventana_ayuda_estados_git,
            padding=12
        )

        marco_ayuda.pack(
            fill=tk.BOTH,
            expand=True
        )

        marco_ayuda.columnconfigure(
            0,
            weight=1
        )

        marco_ayuda.rowconfigure(
            0,
            weight=1
        )

        self.texto_ayuda_estados_git = tk.Text(
            marco_ayuda,
            wrap=tk.WORD,
            font=("Segoe UI", 10)
        )

        scrollbar_ayuda = ttk.Scrollbar(
            marco_ayuda,
            orient=tk.VERTICAL,
            command=self.texto_ayuda_estados_git.yview
        )

        self.texto_ayuda_estados_git.configure(
            yscrollcommand=scrollbar_ayuda.set
        )

        self.texto_ayuda_estados_git.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        scrollbar_ayuda.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        # Jerarquía visual de la ventana de ayuda: títulos de
        # sección en negrita algo mayor, subtítulos cortos en
        # negrita y códigos Git en monoespaciada negrita. Sin
        # colores ni decoración: solo negrita y monoespaciado.
        self.texto_ayuda_estados_git.tag_configure(
            "titulo_seccion",
            font=("Segoe UI", 11, "bold"),
            spacing1=6,
            spacing3=6
        )

        self.texto_ayuda_estados_git.tag_configure(
            "subtitulo",
            font=("Segoe UI", 10, "bold")
        )

        self.texto_ayuda_estados_git.tag_configure(
            "codigo_git",
            font=("Consolas", 10, "bold")
        )

        secciones_ayuda = (
            "modelo_head_indice_working_tree",
            "estado_no_rastreado",
            "estado_modificado_sin_preparar",
            "estado_modificado_preparado",
            "estado_preparado_y_vuelto_a_modificar",
            "estado_conflicto",
            "otros_estados",
            "codigos_xy",
            "inspector_y_acciones",
        )

        for clave in secciones_ayuda:
            # "end-1c" es el índice real de inserción en tk.Text
            # (tk.END apunta un carácter después del último). Se
            # captura ANTES de insertar para marcar exactamente la
            # primera línea del bloque como título de sección.
            inicio = self.texto_ayuda_estados_git.index("end-1c")

            self.texto_ayuda_estados_git.insert(
                tk.END,
                CONTENIDO_AYUDA_ESTADOS_GIT_V1[clave]
            )
            self.texto_ayuda_estados_git.insert(
                tk.END,
                "\n\n"
            )

            self.texto_ayuda_estados_git.tag_add(
                "titulo_seccion",
                inicio,
                f"{inicio} lineend"
            )

        self._aplicar_tags_ayuda_estados_git()

        self.texto_ayuda_estados_git.configure(
            state=tk.DISABLED
        )

    def _aplicar_tags_ayuda_estados_git(self):
        """
        Aplica los tags de subtítulos y códigos Git por igualdad
        EXACTA de línea completa.

        Recorre las líneas ya insertadas y compara line.strip() con
        las constantes _SUBTITULOS_AYUDA_ESTADOS y
        _LINEAS_CODIGO_GIT_AYUDA. NO usa regex ni busca una letra
        M aislada: los patrones son textos completos, por lo que
        " M" y "M " se distinguen sin ambigüedad y una M común nunca
        recibe el tag.
        """

        contenido = self.texto_ayuda_estados_git.get(
            "1.0",
            tk.END
        )

        indice = "1.0"

        for linea in contenido.splitlines():
            texto_linea = linea.strip()

            if texto_linea in _SUBTITULOS_AYUDA_ESTADOS:
                self.texto_ayuda_estados_git.tag_add(
                    "subtitulo",
                    indice,
                    f"{indice} lineend"
                )
            elif texto_linea in _LINEAS_CODIGO_GIT_AYUDA:
                self.texto_ayuda_estados_git.tag_add(
                    "codigo_git",
                    indice,
                    f"{indice} lineend"
                )

            indice = f"{indice} +1 line"

    def cerrar_ventana_ayuda_estados_git(self):
        """
        Cierra la ventana de la leyenda y libera sus referencias.
        """

        ventana = self.ventana_ayuda_estados_git

        self.ventana_ayuda_estados_git = None
        self.texto_ayuda_estados_git = None

        if (
            ventana is not None
            and ventana.winfo_exists()
        ):
            ventana.destroy()

    # =============================================================
    # HISTORIAL DE COMMITS
    # =============================================================

    def abrir_historial(self):
        """
        Abre una ventana de solo lectura con los commits locales.
        """

        if not self.ruta_repositorio:
            return

        if (
            self.ventana_historial is not None
            and self.ventana_historial.winfo_exists()
        ):
            self.ventana_historial.deiconify()
            self.ventana_historial.lift()
            self.ventana_historial.focus_force()
            self.cargar_historial()
            return

        self.crear_ventana_historial()
        self.cargar_historial()

    def crear_ventana_historial(self):
        """
        Construye la ventana, los filtros y la tabla del historial.
        """

        self.ventana_historial = tk.Toplevel(
            self.ventana_principal
        )

        self.ventana_historial.title(
            "Historial de commits - Gestor Git"
        )

        self.ventana_historial.geometry(
            "1180x640"
        )

        self.ventana_historial.minsize(
            900,
            480
        )

        self.ventana_historial.transient(
            self.ventana_principal
        )

        self.ventana_historial.protocol(
            "WM_DELETE_WINDOW",
            self.cerrar_historial
        )

        marco_historial = ttk.Frame(
            self.ventana_historial,
            padding=15
        )

        marco_historial.pack(
            fill=tk.BOTH,
            expand=True
        )

        marco_historial.columnconfigure(
            0,
            weight=1
        )

        marco_historial.rowconfigure(
            3,
            weight=1
        )

        ttk.Label(
            marco_historial,
            text="Historial de commits",
            style="Titulo.TLabel"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ttk.Label(
            marco_historial,
            text=(
                "Vista de solo lectura del historial local. "
                "Puedes filtrar por archivo y por un rango de fechas. "
                "No ejecuta Checkout, Reset, Revert, Pull ni Push."
            ),
            style="AyudaVisible.TLabel",
            wraplength=1050
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 10)
        )

        # ---------------------------------------------------------
        # Filtros del historial
        # ---------------------------------------------------------

        marco_filtros = ttk.LabelFrame(
            marco_historial,
            text="Filtros",
            padding=10
        )

        marco_filtros.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        marco_filtros.columnconfigure(
            1,
            weight=1
        )

        self.variable_filtro_archivo_historial = tk.StringVar()
        self.variable_fecha_desde_historial = tk.StringVar()
        self.variable_fecha_hasta_historial = tk.StringVar()

        ttk.Label(
            marco_filtros,
            text="Archivo contiene:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 6)
        )

        self.entrada_filtro_archivo_historial = ttk.Entry(
            marco_filtros,
            textvariable=self.variable_filtro_archivo_historial,
            width=34
        )

        self.entrada_filtro_archivo_historial.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 16)
        )

        ttk.Label(
            marco_filtros,
            text="Desde:"
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 6)
        )

        self.entrada_fecha_desde_historial = ttk.Entry(
            marco_filtros,
            textvariable=self.variable_fecha_desde_historial,
            width=12
        )

        self.entrada_fecha_desde_historial.grid(
            row=0,
            column=3,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_filtros,
            text="dd/mm/aaaa"
        ).grid(
            row=0,
            column=4,
            sticky="w",
            padx=(0, 16)
        )

        ttk.Label(
            marco_filtros,
            text="Hasta:"
        ).grid(
            row=0,
            column=5,
            sticky="w",
            padx=(0, 6)
        )

        self.entrada_fecha_hasta_historial = ttk.Entry(
            marco_filtros,
            textvariable=self.variable_fecha_hasta_historial,
            width=12
        )

        self.entrada_fecha_hasta_historial.grid(
            row=0,
            column=6,
            sticky="w",
            padx=(0, 5)
        )

        ttk.Label(
            marco_filtros,
            text="dd/mm/aaaa"
        ).grid(
            row=0,
            column=7,
            sticky="w",
            padx=(0, 16)
        )

        self.boton_aplicar_filtros_historial = ttk.Button(
            marco_filtros,
            text="Aplicar filtros",
            command=self.cargar_historial,
            style="Accion.TButton"
        )

        self.boton_aplicar_filtros_historial.grid(
            row=0,
            column=8,
            sticky="e"
        )

        self.boton_limpiar_filtros_historial = ttk.Button(
            marco_filtros,
            text="Limpiar",
            command=self.limpiar_filtros_historial,
            style="Accion.TButton"
        )

        self.boton_limpiar_filtros_historial.grid(
            row=0,
            column=9,
            sticky="e",
            padx=(8, 0)
        )

        # Presionar Enter en cualquiera de los filtros aplica la consulta.
        for entrada in (
            self.entrada_filtro_archivo_historial,
            self.entrada_fecha_desde_historial,
            self.entrada_fecha_hasta_historial
        ):
            entrada.bind(
                "<Return>",
                lambda _evento: self.cargar_historial()
            )

        self.ayuda_filtro_archivo_historial = AyudaEmergente(
            self.entrada_filtro_archivo_historial,
            TEXTOS_AYUDA_GIT_V1["historial_filtro_archivo"]
        )

        self.ayuda_fecha_desde_historial = AyudaEmergente(
            self.entrada_fecha_desde_historial,
            TEXTOS_AYUDA_GIT_V1["historial_fecha_desde"]
        )

        self.ayuda_fecha_hasta_historial = AyudaEmergente(
            self.entrada_fecha_hasta_historial,
            TEXTOS_AYUDA_GIT_V1["historial_fecha_hasta"]
        )

        self.ayuda_aplicar_filtros_historial = AyudaEmergente(
            self.boton_aplicar_filtros_historial,
            TEXTOS_AYUDA_GIT_V1["historial_aplicar_filtros"]
        )

        self.ayuda_limpiar_filtros_historial = AyudaEmergente(
            self.boton_limpiar_filtros_historial,
            TEXTOS_AYUDA_GIT_V1["historial_limpiar_filtros"]
        )

        # ---------------------------------------------------------
        # Tabla del historial
        # ---------------------------------------------------------

        marco_tabla_historial = ttk.Frame(
            marco_historial
        )

        marco_tabla_historial.grid(
            row=3,
            column=0,
            sticky="nsew"
        )

        marco_tabla_historial.columnconfigure(
            0,
            weight=1
        )

        marco_tabla_historial.rowconfigure(
            0,
            weight=1
        )

        columnas = (
            "hash",
            "fecha",
            "autor",
            "mensaje"
        )

        self.tabla_historial = ttk.Treeview(
            marco_tabla_historial,
            columns=columnas,
            show="headings",
            selectmode="browse"
        )

        self.tabla_historial.heading(
            "hash",
            text="Hash"
        )

        self.tabla_historial.heading(
            "fecha",
            text="Fecha ↓"
        )

        self.tabla_historial.heading(
            "autor",
            text="Autor"
        )

        self.tabla_historial.heading(
            "mensaje",
            text="Mensaje"
        )

        self.tabla_historial.column(
            "hash",
            width=100,
            minwidth=85,
            stretch=False
        )

        self.tabla_historial.column(
            "fecha",
            width=155,
            minwidth=140,
            stretch=False
        )

        self.tabla_historial.column(
            "autor",
            width=190,
            minwidth=140
        )

        self.tabla_historial.column(
            "mensaje",
            width=540,
            minwidth=250
        )

        self.tabla_historial.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        barra_vertical = ttk.Scrollbar(
            marco_tabla_historial,
            orient=tk.VERTICAL,
            command=self.tabla_historial.yview
        )

        barra_vertical.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        barra_horizontal = ttk.Scrollbar(
            marco_tabla_historial,
            orient=tk.HORIZONTAL,
            command=self.tabla_historial.xview
        )

        barra_horizontal.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        self.tabla_historial.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set
        )

        self.tabla_historial.bind(
            "<<TreeviewSelect>>",
            self.actualizar_estado_boton_ver_cambios
        )

        self.tabla_historial.bind(
            "<Double-1>",
            self.abrir_detalle_commit_seleccionado
        )

        marco_inferior = ttk.Frame(
            marco_historial
        )

        marco_inferior.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        marco_inferior.columnconfigure(
            0,
            weight=1
        )

        self.variable_estado_historial = tk.StringVar(
            value="Listo para consultar el historial."
        )

        ttk.Label(
            marco_inferior,
            textvariable=self.variable_estado_historial
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.boton_ver_cambios_historial = ttk.Button(
            marco_inferior,
            text="Ver cambios...",
            command=self.abrir_detalle_commit_seleccionado,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_ver_cambios_historial.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(10, 0)
        )

        self.boton_exportar_csv_historial = ttk.Button(
            marco_inferior,
            text="Exportar CSV",
            command=self.exportar_historial_csv,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_exportar_csv_historial.grid(
            row=0,
            column=2,
            sticky="e",
            padx=(8, 0)
        )

        self.boton_exportar_txt_historial = ttk.Button(
            marco_inferior,
            text="Exportar TXT",
            command=self.exportar_historial_txt,
            state=tk.DISABLED,
            style="Accion.TButton"
        )

        self.boton_exportar_txt_historial.grid(
            row=0,
            column=3,
            sticky="e",
            padx=(8, 0)
        )

        self.boton_actualizar_historial = ttk.Button(
            marco_inferior,
            text="Actualizar historial",
            command=self.cargar_historial,
            style="Accion.TButton"
        )

        self.boton_actualizar_historial.grid(
            row=0,
            column=4,
            sticky="e",
            padx=(8, 0)
        )

        self.ayuda_ver_cambios_historial = AyudaEmergente(
            self.boton_ver_cambios_historial,
            TEXTOS_AYUDA_GIT_V1["historial_ver_cambios"]
        )

        self.ayuda_exportar_csv_historial = AyudaEmergente(
            self.boton_exportar_csv_historial,
            TEXTOS_AYUDA_GIT_V1["exportar_historial_csv"]
        )

        self.ayuda_exportar_txt_historial = AyudaEmergente(
            self.boton_exportar_txt_historial,
            TEXTOS_AYUDA_GIT_V1["exportar_historial_txt"]
        )

        self.ayuda_actualizar_historial = AyudaEmergente(
            self.boton_actualizar_historial,
            TEXTOS_AYUDA_GIT_V1["actualizar_historial"]
        )

        self.entrada_filtro_archivo_historial.focus_set()

    def cargar_historial(self):
        """
        Consulta y muestra hasta 100 commits aplicando los filtros visibles.
        """

        if not self.ruta_repositorio:
            return

        if self.tabla_historial is None:
            return

        filtro_archivo = ""
        texto_desde = ""
        texto_hasta = ""

        if self.variable_filtro_archivo_historial is not None:
            filtro_archivo = (
                self.variable_filtro_archivo_historial.get().strip()
            )

        if self.variable_fecha_desde_historial is not None:
            texto_desde = (
                self.variable_fecha_desde_historial.get().strip()
            )

        if self.variable_fecha_hasta_historial is not None:
            texto_hasta = (
                self.variable_fecha_hasta_historial.get().strip()
            )

        fecha_desde = self._convertir_fecha_filtro_historial(
            texto_desde,
            "Desde"
        )

        if fecha_desde is None:
            return

        fecha_hasta = self._convertir_fecha_filtro_historial(
            texto_hasta,
            "Hasta"
        )

        if fecha_hasta is None:
            return

        if (
            fecha_desde
            and fecha_hasta
            and fecha_desde > fecha_hasta
        ):
            if self.variable_estado_historial is not None:
                self.variable_estado_historial.set(
                    "El rango de fechas no es válido."
                )

            messagebox.showwarning(
                "Rango de fechas no válido",
                (
                    "La fecha Desde no puede ser posterior "
                    "a la fecha Hasta."
                ),
                parent=self.ventana_historial
            )

            return

        for elemento in self.tabla_historial.get_children():
            self.tabla_historial.delete(
                elemento
            )

        self.commits_historial_actual = []
        self.actualizar_estado_botones_exportacion_historial()

        # Al recargar, las filas anteriores dejan de existir:
        # se libera la relación fila -> commit y se deshabilita
        # el botón Ver cambios... hasta que haya una selección.
        self.commits_historial_por_elemento.clear()
        self.actualizar_estado_boton_ver_cambios()

        if self.variable_estado_historial is not None:
            self.variable_estado_historial.set(
                "Consultando historial local..."
            )

        resultado = self.servicio_historial.obtener_historial_commits(
            self.ruta_repositorio,
            limite=100,
            filtro_archivo=filtro_archivo,
            fecha_desde=(
                fecha_desde.isoformat()
                if fecha_desde
                else ""
            ),
            fecha_hasta=(
                fecha_hasta.isoformat()
                if fecha_hasta
                else ""
            )
        )

        if not resultado.exitoso:
            if self.variable_estado_historial is not None:
                self.variable_estado_historial.set(
                    "No fue posible consultar el historial."
                )

            messagebox.showerror(
                "Error al consultar historial",
                resultado.error,
                parent=self.ventana_historial
            )

            return

        self.commits_historial_actual = list(
            resultado.commits
        )

        self.filtros_historial_aplicados = {
            "archivo": filtro_archivo,
            "desde": texto_desde,
            "hasta": texto_hasta
        }

        self.actualizar_estado_botones_exportacion_historial()

        for commit in resultado.commits:
            identificador = self.tabla_historial.insert(
                "",
                tk.END,
                values=(
                    commit.hash_corto,
                    self._formatear_fecha_historial(
                        commit.fecha_iso
                    ),
                    commit.autor,
                    commit.mensaje
                )
            )

            # Relaciona la fila visible con el CommitGit para que
            # la ventana de detalle no tenga que volver a consultar
            # el historial.
            self.commits_historial_por_elemento[
                identificador
            ] = commit

        cantidad = len(
            resultado.commits
        )

        hay_filtros = bool(
            filtro_archivo
            or fecha_desde
            or fecha_hasta
        )

        if self.variable_estado_historial is not None:
            if cantidad == 0:
                if hay_filtros:
                    self.variable_estado_historial.set(
                        "No se encontraron commits que cumplan los filtros."
                    )
                else:
                    self.variable_estado_historial.set(
                        "El repositorio todavía no tiene commits."
                    )

            elif cantidad == 1:
                if hay_filtros:
                    self.variable_estado_historial.set(
                        "Se muestra 1 commit que cumple los filtros."
                    )
                else:
                    self.variable_estado_historial.set(
                        "Se muestra 1 commit."
                    )

            else:
                if hay_filtros:
                    self.variable_estado_historial.set(
                        f"Se muestran {cantidad} commits que cumplen los filtros."
                    )
                else:
                    self.variable_estado_historial.set(
                        f"Se muestran {cantidad} commits, del más reciente al más antiguo."
                    )

    def limpiar_filtros_historial(self):
        """
        Vacía todos los filtros y vuelve a cargar el historial.
        """

        if self.variable_filtro_archivo_historial is not None:
            self.variable_filtro_archivo_historial.set("")

        if self.variable_fecha_desde_historial is not None:
            self.variable_fecha_desde_historial.set("")

        if self.variable_fecha_hasta_historial is not None:
            self.variable_fecha_hasta_historial.set("")

        self.cargar_historial()

        if hasattr(
            self,
            "entrada_filtro_archivo_historial"
        ):
            self.entrada_filtro_archivo_historial.focus_set()

    def actualizar_estado_botones_exportacion_historial(self):
        """
        Habilita exportar solamente cuando existen commits visibles.
        """

        estado = (
            tk.NORMAL
            if self.commits_historial_actual
            else tk.DISABLED
        )

        if self.boton_exportar_csv_historial is not None:
            try:
                self.boton_exportar_csv_historial.config(
                    state=estado
                )
            except tk.TclError:
                pass

        if self.boton_exportar_txt_historial is not None:
            try:
                self.boton_exportar_txt_historial.config(
                    state=estado
                )
            except tk.TclError:
                pass

    def exportar_historial_csv(self):
        """
        Guarda exactamente los commits visibles en un archivo CSV.
        """

        if not self.commits_historial_actual:
            messagebox.showinfo(
                "Nada para exportar",
                "No hay commits visibles para exportar.",
                parent=self.ventana_historial
            )
            return

        ruta_destino = filedialog.asksaveasfilename(
            parent=self.ventana_historial,
            title="Guardar historial como CSV",
            defaultextension=".csv",
            filetypes=(
                ("Archivo CSV", "*.csv"),
                ("Todos los archivos", "*.*")
            ),
            initialfile=self._crear_nombre_archivo_historial(
                "csv"
            )
        )

        if not ruta_destino:
            return

        resultado = self.servicio_exportacion_historial.exportar_csv(
            ruta_destino,
            self.commits_historial_actual
        )

        self._procesar_resultado_exportacion_historial(
            resultado,
            "CSV"
        )

    def exportar_historial_txt(self):
        """
        Guarda exactamente los commits visibles en un archivo TXT.
        """

        if not self.commits_historial_actual:
            messagebox.showinfo(
                "Nada para exportar",
                "No hay commits visibles para exportar.",
                parent=self.ventana_historial
            )
            return

        ruta_destino = filedialog.asksaveasfilename(
            parent=self.ventana_historial,
            title="Guardar historial como TXT",
            defaultextension=".txt",
            filetypes=(
                ("Archivo de texto", "*.txt"),
                ("Todos los archivos", "*.*")
            ),
            initialfile=self._crear_nombre_archivo_historial(
                "txt"
            )
        )

        if not ruta_destino:
            return

        resultado = self.servicio_exportacion_historial.exportar_txt(
            ruta_destino,
            self.commits_historial_actual,
            ruta_repositorio=self.ruta_repositorio,
            filtro_archivo=self.filtros_historial_aplicados.get(
                "archivo",
                ""
            ),
            fecha_desde=self.filtros_historial_aplicados.get(
                "desde",
                ""
            ),
            fecha_hasta=self.filtros_historial_aplicados.get(
                "hasta",
                ""
            )
        )

        self._procesar_resultado_exportacion_historial(
            resultado,
            "TXT"
        )

    def _procesar_resultado_exportacion_historial(
        self,
        resultado,
        formato
    ):
        """
        Muestra el resultado de una exportación sin modificar Git.
        """

        if not resultado.exitoso:
            if self.variable_estado_historial is not None:
                self.variable_estado_historial.set(
                    f"No fue posible exportar el historial a {formato}."
                )

            messagebox.showerror(
                "Error al exportar historial",
                resultado.error,
                parent=self.ventana_historial
            )
            return

        if self.variable_estado_historial is not None:
            self.variable_estado_historial.set(
                f"Historial exportado correctamente a {formato}."
            )

        messagebox.showinfo(
            "Historial exportado",
            (
                f"El historial visible se exportó correctamente a {formato}.\n\n"
                f"Archivo:\n{resultado.ruta_archivo}"
            ),
            parent=self.ventana_historial
        )

    def _crear_nombre_archivo_historial(self, extension):
        """
        Crea un nombre sugerido seguro para Windows.
        """

        nombre_repositorio = (
            Path(self.ruta_repositorio).name
            if self.ruta_repositorio
            else "repositorio"
        )

        for caracter in '<>:"/\\|?*':
            nombre_repositorio = nombre_repositorio.replace(
                caracter,
                "_"
            )

        momento = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        return (
            f"historial_{nombre_repositorio}_{momento}.{extension}"
        )

    @staticmethod
    def _convertir_fecha_filtro_historial(
        texto_fecha,
        nombre_campo
    ):
        """
        Convierte dd/mm/aaaa a date para validar los filtros visuales.

        Devuelve una cadena vacía cuando el campo está vacío y None
        cuando el usuario escribió una fecha inválida.
        """

        texto_fecha = texto_fecha.strip()

        if not texto_fecha:
            return ""

        try:
            return datetime.strptime(
                texto_fecha,
                "%d/%m/%Y"
            ).date()

        except ValueError:
            messagebox.showwarning(
                "Fecha no válida",
                (
                    f"La fecha {nombre_campo} no es válida.\n\n"
                    "Utilice el formato dd/mm/aaaa.\n"
                    "Ejemplo: 18/08/2026"
                )
            )

            return None

    def actualizar_historial_si_abierto(self):
        """
        Refresca el historial únicamente si su ventana está abierta.
        """

        if self.ventana_historial is None:
            return

        try:
            existe = self.ventana_historial.winfo_exists()
        except tk.TclError:
            existe = False

        if not existe:
            return

        self.cargar_historial()

    def cerrar_historial(self):
        """
        Cierra y libera los controles asociados al historial.
        """

        if self.ventana_historial is not None:
            try:
                if self.ventana_historial.winfo_exists():
                    self.ventana_historial.destroy()
            except tk.TclError:
                pass

        self.ventana_historial = None
        self.tabla_historial = None
        self.variable_estado_historial = None
        self.variable_filtro_archivo_historial = None
        self.variable_fecha_desde_historial = None
        self.variable_fecha_hasta_historial = None
        self.boton_exportar_csv_historial = None
        self.boton_exportar_txt_historial = None
        self.boton_ver_cambios_historial = None
        self.commits_historial_actual = []
        self.commits_historial_por_elemento = {}
        self.filtros_historial_aplicados = {
            "archivo": "",
            "desde": "",
            "hasta": ""
        }

        # Si el historial se cierra, el detalle pierde su origen
        # visible y también se cierra.
        self.cerrar_detalle_commit()

    @staticmethod
    def _formatear_fecha_historial(fecha_iso):
        """
        Convierte la fecha ISO de Git a un formato compacto para la GUI.
        """

        if not fecha_iso:
            return "-"

        try:
            fecha = datetime.fromisoformat(
                fecha_iso
            )

            return fecha.strftime(
                "%d/%m/%Y %H:%M"
            )

        except ValueError:
            return fecha_iso

    # =============================================================
    # DETALLE DE CAMBIOS DE UN COMMIT
    # =============================================================

    def actualizar_estado_boton_ver_cambios(self, _evento=None):
        """
        Habilita Ver cambios... únicamente cuando existe un
        commit seleccionado en la tabla del historial.
        """

        hay_seleccion = False

        if self.tabla_historial is not None:
            try:
                hay_seleccion = bool(
                    self.tabla_historial.selection()
                )
            except tk.TclError:
                hay_seleccion = False

        estado = (
            tk.NORMAL
            if hay_seleccion
            else tk.DISABLED
        )

        if self.boton_ver_cambios_historial is not None:
            try:
                self.boton_ver_cambios_historial.config(
                    state=estado
                )
            except tk.TclError:
                pass

    def abrir_detalle_commit_seleccionado(self, _evento=None):
        """
        Abre los cambios del commit seleccionado en el historial.

        Utiliza la relación fila -> CommitGit almacenada al cargar
        la tabla y no vuelve a consultar el historial.
        """

        if self.tabla_historial is None:
            return

        try:
            seleccion = self.tabla_historial.selection()
        except tk.TclError:
            seleccion = ()

        if not seleccion:
            return

        commit = self.commits_historial_por_elemento.get(
            seleccion[0]
        )

        if commit is None:
            return

        self.abrir_detalle_commit(commit)

    def abrir_detalle_commit(self, commit):
        """
        Abre la ventana única con los cambios del commit.

        Si ya existe una ventana de detalle abierta, se destruye
        y se recrea con el commit solicitado.
        """

        self.cerrar_detalle_commit()

        self.crear_ventana_detalle_commit(commit)

    def crear_ventana_detalle_commit(self, commit):
        """
        Construye la ventana de solo lectura con el parche del commit.
        """

        self.ventana_detalle_commit = tk.Toplevel(
            self.ventana_principal
        )

        self.ventana_detalle_commit.title(
            "Cambios del commit - Gestor Git"
        )

        self.ventana_detalle_commit.geometry(
            "1100x700"
        )

        self.ventana_detalle_commit.minsize(
            850,
            500
        )

        self.ventana_detalle_commit.transient(
            self.ventana_principal
        )

        self.ventana_detalle_commit.protocol(
            "WM_DELETE_WINDOW",
            self.cerrar_detalle_commit
        )

        marco_detalle = ttk.Frame(
            self.ventana_detalle_commit,
            padding=15
        )

        marco_detalle.pack(
            fill=tk.BOTH,
            expand=True
        )

        marco_detalle.columnconfigure(
            0,
            weight=1
        )

        marco_detalle.rowconfigure(
            3,
            weight=1
        )

        ttk.Label(
            marco_detalle,
            text="Cambios del commit",
            style="Titulo.TLabel"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        advertencia = tk.Label(
            marco_detalle,
            text=(
                "Vista de solo lectura.\n"
                "Esta pantalla no modifica archivos, commits ni ramas."
            ),
            justify=tk.LEFT,
            anchor="w",
            background="#FEF2E0",
            foreground="#7C3A00",
            padx=10,
            pady=7,
            wraplength=1040
        )

        advertencia.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(10, 8)
        )

        marco_datos = ttk.Frame(
            marco_detalle
        )

        marco_datos.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        marco_datos.columnconfigure(
            1,
            weight=1
        )

        self._agregar_fila_dato(
            marco_datos,
            "Hash:",
            commit.hash_completo,
            0
        )

        self._agregar_fila_dato(
            marco_datos,
            "Fecha:",
            self._formatear_fecha_historial(
                commit.fecha_iso
            ),
            1
        )

        self._agregar_fila_dato(
            marco_datos,
            "Autor:",
            commit.autor,
            2
        )

        self._agregar_fila_dato(
            marco_datos,
            "Correo:",
            commit.correo,
            3
        )

        self._agregar_fila_dato(
            marco_datos,
            "Mensaje:",
            commit.mensaje,
            4
        )

        marco_diff = ttk.Frame(
            marco_detalle
        )

        marco_diff.grid(
            row=3,
            column=0,
            sticky="nsew"
        )

        marco_diff.columnconfigure(
            0,
            weight=1
        )

        marco_diff.rowconfigure(
            1,
            weight=1
        )

        ttk.Label(
            marco_diff,
            text="Cambios realizados",
            font=("Segoe UI", 10, "bold")
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 6)
        )

        self.texto_detalle_commit = tk.Text(
            marco_diff,
            wrap=tk.NONE,
            font=("Consolas", 10),
            relief=tk.SOLID,
            borderwidth=1,
            background="#FBFCFE",
            foreground="#1F2937"
        )

        self.texto_detalle_commit.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        barra_vertical_diff = ttk.Scrollbar(
            marco_diff,
            orient=tk.VERTICAL,
            command=self.texto_detalle_commit.yview
        )

        barra_vertical_diff.grid(
            row=1,
            column=1,
            sticky="ns"
        )

        barra_horizontal_diff = ttk.Scrollbar(
            marco_diff,
            orient=tk.HORIZONTAL,
            command=self.texto_detalle_commit.xview
        )

        barra_horizontal_diff.grid(
            row=2,
            column=0,
            sticky="ew"
        )

        self.texto_detalle_commit.configure(
            yscrollcommand=barra_vertical_diff.set,
            xscrollcommand=barra_horizontal_diff.set
        )

        self.texto_detalle_commit.tag_configure(
            "agregado",
            foreground="#1A7F37"
        )

        self.texto_detalle_commit.tag_configure(
            "eliminado",
            foreground="#CF222E"
        )

        self.texto_detalle_commit.tag_configure(
            "bloque",
            foreground="#0969DA",
            font=("Consolas", 10, "bold")
        )

        self.texto_detalle_commit.tag_configure(
            "tecnico",
            foreground="#57606A"
        )

        resultado = self.servicio_historial.obtener_cambios_commit(
            self.ruta_repositorio,
            commit.hash_completo
        )

        if not resultado.exitoso:
            self.texto_detalle_commit.insert(
                tk.END,
                (
                    "No fue posible obtener los cambios del commit.\n\n"
                    f"{resultado.error}"
                )
            )

        elif not resultado.salida:
            self.texto_detalle_commit.insert(
                tk.END,
                "Este commit no contiene cambios de archivos visibles."
            )

        else:
            self._mostrar_diff_en_texto(
                resultado.salida
            )

        self.texto_detalle_commit.config(
            state=tk.DISABLED
        )

        marco_botones_detalle = ttk.Frame(
            marco_detalle
        )

        marco_botones_detalle.grid(
            row=4,
            column=0,
            sticky="e",
            pady=(10, 0)
        )

        self.boton_copiar_diff_commit = ttk.Button(
            marco_botones_detalle,
            text="Copiar diff",
            command=self.copiar_diff_commit,
            style="Accion.TButton"
        )

        self.boton_copiar_diff_commit.grid(
            row=0,
            column=0,
            sticky="e",
            padx=(0, 8)
        )

        AyudaEmergente(
            self.boton_copiar_diff_commit,
            TEXTOS_AYUDA_GIT_V1["copiar_diff_commit"]
        )

        ttk.Button(
            marco_botones_detalle,
            text="Cerrar",
            command=self.cerrar_detalle_commit,
            style="Accion.TButton"
        ).grid(
            row=0,
            column=1,
            sticky="e"
        )

    def _agregar_fila_dato(self, marco, nombre, valor, fila):
        """
        Agrega una fila nombre/valor en la ventana de detalle.
        """

        ttk.Label(
            marco,
            text=nombre,
            font=("Segoe UI", 9, "bold")
        ).grid(
            row=fila,
            column=0,
            sticky="nw",
            padx=(0, 8)
        )

        ttk.Label(
            marco,
            text=valor if valor else "-",
            wraplength=950
        ).grid(
            row=fila,
            column=1,
            sticky="w"
        )

    def _mostrar_diff_en_texto(self, salida):
        """
        Inserta el diff en el widget de texto con colores simples.

        La visualización se limita a
        self.limite_caracteres_detalle caracteres; la truncación
        es solamente visual y no modifica el repositorio.
        """

        texto = salida

        if len(texto) > self.limite_caracteres_detalle:
            texto = texto[:self.limite_caracteres_detalle]

        self.texto_detalle_commit.insert(
            tk.END,
            texto
        )

        lineas = texto.split("\n")

        # Posición inicial de cada línea dentro del texto insertado.
        posiciones = []
        posicion = 0

        for linea in lineas:
            posiciones.append(posicion)
            posicion += len(linea) + 1

        for numero, linea in enumerate(lineas, start=1):
            tag = self._tag_para_linea_diff(
                linea
            )

            if tag is None:
                continue

            inicio = posiciones[numero - 1]

            self.texto_detalle_commit.tag_add(
                tag,
                f"1.0+{inicio}c",
                f"1.0+{inicio + len(linea)}c"
            )

        if len(salida) > self.limite_caracteres_detalle:
            self.texto_detalle_commit.insert(
                tk.END,
                (
                    "\n\n[Vista truncada: el commit contiene más "
                    "cambios de los que se muestran en esta pantalla.]\n"
                )
            )

    @staticmethod
    def _tag_para_linea_diff(linea):
        """
        Devuelve el tag visual de una línea del diff o None.
        """

        if (
            linea.startswith("diff --git")
            or linea.startswith("---")
            or linea.startswith("+++")
        ):
            return "tecnico"

        if linea.startswith("@@"):
            return "bloque"

        if linea.startswith("+"):
            return "agregado"

        if linea.startswith("-"):
            return "eliminado"

        return None

    def copiar_diff_commit(self):
        """
        Copia el diff visible de la ventana al portapapeles.
        """

        if self.texto_detalle_commit is None:
            return

        try:
            # Solamente se copia el área del diff, no los metadatos
            # del commit mostrados arriba.
            contenido = self.texto_detalle_commit.get(
                "1.0",
                tk.END
            )

            self.ventana_detalle_commit.clipboard_clear()
            self.ventana_detalle_commit.clipboard_append(
                contenido.rstrip("\n")
            )
        except tk.TclError:
            pass

    def cerrar_detalle_commit(self):
        """
        Cierra la ventana de detalle si está abierta.
        """

        if self.ventana_detalle_commit is not None:
            try:
                if self.ventana_detalle_commit.winfo_exists():
                    self.ventana_detalle_commit.destroy()
            except tk.TclError:
                pass

        self.ventana_detalle_commit = None
        self.texto_detalle_commit = None

    # =============================================================
    # INSPECTOR DE CAMBIOS LOCALES
    # =============================================================

    def abrir_cambios_locales(self):
        """
        Abre (o recrea) la ventana única del inspector de cambios
        locales con el archivo seleccionado.

        Solamente funciona con exactamente un archivo seleccionado.
        """

        if not self.ruta_repositorio:
            return

        seleccion = self.tabla_cambios.selection()

        if len(seleccion) != 1:
            return

        identificador = seleccion[0]

        cambio = self.cambios_por_elemento.get(
            identificador
        )

        if cambio is None:
            return

        self.cerrar_cambios_locales()

        self.ruta_archivo_inspector = cambio.ruta

        self.crear_ventana_cambios_locales()

    def crear_ventana_cambios_locales(self):
        """
        Construye la ventana de inspección de cambios locales.
        """

        self.ventana_cambios_locales = tk.Toplevel(
            self.ventana_principal
        )

        self.ventana_cambios_locales.title(
            "Cambios locales - Gestor Git"
        )

        self.ventana_cambios_locales.geometry(
            "1100x700"
        )

        self.ventana_cambios_locales.minsize(
            850,
            500
        )

        self.ventana_cambios_locales.transient(
            self.ventana_principal
        )

        self.ventana_cambios_locales.protocol(
            "WM_DELETE_WINDOW",
            self.cerrar_cambios_locales
        )

        marco_inspector = ttk.Frame(
            self.ventana_cambios_locales,
            padding=15
        )

        marco_inspector.pack(
            fill=tk.BOTH,
            expand=True
        )

        marco_inspector.columnconfigure(
            0,
            weight=1
        )

        marco_inspector.rowconfigure(
            3,
            weight=1
        )

        ttk.Label(
            marco_inspector,
            text="Cambios locales",
            style="Titulo.TLabel"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        advertencia = tk.Label(
            marco_inspector,
            text=(
                "Pantalla de inspección.\n"
                "La única acción que modifica el working tree es "
                "'Descartar cambios sin preparar...' desde la pestaña "
                "'Sin preparar'.\n"
                "El staging se conserva intacto y no se ejecuta "
                "Fetch, Pull ni Push."
            ),
            justify=tk.LEFT,
            anchor="w",
            background="#FEF2E0",
            foreground="#7C3A00",
            padx=10,
            pady=7,
            wraplength=1040
        )

        advertencia.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(10, 8)
        )

        marco_datos = ttk.Frame(
            marco_inspector
        )

        marco_datos.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        marco_datos.columnconfigure(
            1,
            weight=1
        )

        self._agregar_fila_dato(
            marco_datos,
            "Repositorio:",
            self.ruta_repositorio,
            0
        )

        self._agregar_fila_dato(
            marco_datos,
            "Archivo:",
            self.ruta_archivo_inspector,
            1
        )

        self.variable_estado_inspector = tk.StringVar(
            value="..."
        )

        self.variable_preparado_inspector = tk.StringVar(
            value="..."
        )

        self.variable_commit_inspector = tk.StringVar(
            value="..."
        )

        self._agregar_fila_dato_variable(
            marco_datos,
            "Estado:",
            self.variable_estado_inspector,
            2
        )

        self._agregar_fila_dato_variable(
            marco_datos,
            "Preparado:",
            self.variable_preparado_inspector,
            3
        )

        self._agregar_fila_dato_variable(
            marco_datos,
            "Último commit local:",
            self.variable_commit_inspector,
            4
        )

        self.notebook_cambios_locales = ttk.Notebook(
            marco_inspector
        )

        self.notebook_cambios_locales.grid(
            row=3,
            column=0,
            sticky="nsew"
        )

        self.marco_sin_preparar_locales = ttk.Frame(
            self.notebook_cambios_locales
        )

        self.marco_preparados_locales = ttk.Frame(
            self.notebook_cambios_locales
        )

        self.notebook_cambios_locales.add(
            self.marco_sin_preparar_locales,
            text="Sin preparar"
        )

        self.notebook_cambios_locales.add(
            self.marco_preparados_locales,
            text="Preparados"
        )

        # El botón de descarte solo se habilita en la pestaña
        # 'Sin preparar': al cambiar de pestaña se reevalúa.
        self.notebook_cambios_locales.bind(
            "<<NotebookTabChanged>>",
            self.actualizar_estado_boton_descartar
        )

        self.variable_resumen_sin_preparar = tk.StringVar(
            value=""
        )

        self.variable_resumen_preparados = tk.StringVar(
            value=""
        )

        self.texto_sin_preparar_locales = (
            self._construir_pestana_diff_locales(
                self.marco_sin_preparar_locales,
                self.variable_resumen_sin_preparar
            )
        )

        self.texto_preparados_locales = (
            self._construir_pestana_diff_locales(
                self.marco_preparados_locales,
                self.variable_resumen_preparados
            )
        )

        self.detalle_cambio_local_actual = None

        self.actualizar_cambios_locales()

        marco_botones_inspector = ttk.Frame(
            marco_inspector
        )

        marco_botones_inspector.grid(
            row=4,
            column=0,
            sticky="e",
            pady=(10, 0)
        )

        self.boton_descartar_sin_preparar = ttk.Button(
            marco_botones_inspector,
            text="Descartar cambios sin preparar...",
            command=self.descartar_cambios_sin_preparar,
            style="Accion.TButton",
            state=tk.DISABLED
        )

        self.boton_descartar_sin_preparar.grid(
            row=0,
            column=0,
            padx=(0, 18)
        )

        AyudaEmergente(
            self.boton_descartar_sin_preparar,
            TEXTOS_AYUDA_GIT_V1["descartar_sin_preparar"],
            ancho_texto=620
        )

        self.boton_actualizar_cambios_locales = ttk.Button(
            marco_botones_inspector,
            text="Actualizar",
            command=self.actualizar_cambios_locales,
            style="Accion.TButton"
        )

        self.boton_actualizar_cambios_locales.grid(
            row=0,
            column=1,
            padx=(0, 8)
        )

        AyudaEmergente(
            self.boton_actualizar_cambios_locales,
            TEXTOS_AYUDA_GIT_V1["actualizar_inspector"]
        )

        self.boton_copiar_diff_cambios_locales = ttk.Button(
            marco_botones_inspector,
            text="Copiar diff",
            command=self.copiar_diff_cambios_locales,
            style="Accion.TButton"
        )

        self.boton_copiar_diff_cambios_locales.grid(
            row=0,
            column=2,
            padx=(0, 8)
        )

        AyudaEmergente(
            self.boton_copiar_diff_cambios_locales,
            TEXTOS_AYUDA_GIT_V1["copiar_diff_inspector"]
        )

        ttk.Button(
            marco_botones_inspector,
            text="Cerrar",
            command=self.cerrar_cambios_locales,
            style="Accion.TButton"
        ).grid(
            row=0,
            column=3
        )

        # El botón se crea deshabilitado y se recalcula recién ahora:
        # actualizar_cambios_locales() se ejecutó antes de crearlo y
        # su llamada a actualizar_estado_boton_descartar() entonces
        # no tenía efecto. Sin esta llamada, al abrir por primera
        # vez el Inspector el botón podría quedar habilitado sin
        # importar si el archivo es descartable.
        self.actualizar_estado_boton_descartar()

    def _construir_pestana_diff_locales(
        self,
        marco,
        variable_resumen
    ):
        """
        Construye una pestaña con su resumen y su visor de diff.
        """

        marco.columnconfigure(
            0,
            weight=1
        )

        marco.rowconfigure(
            1,
            weight=1
        )

        ttk.Label(
            marco,
            textvariable=variable_resumen
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(6, 6)
        )

        texto = tk.Text(
            marco,
            wrap=tk.NONE,
            font=("Consolas", 10),
            relief=tk.SOLID,
            borderwidth=1,
            background="#FBFCFE",
            foreground="#1F2937"
        )

        texto.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        barra_vertical = ttk.Scrollbar(
            marco,
            orient=tk.VERTICAL,
            command=texto.yview
        )

        barra_vertical.grid(
            row=1,
            column=1,
            sticky="ns"
        )

        barra_horizontal = ttk.Scrollbar(
            marco,
            orient=tk.HORIZONTAL,
            command=texto.xview
        )

        barra_horizontal.grid(
            row=2,
            column=0,
            sticky="ew"
        )

        texto.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set
        )

        texto.tag_configure(
            "agregado",
            foreground="#1A7F37"
        )

        texto.tag_configure(
            "eliminado",
            foreground="#CF222E"
        )

        texto.tag_configure(
            "bloque",
            foreground="#0969DA",
            font=("Consolas", 10, "bold")
        )

        texto.tag_configure(
            "tecnico",
            foreground="#57606A"
        )

        return texto

    def _agregar_fila_dato_variable(
        self,
        marco,
        nombre,
        variable,
        fila
    ):
        """
        Agrega una fila nombre/valor dinámico en el inspector.
        """

        ttk.Label(
            marco,
            text=nombre,
            font=("Segoe UI", 9, "bold")
        ).grid(
            row=fila,
            column=0,
            sticky="nw",
            padx=(0, 8)
        )

        ttk.Label(
            marco,
            textvariable=variable,
            wraplength=950
        ).grid(
            row=fila,
            column=1,
            sticky="w"
        )

    def actualizar_cambios_locales(self):
        """
        Consulta nuevamente el estado LOCAL del archivo y
        actualiza las pestañas y los datos mostrados.

        No ejecuta Fetch ni ninguna operación remota y nunca
        modifica el repositorio.
        """

        if self.ventana_cambios_locales is None:
            return

        if not self.ruta_repositorio:
            return

        if not self.ruta_archivo_inspector:
            return

        resultado = self.servicio_cambios_locales.obtener_detalle(
            self.ruta_repositorio,
            self.ruta_archivo_inspector
        )

        if not resultado.exitoso:
            self.detalle_cambio_local_actual = None

            self.variable_estado_inspector.set(
                "No fue posible consultar los cambios."
            )

            self.variable_preparado_inspector.set("-")
            self.variable_commit_inspector.set("-")

            self.variable_resumen_sin_preparar.set("")
            self.variable_resumen_preparados.set("")

            self._limpiar_textos_inspector()

            self._insertar_mensaje_inspector(
                self.texto_sin_preparar_locales,
                (
                    "No fue posible consultar los cambios "
                    f"del archivo.\n\n{resultado.error}"
                )
            )

            self._insertar_mensaje_inspector(
                self.texto_preparados_locales,
                "No fue posible consultar los cambios del archivo."
            )

            self.actualizar_estado_boton_descartar()

            return

        if resultado.detalle is None:
            # El archivo ya no tiene cambios pendientes.
            self.detalle_cambio_local_actual = None

            self.variable_estado_inspector.set(
                "Sin cambios pendientes"
            )

            self.variable_preparado_inspector.set("-")
            self.variable_commit_inspector.set("-")

            self.variable_resumen_sin_preparar.set("")
            self.variable_resumen_preparados.set("")

            self._limpiar_textos_inspector()

            mensaje = (
                "El archivo ya no tiene cambios locales pendientes."
            )

            self._insertar_mensaje_inspector(
                self.texto_sin_preparar_locales,
                mensaje
            )

            self._insertar_mensaje_inspector(
                self.texto_preparados_locales,
                mensaje
            )

            self.actualizar_estado_boton_descartar()

            return

        detalle = resultado.detalle

        self.detalle_cambio_local_actual = detalle

        self.variable_estado_inspector.set(
            detalle.descripcion
        )

        if detalle.en_conflicto:
            # Un conflicto no es "preparado" ni "sin preparar".
            texto_preparado = "No aplica"
        elif not detalle.preparado:
            texto_preparado = "No"
        elif detalle.requiere_actualizar_preparado:
            texto_preparado = "Sí (hay cambios nuevos)"
        else:
            texto_preparado = "Sí"

        self.variable_preparado_inspector.set(
            texto_preparado
        )

        if detalle.hash_commit:
            texto_commit = (
                f"{detalle.hash_commit} {detalle.mensaje_commit}"
            ).strip()
        else:
            texto_commit = (
                "El repositorio todavía no tiene commits. "
                "Los cambios preparados se comparan contra un "
                "árbol vacío."
            )

        self.variable_commit_inspector.set(
            texto_commit
        )

        self._limpiar_textos_inspector()

        if detalle.nuevo_sin_preparar:
            self._insertar_mensaje_inspector(
                self.texto_sin_preparar_locales,
                (
                    "Este archivo es nuevo y todavía no está preparado.\n\n"
                    "Git aún no tiene una versión anterior para comparar "
                    "en el índice.\n\n"
                    "Después de prepararlo podrá verse su contenido en la "
                    "pestaña 'Preparados'."
                )
            )
        elif detalle.diff_sin_preparar:
            self._mostrar_diff_en_texto_inspector(
                self.texto_sin_preparar_locales,
                detalle.diff_sin_preparar
            )
        else:
            self._insertar_mensaje_inspector(
                self.texto_sin_preparar_locales,
                "No hay cambios sin preparar."
            )

        if detalle.diff_preparado:
            self._mostrar_diff_en_texto_inspector(
                self.texto_preparados_locales,
                detalle.diff_preparado
            )
        else:
            self._insertar_mensaje_inspector(
                self.texto_preparados_locales,
                "No hay cambios preparados."
            )

        self.variable_resumen_sin_preparar.set(
            self._crear_resumen_cambios_locales(
                detalle.binario_sin_preparar,
                detalle.inserciones_sin_preparar,
                detalle.eliminaciones_sin_preparar
            )
        )

        self.variable_resumen_preparados.set(
            self._crear_resumen_cambios_locales(
                detalle.binario_preparado,
                detalle.inserciones_preparadas,
                detalle.eliminaciones_preparadas
            )
        )

        self.actualizar_estado_boton_descartar()

    def _limpiar_textos_inspector(self):
        """
        Vacía ambos visores y los deja editables para rellenarlos.
        """

        for texto in (
            self.texto_sin_preparar_locales,
            self.texto_preparados_locales,
        ):
            if texto is None:
                continue

            texto.configure(
                state=tk.NORMAL
            )

            texto.delete(
                "1.0",
                tk.END
            )

    def _mostrar_diff_en_texto_inspector(
        self,
        texto,
        salida
    ):
        """
        Inserta el diff en el visor indicado con colores simples.

        La visualización se limita a
        self.limite_caracteres_detalle caracteres; la truncación
        es solamente visual y no modifica el repositorio.
        """

        if len(salida) > self.limite_caracteres_detalle:
            texto_exhibido = salida[
                :self.limite_caracteres_detalle
            ]
        else:
            texto_exhibido = salida

        texto.insert(
            tk.END,
            texto_exhibido
        )

        lineas = texto_exhibido.split("\n")

        # Posición inicial de cada línea dentro del texto insertado.
        posiciones = []
        posicion = 0

        for linea in lineas:
            posiciones.append(posicion)
            posicion += len(linea) + 1

        for numero, linea in enumerate(lineas, start=1):
            tag = self._tag_para_linea_diff(
                linea
            )

            if tag is None:
                continue

            inicio = posiciones[numero - 1]

            texto.tag_add(
                tag,
                f"1.0+{inicio}c",
                f"1.0+{inicio + len(linea)}c"
            )

        if len(salida) > self.limite_caracteres_detalle:
            texto.insert(
                tk.END,
                (
                    "\n\n[Vista truncada: el archivo contiene más "
                    "cambios de los que se muestran en esta pantalla.]\n"
                )
            )

        texto.configure(
            state=tk.DISABLED
        )

    def _insertar_mensaje_inspector(self, texto, mensaje):
        """
        Inserta un mensaje informativo y deja el visor
        en modo solo lectura.
        """

        texto.insert(
            tk.END,
            mensaje
        )

        texto.configure(
            state=tk.DISABLED
        )

    @staticmethod
    def _crear_resumen_cambios_locales(
        binario,
        inserciones,
        eliminaciones
    ):
        """
        Crea el resumen de una pestaña del inspector.

        Para archivos binarios devuelve "Archivo binario"
        sin intentar interpretar las cantidades.
        """

        if binario:
            return "Archivo binario"

        partes = []

        if inserciones == 1:
            partes.append("1 inserción")
        else:
            partes.append(f"{inserciones} inserciones")

        if eliminaciones == 1:
            partes.append("1 eliminación")
        else:
            partes.append(f"{eliminaciones} eliminaciones")

        return " · ".join(partes)

    def copiar_diff_cambios_locales(self):
        """
        Copia el contenido visible de la pestaña activa
        al portapapeles.
        """

        if self.ventana_cambios_locales is None:
            return

        if self.notebook_cambios_locales is None:
            return

        if (
            self.texto_sin_preparar_locales is None
            or self.texto_preparados_locales is None
        ):
            return

        pestana_activa = (
            self.notebook_cambios_locales.select()
        )

        if pestana_activa == str(
            self.marco_sin_preparar_locales
        ):
            texto_activo = self.texto_sin_preparar_locales
        else:
            texto_activo = self.texto_preparados_locales

        try:
            contenido = texto_activo.get(
                "1.0",
                tk.END
            )
        except tk.TclError:
            return

        self.ventana_cambios_locales.clipboard_clear()

        self.ventana_cambios_locales.clipboard_append(
            contenido.rstrip("\n")
        )

    def actualizar_estado_boton_descartar(self, _evento=None):
        """
        Habilita el botón de descarte únicamente cuando la pestaña
        activa es 'Sin preparar' y el archivo inspeccionado tiene
        cambios sin preparar reales (no es nuevo y no está en
        conflicto).
        """

        permitido = False

        if (
            self.boton_descartar_sin_preparar is not None
            and self.ventana_cambios_locales is not None
            and self.notebook_cambios_locales is not None
            and self.marco_sin_preparar_locales is not None
            and self.ruta_repositorio
            and not self.operacion_remota_en_curso
        ):
            pestana_activa = (
                self.notebook_cambios_locales.select()
            )

            detalle = self.detalle_cambio_local_actual

            if (
                pestana_activa == str(
                    self.marco_sin_preparar_locales
                )
                and detalle is not None
            ):
                permitido = (
                    not detalle.nuevo_sin_preparar
                    and not detalle.en_conflicto
                    and bool(detalle.diff_sin_preparar)
                )

        if self.boton_descartar_sin_preparar is not None:
            self.boton_descartar_sin_preparar.config(
                state=(
                    tk.NORMAL
                    if permitido
                    else tk.DISABLED
                )
            )

    def descartar_cambios_sin_preparar(self):
        """
        Descarta únicamente los cambios SIN PREPARAR del archivo
        inspeccionado.

        Primero consulta el estado LOCAL de nuevo (sin Fetch) para
        decidir si la operación sigue permitida; después muestra una
        confirmación fuerte y ejecuta el restore desde el índice.
        El staging se conserva intacto.

        Si hay una operación remota en curso (Fetch/Pull/Push),
        el descarte se bloquea antes de cualquier consulta o
        confirmación: la defensa en profundidad no depende de
        la modalidad de las ventanas.
        """

        if self.operacion_remota_en_curso:
            self.variable_estado.set(
                "Espere a que termine la operación remota en curso "
                "(Fetch/Pull/Push) antes de descartar cambios."
            )
            return

        if self.ventana_cambios_locales is None:
            return

        if not self.ruta_repositorio:
            return

        if not self.ruta_archivo_inspector:
            return

        self.actualizar_cambios_locales()

        if self.notebook_cambios_locales.select() != str(
            self.marco_sin_preparar_locales
        ):
            self.variable_estado.set(
                "La acción de descarte solamente está disponible "
                "desde la pestaña 'Sin preparar'."
            )
            return

        detalle = self.detalle_cambio_local_actual

        if detalle is None:
            self.variable_estado.set(
                "El archivo ya no tiene cambios sin preparar."
            )
            return

        if detalle.nuevo_sin_preparar:
            messagebox.showinfo(
                "No se puede descartar",
                (
                    "Este archivo es nuevo y todavía no está "
                    "bajo seguimiento.\n\n"
                    "GestorGit no lo eliminará automáticamente."
                ),
                parent=self.ventana_cambios_locales
            )
            return

        if detalle.en_conflicto:
            messagebox.showwarning(
                "Archivo en conflicto",
                (
                    "El archivo está en conflicto. GestorGit no "
                    "descartará cambios automáticamente mientras "
                    "exista un conflicto."
                ),
                parent=self.ventana_cambios_locales
            )
            return

        if not detalle.diff_sin_preparar:
            self.variable_estado.set(
                "El archivo ya no tiene cambios sin preparar."
            )
            return

        ruta_archivo = self.ruta_archivo_inspector

        if detalle.preparado:
            texto_restauracion = (
                "El archivo volverá a coincidir con la versión "
                "que está actualmente en el área preparada "
                "(staging).\n\n"
                "Si el archivo ya tiene cambios preparados, "
                "esos cambios SE CONSERVARÁN."
            )
        else:
            texto_restauracion = (
                "El archivo volverá a coincidir con la versión "
                "actualmente registrada en el índice/HEAD."
            )

        continuar = messagebox.askyesno(
            "Descartar cambios sin preparar",
            (
                "Se descartarán permanentemente los cambios "
                f"SIN PREPARAR de:\n\n{ruta_archivo}\n\n"
                f"{texto_restauracion}\n\n"
                "Esta acción no puede deshacerse desde GestorGit.\n\n"
                "¿Desea continuar?"
            ),
            icon="warning",
            parent=self.ventana_cambios_locales
        )

        if not continuar:
            return

        resultado = (
            self.servicio_descarte_cambios
            .descartar_cambios_sin_preparar(
                self.ruta_repositorio,
                ruta_archivo
            )
        )

        if not resultado.exitoso:
            messagebox.showerror(
                "No se pudo descartar",
                resultado.error,
                parent=self.ventana_cambios_locales
            )
            return

        self.cargar_cambios()

        self.actualizar_cambios_locales()

        if detalle.preparado:
            mensaje_exito = (
                "Se descartaron los cambios sin preparar.\n"
                "Los cambios preparados se conservaron."
            )
        else:
            mensaje_exito = (
                "Se descartaron los cambios sin preparar.\n"
                "El archivo volvió a la versión registrada "
                "en el índice/HEAD."
            )

        messagebox.showinfo(
            "Cambios descartados",
            mensaje_exito,
            parent=self.ventana_cambios_locales
        )

    def cerrar_cambios_locales(self):
        """
        Cierra la ventana del inspector si está abierta.
        """

        if self.ventana_cambios_locales is not None:
            try:
                if self.ventana_cambios_locales.winfo_exists():
                    self.ventana_cambios_locales.destroy()
            except tk.TclError:
                pass

        self.ventana_cambios_locales = None
        self.notebook_cambios_locales = None
        self.marco_sin_preparar_locales = None
        self.marco_preparados_locales = None
        self.texto_sin_preparar_locales = None
        self.texto_preparados_locales = None
        self.variable_resumen_sin_preparar = None
        self.variable_resumen_preparados = None
        self.variable_estado_inspector = None
        self.variable_preparado_inspector = None
        self.variable_commit_inspector = None
        self.detalle_cambio_local_actual = None
        self.ruta_archivo_inspector = ""
        self.boton_descartar_sin_preparar = None

    # =============================================================
    # FETCH
    # =============================================================

    def iniciar_fetch(self):
        """
        Inicia Fetch en un hilo secundario.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        resultado_remoto = (
            self.servicio_git.obtener_remoto_sincronizacion(
                self.ruta_repositorio
            )
        )

        if not resultado_remoto.exitoso:
            messagebox.showerror(
                "No se puede ejecutar Fetch",
                resultado_remoto.error
            )

            return

        remoto = resultado_remoto.salida

        ruta_repositorio = (
            self.ruta_repositorio
        )

        self.operacion_remota_en_curso = True

        self.actualizar_controles_operacion_remota()

        self.variable_estado.set(
            f"Consultando remoto '{remoto}' mediante Fetch..."
        )

        self.variable_ultima_consulta.set(
            "Fetch en curso..."
        )

        hilo_fetch = threading.Thread(
            target=self.trabajo_fetch,
            args=(
                ruta_repositorio,
                remoto
            ),
            daemon=True
        )

        hilo_fetch.start()

    def trabajo_fetch(
        self,
        ruta_repositorio,
        remoto
    ):
        """
        Trabajo de Fetch ejecutado fuera del hilo principal.

        Este método nunca modifica controles Tkinter.
        """

        resultado_fetch = (
            self.servicio_git.ejecutar_fetch(
                ruta_repositorio,
                remoto
            )
        )

        estado_sincronizacion = None

        if resultado_fetch.exitoso:
            estado_sincronizacion = (
                self.servicio_git.obtener_estado_sincronizacion(
                    ruta_repositorio
                )
            )

        self.cola_resultados.put(
            (
                "fetch",
                ruta_repositorio,
                remoto,
                resultado_fetch,
                estado_sincronizacion
            )
        )

    # =============================================================
    # PULL
    # =============================================================

    def iniciar_pull(self):
        """
        Prepara y confirma un Pull seguro.

        La operación real se ejecuta en un hilo secundario.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        if not self.fetch_exitoso_en_sesion:
            messagebox.showinfo(
                "Fetch requerido",
                (
                    "Ejecute Fetch antes de realizar Pull.\n\n"
                    "Además, el motor de Pull realizará otro Fetch "
                    "inmediatamente antes de descargar los commits."
                )
            )

            return

        # Consultamos nuevamente el área de trabajo.
        resultado_cambios = self.servicio_git.obtener_cambios(
            self.ruta_repositorio
        )

        if not resultado_cambios.exitoso:
            messagebox.showerror(
                "No se puede realizar Pull",
                resultado_cambios.error
            )

            return

        if resultado_cambios.cambios:
            self.cargar_cambios()

            messagebox.showwarning(
                "Cambios pendientes",
                (
                    "No se realizará Pull porque existen cambios "
                    "sin commit en el repositorio.\n\n"
                    "La aplicación exige un área de trabajo "
                    "completamente limpia."
                )
            )

            return

        estado = self.servicio_git.obtener_estado_sincronizacion(
            self.ruta_repositorio
        )

        self.aplicar_estado_sincronizacion(
            estado
        )

        if not estado.exitoso:
            messagebox.showerror(
                "No se puede realizar Pull",
                estado.error
            )

            return

        if not estado.upstream_configurado:
            messagebox.showwarning(
                "Upstream no configurado",
                (
                    "No se puede realizar Pull porque la rama "
                    "actual no tiene upstream configurado."
                )
            )

            return

        if estado.divergente:
            messagebox.showwarning(
                "Ramas divergentes",
                (
                    "No se realizará Pull porque la rama local "
                    "y la rama remota han divergido.\n\n"
                    f"Por enviar: {estado.commits_por_subir}\n"
                    f"Por descargar: {estado.commits_por_bajar}\n\n"
                    "La aplicación no realizará Merge ni Rebase "
                    "automáticamente."
                )
            )

            return

        if estado.commits_por_subir > 0:
            messagebox.showwarning(
                "Hay commits locales",
                (
                    "No se realizará Pull porque existen commits "
                    "locales pendientes de enviar.\n\n"
                    f"Por enviar: {estado.commits_por_subir}"
                )
            )

            return

        if estado.commits_por_bajar <= 0:
            messagebox.showinfo(
                "Nada para descargar",
                "No hay commits remotos pendientes de descargar."
            )

            return

        mensaje_confirmacion = (
            self._crear_mensaje_confirmacion_pull(
                estado
            )
        )

        confirmado = messagebox.askyesno(
            "Confirmar Pull",
            mensaje_confirmacion
        )

        if not confirmado:
            return

        ruta_repositorio = (
            self.ruta_repositorio
        )

        self.operacion_remota_en_curso = True

        self.actualizar_controles_operacion_remota()

        self.variable_estado.set(
            "Verificando el remoto y ejecutando Pull..."
        )

        self.variable_ultima_consulta.set(
            (
                "Pull en curso. Se ejecutará Fetch nuevamente "
                "antes de descargar."
            )
        )

        hilo_pull = threading.Thread(
            target=self.trabajo_pull,
            args=(
                ruta_repositorio,
            ),
            daemon=True
        )

        hilo_pull.start()

    def trabajo_pull(
        self,
        ruta_repositorio
    ):
        """
        Ejecuta Pull seguro fuera del hilo principal.

        Este método nunca modifica controles Tkinter.
        """

        resultado_pull = (
            self.servicio_git.ejecutar_pull_seguro(
                ruta_repositorio
            )
        )

        resultado_fetch_final = None
        estado_sincronizacion = None

        if resultado_pull.exitoso:
            resultado_remoto = (
                self.servicio_git.obtener_remoto_sincronizacion(
                    ruta_repositorio
                )
            )

            if resultado_remoto.exitoso:
                resultado_fetch_final = (
                    self.servicio_git.ejecutar_fetch(
                        ruta_repositorio,
                        resultado_remoto.salida
                    )
                )

                if resultado_fetch_final.exitoso:
                    estado_sincronizacion = (
                        self.servicio_git.obtener_estado_sincronizacion(
                            ruta_repositorio
                        )
                    )

        self.cola_resultados.put(
            (
                "pull",
                ruta_repositorio,
                resultado_pull,
                resultado_fetch_final,
                estado_sincronizacion
            )
        )

    # =============================================================
    # PUSH
    # =============================================================

    def iniciar_push(self):
        """
        Prepara y confirma un Push seguro.

        La ejecución real se realiza en un hilo secundario.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        if not self.fetch_exitoso_en_sesion:
            messagebox.showinfo(
                "Fetch requerido",
                (
                    "Ejecute Fetch antes de realizar Push.\n\n"
                    "Además, el motor de Push realizará otro Fetch "
                    "inmediatamente antes de enviar los commits."
                )
            )

            return

        resultado_cambios = self.servicio_git.obtener_cambios(
            self.ruta_repositorio
        )

        if not resultado_cambios.exitoso:
            messagebox.showerror(
                "No se puede realizar Push",
                resultado_cambios.error
            )

            return

        if resultado_cambios.cambios:
            self.cargar_cambios()

            messagebox.showwarning(
                "Cambios pendientes",
                (
                    "No se realizará Push porque existen cambios "
                    "sin commit en el repositorio.\n\n"
                    "Nuestra aplicación exige un área de trabajo "
                    "limpia antes de enviar."
                )
            )

            return

        estado = self.servicio_git.obtener_estado_sincronizacion(
            self.ruta_repositorio
        )

        self.aplicar_estado_sincronizacion(
            estado
        )

        if not estado.exitoso:
            messagebox.showerror(
                "No se puede realizar Push",
                estado.error
            )

            return

        if estado.divergente:
            messagebox.showwarning(
                "Ramas divergentes",
                (
                    "No se realizará Push porque la rama local "
                    "y la rama remota han divergido.\n\n"
                    f"Por enviar: {estado.commits_por_subir}\n"
                    f"Por descargar: {estado.commits_por_bajar}"
                )
            )

            return

        if estado.commits_por_bajar > 0:
            messagebox.showwarning(
                "Hay commits por descargar",
                (
                    "No se realizará Push porque existen commits "
                    "remotos que primero deben descargarse.\n\n"
                    f"Por descargar: {estado.commits_por_bajar}"
                )
            )

            return

        if estado.commits_por_subir <= 0:
            messagebox.showinfo(
                "Nada para enviar",
                "No hay commits locales pendientes de enviar."
            )

            return

        mensaje_confirmacion = (
            self._crear_mensaje_confirmacion_push(
                estado
            )
        )

        confirmado = messagebox.askyesno(
            "Confirmar Push",
            mensaje_confirmacion
        )

        if not confirmado:
            return

        ruta_repositorio = (
            self.ruta_repositorio
        )

        self.operacion_remota_en_curso = True

        self.actualizar_controles_operacion_remota()

        self.variable_estado.set(
            "Verificando el remoto y ejecutando Push..."
        )

        self.variable_ultima_consulta.set(
            (
                "Push en curso. Se ejecutará Fetch nuevamente "
                "antes de enviar."
            )
        )

        hilo_push = threading.Thread(
            target=self.trabajo_push,
            args=(
                ruta_repositorio,
            ),
            daemon=True
        )

        hilo_push.start()

    def trabajo_push(
        self,
        ruta_repositorio
    ):
        """
        Ejecuta Push seguro fuera del hilo principal.

        Este método nunca modifica controles Tkinter.
        """

        resultado_push = (
            self.servicio_git.ejecutar_push_seguro(
                ruta_repositorio
            )
        )

        resultado_fetch_final = None
        estado_sincronizacion = None

        if resultado_push.exitoso:
            resultado_remoto = (
                self.servicio_git.obtener_remoto_sincronizacion(
                    ruta_repositorio
                )
            )

            if resultado_remoto.exitoso:
                resultado_fetch_final = (
                    self.servicio_git.ejecutar_fetch(
                        ruta_repositorio,
                        resultado_remoto.salida
                    )
                )

                if resultado_fetch_final.exitoso:
                    estado_sincronizacion = (
                        self.servicio_git.obtener_estado_sincronizacion(
                            ruta_repositorio
                        )
                    )

        self.cola_resultados.put(
            (
                "push",
                ruta_repositorio,
                resultado_push,
                resultado_fetch_final,
                estado_sincronizacion
            )
        )

    # =============================================================
    # COLA DE RESULTADOS
    # =============================================================

    def procesar_cola_resultados(self):
        """
        Procesa los resultados enviados por los hilos secundarios.
        """

        try:
            while True:
                elemento = (
                    self.cola_resultados.get_nowait()
                )

                tipo_operacion = elemento[0]

                if tipo_operacion == "fetch":
                    self.procesar_resultado_fetch(
                        *elemento[1:]
                    )

                elif tipo_operacion == "pull":
                    self.procesar_resultado_pull(
                        *elemento[1:]
                    )

                elif tipo_operacion == "push":
                    self.procesar_resultado_push(
                        *elemento[1:]
                    )

        except queue.Empty:
            pass

        self.ventana_principal.after(
            100,
            self.procesar_cola_resultados
        )

    def procesar_resultado_fetch(
        self,
        ruta_repositorio,
        remoto,
        resultado_fetch,
        estado_sincronizacion
    ):
        """
        Actualiza la interfaz cuando Fetch termina.
        """

        self.operacion_remota_en_curso = False

        self.actualizar_controles_operacion_remota()

        if ruta_repositorio != self.ruta_repositorio:
            return

        if not resultado_fetch.exitoso:
            self.fetch_exitoso_en_sesion = False

            self.variable_estado.set(
                "Fetch falló."
            )

            self.variable_ultima_consulta.set(
                "El último Fetch no pudo completarse."
            )

            self.actualizar_estado_botones_sincronizacion()

            detalle = (
                resultado_fetch.error
                if resultado_fetch.error
                else resultado_fetch.salida
            )

            messagebox.showerror(
                "Error durante Fetch",
                detalle
            )

            return

        self.fetch_exitoso_en_sesion = True

        if estado_sincronizacion is None:
            self.variable_estado.set(
                (
                    "Fetch completado, pero no se pudo "
                    "calcular el estado."
                )
            )

            self.actualizar_estado_botones_sincronizacion()

            return

        self.aplicar_estado_sincronizacion(
            estado_sincronizacion
        )

        self.variable_ultima_consulta.set(
            f"Fetch completado correctamente desde '{remoto}'."
        )

        if estado_sincronizacion.exitoso:
            self.variable_estado.set(
                "Fetch completado. Estado remoto actualizado."
            )
        else:
            self.variable_estado.set(
                (
                    "Fetch completado, pero el estado "
                    "no pudo calcularse."
                )
            )

    def procesar_resultado_pull(
        self,
        ruta_repositorio,
        resultado_pull,
        resultado_fetch_final,
        estado_sincronizacion
    ):
        """
        Actualiza la interfaz cuando Pull termina.
        """

        self.operacion_remota_en_curso = False

        self.actualizar_controles_operacion_remota()

        if ruta_repositorio != self.ruta_repositorio:
            return

        if not resultado_pull.exitoso:
            # Exigimos otro Fetch después de cualquier Pull fallido.
            self.fetch_exitoso_en_sesion = False

            # El motor pudo haber actualizado las referencias remotas
            # antes de decidir que Pull no era seguro.
            self.cargar_estado_sincronizacion_local()

            self.variable_estado.set(
                "Pull no realizado."
            )

            self.variable_ultima_consulta.set(
                (
                    "Pull no realizado. Ejecute Fetch nuevamente "
                    "antes de reintentarlo."
                )
            )

            detalle = (
                resultado_pull.error
                if resultado_pull.error
                else resultado_pull.salida
            )

            messagebox.showerror(
                "Pull no realizado",
                detalle
            )

            return

        # Pull fue exitoso.
        self.fetch_exitoso_en_sesion = True

        if (
            resultado_fetch_final is not None
            and resultado_fetch_final.exitoso
            and estado_sincronizacion is not None
        ):
            self.aplicar_estado_sincronizacion(
                estado_sincronizacion
            )

            self.variable_ultima_consulta.set(
                (
                    "Pull completado y estado remoto "
                    "verificado correctamente."
                )
            )

        else:
            self.cargar_estado_sincronizacion_local()

            self.variable_ultima_consulta.set(
                (
                    "Pull completado. No fue posible completar "
                    "la verificación remota posterior."
                )
            )

        # Los archivos y el historial pudieron cambiar
        # como consecuencia del fast-forward.
        self.cargar_cambios()
        self.actualizar_historial_si_abierto()

        self.variable_estado.set(
            "Pull completado correctamente mediante fast-forward."
        )

        messagebox.showinfo(
            "Pull completado",
            (
                "Los commits remotos fueron descargados correctamente.\n\n"
                "La actualización se realizó mediante fast-forward.\n\n"
                "No se creó ningún Merge automático.\n"
                "No se realizó ningún Rebase automático."
            )
        )

    def procesar_resultado_push(
        self,
        ruta_repositorio,
        resultado_push,
        resultado_fetch_final,
        estado_sincronizacion
    ):
        """
        Actualiza la interfaz cuando Push termina.
        """

        self.operacion_remota_en_curso = False

        self.actualizar_controles_operacion_remota()

        if ruta_repositorio != self.ruta_repositorio:
            return

        if not resultado_push.exitoso:
            # Después de un fallo exigimos otro Fetch
            # antes de permitir un nuevo Push.
            self.fetch_exitoso_en_sesion = False

            self.cargar_estado_sincronizacion_local()

            self.variable_estado.set(
                "Push no realizado."
            )

            self.variable_ultima_consulta.set(
                (
                    "Push no realizado. Ejecute Fetch nuevamente "
                    "antes de reintentarlo."
                )
            )

            detalle = (
                resultado_push.error
                if resultado_push.error
                else resultado_push.salida
            )

            messagebox.showerror(
                "Push no realizado",
                detalle
            )

            return

        self.fetch_exitoso_en_sesion = True

        if (
            resultado_fetch_final is not None
            and resultado_fetch_final.exitoso
            and estado_sincronizacion is not None
        ):
            self.aplicar_estado_sincronizacion(
                estado_sincronizacion
            )

            self.variable_ultima_consulta.set(
                (
                    "Push completado y estado remoto "
                    "verificado correctamente."
                )
            )

        else:
            self.cargar_estado_sincronizacion_local()

            self.variable_ultima_consulta.set(
                (
                    "Push completado. No fue posible completar "
                    "la verificación remota posterior."
                )
            )

        self.cargar_cambios()

        self.variable_estado.set(
            "Push completado correctamente."
        )

        messagebox.showinfo(
            "Push completado",
            (
                "Los commits fueron enviados correctamente.\n\n"
                "No se utilizó Push forzado.\n\n"
                "La información de sincronización fue actualizada."
            )
        )

    # =============================================================
    # ESTADO DE CONTROLES REMOTOS
    # =============================================================

    def actualizar_controles_operacion_remota(self):
        """
        Evita operaciones incompatibles mientras
        Fetch, Pull o Push están activos.
        """

        if self.operacion_remota_en_curso:
            self.boton_seleccionar.config(
                state=tk.DISABLED
            )

            self.boton_actualizar.config(
                state=tk.DISABLED
            )

            self.boton_historial.config(
                state=tk.DISABLED
            )

            self.boton_ramas.config(
                state=tk.DISABLED
            )

            self.boton_fetch.config(
                state=tk.DISABLED
            )

            self.boton_configurar_github.config(
                state=tk.DISABLED
            )

            self.boton_pull.config(
                state=tk.DISABLED
            )

            self.boton_push.config(
                state=tk.DISABLED
            )

            # El botón de descarte del Inspector también se bloquea
            # durante la operación remota; segura si no existe.
            self.actualizar_estado_boton_descartar()

            # Los botones de la ventana de ramas se bloquean
            # igualmente; segura si la ventana no existe.
            self.actualizar_estado_botones_ventana_ramas()

            return

        self.boton_seleccionar.config(
            state=tk.NORMAL
        )

        self.boton_actualizar.config(
            state=(
                tk.NORMAL
                if self.ruta_repositorio
                else tk.DISABLED
            )
        )

        self.boton_historial.config(
            state=(
                tk.NORMAL
                if self.ruta_repositorio
                else tk.DISABLED
            )
        )

        self.boton_ramas.config(
            state=(
                tk.NORMAL
                if self.ruta_repositorio
                else tk.DISABLED
            )
        )

        self.boton_fetch.config(
            state=(
                tk.NORMAL
                if (
                    self.ruta_repositorio
                    and self.remotos_repositorio
                )
                else tk.DISABLED
            )
        )

        self.boton_configurar_github.config(
            state=(
                tk.NORMAL
                if (
                    self.ruta_repositorio
                    and not self.remotos_repositorio
                )
                else tk.DISABLED
            )
        )

        self.actualizar_estado_botones_sincronizacion()

        # Al terminar la operación remota el botón de descarte del
        # Inspector vuelve a recalcularse; segura si no existe.
        self.actualizar_estado_boton_descartar()

        # Lo mismo para los botones de la ventana de ramas.
        self.actualizar_estado_botones_ventana_ramas()

    def actualizar_estado_botones_sincronizacion(self):
        """
        Habilita Pull o Push solamente cuando el estado
        conocido permite considerarlos candidatos.

        El servicio vuelve a validar todo antes
        de ejecutar la operación real.
        """

        puede_hacer_pull = False
        puede_hacer_push = False

        estado = (
            self.estado_sincronizacion_actual
        )

        condiciones_generales = (
            not self.operacion_remota_en_curso
            and bool(self.ruta_repositorio)
            and self.fetch_exitoso_en_sesion
            and not self.hay_cambios_pendientes
            and estado is not None
            and estado.exitoso
            and not estado.divergente
        )

        if condiciones_generales:
            # Pull:
            #
            # - upstream configurado
            # - ningún commit local pendiente
            # - uno o más commits remotos pendientes
            if (
                estado.upstream_configurado
                and estado.commits_por_subir == 0
                and estado.commits_por_bajar > 0
            ):
                puede_hacer_pull = True

            # Push:
            #
            # - uno o más commits locales pendientes
            # - ningún commit remoto pendiente
            if (
                estado.commits_por_subir > 0
                and estado.commits_por_bajar == 0
            ):
                puede_hacer_push = True

        self.boton_pull.config(
            state=(
                tk.NORMAL
                if puede_hacer_pull
                else tk.DISABLED
            )
        )

        self.boton_push.config(
            state=(
                tk.NORMAL
                if puede_hacer_push
                else tk.DISABLED
            )
        )

    # =============================================================
    # CONFIGURACIÓN INICIAL DE GITHUB
    # =============================================================

    def abrir_configuracion_github(self):
        """
        Abre la ventana educativa para configurar el primer remoto.

        Solamente está disponible cuando el repositorio no tiene
        ningún remoto configurado.
        """

        if self.operacion_remota_en_curso:
            return

        if not self.ruta_repositorio:
            return

        if self.remotos_repositorio:
            messagebox.showinfo(
                "Remoto ya configurado",
                (
                    "Este repositorio ya tiene remoto(s) "
                    "configurado(s).\n\n"
                    "La aplicación no modificará ni eliminará "
                    "remotos existentes."
                )
            )

            return

        # Reutilizamos la ventana existente en lugar de crear otra.
        if (
            self.ventana_configuracion_github is not None
            and self.ventana_configuracion_github.winfo_exists()
        ):
            self.ventana_configuracion_github.deiconify()
            self.ventana_configuracion_github.lift()
            self.ventana_configuracion_github.focus_force()
            return

        self.ventana_configuracion_github = tk.Toplevel(
            self.ventana_principal
        )

        self.ventana_configuracion_github.title(
            "Configurar GitHub - Gestor Git"
        )

        self.ventana_configuracion_github.geometry(
            "760x520"
        )

        self.ventana_configuracion_github.minsize(
            640,
            440
        )

        self.ventana_configuracion_github.transient(
            self.ventana_principal
        )

        marco_configuracion = ttk.Frame(
            self.ventana_configuracion_github,
            padding=15
        )

        marco_configuracion.pack(
            fill=tk.BOTH,
            expand=True
        )

        ttk.Label(
            marco_configuracion,
            text="Configurar GitHub",
            style="Titulo.TLabel"
        ).pack(
            anchor="w"
        )

        ttk.Label(
            marco_configuracion,
            text=(
                "Paso a paso para conectar este repositorio local "
                "con un repositorio de GitHub:"
            ),
            style="AyudaVisible.TLabel",
            wraplength=700
        ).pack(
            anchor="w",
            pady=(8, 10)
        )

        pasos = (
            "1. Primero crea un repositorio VACÍO en GitHub.",
            "2. No agregues README, .gitignore ni licencia desde "
            "GitHub para este caso, porque el proyecto local ya "
            "tiene historial.",
            "3. Copia la URL HTTPS del repositorio.",
            "4. Pégala en GestorGit.",
            "5. GestorGit configurará solamente el remoto origin.",
            "6. Después será necesario ejecutar Fetch.",
            "7. Finalmente Push podrá enviar los commits locales "
            "si las validaciones existentes lo permiten.",
        )

        for paso in pasos:
            ttk.Label(
                marco_configuracion,
                text=paso,
                wraplength=700
            ).pack(
                anchor="w",
                pady=(1, 0)
            )

        ttk.Label(
            marco_configuracion,
            text=(
                "\nGestorGit NO inicia sesión, no recibe usuario, "
                "contraseña ni PAT, y no utiliza la API de GitHub. "
                "Solamente abre el navegador."
            ),
            style="AyudaVisible.TLabel",
            wraplength=700
        ).pack(
            anchor="w",
            pady=(8, 0)
        )

        self.boton_abrir_github = ttk.Button(
            marco_configuracion,
            text="Abrir GitHub para crear repositorio",
            command=self.abrir_github_para_crear_repositorio,
            style="Accion.TButton"
        )

        self.boton_abrir_github.pack(
            anchor="w",
            pady=(10, 0)
        )

        marco_url = ttk.Frame(
            marco_configuracion
        )

        marco_url.pack(
            fill=tk.X,
            pady=(14, 0)
        )

        ttk.Label(
            marco_url,
            text="URL HTTPS de GitHub:"
        ).pack(
            side=tk.LEFT
        )

        self.variable_url_github = tk.StringVar()

        entrada_url = ttk.Entry(
            marco_url,
            textvariable=self.variable_url_github,
            width=52
        )

        entrada_url.pack(
            side=tk.LEFT,
            padx=(8, 0)
        )

        entrada_url.focus_set()

        marco_botones = ttk.Frame(
            marco_configuracion
        )

        marco_botones.pack(
            anchor="e",
            pady=(14, 0)
        )

        self.boton_agregar_origin = ttk.Button(
            marco_botones,
            text="Agregar origin",
            command=self.agregar_origin_desde_ventana,
            style="Commit.TButton"
        )

        self.boton_agregar_origin.pack(
            side=tk.LEFT
        )

        AyudaEmergente(
            self.boton_agregar_origin,
            TEXTOS_AYUDA_GIT_V1["agregar_origin"],
            ancho_texto=620
        )

        self.boton_cancelar_configuracion = ttk.Button(
            marco_botones,
            text="Cancelar",
            command=self.cerrar_configuracion_github,
            style="Accion.TButton"
        )

        self.boton_cancelar_configuracion.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.ventana_configuracion_github.protocol(
            "WM_DELETE_WINDOW",
            self.cerrar_configuracion_github
        )

    def abrir_github_para_crear_repositorio(self):
        """
        Abre el navegador en la página de creación de repositorios.

        La aplicación no inicia sesión ni recibe credenciales.
        """

        navegador_abierto = False

        try:
            navegador_abierto = webbrowser.open(
                "https://github.com/new"
            )
        except Exception:
            navegador_abierto = False

        if not navegador_abierto:
            messagebox.showerror(
                "No fue posible abrir el navegador",
                (
                    "No fue posible abrir el navegador.\n\n"
                    "Puede ingresar manualmente a:\n"
                    "https://github.com/new"
                )
            )

    def agregar_origin_desde_ventana(self):
        """
        Configura el remoto origin con la URL indicada por el usuario.

        Solamente modifica la configuración local de Git.
        No ejecuta Fetch ni Push automáticamente.
        """

        if self.operacion_remota_en_curso:
            messagebox.showinfo(
                "Operación en curso",
                (
                    "Espere a que termine la operación remota "
                    "en curso antes de configurar el remoto."
                )
            )

            return

        if not self.ruta_repositorio:
            self.cerrar_configuracion_github()
            return

        url_remoto = (
            self.variable_url_github.get()
        )

        self.variable_estado.set(
            "Configurando el remoto origin..."
        )

        self.ventana_principal.update_idletasks()

        resultado = self.servicio_git.agregar_remoto_github(
            self.ruta_repositorio,
            url_remoto
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible configurar el remoto origin."
            )

            detalle = (
                resultado.error
                if resultado.error
                else resultado.salida
            )

            messagebox.showerror(
                "No fue posible configurar origin",
                detalle
            )

            return

        self.cerrar_configuracion_github()

        # Volvemos a cargar el repositorio para actualizar remotos
        # e información local, y exigimos un Fetch nuevo antes de
        # habilitar Pull o Push.
        self.cargar_repositorio(
            self.ruta_repositorio,
            reiniciar_fetch=True
        )

        messagebox.showinfo(
            "Remoto origin configurado",
            (
                "El remoto origin fue configurado correctamente.\n\n"
                "Ahora ejecute Fetch para consultar GitHub."
            )
        )

    def cerrar_configuracion_github(self):
        """
        Cierra la ventana de configuración si está abierta.
        """

        if hasattr(
            self,
            "ventana_configuracion_github"
        ):
            ventana = self.ventana_configuracion_github

            if ventana is not None:
                try:
                    if ventana.winfo_exists():
                        ventana.destroy()
                except tk.TclError:
                    pass

            self.ventana_configuracion_github = None
            self.variable_url_github = None

    # =============================================================
    # ARCHIVOS
    # =============================================================

    def seleccionar_todos_los_cambios(self):
        """
        Selecciona todos los archivos visibles.
        """

        elementos = self.tabla_cambios.get_children()

        if not elementos:
            return

        self.tabla_cambios.selection_set(
            elementos
        )

    def preparar_seleccionados(self):
        """
        Prepara los archivos seleccionados para commit.
        """

        if not self.ruta_repositorio:
            return

        seleccion = self.tabla_cambios.selection()

        if not seleccion:
            messagebox.showinfo(
                "Sin selección",
                "Seleccione al menos un archivo."
            )

            return

        rutas_archivos = []

        for identificador in seleccion:
            cambio = self.cambios_por_elemento.get(
                identificador
            )

            if cambio is None:
                continue

            if cambio.preparado:
                continue

            if cambio.en_conflicto:
                continue

            rutas_archivos.append(
                cambio.ruta
            )

        if not rutas_archivos:
            messagebox.showinfo(
                "Sin archivos pendientes",
                (
                    "Los archivos seleccionados ya están "
                    "preparados para commit."
                )
            )

            return

        mensaje = self._crear_mensaje_confirmacion_archivos(
            rutas_archivos,
            singular=(
                "Se preparará 1 archivo para el próximo commit."
            ),
            plural=(
                "Se prepararán {cantidad} archivos "
                "para el próximo commit."
            )
        )

        confirmado = messagebox.askyesno(
            "Preparar archivos",
            mensaje
        )

        if not confirmado:
            return

        self.variable_estado.set(
            "Preparando archivos..."
        )

        self.ventana_principal.update_idletasks()

        resultado = self.servicio_git.agregar_archivos(
            self.ruta_repositorio,
            rutas_archivos
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible preparar los archivos."
            )

            messagebox.showerror(
                "Error al preparar archivos",
                resultado.error
            )

            return

        self.cargar_cambios()

    def quitar_preparados_seleccionados(self):
        """
        Quita del área preparada los archivos seleccionados.

        Esta operación NO borra archivos.
        """

        if not self.ruta_repositorio:
            return

        seleccion = self.tabla_cambios.selection()

        if not seleccion:
            messagebox.showinfo(
                "Sin selección",
                "Seleccione al menos un archivo preparado."
            )

            return

        rutas_archivos = []

        for identificador in seleccion:
            cambio = self.cambios_por_elemento.get(
                identificador
            )

            if cambio is None:
                continue

            if not cambio.preparado:
                continue

            if cambio.en_conflicto:
                continue

            rutas_archivos.append(
                cambio.ruta
            )

        if not rutas_archivos:
            messagebox.showinfo(
                "Sin archivos preparados",
                (
                    "Los archivos seleccionados no están "
                    "preparados para commit."
                )
            )

            return

        mensaje = self._crear_mensaje_confirmacion_archivos(
            rutas_archivos,
            singular=(
                "Se quitará 1 archivo del próximo commit."
            ),
            plural=(
                "Se quitarán {cantidad} archivos "
                "del próximo commit."
            ),
            texto_final=(
                "Los archivos NO serán eliminados del disco.\n\n"
                "¿Desea continuar?"
            )
        )

        confirmado = messagebox.askyesno(
            "Quitar de preparados",
            mensaje
        )

        if not confirmado:
            return

        self.variable_estado.set(
            "Quitando archivos del área preparada..."
        )

        self.ventana_principal.update_idletasks()

        resultado = (
            self.servicio_git.quitar_archivos_preparados(
                self.ruta_repositorio,
                rutas_archivos
            )
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible quitar los archivos."
            )

            messagebox.showerror(
                "Error al quitar archivos",
                resultado.error
            )

            return

        self.cargar_cambios()

    def actualizar_preparados_seleccionados(self):
        """
        Actualiza el área preparada con la versión actual completa
        de los archivos seleccionados que lo requieran.

        Equivale a volver a ejecutar git add sobre cada ruta.
        No modifica el working tree y no crea commits.
        """

        if not self.ruta_repositorio:
            return

        seleccion = self.tabla_cambios.selection()

        if not seleccion:
            messagebox.showinfo(
                "Sin selección",
                "Seleccione al menos un archivo."
            )

            return

        rutas_archivos = []

        for identificador in seleccion:
            cambio = self.cambios_por_elemento.get(
                identificador
            )

            if cambio is None:
                continue

            if not cambio.requiere_actualizar_preparado:
                continue

            if cambio.en_conflicto:
                continue

            rutas_archivos.append(
                cambio.ruta
            )

        if not rutas_archivos:
            messagebox.showinfo(
                "Sin archivos para actualizar",
                (
                    "Ninguno de los archivos seleccionados "
                    "necesita actualización: ya están preparados "
                    "con su versión actual completa."
                )
            )

            return

        mensaje = self._crear_mensaje_confirmacion_archivos(
            rutas_archivos,
            singular=(
                "Se actualizará 1 archivo preparado "
                "con sus cambios actuales."
            ),
            plural=(
                "Se actualizarán {cantidad} archivos preparados "
                "con sus cambios actuales."
            ),
            texto_final=(
                "La versión preparada anterior de estos archivos "
                "será reemplazada en el área preparada por su "
                "versión actual completa.\n\n"
                "Los archivos del disco NO serán modificados "
                "ni eliminados.\n"
                "No se creará ningún commit.\n\n"
                "Si preparaste solamente parte de alguno de estos "
                "archivos con otra herramienta, también se "
                "incluirán sus cambios restantes.\n\n"
                "¿Desea continuar?"
            )
        )

        confirmado = messagebox.askyesno(
            "Actualizar preparados",
            mensaje
        )

        if not confirmado:
            return

        self.variable_estado.set(
            "Actualizando archivos preparados..."
        )

        self.ventana_principal.update_idletasks()

        resultado = (
            self.servicio_git.actualizar_archivos_preparados(
                self.ruta_repositorio,
                rutas_archivos
            )
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible actualizar los archivos preparados."
            )

            messagebox.showerror(
                "Error al actualizar preparados",
                resultado.error
            )

            return

        self.cargar_cambios()

    # =============================================================
    # COMMIT
    # =============================================================

    def crear_commit_desde_interfaz(self):
        """
        Crea un commit local con todos los archivos preparados.
        """

        if not self.ruta_repositorio:
            return

        mensaje_commit = (
            self.variable_mensaje_commit.get().strip()
        )

        if not mensaje_commit:
            messagebox.showinfo(
                "Mensaje obligatorio",
                "Escriba un mensaje para el commit."
            )

            self.entrada_mensaje_commit.focus_set()

            return

        resultado_cambios = self.servicio_git.obtener_cambios(
            self.ruta_repositorio
        )

        if not resultado_cambios.exitoso:
            messagebox.showerror(
                "Error al consultar Git",
                resultado_cambios.error
            )

            return

        # Bloqueo por conflicto ANTES de la confirmación: un
        # conflicto es un estado especial que Git deja para que una
        # persona decida. La decisión usa el dato estructurado
        # en_conflicto (procedente de los códigos Git), nunca el
        # texto localizado de la descripción.
        archivos_conflicto = [
            cambio.ruta
            for cambio in resultado_cambios.cambios
            if cambio.en_conflicto
        ]

        if archivos_conflicto:
            lista_conflictos = "\n".join(
                archivos_conflicto
            )

            messagebox.showwarning(
                "Conflicto en el índice",
                (
                    "No se puede crear el commit porque existen "
                    "archivos en conflicto:\n\n"
                    f"{lista_conflictos}\n\n"
                    "Git necesita que una persona decida cómo "
                    "resolver el conflicto. GestorGit no elige "
                    "una versión automáticamente."
                )
            )

            return

        rutas_preparadas = [
            cambio.ruta
            for cambio in resultado_cambios.cambios
            if cambio.preparado and not cambio.en_conflicto
        ]

        if not rutas_preparadas:
            messagebox.showinfo(
                "Sin archivos preparados",
                "No hay archivos preparados para crear el commit."
            )

            self.cargar_cambios()

            return

        resumen_archivos = self._crear_resumen_rutas(
            rutas_preparadas
        )

        mensaje_confirmacion = (
            "Se creará un commit LOCAL.\n\n"
            f"Mensaje:\n{mensaje_commit}\n\n"
            "Archivos que entrarán en el commit:\n"
            f"{resumen_archivos}\n\n"
            "El commit no será enviado automáticamente.\n\n"
            "¿Desea continuar?"
        )

        confirmado = messagebox.askyesno(
            "Crear commit",
            mensaje_confirmacion
        )

        if not confirmado:
            return

        self.variable_estado.set(
            "Creando commit..."
        )

        self.ventana_principal.update_idletasks()

        resultado = self.servicio_git.crear_commit(
            self.ruta_repositorio,
            mensaje_commit
        )

        if not resultado.exitoso:
            self.variable_estado.set(
                "No fue posible crear el commit."
            )

            detalle_error = (
                resultado.error
                if resultado.error
                else resultado.salida
            )

            messagebox.showerror(
                "No fue posible crear el commit",
                detalle_error
            )

            self.cargar_cambios()

            return

        resultado_hash = self.servicio_git.obtener_hash_actual(
            self.ruta_repositorio
        )

        hash_commit = (
            resultado_hash.salida
            if resultado_hash.exitoso
            else "No disponible"
        )

        self.variable_mensaje_commit.set(
            ""
        )

        self.cargar_repositorio(
            self.ruta_repositorio,
            reiniciar_fetch=False
        )

        messagebox.showinfo(
            "Commit creado",
            (
                "El commit fue creado correctamente.\n\n"
                f"Hash: {hash_commit}\n\n"
                "El commit existe solamente en el repositorio local.\n"
                "Utilice Push cuando desee enviarlo al remoto."
            )
        )

    # =============================================================
    # LIMPIEZA
    # =============================================================

    def limpiar_tabla(self):
        """
        Limpia la tabla de cambios.
        """

        for elemento in self.tabla_cambios.get_children():
            self.tabla_cambios.delete(
                elemento
            )

        self.cambios_por_elemento.clear()

    def deshabilitar_botones_de_archivos(self):
        """
        Deshabilita las acciones relacionadas con archivos.
        """

        self.boton_seleccionar_todo.config(
            state=tk.DISABLED
        )

        self.boton_preparar.config(
            state=tk.DISABLED
        )

        self.boton_actualizar_preparados.config(
            state=tk.DISABLED
        )

        self.boton_quitar_preparados.config(
            state=tk.DISABLED
        )

        self.boton_ver_cambios_locales.config(
            state=tk.DISABLED
        )

        self.boton_crear_commit.config(
            state=tk.DISABLED
        )

    def actualizar_estado_botones_archivos(self, _evento=None):
        """
        Actualiza el estado de los botones de archivos según
        el contenido de la tabla y la selección actual.
        """

        cambios = [
            self.cambios_por_elemento[elemento]
            for elemento in self.tabla_cambios.get_children()
            if elemento in self.cambios_por_elemento
        ]

        cambios_seleccionados = [
            self.cambios_por_elemento[elemento]
            for elemento in self.tabla_cambios.selection()
            if elemento in self.cambios_por_elemento
        ]

        hay_cambios_visibles = len(
            cambios
        ) > 0

        # Preparar actúa sobre los seleccionados que todavía
        # no están en el área preparada. Los conflictos nunca
        # son "preparables".
        hay_no_preparados_seleccionados = any(
            not cambio.preparado
            and not cambio.en_conflicto
            for cambio in cambios_seleccionados
        )

        # Quitar actúa sobre los seleccionados ya preparados,
        # pero NUNCA sobre conflictos: un conflicto no puede
        # "quitarse de preparados" (eso alteraría el estado
        # unmerged del índice).
        hay_preparados_seleccionados = any(
            cambio.preparado
            and not cambio.en_conflicto
            for cambio in cambios_seleccionados
        )

        # Actualizar actúa sobre los seleccionados que tienen
        # cambios nuevos fuera del índice. Los conflictos quedan
        # excluidos por su propia semántica.
        hay_que_actualizar = any(
            cambio.requiere_actualizar_preparado
            and not cambio.en_conflicto
            for cambio in cambios_seleccionados
        )

        self.boton_seleccionar_todo.config(
            state=(
                tk.NORMAL
                if hay_cambios_visibles
                else tk.DISABLED
            )
        )

        self.boton_preparar.config(
            state=(
                tk.NORMAL
                if hay_no_preparados_seleccionados
                else tk.DISABLED
            )
        )

        self.boton_actualizar_preparados.config(
            state=(
                tk.NORMAL
                if hay_que_actualizar
                else tk.DISABLED
            )
        )

        self.boton_quitar_preparados.config(
            state=(
                tk.NORMAL
                if hay_preparados_seleccionados
                else tk.DISABLED
            )
        )

        # El inspector actúa únicamente con exactamente un
        # archivo seleccionado.
        hay_un_solo_seleccionado = (
            len(cambios_seleccionados) == 1
        )

        self.boton_ver_cambios_locales.config(
            state=(
                tk.NORMAL
                if hay_un_solo_seleccionado
                else tk.DISABLED
            )
        )

        # El commit se habilita cuando hay preparados normales; el
        # servicio vuelve a bloquearlo con su mensaje educativo si
        # algún archivo fue modificado después de haber sido
        # preparado o si existe cualquier conflicto. Un conflicto
        # NO cuenta por sí solo como contenido commiteable.
        self.boton_crear_commit.config(
            state=(
                tk.NORMAL
                if any(
                    cambio.preparado
                    and not cambio.en_conflicto
                    for cambio in cambios
                )
                else tk.DISABLED
            )
        )

    def limpiar_estado_sincronizacion(self):
        """
        Restablece la información de sincronización.
        """

        self.estado_sincronizacion_actual = None

        self.variable_upstream.set(
            "-"
        )

        self.variable_rama_remota.set(
            "-"
        )

        self.variable_por_subir.set(
            "-"
        )

        self.variable_por_bajar.set(
            "-"
        )

        self.variable_estado_sincronizacion.set(
            "Seleccione un repositorio."
        )

        self.variable_ultima_consulta.set(
            "Todavía no se ejecutó Fetch en esta sesión."
        )

        self.actualizar_estado_botones_sincronizacion()

    def limpiar_repositorio(self):
        """
        Restablece toda la información visual.
        """

        self.ruta_repositorio = ""

        self.remotos_repositorio = []

        self.hay_cambios_pendientes = False

        self.estado_sincronizacion_actual = None

        self.fetch_exitoso_en_sesion = False

        self.variable_ruta.set(
            "Ningún repositorio seleccionado"
        )

        self.variable_rama.set("-")
        self.variable_remoto.set("-")
        self.variable_commits.set("-")

        self.variable_mensaje_commit.set(
            ""
        )

        self.boton_actualizar.config(
            state=tk.DISABLED
        )

        self.boton_historial.config(
            state=tk.DISABLED
        )

        self.boton_ramas.config(
            state=tk.DISABLED
        )

        self.boton_fetch.config(
            state=tk.DISABLED
        )

        self.boton_configurar_github.config(
            state=tk.DISABLED
        )

        self.boton_pull.config(
            state=tk.DISABLED
        )

        self.boton_push.config(
            state=tk.DISABLED
        )

        self.deshabilitar_botones_de_archivos()

        self.limpiar_tabla()

        self.limpiar_estado_sincronizacion()

        self.cerrar_configuracion_github()

        self.cerrar_historial()

        self.cerrar_detalle_commit()

        self.cerrar_ventana_ramas()

    # =============================================================
    # MENSAJES DE CONFIRMACIÓN
    # =============================================================

    @staticmethod
    def _crear_mensaje_confirmacion_pull(
        estado
    ):
        """
        Construye la confirmación detallada de Pull.
        """

        cantidad = (
            estado.commits_por_bajar
        )

        if cantidad == 1:
            encabezado = (
                "Se descargará 1 commit."
            )
        else:
            encabezado = (
                f"Se descargarán {cantidad} commits."
            )

        return (
            f"{encabezado}\n\n"
            f"Rama local: {estado.rama_local}\n"
            f"Remoto: {estado.remoto}\n"
            f"Origen: {estado.rama_remota}\n\n"
            "Antes de descargar se ejecutará Fetch nuevamente.\n"
            "Si el estado remoto cambió, Pull será bloqueado.\n\n"
            "La actualización solamente se permitirá mediante "
            "fast-forward.\n\n"
            "No se realizará Merge automático.\n"
            "No se realizará Rebase automático.\n\n"
            "¿Desea continuar?"
        )

    @staticmethod
    def _crear_mensaje_confirmacion_push(
        estado
    ):
        """
        Construye la confirmación detallada de Push.
        """

        cantidad = (
            estado.commits_por_subir
        )

        if cantidad == 1:
            encabezado = (
                "Se enviará 1 commit."
            )
        else:
            encabezado = (
                f"Se enviarán {cantidad} commits."
            )

        if (
            not estado.upstream_configurado
            and not estado.rama_remota_existe
        ):
            explicacion_destino = (
                "La rama remota todavía no existe.\n"
                "Se creará y quedará configurada como upstream."
            )

        elif not estado.upstream_configurado:
            explicacion_destino = (
                "La rama remota ya existe, pero todavía no está "
                "configurada como upstream.\n"
                "El Push establecerá esa relación."
            )

        else:
            explicacion_destino = (
                "La rama ya tiene su upstream configurado."
            )

        return (
            f"{encabezado}\n\n"
            f"Rama local: {estado.rama_local}\n"
            f"Remoto: {estado.remoto}\n"
            f"Destino: {estado.rama_remota}\n\n"
            f"{explicacion_destino}\n\n"
            "Antes de enviar se ejecutará Fetch nuevamente.\n"
            "Si el remoto cambió, Push será bloqueado.\n\n"
            "Nunca se utilizará Push forzado.\n\n"
            "¿Desea continuar?"
        )

    @staticmethod
    def _crear_resumen_rutas(rutas):
        """
        Crea un resumen de rutas para mostrar
        en una confirmación.
        """

        limite = 15

        rutas_visibles = rutas[
            :limite
        ]

        texto = "\n".join(
            f"- {ruta}"
            for ruta in rutas_visibles
        )

        cantidad_restante = (
            len(rutas)
            - len(rutas_visibles)
        )

        if cantidad_restante > 0:
            texto += (
                f"\n- ... y {cantidad_restante} archivo(s) más"
            )

        return texto

    def _crear_mensaje_confirmacion_archivos(
        self,
        rutas,
        singular,
        plural,
        texto_final="¿Desea continuar?"
    ):
        """
        Construye mensajes de confirmación para archivos.
        """

        cantidad = len(
            rutas
        )

        if cantidad == 1:
            encabezado = singular
        else:
            encabezado = plural.format(
                cantidad=cantidad
            )

        resumen = self._crear_resumen_rutas(
            rutas
        )

        return (
            f"{encabezado}\n\n"
            f"{resumen}\n\n"
            f"{texto_final}"
        )


def iniciar_aplicacion():
    """
    Inicia la aplicación.
    """

    ventana_principal = tk.Tk()

    AplicacionGit(
        ventana_principal
    )

    ventana_principal.mainloop()


if __name__ == "__main__":
    iniciar_aplicacion()
