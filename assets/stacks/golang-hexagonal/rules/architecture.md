---
description: Protección de límites de arquitectura hexagonal en Golang
globs: ["internal/**", "cmd/**"]
---

# Reglas de Arquitectura Hexagonal en Golang

- **Capa Domain (`internal/*/domain/**`):**
  - Solo Go estándar (`time`, `strings`, `errors`).
  - Prohibido importar paquetes de transporte (`net/http`, `chi`), persistencia (`pgx`, `sql`) o frameworks.
  - Las entidades protegen sus invariantes de negocio mediante métodos de fábrica y constructores explícitos.
- **Capa Application (`internal/*/application/**`):**
  - Define interfaces de entrada (`ports/in.go`) y puertos de salida (`ports/out.go`).
  - Solo depende de `domain` y de sus propios puertos. Nunca de adaptadores concretos ni librerías de infraestructura.
- **Capa Adapters In (`internal/*/adapter/in/**`):**
  - Traduce peticiones HTTP (Chi router, DTOs, validaciones) a comandos de casos de uso.
  - Errores de negocio mapeados explícitamente a RFC 7807 `ProblemDetail`.
- **Capa Adapters Out (`internal/*/adapter/out/**`):**
  - Implementa puertos de salida (persistencia en memoria, PostgreSQL con pgx, logs de eventos, reloj del sistema).
  - Mapeo bidireccional estricto entre registros/tablas y entidades de dominio; sin entidades de persistencia en el dominio.
- **Capa Platform y Composition Root (`internal/platform/**`, `cmd/server/main.go`):**
  - Configuración, middlewares transversales (Correlation ID, structured logging, recovery) y health checks.
  - `cmd/server/main.go` es el único punto autorizado para instanciar y cablear adapters con use cases.
