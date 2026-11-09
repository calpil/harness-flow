---
description: Protección de límites hexagonales, independiente de la feature de ejemplo
globs: ["src/main/java/**"]
---
- La regla se aplica a cualquier feature, no solo a `workitems`.
- `domain/**`: solo Java y otros tipos de dominio; sin Spring/JPA/HTTP/Jackson/cloud.
- `application/**`: puerto in/out y dominio; nunca depender de adapters concretos.
- `adapter/in/**`: traduce transportes a puertos in; no accede a JPA directo.
- `adapter/out/**`: implementa puertos out; traducción explícita de datos.
- `platform/**` y `configuration/**`: concern transversal/composition root.
- Fuente normativa: `docs/ai/ARCHITECTURE_RULES.md`. Verificar con ArchUnit al cambiar límites. Nunca acoplar el estándar a un nombre de ejemplo.
