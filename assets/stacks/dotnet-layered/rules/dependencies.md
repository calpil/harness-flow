---
description: Gobierno de paquetes NuGet con versiones centralizadas, lock file y fuente única
globs: ["**/*.csproj", "Directory.Packages.props", "Directory.Build.props", "nuget.config", "global.json", "**/packages.lock.json"]
trigger: always_on
---

# Reglas de dependencias NuGet

- **Versiones centralizadas:** toda versión vive en `Directory.Packages.props`. Los `.csproj` declaran `<PackageReference Include="..." />` sin `Version`.
- **Lock file:** `packages.lock.json` se versiona. Tras cambiar un paquete, ejecutar `dotnet restore` y commitear el lock; CI y Docker restauran con `--locked-mode`.
- **Fuente única:** `nuget.config` declara una sola fuente con `packageSourceMapping`. No agregar fuentes sin mapear sus patrones.
- **Solo versiones estables:** prohibido alpha, beta, preview o rc en código que va a producción.
- **Acceso a datos:** Dapper + `Microsoft.Data.SqlClient` (línea 6.x). Prohibido incorporar un ORM (EF Core, NHibernate) u otra librería de acceso a datos.
- **Antes de agregar un paquete:** confirmar que el framework no lo resuelve ya (ASP.NET Core incluye JSON, validación, health checks, Problem Details, logging, `TimeProvider`).
- **Vulnerabilidades:** `make audit` debe pasar; cubre dependencias transitivas. Un paquete con vulnerabilidad alta o crítica no entra.
- **Paquetes de prueba** solo en proyectos bajo `tests/`.
