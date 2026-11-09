# Release Engineering / Operational Go-No-Go — Playbook técnico de ejecución


## Go/no-go matrix (rellenar con pruebas, no afirmaciones)

| Gate | Evidencia requerida | PASS/FAIL/BLOCKED/NOT RUN | Owner |
|---|---|---|---|
| Source revision | SHA, tag, changelog, working tree | | |
| Quality | Maven verify, ArchUnit, JaCoCo, Spotless | | |
| Security | SAST/SCA/IaC, threat model, authz checks | | |
| Database | Liquibase upgrade + coexistence + backup | | |
| Artifact | container digest, registry, signing policy | | |
| Environment | Key Vault/identity/service connection | | |
| Routing | Front Door/Gateway API/ingress/tenant | | |
| Observability | probes, metrics, traces, alerts | | |
| Functional | auth HTTP smoke + critical API journeys | | |
| Rollback | app rollback tested, DB path defined | | |

## Secuencia recomendable de promoción

**Build**: fijar SHA/source, `./mvnw verify`, image digest inmutable, SBOM/alertas de seguridad bajo políticas reales. No construir imagen distinta por ambiente cuando el objetivo es trazabilidad/promoción de binario.

**DB**: preferir Liquibase expand-compatible antes de desplegar nueva app, mantener downgrade de app funcional mientras conviven versiones. Evaluar backfill y locks para tabla real.

**Cluster**: al desplegar, comprobar namespace, Helm values, secretos CSI/workload identity, probes, resources, gateway routes y restricción Front Door validada; no inferir IDs de perfil sin fuente actual.

**Smoke**: ejecutar request HTTP firmado con permisos adecuados, path v1, consulta real en DB, respuesta de error, correlation ID y señal de salud. Confirmar logs/metrics sin secrets.

**Monitoreo**: observar ventana definida con dueño, SLO/errors/latency/saturation; abortar ante criterio fijado. No inventar duración o métricas.

## Rollback y datos

- Revertir release Helm/manifiesto **solo** revierte binario; cambios SQL pueden persistir.
- Schema expand suele permitir rollback de app, pero contract/destructivo puede impedirlo.
- Definir backup/restore, feature flags, reversión parcial de tráfico o forward fix según impacto.
- `PROD` necesita dueño de cambio/aprobación corporativa real, no autoaprobación del agente.

## Notas de release

Versión, SHA, fecha real, entorno, cambios visibles, migration guide, feature flags, controles ejecutados, riesgos abiertos, owners y enlaces a evidencia real. La skill prepara evidencia; no ejecuta despliegue no autorizado por la solicitud.

## Gate final

- [ ] immutable SHA/image digest documented
- [ ] Maven/CI/SAST/SCA/IaC gates real
- [ ] schema upgrade/rollback and coexistence tested
- [ ] Secrets and per-env Helm configuration verified
- [ ] HTTP authentication smoke and probes pass
- [ ] monitor window and abort thresholds agreed

## Preflight AKS / Gateway de ejemplo

```text
Release source: <git SHA y build ID>
Pipeline: <proyecto ADO / environment corporate-sandbox|nonprod|prod>
Image: <registry/repository@sha256:digest>
Namespace: <deployment namespace real>
Helm: <chart name/version + values commit>
Front Door routing: <actual gatewayApi.public.frontDoorId source>
Auth: <identity, scope, tenant y token tests>
``` 

### Orden y gates

1. Validar artifact digest, no solo tag mutable; conservar provenance.
2. Evaluar schema/DDL y respaldos antes de rollout.
3. Verificar CSI Key Vault secret mounts con identidades autorizadas; no exportar secrets.
4. Confirmar resource requests/limits, readiness, startup y gateway HTTPRoute.
5. Comprobar un happy path, un rechazo 401 y una denegación por tenant/recurso en entorno con auth activa.
6. Verificar que p95/5xx no regresan respecto del baseline medido; si no hay baseline, marcar pendiente.
7. Ante falla, detener promoción, recuperar tráfico/código y evaluar DB por separado.

No asumir que service connection o Front Door de sandbox son apropiados para prod. La decisión de promover pertenece a owner autorizado.
