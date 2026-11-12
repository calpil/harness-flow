# Normas de ingeniería: una lista para quien escribe y para quien revisa

Léelo cuando una norma no llegue a un rol, cuando quieras agregar o cambiar una,
o cuando el revisor bloquee por algo que el implementer dice no haber recibido.

## Qué problema resuelve

Las normas que salen de los libros de referencia vivían repartidas en prompts
distintos. El resultado, medido antes de este cambio:

- El briefing del revisor mandaba marcar sus violaciones como bloqueantes o
  mayores. El implementer en modo pair, que es el modo por defecto, no recibía
  ninguna: estaban solo en `agents/implementer.md`, el prompt del modo delegado
  en algunos hosts.
- OWASP, la construcción defensiva y STE100 se auditaban solo donde el revisor
  carga `agents/revisor.md`. Un host que recibe solo el briefing no las veía.
- El rol producto y el leader recibían unas sí y otras no, según la plantilla.

Ahora hay un registro, `scripts/normas.py`, y cada rol recibe su parte por la
salida de un script. Los prompts de `agents/` y `commands/` solo mandan a leer
esa salida: si contradicen al script, gana el script.

## El cuadro norma × rol

```bash
"$PY" "$H/normas.py" --cuadro      # exit 1 si una celda queda vacía
```

Son 12 normas y 5 columnas. Todas las celdas dicen "Sí" y un test falla si una
queda vacía (`tests/test_normas.py`).

| id | Norma | Referencia |
| --- | --- | --- |
| `datos` | Datos confiables (DDIA, Kleppmann) | `patrones-datos-ddia.md` |
| `diseno` | Filosofía de diseño (Ousterhout) | `filosofia-diseno-ousterhout.md` |
| `refactor` | Dos sombreros y code smells (Beck, Fowler) | `patrones-gof-y-refactoring.md` |
| `patrones` | Design Patterns (GoF) | `design-patterns-gof.md` |
| `rendimiento` | Algoritmos y estructuras de datos (CLRS) | `algoritmos-y-estructuras-clrs.md` |
| `ia` | Ingeniería de IA (Chip Huyen) | `ai-engineering-chip-huyen.md` |
| `servicios` | Microservicios y sistemas distribuidos (Sam Newman) | `microservicios-sam-newman.md` |
| `construccion` | Construcción y programación defensiva (McConnell) | `code-complete-mcconnell.md` |
| `seguridad` | Seguridad de aplicaciones (OWASP Top 10, CLASP) | `seguridad-owasp-y-zap.md` |
| `documentacion` | Versiones vigentes y documentación oficial (Context7) | `context7-documentacion-oficial.md` |
| `comunicacion` | ASD-STE100 y principios de Karpathy | `comunicacion-ste100-y-prompts.md` |
| `revision` | Entrega predecible y code review pragmático (Orosz) | `ingenieria-software-gergely-orosz.md` |

Cada norma dice a qué cambios aplica (`cuando`). Una feature sin llamadas a un
modelo de lenguaje no tiene nada que cumplir de la norma `ia`.

## Cómo llega a cada rol

| Rol | Script que la imprime | Qué recibe |
| --- | --- | --- |
| Producto | `producto.py borrador --doc prd\|sdd` | Lo que cada norma pide dejar en ese documento |
| Leader | `contexto.py brief --feature <id>`, con el spec sin sellar | Líneas `en el spec: ...` y lo que hará el implementer |
| Implementer, pair o delegado | `contexto.py brief --feature <id>` | Bloque `NORMAS DE INGENIERIA` |
| Revisor | `revision.py --feature <id> --briefing` | Una línea `- Audita ... [id]` por norma, con severidades |

- El bloque va fuera del recorte de `--max-lineas`: un brief recortado no lo pierde.
- Pair y delegado reciben lo mismo. No depende de `agents/implementer.md`.
- El briefing no repite el bloque del implementer: el revisor recibe qué
  auditar, no la lista de quien escribe.
- Para verlas sueltas: `"$PY" "$H/normas.py" --rol producto|leader|implementer|revisor [--doc prd|sdd]`.

Es igual en Claude Code, Hermes, Codex, Grok, AGY y Kimi: todos corren los
mismos scripts. `commands/*.md` y `agents/*.md` solo los lee Claude Code (y Kimi
con el plugin), y por eso no llevan la lista: llevan la instrucción de leerla.

## El invariante

Una norma cuyo incumplimiento el revisor clasifica como bloqueante o mayor tiene
siempre su instrucción para quien escribe. El revisor no bloquea por algo que al
implementer no se le dijo. Lo comprueba
`test_nada_que_el_revisor_bloquea_queda_sin_decir_a_quien_escribe`.

