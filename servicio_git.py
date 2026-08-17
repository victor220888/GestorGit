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

            ruta_repositorio:
                Carpeta desde donde debe ejecutarse Git.

            tiempo_maximo:
                Cantidad máxima de segundos permitidos.

        Devuelve:
            Un objeto ResultadoComando.
        """

        if not self.git_disponible():
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error="Git no fue encontrado en el sistema.",
                comando=""
            )

        # Construimos siempre el comando utilizando una lista.
        # Nunca utilizamos shell=True.
        comando = [self.ruta_git] + argumentos

        carpeta_trabajo = None

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

            # No utilizamos strip() porque algunos espacios
            # iniciales tienen significado para Git.
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
        """

        return self.ejecutar_git(
            argumentos=["--version"]
        )

    def analizar_repositorio(self, ruta_repositorio):
        """
        Analiza una carpeta para determinar si contiene
        un repositorio Git válido.

        Esta operación solamente consulta información.
        """

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

        if not carpeta.exists():
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="La carpeta indicada no existe."
            )

        if not carpeta.is_dir():
            return EstadoRepositorio(
                es_repositorio=False,
                mensaje="La ruta indicada no corresponde a una carpeta."
            )

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
            rama_actual = ""

        resultado_head = self.ejecutar_git(
            argumentos=[
                "rev-parse",
                "--verify",
                "HEAD"
            ],
            ruta_repositorio=ruta_raiz
        )

        tiene_commits = resultado_head.exitoso

        resultado_remotos = self.ejecutar_git(
            argumentos=["remote"],
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
        Obtiene todos los archivos que tienen cambios.

        Esta operación solamente consulta información.
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

        if not resultado.exitoso:
            return ResultadoCambios(
                exitoso=False,
                error=resultado.error
            )

        if not resultado.salida:
            return ResultadoCambios(
                exitoso=True,
                cambios=[]
            )

        cambios = []

        registros = resultado.salida.split("\0")

        indice = 0

        while indice < len(registros):
            registro = registros[indice]

            if not registro:
                indice += 1
                continue

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
                indice += 1

            descripcion = self._traducir_estado_archivo(
                estado_indice,
                estado_trabajo
            )

            preparado = estado_indice not in (
                " ",
                "?",
                "!"
            )

            cambios.append(
                CambioArchivo(
                    ruta=ruta_archivo,
                    estado_indice=estado_indice,
                    estado_trabajo=estado_trabajo,
                    descripcion=descripcion,
                    preparado=preparado,
                    ruta_anterior=ruta_anterior
                )
            )

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

        Equivale a git add.
        """

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

        rutas_validas, mensaje_error = (
            self._validar_rutas_relativas(
                rutas_archivos
            )
        )

        if mensaje_error:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=mensaje_error,
                comando=""
            )

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

    def quitar_archivos_preparados(
        self,
        ruta_repositorio,
        rutas_archivos
    ):
        """
        Quita uno o varios archivos del área preparada.

        IMPORTANTE:
            Esta operación NO elimina los archivos del disco.

        Si el repositorio ya tiene commits utilizamos:

            git restore --staged

        Si todavía no existe ningún commit utilizamos:

            git rm --cached

        porque todavía no existe HEAD contra el cual restaurar.
        """

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

        rutas_validas, mensaje_error = (
            self._validar_rutas_relativas(
                rutas_archivos
            )
        )

        if mensaje_error:
            return ResultadoComando(
                exitoso=False,
                codigo_salida=-1,
                salida="",
                error=mensaje_error,
                comando=""
            )

        if estado_repositorio.tiene_commits:
            # El repositorio ya tiene HEAD.
            #
            # restore --staged modifica solamente el índice.
            argumentos = [
                "--literal-pathspecs",
                "restore",
                "--staged",
                "--",
            ]

        else:
            # En un repositorio sin commits todavía no existe HEAD.
            #
            # rm --cached quita el archivo del índice pero conserva
            # el archivo físicamente en el disco.
            argumentos = [
                "--literal-pathspecs",
                "rm",
                "--cached",
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
    def _validar_rutas_relativas(rutas_archivos):
        """
        Valida una colección de rutas recibidas desde la interfaz.

        Las rutas deben ser relativas al repositorio.

        Devuelve:
            rutas_validas
            mensaje_error
        """

        if rutas_archivos is None:
            return (
                None,
                "No se indicó ningún archivo."
            )

        rutas_validas = []

        for ruta_archivo in rutas_archivos:

            if ruta_archivo is None:
                return (
                    None,
                    "Se recibió una ruta de archivo inválida."
                )

            ruta_texto = str(
                ruta_archivo
            )

            if not ruta_texto or ruta_texto.isspace():
                return (
                    None,
                    "Se recibió una ruta de archivo vacía."
                )

            ruta_objeto = Path(
                ruta_texto
            )

            # Nunca permitimos rutas absolutas.
            if ruta_objeto.is_absolute():
                return (
                    None,
                    (
                        "Los archivos deben indicarse mediante "
                        "rutas relativas al repositorio."
                    )
                )

            # Evitamos salir del repositorio mediante ..
            if ".." in ruta_objeto.parts:
                return (
                    None,
                    (
                        "La ruta del archivo intenta salir "
                        "del repositorio."
                    )
                )

            # Eliminamos duplicados conservando el orden.
            if ruta_texto not in rutas_validas:
                rutas_validas.append(
                    ruta_texto
                )

        if not rutas_validas:
            return (
                None,
                "No se indicó ningún archivo."
            )

        return (
            rutas_validas,
            ""
        )

    @staticmethod
    def _traducir_estado_archivo(
        estado_indice,
        estado_trabajo
    ):
        """
        Convierte los códigos utilizados por Git
        en una descripción comprensible.
        """

        codigo = estado_indice + estado_trabajo

        if codigo == "??":
            return "Nuevo"

        if codigo == "!!":
            return "Ignorado"

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

        if "R" in codigo:
            return "Renombrado"

        if "C" in codigo:
            return "Copiado"

        if estado_indice == "A":
            if estado_trabajo == "M":
                return "Agregado y modificado después"

            if estado_trabajo == "D":
                return "Agregado y eliminado después"

            return "Agregado y preparado"

        if estado_indice == "D":
            return "Eliminado y preparado"

        if estado_trabajo == "D":
            return "Eliminado"

        if (
            estado_indice == "M"
            and estado_trabajo == "M"
        ):
            return "Modificado, preparado y vuelto a modificar"

        if estado_indice == "M":
            return "Modificado y preparado"

        if estado_trabajo == "M":
            return "Modificado"

        if estado_indice == "T":
            return "Tipo de archivo modificado y preparado"

        if estado_trabajo == "T":
            return "Tipo de archivo modificado"

        return "Cambio detectado"

    @staticmethod
    def _convertir_comando_a_texto(comando):
        """
        Convierte la lista del comando en texto únicamente
        para mostrarla o registrarla.
        """

        return " ".join(
            str(parte)
            for parte in comando
        )
