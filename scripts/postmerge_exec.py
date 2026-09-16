"""Helper privado Go -exec: una ejecucion, evidencia de wait fuera de stdout.

No ejecutarlo a mano. El gate crea un directorio nuevo y lo pasa por entorno.
La marca aleatoria SOLO vincula este proceso al Package asignado por Go; no
transporta resultados ni exit codes. No se deduce ningun estado de los logs.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

PROTOCOL = "go-exec-wait-v1"
DIRECTORY = "POSTMERGE_EXEC_DIR"
ORIGINAL_FLAGS = "POSTMERGE_ORIGINAL_GOFLAGS"
PREFIX = "postmerge-exec:"


def main():
    directory = Path(os.environ[DIRECTORY])
    identity = uuid.uuid4().hex
    record = directory / (identity + ".jsonl")
    # Crear antes de lanzar: crash/kill/spawn fallido deja registro incompleto.
    with record.open("x", encoding="utf-8") as log:
        start = {"protocol": PROTOCOL, "id": identity, "state": "started",
                 "argv": sys.argv[1:], "cwd": os.getcwd()}
        log.write(json.dumps(start) + "\n")
        log.flush()
        os.fsync(log.fileno())
        print(PREFIX + identity, flush=True)
        env = os.environ.copy()
        env.pop(DIRECTORY)
        original = json.loads(env.pop(ORIGINAL_FLAGS))
        if original is None:
            env.pop("GOFLAGS", None)
        else:
            env["GOFLAGS"] = original
        # Heredar streams sin interpretar texto. wait es del binario, no de Go.
        process = subprocess.Popen(sys.argv[1:], env=env)
        code = process.wait()
        log.write(json.dumps({"protocol": PROTOCOL, "id": identity,
                              "state": "exited", "returncode": code}) + "\n")
        log.flush()
        os.fsync(log.fileno())
    # Go solo necesita exito/fallo; el codigo original (incluida senal) esta arriba.
    return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
