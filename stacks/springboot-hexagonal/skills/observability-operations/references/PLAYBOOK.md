# Observability / SLO / AKS Operations — Playbook técnico de ejecución


## Modelo operativo para API sobre AKS

- **SLI disponibilidad**: respuestas satisfactorias / total de requests elegibles. Excluir probes y ruido según contrato.
- **SLI latencia**: percentil p95/p99 por operación agregada, sin route IDs de alta cardinalidad.
- **SLI errores**: 5xx vs 4xx esperados; separar downstream failure y negocio inválido.
- **Saturación**: requests in-flight, pool JDBC, threads, heap/GC, throttle CPU, queue depth.

Un SLO numérico (ej. 99.9%) requiere acuerdo, baseline y presupuesto de error; no inventarlo por defecto.

## Correlation, logs y trazas

El template tiene `CorrelationIdFilter` y puente `micrometer-tracing-bridge-otel`. Verificar que request ID se propague/regenere con reglas de longitud/carácter y no confiar en cabeceras externas sin validación. Unir trace/span IDs del collector si realmente se exportan; tener bridge **no equivale** a exportar y visualizar traces.

```text
Log event:
  timestamp, severity, service, env, operation, routeTemplate,
  correlationId, traceId, spanId, errorCode, durationMs
No loggear:
  Authorization, cookies, PAT, api-key, client-secret, DB password,
  payload con PII, raw token claims ni raw SQL con valores sensibles.
```

## Probes correctas

- `liveness`: proceso puede recuperarse sin reinicio; NO usar DB como condición porque provoca restart storms.
- `readiness`: instancia capaz de atender requests y dependencias indispensables conforme diseño.
- `startup`: cubre cold start/migraciones de arranque si aplican; alinear `failureThreshold` y `periodSeconds` con mediciones reales.
- Graceful shutdown: drenaje, terminación y requests pendientes según Helm/pod lifecycle.

## Alertas útiles

| Síntoma | Fuente | Acción | Runbook |
|---|---|---|---|
| ratio 5xx inusual | métricas API | correlacionar deploy/version | revisar logs por trace |
| p99 creciente | latency + CPU/DB | comparar pool y slow queries | investigar saturación |
| pods no ready | kube events + actuator | ver errores config/DB/CSI | rollback si umbral |
| error dependencia externa | spans outbound | timeouts/circuit breaker | degradación/cola |
| backlog/evento duplicado | outbox/queue | detectar retries y dead letters | re-proceso idempotente |

No configurar umbrales exactos sin SLO, histórico y costos de alert fatigue.

## Runbook mínimo

1. Scope y ventana del incidente, deploy SHA/imagen digest, namespace.
2. Cambios recientes, pods readiness, restart count, memory/CPU, saturación.
3. Request ejemplo con correlation ID redactado, métricas y trazas alrededor.
4. DB pool/locks y dependencias externas con timeout; distinguir efecto y causa.
5. Mitigación de bajo riesgo, bandera/canary/rollback de app y política de datos.
6. Postmortem con test de regresión, SLO afectado, responsable y seguimiento.

## Gate final

- [ ] correlation and trace propagation proven across hop
- [ ] log fields redacted and cardinality bounded
- [ ] liveness/readiness separation verified
- [ ] critical dependency saturation and timeout visible
- [ ] alert on symptoms/SLO rather than random thresholds
- [ ] runbook recovery and owner clearly identified

## Etiquetado y correlación para remolcadores/tenants

Evitar usar nombre o matrícula de remolcador como etiqueta de métricas: la cardinalidad crecerá por activo. En logs de auditoría puede existir un ID pseudonimizado aprobado, con retención y acceso adecuados.

```text
Buenas etiquetas métricas: application, environment, routeTemplate, statusClass
Malas etiquetas métricas: requestId, rawUserId, tugId, rawTenantString
```

### Pruebas operativas con falla inyectada

1. Caída temporal PostgreSQL: readiness se comporta según diseño; liveness no causa tormenta de reinicios.
2. HTTP upstream timeout: se registra `errorCode` y span sin exponer token/URL con query sensible.
3. Request repetido/retry: correlación preservada y side effects idempotentes donde aplica.
4. Latencia creciente: dashboard separa handler, DB y outbound; alert owner puede acotar causa.
5. Tráfico sin `X-Correlation-ID`: el servicio genera uno válido; uno malicioso/largo se rechaza o normaliza.
6. Despliegue/rollback: etiquetas `version`/digest permiten correlacionar problemas de rollout.

No declarar exportación OpenTelemetry activa solo por incluir un bridge Maven; demostrar exporter y backend de observabilidad.
