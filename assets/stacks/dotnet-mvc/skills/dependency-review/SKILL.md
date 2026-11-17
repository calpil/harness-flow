---
name: dependency-review
description: Evalúa el alta o actualización de paquetes NuGet y de librerías de cliente (Bootstrap, jQuery) en el portal .NET MVC: necesidad, estabilidad, vulnerabilidades y lock file.
---

# Dependency Review — CALPIL .NET MVC

## Objetivo y activación
Activar cuando un cambio agrega, actualiza o elimina un paquete NuGet o una librería de `wwwroot/lib`, o cuando se pide revisar dependencias.

## Inspección obligatoria
Antes de escribir código, lee:
1. `.claude/rules/dependencies.md`: política del stack.
2. `Directory.Packages.props`, `nuget.config` y `global.json`.
3. `src/Calpil.Template.Web/Calpil.Template.Web.csproj` y su `packages.lock.json`.
4. `src/Calpil.Template.Web/wwwroot/lib/`: versión actual de cada librería de cliente.

## Procedimiento ejecutable
1. **Justificar la necesidad:** confirmar que ASP.NET Core no lo resuelve ya y que no es un paquete de acceso a datos (prohibido en el portal).
2. **Evaluar el paquete o librería:** última versión estable, mantenimiento, licencia y avisos de seguridad publicados.
3. **NuGet:** declarar la versión en `Directory.Packages.props` y la referencia sin versión en el `.csproj`.
4. **Librería de cliente:** reemplazar su carpeta completa en `wwwroot/lib` por la distribución publicada de la versión nueva, sin editar archivos y sin CDN.
5. **Regenerar el lock:** `dotnet restore Calpil.Template.slnx` y revisar el diff de `packages.lock.json`.
6. **Auditar y probar:** `make audit`, `make build`, `make test`.
7. **Verificar en el navegador** las páginas con formularios (la validación del lado del cliente depende de jQuery Validation) y `make docker-build`.

## Patrón de implementación
```xml
<!-- Directory.Packages.props -->
<PackageVersion Include="Microsoft.AspNetCore.Authentication.OpenIdConnect" Version="10.0.15" />

<!-- src/Calpil.Template.Web/Calpil.Template.Web.csproj -->
<PackageReference Include="Microsoft.AspNetCore.Authentication.OpenIdConnect" />
```

## Decisiones y anti-patrones
- **NO** poner `Version` en un `.csproj`.
- **NO** agregar versiones preview, rc, alpha o beta.
- **NO** agregar paquetes de acceso a datos.
- **NO** cargar librerías desde un CDN ni editar archivos dentro de `wwwroot/lib`.
- **NO** dejar el paquete de autenticación en una versión distinta a la del runtime de ASP.NET Core en uso.
- **NO** commitear un `.csproj` cambiado sin su `packages.lock.json`.

## Verificación / Definition of Done
- `make audit` sin paquetes vulnerables.
- El diff de `packages.lock.json` fue revisado y coincide con el cambio.
- `make build`, `make test` y `make docker-build` en verde.
- Formularios verificados en el navegador si se tocó `wwwroot/lib`.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Paquete o librería, versión anterior y nueva, y motivo.
2. Dependencias transitivas relevantes agregadas.
3. Resultado de `make audit`.
4. Resultado de build, pruebas, imagen y verificación manual.
