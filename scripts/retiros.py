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

Un SUBTEST cuyo padre sigue vivo se declara `<paquete>::<TestX>/<seg>[/<seg>...]`,
con el nombre exacto que reporto `go test -json` en la base. El destino ya no lo
registra en ningun estado (un skip no es baja), ni registra sin medir ningun
descendiente suyo (la baja lo cubriria), el padre tiene que seguir
midiendose ahi (si no, es la baja de primer nivel), y "lo borro
la feature" se prueba sobre LITERALES de cadena Go de los *_test.go del
directorio del paquete, reescritos como testing.rewrite: cada segmento escrito
en base_sha y la hoja ya no escrita en la fuente ni en el destino. Un segmento
`#NN` (desambiguacion de go test) no es un literal y se rechaza. El review
sellado lo tiene que nombrar como palabra completa fuera del sello. Un subtest
declarado cubre tambien sus propios subtests. Un *_test.go symlink en el
directorio del paquete bloquea, en subtests y en primer nivel: no se puede leer.

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
   "retirados": {"orders": ["<paquete>::<TestDePrimerNivel>", "<paquete>::<TestX>/<subtest>"],
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
FORMA = ("retirados: se declara '<paquete>::<TestDePrimerNivel>' o "
         "'<paquete>::<TestX>/<subtest>[/...]' en destinos Go, o "
         "[\"angular:<proyecto>\"|\"node:test\", \"<archivo>\", \"<nombre completo>\"] "
         "en destinos frontend")
# Sufijo con que go test desambigua subtests repetidos (testing.unique, "%s#%02d").
DESAMBIGUACION = re.compile(r"#[0-9]{2,}\Z")

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


def partes(test: str) -> tuple[str, list[str]]:
    """`TestX/a/b` -> ("TestX", ["a", "b"]); un test de primer nivel no tiene segmentos."""
    padre, barra, resto = test.partition("/")
    return padre, (resto.split("/") if barra else [])


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
            padre, segs = partes(test)
            require(sep and PAQUETE.fullmatch(pkg) and NOMBRE.fullmatch(padre),
                    f"{FORMA}, no '{item}'")
            # go test -json ya reescribio espacios y no imprimibles: un segmento
            # con ellos, o vacio, no es un nombre que se haya podido medir.
            require(all(s and s.isprintable() and not any(c.isspace() for c in s) for s in segs),
                    f"{FORMA}, no '{item}': cada segmento del subtest es no vacio, sin espacios "
                    "ni caracteres de control (el nombre exacto que reporto go test -json)")
            repetido = next((s for s in segs if DESAMBIGUACION.search(s)), None)
            require(repetido is None,
                    f"retirados: '{item}': el segmento '{repetido}' termina en #NN, el sufijo con "
                    "que go test desambigua subtests repetidos; no es un nombre escrito en el "
                    "codigo y no se puede verificar como baja (sobrebloqueo explicito)")
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


def _tests_go(repo, sha, directorio) -> list[tuple[str, str]]:
    """(ruta, blob) de los *_test.go del directorio del paquete en ese commit, sin
    subdirectorios. Un symlink BLOQUEA: su blob es la ruta destino, no el codigo
    que Go compila, y ni `git grep` ni la busqueda de literales lo pueden leer."""
    raiz = PurePosixPath(directorio or ".")
    salida = git(repo, "ls-tree", "-z", sha, "--", *([directorio + "/"] if directorio else []))
    archivos = []
    for entrada in filter(None, salida.split("\0")):
        meta, _, ruta = entrada.partition("\t")
        modo, clase, objeto = meta.split(" ")
        if clase != "blob" or not ruta.endswith("_test.go") or PurePosixPath(ruta).parent != raiz:
            continue
        require(modo != "120000",
                f"retirados: {ruta} es un symlink en {sha[:12]}: el gate no puede leer el codigo que "
                "Go compila detras de el (symlink no verificable); reemplazalo por el archivo real")
        archivos.append((ruta, objeto))
    return archivos


def _definido(repo, sha, directorio, test) -> bool:
    _tests_go(repo, sha, directorio)  # un symlink no verificable bloquea antes del grep
    # Solo el directorio del paquete, no sus subdirectorios: glob no cruza '/'.
    spec = f":(glob){directorio}/*_test.go" if directorio else ":(glob)*_test.go"
    return bool(git(repo, "grep", "-l", "-E", "-e", rf"^func {test}\(", sha, "--", spec, ok=(0, 1)))


# --- subtests Go: el nombre vive en LITERALES de cadena, no en un `func` -----

ESCAPES_GO = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11, "\\": 92, "'": 39, '"': 34}
# Dentro de un comentario no hay gramatica: se buscan pares de comillas sueltos.
EN_COMENTARIO = re.compile(r'"((?:\\.|[^"\\\n])*)"|`([^`]*)`')


