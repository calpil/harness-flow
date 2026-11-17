---
name: debug-targeted
description: Diagnostica y corrige un bug de la API .NET layered con el mínimo cambio: reproducir, escribir la prueba de regresión que falla, corregir la causa y validar.
---

# Debug Targeted — CALPIL .NET Layered

## Objetivo y activación
Activar ante un error en ejecución, una prueba que falla o un comportamiento incorrecto reportado. El objetivo es corregir la causa raíz con una prueba que impida que vuelva, sin refactors colaterales.

## Inspección obligatoria
Antes de escribir código, lee:
1. El síntoma exacto: request, respuesta, `correlationId`, mensaje y stack del log.
2. La capa donde ocurre: controller, service, repositorio o `Platform/`.
3. Las pruebas existentes del área afectada.
4. `git log -p` reciente de los archivos involucrados.

## Procedimiento ejecutable
1. **Reproducir** con el caso más pequeño: una prueba, un `curl` o `make run` con `.env` local. Sin reproducción no hay corrección.
2. **Ubicar la capa:** seguir el `correlationId` en los logs; decidir si es validación (controller), regla (service), SQL (repositorio) o infraestructura (`Platform/`).
3. **Escribir la prueba de regresión** en el nivel de esa capa y verla fallar por el motivo correcto.
4. **Formular la causa raíz** en una frase antes de tocar el código.
5. **Corregir con el cambio mínimo** en la capa responsable; no parchar el síntoma en otra capa.
6. **Validar:** la prueba nueva pasa, el proyecto de pruebas completo pasa, y `make test-integration` si se tocó SQL.
7. **Buscar el mismo defecto** en código hermano (otras features) y reportarlo, sin corregirlo si no se pidió.

## Patrón de implementación
```bash
dotnet test tests/Calpil.Template.Api.Tests --filter "FullyQualifiedName~ChangeStatus"
# Reproducir contra la API local, conservando el id de correlación para buscarlo en el log:
curl -i -X PATCH http://localhost:8080/api/v1/work-items/<id>/status \
  -H 'Content-Type: application/json' -H 'X-Correlation-ID: debug-123' \
  -d '{"targetStatus":"DONE"}'
```

## Decisiones y anti-patrones
- **NO** corregir sin haber reproducido el problema.
- **NO** atrapar y silenciar la excepción para que el síntoma desaparezca.
- **NO** cambiar o borrar una prueba existente para que pase, salvo que la prueba sea la que está mal y se explique por qué.
- **NO** aprovechar para refactorizar, renombrar o actualizar paquetes.
- **NO** agregar reintentos o `Task.Delay` para tapar una condición de carrera: usar el control de versión.

## Verificación / Definition of Done
- Existe una prueba de regresión que fallaba antes y pasa después.
- La causa raíz está descrita, no solo el síntoma.
- El diff toca solo lo necesario.
- Las suites afectadas están en verde.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Síntoma y cómo se reprodujo.
2. Causa raíz y capa responsable.
3. Cambio aplicado y prueba de regresión agregada.
4. Salida de las pruebas y defectos hermanos detectados.
