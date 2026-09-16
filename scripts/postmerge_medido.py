#!/usr/bin/env python3
"""postmerge.py - la suite de integracion sobre la RAMA DESTINO, no sobre el worktree.

Los AC de una feature miden su propio worktree. Por construccion no pueden ver
lo que se rompe cuando dos features conviven: dos migraciones que toman el mismo
numero, una que inserta una fila donde otra fija un conteo exacto, un CHECK que
choca con un vocabulario ampliado. Cada rama verde, la integracion roja.

Este gate corre DESPUES del merge y compara los rojos contra una base tomada
ANTES. El conteo absoluto no sirve como criterio: casi siempre hay deuda roja
tolerada, y exigir cero convierte el gate en algo que se apaga. Lo que importa
es el DELTA: que el merge no haya agregado rojos nuevos.

  # antes de mergear, parado en la rama destino:
  postmerge.py base --repo <ruta> --guardar /tmp/base.json

  # despues del merge:
  postmerge.py check --repo <ruta> --base /tmp/base.json

exit 0 si no hay rojos nuevos; exit 1 si el merge rompio algo; exit 2 si no pudo medir.

Solo acepta stdout de go test -json, con finales de paquetes/tests y evidencia
lateral del exit real mediante postmerge_exec.py (-exec). Base v2 exige esa
evidencia: mismo repo canonico, rama, comando e historial Git; tests
antes medidos deben seguir ejecutandose. Skip/ausencia no es curacion.
--cmd ejecuta shell de confianza: debe preservar JSON, exit de Go y GOFLAGS
instrumentado. No reutilices bases sin evidencia -exec; mide ANTES del merge.
Al verificar el exit NO uses un pipe: 'script | tail' devuelve el status del
tail y te va a mostrar 0 aunque el gate haya salido 1.
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import NoReturn

from postmerge_exec import PROTOCOL, DIRECTORY, ORIGINAL_FLAGS, PREFIX


def no_medicion(motivo: str) -> NoReturn:
    print(f"[!!] no pude medir: {motivo}")
    raise SystemExit(2)


def go_quote(value: str) -> str:
    """quoted.Split de Go NO es shell: no interpreta backslash/escapes."""
    if not any(c.isspace() or c in "\"'" for c in value):
        return value
    for quote in ("'", '"'):
        if quote not in value:
            return quote + value + quote
    no_medicion("ruta de Python/helper no representable en GOFLAGS -exec.")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            no_medicion("registro JSON ambiguo: clave duplicada.")
        result[key] = value
    return result


def leer_registros(directory: pathlib.Path) -> dict:
    records = {}
    for path in directory.iterdir():
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) != 2:
            no_medicion("registro -exec incompleto: falta terminacion real.")
        start, end = [json.loads(line, object_pairs_hook=unique_object) for line in lines]
        identity = path.stem
        if (not re.fullmatch(r"[0-9a-f]{32}", identity) or path.suffix != ".jsonl"
                or not isinstance(start, dict) or not isinstance(end, dict)
                or start.get("protocol") != PROTOCOL or end.get("protocol") != PROTOCOL
                or start.get("id") != identity or end.get("id") != identity
                or start.get("state") != "started" or end.get("state") != "exited"
                or not isinstance(start.get("argv"), list) or not start["argv"]
                or not all(isinstance(a, str) and a for a in start["argv"])
                or not isinstance(start.get("cwd"), str) or not start["cwd"]
                or type(end.get("returncode")) is not int or identity in records):
            no_medicion("registro -exec invalido o ambiguo.")
        records[identity] = end["returncode"]
    return records


def ejecutar(repo: str, cmd: str):
    """Instrumenta por entorno sin reescribir --cmd ni repetir la suite."""
    try:
        with tempfile.TemporaryDirectory(prefix="postmerge-exec-") as directory:
            env = os.environ.copy()
            env[DIRECTORY] = directory
            env[ORIGINAL_FLAGS] = json.dumps(env.get("GOFLAGS"))
            args = [sys.executable, "-B", str(pathlib.Path(__file__).with_name("postmerge_exec.py").resolve())]
            exec_flag = "-exec=" + " ".join(go_quote(arg) for arg in args)
            env["GOFLAGS"] = env.get("GOFLAGS", "") + " " + go_quote(exec_flag)
            result = subprocess.run(cmd, shell=True, cwd=repo, env=env,
                                    capture_output=True, text=True, encoding="utf-8")
            return result, leer_registros(pathlib.Path(directory))
    except (OSError, ValueError, RecursionError) as error:
        no_medicion(f"no se pudo leer la ejecucion/evidencia -exec ({type(error).__name__}).")


def vincular_procesos(stdout: str, stderr: str, records: dict, resultados: dict, paquetes: dict) -> dict:
    # La marca viene del helper, solo da correlacion. El veredicto siempre viene
    # de Action y el exit exclusivamente de wait en el registro lateral.
    seen, processes = set(), {}
    for output, selected in ((stdout, True), (stderr, False)):
        for line in output.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue  # stderr puede ser diagnostico no JSON.
            if not isinstance(event, dict) or event.get("Action") != "output":
                continue
            text = event.get("Output")
            if not isinstance(text, str) or not text.startswith(PREFIX):
                continue
            identity = text[len(PREFIX):].removesuffix("\n")
            package = event.get("Package")
            if (identity not in records or identity in seen or event.get("Test") is not None
                    or not isinstance(package, str) or not package):
                no_medicion("vinculo -exec faltante, repetido o ambiguo.")
            seen.add(identity)
            if selected:
                if package not in paquetes or package in processes:
                    no_medicion("multiples procesos -exec para el mismo paquete o paquete ajeno.")
                processes[package] = records[identity]
    if seen != records.keys():
        no_medicion("registro -exec sin vinculo unico a un stream Go.")
    expected = {p for p, state in paquetes.items() if state != "skip"} | {p for p, _ in resultados}
    if processes.keys() != expected:
        no_medicion("falta evidencia de terminacion real -exec por paquete; no se acepta cache/JSON solo.")
    for p, code in processes.items():
        expected_code = int(any(pkg == p and state == "fail" for (pkg, _), state in resultados.items()))
        if code != expected_code:
            no_medicion(f"exit real del binario {p}: {code}; esperado {expected_code} por sus tests.")
    return processes


def correr(repo: str, cmd: str) -> tuple[dict, dict, dict]:
    print(f"$ (cd {repo}) {cmd}", flush=True)
    r, records = ejecutar(repo, cmd)
    resultados, paquetes = parsear_eventos(r)
    processes = vincular_procesos(r.stdout, r.stderr, records, resultados, paquetes)
    return resultados, paquetes, processes


def parsear_eventos(r) -> tuple[dict, dict]:
    """Solo protocolo JSON. NO es una medicion sin validar tambien -exec."""
    resultados, paquetes = {}, {}
    iniciados, corridos = set(), set()
    for linea in r.stdout.splitlines():
        try:
            evento = json.loads(linea)
        except ValueError:
            no_medicion("stdout no es Go JSON; usa go test -json -count=1.")
        if not isinstance(evento, dict):
            no_medicion("evento Go JSON invalido.")
        accion = evento.get("Action")
        if accion == "build-output":
            continue
        if accion == "build-fail":
            no_medicion("fallo la compilacion; la suite no termino correctamente.")
        paquete, test = evento.get("Package"), evento.get("Test")
        if not isinstance(paquete, str) or not paquete:
            no_medicion("evento sin identidad de paquete.")
        if "Test" in evento and (not isinstance(test, str) or not test):
            no_medicion("evento sin identidad de test.")
        if accion == "output":
            # Output es texto del test, no un resultado ni diagnostico de build.
            continue
        if accion == "start" and test is None and paquete not in iniciados:
            iniciados.add(paquete)
            continue
        if paquete not in iniciados or paquete in paquetes:
            no_medicion(f"paquete sin inicio, repetido o ya finalizado: {paquete}")
        clave = (paquete, test)
        if accion == "run" and test is not None and clave not in corridos:
            corridos.add(clave)
        elif accion in ("pause", "cont", "attr") and clave in corridos and clave not in resultados:
            # attr (Go 1.26) es metadata del test activo, nunca un resultado.
            continue
        elif accion in ("pass", "fail", "skip"):
            if test is None:
                paquetes[paquete] = accion
            elif clave in corridos and clave not in resultados:
                resultados[clave] = accion
            else:
                no_medicion(f"test sin inicio o resultado repetido: {paquete}::{test}")
        else:
            no_medicion(f"evento Go JSON inesperado: {accion}")
    if iniciados != paquetes.keys() or corridos != resultados.keys():
        no_medicion("faltan finales de paquetes o tests; ejecucion incompleta.")
    if not any(estado in ("pass", "fail") for estado in resultados.values()):
        no_medicion("no termino NI UN test no omitido; suite vacia o totalmente skip.")
    fallidos = {p for (p, _), estado in resultados.items() if estado == "fail"}
    if fallidos != {p for p, estado in paquetes.items() if estado == "fail"}:
        no_medicion("fallo de paquete no explicado por tests; build o ejecucion invalidos.")
    if any(paquetes[p] == "skip" and estado != "skip" for (p, _), estado in resultados.items()):
        no_medicion("paquete omitido con resultados contradictorios.")
    if r.returncode != (1 if fallidos else 0):
        no_medicion(f"exit {r.returncode} incompatible con los resultados de Go.")
    return resultados, paquetes


def git(repo: str, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                              text=True, check=True, timeout=30).stdout.strip()
    except (OSError, UnicodeError, subprocess.SubprocessError) as error:
        no_medicion(f"Git no pudo validar el contexto ({type(error).__name__}).")


def leer_base(ruta: str, repo: str, rama: str, sha: str, cmd: str) -> dict:
    try:
        base = json.loads(pathlib.Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as error:
        no_medicion(f"base ausente o ilegible ({type(error).__name__}).")
    if not isinstance(base, dict) or type(base.get("version")) is not int or base["version"] != 2:
        no_medicion("base incompatible: se requiere version 2 tomada ANTES del merge.")
    for campo, valor in (("repo", repo), ("rama", rama), ("cmd", cmd)):
        if base.get(campo) != valor:
            no_medicion(f"base de otro alcance: no coincide {campo}.")
    if not isinstance(base.get("sha"), str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", base["sha"]):
        no_medicion("base sin SHA completo valido.")
    paquetes, registros = base.get("paquetes"), base.get("resultados")
    if not isinstance(paquetes, list) or not paquetes or not all(isinstance(p, str) and p for p in paquetes):
        no_medicion("inventario de paquetes invalido en la base.")
    if len(set(paquetes)) != len(paquetes) or not isinstance(registros, list):
        no_medicion("inventario duplicado o sin resultados en la base.")
    resultados = {}
    for registro in registros:
        if not isinstance(registro, dict):
            no_medicion("resultado invalido en la base.")
        p, t, estado = registro.get("Package"), registro.get("Test"), registro.get("Action")
        if (not isinstance(p, str) or p not in paquetes or not isinstance(t, str) or not t
                or estado not in ("pass", "fail", "skip") or (p, t) in resultados):
            no_medicion("identidad o resultado invalido/duplicado en la base.")
        resultados[p, t] = estado
    if not any(estado in ("pass", "fail") for estado in resultados.values()):
        no_medicion("la base no contiene tests medidos.")
    rojos = sorted([p, t] for (p, t), estado in resultados.items() if estado == "fail")
    if base.get("rojos") != rojos:
        no_medicion("rojos incompatibles con los resultados de la base.")
    evidence = base.get("ejecucion")
    if (not isinstance(evidence, dict) or evidence.get("protocolo") != PROTOCOL
            or not isinstance(evidence.get("finales"), dict)
            or not isinstance(evidence.get("exits"), dict)):
        no_medicion("base sin evidencia de terminacion real: vuelve a medir ANTES del merge.")
    finals, exits = evidence["finales"], evidence["exits"]
    if set(finals) != set(paquetes) or any(s not in ("pass", "fail", "skip") for s in finals.values()):
        no_medicion("finales de procesos invalidos en la base.")
    expected = {p for p, s in finals.items() if s != "skip"} | {p for p, _ in resultados}
    if set(exits) != expected:
        no_medicion("evidencia de procesos incompleta en la base.")
    for p, state in finals.items():
        states = [s for (pkg, _), s in resultados.items() if pkg == p]
        red = "fail" in states
        if ((state == "fail") != red or (state == "skip" and any(s != "skip" for s in states))
                or (p in exits and (type(exits[p]) is not int or exits[p] != int(red)))):
            no_medicion("exit real incompatible con resultados de la base.")
    # La base debe provenir del historial que estamos integrando, no de otra linea.
    git(repo, "merge-base", "--is-ancestor", base["sha"], sha)
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    com = argparse.ArgumentParser(add_help=False)
    com.add_argument("--repo", required=True, help="ruta del repo (la rama destino ya hecha checkout)")
    com.add_argument(
        "--cmd",
        # JSON conserva paquete/test y resultados; -count=1 evita reutilizar cache.
        default="go test -tags integration -count=1 -json ./integration/...",
        help="comando confiable de la suite (stdout Go JSON; go test -json -count=1)",
    )

    b = sub.add_parser("base", parents=[com], help="toma la foto ANTES del merge")
    b.add_argument("--guardar", required=True)

    c = sub.add_parser("check", parents=[com], help="compara DESPUES del merge")
    c.add_argument("--base", required=True)

    a = ap.parse_args()
    repo = str(pathlib.Path(a.repo).expanduser().resolve())
    rama = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    sha = git(repo, "rev-parse", "HEAD")
    print(f"[i]  {repo} en {rama} ({sha})")

    base = leer_base(a.base, repo, rama, sha, a.cmd) if hasattr(a, "base") else None
    resultados, paquetes, procesos = correr(repo, a.cmd)
    if (git(repo, "rev-parse", "--abbrev-ref", "HEAD"), git(repo, "rev-parse", "HEAD")) != (rama, sha):
        no_medicion("la rama o el commit cambiaron durante la suite.")
    rojos = {t for t, estado in resultados.items() if estado == "fail"}

    if hasattr(a, "guardar"):
        try:
            pathlib.Path(a.guardar).write_text(
                json.dumps({"version": 2, "repo": repo, "rama": rama, "sha": sha, "cmd": a.cmd,
                            "rojos": sorted(rojos), "paquetes": sorted(paquetes),
                            "ejecucion": {"protocolo": PROTOCOL, "finales": paquetes, "exits": procesos},
                            "resultados": [{"Package": p, "Test": t, "Action": estado}
                                           for (p, t), estado in sorted(resultados.items())]}, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            no_medicion(f"no se pudo guardar la base ({type(error).__name__}).")
        print(f"[ok] base guardada en {a.guardar}: {len(rojos)} rojo(s) preexistente(s)")
        for p, t in sorted(rojos):
            print(f"     - {p}::{t}")
        return 0

    assert base is not None
    medidos_antes = {(r["Package"], r["Test"]) for r in base["resultados"] if r["Action"] != "skip"}
    medidos_ahora = {t for t, estado in resultados.items() if estado != "skip"}
    faltantes = medidos_antes - medidos_ahora
    if set(base["paquetes"]) - paquetes.keys() or faltantes:
        detalle = ", ".join(f"{p}::{t}" for p, t in sorted(faltantes))
        no_medicion(f"alcance incompleto: faltan paquetes/tests antes medidos o ahora omitidos. {detalle}")
    previos = {tuple(t) for t in base["rojos"]}
    nuevos = rojos - previos
    curados = previos - rojos

    print()
    print(f"[i]  base: {base['sha']} ({len(previos)} rojo(s)) -> ahora: {sha} ({len(rojos)} rojo(s))")
    for p, t in sorted(curados):
        print(f"[ok] se curo: {p}::{t}")

    if not nuevos:
        print("[ok] el merge no agrego rojos nuevos.")
        if previos & rojos:
            print("[i]  OJO: la deuda preexistente sigue ahi y este gate NO la perdona,")
            print("     solo la separa de lo que rompio este merge. Debe estar fichada.")
        return 0

    print(f"[!!] el merge agrego {len(nuevos)} rojo(s) que NINGUN AC de feature vio:")
    for p, t in sorted(nuevos):
        print(f"     - {p}::{t}")
    print()
    print("     Cada rama puede estar verde por separado y romperse al convivir.")
    print("     Ficha el choque; no lo tapes bajando la asercion que lo detecto.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