def _utf8_go(datos: bytes) -> str:
    """Decodifica como `for range` de Go: cada byte invalido es un U+FFFD."""
    try:
        return datos.decode("utf-8")
    except UnicodeDecodeError:
        pass
    salida, i = [], 0
    while i < len(datos):
        for n in (1, 2, 3, 4):
            try:
                salida.append(datos[i:i + n].decode("utf-8"))
            except UnicodeDecodeError:
                continue
            i += n
            break
        else:
            salida.append("\ufffd")
            i += 1
    return "".join(salida)


def _cadena_go(crudo: str) -> str:
    """Contenido de un literal interpretado de Go (sin las comillas). Un escape
    invalido se conserva tal cual: ese codigo no compila y no se mide."""
    salida, i = bytearray(), 0
    while i < len(crudo):
        c = crudo[i]
        if c != "\\" or i + 1 == len(crudo):
            salida += c.encode("utf-8", "surrogatepass")
            i += 1
            continue
        s = crudo[i + 1]
        largo = {"x": 2, "u": 4, "U": 8}.get(s, 0)
        cifras = crudo[i + 2:i + 2 + largo]
        if s in ESCAPES_GO:
            salida.append(ESCAPES_GO[s])
            i += 2
        elif re.fullmatch(r"[0-3][0-7]{2}", crudo[i + 1:i + 4]):
            salida.append(int(crudo[i + 1:i + 4], 8))
            i += 4
        elif largo and re.fullmatch(rf"[0-9A-Fa-f]{{{largo}}}", cifras):
            valor = int(cifras, 16)
            if s == "x":
                salida.append(valor)
            else:
                salida += (chr(valor) if valor <= 0x10FFFF and not 0xD800 <= valor <= 0xDFFF
                           else "\ufffd").encode("utf-8")
            i += 2 + largo
        else:
            salida += crudo[i:i + 2].encode("utf-8", "surrogatepass")
            i += 2
    return _utf8_go(bytes(salida))


def _en_comentario(texto: str) -> set[str]:
    return {_cadena_go(m.group(1)) if m.group(1) is not None else m.group(2)
            for m in EN_COMENTARIO.finditer(texto)}


def literales_go(texto: str) -> set[str]:
    """Contenido de CADA literal de cadena de un fuente Go (interpretado `"..."`
    desescapado, o crudo `` `...` `` sin retornos de carro), sea o no argumento
    de t.Run: los subtests de tabla ponen el nombre en un struct.

    Un lexer, no una busqueda de comillas: una runa `'"'` no desincroniza el
    resto del archivo. Es generoso a proposito -- reconocer de mas bloquea de
    mas, nunca de menos --: tambien cuenta lo que quede entre comillas dentro
    de un comentario (un t.Run comentado sigue escrito)."""
    salida, i, n = set(), 0, len(texto)
    while i < n:
        c = texto[i]
        if texto.startswith("//", i):
            fin = texto.find("\n", i)
            fin = n if fin < 0 else fin
            salida |= _en_comentario(texto[i + 2:fin])
            i = fin
        elif texto.startswith("/*", i):
            fin = texto.find("*/", i + 2)
            fin = n if fin < 0 else fin
            salida |= _en_comentario(texto[i + 2:fin])
            i = fin + 2
        elif c == "`":
            fin = texto.find("`", i + 1)
            fin = n if fin < 0 else fin
            salida.add(texto[i + 1:fin].replace("\r", ""))
            i = fin + 1
        elif c in "\"'":
            j = i + 1
            while j < n and texto[j] not in (c, "\n"):
                j += 2 if texto[j] == "\\" and j + 1 < n and texto[j + 1] != "\n" else 1
            if j < n and texto[j] == c:
                if c == '"':
                    salida.add(_cadena_go(texto[i + 1:j]))
                i = j + 1
            else:
                i += 1  # comilla suelta (no compila): sigue sin perder lo que viene
        else:
            i += 1
    return salida


def _espacio_go(r: int) -> bool:
    """testing.isSpace: NO es la clase Z de Unicode."""
    if r < 0x2000:
        return r in (0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20, 0x85, 0xA0, 0x1680)
    return r <= 0x200A or r in (0x2028, 0x2029, 0x202F, 0x205F, 0x3000)


