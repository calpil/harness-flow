---
name: dependency-review
description: Evalúa, audita y actualiza paquetes NuGet en proyectos .NET garantizando compatibilidad, licencias corporativas permitidas y ausencia de CVEs.
---

# Dependency Review — CALPIL .NET Engineering Skill

## Objetivo y activación
Activar cuando se proponga agregar, actualizar o desinstalar un paquete NuGet en cualquiera de los proyectos `.csproj` de la solución. Garantiza que cada dependencia esté técnicamente justificada, tenga una licencia corporativa válida y esté libre de vulnerabilidades reportadas.

## Inspección obligatoria
Antes de modificar paquetes, inspecciona:
1. Todos los archivos `.csproj` en `src/` y `tests/`.
2. El paquete candidato en `nuget.org` para evaluar descargas, actividad y tipo de licencia.
3. El resultado de `dotnet list package --vulnerable`.

## Procedimiento ejecutable
1. **Evaluar Necesidad Técnica:** Determinar si la capacidad requerida puede resolverse limpiamente con la biblioteca base de .NET (BCL) antes de incorporar una librería externa.
2. **Revisar Licencia:** Asegurar que el paquete tenga licencia permisiva (MIT, Apache 2.0, BSD). Prohibir licencias restrictivas tipo GPL o comerciales no aprobadas.
3. **Instalar el Paquete:** Usar `dotnet add <proyecto>.csproj package <PackageName> --version <Version>` fijando una versión semántica mayormente probada.
4. **Verificar Vulnerabilidades:** Ejecutar `dotnet list package --vulnerable` para comprobar que no existan avisos de seguridad (CVEs).
5. **Verificar Compilación de la Solución:** Ejecutar `dotnet build` para comprobar que no se hayan introducido conflictos de ensamblados o advertencias de compatibilidad.
6. **Ejecutar Suite de Pruebas:** Correr `dotnet test` para asegurar que las pruebas existentes continúen pasando sin regresiones.

## Patrón de implementación
```bash
# Agregar un paquete y auditar vulnerabilidades
dotnet add src/Calpil.Template.Infrastructure/Calpil.Template.Infrastructure.csproj package Dapper --version 2.1.89
dotnet list package --vulnerable
dotnet test
```

## Decisiones y anti-patrones
- **NO** instalar paquetes NuGet en `Calpil.Template.Domain`.
- **NO** utilizar versiones preview, rc o no estables en entornos productivos.
- **NO** ignorar avisos de paquetes deprecados o no mantenidos.

## Verificación / Definition of Done
- `dotnet list package --vulnerable` no reporta ninguna vulnerabilidad.
- Solución compila con 0 errores y 0 warnings.
- `dotnet test` pasa al 100%.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Paquete NuGet añadido o actualizado y proyecto afectado.
2. Justificación técnica de la inclusión.
3. Tipo de licencia del paquete.
4. Estado del análisis de vulnerabilidades y pruebas.
