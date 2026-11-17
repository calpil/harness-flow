---
name: debug-targeted
description: Diagnostica y corrige un bug del portal .NET MVC con el mínimo cambio: reproducir, ubicar si es vista, controller, cliente o API, prueba de regresión que falla y corrección.
---

# Debug Targeted — CALPIL .NET MVC

## Objetivo y activación
Activar ante un error en una página, un formulario que no funciona, una prueba que falla o un comportamiento incorrecto reportado. Corrige la causa raíz con una prueba que impida que vuelva.

## Inspección obligatoria
Antes de escribir código, lee:
1. El síntoma exacto: URL, acción, lo que se ve, el código de seguimiento de la página de error.
2. Los logs del portal y de la API para ese `X-Correlation-ID`.
3. La consola del navegador (errores de CSP o de validación) si el problema es de interfaz.
4. Las pruebas existentes del área y el `git log -p` reciente de los archivos involucrados.

## Procedimiento ejecutable
1. **Reproducir** con el caso más pequeño: una prueba de página o el flujo en el navegador con `make run`.
2. **Ubicar el origen:** vista (se ve mal), controller (flujo o redirección), cliente (traducción de la respuesta), configuración o la API. Usar el `X-Correlation-ID` para cruzar logs.
3. **Si el defecto es de la API,** detenerse y reportarlo con el request y la respuesta: no se compensa en el portal.
4. **Escribir la prueba de regresión** en el nivel de la capa responsable y verla fallar por el motivo correcto.
5. **Formular la causa raíz** en una frase y corregir con el cambio mínimo en esa capa.
6. **Validar:** la prueba nueva y `dotnet test tests/Calpil.Template.Web.Tests` completo; verificar en el navegador si el defecto era visual o de CSP.
7. **Buscar el mismo defecto** en páginas hermanas y reportarlo.

## Patrón de implementación
```bash
dotnet test tests/Calpil.Template.Web.Tests --filter "FullyQualifiedName~ChangeStatus"
# Reproducir en local con un id de correlación propio para buscarlo en los logs de portal y API:
curl -i http://localhost:8090/work-items -H 'X-Correlation-ID: debug-123'
```

## Decisiones y anti-patrones
- **NO** corregir sin haber reproducido el problema.
- **NO** capturar `ApiUnavailableException` en un controller para que la página "no falle".
- **NO** compensar en el portal un error de la API.
- **NO** relajar la CSP, el antiforgery o la autorización para que algo funcione.
- **NO** cambiar o borrar una prueba existente para que pase, salvo que la prueba esté mal y se explique por qué.
- **NO** aprovechar para refactorizar o actualizar paquetes.

## Verificación / Definition of Done
- Existe una prueba de regresión que fallaba antes y pasa después.
- La causa raíz está descrita, con la capa responsable.
- El diff toca solo lo necesario.
- Las pruebas del portal están en verde.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Síntoma y cómo se reprodujo.
2. Causa raíz y capa responsable (o que el defecto es de la API).
3. Cambio aplicado y prueba de regresión agregada.
4. Salida de las pruebas y defectos hermanos detectados.
