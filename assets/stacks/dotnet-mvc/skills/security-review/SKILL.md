---
name: security-review
description: Revisa la seguridad del portal web .NET MVC: XSS, CSRF, sesión y autorización, redirecciones abiertas, CSP, secretos, fugas en errores, cookies y configuración de OpenID Connect.
---

# Security Review — CALPIL .NET MVC

## Objetivo y activación
Activar antes de un release, tras cambios en vistas, controllers, autenticación, configuración o Dockerfile, o cuando se pide una revisión de seguridad. Reporta hallazgos con evidencia; corrige solo si se pide.

## Inspección obligatoria
Antes de escribir código, lee:
1. `.claude/rules/security.md`: la regla que se audita.
2. `src/Calpil.Template.Web/Views/**`: toda salida de datos.
3. `src/Calpil.Template.Web/Controllers/**`: acciones, métodos HTTP y atributos de autorización.
4. `src/Calpil.Template.Web/Program.cs` y `src/Calpil.Template.Web/Platform/`: filtros globales, cabeceras, cookies y OIDC.
5. `Dockerfile`, `compose.yaml`, `.env.example` y `appsettings*.json`.

## Procedimiento ejecutable
1. **XSS:** buscar salida sin codificar (`grep -rnE 'Html\.Raw|HtmlString|@\(new' src --include='*.cshtml' --include='*.cs'`) y HTML armado por concatenación.
2. **CSP:** confirmar que no se relajó la política y que ninguna vista agrega código en línea u orígenes externos.
3. **CSRF:** listar las acciones que cambian estado; todas deben ser POST y ninguna llevar `[IgnoreAntiforgeryToken]` (salvo la página de error).
4. **Sesión y autorización:** listar cada `[AllowAnonymous]` y justificarlo; verificar que sigue activo el `AuthorizeFilter` global y, si hay roles o pertenencia, que cada acción los verifique.
5. **Redirecciones:** todo parámetro que termina en una redirección debe pasar por `Url.IsLocalUrl`.
6. **Secretos y modo dev:** buscar credenciales en el repositorio sin imprimir su valor; confirmar que `AUTH_MODE=dev` no aparece en manifiestos de ambientes desplegados.
7. **Errores y logs:** confirmar que la página de error y los logs no exponen detalles internos, tokens ni datos personales.
8. **Cookies, transporte e imagen:** atributos de la cookie de sesión, HSTS, cabeceras reenviadas, claves de Data Protection, `make audit`, usuario no root y digest fijo.

## Patrón de implementación
```text
[Alta] src/Calpil.Template.Web/Views/Orders/Details.cshtml:18
       @Html.Raw(Model.Notes) emite sin codificar un texto que viene de la API.
       Impacto: XSS almacenado. Corrección: @Model.Notes.

[Media] src/Calpil.Template.Web/Controllers/OrdersController.cs:52
       [HttpGet("{id}/cancel")] cambia estado con GET: sin antiforgery y ejecutable desde un enlace.
       Corrección: POST de formulario.
```

## Decisiones y anti-patrones
- **NO** mostrar en el reporte ni en la terminal el valor de un secreto encontrado.
- **NO** resolver un bloqueo de la CSP agregando `'unsafe-inline'`.
- **NO** considerar seguro un dato porque "viene de nuestra API": se codifica igual.
- **NO** aceptar como control de acceso que un enlace esté oculto.
- **NO** recomendar `X-XSS-Protection`: está obsoleta.

## Verificación / Definition of Done
- Todas las vistas y acciones del alcance fueron revisadas.
- Cada hallazgo tiene severidad (Alta, Media, Baja), `archivo:línea`, impacto y corrección.
- Se ejecutaron `make audit` y las pruebas de seguridad existentes, con su resultado.
- Se declara lo que quedó fuera de alcance o no se pudo verificar (por ejemplo, la configuración real del proveedor de identidad).

## Contrato de entrega del agente
El mensaje final debe informar:
1. Resumen y veredicto (apto, apto con observaciones, no apto).
2. Hallazgos por severidad.
3. Controles verificados que sí se cumplen.
4. Riesgos abiertos, incluida la confianza portal → API si aún no está definida.
