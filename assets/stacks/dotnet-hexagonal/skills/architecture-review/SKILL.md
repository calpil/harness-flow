---
name: architecture-review
description: Audita la solución .NET / C# para verificar el estricto cumplimiento de los límites de Clean Architecture y la pureza del dominio.
---

# Architecture Review — CALPIL .NET Engineering Skill

## Objetivo y activación
Activar antes de enviar un Pull Request o tras refactorizar código para auditar que la solución mantenga el desacoplamiento de Clean Architecture, no existan referencias circulares ni dependencias ilegales y el dominio permanezca 100% puro.

## Inspección obligatoria
Antes de emitir el informe, inspecciona:
1. `src/Calpil.Template.Domain/Calpil.Template.Domain.csproj`: Verificar que no tenga `PackageReference` de transporte, ORM o librerías de infraestructura.
2. `src/Calpil.Template.Application/Calpil.Template.Application.csproj`: Verificar que solo tenga `ProjectReference` hacia `Calpil.Template.Domain`.
3. `src/Calpil.Template.WebApi/Controllers/`: Comprobar que los controladores solo consuman interfaces de la capa de aplicación.
4. `src/Calpil.Template.WebApi/Program.cs`: Verificar que sea el único punto donde se resuelve la composición de infraestructura.

## Procedimiento ejecutable
1. **Auditar Referencias de Proyectos:** Revisar los archivos `.csproj` asegurando que la regla de dependencias unidireccional se cumpla estrictamente (`WebApi -> Infrastructure & Application -> Domain`).
2. **Auditar Usings del Dominio:** Comprobar que ningún archivo en `Calpil.Template.Domain` importe `Microsoft.AspNetCore`, `Dapper`, `Npgsql` o `System.Data`.
3. **Revisar Encapsulamiento del Modelo:** Asegurar que los setters de propiedades de las entidades de dominio sean `private` o `init` y que las mutaciones ocurran mediante métodos de negocio.
4. **Verificar Aislamiento de Controladores:** Comprobar que ningún controlador instancie repositorios directamente ni ejecute queries SQL.
5. **Revisar Gestión de Middlewares:** Confirmar que la correlación, logging y manejo de excepciones RFC 7807 residan en la capa `WebApi.Middlewares`.
6. **Verificar Paridad InMemory:** Asegurar que cada repositorio en `Infrastructure.Persistence.Dapper` tenga su contraparte en `Infrastructure.Persistence.InMemory`.
7. **Emitir Diagnóstico y Veredicto:** Documentar hallazgos categorizados por gravedad (Crítico, Alto, Medio, Informativo) y proponer correcciones.

## Patrón de implementación
Diagrama de dependencias de la solución:
```text
Calpil.Template.WebApi  ──┐
           │              │ (Solo DI en Program.cs)
           ▼              ▼
Calpil.Template.Application ◄── Calpil.Template.Infrastructure
           │
           ▼
Calpil.Template.Domain (C# puro)
```

## Decisiones y anti-patrones
- **NO** tolerar que `Domain` o `Application` hagan referencia directa a `Infrastructure`.
- **NO** omitir interfaces en los puertos de entrada o salida.
- **NO** admitir bypasses donde un endpoint HTTP acceda a la base de datos sin pasar por la capa de aplicación.

## Verificación / Definition of Done
- Los 4 proyectos de `src/` compilan limpiamente sin advertencias arquitectónicas.
- Pruebas unitarias de dominio y de aplicación pasando al 100%.
- Veredicto final emitido.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Proyectos y archivos auditados.
2. Estado de cumplimiento de las reglas de arquitectura.
3. Observaciones y hallazgos identificados.
4. Veredicto final: Conforme / No conforme.
