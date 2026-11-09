# Third-Party Dependency Architecture Review — Matriz de aceptación y casos negativos

## Evidencia mínima por test

Cada escenario contiene: **precondición, acción, resultado esperado, comandos, evidencia real, estado**. Declarar `NOT RUN` inicialmente. El operador completa con resultados de ejecución; el agente no debe escribir PASS por intención.

| # | Escenario verificable | Evidencia esperada | Estado inicial |
|---|---|---|---|
| 01 | Necessity and no-library alternative articulated | Test, diff, contrato, log sanitizado o informe real | NOT RUN |
| 02 | Bom ownership/scope and transitive graph verified | Test, diff, contrato, log sanitizado o informe real | NOT RUN |
| 03 | Cve/license/upstream support evidence recorded | Test, diff, contrato, log sanitizado o informe real | NOT RUN |
| 04 | Domain/application remain technology agnostic | Test, diff, contrato, log sanitizado o informe real | NOT RUN |
| 05 | Integration smoke and rollback validated | Test, diff, contrato, log sanitizado o informe real | NOT RUN |
| 06 | Upgrade owner and policy documented | Test, diff, contrato, log sanitizado o informe real | NOT RUN |

## Flujos que obligan revisión de efectos colaterales

1. **Cambio de contrato**: revisar consumidores, estado HTTP/DB, backward compatibility y observabilidad.
2. **Cambio de datos**: revisar migración en DB previa y DB limpia, integridad, locks y rollback.
3. **Cambio de identidad o roles**: probar 401/403/tenant crossing con security chain habilitada.
4. **Cambio de dependencias**: revisar resolved dependency tree, pisos de seguridad, Maven verify e integración.
5. **Cambio de despliegue**: readiness/liveness, secretos, rutas, post-deploy smoke y mitigación.

## Criterios de bloqueo, sin atajos

- No se prueba una invariante afectada ni existe prueba de no regresión.
- Un test crítico salta por falta de Docker y se presenta como PASS.
- El cambio deja drift API / base de datos sin plan compatible.
- `permitAll`, desactivación de scanners, bypass CI o secretos embebidos se usan para completar tarea.
- El reporte afirma aprobación, ticket, advisory, deploy o release no observado.

## Plantilla de salida

```text
Resultado: implemented/proposed/blocked/review-only
Archivos y porqué: ...
Escenarios verificados: N PASS, N FAIL, N SKIPPED, N NOT RUN
Evidencia: comando -> salida/resumen -> referencia a reporte
Riesgos residuales: ...
Rollback/mitigación: ...
Cross-skill follow-ups (si aplican): ...
```
