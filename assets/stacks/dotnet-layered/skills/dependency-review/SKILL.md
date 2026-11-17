---
name: dependency-review
description: Evalúa el alta o actualización de un paquete NuGet en la API .NET layered: necesidad, estabilidad, vulnerabilidades, versiones centralizadas y lock file.
---

# Dependency Review — CALPIL .NET Layered

## Objetivo y activación
Activar cuando un cambio agrega, actualiza o elimina un paquete NuGet, o cuando se pide revisar dependencias. Evita paquetes innecesarios o vulnerables y mantiene coherentes `Directory.Packages.props` y los `packages.lock.json`.

## Inspección obligatoria
Antes de escribir código, lee:
1. `.claude/rules/dependencies.md`: política del stack.
2. `Directory.Packages.props`: versiones centralizadas.
3. `nuget.config` y `global.json`: fuente y SDK.
4. Los `.csproj` afectados y sus `packages.lock.json`.

## Procedimiento ejecutable
1. **Justificar la necesidad:** confirmar que .NET o ASP.NET Core no lo resuelven ya, y que no existe un paquete equivalente en el repositorio.
2. **Evaluar el paquete:** última versión estable, mantenimiento reciente, licencia compatible, dependencias transitivas que arrastra. Contrastar en nuget.org y en la documentación oficial.
3. **Declarar la versión** en `Directory.Packages.props` (`<PackageVersion>`) y la referencia sin versión en el `.csproj`.
4. **Regenerar el lock:** `dotnet restore Calpil.Template.slnx` y revisar el diff de `packages.lock.json`; debe contener solo lo esperado.
5. **Auditar:** `make audit` (incluye transitivas).
6. **Compilar y probar:** `make build && make test`; `make test-integration` si el paquete toca datos.
7. **Verificar la imagen:** `make docker-build` (el restore usa `--locked-mode`).

## Patrón de implementación
```xml
<!-- Directory.Packages.props -->
<PackageVersion Include="Microsoft.Data.SqlClient" Version="6.1.8" />

<!-- src/Calpil.Template.Api/Calpil.Template.Api.csproj -->
<PackageReference Include="Microsoft.Data.SqlClient" />
```

## Decisiones y anti-patrones
- **NO** poner `Version` en un `.csproj`.
- **NO** agregar versiones preview, rc, alpha o beta.
- **NO** agregar un ORM u otra librería de acceso a datos distinta de Dapper + SqlClient.
- **NO** agregar fuentes NuGet sin `packageSourceMapping`.
- **NO** saltar de versión mayor (por ejemplo SqlClient 6.x a 7.x) sin leer las notas de cambios incompatibles y sin acuerdo del equipo.
- **NO** commitear un `.csproj` cambiado sin su `packages.lock.json`.

## Verificación / Definition of Done
- `make audit` sin paquetes vulnerables.
- El diff de `packages.lock.json` fue revisado y coincide con el cambio.
- `make build`, `make test` y `make docker-build` en verde.
- La justificación del paquete queda en la descripción del cambio.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Paquete, versión anterior y nueva, y motivo.
2. Dependencias transitivas relevantes agregadas.
3. Resultado de `make audit`.
4. Resultado de build, pruebas e imagen.
