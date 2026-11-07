---
description: Evaluación y gobierno de paquetes NuGet en .NET
globs: ["**/*.csproj", "Calpil.Template.sln*"]
---

# Reglas de Dependencias NuGet en .NET / C#

- Solo paquetes NuGet estables, ampliamente auditados y compatibles con el TargetFramework del proyecto (`net10.0` / LTS).
- Prohibido agregar paquetes de terceros en `Calpil.Template.Domain`. El dominio debe permanecer libre de dependencias externas.
- En persistencia, mantener el enfoque Dapper / ADO.NET explícito sin incorporar ORMs mágicos que filtren abstracciones hacia el dominio.
- Verificar vulnerabilidades conocidas antes de introducir paquetes de terceros mediante `dotnet list package --vulnerable`.
- Prohibido agregar dependencias en versiones beta, alpha o preview en proyectos destinados a producción.
