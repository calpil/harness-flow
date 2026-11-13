#!/usr/bin/env python3
"""Normas de ingenieria del arnes: UNA fuente para quien escribe y para quien revisa.

Las normas que salen de los libros de referencia (DDIA, Ousterhout, Fowler y
GoF, CLRS, Chip Huyen, Sam Newman, McConnell, OWASP, Context7, ASD-STE100,
Orosz) vivian repartidas en prompts distintos. El briefing del revisor mandaba
marcar sus violaciones como bloqueantes o mayores, pero el implementer en modo
pair -el modo por defecto- no recibia ninguna, y el revisor de un host sin
`agents/revisor.md` no auditaba OWASP ni la construccion defensiva.

Aqui cada norma dice las tres cosas juntas: que escribe el leader en el spec,
que hace el implementer y que audita el revisor, y antes que eso que deja el rol
producto en el PRD y el SDD. `producto.py borrador` imprime lo del rol producto,
el brief (`contexto.py brief`) lo del leader y el implementer, y el briefing
(`revision.py --briefing`) lo del revisor.
Salen del mismo registro, asi que el revisor no puede bloquear por algo que a
quien escribio el codigo no se le dijo: tests/test_normas.py lo comprueba.

Una norma aplica solo si el cambio toca su materia (una feature sin llamadas a
un LLM no tiene nada que cumplir de la norma de IA). Eso lo dice `cuando`.
"""
from __future__ import annotations

from pathlib import Path

REFERENCIAS = Path(__file__).resolve().parent.parent / "references"

BLOQUEANTE, MAYOR, MENOR = "BLOQUEANTE", "MAYOR", "MENOR"

