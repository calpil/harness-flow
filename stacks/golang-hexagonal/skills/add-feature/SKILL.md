---
name: add-feature
description: Implementa una nueva vertical funcional completa en Go siguiendo la arquitectura hexagonal, puertos de entrada/salida, adaptadores HTTP y persistencia.
---

# Add Feature — CALPIL Golang Engineering Skill

## Objetivo y activación
Activar cuando se requiera implementar una nueva vertical de negocio (ej. gestión de inventario, auditoría, órdenes) desde cero en el backend Go. Garantiza que la nueva funcionalidad respete el aislamiento de capas hexagonales, el encapsulamiento de entidades y la testabilidad.

## Inspección obligatoria
Antes de escribir código, inspecciona:
1. `internal/workitems/`: Tomar la feature `workitems` como referencia arquitectónica canónica del repositorio.
2. `internal/platform/config/`: Revisar configuración existente para determinar si la nueva feature requiere flags o variables de entorno.
3. `cmd/server/main.go`: Comprender el punto de composición y arranque del servidor.

## Procedimiento ejecutable
1. **Crear Estructura de Paquetes:** Crear la carpeta `internal/<feature>` con subcarpetas `domain`, `application/ports`, `application/services`, `adapter/in/http`, `adapter/out/persistence/inmemory` y `adapter/out/persistence/postgres`.
2. **Modelar el Dominio:** Definir entidades, value objects, eventos de dominio y errores centinela en `domain/`. Proteger invariantes mediante constructores como `New<Entity>`. Escribir pruebas unitarias en `domain/model_test.go`.
3. **Declarar Puertos:** Definir comandos e interfaces de entrada en `application/ports/in.go` y repositorios/eventos en `application/ports/out.go`.
4. **Implementar Servicio de Aplicación:** Crear el caso de uso en `application/services/service.go` orquestando dominio, puertos de persistencia y publicación de eventos.
5. **Implementar Adaptadores de Salida:** Crear el repositorio en memoria en `adapter/out/persistence/inmemory/` para tests y desarrollo local, y opcionalmente el repositorio PostgreSQL en `adapter/out/persistence/postgres/`.
6. **Implementar Adaptador HTTP:** Diseñar handlers Chi, DTOs y validaciones en `adapter/in/http/` registrando rutas bajo `/api/v1/<feature>`.
7. **Cablear en Composition Root:** Registrar y conectar la nueva feature en `cmd/server/main.go`.

## Patrón de implementación
```text
internal/<feature>/
├── domain/
│   ├── model.go       # Entidades e invariantes de negocio
│   ├── events.go      # Eventos de dominio
│   └── errors.go      # Errores centinela
├── application/
│   ├── ports/
│   │   ├── in.go      # Use case interfaces y commands
│   │   └── out.go     # Repository and publisher interfaces
│   └── services/
│       └── service.go # Orquestación de casos de uso
└── adapter/
    ├── in/http/       # Handlers Chi, DTOs y routers
    └── out/           # Adaptadores inmemory y postgres
```

## Decisiones y anti-patrones
- **NO** importar `internal/<feature>/adapter` dentro de `domain` o `application`.
- **NO** compartir bases de datos o tablas entre features sin pasar por contratos explícitos de aplicación.
- **NO** crear dependencias circulares entre paquetes de diferentes features.
- **NO** omitir el adaptador en memoria; es fundamental para pruebas rápidas y desarrollo desacoplado de infraestructura.

## Verificación / Definition of Done
- Pruebas unitarias de dominio pasando con `go test -v ./internal/<feature>/domain/...`.
- Pruebas de integración HTTP pasando con `go test -v ./internal/<feature>/adapter/in/http/...`.
- Suite global limpia: `go test -race ./...`.
- Endpoint registrado respondiendo correctamente en ejecución local.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Nombre de la nueva vertical y arquitectura de paquetes creada.
2. Puertos de entrada y salida expuestos.
3. Adaptadores implementados (HTTP, in-memory, SQL).
4. Evidencia de ejecución de tests unitarios y de integración.
