"""Bajas de tests declaradas: la unica ausencia que acepta la medicion postmerge.

Una feature que retira codigo borra tambien los tests que solo lo certificaban.
La medicion postmerge lo ve como cobertura perdida y bloquea: un test de la base
que ya no corre es justo la senal de un skip, un build tag o un paquete que dejo
de compilar. Por eso la baja no se toma de palabra. Cada test declarado debe:

  - haberse medido en la base y no medirse en el destino;
  - tener su declaracion presente en base_sha y AUSENTE en la fuente y en el
    destino: lo borro la feature. Un build tag, un skip o un todo dejan la
    declaracion en su lugar y siguen bloqueando.

En destinos Go se declaran tests de primer nivel `<paquete>::<TestX>`; sus
subtests caen con ellos, y su `func TestX(` se busca en el directorio del
paquete. Un paquete entero solo puede desaparecer si tenia tests medidos y TODOS
se retiran.

En destinos FRONTEND (Angular22/Vitest4 y node:test) se declara el id EXACTO que
mide el runner, `[<proyecto>, <archivo>, <nombre completo>]`, y la declaracion se
busca en el propio spec: una llamada it/test -- con cualquier modificador -- cuyo
titulo literal sea el titulo hoja del nombre medido. El titulo hoja se resuelve
probando que sufijos del nombre completo declara el archivo en base_sha, sin
suponer un separador entre describe e it, y debe ser unico. Ademas el review
sellado tiene que nombrar ese titulo hoja Y la ruta del spec.

Lo que falte sin baja declarada sigue bloqueando exactamente como antes
(postmerge_medido.sin_baja para Go, postmerge_frontend.compare para frontend).

  {"version": 1, "feature": "10",
   "retirados": {"orders": ["<paquete>::<TestDePrimerNivel>"],
                 "front": [["angular:api-client", "projects/api-client/src/lib/x.spec.ts",
                            "XApi hace POST"]]}}
"""
from __future__ import annotations

import json
from pathlib import PurePosixPath
import re

from multirepo import git, read_manifest, require

NOMBRE = re.compile(r"(?:Test|Example|Fuzz)[A-Za-z0-9_]*")
PAQUETE = re.compile(r"[^\s:]+")
PROYECTO = re.compile(r"node:test|angular:[A-Za-z0-9][A-Za-z0-9_-]*")
RUTA = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./-]*")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
GO, FRONT = "go", "frontend"
FORMA = ("retirados: se declara '<paquete>::<TestDePrimerNivel>' en destinos Go, o "
         "[\"angular:<proyecto>\"|\"node:test\", \"<archivo>\", \"<nombre completo>\"] "
         "en destinos frontend")

# Una llamada de test con su titulo literal: it/test, sus formas x/f y cualquier
# cadena de modificadores (.skip, .only, .todo, .each(tabla), .each`tabla`).
# Reconoce de mas antes que de menos: una declaracion NO reconocida en la fuente
# se leeria como baja legitima, y eso si seria un falso verde.
DECLARACION = re.compile(r"""
    (?<![A-Za-z0-9_$.])
    (?:x|f)?(?:it|test)
    (?:\s*\.\s*[A-Za-z_$][A-Za-z0-9_$]*|\s*\([^()]*\)|\s*`[^`]*`)*
    \s*\(\s*
    (?P<comilla>['"`])(?P<titulo>(?:\\.|(?!(?P=comilla)).)*?)(?P=comilla)
""", re.S | re.X)

# El sello lo estampa gate.py revision: no es el revisor nombrando una baja.
SELLO = re.compile(r"\s*Revisado:")
DELIMITADORES = (("'", "'"), ('"', '"'), ("`", "`"), ("«", "»"))
COMILLAS = ("'", '"', "`")
# La ruta citada tiene que estar completa: <spec>.orig o <spec>x nombran otro
# archivo. No se exige limite por la izquierda: un prefijo de repo sigue valiendo.
RUTA_COMPLETA = r"(?![A-Za-z0-9_/-]|\.[A-Za-z0-9])"

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