# Cada norma:
#   id, titulo, ref (archivo en references/), cuando (a que cambios aplica),
#   producto  -> {"prd": [...], "sdd": [...]}: lo que el rol producto deja en cada documento,
#   spec      -> lo que el leader deja escrito en el spec,
#   construye -> lo que hace quien implementa, en pair o delegado,
#   audita    -> [(severidad, texto)] que el revisor busca en el diff.
# Las cuatro partes son obligatorias en cada norma: es el cuadro norma x rol, y
# tests/test_normas.py falla si una celda queda vacia.
NORMAS: list[dict] = [
    {
        "id": "datos",
        "titulo": "Datos confiables (DDIA, Kleppmann)",
        "ref": "patrones-datos-ddia.md",
        "cuando": "el cambio escribe en una base de datos, publica eventos o expone una mutacion por red",
        "producto": {"sdd": ["Una `D-n` por cada decision de persistencia: que base, que consistencia entre "
                             "servicios (Outbox o no), como se versionan las filas y como evoluciona el esquema."]},
        "spec": ["Si un AC muta estado por red o dispara un efecto externo, declara en el AC como se "
                 "comporta el reintento (idempotencia) y la escritura concurrente."],
        "construye": [
            "Nunca guardes en la base y despues llames al broker o a una API externa: usa Transactional "
            "Outbox en la MISMA transaccion.",
            "Una entidad mutable que dos escritores pueden tocar se actualiza con control optimista "
            "(columna `version`).",
            "Una mutacion expuesta a la red acepta `Idempotency-Key` cuando el spec declara reintentos.",
            "Un cambio de esquema va en Expand-Contract: nunca una migracion que rompa la version desplegada.",
        ],
        "audita": [
            (BLOQUEANTE, "doble escritura (Dual-Write): persistir y luego invocar un broker o una API "
                         "externa fuera de un Transactional Outbox atomico en la misma TX"),
            (MAYOR, "updates concurrentes de una entidad mutable sin control optimista (OCC con `version`)"),
            (MAYOR, "mutaciones de red no idempotentes cuando el spec declara reintentos"),
        ],
    },
    {
        "id": "diseno",
        "titulo": "Filosofia de diseno (Ousterhout)",
        "ref": "filosofia-diseno-ousterhout.md",
        "cuando": "el cambio agrega o modifica modulos, clases o funciones",
        "producto": {"sdd": ["Cada componente se describe por su interfaz y lo que oculta. Diseña dos veces: "
                             "cada `D-n` nombra la alternativa descartada."]},
        "spec": ["En el plan vertical, nombra la interfaz publica que el slice agrega o cambia: "
                 "compacta, y sin exponer detalles de persistencia o transporte."],
        "construye": [
            "Modulos profundos: interfaz chica, implementacion completa. No desmenuces una funcion "
            "cohesiva en micro-metodos de 3 a 5 lineas.",
            "Ningun metodo pass-through: si solo reenvia argumentos con la misma firma, sobra o le falta abstraccion.",
            "Nada de esquema de BD, queries ni detalles de infraestructura en el dominio ni en lo que ve el cliente.",
            "Define los errores fuera de la existencia: un caso limite ordinario (coleccion vacia, borrado "
            "repetido) es flujo normal, no una excepcion.",
            "Los comentarios dicen contrato, invariante e intencion (que y por que), nunca parafrasean el codigo.",
        ],
        "audita": [
            (MAYOR, "metodos pass-through que solo reenvian llamadas sin abstraer"),
            (MAYOR, "fuga de informacion entre capas (Information Leakage): esquema de BD, queries o "
                    "infraestructura en el dominio o hacia el cliente"),
            (MAYOR, "sobre-fragmentacion artificial (classitis, micro-funciones que dispersan el flujo)"),
            (MENOR, "comentarios que parafrasean la sintaxis en vez de documentar invariantes"),
        ],
    },
    {
        "id": "refactor",
        "titulo": "Dos sombreros y code smells (Beck, Fowler)",
        "ref": "patrones-gof-y-refactoring.md",
        "cuando": "todo cambio de codigo",
        "producto": {"sdd": ["El SDD no reserva abstracciones para features futuras: describe lo que el "
                             "sistema necesita hoy y deja el saneamiento al sombrero de refactor."]},
        "spec": ["El plan vertical separa lo que agrega comportamiento de lo que solo sanea: un refactor "
                 "amplio es su propio slice, no un paso escondido."],
        "construye": [
            "Sombrero 1 (Red -> Green): un test en la costura publica y el codigo mas simple que lo pasa. "
            "Sin jerarquias ni patrones en este paso.",
            "Sombrero 2 (refactor en verde): con el test verde, sanea los smells de abajo. Aplicalo tu, en "
            "pair y en delegado, dentro de los archivos que la feature ya toca y en su propio commit. Un "
            "refactor que cambia una interfaz publica o sale de esos archivos es una decision de diseno: "
            "parada (1).",
            "Un concepto del dominio (identificador, importe, estado) es un Value Object con validacion, "
            "no un `string` o `int` crudo.",
            "Un cambio conceptual toca un lugar: si te obliga a editar muchos archivos, mueve el "
            "comportamiento a donde viven sus datos (Move Method).",
            "Ninguna interfaz con una sola implementacion sin motivo de test, ni fabrica o abstraccion "
            "'por si acaso' que ningun AC pide.",
            "Commits separados: `feat:`/`fix:` para comportamiento, `refactor:` para saneamiento. Los "
            "tests existentes no se tocan durante el refactor.",
        ],
        "audita": [
            (MAYOR, "Primitive Obsession: identificadores o importes del dominio como strings/ints sin Value Objects"),
            (MAYOR, "Shotgun Surgery o Divergent Change: un cambio conceptual disperso en muchos archivos, "
                    "o una clase modificada por motivos dispares (BLOQUEANTE si rompe un limite de capa)"),
            (MAYOR, "Feature Envy: metodos que manipulan los atributos de otra clase en vez de delegarle"),
            (MAYOR, "Middle Man: clases o metodos que solo delegan sin aportar transformacion"),
        ],
    },
    {
        "id": "patrones",
        "titulo": "Design Patterns (GoF: Gamma, Helm, Johnson, Vlissides)",
        "ref": "design-patterns-gof.md",
        "cuando": "el cambio introduce una interfaz, una jerarquia, una fabrica o una indireccion",
        "producto": {"sdd": ["Un patron entra en una `D-n` solo si el eje de variacion ya es real, con su costo y "
                             "la alternativa descartada. El catalogo no disena el sistema."]},
        "spec": ["No pidas un patron en un AC: el AC describe comportamiento observable. Un patron entra "
                 "al plan solo si el eje de variacion ya existe en el codigo."],
        "construye": [
            "Un patron es el destino de un refactor cuando el eje ya es real, nunca el punto de partida "
            "del primer verde.",
            "Programa contra el puerto que el stack define, no contra la implementacion: Adapter en los "
            "puertos, Strategy o State en el dominio, Factory solo en el composition root.",
            "Si dudas entre un patron y una funcion, escribe la funcion.",
        ],
        "audita": [
            (MAYOR, "Speculative Generality: un patron o una abstraccion sin eje de variacion real, que "
                    "ningun AC pide (interfaz con una sola implementacion sin motivo de test, fabrica vacia)"),
            (MAYOR, "un patron aplicado fuera de su capa: fabricas o cableado fuera del composition root, "
                    "logica de negocio dentro de un Adapter"),
        ],
    },
    {
        "id": "rendimiento",
        "titulo": "Algoritmos y estructuras de datos (CLRS)",
        "ref": "algoritmos-y-estructuras-clrs.md",
        "cuando": "el cambio recorre colecciones, consulta persistencia o llama servicios dentro de un bucle",
        "producto": {"prd": ["Si el volumen o la latencia importan al usuario, el PRD da el numero "
                             "(cuantos registros, en cuanto tiempo)."],
                     "sdd": ["Para cada camino con volumen, el SDD nombra la estructura de datos o el indice "
                             "que lo sostiene y su orden de crecimiento."]},
        "spec": ["Si un AC procesa una coleccion o consulta por lote, declara el tamano esperado o el limite "
                 "que debe soportar."],
        "construye": [
            "Ninguna consulta a base de datos ni llamada HTTP dentro de un bucle: agrupa en batch "
            "(`IN (...)`, un solo viaje de red).",
            "Ninguna busqueda lineal anidada sobre listas: indexa por Map o Set antes de recorrer.",
            "Ninguna concatenacion de strings con `+=` en un bucle no acotado: usa un buffer o builder.",
            "Pre-aloca la coleccion cuando el tamano se conoce.",
        ],
        "audita": [
            (BLOQUEANTE, "consultas N+1: queries a base de datos o llamadas HTTP en bucles sin batching"),
            (MAYOR, "busquedas lineales anidadas O(N^2) sobre colecciones sin indexar"),
            (MAYOR, "concatenacion iterativa de strings en bucles sin buffer contiguo (StringBuilder)"),
            (MENOR, "colecciones de tamano conocido sin pre-alocar capacidad"),
        ],
    },
    {
        "id": "ia",
        "titulo": "Ingenieria de IA (Chip Huyen)",
        "ref": "ai-engineering-chip-huyen.md",
        "cuando": "el cambio llama a un modelo de lenguaje o construye un prompt",
        "producto": {"prd": ["Una feature con IA declara su respaldo determinista y como se mide que acierta "
                             "(Golden Dataset), no un 'se ve bien'."],
                     "sdd": ["Las capas de una llamada a un modelo van en el SDD: guardrail de entrada, armado de "
                             "contexto, modelo, salida estructurada y validador con cortacircuito."]},
        "spec": ["Si la feature llama a un LLM, declara en un AC el esquema de la salida y que pasa "
                 "cuando el modelo falla o devuelve algo invalido."],
        "construye": [
            "Toda llamada a una API de IA lleva timeout explicito y reintentos con backoff exponencial y jitter.",
            "Un bucle de auto-correccion o agentico tiene un tope estricto de 2 iteraciones; despues degrada o aborta.",
            "La salida de un LLM se consume como Structured Output (JSON Schema o Tool Calling), nunca con "
            "regex sobre texto libre.",
            "El input del usuario entra al prompt entre delimitadores semanticos, nunca concatenado crudo.",
        ],
        "audita": [
            (BLOQUEANTE, "llamadas a APIs de LLMs sin timeout ni reintentos resilientes (backoff + jitter)"),
            (BLOQUEANTE, "loops agenticos o de auto-correccion sin limite estricto de <= 2 iteraciones"),
            (MAYOR, "parsing de texto libre en lugar de Structured Outputs (JSON Schema / Tool Calling)"),
            (MAYOR, "concatenacion directa de inputs de usuario en prompts sin delimitadores semanticos"),
        ],
    },
    {
        "id": "servicios",
        "titulo": "Microservicios y sistemas distribuidos (Sam Newman)",
        "ref": "microservicios-sam-newman.md",
        "cuando": "el cambio llama a otro servicio, publica un evento o cambia un contrato compartido",
        "producto": {"sdd": ["Los servicios se cortan por contexto delimitado, cada uno con su base. Cada "
                             "interaccion entre servicios dice si es sincrona o por eventos, y por que."]},
        "spec": ["Si un AC cambia un contrato que otro servicio consume, declara la version nueva o los "
                 "pasos Expand-Contract, y los repos afectados en `microservicios`."],
        "construye": [
            "Database per Service: nunca leas ni escribas la base de otro servicio; pasa por su API o sus eventos.",
            "Toda llamada remota lleva timeout explicito y cortacircuito.",
            "Un contrato compartido (API o evento) cambia con version o con Expand-Contract, nunca rompiendo "
            "al consumidor desplegado.",
            "Propaga `X-Correlation-ID` o `traceparent` en cada llamada saliente y en cada evento.",
        ],
        "audita": [
            (BLOQUEANTE, "acceso a la base de datos de otro servicio (violacion de Database per Service)"),
            (BLOQUEANTE, "llamadas remotas sin timeouts ni circuit breakers"),
            (BLOQUEANTE, "breaking changes de APIs o eventos sin version ni Expand-Contract"),
            (MAYOR, "omision de correlation IDs (X-Correlation-ID o traceparent) en llamadas remotas o eventos"),
        ],
    },
    {
        "id": "construccion",
        "titulo": "Construccion y programacion defensiva (McConnell, Code Complete)",
        "ref": "code-complete-mcconnell.md",
        "cuando": "todo cambio de codigo",
        "producto": {"sdd": ["El SDD fija la estrategia de errores (que falla en voz alta y que se degrada) y "
                             "donde esta la barricada que valida los datos externos."]},
        "spec": ["Cada AC con un camino de error dice que ve el usuario o el consumidor cuando falla, "
                 "segun la estrategia de errores del SDD."],
        "construye": [
            "Ningun error tragado: un `catch` o manejador registra el motivo y relanza o devuelve el fallo; "
            "nunca simula exito.",
            "Barricada defensiva: los datos externos se validan y convierten en el adaptador o puerto de "
            "entrada; el dominio no recibe datos sucios.",
            "Donde el SDD o el dominio exige correccion, no inventes un valor por defecto (saldo, folio, "
            "estado): falla.",
            "El formato lo decide el formateador del stack, no tu criterio.",
        ],
        "audita": [
            (BLOQUEANTE, "errores tragados: `catch` vacios o manejadores que silencian la falla y simulan exito "
                         "(MAYOR si el fallo queda registrado pero no se propaga)"),
            (MAYOR, "ruptura de la barricada defensiva: el dominio procesa datos externos sin validar"),
            (MAYOR, "datos de negocio inventados (defaults no comprobados) donde se exige correccion estricta"),
        ],
    },
    {
        "id": "seguridad",
        "titulo": "Seguridad de aplicaciones (OWASP Top 10, CLASP)",
        "ref": "seguridad-owasp-y-zap.md",
        "cuando": "el cambio expone un endpoint, consulta datos, llama a una URL externa o toca credenciales",
        "producto": {"prd": ["El PRD incluye los casos de abuso: quien podria usar mal la funcionalidad y que "
                             "no debe poder hacer."],
                     "sdd": ["El diagrama de componentes marca las fronteras de confianza. Autenticacion, "
                             "cifrado y salidas a URLs externas van como `D-n`."]},
        "spec": ["Todo AC que expone un endpoint o una accion con permisos lleva al menos un AC negativo, "
                 "marcado `[negativo]`: que pasa SIN permiso, con entrada invalida o fuera del limite. "
                 "Si la feature no tiene nada que rechazar, dilo en `## Fuera de alcance`."],
        "construye": [
            "Por cada AC `[negativo]` el test de rechazo (401/403/422 o el error de dominio) se escribe "
            "antes que el camino feliz de ese AC.",
            "Consultas siempre parametrizadas: ninguna concatenacion de parametros en SQL, NoSQL, shell o scripts.",
            "Ningun secreto, token, clave ni certificado en el codigo, los tests, los fixtures o los commits.",
            "Todo acceso a datos filtra por el tenant y el usuario autenticado: nada de IDs que otro puede adivinar.",
            "Una peticion saliente a una URL que viene de fuera se valida contra una lista permitida y "
            "bloquea IPs privadas y metadata de la nube.",
        ],
        "audita": [
            (BLOQUEANTE, "inyeccion (A03): concatenacion dinamica de parametros en SQL/NoSQL, scripts o shell"),
            (BLOQUEANTE, "secretos o credenciales en el diff o en los commits (A02)"),
            (BLOQUEANTE, "control de acceso roto (A01): endpoints o queries que no filtran por tenant/usuario (IDOR)"),
            (MAYOR, "SSRF (A10): peticiones salientes a URLs externas sin lista permitida ni bloqueo de IPs privadas"),
            (MAYOR, "falta de tests negativos: endpoints con autenticacion o autorizacion sin un test de rechazo"),
            (MENOR, "configuracion insegura (A05): cabeceras de seguridad omitidas o stack traces expuestos"),
        ],
    },
    {
        "id": "documentacion",
        "titulo": "Versiones vigentes y documentacion oficial (Context7)",
        "ref": "context7-documentacion-oficial.md",
        "cuando": "el cambio agrega o sube una dependencia, o usa una API de una libreria o framework",
        "producto": {"sdd": ["El SDD declara la version mayor vigente de cada stack y de cada servicio externo, "
                             "contrastada con la documentacion oficial o Context7 del bloque del stack."]},
        "spec": ["Si el slice introduce una libreria o un servicio externo nuevo, nombralo en el plan: "
                 "es lo que el implementer contrasta contra la documentacion vigente."],
        "construye": [
            "Antes de usar una API de libreria o framework, contrastala con Context7 (`resolve-library-id`, "
            "`query-docs`) o con la documentacion oficial del stack: el bloque del stack trae el id y la URL.",
            "Ninguna API marcada como obsoleta (`@deprecated`).",
            "Si agregas o subes una dependencia, corre `stack.py auditar --repo <repo>`: exit 1 son "
            "vulnerabilidades, exit 2 es que no se pudo medir. Ninguno de los dos se da por bueno.",
            "Sin Context7 ni acceso web, dilo en la evidencia con la lista de dependencias nuevas: no des "
            "la verificacion por hecha.",
        ],
        "audita": [
            (BLOQUEANTE, "dependencias nuevas con vulnerabilidades conocidas de severidad alta o critica "
                         "(corre `stack.py auditar --repo <repo>` si el diff toca dependencias)"),
            (MAYOR, "uso de APIs obsoletas (`@deprecated`) o de una sintaxis que la documentacion vigente retiro"),
            (MAYOR, "auditoria de versiones sin hacer: si no tienes Context7 ni acceso web, escribe en el acta "
                    "'versiones y APIs sin contrastar' con la lista de dependencias nuevas"),
        ],
    },
    {
        "id": "comunicacion",
        "titulo": "Comunicacion ASD-STE100 y principios de Karpathy",
        "ref": "comunicacion-ste100-y-prompts.md",
        "cuando": "todo cambio",
        "producto": {"prd": ["Historias y criterios en frases de hasta 20 palabras, voz activa, sin sinonimos ambiguos."],
                     "sdd": ["Componentes e interacciones en diagramas Mermaid; ningun parrafo de mas de 3 lineas."]},
        "spec": ["Cada AC es atomico y comprobable en menos de 5 minutos: frases de hasta 20 palabras, voz activa."],
        "construye": [
            "Micro-reportes y evidencia en frases de hasta 20 palabras, voz activa, con `archivo:linea`.",
            "Sin alcance no pedido: lo que ningun AC pide no se escribe.",
        ],
        "audita": [
            (MENOR, "tu propia acta: cada hallazgo en una frase de hasta 20 palabras, voz activa, con "
                    "`archivo:linea`; sin parrafos decorativos"),
        ],
    },
    {
        "id": "revision",
        "titulo": "Entrega predecible y code review pragmatico (Gergely Orosz)",
        "ref": "ingenieria-software-gergely-orosz.md",
        "cuando": "todo cambio",
        "producto": {"prd": ["Objetivos y no-objetivos con nombre (`O-n`, `NO-n`); cada candidata cabe en 1 a 3 dias."],
                     "sdd": ["Cada `D-n` trae contexto, alternativa descartada y lo que queda fuera de alcance."]},
        "spec": ["El slice cabe en 1 a 3 dias y dice que queda fuera (`## Fuera de alcance`)."],
        "construye": [
            "Incrementos chicos: un paso que supera ~50 lineas o 3 archivos se parte.",
            "Regla del Boy Scout dentro del slice: deja lo que tocas un poco mejor, sin salir del alcance.",
        ],
        "audita": [
            (MENOR, "cero nitpicking: el formato y el estilo cosmetico no son hallazgos; las sugerencias van "
                    "a '## Observaciones' y NO abren otra ronda"),
        ],
    },
]


