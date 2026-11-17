---
name: add-feature
description: Implementa una vertical funcional nueva en la API .NET layered: carpeta de feature con controller, service, repositorio Dapper, migración T-SQL, registro en Program.cs y pruebas.
---

# Add Feature — CALPIL .NET Layered

## Objetivo y activación
Activar cuando se pide un recurso o capacidad nueva que no cabe en una feature existente. Produce una carpeta hermana de `WorkItems/` con las tres capas, su tabla y sus pruebas, sin tocar otras features.

## Inspección obligatoria
Antes de escribir código, lee:
1. `src/Calpil.Template.Api/WorkItems/`: la feature de referencia, archivo por archivo.
2. `src/Calpil.Template.Api/WorkItems/WorkItemsServiceCollectionExtensions.cs` y `src/Calpil.Template.Api/Program.cs`: cómo se registra una feature.
3. `db/migrations/`: último número usado y estilo de los scripts.
4. `tests/Calpil.Template.Api.Tests/WorkItems/InMemoryWorkItemRepository.cs`: contrato que debe respetar el fake.
5. `.claude/rules/architecture.md`: límites entre capas.

## Procedimiento ejecutable
1. **Modelar:** entidad, campos, reglas, estados y errores. Si hay dudas de negocio, preguntar antes de crear tablas.
2. **Crear la carpeta `src/Calpil.Template.Api/<Feature>/`** con `<Entidad>.cs` (record interno), `<Feature>Dtos.cs` y, si aplica, el enum de estados con `ToCode`/`ParseCode`.
3. **Definir `I<Entidad>Repository`** con operaciones en términos del modelo, no de SQL.
4. **Escribir el service** con las reglas y sus `AppException`; el reloj es `TimeProvider`.
5. **Escribir las pruebas del service** con un fake en memoria que cumpla el contrato del repositorio.
6. **Agregar la migración** `db/migrations/NNNN_create_<tabla>.sql` y el repositorio Dapper (skill `add-persistence`).
7. **Escribir el controller** y sus pruebas HTTP (skill `add-api-endpoint`).
8. **Registrar la feature:** `Add<Feature>()` en su carpeta y una línea en `Program.cs`.
9. **Validar:** `make validate`.

## Patrón de implementación
```csharp
// <Feature>/<Feature>ServiceCollectionExtensions.cs
public static class OrdersServiceCollectionExtensions
{
    public static IServiceCollection AddOrders(this IServiceCollection services)
    {
        services.AddScoped<IOrderRepository, OrderRepository>();
        services.AddScoped<OrderService>();
        return services;
    }
}

// Program.cs
builder.Services.AddOrders();
```

## Decisiones y anti-patrones
- **NO** repartir la feature en carpetas por capa (`Controllers/`, `Services/`): es una carpeta por feature.
- **NO** reutilizar el repositorio de otra feature; si se necesitan sus datos, llamar a su service.
- **NO** registrar dependencias fuera de `Program.cs` y del `AddXxx()` de la feature.
- **NO** agregar código "por si acaso" (interfaces del service, mapeadores genéricos, clases base): solo lo que la feature usa.
- **NO** crear la tabla a mano en la base: siempre por migración.

## Verificación / Definition of Done
- Las tres capas existen y `LayeringTests` pasa sin modificarse.
- Pruebas de service, HTTP e integración de la feature en verde.
- La migración aplica en una base vacía y es idempotente al re-ejecutar el runner.
- `make validate` termina sin fallas ni warnings.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Archivos creados por capa y la migración agregada.
2. Endpoints expuestos y sus códigos de respuesta.
3. Reglas de negocio implementadas y `code` de cada error.
4. Salida de `make validate`.
