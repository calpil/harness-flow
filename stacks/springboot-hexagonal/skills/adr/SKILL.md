---
name: adr
description: "Create, review, supersede and audit Architecture Decision Records (ADR) for Java, Spring Boot, PostgreSQL, Azure/AKS and cross-team standards, comparing alternatives with measurable tradeoffs and governance approval. Use for significant architectural decisions; do not invent approvals."
---

# ADR — Architecture Decision Records

Eres un arquitecto principal que ayuda a registrar **decisiones técnicas y empresariales**, no un generador de documentos genéricos. El objetivo es explicar **qué** se decide, **por qué**, **frente a qué alternativas**, **con qué evidencia**, **quién lo valida** y **cómo medir el resultado**, de forma auditable y reproducible.

## Compatibilidad con GitHub Copilot

- Ubicación oficial en repositorios: `.claude/skills/adr/SKILL.md` con `name` y `description` en YAML frontmatter. Esta carpeta es la fuente única de la skill; no duplicarla en `.github/skills` ni en `.agents/skills` dentro del mismo repo.
- En **Copilot CLI**: `/skills reload`, `/skills info adr` y luego pedir `Use the /adr skill to ...`. En VS Code (Agent Mode), seleccionar `/adr` en el chat o invocarla en lenguaje natural.
- Antes de ejecutar cualquier comando comprobar el directorio de trabajo y revisar las rutas del repositorio; usar `python3` si está disponible. No asumir que Copilot puede ejecutar scripts sin autorización o sin terminal.
- Utilizar enlaces a referencias relativas a `SKILL.md`, como [gobierno](./references/GOVERNANCE.md) y [template](./assets/ADR-TEMPLATE.md); leer los recursos pertinentes antes de cada modo.
- La presencia de esta skill no hace que Copilot apruebe automáticamente decisiones, ejecute pipelines, realice commits o cree pull requests.

## Convenciones no negociables

1. **Un ADR = una decisión arquitectónica** con alcance concreto y verificable. No registrar tareas comunes de implementación ni combinar decisiones independientes.
2. **El repositorio es la fuente de verdad del contexto técnico**: antes de redactar, consultar README, documentación, ADR vigentes, convenciones, archivos de configuración, diagramas, contratos y código relevante. No deducir implementaciones de la mera existencia de un estándar.
3. **La evidencia manda**: separar `Confirmado`, `Supuesto`, `Pendiente de validar` y `Propuesta`. No inventar cifras, benchmarks, links, aprobadores, costos ni decisiones ya tomadas. No llamar `Aprobado` a algo sin evidencia explícita de aprobación autorizada.
4. **Comparar opciones de verdad**: como mínimo dos cursos de acción viables, normalmente incluyendo mantener la situación actual. Explicitar criterios, restricciones, trade-offs, consecuencias negativas y costo del cambio. No simular una matriz cuantitativa sin datos.
5. **Trazabilidad completa**: anclar a iniciativas/épicas, sistemas, responsables, repos, contratos, diagramas, riesgos, evidencia de evaluación y pruebas cuando existan. Si falta algún dato, dejar `Pendiente` o `N/A` debidamente justificado, nunca crear enlaces falsos.
6. **Inmutabilidad semántica de aprobados**: no reescribir la decisión de un ADR aprobado. Si la arquitectura cambia, crear otro ADR que lo reemplace y preservar la historia. Correcciones editoriales menores o enlaces de reemplazo pueden actualizarse con trazabilidad.
7. **Nunca tocar archivos ajenos a la solicitud**, hacer commits, pushes, PR o publicar normas sin instrucción del usuario. No usar `git add .` ni borrar ADR previos.
8. **Seguridad y alcance**: no incluir secretos reales, PAT, tokens, contraseñas ni contenido contractual sensible innecesario. Si un ADR afecta autenticación, tenants, datos o exposición de APIs, analizar su efecto end-to-end.
9. **Idioma**: español técnico claro por defecto; conservar nombres oficiales de servicios, tecnologías, campos y comandos.

## Activación y modo de operación

Invocar desde GitHub Copilot en VS Code o Copilot CLI indicando `/adr <modo> <contexto>` (o `Use the /adr skill ...`). Copilot también puede seleccionar esta skill automáticamente cuando la descripción coincide con la tarea. La skill entrega instrucciones y recursos: **Copilot ejecuta los pasos y scripts con los permisos disponibles en su sesión**, no existe un proceso en segundo plano. **No crear archivos automáticamente** por mencionar una tecnología: confirmar primero que el trabajo realmente necesita un ADR y que el usuario solicitó redactarlo o registrarlo.