def comando(script: str, *args: str) -> str:
    """Un comando listo para pegar: interprete y script con ruta absoluta.

    El brief lo imprime para que un agente delegado lea una skill o una
    referencia sin tener `$PY`/`$H` en su entorno y sin depender de que su host
    le deje abrir archivos fuera del proyecto.
    """
    import re
    import shlex
    import sys

    def cita(x: str) -> str:   # un hueco como <nombre> se deja a la vista, sin comillas
        return x if re.fullmatch(r"<[\w -]+>", x) else shlex.quote(x)
    return " ".join(cita(x) for x in (sys.executable, str(Path(__file__).resolve().parent / script), *args))


def ruta_referencia(nombre: str) -> Path | None:
    """El archivo de references/ que nombra `nombre`: el id de una norma o el nombre del archivo."""
    por_id = {n["id"]: n["ref"] for n in NORMAS}
    archivo = por_id.get(nombre, nombre)
    if not archivo.endswith(".md"):
        archivo += ".md"
    ruta = REFERENCIAS / archivo
    # Solo archivos de references/: el nombre no puede salir de la carpeta.
    return ruta if ruta.is_file() and ruta.resolve().parent == REFERENCIAS.resolve() else None


def referencia(norma: dict) -> str:
    """Ruta absoluta de la referencia de una norma: abrible desde cualquier host."""
    return str(REFERENCIAS / norma["ref"])


