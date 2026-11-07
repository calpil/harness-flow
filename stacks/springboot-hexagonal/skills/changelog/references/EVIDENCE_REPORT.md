# Protocolo común de evidencia (cargar al cerrar la skill)

Usar este formato al finalizar, incluso si una parte no pudo validarse:

| Gate / Test | Comando exacto o evidencia | Resultado | Observación / bloqueo |
|---|---|---|---|
| Compilación | `./mvnw ...` | PASS/FAIL/NOT RUN | ... |
| Tests unitarios | nombre de prueba/comando | PASS/FAIL/NOT RUN | ... |
| ArchUnit | nombre de prueba/comando | PASS/FAIL/NOT RUN | ... |
| PostgreSQL integration | reports Surefire/Testcontainers | PASS/FAIL/SKIPPED/BLOCKED | verificar skipped |
| Seguridad | tests + scan y política aplicable | PASS/FAIL/BLOCKED | no confundir baseline demo |
| Documentación | diff, enlaces, changelog | PASS/FAIL/NOT RUN | ... |
| Rollback | procedimiento ensayado o diseño | VERIFIED/PROPOSED/BLOCKED | ... |

## Efectos colaterales obligatorios

- **API**: consumidores, versionamiento, códigos de error, contratos.
- **Datos**: cambios irreversibles, backfill, locks, coexistencia de versiones.
- **Seguridad**: identidad confiable, tenant/recurso, secretos, permisos.
- **Operación**: timeouts, recursos, tracing, probes, despliegue, rollback.
- **Pruebas/CI**: test faltante, skipped, gate alterado o dependencia Docker/red.

## Protección contra alucinaciones

Si no existe ticket, PR, aprobador, versión GA confirmada, test o métrica no fabricar. No poner valores de ejemplo como evidencia real. En documentos distinguir explícitamente `EJEMPLO`, `PENDIENTE`, `SUPUESTO` y `VERIFICADO`. Un bloqueo no es aprobación tácita.

## Diferenciar ejecución de propuesta

Un plan o README puede contener comandos de validación sin haberlos corrido. Solo `PASS` cuando la ejecución observada tuvo exit code exitoso y assertions relevantes. Verificar reportes Surefire de Testcontainers, no solo el código 0 del build. Ante red o Docker no disponible, usar `BLOCKED` y entregar comandos reproducibles sin intentar eludir controles.