def _literal(crudo: str) -> str:
    """Contenido real de un literal JS. Lo que no sepa desescapar (\\u, \\x) no va
    a coincidir con el nombre medido: bloquea en la base en vez de pasar."""
    salida, i = [], 0
    while i < len(crudo):
        c = crudo[i]
        if c == "\\" and i + 1 < len(crudo):
            siguiente = crudo[i + 1]
            salida.append(crudo[i:i + 2] if siguiente in "uUxX"
                          else ESCAPES.get(siguiente, siguiente))
            i += 2
            continue
        salida.append(c)
        i += 1
    return "".join(salida)


def declaraciones(texto: str) -> set[str]:
    """Titulos hoja que el archivo DECLARA como test, corran o no."""
    return {_literal(m.group("titulo")) for m in DECLARACION.finditer(texto)}


def escrito(texto: str, hoja: str) -> bool:
    """El titulo sigue en el archivo: declarado por it/test, o escrito entre
    comillas en cualquier parte.

    Un wrapper no-op, un alias de `it` o `test.extend` dejan el titulo escrito
    pero no registran el test: ni lo declara `it`/`test` ni lo mide el destino.
    Se busca `'hoja'`, `"hoja"` o `` `hoja` `` como SUBCADENA, sin emparejar
    comillas por el archivo: un apostrofo suelto antes (un comentario, una
    regex) desincronizaba ese emparejado y volvia invisible el titulo.
    """
    return hoja in declaraciones(texto) or any(c + hoja + c in texto for c in COMILLAS)


def es_frontend(item) -> bool:
    """Un id medido de frontend son tres partes; uno de Go, paquete y test."""
    return len(item) == 3


def tipo(declarados) -> str | None:
    """Tipo de destino de las bajas de un microservicio; leer() no las mezcla."""
    for item in declarados:
        return FRONT if es_frontend(item) else GO
    return None


def marca(item) -> str:
    return "::".join(item)


def _motivo_frontend(item) -> str | None:
    if len(item) != 3 or not all(isinstance(x, str) and x for x in item):
        return "son tres cadenas no vacias"
    proyecto, archivo, nombre = item
    if not PROYECTO.fullmatch(proyecto):
        return "el proyecto es 'node:test' o 'angular:<nombre>'"
    if not RUTA.fullmatch(archivo) or ".." in PurePosixPath(archivo).parts:
        return "el archivo es una ruta relativa del repo, sin '..'"
    if proyecto.startswith("angular:"):
        raiz = "projects/" + proyecto[len("angular:"):] + "/"
        if not archivo.startswith(raiz):
            return f"los tests de {proyecto} viven bajo {raiz}"
    if CONTROL.search(nombre):
        return "el nombre completo no lleva saltos de linea ni caracteres de control"
    return None


def leer(path, nombres=None, feature=None) -> dict[str, set[tuple[str, ...]]]:
    data = read_manifest(path)
    require(isinstance(data, dict) and set(data) == {"version", "feature", "retirados"}
            and type(data["version"]) is int and data["version"] == 1
            and isinstance(data["feature"], str)
            and (feature is None or data["feature"] == str(feature)),
            "retirados: esquema invalido o de otra feature")
    declarados = data["retirados"]
    require(isinstance(declarados, dict) and declarados
            and (nombres is None or set(declarados) <= set(nombres)),
            "retirados: sin microservicios o con uno ajeno al mapa")
    out = {}
    for nombre, lista in declarados.items():
        require(isinstance(lista, list) and lista
                and len({json.dumps(x, sort_keys=True) for x in lista}) == len(lista),
                f"retirados: lista vacia o duplicada en {nombre}")
        pares = set()
        for item in lista:
            if isinstance(item, list):
                motivo = _motivo_frontend(item)
                require(motivo is None, f"{FORMA}, no {item!r}: {motivo}")
                pares.add(tuple(item))
                continue
            require(isinstance(item, str), f"{FORMA}, no {item!r}")
            pkg, sep, test = item.partition("::")
            require(sep and PAQUETE.fullmatch(pkg) and NOMBRE.fullmatch(test),
                    f"{FORMA}, no '{item}'")
            pares.add((pkg, test))
        require(len({len(x) for x in pares}) == 1,
                f"retirados: {nombre} mezcla ids de Go y de frontend")
        out[nombre] = pares
    return out