def lineas_para_construir(con_spec: bool) -> list[str]:
    """El bloque del brief: lo que cumple quien escribe el spec y el codigo.

    `con_spec` agrega lo que el leader deja en el spec; se pide mientras el
    spec no esta sellado. Despues solo queda lo que hace el implementer.
    """
    L = ["", "=" * 72,
         "NORMAS DE INGENIERIA - las mismas que audita el revisor (su violacion es hallazgo)",
         "cada una aplica solo si el cambio toca su materia; detalle en " + str(REFERENCIAS) + "/<ref>",
         "para leer una referencia sin abrir el archivo: " + comando("normas.py", "--ref", "<id>"),
         "=" * 72]
    for n in NORMAS:
        L.append(f"[{n['id']}] {n['titulo']} · alcance: {n['cuando']} · ref: {n['ref']}")
        if con_spec:
            L += [f"  en el spec: {x}" for x in n.get("spec", [])]
        L += [f"  - {x}" for x in n["construye"]]
    return L


def lineas_para_producto(doc: str) -> list[str]:
    """El bloque que recibe el rol producto al crear el borrador de `doc` (prd o sdd)."""
    L = ["", "=" * 72,
         f"NORMAS DE INGENIERIA - lo que el {doc.upper()} deja escrito (el spec, el codigo y el review las heredan)",
         "cada una aplica solo si el producto toca su materia; detalle en " + str(REFERENCIAS) + "/<ref>",
         "para leer una referencia sin abrir el archivo: " + comando("normas.py", "--ref", "<id>"),
         "=" * 72]
    for n in NORMAS:
        for x in n["producto"].get(doc, []):
            L.append(f"[{n['id']}] {n['titulo']} · ref: {n['ref']}")
            L.append(f"  - {x}")
    return L


