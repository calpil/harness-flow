---
name: prepare-release
description: Ejecuta la lista de verificación final previa a un release en Go incluyendo compilación, linter, tests con race detector, build de Docker y changelog.
---

# Prepare Release — CALPIL Golang Engineering Skill

## Objetivo y activación
Activar cuando el equipo de desarrollo o el usuario indique que una versión o hito del backend en Go está listo para empaquetado, etiquetado o despliegue a ambientes de pruebas o producción.

## Inspección obligatoria
Antes de iniciar la preparación del release, inspecciona:
1. `git status`: Confirmar que el working tree esté limpio y todos los cambios guardados.
2. `CHANGELOG.md`: Registro de cambios acumulados en la versión actual.
3. `api/openapi.yaml`: Verificar que la versión en el metadata coincida con la versión del release.
4. `go.mod`: Ausencia de directivas `replace` locales que apunten a rutas del sistema de archivos.

## Procedimiento ejecutable
1. **Ejecutar Linters y Verificación Estática:** Ejecutar `go vet ./...` y asegurar que no existan advertencias ni código muerto.
2. **Ejecutar Suite Completa de Tests:** Ejecutar `go test -v -race ./...` asegurando 100% de éxito en tests unitarios y de integración.
3. **Compilar Binario de Producción:** Ejecutar `CGO_ENABLED=0 go build -ldflags="-s -w" -o bin/server ./cmd/server` y verificar que el binario se genere correctamente.
4. **Validar Contenedor Docker:** Ejecutar `docker build -t calpil-golang-hexagonal-template:release .` comprobando que el multi-stage build finalice sin errores y el binario corra como `appuser`.
5. **Validar Habilidades del Agente:** Ejecutar `node scripts/validate-agent-skills.mjs` para verificar la integridad de los runbooks y enlaces de skills.
6. **Actualizar Documentación de Release:** Incrementar versión en `api/openapi.yaml`, agregar notas en `CHANGELOG.md` con las nuevas features, correcciones y breaking changes.

## Patrón de implementación
```bash
# Secuencia completa de pre-release
go vet ./...
go test -v -race ./...
CGO_ENABLED=0 go build -ldflags="-s -w" -o bin/server ./cmd/server
node scripts/validate-agent-skills.mjs
```

## Decisiones y anti-patrones
- **NO** generar un release si algún test presenta intermitencia (*flaky test*).
- **NO** dejar directivas `replace` en `go.mod` apuntando a directorios locales.
- **NO** omitir la actualización de `CHANGELOG.md`.

## Verificación / Definition of Done
- `go vet ./...` limpio.
- `go test -race ./...` pasando al 100%.
- Binario compila sin CGO (`CGO_ENABLED=0`).
- Imagen Docker construye exitosamente.
- `scripts/validate-agent-skills.mjs` pasa sin errores.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Versión del release preparada.
2. Resumen de verificaciones ejecutadas (tests, linter, docker build, skills check).
3. Entradas agregadas a `CHANGELOG.md`.
4. Artefactos listos para publicación.