El revisor sigue clasificando una violación real como bloqueante o mayor. Lo que
cambió es que la lista es la misma en los dos lados.

## AC negativos

Un AC negativo dice qué pasa cuando NO debe funcionar: sin permiso, con entrada
inválida, fuera del límite. Se marca en su línea, igual que la costura:

```markdown
- AC-2 [costura: endpoint] [negativo]: sin token responde 401. `verificar: pytest tests/test_auth.py -q`
```

- `gate.py approve-spec` y `gate.py check-spec` avisan si un spec tiene un AC
  con costura `endpoint`, `api`, `http`, `rest`, `grpc` o `webhook` y ningún AC
  `[negativo]`. Es un aviso, no un bloqueo.
- El brief pide escribir el test de rechazo antes que el camino feliz.
- El revisor marca como hallazgo mayor un endpoint con permisos sin test de rechazo.
- Si la feature no tiene nada que rechazar, se dice en `## Fuera de alcance`.

## Documentación vigente y Context7, por stack

Cada stack declara en su `manifest.json` dónde contrastar versiones y APIs. El
brief, el briefing y el borrador del SDD lo imprimen en el bloque
`DOCUMENTACION VIGENTE DEL STACK <id>`.

```json
"documentation": {
  "official_docs": "https://go.dev/doc/",
  "security_advisories": "https://pkg.go.dev/vuln/",
  "context7": {
    "library_id": "/golang/go",
    "ecosystem": "go",
    "suggested_queries": ["Go net/http routing and middleware"]
  }
},
"security_audit": {
  "command": "govulncheck ./...",
  "alternative_commands": ["./gradlew dependencyCheckAnalyze"],
  "findings_pattern": "has the following vulnerable packages",
  "minimum_version": "1.23.0"
}
```

| Clave | Para qué |
| --- | --- |
| `documentation.official_docs` | URL de la documentación oficial del stack |
| `documentation.context7.library_id` | Id real de Context7 (`/org/proyecto`). Se resuelve con `resolve-library-id`, no se inventa |
| `security_audit.command` | Escáner de dependencias que corre `stack.py auditar` |
| `security_audit.alternative_commands` | Otros escáneres válidos; corre el primero cuya herramienta exista. Opcional |
| `security_audit.findings_pattern` | Texto que delata hallazgos cuando el escáner sale con 0 (`dotnet list package --vulnerable`). Opcional |
| `security_audit.minimum_version` | Versión mínima recomendada del lenguaje o framework. Opcional |

La consulta a Context7 la hace el agente con el MCP de su host. Ningún script se
conecta a Context7. Cómo conectarlo por host:
[`context7-documentacion-oficial.md`](context7-documentacion-oficial.md).

`stack.py auditar --repo <ruta>` mide, no informa:

| Exit | Significado |
| --- | --- |
| 0 | El escáner corrió y está limpio |
| 1 | El escáner reportó hallazgos |
| 2 | No se pudo medir: escáner no instalado, stack sin escáner o repo sin stack |

Un exit 2 no es un verde. Un wrapper del repo (`./mvnw`, `./gradlew`) se busca
en el repo, no en el `PATH`. `--dast` (OWASP ZAP) es informativo y no cambia el
exit. Ningún gate corre `auditar` solo: lo corren el implementer y el revisor
cuando el diff toca dependencias.

## Agregar o cambiar una norma

1. Edita `NORMAS` en `scripts/normas.py`. Las cuatro partes son obligatorias:
   `producto` (`prd` o `sdd`), `spec`, `construye` y `audita`.
2. Pon en `audita` la severidad de cada hallazgo: `BLOQUEANTE`, `MAYOR` o `MENOR`.
3. Si citas una referencia nueva, créala en `references/` y agrégala a la tabla
   de `SKILL.md`.
4. Corre `"$PY" "$H/normas.py" --cuadro` y `tests/test_normas.py`.

No hace falta tocar `commands/`, `agents/` ni `SKILL.md`: el brief y el briefing
imprimen la norma nueva en la siguiente llamada.

## Qué está garantizado y qué no

- **Garantizado**: que cada rol recibe su parte, en cualquier host y en
  cualquier modo.
- **No garantizado**: que el código cumpla una norma. Eso lo decide el revisor.
  Ningún script analiza el código contra las normas; los límites de capas sí los
  mide `check-architecture.py` de cada stack (ver
  [`arquitectura-heredada.md`](arquitectura-heredada.md)).

## Tests

- `tests/test_normas.py`: registro, cuadro, brief, briefing, AC negativos,
  documentación por stack, `auditar`, plan de refactor y textos por host.
- `tests/test_normativa_por_rol.py`: índice de skills, rol producto,
  restricciones de arquitectura y modo pair al aprobar el spec.