def _medidos(base) -> set[tuple[str, str]]:
    return {(r["Package"], r["Test"]) for r in base["resultados"] if r["Action"] != "skip"}


def _modulo(repo, sha) -> str:
    require(git(repo, "ls-tree", "--name-only", sha, "--", "go.mod") == "go.mod",
            "retirados: la base no tiene go.mod en la raiz del repo")
    m = re.search(r"^module\s+(\S+)\s*$", git(repo, "show", f"{sha}:go.mod"), re.M)
    require(m, "retirados: go.mod de la base sin directiva module")
    return m.group(1).strip('"')


def _definido(repo, sha, directorio, test) -> bool:
    # Solo el directorio del paquete, no sus subdirectorios: glob no cruza '/'.
    spec = f":(glob){directorio}/*_test.go" if directorio else ":(glob)*_test.go"
    return bool(git(repo, "grep", "-l", "-E", "-e", rf"^func {test}\(", sha, "--", spec, ok=(0, 1)))


def verificar(repo, base_sha, ausente_en, base, medidos_ahora, declarados) -> None:
    """Cada baja declarada la borro la feature; si no, Invalid."""
    if not declarados:
        return
    antes = _medidos(base)
    modulo = _modulo(repo, base_sha)
    for pkg, test in sorted(declarados):
        item = f"{pkg}::{test}"
        require((pkg, test) in antes, f"retirados: {item} no se midio en la base")
        require((pkg, test) not in medidos_ahora, f"retirados: {item} se sigue midiendo en el destino")
        require(pkg == modulo or pkg.startswith(modulo + "/"), f"retirados: {item} fuera del modulo {modulo}")
        directorio = pkg[len(modulo) + 1:]
        require(not re.search(r"[*?\[\]\\]", directorio), f"retirados: directorio no literal en {item}")
        require(_definido(repo, base_sha, directorio, test), f"retirados: {item} no esta definido en la base")
        for sha in ausente_en:
            require(not _definido(repo, sha, directorio, test),
                    f"retirados: {item} sigue definido en {sha[:12]}; la feature no lo borro "
                    "(un build tag o un skip no son una baja)")


def _blob(repo, sha, archivo) -> str | None:
    """Contenido del archivo en ese commit, o None si ahi no existe."""
    entrada = git(repo, "ls-tree", "-z", sha, "--", archivo).rstrip("\0")
    if not entrada:
        return None
    require(entrada.split(" ", 2)[1] == "blob",
            f"retirados: {archivo} no es un archivo regular en {sha[:12]}")
    return git(repo, "show", f"{sha}:{archivo}", binary=True).decode("utf-8", "replace")


def verificar_frontend(repo, base_sha, ausente_en, base, hojas, declarados, revisado=None) -> dict:
    """Bajas de un destino frontend: medidas en la base, borradas por la feature
    y citadas en el review. Devuelve el titulo hoja de cada una.

    `hojas` viene de la MEDICION de la base (postmerge_frontend.leaf_titles): el
    titulo hoja no se adivina partiendo el nombre completo, se lee del raw que ya
    valido `read_base`. Asi dos hojas homonimas o una sufijo de otra no colapsan.

    Corre ANTES de medir el destino: una declaracion que no se sostiene debe
    bloquear por su motivo y no por el rechazo generico de skip/todo del runner.
    """
    if not declarados:
        return {}
    antes = {tuple(r["id"]) for r in base["results"]}
    resueltas = {}
    for item in sorted(tuple(x) for x in declarados):
        etiqueta = marca(item)
        # Guarda: un id de Go aqui seria un IndexError, no un bloqueo explicado.
        require(es_frontend(item), f"retirados: {etiqueta} no es un id medido de frontend")
        require(item in antes, f"retirados: {etiqueta} no se midio en la base")
        hoja = hojas.get(item)
        require(hoja is not None,
                f"retirados: {etiqueta}: la medicion de la base no registra su titulo hoja")
        require(hoja, f"retirados: {etiqueta}: titulo hoja vacio; no hay nada que citar")
        archivo = item[1]
        texto = _blob(repo, base_sha, archivo)
        require(texto is not None,
                f"retirados: {etiqueta}: {archivo} no existe en la base {base_sha[:12]}")
        require(hoja in declaraciones(texto),
                f"retirados: {etiqueta}: {archivo} no declara el titulo hoja '{hoja}' en la "
                f"base {base_sha[:12]}; su ausencia posterior no prueba que se haya borrado")
        for sha in ausente_en:
            texto = _blob(repo, sha, archivo)
            require(texto is None or not escrito(texto, hoja),
                    f"retirados: {etiqueta} sigue declarado en {sha[:12]} con el titulo "
                    f"'{hoja}'; la feature no lo borro (un skip/todo/only, renombrar solo el "
                    "describe, o dejarlo escrito tras un wrapper que no lo registra, no son bajas)")
        resueltas[item] = hoja
    if revisado is not None:
        faltan = sin_cita_frontend(revisado, resueltas)
        require(not faltan, "retirados: el review no cita la baja de " + ", ".join(faltan))
    return resueltas


