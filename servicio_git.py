import shutil
import subprocess
from pathlib import Path

from modelos import (
    CambioArchivo,
    EstadoRepositorio,
    ResultadoCambios,
    ResultadoComando,
)


class ServicioGit:
    """
    Se encarga de toda la comunicación entre nuestra aplicación y Git.

    La interfaz gráfica nunca ejecutará comandos Git directamente.
    Todas las operaciones pasarán por esta clase.
    """

    def __init__(self):
        # Buscamos git.exe utilizando el PATH configurado en Windows.
        self.ruta_git = shutil.which("git")

    def git_disponible(self):
        """
        Indica si Git fue encontrado en el sistema.
        """

        return self.ruta_git is not None

    def obtener_ruta_git(self):
        """
        Devuelve la ruta completa donde fue encontrado git.exe.
        """

        return self.ruta_git

    def ejecutar_git(
        self,
        argumentos,
        ruta_repositorio=None,
        tiempo_maximo=30
    ):
        """
        Ejecuta un comando Git de manera controlada.

        Parámetros:
            argumentos:
                Lista con los argumentos que recibirá Git.

                Ejemplo:
                    ["--version"]

                Otro ejemplo:
                    ["status", "--short"]

            ruta_repositorio:
                Carpeta desde donde debe ejecutarse Git.

            tiempo_maximo:
                Cantidad máxima de segundos permitidos.

        Devuelve:
            Un objeto ResultadoComando.
        """

        # No intentamos ejecutar nada si Git no está disponible.
        if not self.git_disponible():
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="Git no fue encontrado en el sistema.",
                comando=""
            )

        # Construimos el comando utilizando una lista.
        #
        # Nunca construiremos comandos concatenando texto
        # para ejecutarlos mediante shell=True.
        comando = [self.ruta_git] + argumentos

        carpeta_trabajo = None

        # Si se indicó una carpeta, comprobamos que exista.
        if ruta_repositorio is not None:
            carpeta_trabajo = Path(ruta_repositorio)

            if not carpeta_trabajo.exists():
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error="La carpeta indicada no existe.",
                    comando=self._convertir_comando_a_texto(comando)
                )

            if not carpeta_trabajo.is_dir():
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error="La ruta indicada no corresponde a una carpeta.",
                    comando=self._convertir_comando_a_texto(comando)
                )

        try:
            resultado = subprocess.run(
                comando,
                cwd=carpeta_trabajo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=tiempo_maximo,
                shell=False
            )

            # IMPORTANTE:
            #
            # No utilizamos strip() porque eliminaría espacios
            # al principio de la salida.
            #
            # En algunos comandos de Git esos espacios tienen
            # un significado especial.
            #
            # Por ejemplo:
            #
            # " M archivo.sql"
            #
            # no significa lo mismo que:
            #
            # "M  archivo.sql"
            #
            # Por eso quitamos únicamente los saltos de línea
            # que puedan existir al final.
            salida = resultado.stdout.rstrip("\r\n")
            error = resultado.stderr.rstrip("\r\n")

            return ResultadoComando(
                exitoso=resultado.returncode == 0,
                codigo_salida=resultado.returncode,
                salida=salida,
                error=error,
                comando=self._convertir_comando_a_texto(comando)
            )

        except subprocess.TimeoutExpired:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=(
                    f"El comando superó el tiempo máximo "
                    f"de {tiempo_maximo} segundos."
                ),
                comando=self._convertir_comando_a_texto(comando)
            )

        except FileNotFoundError:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="No fue posible encontrar git.exe.",
                comando=self._convertir_comando_a_texto(comando)
            )

        except PermissionError:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="Windows denegó el acceso al ejecutar Git.",
                comando=self._convertir_comando_a_texto(comando)
            )

        except OSError as error_sistema:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=f"Error del sistema operativo: {error_sistema}",
                comando=self._convertir_comando_a_texto(comando)
            )

    def obtener_version(self):
        """
        Obtiene la versión instalada de Git.

        No modifica ningún repositorio.
        """

        return self.ejecutar_git(
            argumentos=["--version"]
        )

    def analizar_repositorio(self, ruta_repositorio):
        """
        Analiza una carpeta para determinar si contiene
        un repositorio Git válido.

        Esta función solamente ejecuta comandos de lectura.
        No modifica el repositorio.
        """

        # Primero comprobamos que se haya recibido una ruta.
        if ruta_repositorio is None:
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="No se indicó ninguna carpeta."
            )

        ruta_texto = str(ruta_repositorio).strip()

        if not ruta_texto:
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="No se indicó ninguna carpeta."
            )

        carpeta = Path(ruta_texto)

        # Comprobamos que la carpeta exista.
        if not carpeta.exists():
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="La carpeta indicada no existe."
            )

        # Comprobamos que realmente sea una carpeta.
        if not carpeta.is_dir():
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="La ruta indicada no corresponde a una carpeta."
            )

        # Preguntamos a Git si estamos dentro de un árbol de trabajo.
        resultado_validacion = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--is-inside-work-tree"
            ],
            ruta_repositorio=carpeta
        )

        if (
            not resultado_validacion.exitoso
            or resultado_validacion.salida.lower() != "true"
        ):
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="La carpeta no corresponde a un repositorio Git."
            )

        # Obtenemos la carpeta raíz real del repositorio.
        resultado_raiz = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--show-toplevel"
            ],
            ruta_repositorio=carpeta
        )

        if resultado_raiz.exitoso:
            ruta_raiz = resultado_raiz.salida
        else:
            ruta_raiz = str(carpeta.resolve())

        # Obtenemos la rama actual.
        #
        # symbolic-ref también permite conocer la rama
        # cuando todavía no existe ningún commit.
        resultado_rama = self.ejecutar_git(
            argumentos=[
                "symbolic-ref",
                "--quiet",
                "--short",
                "HEAD"
            ],
            ruta_repositorio=ruta_raiz
        )

        if resultado_rama.exitoso:
            rama_actual = resultado_rama.salida
        else:
            # Más adelante diferenciaremos este caso
            # de un HEAD separado.
            rama_actual = ""

        # Comprobamos si HEAD ya apunta a un commit.
        #
        # En un repositorio nuevo este comando puede fallar,
        # pero eso no significa que el repositorio esté dañado.
        resultado_head = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--verify",
                "HEAD"
            ],
            ruta_repositorio=ruta_raiz
        )

        tiene_commits = resultado_head.exitoso

        # Obtenemos la lista de remotos configurados.
        resultado_remotos = self.ejecutar_git(
            argumentos=[
                "remote"
            ],
            ruta_repositorio=ruta_raiz
        )

        remotos = []

        if resultado_remotos.exitoso and resultado_remotos.salida:
            remotos = [
                linea.strip()
                for linea in resultado_remotos.salida.splitlines()
                if linea.strip()
            ]

        return EstadoRepositorio(
            es_repositorio=True,
            ruta_raiz=ruta_raiz,
            rama_actual=rama_actual,
            tiene_commits=tiene_commits,
            remotos=remotos,
            mensaje="Repositorio Git válido."
        )

    def obtener_cambios(self, ruta_repositorio):
        """
        Obtiene todos los archivos que tienen cambios dentro
        del repositorio.

        Esta operación es únicamente de lectura.

        Utilizamos:

            git status --porcelain=v1 -z --untracked-files=all

        porque el formato porcelain está pensado para ser
        interpretado por programas.

        La opción -z separa los nombres mediante el carácter NUL.
        Esto nos permite manejar correctamente archivos cuyos
        nombres contienen espacios u otros caracteres especiales.
        """

        resultado = self.ejecutar_git(
            argumentos=[
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all"
            ],
            ruta_repositorio=ruta_repositorio
        )

        # Si Git devuelve un error, no intentamos interpretar
        # ninguna información.
        if not resultado.exitoso:
            return ResultadoCambios(
                exitoso=False,
                error=resultado.error
            )

        # Si Git no devolvió ningún registro significa que
        # el repositorio está limpio.
        if not resultado.salida:
            return ResultadoCambios(
                exitoso=True,
                cambios=[]
            )

        cambios = []

        # Cuando utilizamos -z, Git separa cada registro mediante
        # el carácter NUL.
        registros = resultado.salida.split("\0")

        indice = 0

        while indice < len(registros):
            registro = registros[indice]

            # Debido al NUL final puede existir un registro vacío.
            if not registro:
                indice += 1
                continue

            # Un registro normal tiene esta estructura:
            #
            # XY archivo
            #
            # Ejemplo:
            #
            # ?? Paquetes/FINI004.pkb
            #
            # Posición 0 = estado del índice
            # Posición 1 = estado del área de trabajo
            # Posición 2 = espacio separador
            # Posición 3 en adelante = ruta del archivo
            if len(registro) < 4:
                return ResultadoCambios(
                    exitoso=False,
                    error=(
                        "Git devolvió un estado de archivo "
                        "con un formato inesperado."
                    )
                )

            estado_indice = registro[0]
            estado_trabajo = registro[1]

            ruta_archivo = registro[3:]

            ruta_anterior = ""

            # Cuando un archivo fue renombrado o copiado,
            # Git devuelve una segunda ruta.
            #
            # Con el formato -z:
            #
            # primer registro  -> nueva ruta
            # segundo registro -> ruta anterior
            if (
                estado_indice in ("R", "C")
                or estado_trabajo in ("R", "C")
            ):
                if indice + 1 >= len(registros):
                    return ResultadoCambios(
                        exitoso=False,
                        error=(
                            "Git informó un archivo renombrado "
                            "o copiado sin indicar su ruta anterior."
                        )
                    )

                ruta_anterior = registros[indice + 1]

                # Como hemos consumido también la segunda ruta,
                # avanzamos una posición adicional.
                indice += 1

            descripcion = self._traducir_estado_archivo(
                estado_indice,
                estado_trabajo
            )

            # El primer carácter representa el estado del índice.
            #
            # Si no es un espacio, ? o ! significa que existe
            # algún cambio preparado para commit.
            preparado = estado_indice not in (
                " ",
                "?",
                "!"
            )

            cambio = CambioArchivo(
                ruta=ruta_archivo,
                estado_indice=estado_indice,
                estado_trabajo=estado_trabajo,
                descripcion=descripcion,
                preparado=preparado,
                ruta_anterior=ruta_anterior
            )

            cambios.append(cambio)

            indice += 1

        return ResultadoCambios(
            exitoso=True,
            cambios=cambios
        )

    def agregar_archivos(
        self,
        ruta_repositorio,
        rutas_archivos
    ):
        """
        Prepara uno o varios archivos para el próximo commit.

        Esta operación equivale a ejecutar git add.

        Parámetros:
            ruta_repositorio:
                Carpeta del repositorio Git.

            rutas_archivos:
                Lista de rutas relativas de archivos.

                Ejemplo:

                    [
                        "Paquetes/FINI004.pls",
                        "Paquetes/FINI005.pls"
                    ]

        Devuelve:
            Un objeto ResultadoComando.
        """

        # Primero comprobamos que la carpeta corresponda
        # realmente a un repositorio Git válido.
        estado_repositorio = self.analizar_repositorio(
            ruta_repositorio
        )

        if not estado_repositorio.es_repositorio:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=estado_repositorio.mensaje,
                comando=""
            )

        # Comprobamos que se haya recibido una lista de archivos.
        if rutas_archivos is None:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="No se indicó ningún archivo para agregar.",
                comando=""
            )

        rutas_validas = []

        for ruta_archivo in rutas_archivos:

            # No aceptamos valores None.
            if ruta_archivo is None:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error="Se recibió una ruta de archivo inválida.",
                    comando=""
                )

            ruta_texto = str(
                ruta_archivo
            )

            # No aceptamos nombres vacíos.
            if not ruta_texto or ruta_texto.isspace():
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error="Se recibió una ruta de archivo vacía.",
                    comando=""
                )

            ruta_objeto = Path(
                ruta_texto
            )

            # Los archivos deben indicarse siempre mediante
            # rutas relativas al repositorio.
            #
            # Ejemplo permitido:
            #
            # Paquetes/FINI004.pls
            #
            # Ejemplo rechazado:
            #
            # D:\\Documentos\\archivo.sql
            if ruta_objeto.is_absolute():
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        "Los archivos deben indicarse mediante "
                        "rutas relativas al repositorio."
                    ),
                    comando=""
                )

            # No permitimos salir del repositorio mediante "..".
            #
            # Por ejemplo:
            #
            # ../otro_archivo.sql
            if ".." in ruta_objeto.parts:
                return ResultadoComando(
                    exitoso=False,
                    codigo_salida=-1,
                    salida="",
                    error=(
                        "La ruta del archivo intenta salir "
                        "del repositorio."
                    ),
                    comando=""
                )

            # Evitamos agregar dos veces exactamente
            # la misma ruta.
            if ruta_texto not in rutas_validas:
                rutas_validas.append(
                    ruta_texto
                )

        # Después de validar, la lista todavía podría estar vacía.
        if not rutas_validas:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="No se indicó ningún archivo para agregar.",
                comando=""
            )

        # Utilizamos --literal-pathspecs para indicarle a Git
        # que trate los nombres recibidos literalmente.
        #
        # De esta manera caracteres especiales como:
        #
        # *
        # ?
        # [
        # ]
        #
        # no serán interpretados como patrones de búsqueda.
        #
        # También utilizamos "--" antes de las rutas para evitar
        # que un archivo cuyo nombre empiece por "-" pueda ser
        # interpretado como una opción de Git.
        argumentos = [
            "--literal-pathspecs",
            "add",
            "--",
        ]

        argumentos.extend(
            rutas_validas
        )

        return self.ejecutar_git(
            argumentos=argumentos,
            ruta_repositorio=estado_repositorio.ruta_raiz
        )

    @staticmethod
    def _traducir_estado_archivo(
        estado_indice,
        estado_trabajo
    ):
        """
        Convierte los códigos internos utilizados por Git
        en una descripción sencilla para el usuario.
        """

        codigo = estado_indice + estado_trabajo

        # Archivo nuevo que todavía no está siendo controlado por Git.
        if codigo == "??":
            return "Nuevo"

        # Archivo ignorado.
        #
        # Normalmente no aparecerá porque no estamos utilizando
        # --ignored, pero contemplamos el caso.
        if codigo == "!!":
            return "Ignorado"

        # Estados que Git utiliza para representar conflictos.
        codigos_conflicto = {
            "DD",
            "AU",
            "UD",
            "UA",
            "DU",
            "AA",
            "UU",
        }

        if codigo in codigos_conflicto:
            return "Conflicto"

        # Archivo renombrado.
        if "R" in codigo:
            return "Renombrado"

        # Archivo copiado.
        if "C" in codigo:
            return "Copiado"

        # Archivo nuevo agregado al área preparada.
        if estado_indice == "A":
            if estado_trabajo == "M":
                return "Agregado y modificado después"

            if estado_trabajo == "D":
                return "Agregado y eliminado después"

            return "Agregado y preparado"

        # Archivo eliminado.
        if estado_indice == "D":
            return "Eliminado y preparado"

        if estado_trabajo == "D":
            return "Eliminado"

        # Archivo modificado tanto antes como después de prepararlo.
        if (
            estado_indice == "M"
            and estado_trabajo == "M"
        ):
            return "Modificado, preparado y vuelto a modificar"

        # Archivo modificado y preparado para commit.
        if estado_indice == "M":
            return "Modificado y preparado"

        # Archivo modificado pero todavía no preparado.
        if estado_trabajo == "M":
            return "Modificado"

        # Git puede indicar cambios en el tipo de archivo.
        if estado_indice == "T":
            return "Tipo de archivo modificado y preparado"

        if estado_trabajo == "T":
            return "Tipo de archivo modificado"

        # Si aparece un estado que todavía no contemplamos,
        # no fallamos. Lo informamos como un cambio genérico.
        return "Cambio detectado"

    @staticmethod
    def _convertir_comando_a_texto(comando):
        """
        Convierte la lista del comando en texto únicamente
        para mostrarla o registrarla.

        Este texto nunca se utiliza para ejecutar el comando.
        """

        return " ".join(
            str(parte)
            for parte in comando
        )
