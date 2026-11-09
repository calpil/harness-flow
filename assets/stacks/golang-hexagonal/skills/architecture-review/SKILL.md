---
name: architecture-review
description: Audita el backend en Go para verificar el estricto cumplimiento de los límites hexagonales, ausencia de dependencias cruzadas y pureza del dominio.
---

# Architecture Review — CALPIL Golang Engineering Skill

## Objetivo y activación
Activar antes de enviar un Pull Request o cuando se refactorice código para auditar que el proyecto mantenga las invariantes de la arquitectura hexagonal, no existan acoplamientos prohibidos y el dominio permanezca 100% puro.

## Inspección obligatoria
Antes de emitir conclusiones, inspecciona:
1. `internal/*/domain/`: Comprobar imports. Solo se permiten paquetes estándar de Go (`time`, `strings`, `errors`, `math`).
2. `internal/*/application/`: Comprobar imports. Solo se permite importar paquetes `domain` propios o paquetes estándar (`context`, `fmt`).
3. `internal/*/adapter/`: Verificar que los adaptadores dependan de `application/ports` y `domain`, pero nunca entre adaptadores paralelos.
4. `cmd/server/main.go`: Comprobar que sea el único punto donde se instancia y orquesta la infraestructura.

## Procedimiento ejecutable
1. **Analizar Imports de Dominio:** Ejecutar un escaneo de imports en `internal/*/domain/...` asegurando que no existan dependencias a `net/http`, `chi`, `pgx`, `sql` ni frameworks externos.
2. **Revisar Interfaces de Puertos:** Verificar que los puertos en `application/ports` no expongan estructuras específicas de bases de datos o transporte HTTP.
3. **Validar Encapsulamiento de Entidades:** Asegurar que los campos mutables de las entidades de dominio no se modifiquen arbitrariamente desde fuera sin pasar por métodos de negocio (ej. `ChangeStatus`).
4. **Comprobar Manejo de Errores:** Verificar que los adaptadores de salida traduzcan errores de infraestructura a errores centinela del dominio antes de retornarlos al servicio.
5. **Verificar Aislamiento de Features:** Comprobar que una feature no importe directamente adaptadores de otra feature; cualquier interacción debe ocurrir vía puertos de aplicación.
6. **Revisar Middlewares y Plataforma:** Asegurar que los middlewares transversales (Correlation ID, recovery, security headers) residan exclusivamente en `internal/platform/middleware/`.
7. **Generar Informe de Hallazgos:** Detallar incumplimientos, gravedad, archivo y línea, y proponer remediación inmediata.

## Patrón de implementación
Regla de dependencia hexagonal unidireccional:
```text
[ Transport / HTTP Handler ]  (adapter/in)
           │
           ▼
[ Use Case / Service ]        (application)
           │
     ┌─────┴───────────────┐
     ▼                     ▼
[ Domain Model ]   [ Repository Port ] (ports/out)
                           ▲
                           │
            [ Postgres / In-Memory Repo ] (adapter/out)
```

## Decisiones y anti-patrones
- **NO** tolerar imports de paquetes de infraestructura en `domain` o `application`.
- **NO** aceptar "atajos" donde un handler HTTP interactúe directamente con la base de datos sin pasar por un caso de uso.
- **NO** permitir dependencias circulares entre paquetes Go.

## Verificación / Definition of Done
- Todos los paquetes bajo `internal/*/domain` libres de imports de terceros.
- `go vet ./...` pasa sin observaciones.
- Pruebas unitarias y de integración pasando con `go test ./...`.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Lista de paquetes auditados.
2. Cumplimiento de pureza del dominio verificado.
3. Observaciones o hallazgos arquitectónicos detectados (si los hubiere).
4. Veredicto final: Conforme / No conforme.
