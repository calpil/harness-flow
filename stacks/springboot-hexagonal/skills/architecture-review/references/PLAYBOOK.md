# Architecture Fitness / Review and ADR — Playbook técnico de ejecución


## Checklist de límites a revisar

```text
domain imports framework?                         BLOCKER
application imports adapter or Spring web/JPA?     HIGH/BLOCKER
web controller contains business transition?      HIGH
JPA entity or HTTP DTO crosses a port?            HIGH
adapter calls application through proper port?    required
transaction boundaries and domain events sound?   inspect
security boundary and tenant resolution trusted?  inspect
new dependency has explicit owner/upgrade?        inspect
```

## Reporte reproducible de hallazgos

| ID | Severidad | Ubicación | Evidencia | Impacto | Mitigación | Test |
|---|---|---|---|---|---|---|
| ARC-001 | HIGH | `.../application/...` | import de JPA | acoplamiento de core | puerto independiente | ArchUnit |
| API-002 | HIGH | endpoint v1 | shape de respuesta cambia | rompe BFF | estrategia de versionado | contract test |

El ejemplo es formato, no hallazgo del repo. Referenciar rutas/líneas reales cuando se emita un finding y distinguir hecho de sospecha.

## Cross-cutting end-to-end

**Flujo**: identificar request handler, use case, invariantes y persistencia. Revisar que la operación sea atómica y tenga control de race; si hay publicación de eventos, en qué momento ocurre respecto a commit y si se toleran duplicados.

**Consumo**: identificar BFFs y clientes que esperan contrato/API y fechas de deprecación; el código de tercer proveedor debe mantenerse detrás de un ACL outbound.

**Datos**: evaluar `ddl-auto`, changelog, carga real de migración, compatibilidad de versiones coexistentes, rollback e índices.

**Seguridad**: validar controles en API y BFF; no delegar autorización por recurso al gateway; verificar scopes vs roles y tenant.

**Operación**: verificar timeouts, readiness, forward/backward compatibility, observabilidad, feature flags, secretos y gates de entrega.

## Severidad y decisiones

- **BLOCKER**: riesgo de acceso no autorizado, pérdida de datos, compilación rota o invariantes comprometidas.
- **HIGH**: bug funcional relevante y probable, API breaking sin transición, inconsistencia no controlada.
- **MEDIUM**: deuda con impacto observable o evolución difícil, no solo preferencia.
- **LOW**: mejoras de mantenibilidad opcionales.

Para decisiones estructurales crear/actualizar ADR: contexto, 2–3 opciones, costos, riesgos, ownership, criterios de reevaluación. No reescribir ADR antiguo para hacerlo coincidir con implementación actual.

## Disciplina de review

1. Usar `git diff --name-only`, luego buscar imports y callers en archivos afectados.
2. Revisar ArchUnit y tests existentes para no inventar supuestos.
3. Si hay hallazgo en configuración, buscar quién lo usa y perfil en que aplica.
4. No proponer arreglos de todo el sistema cuando solo se pidió revisión de PR.
5. Priorizar correcciones que cortan riesgo sin introducir nueva deuda/side effects.

## Gate final

- [ ] findings based on path/line evidence
- [ ] flaws prioritized by severity/impact
- [ ] external contracts and DB compatibility checked
- [ ] auth and tenant boundaries verified
- [ ] operation failure paths/rollback documented
- [ ] review vs changes scope explicit

## Inspección guiada por dominio

| Pregunta | Evidencia | Consecuencia |
|---|---|---|
| ¿Domain puede compilar sin Spring? | imports + ArchUnit | acoplamiento al framework |
| ¿Application referencia JpaRepository? | imports y wiring | inversión de dependencias rota |
| ¿Tenant se obtiene de identidad? | security context + usecase | exposición horizontal |
| ¿Publicación de evento puede preceder rollback? | transacción/port y tests | entrega fantasma |
| ¿Consulta paginada escala? | SQL + index + bound | latencia y locks |
| ¿Pod/DB pueden coexistir con versión anterior? | migrations + rollout | imposibilidad rollback |

### Presentación del informe

1. **Hallazgos confirmados**: severidad, ubicación, evidencia y fallo.
2. **Riesgos condicionados**: hipótesis y cómo probarla, sin afirmar como bug comprobado.
3. **Buenas prácticas relevantes**: únicamente las verificadas y que afecten el objetivo.
4. **Plan mínimo de reparación**: orden lógico, dependencias, responsable, pruebas de salida.
5. **ADR pendiente**: cuando cambio requiere trade-off no meramente código.

No reportar “falta autenticación” como ausencia corporativa global si la plataforma dispone de controles; especificar exactamente qué evidencia de autorización falta en esta aplicación.