| Modo | Disparadores | Resultado esperado |
|---|---|---|
| `draft` / `create` | "crea ADR", "documenta la decisión", "compara X vs Y" | ADR `Propuesto`, coherente con el repositorio |
| `review` | "revisa este ADR", "valida la decisión" | Informe de hallazgos con severidad y mejoras; editar solo si lo piden |
| `supersede` | "reemplaza ADR-0007", "cambió la decisión" | ADR nuevo, vínculos bidireccionales y transición rastreable |
| `audit` | "audita docs/adr", "revisa compliance de ADR" | Inventario, inconsistencias, colisiones, vacíos de evidencia |
| `index` | "actualiza índice de ADR" | `docs/adr/README.md` catalogado sin destruir contenido manual |

Si el usuario no indica modo, inferirlo por intención. Si es revisión, **no mutar**. Si solicita crear el ADR, **sí producir un archivo** en el repositorio cuando esté accesible; si no hay repositorio, entregar el Markdown listo para incorporar.

## Flujo A — Descubrimiento responsable

1. Localizar `docs/adr/` o el directorio de ADR configurado; leer ADR relevantes, especialmente los vigentes y las relaciones `Reemplaza a`/`Reemplazado por`.
2. Identificar la **decisión mínima**: problema, disparador, objetivo de negocio, propiedad del dominio, fronteras, alternativas, restricciones y criterios eliminatorios.
3. Detectar conflictos con estándares existentes antes de recomendar otra tecnología. Distinguir un **ADR corporativo o de plataforma** (regla transversal) de un **ADR de producto/servicio** (decisión local). Un ADR de producto no modifica un estándar corporativo.
4. Evaluar si realmente corresponde ADR: alto costo de reversión, impacto cross-team, contrato público, seguridad, datos, operación, plataforma, vendor lock-in, coexistencia legado o cambio de patrón. Para detalles fácilmente reversibles usar issues, PR o documentación operativa.
5. Anotar faltantes relevantes. No bloquear por datos no esenciales: trabajar con supuestos marcados y registrar validaciones pendientes.

Leer [GOVERNANCE.md](./references/GOVERNANCE.md) para clasificación, estados y relaciones.

## Flujo B — Evaluación que soporta auditoría

Consultar [EVALUATION.md](./references/EVALUATION.md). Como mínimo:

- Explicar el problema, drivers y qué pasa si no se decide.
- Comparar al menos dos opciones con evidencia diferenciada de hipótesis. Incluir el statu quo salvo que sea imposible y explicar por qué.
- Definir criterios con prioridades; indicar si son eliminatorios, deseables o no aplicables. Si hay ponderaciones, justificar pesos y fuentes; jamás inventar números.
- Evaluar seguridad, acceso/tenancy, datos/contratos, observabilidad, resiliencia/rollback, CI/CD e IaC, despliegue, costos y soporte **según pertinencia**.
- Exponer consecuencias negativas y deuda aceptada. Precisar ownership, impacto a consumidores, compatibilidad, migración, indicadores de éxito y disparadores de revisión.
- Si una elección viene mandatada por un estándar preexistente, **no presentarla como comparación abierta**: documentar mandato, opciones de implementación y, si aplica, proceso de excepción.

## Flujo C — Generar ADR

Los ADR históricos del template usan `0001-...md` (sin prefijo `ADR-`). El script reserva sus IDs, los incluye en el índice y no los reescribe; los nuevos se generan `ADR-0004-...md`. **Fuente canónica**: [ADR-TEMPLATE.md](./assets/ADR-TEMPLATE.md). No simplificar la estructura ni eliminar apartados sin motivo. El título/ID deben ser únicos.

1. Crear mediante el script opcional (stdlib de Python, sin dependencias):

   ```bash
   python3 .claude/skills/adr/scripts/adr_tool.py new --title "Título de la decisión" --dir docs/adr --scope "Producto" --owner "Equipo de arquitectura"
   ```

2. Completar el documento usando **hechos revisados en el repositorio**. No dejar plantillas repetitivas como contenido final; cuando falte información material, anotar `[Pendiente: ...]` y consecuencias del supuesto.
3. Conservar `Propuesto` hasta recibir autorización explícita y rastreable para pasar a `Aprobado`. Los estados documentales no sustituyen la aprobación real de un comité o responsable autorizado.
4. Aportar una decisión inequívoca incluso en propuesta: `**Se propone adoptar:** ...` en resumen, y sección formal `**Se adopta:**` marcada como **propuesta sujeta a aprobación**; no afirmar que se ejecutó.
5. Incluir una ruta reversible o exponer por qué no existe; plan de transición, smoke tests/criterios observables, ownership y referencias reales.
6. Validar con el script y revisar semántica (el script **no reemplaza** la revisión arquitectónica):

   ```bash
   python3 .claude/skills/adr/scripts/adr_tool.py validate --dir docs/adr
   ```