def reescribir(nombre: str) -> str:
    """El nombre como lo reporta go test (testing.rewrite): espacios a `_` y lo no
    imprimible escapado como strconv.QuoteRune."""
    salida = []
    for c in nombre:
        r = ord(c)
        if _espacio_go(r):
            salida.append("_")
        elif c.isprintable():
            salida.append(c)
        elif r in (7, 8):
            salida.append("\\a" if r == 7 else "\\b")
        elif r < 0x20 or r == 0x7F:
            salida.append(f"\\x{r:02x}")
        elif r < 0x10000:
            salida.append(f"\\u{r:04x}")
        else:
            salida.append(f"\\U{r:08x}")
    return "".join(salida)


def _escritos(repo, sha, directorio) -> set[str]:
    """Literales reescritos de los *_test.go del directorio del paquete en ese
    commit. Solo ese directorio, no sus subdirectorios (igual que _definido), y
    ciego a build tags."""
    textos = set()
    for _, objeto in _tests_go(repo, sha, directorio):
        fuente = git(repo, "cat-file", "blob", objeto, binary=True).decode("utf-8", "replace")
        textos |= {reescribir(x) for x in literales_go(fuente)}
    return textos


def cubiertos(textos, segs) -> set[int]:
    """Indices de los segmentos que algun literal escribe. Un literal puede nombrar
    varios seguidos: t.Run("a/b") dentro de TestX se mide `TestX/a/b`."""
    indices = set()
    for i in range(len(segs)):
        for j in range(i + 1, len(segs) + 1):
            if "/".join(segs[i:j]) in textos:
                indices.update(range(i, j))
    return indices


def _verificar_subtest(repo, item, directorio, segs, base_sha, ausente_en) -> None:
    """Lo borro la feature: cada segmento escrito en la base y la hoja ya no
    escrita en la fuente ni en el destino. Un nombre armado en runtime no deja
    literal y no se puede verificar: bloquea."""
    en_base = cubiertos(_escritos(repo, base_sha, directorio), segs)
    for k, seg in enumerate(segs):
        require(k in en_base,
                f"retirados: {item}: el segmento '{seg}' no esta escrito en la base {base_sha[:12]} "
                "(ningun literal de cadena de los *_test.go de su directorio lo nombra); un nombre "
                "armado en runtime no se puede verificar como baja")
    hoja = len(segs) - 1
    for sha in ausente_en:
        require(hoja not in cubiertos(_escritos(repo, sha, directorio), segs),
                f"retirados: {item} sigue escrito en {sha[:12]}: un literal de los *_test.go de su "
                f"directorio todavia nombra '{segs[hoja]}'; la feature no lo borro (un if, un skip, "
                "un build tag o un comentario no son una baja)")


def padres_sin_medir(medidos, declarados) -> list[str]:
    """Bajas de subtest cuyo test padre ya no se mide: esa es la baja de primer nivel."""
    return [f"{p}::{t}" for p, t in sorted(declarados)
            if partes(t)[1] and (p, partes(t)[0]) not in medidos]


def verificar(repo, base_sha, ausente_en, base, medidos_ahora, declarados, registrados=None) -> None:
    """Cada baja declarada la borro la feature; si no, Invalid.

    `registrados` son TODOS los resultados del destino, {(paquete, test): Action}:
    un id declarado que siga ahi en cualquier estado -- skip incluido -- se
    rechaza antes de mirar el codigo: un subtest puede no tener literal (armado en
    runtime, o una constante de un .go comun) y un `func TestX (t` sin gofmt no lo
    ve `_definido`, y aun asi los dos siguen corriendo."""
    registrados = registrados or {}
    if not declarados:
        return
    antes = _medidos(base)
    modulo = _modulo(repo, base_sha)
    for pkg, test in sorted(declarados):
        item = f"{pkg}::{test}"
        require((pkg, test) in antes, f"retirados: {item} no se midio en la base")
        require((pkg, test) not in medidos_ahora, f"retirados: {item} se sigue midiendo en el destino")
        padre, segs = partes(test)
        # Vale para TODO id: go test registra por AST y _definido busca
        # `^func TestX\(`, asi que un `func TestX (t` sin gofmt que termina en
        # skip no se ve definido (review r3, P3-7).
        require((pkg, test) not in registrados,
                f"retirados: {item} sigue registrado en el destino ({registrados.get((pkg, test))}): "
                "el test todavia corre, aunque sea para omitirse; un skip no es una baja")
        # La baja cubre lo que cuelga de ella (postmerge_medido.sin_baja): un
        # descendiente que el destino registra sin medirlo (skip) tampoco es baja.
        # t.Run("a/b") registra `TestX/a/b` sin registrar `TestX/a`.
        colgados = sorted(f"{p}::{t}" for p, t in registrados
                          if segs and p == pkg and t.startswith(test + "/") and (p, t) not in medidos_ahora)
        require(not colgados, f"retirados: {item} cubre subtests que el destino todavia registra "
                f"(skip): {', '.join(colgados)}; un skip no es una baja")
        require(not segs or (pkg, padre) in medidos_ahora,
                f"retirados: {item}: su test padre {padre} ya no se mide en el destino; eso es la "
                f"baja de primer nivel '{pkg}::{padre}', no la de un subtest")
        require(pkg == modulo or pkg.startswith(modulo + "/"), f"retirados: {item} fuera del modulo {modulo}")
        directorio = pkg[len(modulo) + 1:]
        require(not re.search(r"[*?\[\]\\]", directorio), f"retirados: directorio no literal en {item}")
        if segs:
            _verificar_subtest(repo, item, directorio, segs, base_sha, ausente_en)
            continue
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
        padre, segs = partes(test)
        if segs:
            _verificar_subtest_historico(repo, item, directorio, padre, segs, base_sha, source_sha, target_sha)
            continue
        require(_definido(repo, source_sha, directorio, test),
                f"retirados: {item} no esta definido en la fuente {source_sha[:12]}")
        require(not _definido(repo, base_sha, directorio, test),
                f"retirados: {item} ya existia en la base {base_sha[:12]}; el cierre historico solo "
                "declara bajas de tests que la propia feature agrego")
        require(not _definido(repo, target_sha, directorio, test),
                f"retirados: {item} sigue definido en el destino {target_sha[:12]}; el cierre "
                "historico no lo puede declarar baja (un build tag o un skip no son una baja)")