def sin_cita_frontend(revisado, bajas) -> list[str]:
    """Bajas que el review sellado no DECLARA: el revisor no las vio.

    Una mencion no es una declaracion. Se exige, en UNA MISMA linea que no sea la
    del sello, la ruta del spec y el titulo entre delimitadores -- o el id medido
    completo. Buscar hoja y ruta sueltas por todo el texto deja que una hoja
    corta quede 'citada' por aparecer dentro de otra palabra.
    """
    lineas = [x for x in _sin_sello(revisado or "").splitlines() if not SELLO.match(x)]
    faltan = []
    for item, hoja in sorted(bajas.items()):
        archivo, nombre = item[1], item[2]
        formas = [a + t + b for t in (hoja, nombre) for a, b in DELIMITADORES]
        formas.append(marca(item))
        citada = re.compile(re.escape(archivo) + RUTA_COMPLETA)
        if not any(citada.search(linea) and any(f in linea for f in formas) for linea in lineas):
            faltan.append(marca(item))
    return faltan


def _sin_sello(texto: str) -> str:
    """Quita el sello COMPLETO que estampa gate.py revision.

    No alcanza con descartar las lineas que empiezan con `Revisado:`: el sello
    puede ocupar VARIAS lineas si quien sello metio saltos en `--por`, y ese
    texto lo escribio el gate, no el revisor. gate.py ya no acepta esos saltos;
    esto lo sostiene igual si el review llega sellado desde otro lado.
    """
    from comun import REVISADO_RE  # solo en el camino del cierre, que ya usa comun
    return REVISADO_RE.sub("", texto)


def midiendo_frontend(medidos_ahora, declarados) -> list[str]:
    """Bajas que el destino sigue midiendo: no son bajas."""
    return [marca(x) for x in sorted({tuple(i) for i in declarados} & set(medidos_ahora))]


def verificar_historico(repo, base_sha, source_sha, target_sha, declarados) -> None:
    """Baja de CIERRE HISTORICO (sin base medida): la unica prueba de que la
    propia feature agrego el test es su declaracion en source_sha Y su
    AUSENCIA en base_sha (la misma identidad de tests_agregados_go); la unica
    prueba de la baja es su ausencia (no definicion) en target_sha. Sin el
    chequeo contra base_sha, cualquier test preexistente que otra feature
    borre despues se podria declarar como baja de ESTA feature aunque nunca la
    haya agregado (hallazgo P2 ronda 2) -- ver diseno en
    docs/diseno-arnes-cierre-historico.md, garantia 4."""
    if not declarados:
        return
    modulo = _modulo(repo, source_sha)
    for pkg, test in sorted(declarados):
        item = f"{pkg}::{test}"
        require(pkg == modulo or pkg.startswith(modulo + "/"), f"retirados: {item} fuera del modulo {modulo}")
        directorio = pkg[len(modulo) + 1:]
        require(not re.search(r"[*?\[\]\\]", directorio), f"retirados: directorio no literal en {item}")
        require(_definido(repo, source_sha, directorio, test),
                f"retirados: {item} no esta definido en la fuente {source_sha[:12]}")
        require(not _definido(repo, base_sha, directorio, test),
                f"retirados: {item} ya existia en la base {base_sha[:12]}; el cierre historico solo "
                "declara bajas de tests que la propia feature agrego")
        require(not _definido(repo, target_sha, directorio, test),
                f"retirados: {item} sigue definido en el destino {target_sha[:12]}; el cierre "
                "historico no lo puede declarar baja (un build tag o un skip no son una baja)")


