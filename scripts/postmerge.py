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

Probado en los tres caminos contra un caso real (realestate, ms-tenant-service):
  - base 8c82d68 pre-merge: 1434 tests, 5 rojos (deuda F101) -> exit 0
  - check a7a60a5 post-merge: 1487 tests, 10 rojos -> 5 nuevos, exit 1
  - suite sin '-v' (sin evidencia de ejecucion) -> exit 2, se niega a opinar
Al verificar el exit NO uses un pipe: 'script | tail' devuelve el status del
tail y te va a mostrar 0 aunque el gate haya salido 1.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

RE_FAIL = re.compile(r"^\s*--- FAIL: (\S+)", re.M)
RE_RUN = re.compile(r"^\s*=== RUN", re.M)
RE_OK = re.compile(r"^ok\s+\S+", re.M)
RE_OK_NO_TESTS = re.compile(r"^ok\s+\S+.*\[no tests to run\]", re.M)


def correr(repo: str, cmd: str) -> tuple[set, str]:
    """Corre la suite y devuelve (tests rojos, salida cruda)."""
    print(f"$ (cd {repo}) {cmd}", flush=True)
    r = subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, text=True)
    out = r.stdout + r.stderr
    rojos = set(RE_FAIL.findall(out))
    corridos = len(RE_RUN.findall(out))
    oks = len(RE_OK.findall(out))
    oks_sin_tests = len(RE_OK_NO_TESTS.findall(out))
    oks_con_tests = oks - oks_sin_tests
    # Un 'no tests to run' sale 0 y no es verde: exigimos evidencia POSITIVA.
    if corridos == 0 and oks_con_tests == 0:
        print("[!!] la suite no reporto NI UN '=== RUN' ni un 'ok <paquete>' con tests ejecutados.")
        print("     Eso no es verde: es una suite que no corrio. Revisa el comando.")
        sys.exit(2)
    print(f"[i]  {corridos} '=== RUN', {oks_con_tests} paquete(s) ok con tests, {oks_sin_tests} paquete(s) sin tests, {len(rojos)} rojo(s) top-level")
    return rojos, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    com = argparse.ArgumentParser(add_help=False)
    com.add_argument("--repo", required=True, help="ruta del repo (la rama destino ya hecha checkout)")
    com.add_argument(
        "--cmd",
        # -v es OBLIGATORIO en el default: sin el, Go no imprime '=== RUN', y si la
        # suite falla tampoco imprime 'ok <paquete>'. Sin ninguna de las dos senales
        # el gate no puede distinguir "todo bien" de "no corrio nada" y se niega a
        # opinar. Si cambias este comando, conserva la evidencia positiva.
        default="go test -tags integration -count=1 -v ./integration/...",
        help="comando de la suite de integracion (debe emitir evidencia de ejecucion: -v en Go)",
    )

    b = sub.add_parser("base", parents=[com], help="toma la foto ANTES del merge")
    b.add_argument("--guardar", required=True)

    c = sub.add_parser("check", parents=[com], help="compara DESPUES del merge")
    c.add_argument("--base", required=True)

    a = ap.parse_args()
    repo = str(pathlib.Path(a.repo).expanduser())
    rama = subprocess.run(
        "git rev-parse --abbrev-ref HEAD", shell=True, cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    sha = subprocess.run(
        "git rev-parse --short HEAD", shell=True, cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    print(f"[i]  {repo} en {rama} ({sha})")

    rojos, _ = correr(repo, a.cmd)

    if hasattr(a, "guardar"):
        pathlib.Path(a.guardar).write_text(
            json.dumps({"repo": repo, "rama": rama, "sha": sha, "rojos": sorted(rojos)}, indent=2),
            encoding="utf-8",
        )
        print(f"[ok] base guardada en {a.guardar}: {len(rojos)} rojo(s) preexistente(s)")
        for t in sorted(rojos):
            print(f"     - {t}")
        return 0

    base = json.loads(pathlib.Path(a.base).read_text(encoding="utf-8"))
    previos = set(base["rojos"])
    nuevos = rojos - previos
    curados = previos - rojos

    print()
    print(f"[i]  base: {base['sha']} ({len(previos)} rojo(s)) -> ahora: {sha} ({len(rojos)} rojo(s))")
    for t in sorted(curados):
        print(f"[ok] se curo: {t}")

    if not nuevos:
        print("[ok] el merge no agrego rojos nuevos.")
        if previos:
            print("[i]  OJO: la deuda preexistente sigue ahi y este gate NO la perdona,")
            print("     solo la separa de lo que rompio este merge. Debe estar fichada.")
        return 0

    print(f"[!!] el merge agrego {len(nuevos)} rojo(s) que NINGUN AC de feature vio:")
    for t in sorted(nuevos):
        print(f"     - {t}")
    print()
    print("     Cada rama puede estar verde por separado y romperse al convivir.")
    print("     Ficha el choque; no lo tapes bajando la asercion que lo detecto.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
