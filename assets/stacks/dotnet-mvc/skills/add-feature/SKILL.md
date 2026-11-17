---
name: add-feature
description: Implementa una feature nueva de punta a punta en el portal .NET MVC: cliente de API, modelos de vista, controller, vistas Razor, navegación y pruebas, sin acceso a datos.
---

# Add Feature — CALPIL .NET MVC

## Objetivo y activación
Activar cuando se pide un conjunto nuevo de pantallas sobre un recurso que el portal aún no maneja. Coordina `add-api-client` y `add-page`. Requiere que la API ya exponga el recurso: el portal no lo implementa.

## Inspección obligatoria
Antes de escribir código, lee:
1. `.claude/rules/architecture.md`: reparto Model / View / Controller / Services.
2. Los archivos de Work Items en `src/Calpil.Template.Web/Controllers`, `Models`, `Views/WorkItems` y `Services`: la feature de referencia.
3. `src/Calpil.Template.Web/Views/Shared/_Layout.cshtml`: navegación.
4. `src/Calpil.Template.Web/Program.cs`: registro de clientes.
5. El contrato de la API para el recurso nuevo.

## Procedimiento ejecutable
1. **Confirmar que la API expone el recurso** y leer su contrato. Si falta, detenerse: primero se implementa en la API.
2. **Listar las pantallas** con su ruta, método, quién accede y cómo se presenta cada error de la API.
3. **Crear el cliente** `I<Recurso>Api`, su implementación, su contrato y su fake (skill `add-api-client`).
4. **Crear modelos de vista y formularios** en `Models/`.
5. **Crear el controller** `<Recurso>Controller` con rutas por atributo y acciones delgadas.
6. **Crear las vistas** en `Views/<Recurso>/` reutilizando parciales (skill `add-page` por cada pantalla).
7. **Agregar el enlace de navegación** en `_Layout.cshtml`.
8. **Escribir las pruebas** de páginas, sesión, formularios y cliente.
9. **Validar:** `make validate` y recorrer el flujo en el navegador contra la API local.

## Patrón de implementación
```text
src/Calpil.Template.Web/
  Services/IOrdersApi.cs  OrdersApiClient.cs  OrdersApiModels.cs
  Models/OrderViewModels.cs
  Controllers/OrdersController.cs
  Views/Orders/Index.cshtml  Details.cshtml  Create.cshtml
tests/Calpil.Template.Web.Tests/
  FakeOrdersApi.cs  OrdersPagesTests.cs  OrdersApiClientTests.cs
```

## Decisiones y anti-patrones
- **NO** implementar en el portal una regla o un dato que le corresponde a la API.
- **NO** agregar una base de datos, caché persistente o paquete de acceso a datos al portal.
- **NO** compartir un controller o una vista entre dos recursos distintos con condicionales.
- **NO** construir un generador genérico de formularios o tablas: cada pantalla es una vista.
- **NO** dejar páginas nuevas sin sesión por omisión.

## Verificación / Definition of Done
- Todas las pantallas tienen pruebas de contenido, de sesión y de errores.
- `ArchitectureTests` en verde sin modificarse.
- `make validate` sin fallas ni warnings.
- El flujo completo funciona en el navegador contra la API local.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Pantallas agregadas con sus rutas.
2. Operaciones de la API consumidas.
3. Archivos creados por carpeta.
4. Salida de `make validate` y supuestos sobre la API.