def _sufijos(nombre: str) -> list[str]:
    """Sufijos de un nombre completo que empiezan en un limite de PALABRA, del
    mas largo (el nombre entero) al mas corto (la ultima palabra). Angular une
    ancestros de describe y titulo con el mismo espacio: no hay separador fijo
    que distinga uno de otro."""
    palabras = nombre.split(" ")
    return [" ".join(palabras[i:]) for i in range(len(palabras))]


def sufijos_declarados(texto: str, nombre_completo: str) -> set[str]:
    """Sufijos del nombre completo que el archivo DECLARA como titulo de test.

    Sin medicion (cierre historico: source_sha no se puede correr con el
    runner vigente) el unico dato disponible es el texto fuente. Debe resultar
    EXACTAMENTE un sufijo declarado para que el titulo hoja sea univoco."""
    declaradas = declaraciones(texto)
    return {s for s in _sufijos(nombre_completo) if s and s in declaradas}


def verificar_frontend_historico(repo, base_sha, source_sha, target_sha, declarados, revisado=None) -> dict:
    """Baja de CIERRE HISTORICO frontend: sin base medida, el titulo hoja se
    resuelve por sufijos del nombre completo declarado en source_sha (ver
    sufijos_declarados) y debe ser unico. Ademas debe estar AUSENTE de las
    declaraciones de base_sha (la misma identidad de tests_agregados_front):
    sin ese chequeo, un titulo preexistente que otra feature borre despues se
    podria declarar como baja de ESTA feature aunque nunca lo haya agregado
    (hallazgo P2 ronda 2, repro simetrico del hueco Go). Ausente en destino
    significa que su archivo no existe ahi o ya no lo declara ni lo deja
    escrito (retiros.escrito).
    """
    if not declarados:
        return {}
    resueltas = {}
    for item in sorted(tuple(x) for x in declarados):
        etiqueta = marca(item)
        require(es_frontend(item), f"retirados: {etiqueta} no es un id medido de frontend")
        archivo, nombre = item[1], item[2]
        texto_fuente = _blob(repo, source_sha, archivo)
        require(texto_fuente is not None,
                f"retirados: {etiqueta}: {archivo} no existe en la fuente {source_sha[:12]}")
        candidatos = sufijos_declarados(texto_fuente, nombre)
        require(candidatos,
                f"retirados: {etiqueta}: {archivo} no declara un titulo hoja de '{nombre}' "
                f"en la fuente {source_sha[:12]}")
        require(len(candidatos) == 1,
                f"retirados: {etiqueta}: titulo hoja ambiguo entre {sorted(candidatos)!r} "
                f"en la fuente {source_sha[:12]}")
        hoja = next(iter(candidatos))
        texto_base = _blob(repo, base_sha, archivo)
        require(texto_base is None or hoja not in declaraciones(texto_base),
                f"retirados: {etiqueta}: '{hoja}' ya estaba declarado en la base {base_sha[:12]}; "
                "el cierre historico solo declara bajas de tests que la propia feature agrego")
        texto_destino = _blob(repo, target_sha, archivo)
        require(texto_destino is None or not escrito(texto_destino, hoja),
                f"retirados: {etiqueta} sigue definido en el destino {target_sha[:12]} con el "
                f"titulo '{hoja}'; el cierre historico no lo puede declarar baja")
        resueltas[item] = hoja
    if revisado is not None:
        faltan = sin_cita_frontend(revisado, resueltas)
        require(not faltan, "retirados: el review no cita la baja de " + ", ".join(faltan))
    return resueltas


def sin_cita(texto, declarados) -> list[str]:
    """Bajas Go que el review sellado no nombra: el revisor no las vio."""
    return [f"{p}::{t}" for p, t in sorted(declarados)
            if not re.search(rf"(?<![A-Za-z0-9_]){re.escape(t)}(?![A-Za-z0-9_])", texto)]
