---
name: add-feature
description: Implementa una nueva vertical funcional completa en .NET / C# siguiendo Clean Architecture, puertos de entrada/salida, adaptadores Dapper y controllers.
---

# Add Feature — CALPIL .NET Engineering Skill

## Objetivo y activación
Activar cuando se requiera implementar una nueva vertical o bounded context de negocio (ej. pagos, notificaciones, usuarios) en la solución .NET. Guía la creación de modelos en `Domain`, casos de uso en `Application`, persistencia Dapper en `Infrastructure` y controladores en `WebApi`.

## Inspección obligatoria
Antes de escribir código, inspecciona:
1. `src/Calpil.Template.Domain/WorkItems/`: La vertical `WorkItems` como referencia arquitectónica canónica del repositorio.
2. `src/Calpil.Template.Application/WorkItems/`: Estructura de puertos, commands y services.
3. `src/Calpil.Template.Infrastructure/Persistence/`: Adaptadores Dapper e InMemory.
4. `src/Calpil.Template.Infrastructure/DependencyInjection.cs`: Registro de dependencias.

## Procedimiento ejecutable
1. **Modelar la Entidad de Dominio:** En `Calpil.Template.Domain/<Feature>/`, definir la entidad, value objects, eventos de dominio y excepciones específicas. Escribir constructores privados con métodos estáticos `Create` y `Hydrate`.
2. **Definir Puertos de Aplicación:** En `Calpil.Template.Application/<Feature>/Ports/`, declarar el puerto de salida `I...Repository` y el puerto de entrada `I...UseCase`.
3. **Implementar el Servicio de Aplicación:** En `Calpil.Template.Application/<Feature>/Services/`, implementar la lógica de orquestación, eventos y llamadas al repositorio.
4. **Implementar el Repositorio InMemory:** En `Calpil.Template.Infrastructure/Persistence/InMemory/`, crear la implementación concurrente segura con `ConcurrentDictionary`.
5. **Implementar el Repositorio Dapper:** En `Calpil.Template.Infrastructure/Persistence/Dapper/`, escribir las consultas SQL parametrizadas y script de migración DDL correspondiente.
6. **Crear el Controlador MVC:** En `Calpil.Template.WebApi/Controllers/`, implementar las acciones REST delegando en `I...UseCase`.
7. **Registrar en Inyección de Dependencias:** Registrar use case y repositorios en `Calpil.Template.Infrastructure/DependencyInjection.cs`.
8. **Escribir Pruebas:** Crear pruebas unitarias de dominio en `Domain.Tests`, pruebas de servicio en `Application.Tests` y pruebas HTTP en `WebApi.Tests`.

## Patrón de implementación
```text
src/
├── Calpil.Template.Domain/<Feature>/
│   ├── <Entity>.cs
│   ├── Events/
│   └── Exceptions/
├── Calpil.Template.Application/<Feature>/
│   ├── Commands/
│   ├── DTOs/
│   ├── Ports/
│   └── Services/
├── Calpil.Template.Infrastructure/Persistence/
│   ├── InMemory/
│   └── Dapper/
└── Calpil.Template.WebApi/Controllers/
```

## Decisiones y anti-patrones
- **NO** introducir dependencias circulares entre proyectos `.csproj`.
- **NO** omitir el adaptador InMemory; es esencial para pruebas rápidas y ejecución desacoplada.
- **NO** modificar la entidad de dominio directamente desde el controlador o el servicio; respetar los métodos de negocio de la entidad.

## Verificación / Definition of Done
- Pruebas unitarias de dominio pasando al 100%.
- Pruebas de aplicación y de integración pasando en `dotnet test`.
- Contrato OpenAPI actualizado en `api/openapi.yaml`.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Nombre de la nueva vertical y proyectos modificados.
2. Puertos de entrada y salida creados.
3. Repositorios implementados (InMemory y Dapper).
4. Evidencia de pruebas ejecutadas con éxito.