ROLES = ("producto", "leader", "implementer pair", "implementer delegado", "revisor")


def cuadro() -> list[tuple[str, dict[str, bool]]]:
    """Norma x rol: True si el registro tiene que decirle a ese rol.

    Pair y delegado comparten `construye` a proposito: el brief es el mismo.
    """
    filas = []
    for n in NORMAS:
        construye = bool(n.get("construye"))
        filas.append((n["titulo"], {
            "producto": any(n.get("producto", {}).get(d) for d in ("prd", "sdd")),
            "leader": bool(n.get("spec")),
            "implementer pair": construye,
            "implementer delegado": construye,
            "revisor": bool(n.get("audita")),
        }))
    return filas


def lineas_cuadro() -> list[str]:
    L = ["| Norma | " + " | ".join(r.capitalize() for r in ROLES) + " |",
         "|---|" + "---|" * len(ROLES)]
    for titulo, celdas in cuadro():
        L.append(f"| {titulo} | " + " | ".join("Sí" if celdas[r] else "NO" for r in ROLES) + " |")
    return L


def lineas_para_revisar() -> list[str]:
    """Las instrucciones de auditoria del briefing del revisor, una por norma."""
    L = []
    for n in NORMAS:
        partes = "; ".join(f"{sev}: {texto}" for sev, texto in n["audita"])
        L.append(f"- Audita {n['titulo']} [{n['id']}] (alcance: {n['cuando']}; "
                 f"ref: {referencia(n)}). Detecta y clasifica: {partes}.")
    return L


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Normas de ingenieria del arnes, por rol")
    ap.add_argument("--rol", choices=["producto", "leader", "implementer", "revisor"], default="implementer")
    ap.add_argument("--doc", choices=["prd", "sdd"], default="sdd", help="con --rol producto")
    ap.add_argument("--cuadro", action="store_true", help="tabla norma x rol; exit 1 si una celda esta vacia")
    ap.add_argument("--ref", help="imprime una referencia: el id de una norma (seguridad, datos...) o el "
                                  "nombre de un archivo de references/ (vertical-slice)")
    a = ap.parse_args()
    if a.ref:
        ruta = ruta_referencia(a.ref)
        if ruta is None:
            import sys
            ids = ", ".join(n["id"] for n in NORMAS)
            archivos = ", ".join(sorted(x.stem for x in REFERENCIAS.glob("*.md")))
            print(f"[!!] normas: no hay referencia '{a.ref}'. Ids de norma: {ids}. Archivos: {archivos}",
                  file=sys.stderr)
            raise SystemExit(2)
        print(f"# referencia {ruta.name} ({ruta})\n")
        print(ruta.read_text(encoding="utf-8"))
        raise SystemExit(0)
    if a.cuadro:
        print("\n".join(lineas_cuadro()))
        raise SystemExit(0 if all(all(c.values()) for _, c in cuadro()) else 1)
    if a.rol == "producto":
        print("\n".join(lineas_para_producto(a.doc)))
    elif a.rol == "revisor":
        print("\n".join(lineas_para_revisar()))
    else:
        print("\n".join(lineas_para_construir(con_spec=(a.rol == "leader"))))
