---
name: security-review
description: Revisa la seguridad de la API .NET layered: inyección SQL, secretos, validación de entrada, fugas en errores, cabeceras, TLS a SQL Server, privilegios e imagen.
---

# Security Review — CALPIL .NET Layered

## Objetivo y activación
Activar antes de un release, tras cambios en controllers, repositorios, configuración, Dockerfile o dependencias, o cuando se pide una revisión de seguridad. Reporta hallazgos con evidencia; corrige solo si se pide.

## Inspección obligatoria
Antes de escribir código, lee:
1. `.claude/rules/security.md`: la regla que se audita.
2. `src/Calpil.Template.Api/**/*Repository.cs` y `db/migrations/`: todo el SQL.
3. `src/Calpil.Template.Api/Platform/`: manejo de errores, correlación, cabeceras y `DatabaseOptions`.
4. `Dockerfile`, `compose.yaml`, `.env.example`, `appsettings*.json`, `nuget.config`.
5. El diff del cambio, si la revisión es sobre un cambio.

## Procedimiento ejecutable
1. **Inyección SQL:** revisar cada sentencia; buscar interpolación y concatenación (`grep -rnE '\$\"|\+ *\"' --include='*Repository.cs' src`) y SQL dinámico en procedimientos (`EXEC(`, `sp_executesql`).
2. **Secretos:** buscar credenciales en código, configuración, pruebas e historial del cambio (`grep -rniE 'password|pwd=|secret|token' src tests --include='*.cs' --include='*.json'`). No imprimir valores encontrados.
3. **Entrada:** confirmar que cada DTO limita tipo y largo, que los enums rechazan números y que la paginación tiene tope.
4. **Errores:** confirmar que ninguna ruta devuelve mensajes de excepción no controlada; revisar `AppExceptionHandler` y la prueba `Unexpected_failure_returns_500_problem_without_internal_details`.
5. **Transporte y base:** `DB_SSL` obligatorio en `Production`, sin `TrustServerCertificate=true` fuera de local, login de la aplicación sin `sa`/`db_owner`.
6. **Cabeceras y límites:** `SecurityHeadersMiddleware` aplicado a toda respuesta, límite de cuerpo vigente, sin descompresión de requests.
7. **Autorización:** si el proyecto ya agregó autenticación, que cada endpoint la exija y que el acceso a un recurso verifique pertenencia. Si no hay, declararlo como riesgo abierto.
8. **Cadena de suministro e imagen:** `make audit`, digest fijo, usuario no root, sin herramientas extra en la imagen.

## Patrón de implementación
```text
[Alta] src/Calpil.Template.Api/Orders/OrderRepository.cs:58
       SQL construido con interpolación del parámetro `status` del request.
       Impacto: inyección SQL. Corrección: parámetro Dapper @Status (DbString ANSI).

[Media] compose.yaml:7
       La contraseña local se reutiliza en el manifiesto de staging.
       Corrección: referenciar el secreto del almacén; rotar la contraseña.
```

## Decisiones y anti-patrones
- **NO** mostrar en el reporte ni en la terminal el valor de un secreto encontrado; indicar solo archivo y línea.
- **NO** reportar riesgos genéricos sin evidencia en este repositorio.
- **NO** dar por segura una consulta porque "el valor viene de un enum": debe ser parámetro igual.
- **NO** recomendar `X-XSS-Protection`: está obsoleta.
- **NO** relajar una validación o una cabecera para resolver un problema funcional.

## Verificación / Definition of Done
- Todas las sentencias SQL del alcance fueron revisadas.
- Cada hallazgo tiene severidad (Alta, Media, Baja), `archivo:línea`, impacto y corrección.
- Se ejecutaron `make audit` y las pruebas de seguridad existentes, con su resultado.
- Se declara lo que quedó fuera de alcance o no se pudo verificar.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Resumen y veredicto (apto, apto con observaciones, no apto).
2. Hallazgos por severidad.
3. Controles verificados que sí se cumplen.
4. Riesgos abiertos, incluida la ausencia de autenticación si aplica.
