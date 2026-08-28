"""
Pruebas de ServicioRemotoReservas (Bloque D).

Usan TemporaryDirectory y repositorios Git bare LOCALES temporales
como remoto. No usan internet, no tocan APPDATA real, no tocan el
repositorio Oracle productivo y no modifican Git global/system
(GIT_CONFIG_GLOBAL temporal + GIT_CONFIG_NOSYSTEM=1).

Cobertura (16.2):

1.  ref SHA-256 completo y determinista;
2.  hash cambia con project_uuid;
3.  hash cambia con clave;
4.  Fetch usa refspec exacto;
5.  ref inexistente -> libre;
6.  commit invalido -> NO_VERIFICABLE;
7.  tree sin reserva.json -> NO_VERIFICABLE;
8.  tree con archivo extra -> NO_VERIFICABLE;
9.  reserva.json no blob normal -> NO_VERIFICABLE;
10. JSON invalido -> NO_VERIFICABLE;
11. payload con project_uuid incorrecto -> NO_VERIFICABLE;
12. payload con clave incorrecta -> NO_VERIFICABLE;
13. hash-object/mktree/commit-tree construyen commit;
14. primera reserva sin parent;
15. siguiente estado con parent exacto;
16. author tecnico fijo;
17. committer tecnico fijo;
18. no aparece user.email personal;
19. Push usa source OID + ref exacta;
20. Push no contiene '+', '--force' ni '--force-with-lease';
21. no se crea rama local;
22. no se usa update-ref normal;
23. timeout controlado;
24. OSError controlado.

REV3 §8: payload invalido -> crear_commit_reserva False y
   _ejecutar_git NO llamado (cero comandos Git de escritura).
REV3 §11: aislamiento Git desde ANTES del primer comando del test
   (GIT_CONFIG_GLOBAL temporal + GIT_CONFIG_NOSYSTEM=1).
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from modelos_reservas import (
    ClasificacionReservaObservada,
    EstadoReservaPersistido,
    ReservaPayloadV1,
    ahora_utc,
    calcular_ref_reserva,
    formatear_timestamp_utc,
)
from servicio_remoto_reservas import (
    IDENTIDAD_TECNICA_RESERVAS,
    NOMBRE_ARCHIVO_RESERVA,
    REFSPEC_RESERVAS_V1,
    ResultadoLecturaReserva,
    ServicioRemotoReservas,
)


def _uuid4():
    return str(uuid.uuid4())


def _proyecto_uuid():
    return _uuid4()


def _clave():
    return "PACKAGE|FINI004"


def _payload(project_uuid, clave_objeto, estado="ACTIVA", id_cliente=None):
    """Payload V1 valido con timestamps coherentes."""

    ahora = ahora_utc()
    if estado == "LIBERADA":
        vencimiento = ahora
    else:
        vencimiento = ahora + __import__("datetime").timedelta(
            seconds=1800
        )
    return ReservaPayloadV1(
        format_version=1,
        operation_id=_uuid4(),
        project_uuid=project_uuid,
        clave_objeto=clave_objeto,
        estado=EstadoReservaPersistido(estado),
        id_cliente=id_cliente if id_cliente else _uuid4(),
        alias="equipo",
        hostname="pc-1",
        user_name="ana",
        inicio=formatear_timestamp_utc(ahora),
        heartbeat=formatear_timestamp_utc(ahora),
        vencimiento=formatear_timestamp_utc(vencimiento),
        rama_local="",
        rutas=("Paquetes/FINI004.pls",),
    )


class _BaseServicioRemoto(unittest.TestCase):
    """Base con backend bare temporal y remoto local."""

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.remoto = self.base / "remoto.git"
        self.backend = self.base / "backend.git"

        # Aislamiento de configuracion Git desde ANTES del primer
        # comando Git del test: GIT_CONFIG_GLOBAL temporal y
        # GIT_CONFIG_NOSYSTEM=1 activos en os.environ, de modo que
        # git init/remote add/config, los fixtures y TODAS las
        # llamadas al servicio hereden ese entorno aislado. Se
        # restaura al terminar la prueba.
        self.global_temp = self.base / "config_global_temporal"
        self.global_temp.write_text("", encoding="utf-8")
        parche_entorno = mock.patch.dict(
            os.environ,
            {
                "GIT_CONFIG_GLOBAL": str(self.global_temp),
                "GIT_CONFIG_NOSYSTEM": "1",
            },
        )
        parche_entorno.start()
        self.addCleanup(parche_entorno.stop)
        self.entorno = dict(os.environ)

        # Remoto local (file protocol), sin red.
        subprocess.run(
            ["git", "init", "--bare", str(self.remoto)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
            check=True,
            env=self.entorno,
        )
        # Backend cache local.
        subprocess.run(
            ["git", "init", "--bare", str(self.backend)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
            check=True,
            env=self.entorno,
        )
        subprocess.run(
            ["git", "-C", str(self.backend),
             "remote", "add", "origin", str(self.remoto)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
            check=True,
            env=self.entorno,
        )
        subprocess.run(
            ["git", "-C", str(self.backend),
             "config", "--replace-all",
             "remote.origin.fetch", REFSPEC_RESERVAS_V1],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
            check=True,
            env=self.entorno,
        )

        self.servicio = ServicioRemotoReservas(
            ruta_backend=str(self.backend)
        )

    def tearDown(self):
        self.temporal.cleanup()

    def _git_remoto(self, *argumentos):
        resultado = subprocess.run(
            ["git", "-C", str(self.remoto)] + list(argumentos),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
            env=self.entorno,
        )
        return resultado

    def _git_backend(self, *argumentos, entorno=None):
        resultado = subprocess.run(
            ["git", "-C", str(self.backend)] + list(argumentos),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
            env=entorno if entorno is not None else self.entorno,
        )
        return resultado


class TestRefSha256(_BaseServicioRemoto):
    """16.2.1-3: ref SHA-256 completo, determinista y sensible."""

    def test_ref_completo_determinista(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        r1 = self.servicio._ref_remoto(proyecto, clave)
        r2 = self.servicio._ref_remoto(proyecto, clave)
        self.assertEqual(r1, r2)
        self.assertTrue(r1.startswith(
            "refs/remotes/origin/gestorgit-reservas/"
        ))
        hash_ref = r1.rsplit("/", 1)[1]
        self.assertEqual(len(hash_ref), 64)

    def test_hash_cambia_con_project_uuid(self):
        clave = _clave()
        h1 = calcular_ref_reserva(_proyecto_uuid(), clave)
        h2 = calcular_ref_reserva(_proyecto_uuid(), clave)
        self.assertNotEqual(h1, h2)

    def test_hash_cambia_con_clave(self):
        proyecto = _proyecto_uuid()
        h1 = calcular_ref_reserva(proyecto, "PACKAGE|FINI004")
        h2 = calcular_ref_reserva(proyecto, "PACKAGE|FINI005")
        self.assertNotEqual(h1, h2)


class TestFetchRefspec(_BaseServicioRemoto):
    """16.2.4: Fetch usa refspec exacto."""

    def test_fetch_usa_refspec_exacto(self):
        with mock.patch.object(
            self.servicio, "_ejecutar_git", wraps=self.servicio._ejecutar_git
        ) as ejecutar:
            ok, _mensaje = self.servicio.fetch_reservas()
            self.assertTrue(ok)
            llamadas = [
                c.args[0] for c in ejecutar.call_args_list
                if c.args and "fetch" in c.args[0]
            ]
            self.assertTrue(any(
                "fetch" in llamada and REFSPEC_RESERVAS_V1 in llamada
                for llamada in llamadas
            ))

    def test_fetch_refspec_contiene_prune(self):
        with mock.patch.object(
            self.servicio, "_ejecutar_git", wraps=self.servicio._ejecutar_git
        ) as ejecutar:
            self.servicio.fetch_reservas()
            llamadas = [
                c.args[0] for c in ejecutar.call_args_list
                if c.args and "fetch" in c.args[0]
            ]
            self.assertTrue(any(
                "--prune" in llamada for llamada in llamadas
            ))


class TestLecturaHead(_BaseServicioRemoto):
    """16.2.5-12: lectura y validacion del head."""

    def test_ref_inexistente_libre(self):
        proyecto = _proyecto_uuid()
        lectura = self.servicio.leer_head_reserva(
            proyecto, _clave(), _uuid4()
        )
        self.assertTrue(lectura.exitoso)
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.LIBRE,
        )
        self.assertFalse(lectura.head_existe)
        self.assertEqual(lectura.parent, "")

    def test_commit_invalido_no_verificable(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        ref_heads = (
            "refs/heads/gestorgit-reservas/"
            + calcular_ref_reserva(proyecto, clave)
        )
        # Crear un commit cuyo tree NO tenga reserva.json (tree vacio)
        # con plumbing, porque el remoto es bare y no admite
        # `git commit` con arbol de trabajo.
        import subprocess as sp

        identidad = dict(os.environ)
        identidad.update(
            {
                "GIT_AUTHOR_NAME": "T",
                "GIT_AUTHOR_EMAIL": "t@x",
                "GIT_COMMITTER_NAME": "T",
                "GIT_COMMITTER_EMAIL": "t@x",
            }
        )
        tree_vacio = sp.run(
            ["git", "-C", str(self.remoto), "mktree"],
            input="",
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        oid = sp.run(
            ["git", "-C", str(self.remoto), "commit-tree", tree_vacio,
             "-m", "no es reserva"],
            capture_output=True, text=True, check=True,
            env=identidad,
        ).stdout.strip()
        sp.run(
            ["git", "-C", str(self.remoto), "update-ref",
             ref_heads, oid],
            capture_output=True, check=True,
        )
        self.servicio.fetch_reservas()
        lectura = self.servicio.leer_head_reserva(
            proyecto, clave, _uuid4()
        )
        self.assertFalse(lectura.exitoso)
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )

    def _publicar_commit_arbitrario(self, ref_heads, contenido, modo="100644"):
        """Publica un commit con un solo archivo reserva.json en el remoto."""

        import subprocess as sp

        sp.run(
            ["git", "-C", str(self.remoto), "config", "user.name", "T"],
            capture_output=True, check=True,
        )
        sp.run(
            ["git", "-C", str(self.remoto), "config", "user.email", "t@x"],
            capture_output=True, check=True,
        )
        blob = sp.run(
            ["git", "-C", str(self.remoto), "hash-object", "-w", "--stdin"],
            input=contenido,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        tree = sp.run(
            ["git", "-C", str(self.remoto), "mktree"],
            input=f"{modo} blob {blob}\t{NOMBRE_ARCHIVO_RESERVA}\n",
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        commit = sp.run(
            ["git", "-C", str(self.remoto), "commit-tree", tree,
             "-m", "arbitrario"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        sp.run(
            ["git", "-C", str(self.remoto), "update-ref",
             ref_heads, commit],
            capture_output=True, check=True,
        )
        return commit

    def test_tree_sin_reserva_json(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        ref_heads = (
            "refs/heads/gestorgit-reservas/"
            + calcular_ref_reserva(proyecto, clave)
        )
        # Tree vacio (sin reserva.json).
        import subprocess as sp

        sp.run(
            ["git", "-C", str(self.remoto), "config", "user.name", "T"],
            capture_output=True, check=True,
        )
        sp.run(
            ["git", "-C", str(self.remoto), "config", "user.email", "t@x"],
            capture_output=True, check=True,
        )
        tree_vacio = sp.run(
            ["git", "-C", str(self.remoto), "mktree"],
            input="",
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        commit = sp.run(
            ["git", "-C", str(self.remoto), "commit-tree", tree_vacio,
             "-m", "tree vacio"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        sp.run(
            ["git", "-C", str(self.remoto), "update-ref",
             ref_heads, commit],
            capture_output=True, check=True,
        )
        self.servicio.fetch_reservas()
        lectura = self.servicio.leer_head_reserva(
            proyecto, clave, _uuid4()
        )
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )

    def test_tree_con_archivo_extra(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        ref_heads = (
            "refs/heads/gestorgit-reservas/"
            + calcular_ref_reserva(proyecto, clave)
        )
        # Tree con dos archivos: reserva.json + extra.txt.
        import subprocess as sp

        sp.run(
            ["git", "-C", str(self.remoto), "config", "user.name", "T"],
            capture_output=True, check=True,
        )
        sp.run(
            ["git", "-C", str(self.remoto), "config", "user.email", "t@x"],
            capture_output=True, check=True,
        )
        blob = sp.run(
            ["git", "-C", str(self.remoto), "hash-object", "-w", "--stdin"],
            input='{"a":1}',
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        blob2 = sp.run(
            ["git", "-C", str(self.remoto), "hash-object", "-w", "--stdin"],
            input="extra",
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        entrada = (
            f"100644 blob {blob}\t{NOMBRE_ARCHIVO_RESERVA}\n"
            f"100644 blob {blob2}\textra.txt\n"
        )
        tree = sp.run(
            ["git", "-C", str(self.remoto), "mktree"],
            input=entrada,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        commit = sp.run(
            ["git", "-C", str(self.remoto), "commit-tree", tree,
             "-m", "tree con extra"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        sp.run(
            ["git", "-C", str(self.remoto), "update-ref",
             ref_heads, commit],
            capture_output=True, check=True,
        )
        self.servicio.fetch_reservas()
        lectura = self.servicio.leer_head_reserva(
            proyecto, clave, _uuid4()
        )
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )

    def test_reserva_json_no_blob_normal(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        ref_heads = (
            "refs/heads/gestorgit-reservas/"
            + calcular_ref_reserva(proyecto, clave)
        )
        self._publicar_commit_arbitrario(
            ref_heads, '{"a":1}', modo="100755"
        )
        self.servicio.fetch_reservas()
        lectura = self.servicio.leer_head_reserva(
            proyecto, clave, _uuid4()
        )
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )

    def test_json_invalido(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        ref_heads = (
            "refs/heads/gestorgit-reservas/"
            + calcular_ref_reserva(proyecto, clave)
        )
        self._publicar_commit_arbitrario(
            ref_heads, "esto no es json"
        )
        self.servicio.fetch_reservas()
        lectura = self.servicio.leer_head_reserva(
            proyecto, clave, _uuid4()
        )
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )

    def test_payload_project_uuid_incorrecto(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(_proyecto_uuid(), clave)  # otro uuid
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        self.servicio.publicar_reserva(oid, proyecto, clave)
        self.servicio.fetch_reservas()
        lectura = self.servicio.leer_head_reserva(
            proyecto, clave, _uuid4()
        )
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )

    def test_payload_clave_incorrecta(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, "PACKAGE|FINI005")
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        self.servicio.publicar_reserva(oid, proyecto, clave)
        self.servicio.fetch_reservas()
        lectura = self.servicio.leer_head_reserva(
            proyecto, clave, _uuid4()
        )
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )

    def test_payload_activa_clasificacion_por_id_cliente(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        id_cliente = _uuid4()
        payload = _payload(proyecto, clave, id_cliente=id_cliente)
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        self.servicio.publicar_reserva(oid, proyecto, clave)
        self.servicio.fetch_reservas()
        lectura = self.servicio.leer_head_reserva(
            proyecto, clave, id_cliente
        )
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_MI,
        )
        lectura_otro = self.servicio.leer_head_reserva(
            proyecto, clave, _uuid4()
        )
        self.assertIs(
            lectura_otro.clasificacion,
            ClasificacionReservaObservada.RESERVADO_POR_OTRO,
        )

    def test_liberada_se_interpreta_libre(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(
            proyecto, clave, estado="LIBERADA"
        )
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        self.servicio.publicar_reserva(oid, proyecto, clave)
        self.servicio.fetch_reservas()
        lectura = self.servicio.leer_head_reserva(
            proyecto, clave, _uuid4()
        )
        self.assertTrue(lectura.exitoso)
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.LIBRE,
        )
        self.assertTrue(lectura.head_existe)
        self.assertIsNotNone(lectura.payload)


class TestPlumbing(_BaseServicioRemoto):
    """16.2.13-18: construccion de commits tecnicos."""

    def test_construye_commit_con_reserva_json(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, clave)
        ok, oid, mensaje, error = self.servicio.crear_commit_reserva(
            payload
        )
        self.assertTrue(ok, error)
        self.assertTrue(oid)
        tipo = self._git_backend("cat-file", "-t", oid)
        self.assertEqual(tipo.stdout.strip(), "commit")

    def test_primera_reserva_sin_parent(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, clave)
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        padres = self._git_backend("rev-list", "--parents", "-n", "1", oid)
        lineas = [l for l in padres.stdout.splitlines() if l.strip()]
        # Solo el propio oid, sin parent.
        self.assertEqual(len(lineas[0].split()), 1)

    def test_siguiente_estado_con_parent_exacto(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload1 = _payload(proyecto, clave)
        ok1, oid1, _m, _e = self.servicio.crear_commit_reserva(payload1)
        self.assertTrue(ok1)
        payload2 = _payload(proyecto, clave, estado="LIBERADA")
        ok2, oid2, _m, _e = self.servicio.crear_commit_reserva(
            payload2, parent_oid=oid1
        )
        self.assertTrue(ok2)
        padres = self._git_backend("rev-list", "--parents", "-n", "1", oid2)
        lineas = [l for l in padres.stdout.splitlines() if l.strip()]
        self.assertEqual(lineas[0].split(), [oid2, oid1])

    def test_author_tecnico_fijo(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, clave)
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        salida = self._git_backend("cat-file", "commit", oid)
        self.assertIn(
            "author GestorGit Reservas "
            "<reservas@gestorgit.invalid>",
            salida.stdout,
        )

    def test_committer_tecnico_fijo(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, clave)
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        salida = self._git_backend("cat-file", "commit", oid)
        self.assertIn(
            "committer GestorGit Reservas "
            "<reservas@gestorgit.invalid>",
            salida.stdout,
        )

    def test_no_aparece_user_email_personal(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, clave)
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        salida = self._git_backend("cat-file", "commit", oid)
        self.assertNotIn("user.email", salida.stdout)
        self.assertNotIn("victor", salida.stdout.lower())

    def test_tree_exacto_reserva_json_sin_cr(self):
        """
        REV2 §9: el tree publicado contiene exactamente
        100644 blob <oid> reserva.json, sin CR residual en el
        nombre (la entrada binaria de mktree no sufre la
        traduccion \n -> \r\n de Windows).
        """

        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, clave)
        ok, oid_commit, _m, _e = self.servicio.crear_commit_reserva(
            payload
        )
        self.assertTrue(ok)
        salida = self._git_backend(
            "ls-tree", oid_commit
        )
        lineas = [l for l in salida.stdout.splitlines() if l.strip()]
        self.assertEqual(len(lineas), 1)
        modo_tipo_oid, nombre = lineas[0].split("\t", 1)
        self.assertEqual(nombre, "reserva.json")
        self.assertFalse(nombre.startswith('"'))
        modo, tipo, oid_blob = modo_tipo_oid.split()
        self.assertEqual(modo, "100644")
        self.assertEqual(tipo, "blob")
        self.assertEqual(len(oid_blob), 40)
        self.assertNotIn("\r", salida.stdout)

    def test_blob_coincide_con_serializacion_exacta(self):
        """
        El blob publicado es exactamente la serializacion V1:
        UTF-8, sort_keys, separadores compactos, newline final LF
        y sin CR.
        """

        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, clave)
        ok, oid_commit, _m, _e = self.servicio.crear_commit_reserva(
            payload
        )
        self.assertTrue(ok)
        salida = self._git_backend("ls-tree", oid_commit)
        oid_blob = salida.stdout.split()[2]
        # Lectura BINARIA del blob: comparacion byte a byte contra la
        # serializacion V1, sin traducciones de newline del modo texto.
        bruto = subprocess.run(
            ["git", "-C", str(self.backend),
             "cat-file", "blob", oid_blob],
            capture_output=True, timeout=30, shell=False, check=True,
        ).stdout
        self.assertEqual(bruto, payload.serializar().encode("utf-8"))


class TestValidacionFailSafePreGit(_BaseServicioRemoto):
    """REV3 §8: payload invalido -> cero comandos Git de escritura.

    crear_commit_reserva debe validar estructuralmente el payload
    ANTES del primer hash-object: si el payload no cumple V1,
    _ejecutar_git no se llama ni una sola vez.
    """

    def _probar_payload_invalido(self, payload_invalido):
        with mock.patch.object(
            self.servicio, "_ejecutar_git",
            side_effect=AssertionError(
                "no debe ejecutar Git con payload invalido"
            ),
        ) as ejecutar:
            ok, _oid, mensaje, _error = (
                self.servicio.crear_commit_reserva(
                    payload_invalido
                )
            )
            ejecutar.assert_not_called()
        self.assertFalse(ok)
        self.assertTrue(mensaje)

    def test_operation_id_invalido(self):
        payload = _payload(_proyecto_uuid(), _clave())
        payload.operation_id = "op-invalido"
        self._probar_payload_invalido(payload)

    def test_id_cliente_invalido(self):
        payload = _payload(_proyecto_uuid(), _clave())
        payload.id_cliente = "ana"
        self._probar_payload_invalido(payload)

    def test_relacion_temporal_ttl_invalido(self):
        payload = _payload(_proyecto_uuid(), _clave())
        payload.vencimiento = payload.heartbeat  # TTL 0
        self._probar_payload_invalido(payload)

    def test_timestamp_invalido(self):
        payload = _payload(_proyecto_uuid(), _clave())
        payload.inicio = "2026-08-27 10:00:00"
        self._probar_payload_invalido(payload)

    def test_ruta_invalida(self):
        payload = _payload(_proyecto_uuid(), _clave())
        payload.rutas = ("../fuera.pls",)
        self._probar_payload_invalido(payload)


class TestPush(_BaseServicioRemoto):
    """16.2.19-22: Push normal, sin force, sin ramas/update-ref."""

    def test_push_publica_en_ref_exacta(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, clave)
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        publicacion = self.servicio.publicar_reserva(
            oid, proyecto, clave
        )
        self.assertTrue(publicacion.exitoso, publicacion.error)
        ref_heads = (
            "refs/heads/gestorgit-reservas/"
            + calcular_ref_reserva(proyecto, clave)
        )
        # En el remoto debe existir la ref con el OID.
        resultado = self._git_remoto("show-ref", ref_heads)
        self.assertIn(oid, resultado.stdout)

    def test_push_sin_force(self):
        with mock.patch.object(
            self.servicio, "_ejecutar_git", wraps=self.servicio._ejecutar_git
        ) as ejecutar:
            proyecto = _proyecto_uuid()
            clave = _clave()
            payload = _payload(proyecto, clave)
            ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
            self.assertTrue(ok)
            publicacion = self.servicio.publicar_reserva(
                oid, proyecto, clave
            )
            self.assertTrue(publicacion.exitoso)
            llamadas = [
                c.args[0] for c in ejecutar.call_args_list
                if c.args and "push" in c.args[0]
            ]
            self.assertTrue(llamadas)
            for llamada in llamadas:
                self.assertNotIn("+", llamada)
                self.assertNotIn("--force", llamada)
                self.assertNotIn("--force-with-lease", llamada)

    def test_no_se_crea_rama_local(self):
        proyecto = _proyecto_uuid()
        clave = _clave()
        payload = _payload(proyecto, clave)
        ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
        self.assertTrue(ok)
        self.servicio.publicar_reserva(oid, proyecto, clave)
        self.servicio.fetch_reservas()
        # Ninguna rama LOCAL por objeto (refs/heads): la arquitectura
        # solo admite la ref remote-tracking
        # refs/remotes/origin/gestorgit-reservas/<hash>.
        heads = self._git_backend("for-each-ref", "refs/heads")
        self.assertNotIn("gestorgit-reservas", heads.stdout)
        remoto_tracking = self._git_backend(
            "for-each-ref",
            "refs/remotes/origin/gestorgit-reservas",
        )
        self.assertIn(
            calcular_ref_reserva(proyecto, clave), remoto_tracking.stdout
        )

    def test_no_se_usa_update_ref_normal(self):
        with mock.patch.object(
            self.servicio, "_ejecutar_git", wraps=self.servicio._ejecutar_git
        ) as ejecutar:
            proyecto = _proyecto_uuid()
            clave = _clave()
            payload = _payload(proyecto, clave)
            ok, oid, _m, _e = self.servicio.crear_commit_reserva(payload)
            self.assertTrue(ok)
            self.servicio.publicar_reserva(oid, proyecto, clave)
            llamadas = [
                c.args[0] for c in ejecutar.call_args_list
                if c.args
            ]
            for llamada in llamadas:
                self.assertNotIn("update-ref", llamada)


class TestErroresControlados(_BaseServicioRemoto):
    """16.2.23-24: timeout y OSError controlados."""

    def test_timeout_controlado(self):
        with mock.patch.object(
            self.servicio, "_ejecutar_git", return_value=(
                False, "", "El comando supero el tiempo maximo de 1 segundos.", -1
            )
        ):
            ok, mensaje = self.servicio.fetch_reservas()
            self.assertFalse(ok)
            self.assertIn("tiempo maximo", mensaje)

    def test_oserror_controlado(self):
        with mock.patch.object(
            self.servicio, "_ejecutar_git", side_effect=OSError("boom")
        ):
            # El servicio no debe propagar: pero como _ejecutar_git
            # es la frontera, simulamos un fallo interno controlado
            # verificando que la API publica no lanza.
            try:
                self.servicio.fetch_reservas()
            except OSError:
                self.fail("OSError se propago desde la API publica")

    def test_entrada_invalida_no_verificable(self):
        lectura = self.servicio.leer_head_reserva(
            "no-uuid", _clave(), _uuid4()
        )
        self.assertFalse(lectura.exitoso)
        self.assertIs(
            lectura.clasificacion,
            ClasificacionReservaObservada.NO_VERIFICABLE,
        )


if __name__ == "__main__":
    unittest.main()
