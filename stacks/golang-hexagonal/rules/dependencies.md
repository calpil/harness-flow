---
description: Evaluación y gobierno de dependencias en Go
globs: ["go.mod", "go.sum"]
---

# Reglas de Dependencias en Golang

- Solo dependencias estables y auditadas en `go.mod`.
- Mantener siempre `go.sum` actualizado y consistente mediante `go mod tidy`.
- Prohibido agregar ORMs pesados o frameworks intrusivos que fuercen estructuras acopladas en capas internas.
- Verificar vulnerabilidades conocidas antes de introducir paquetes de terceros mediante `govulncheck` o auditoría de seguridad.
- Preferir librerías estándar o de impacto acotado en adapters (ej. `go-chi/chi/v5`, `jackc/pgx/v5`).
