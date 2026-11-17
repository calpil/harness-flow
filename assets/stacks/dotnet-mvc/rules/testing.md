---
description: Estándares de pruebas deterministas con xUnit para páginas, sesión, formularios y cliente HTTP del portal .NET MVC
globs: ["tests/**", "**/*Tests.cs"]
trigger: always_on
---

# Reglas de pruebas

- **Deterministas y sin red.** Prohibido `Thread.Sleep`, `Task.Delay` como espera y llamadas a una API o proveedor de identidad reales.
- **Páginas:** con `WebFactory` (`WebApplicationFactory<Program>`), que usa `FakeWorkItemsApi` y una autenticación de prueba (hay sesión solo con la cabecera `X-Test-User`). Se afirma sobre el HTML que recibe el navegador.
- **Formularios:** siempre por `WebFactory.PostFormAsync`, que obtiene el token antiforgery de la página real. Toda acción POST nueva tiene además su prueba de rechazo sin token.
- **Sesión:** cada página nueva con datos se agrega a `Pages_with_data_require_a_session`.
- **Cliente HTTP:** con un `HttpMessageHandler` de prueba. Cubrir éxito, cada error esperado (400, 404, 409), error inesperado, falla de red, timeout y cuerpo ilegible.
- **Seguridad observable:** texto con HTML proveniente de la API debe salir codificado; las páginas nuevas se agregan a la prueba de "sin código en línea".
- **El fake respeta el contrato de `IWorkItemsApi`.** Si cambia la interfaz, cambian el cliente real, el fake y sus pruebas.
- **Independencia:** cada clase de prueba crea su propia `WebFactory`; ninguna prueba depende de datos de otra.
- **Una prueba nueva debe poder fallar.** Comprobar el rojo rompiendo el comportamiento que protege.
- **Nunca** borrar, saltar (`Skip`) o relajar una prueba para que pase un cambio.
- `make validate` termina con 0 fallas y 0 warnings.
