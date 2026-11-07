---
name: prepare-release
description: Guía de preparación y validación de releases, changelog, compilación release y contenedor Docker para producción
---

# Preparación de Releases en Rust

## Objetivo y activación
Esta skill se activa cuando se prepara una nueva versión o release para despliegue en staging o producción del backend Rust.

## Inspección obligatoria
Antes de generar una release:
- Revisar `CHANGELOG.md` y el historial de commits recientes.
- Inspeccionar las versiones en los `Cargo.toml`.
- Inspeccionar `Dockerfile` y `docker-compose.yml`.
- Inspeccionar `api/openapi.yaml`.

## Procedimiento ejecutable
1. **Actualizar versiones en Cargo:** Incrementar la versión semver correspondiente en los paquetes del workspace.
2. **Actualizar el CHANGELOG:** Documentar en `CHANGELOG.md` los cambios introducidos bajo las secciones Added, Changed, Fixed o Security siguiendo formato Keep a Changelog.
3. **Sincronizar OpenAPI:** Verificar que `api/openapi.yaml` refleje todos los endpoints y modelos de la versión.
4. **Validar build de producción:** Ejecutar `cargo build --release --bin server` para comprobar que la optimización de release compila sin errores.
5. **Ejecutar suite completa de calidad:** Correr `cargo test`, `cargo clippy -- -D warnings` y `node scripts/validate-agent-skills.mjs`.
6. **Verificar construcción de Docker:** Probar la construcción del contenedor de producción con `docker compose build api` o `docker build -t calpil-rust:latest .`.

## Patrón de implementación
```bash
# Comprobación de release y build optimizado
cargo build --release --bin server
node scripts/validate-agent-skills.mjs
```

## Decisiones y anti-patrones
- **No liberar con advertencias de compilación:** Exigir `-D warnings` en clippy antes de taggear una release.
- **Contenedores de producción seguros:** La imagen Docker final no debe contener código fuente ni toolchains de Rust; solo el binario compilado y certificados CA.
- **Trazabilidad semver:** Respetar semver: MAJOR para breaking changes, MINOR para nuevas funcionalidades retrocompatibles, PATCH para corrección de bugs.

## Verificación / Definition of Done
- `CHANGELOG.md` actualizado con fecha y notas de la versión.
- `cargo build --release` exitoso.
- `cargo test` pasando al 100%.
- Contenedor Docker compilable.

## Contrato de entrega del agente
El agente reportará el número de versión preparado, las notas de release añadidas a `CHANGELOG.md` y el resumen de validación de tests y build de release.
