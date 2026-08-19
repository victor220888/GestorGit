"""
Servicio de ramas locales para GestorGit.

Permite listar ramas LOCALES, identificar la rama actual, cambiar
a una rama local existente y crear una rama nueva desde el HEAD
actual.

Toda la Git se ejecuta a través del ServicioGit/ServicioRemotoGit
existente (ejecutar_git), siempre con listas de argumentos y nunca
con shell=True. Ninguna operación consulta Internet ni ejecuta
Fetch, Pull o Push.

Seguridad:
- el working tree, el staging y los archivos nuevos deben estar
  completamente limpios para cambiar o crear ramas;
- ningún cambio se descarta para permitir el switch;
- HEAD separado (detached) bloquea cambiar y crear;
- una rama nueva queda SOLO en el repositorio local y sin
  upstream; la publicación será una etapa posterior separada.
"""

from pathlib import Path

from modelos_ramas import RamaLocal, ResultadoRamas


class ServicioRamasGit:
    """
    Operaciones conservadoras sobre ramas locales.
    """

    def __init__(self, servicio_git):
        """
        Recibe la instancia existente de ServicioGit o de
        ServicioRemotoGit para reutilizar ejecutar_git.
        """

        self.servicio_git = servicio_git

    # =============================================================
    # Consultas
    # =============================================================

    def obtener_ramas_locales(self, ruta_repositorio):
        """
        Lista únicamente las ramas locales (refs/heads/...).

        La rama actual aparece primero y el resto en orden
        alfabético. Con HEAD separado las ramas se listan, pero
        cambiar y crear quedan bloqueados (se avisa en mensaje).
        """

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return ResultadoRamas(
                exitoso=False,
                error=(
                    estado.mensaje
                    or "La ruta indicada no es un repositorio Git válido."
                )
            )

        resultado = self.servicio_git.ejecutar_git(
            argumentos=[
                "for-each-ref",
                "--format=%(refname:short)",
                "refs/heads/"
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return ResultadoRamas(
                exitoso=False,
                error=(
                    resultado.error
                    or "Git no pudo listar las ramas locales."
                )
            )

        nombres = []

        for linea in resultado.salida.splitlines():
            nombre = linea.strip()

            if nombre:
                nombres.append(nombre)

        rama_actual = self._obtener_rama_actual(
            ruta_repositorio
        )

        ramas = [
            RamaLocal(
                nombre=nombre,
                actual=(nombre == rama_actual)
            )
            for nombre in nombres
        ]

        # Rama actual primero; el resto en orden alfabético.
        ramas.sort(
            key=lambda rama: (
                not rama.actual,
                rama.nombre.lower()
            )
        )

        # Distinción estructurada y explícita:
        # A) repositorio con commits y symbolic-ref falla:
        #    HEAD está separado (detached).
        # B) repositorio sin commits: NO es un HEAD separado,
        #    aunque ninguna rama quede marcada como actual.
        tiene_commits = estado.tiene_commits

        head_separado = False

        mensaje = ""

        if tiene_commits and not rama_actual:
            head_separado = True

            mensaje = (
                "HEAD está separado (detached: apunta a un commit "
                "directo). Las ramas se muestran, pero cambiar de "
                "rama y crear ramas quedan bloqueados."
            )
        elif not tiene_commits:
            mensaje = (
                "Repositorio sin commits todavía: no existe "
                "ninguna rama. Primero cree un commit en la rama "
                "inicial con GestorGit."
            )

        return ResultadoRamas(
            exitoso=True,
            ramas=ramas,
            mensaje=mensaje,
            tiene_commits=tiene_commits,
            head_separado=head_separado
        )

    # =============================================================
    # Cambiar de rama
    # =============================================================

    def cambiar_rama(self, ruta_repositorio, nombre_rama):
        """
        Cambia a una rama LOCAL existente.

        Comando productivo:

            git switch --no-guess <nombre_rama>

        La existencia local se comprueba antes; --no-guess evita
        que Git adivine una rama remota con el mismo nombre.
        """

        nombre_valido, motivo = self._validar_nombre_rama(
            nombre_rama,
            ruta_repositorio
        )

        if not nombre_valido:
            return ResultadoRamas(
                exitoso=False,
                error=motivo
            )

        precondiciones_ok, error = self._validar_precondiciones(
            ruta_repositorio
        )

        if not precondiciones_ok:
            return ResultadoRamas(
                exitoso=False,
                error=error
            )

        if not self._rama_existe_local(
            ruta_repositorio,
            nombre_rama
        ):
            return ResultadoRamas(
                exitoso=False,
                error=(
                    f"La rama local '{nombre_rama}' no existe: "
                    "GestorGit no adivinará ni buscará ramas "
                    "remotas con ese nombre."
                )
            )

        rama_actual = self._obtener_rama_actual(
            ruta_repositorio
        )

        if rama_actual == nombre_rama:
            return ResultadoRamas(
                exitoso=False,
                error=(
                    f"Ya se encuentra en la rama local "
                    f"'{nombre_rama}'."
                )
            )

        # SEGUNDA revalidación inmediatamente antes del git switch
        # productivo (defensa en profundidad): entre la primera
        # validación y este punto, otra herramienta podría haber
        # creado, modificado o preparado un archivo. CUALQUIER
        # cambio local vuelve a bloquear el cambio de rama.
        precondiciones_ok, error = self._validar_precondiciones(
            ruta_repositorio
        )

        if not precondiciones_ok:
            return ResultadoRamas(
                exitoso=False,
                error=error
            )

        resultado = self.servicio_git.ejecutar_git(
            argumentos=[
                "switch",
                "--no-guess",
                nombre_rama
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return ResultadoRamas(
                exitoso=False,
                error=(
                    resultado.error
                    or f"No fue posible cambiar a la rama local "
                    f"'{nombre_rama}'."
                )
            )

        return ResultadoRamas(
            exitoso=True,
            mensaje=(
                f"Ahora se encuentra en la rama local "
                f"'{nombre_rama}'."
            )
        )

    # =============================================================
    # Crear rama
    # =============================================================

    def crear_rama(self, ruta_repositorio, nombre_rama):
        """
        Crea una rama local DESDE el HEAD actual y cambia a ella.

        Comando productivo:

            git switch -c <nombre_rama>

        No se acepta un start-point: la rama siempre nace del
        commit actual. La rama queda SOLO en el repositorio
        local y sin upstream.
        """

        nombre_valido, motivo = self._validar_nombre_rama(
            nombre_rama,
            ruta_repositorio
        )

        if not nombre_valido:
            return ResultadoRamas(
                exitoso=False,
                error=motivo
            )

        precondiciones_ok, error = self._validar_precondiciones(
            ruta_repositorio
        )

        if not precondiciones_ok:
            return ResultadoRamas(
                exitoso=False,
                error=error
            )

        if self._rama_existe_local(
            ruta_repositorio,
            nombre_rama
        ):
            return ResultadoRamas(
                exitoso=False,
                error=(
                    f"La rama local '{nombre_rama}' ya existe; "
                    "no se creará otra con el mismo nombre."
                )
            )

        # SEGUNDA revalidación inmediatamente antes del git switch
        # productivo (defensa en profundidad): entre la primera
        # validación y este punto, otra herramienta podría haber
        # creado, modificado o preparado un archivo. CUALQUIER
        # cambio local vuelve a bloquear la creación de la rama.
        precondiciones_ok, error = self._validar_precondiciones(
            ruta_repositorio
        )

        if not precondiciones_ok:
            return ResultadoRamas(
                exitoso=False,
                error=error
            )

        resultado = self.servicio_git.ejecutar_git(
            argumentos=[
                "switch",
                "-c",
                nombre_rama
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return ResultadoRamas(
                exitoso=False,
                error=(
                    resultado.error
                    or f"No fue posible crear la rama local "
                    f"'{nombre_rama}'."
                )
            )

        return ResultadoRamas(
            exitoso=True,
            mensaje=(
                "La rama se creó solamente en el repositorio "
                "local. Todavía no se publicó en el remoto."
            )
        )

    # =============================================================
    # Ayudas privadas
    # =============================================================

    def _obtener_rama_actual(self, ruta_repositorio):
        """
        Consulta estructurada de la rama actual.

        Devuelve una cadena vacía cuando HEAD está separado
        (detached) o no existe HEAD.
        """

        resultado = self.servicio_git.ejecutar_git(
            argumentos=[
                "symbolic-ref",
                "--quiet",
                "--short",
                "HEAD"
            ],
            ruta_repositorio=ruta_repositorio
        )

        if resultado.exitoso:
            return resultado.salida.strip()

        return ""

    def _rama_existe_local(self, ruta_repositorio, nombre_rama):
        """
        Comprueba con una referencia exacta si una rama local
        existe. No permite adivinación de ramas remotas.
        """

        resultado = self.servicio_git.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--verify",
                "--quiet",
                "refs/heads/" + nombre_rama
            ],
            ruta_repositorio=ruta_repositorio
        )

        return resultado.exitoso

    def _validar_precondiciones(self, ruta_repositorio):
        """
        Revalida el estado conservador del repositorio.

        Devuelve (True, "") cuando puede proseguir, o
        (False, mensaje) con el motivo del bloqueo.
        """

        estado = self.servicio_git.analizar_repositorio(
            ruta_repositorio
        )

        if not estado.es_repositorio:
            return (
                False,
                (
                    estado.mensaje
                    or "La ruta indicada no es un repositorio "
                    "Git válido."
                )
            )

        if not estado.tiene_commits:
            return (
                False,
                (
                    "El repositorio no tiene commits todavía. "
                    "La creación y el cambio de ramas necesitan "
                    "al menos un commit."
                )
            )

        if not self._obtener_rama_actual(ruta_repositorio):
            return (
                False,
                (
                    "HEAD está separado (detached: apunta a un "
                    "commit directo). Antes de cambiar o crear "
                    "ramas, vuelva a una rama local."
                )
            )

        operacion_en_curso = (
            self.servicio_git.detectar_operacion_en_curso(
                ruta_repositorio
            )
        )

        if operacion_en_curso:
            return (
                False,
                (
                    operacion_en_curso
                    + "\n\nGestorGit no cambiará ni creará ramas "
                    "mientras haya una operación Git en curso."
                )
            )

        hay_bloqueo, motivo_bloqueo = self._existe_index_lock(
            ruta_repositorio
        )

        if hay_bloqueo:
            return (False, motivo_bloqueo)

        cambios = self.servicio_git.obtener_cambios(
            ruta_repositorio
        )

        if not cambios.exitoso:
            return (
                False,
                (
                    "No fue posible determinar el estado de los "
                    "archivos del repositorio; la operación de "
                    "ramas quedó bloqueada."
                )
            )

        if cambios.cambios:
            return (
                False,
                self._sintetizar_motivo_cambios(
                    cambios.cambios
                )
            )

        return (True, "")

    def _sintetizar_motivo_cambios(self, cambios):
        """
        Construye un mensaje educativo cuando el repositorio
        no está limpio, distinguiendo conflictos.
        """

        tiene_conflicto = any(
            self._calcular_en_conflicto(
                cambio.estado_indice,
                cambio.estado_trabajo
            )
            for cambio in cambios
        )

        cantidad = len(cambios)

        detalle = (
            "El repositorio no está limpio: hay "
            f"{cantidad} archivo(s) con cambios o archivos "
            "nuevos pendientes."
        )

        if tiene_conflicto:
            detalle += (
                " Al menos uno de ellos está en conflicto: "
                "resuelva el conflicto con otra herramienta "
                "antes de cambiar de rama."
            )

        detalle += (
            "\n\nGestorGit no cambia ni crea ramas con cambios "
            "pendientes (tampoco con archivos nuevos) y nunca "
            "descarta cambios para permitir el switch. Confirme, "
            "prepare o descarte los cambios y vuelva a intentarlo."
        )

        return detalle

    @staticmethod
    def _calcular_en_conflicto(estado_indice, estado_trabajo):
        """
        True cuando el par de códigos de git status corresponde
        a un conflicto. Nunca se decide desde textos localizados.
        """

        return (
            estado_indice,
            estado_trabajo
        ) in {
            ("D", "D"),
            ("A", "U"),
            ("U", "D"),
            ("U", "A"),
            ("D", "U"),
            ("A", "A"),
            ("U", "U"),
        }

    def _existe_index_lock(self, ruta_repositorio):
        """
        Comprueba si existe index.lock sin eliminarlo jamás.

        Devuelve (True, motivo) cuando existe o cuando no fue
        posible verificarlo; (False, "") cuando no existe.
        """

        resultado = self.servicio_git.ejecutar_git(
            argumentos=["rev-parse", "--git-dir"],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            return (
                True,
                (
                    "No fue posible verificar si existe "
                    "index.lock; la operación de ramas quedó "
                    "bloqueada."
                )
            )

        ruta_git = Path(resultado.salida.strip())

        if not ruta_git.is_absolute():
            ruta_git = Path(ruta_repositorio) / ruta_git

        if (ruta_git / "index.lock").exists():
            return (
                True,
                (
                    "Hay un archivo index.lock: otro proceso Git "
                    "podría estar escribiendo en el índice. "
                    "GestorGit no lo elimina automáticamente: "
                    "espere a que termine el otro proceso."
                )
            )

        return (False, "")

    def _validar_nombre_rama(self, nombre_rama, ruta_repositorio):
        """
        Valida el nombre de una rama antes de crear nada.

        Primero reglas propias claras (sin corregir el nombre
        silenciosamente), después la sintaxis de Git con
        git check-ref-format refs/heads/<nombre>.

        Devuelve (True, "") o (False, motivo).
        """

        if nombre_rama is None:
            return (
                False,
                "No se indicó ningún nombre de rama."
            )

        if not isinstance(nombre_rama, str):
            return (
                False,
                "El nombre de la rama debe ser texto."
            )

        if nombre_rama == "":
            return (
                False,
                "El nombre de la rama no puede estar vacío."
            )

        if nombre_rama != nombre_rama.strip():
            return (
                False,
                "El nombre de la rama no puede tener espacios "
                "al inicio o al final."
            )

        if "\x00" in nombre_rama:
            return (
                False,
                "El nombre de la rama no puede contener "
                "caracteres NUL."
            )

        if nombre_rama.startswith("-"):
            return (
                False,
                "El nombre de la rama no puede comenzar con "
                "un guion."
            )

        if nombre_rama == "HEAD":
            return (
                False,
                "El nombre 'HEAD' está reservado por Git."
            )

        if nombre_rama == "@":
            return (
                False,
                "El nombre '@' está reservado por Git."
            )

        if "@{" in nombre_rama:
            return (
                False,
                "El nombre no puede contener la sintaxis "
                "especial @{...} (p. ej. @{-1}), que Git "
                "interpretaría de forma ambigua."
            )

        resultado = self.servicio_git.ejecutar_git(
            argumentos=[
                "check-ref-format",
                "refs/heads/" + nombre_rama
            ],
            ruta_repositorio=ruta_repositorio
        )

        if not resultado.exitoso:
            motivo = (
                f"Git rechaza el nombre de rama "
                f"'{nombre_rama}'."
            )

            if resultado.error:
                motivo += f"\n{resultado.error}"

            return (False, motivo)

        return (True, "")