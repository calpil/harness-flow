---
name: prepare-release
description: Ejecuta la lista de verificación final previa a un release en .NET / C# incluyendo pruebas, compilación de release, build de Docker y changelog.
---

# Prepare Release — CALPIL .NET Engineering Skill

## Objetivo y activación
Activar cuando el equipo o el usuario determine que una versión o hito del backend ASP.NET Core está lista para etiquetado, empaquetado o despliegue a ambientes de pruebas o producción.

## Inspección obligatoria
Antes de iniciar la preparación del release, inspecciona:
1. `git status`: Confirmar que no existan cambios pendientes ni archivos sin commitear.
2. `CHANGELOG.md`: Registro de cambios acumulados en la versión actual.
3. `api/openapi.yaml`: Versión del contrato OpenAPI sincronizada.
4. Archivos `.csproj`: Comprobar que no existan rutas locales absolutas.

## Procedimiento ejecutable
1. **Ejecutar Suite Completa de Tests:** Ejecutar `dotnet test --configuration Release` asegurando 100% de éxito en todos los proyectos de prueba.
2. **Compilar en Modo Release:** Ejecutar `dotnet publish src/Calpil.Template.WebApi/Calpil.Template.WebApi.csproj -c Release -o bin/publish` verificando 0 errores y 0 warnings.
3. **Validar Imagen Docker:** Ejecutar `docker build -t calpil-dotnet-hexagonal-template:release .` comprobando que el multi-stage build finalice correctamente y el contenedor corra bajo `appuser`.
4. **Validar Habilidades del Agente:** Ejecutar `node scripts/validate-agent-skills.mjs` para verificar la integridad de todos los runbooks y enlaces de skills.
5. **Actualizar Documentación de Release:** Incrementar versión en `api/openapi.yaml` y documentar cambios en `CHANGELOG.md` siguiendo Keep a Changelog.

## Patrón de implementación
```bash
# Secuencia completa de pre-release
dotnet test --configuration Release
dotnet publish src/Calpil.Template.WebApi/Calpil.Template.WebApi.csproj -c Release -o bin/publish
node scripts/validate-agent-skills.mjs
```

## Decisiones y anti-patrones
- **NO** generar un release si existe alguna prueba fallida o intermitente.
- **NO** incluir credenciales o tokens en los artefactos compilados.
- **NO** omitir la actualización de `CHANGELOG.md`.

## Verificación / Definition of Done
- `dotnet test --configuration Release` pasando al 100%.
- Publicación de release generada en `bin/publish`.
- Imagen Docker construida exitosamente.
- `scripts/validate-agent-skills.mjs` sin errores.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Versión del release preparada.
2. Resumen de verificaciones ejecutadas (tests, publish, docker build, skills check).
3. Entradas agregadas a `CHANGELOG.md`.
4. Artefactos listos para publicación.
