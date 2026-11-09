# Ejemplos de uso de `/adr`

Ejemplos ilustrativos. **No representan ADR aprobados ni describen necesariamente el estado real de un repositorio.**

## Crear

```text
/adr draft Evaluar service discovery para BFF y APIs desplegadas en Kubernetes, comparando registro dinámico vs resolución por Kubernetes DNS. Analiza seguridad, migración, observabilidad, rollback y contratos.
```

Comportamiento esperado: inspeccionar el repo, identificar registry actual y nombres de Service observados, crear `docs/adr/ADR-XXXX-*.md` como `Propuesto`, justificar opciones, dejar pendientes verificables y ejecutar validación local.

## Comparar y decidir, sin fingir aprobación

```text
/adr draft Comparar PostgreSQL + Prisma frente a TypeORM para la persistencia de una API NestJS hexagonal; usa configuración y código reales del repo y separa norma corporativa de elección del producto.
```

Comportamiento esperado: no asumir que el repositorio ya migró ni inventar costos o benchmarks. Si la opción está mandada por una norma aprobada, indicar que las otras se evalúan para implementación/excepción, no como una elección abierta.

## Revisión

```text
/adr review docs/adr/ADR-0005-adopcion-prisma.md
```

Esperado: no editar sin permiso. Reportar bloqueantes, mayores y menores, evidencia por archivo, y sugerir redacción corregida.

## Reemplazo

```text
/adr supersede ADR-0003 porque el contrato público cambió y el modelo anterior rompía compatibilidad. Prepara una propuesta que conserve el razonamiento histórico.
```

Esperado: nuevo ID `Propuesto`, referencia al anterior, análisis de migración. **No marcar el anterior como Reemplazado** hasta una aprobación autorizada.

## Auditoría / inventario

```text
/adr audit docs/adr: detecta IDs duplicados, decisiones aprobadas con placeholders, referencias cruzadas rotas y conflictos de alcance.
/adr index actualiza docs/adr/README.md sin destruir contenido editorial
```

## Uso sin invocar slash command

```text
Necesito registrar por qué elegimos exponer solamente una API propia hacia los consumidores, dejando internas las APIs de terceros. Prepara un ADR propuesto, con alternativas, contratos y seguridad.
```

## Script auxiliar

```bash
# Crear un borrador con ID secuencial por repositorio
python3 .agents/skills/adr/scripts/adr_tool.py new \
  --title "Estrategia de exposición de APIs" --dir docs/adr \
  --scope "Plataforma" --owner "Equipo responsable"

# Validar todos los ADR del directorio
python3 .agents/skills/adr/scripts/adr_tool.py validate --dir docs/adr

# Previsualizar índice sin escribir
python3 .agents/skills/adr/scripts/adr_tool.py index --dir docs/adr

# Actualizar índice, respetando contenido ajeno a los marcadores
python3 .agents/skills/adr/scripts/adr_tool.py index --dir docs/adr --write

# Comprobar en CI que README esté actualizado
python3 .agents/skills/adr/scripts/adr_tool.py index --dir docs/adr --check
```
