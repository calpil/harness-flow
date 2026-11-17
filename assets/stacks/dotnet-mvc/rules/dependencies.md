---
description: Gobierno de paquetes NuGet y librerías de cliente del portal .NET MVC
globs: ["**/*.csproj", "Directory.Packages.props", "Directory.Build.props", "nuget.config", "global.json", "**/packages.lock.json", "src/**/wwwroot/lib/**"]
trigger: always_on
---

# Reglas de dependencias

- **Versiones centralizadas:** toda versión vive en `Directory.Packages.props`. Los `.csproj` declaran `<PackageReference Include="..." />` sin `Version`.
- **Lock file:** `packages.lock.json` se versiona. Tras cambiar un paquete, ejecutar `dotnet restore` y commitear el lock; CI y Docker restauran con `--locked-mode`.
- **Fuente única:** `nuget.config` declara una sola fuente con `packageSourceMapping`.
- **Solo versiones estables:** prohibido alpha, beta, preview o rc.
- **Sin acceso a datos:** prohibido agregar `Microsoft.Data.SqlClient`, Dapper, Entity Framework o cualquier proveedor de base de datos. El portal solo habla con la API.
- **Antes de agregar un paquete:** confirmar que ASP.NET Core no lo resuelve ya (MVC, validación, autenticación por cookie, antiforgery, `IHttpClientFactory`, health checks, logging).
- **Librerías de cliente (`wwwroot/lib`):** Bootstrap, jQuery, jQuery Validation y Unobtrusive vienen de la plantilla oficial de ASP.NET Core. Se actualizan reemplazando la carpeta completa por la versión publicada, nunca editando sus archivos, y nunca se cargan desde un CDN (la CSP solo permite origen propio).
- **Vulnerabilidades:** `make audit` debe pasar; cubre dependencias transitivas.
- **Paquetes de prueba** solo en proyectos bajo `tests/`.
