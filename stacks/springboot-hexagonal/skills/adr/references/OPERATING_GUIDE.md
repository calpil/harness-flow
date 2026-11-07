# Architectural Decision Records / Governance — Playbook técnico de ejecución


## Esquema de decisión completo

| Bloque | Pregunta de calidad |
|---|---|
| Contexto | ¿Qué falla o cuesta hoy, con evidencia cuantitativa si hay? |
| Driver | ¿Qué requisitos no funcionales son innegociables? |
| Alcance | ¿Política corporativa vs solución local? |
| Alternativas | ¿Qué 2-4 opciones viables se evaluaron y por qué? |
| Selección | ¿Cuál tradeoff se acepta explícitamente? |
| Riesgos | ¿Cuál es el peor fallo probable y su mitigación? |
| Impactos | ¿Qué cambia en BFF/API, datos, security, infra, operación? |
| Rollback | ¿Cómo revertir o reevaluar sin borrar historia? |
| Gobierno | ¿Quién decide, quién consulta, dónde consta aceptación? |
| Evidencia | ¿Qué tests, POCs, métricas o links sostienen la conclusión? |

## Flujo propuesto / revisión / supersession

1. Descubrir `docs/adr` actual, listar numéricos y status, evitar IDs duplicados.
2. Crear propuesta con status **Proposed** y fecha real si está disponible.
3. Añadir matriz de alternativas con beneficios, costos, riesgos, lock-in, seguridad y reversibilidad.
4. Separar hechos medidos, supuestos y pendientes; no redactar “se decidió” cuando aún se evalúa.
5. Definir criterios de aceptación y “qué evidencia haría cambiar la decisión”.
6. En aprobación, registrar autoridad y enlace real; no promover a Accepted automáticamente.
7. En supersession, crear nuevo ADR, declarar `Supersedes ADR-XXXX`, vincular inverso desde histórico **sin alterar su razón original**.
8. Actualizar índice y validar links/IDs con herramienta empaquetada.

## Caso real del template

Hay un ADR histórico de persistencia que hace referencia a Flyway y código Java/`pom.xml` que implementa Liquibase. No cambiar retroactivamente texto de decisión aceptada. Abrir ADR de cambio/supersession explicando drivers técnicos, compatibilidad con el historial, estrategia de migraciones, riesgo y fecha real de aceptación.

## Matriz de alternativa realista de ejemplo

**Problema ilustrativo**: decidir boundary de publicación de eventos para un caso de uso transaccional.

| Opción | Pros | Contras | Evidencia requerida |
|---|---|---|---|
| Publicación inline después de save | sencilla | posible evento sin commit, fallos | test de rollback |
| Outbox transaccional | consistente con DB | complejidad/operación | recovery/replay test |
| No publicar eventos | mínima superficie | pierde consumidores asíncronos | aceptación del negocio |

La elección NO es universal; evaluar costos, semántica de duplicados y capacidades reales del producto antes de redactar decisión.

## Herramienta

```bash
python3 .claude/skills/adr/scripts/adr_tool.py --help
python3 -m unittest discover -s .claude/skills/adr/scripts -p 'test_*.py'
```

Consultar help concreto antes de correr subcomandos, porque nombres de CLI dependen de la herramienta que existe en este ZIP. El agente no debe asumir `--approve` o autocommits.

## Gate final

- [ ] ADR ID unique and index current
- [ ] scope corporativo vs producto explicit
- [ ] multiple alternatives with tradeoffs and evidence
- [ ] real status/authority, no fabricated approval
- [ ] historical accepted ADRs unchanged
- [ ] decision consequences and reevaluation tests concrete

## Umbrales para crear ADR

- **Sí**: nueva frontera entre servicios, adoptar/cambiar ORM o migrador, cambiar estrategia de consistencia, renovar patrón de auth, elegir contrato de plataforma que afecta varios equipos.
- **No necesariamente**: rename de variable, fix sin tradeoff, cambio local de mapping o test que no altera decisiones.
- **Propuesto**: decisión aún sujeta a aprobación, POC o métricas incompletas.
- **Aceptado**: solo si aprobación y decisión se acreditan realmente.

## Comparación controlada

Antes de seleccionar opción, definir pesos y origen. Cuando no existan medidas, usar valoración ordinal y marcar `SUPUESTO`; nunca presentar puntuación subjetiva como benchmark. Explicar por qué una alternativa rechazada volvería a ser válida ante nuevos requisitos.

### Formato de conclusión

```text
Decisión propuesta: <texto claro en presente>
Condiciones de adopción: <validaciones y responsables>
Hipótesis que podría invalidarla: <cambio de escala/costo/compliance>
Plan de reversión: <mecanismo y costos>
Aprobación: PENDIENTE hasta evidencia formal
```

Los ADR corporativos pueden establecer política y excepciones; el producto no puede eludirlos simplemente creando un ADR local contradictorio.
