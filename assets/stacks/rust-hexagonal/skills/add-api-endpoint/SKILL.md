---
name: add-api-endpoint
description: Guía paso a paso para añadir un nuevo endpoint HTTP en el backend Rust con Axum, OpenAPI, RFC 7807 y pruebas de integración
---

# Añadir Endpoint HTTP en Rust con Axum

## Objetivo y activación
Esta skill se activa cuando el agente necesita exponer una nueva ruta o verbo HTTP en el backend Rust utilizando el framework Axum (`crates/api`), conectándolo a través de casos de uso y serializando errores en formato RFC 7807 `application/problem+json`.

## Inspección obligatoria
Antes de escribir código, inspecciona:
- El router principal en `crates/api/src/lib.rs`.
- Los manejadores existentes en `crates/api/src/handlers/`.
- Los contratos y DTOs en `crates/api/src/dtos.rs` y `crates/application/src/dtos.rs`.
- El mapeador de errores estándar en `crates/api/src/problem_details.rs`.
- La especificación OpenAPI en `api/openapi.yaml`.

## Procedimiento ejecutable
1. **Definir DTOs de transporte:** Crear las estructuras de Request y Response en `crates/api/src/dtos.rs` con anotaciones `#[derive(Serialize, Deserialize)]`.
2. **Implementar el handler Axum:** Crear o extender una función asíncrona en `crates/api/src/handlers/` que reciba `State(state): State<Arc<AppState>>`, extractores tipados (`Path`, `Query` o `Json`), e invoque el caso de uso correspondiente.
3. **Mapear respuestas y errores:** Devolver `Result<impl IntoResponse, ProblemDetails>`, mapeando los errores de aplicación mediante `ProblemDetails::from`. Para creaciones, responder con `StatusCode::CREATED` y cabecera `Location`.
4. **Registrar la ruta en el Router:** En `crates/api/src/lib.rs`, vincular el verbo HTTP y la ruta (usando la sintaxis `{param}`) al nuevo handler.
5. **Actualizar OpenAPI:** Documentar la ruta, parámetros, payloads de petición y códigos de respuesta (`200/201`, `400`, `404`) en `api/openapi.yaml`.
6. **Escribir prueba de integración:** En `crates/api/tests/api_tests.rs`, agregar tests usando `tower::ServiceExt::oneshot` verificando códigos de estado, cabeceras y payloads.

## Patrón de implementación
```rust
pub async fn get_item_by_id(
    State(state): State<Arc<AppState>>,
    Path(id): Path<Uuid>,
) -> Result<impl IntoResponse, ProblemDetails> {
    let item = state.service.get_by_id(id).await.map_err(ProblemDetails::from)?;
    Ok(Json(item))
}
```

## Decisiones y anti-patrones
- **No acceder a la base de datos directamente:** El handler nunca debe contener lógica de negocio ni ejecutar consultas SQL. Siempre debe invocar puertos de entrada en `calpil-application`.
- **Rutas con llaves `{param}`:** Axum 0.8 prohíbe prefijos con dos puntos `:param`. Siempre usar `{id}`.
- **RFC 7807 estricto:** Los errores deben producir `application/problem+json` con campos `type`, `title`, `status` y `detail`.
- **Propagación de cabeceras:** La capa middleware asegura que `x-correlation-id` viaje en cada request y response.

## Verificación / Definition of Done
- `cargo check -p calpil-api` compila sin errores.
- `cargo test -p calpil-api` ejecuta las pruebas de integración pasando al 100%.
- El endpoint está documentado en `api/openapi.yaml`.
- Respuestas de error validadas con `application/problem+json`.

## Contrato de entrega del agente
El agente debe reportar el endpoint creado, la ruta registrada en el router de Axum, el archivo de pruebas ejecutado y la confirmación de `cargo test`.
