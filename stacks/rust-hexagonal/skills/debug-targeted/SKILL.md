---
name: debug-targeted
description: Procedimiento sistemático para aislar, reproducir y corregir bugs en backend Rust mediante logs estructurados y pruebas focalizadas
---

# Depuración Focalizada en Rust

## Objetivo y activación
Esta skill se activa cuando se detecta un fallo en tiempo de ejecución, una prueba rota o un comportamiento anómalo en el backend Rust, guiando al agente en la reproducción y resolución quirúrgica del problema.

## Inspección obligatoria
Antes de modificar código:
- Inspeccionar el mensaje de error o traza de pánico de Rust (`RUST_BACKTRACE=1`).
- Identificar el crate y el módulo exacto donde se origina la falla.
- Revisar los logs emitidos mediante `tracing` con nivel DEBUG.
- Revisar el middleware de Correlation ID en `crates/api/src/middlewares/correlation_id.rs`.
- Consultar las reglas de testing en `.claude/rules/testing.md`.

## Procedimiento ejecutable
1. **Capturar la traza exacta:** Ejecutar el comando fallido con `RUST_BACKTRACE=1 cargo test -- --nocapture` para obtener el stacktrace completo y el número de línea.
2. **Reproducir con una prueba mínima:** Crear una prueba unitaria o de integración mínima que reproduzca el error de manera determinista sin efectos secundarios.
3. **Analizar la causa raíz:** Determinar si la falla es de invariante de dominio (`crates/domain`), orquestación de caso de uso (`crates/application`), concurrencia/persistencia (`crates/infrastructure`) o enrutamiento/serialización (`crates/api`).
4. **Aplicar la corrección quirúrgica:** Modificar el código fuente afectado preservando los comentarios y firmas existentes.
5. **Ejecutar la prueba focalizada:** Correr la prueba creada en el paso 2 para confirmar que pasa exitosamente: `cargo test --test {nombre_test}`.
6. **Ejecutar regresión completa:** Correr `cargo test` y `cargo clippy -- -D warnings` en todo el workspace para certificar que no se introdujeron regresiones.

## Patrón de implementación
```bash
# Ejecutar prueba individual con salida detallada
cargo test -p calpil-api --test api_tests create_and_get_work_item -- --nocapture
```

## Decisiones y anti-patrones
- **No silenciar errores con `unwrap()` o `expect()` descuidado:** Tratar los errores explícitamente mediante el operador `?` y conversiones tipadas.
- **No añadir `sleep` arbitrarios para resolver carreras:** Utilizar sincronización adecuada (`tokio::sync::RwLock`, channels de Tokio o semáforos).
- **Mantener determinismo:** Las pruebas de depuración no deben depender de la hora del sistema ni de conexiones de red externas.

## Verificación / Definition of Done
- La prueba focalizada que fallaba ahora pasa al 100%.
- `cargo test --workspace` pasa completamente sin fallos.
- `cargo clippy -- -D warnings` sin advertencias.

## Contrato de entrega del agente
El agente reportará la causa raíz identificada, el diff del cambio aplicado, la prueba de regresión agregada y la confirmación de la suite completa de pruebas.