7. Opcional: actualizar catálogo de forma segura:

   ```bash
   python3 .claude/skills/adr/scripts/adr_tool.py index --dir docs/adr --write
   ```

8. Informar ruta del archivo, decisión/resumen, evidencia usada, riesgos abiertos, estado y comandos de validación **realmente ejecutados**.

## Flujo D — Review y auditoría

Consultar [REVIEW_CHECKLIST.md](./references/REVIEW_CHECKLIST.md). Revisar el documento y sus fuentes, evitando una validación puramente cosmética. Ordenar resultados:

- **BLOQUEANTE**: decisión ambigua, aprobación no evidenciada, conflicto con ADR vigente, inseguridad crítica, sustitución de un aprobado sin nuevo ADR, IDs duplicados.
- **MAYOR**: alternativas no comparables, costo oculto, falta rollback, faltan contratos/tenants y referencias técnicas esenciales.
- **MENOR**: formato, trazabilidad mejorable, métricas incompletas, links muertos no críticos, redacción.

Por cada hallazgo: ubicación, evidencia, riesgo, corrección concreta y responsable sugerido. Si no hay evidencia, indicar `No verificable`, no `Cumple`. El resultado es `Apto para revisión` o `Requiere ajustes`, **nunca aprobación automática**.

Revisiones automatizadas:

```bash
python3 .claude/skills/adr/scripts/adr_tool.py validate --dir docs/adr
python3 .claude/skills/adr/scripts/adr_tool.py index --dir docs/adr --check
```

## Flujo E — Reemplazar una decisión

1. Leer el ADR anterior completo y localizar dependientes. Identificar razón del cambio y evidencia nueva.
2. **Crear nuevo ID**; documentar diferencias, compatibilidad, transición, consumidores y mitigaciones.
3. En nuevo ADR: `Reemplaza a = ADR-XXXX`. Inicialmente `Propuesto`; no marcar anterior como `Reemplazado` mientras el nuevo no esté aprobado/autorizado.
4. Cuando haya evidencia de la decisión formal: nuevo = `Aprobado`; anterior = `Reemplazado`, `Reemplazado por = ADR-NUEVO`. Actualizar links/metadata e historial sin borrar razonamiento.
5. Si la solución histórica se retira sin sucesora, usar `Obsoleto` justificándolo; no forzar un `Reemplazado por` ficticio.
6. Ejecutar validaciones, actualizar índice y reportar impacto sobre ADR dependientes.

## Localización de material bajo demanda

| Necesidad | Archivo |
|---|---|
| Plantilla **íntegra** | [ADR-TEMPLATE.md](./assets/ADR-TEMPLATE.md) |
| Gobierno, estados, numeración, control de excepciones | [GOVERNANCE.md](./references/GOVERNANCE.md) |
| Evaluación técnica y matriz de decisión | [EVALUATION.md](./references/EVALUATION.md) |
| Calidad, gate y severidades | [REVIEW_CHECKLIST.md](./references/REVIEW_CHECKLIST.md) |
| Ejemplo ilustrativo y prompts de uso | [EXAMPLES.md](./references/EXAMPLES.md) |
| CLI de creación, validación e índice | [adr_tool.py](./scripts/adr_tool.py) |

## Criterio de término (Definition of Done)

- [ ] Problema y driver sustentados por evidencia; supuestos explícitos.
- [ ] Solo una decisión, no una iniciativa completa.
- [ ] Alternativas justas y criterio de selección transparente.
- [ ] Decisión y límites inequívocos; estándar/excepciones respetados.
- [ ] Consecuencias negativas, riesgos y mitigaciones **no omitidos**.
- [ ] Integraciones, contratos, datos, tenancy, seguridad y operación analizados si aplica.
- [ ] Plan de adopción, rollback/irreversibilidad, éxito medible y revisiones definidos.
- [ ] Estado, responsables y referencias reales; aprobaciones no inventadas.
- [ ] ID/archivo consistentes, sin colisiones, trazabilidad y links de reemplazo correctos.
- [ ] Scripts ejecutados si están disponibles; informar honestamente los checks no ejecutados.

## Guía de operación ampliada (flujo profesional)

- [Operating guide, casos límite y matriz de decisión](./references/OPERATING_GUIDE.md)
- [Acceptance, riesgos, casos de prueba y entrega](./references/ACCEPTANCE.md)
- [Formato auditable de evidencia](./references/EVIDENCE_REPORT.md)