def _verificar_subtest_historico(repo, item, directorio, padre, segs, base_sha, source_sha, target_sha) -> None:
    """La misma semantica historica que el primer nivel, sobre literales: el padre
    definido y cada segmento escrito en source_sha, la hoja AUSENTE de base_sha
    (la agrego la propia feature) y ya no escrita en el destino. Que el padre se
    siga midiendo lo comprueba medicion_destino tras correr la suite."""
    require(_definido(repo, source_sha, directorio, padre),
            f"retirados: {item}: su test padre {padre} no esta definido en la fuente {source_sha[:12]}")
    en_fuente = cubiertos(_escritos(repo, source_sha, directorio), segs)
    for k, seg in enumerate(segs):
        require(k in en_fuente,
                f"retirados: {item}: el segmento '{seg}' no esta escrito en la fuente {source_sha[:12]}")
    hoja = len(segs) - 1
    require(hoja not in cubiertos(_escritos(repo, base_sha, directorio), segs),
            f"retirados: {item}: '{segs[hoja]}' ya estaba escrito en la base {base_sha[:12]}; el cierre "
            "historico solo declara bajas de tests que la propia feature agrego")
    require(hoja not in cubiertos(_escritos(repo, target_sha, directorio), segs),
            f"retirados: {item} sigue escrito en el destino {target_sha[:12]}; el cierre historico no "
            "lo puede declarar baja (un if, un skip, un build tag o un comentario no son una baja)")


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
    """Bajas Go que el review sellado no nombra: el revisor no las vio.

    Un test de primer nivel conserva su regla: su nombre como palabra en el texto.
    Un SUBTEST exige `TestX/<segs>` o el id entero como palabra completa en una
    linea que no sea del sello (la misma regla de linea que la cita frontend)."""
    faltan, lineas = [], None
    for p, t in sorted(declarados):
        if not partes(t)[1]:
            if not re.search(rf"(?<![A-Za-z0-9_]){re.escape(t)}(?![A-Za-z0-9_])", texto):
                faltan.append(f"{p}::{t}")
            continue
        if lineas is None:
            lineas = [x for x in _sin_sello(texto or "").splitlines() if not SELLO.match(x)]
        if not any(_nombra(linea, t) or _nombra(linea, f"{p}::{t}") for linea in lineas):
            faltan.append(f"{p}::{t}")
    return faltan


# Puntuacion que puede rodear un id citado sin ser parte de el. No incluye `_`,
# `/`, `#`, letras ni cifras: `TestX/a_b`, `TestX/a/b` o `TestX/a#01` nombran OTRO
# subtest, no `TestX/a`.
BORDE_CITA = r"""[`'"«»“”‘’*,;:.!?¿¡()\[\]{}<>|]"""


def _nombra(linea: str, ident: str) -> bool:
    """El id es una palabra completa: separado por espacios o bordes de linea, con
    a lo sumo puntuacion de apertura/cierre pegada. Un id de subtest no lleva
    espacios (go test los reescribio a `_`)."""
    return re.search(rf"(?<!\S){BORDE_CITA}*{re.escape(ident)}{BORDE_CITA}*(?!\S)", linea) is not None
