---
name: write-tests
description: Guía para escribir pruebas unitarias deterministas, adaptadores en memoria y pruebas de integración HTTP en Rust
---

# Estrategia y Escritura de Pruebas en Rust

## Objetivo y activación
Esta skill se activa cuando se requiere añadir o ampliar la cobertura de pruebas unitarias o de integración en el backend Rust, asegurando determinismo, rapidez y cobertura de casos límite.

## Inspección obligatoria
Antes de escribir pruebas:
- Revisar pruebas unitarias existentes en `crates/domain/src/model.rs`.
- Revisar pruebas de repositorio en `crates/infrastructure/tests/inmemory_repo_tests.rs`.
- Revisar pruebas de integración HTTP en `crates/api/tests/api_tests.rs`.
- Consultar las directrices de testing en `.claude/rules/testing.md`.

## Procedimiento ejecutable
1. **Identificar la capa a evaluar:** Determinar si la prueba pertenece a reglas de dominio puras (`crates/domain`), casos de uso (`crates/application`), adaptadores (`crates/infrastructure`) o API HTTP (`crates/api`).
2. **Escribir pruebas unitarias de dominio:** En el módulo correspondiente en `crates/domain`, crear casos para caminos felices, datos límite (longitud máxima de texto, caracteres en blanco) y transiciones de estado no permitidas.
3. **Escribir pruebas con fakes en memoria:** Para probar servicios o repositorios, instanciar `InMemoryWorkItemRepository` y validar comportamiento sin tocar bases de datos externas.
4. **Escribir pruebas de integración HTTP:** En `crates/api/tests/api_tests.rs`, construir el router con `build_app(service)` y usar `app.oneshot(req)` para comprobar estatus HTTP (`200`, `201`, `400`, `404`), cabeceras y payloads JSON.
5. **Verificar assertions de Problem Details:** Comprobar que los errores devuelvan `Content-Type: application/problem+json` y los campos RFC 7807 correspondientes.
6. **Ejecutar la suite y comprobar tiempos:** Correr `cargo test` para certificar que todas las pruebas pasen en milisegundos de forma concurrente y aislada.

## Patrón de implementación
```rust
#[tokio::test]
async fn create_item_with_invalid_payload_returns_400() {
    let app = setup_test_app();
    let body = json!({ "title": "" });
    let req = Request::builder()
        .method("POST")
        .uri("/api/v1/work-items")
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from(serde_json::to_vec(&body).unwrap()))
        .unwrap();

    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}
```

## Decisiones y anti-patrones
- **No mocks mágicos ni reflection:** En Rust se prefieren traits limpios y fakes en memoria explícitos.
- **Aislamiento de pruebas:** Cada prueba debe crear su propio estado en memoria para permitir ejecución paralela sin interferencias.
- **Validar siempre códigos y headers:** No limitarse a verificar el cuerpo de la respuesta; validar siempre `StatusCode`, cabecera `Location` en creaciones y cabeceras de seguridad.

## Verificación / Definition of Done
- Pruebas añadidas y compilando sin advertencias.
- `cargo test --workspace` pasando al 100%.
- Tiempos de ejecución inferiores a 1 segundo para la suite completa.

## Contrato de entrega del agente
El agente reportará las pruebas nuevas añadidas, los casos límite cubiertos y el resultado de la ejecución con `cargo test`.
