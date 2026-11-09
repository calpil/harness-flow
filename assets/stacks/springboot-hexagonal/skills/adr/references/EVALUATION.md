# Evaluación arquitectónica — Evidencia, criterios y trade-offs

## 1. Preparación

Empezar con cinco frases concretas: situación actual verificada, problema, stakeholders, consecuencias de no decidir y horizonte/alcance. Adjuntar evidencia (archivo, línea, benchmark, PoC, estándar, incidente, contrato). Etiquetar cada afirmación como comprobada, supuesta o pendiente cuando haya ambigüedad.

## 2. Formular alternativas honestas

1. A: candidata recomendada (descrita sin vocabulario de venta).
2. B: alternativa técnica plausible.
3. C: estado actual o mitigación mínima cuando sea viable.

Opciones deben cumplir el **mismo problema** y compararse con **los mismos criterios**. Evitar una opción caricaturizada que exista únicamente para perder.

## 3. Criterios: primero los eliminatorios

| Dimensión | Preguntas clave | Evidencia sugerida |
|---|---|---|
| Seguridad y compliance | AuthN/AuthZ, scopes, roles, JWT, tenants, secrets, datos sensibles, audit trail | Normativa, threat model, prueba de seguridad |
| Arquitectura e integración | Ownership, DDD, API pública/privada, contratos y versionamiento | OpenAPI, eventos, dependencias, diagramas |
| Datos | Consistencia, linaje, calidad, migraciones, retención y ownership | Modelo ER, políticas, migration plan |
| Plataforma | Kubernetes/AKS, redes, Front Door, Gateway API, IaC, Helm, DR | Manifiestos, arquitectura, pipelines |
| Operación | SLO, métricas, trazas, incidentes, soporte, alertas, mantenimiento | Runbooks, telemetría y dashboards |
| Confiabilidad | Escalado, RTO/RPO, concurrencia, failover, idempotencia | Prueba de carga y resiliencia |
| Cambio | Impacto a consumidores, estrategia de migración, rollback | Compatibility matrix, plan por fases |
| Economía | TCO, licencias, horas de soporte, salida de proveedor, egress | Cotización real, proyecciones y supuestos |
| Delivery | Capacidad del equipo, pruebas, pipelines, deuda técnica | Repos, backlog, pruebas, dependencias |

Usar solo dimensiones pertinentes. Registrar explícitamente **No aplica** si corresponde.

## 4. Comparación cualitativa por defecto

Es preferible una evaluación defendible a una puntuación inventada:

| Criterio | Relevancia | Opción A | Opción B | Evidencia / brecha |
|---|---|---|---|---|
| Seguridad | Eliminatorio | Cumple / No cumple / Pendiente | ... | [Referencia real] |
| Mantenibilidad | Alta | Mejor / Similar / Peor | ... | [Referencia real] |
| Costo | Media | Menor / Similar / Mayor / Indeterminado | ... | [Supuestos] |

Una matriz ponderada solo cuando existan **datos y pesos pactados**. En ese caso incluir escala, pesos que suman 100 %, fuente de cada calificación y sensibilidad del resultado.

## 5. Consecuencias negativas y reversibilidad

No omitir: nuevos puntos de fallo, expertise operativo, licencias/egress, vendor lock-in, migración de datos, dobles escrituras, ruptura de contratos, exposición de red, gestión de secretos, regulatorio y complejidad del rollback. Si no hay reversión segura, documentar mecanismos de contención y ventanas.

## 6. Pruebas, adopción y verificación

Definir señales observables (cobertura de contratos, latencia p95, error rate, SLO, cantidad de consumidores migrados, costo de operación). No proponer números arbitrarios como umbral; fijarlos a partir de SLA/SLO válidos, capacidad probada o metas aprobadas.

Estructura de adopción: diseño → PoC/validación → implementación incremental → migración → retiro → monitoreo. Cada etapa con owner, criterio de aceptación y plan de rollback.

## 7. Tópicos específicos para entornos empresariales modernos

Si aplica al repositorio o decisión, verificar explícitamente:

- Multi-organización y multitenancy: aislamiento por país/tenant, autenticación técnica, segregación, API Keys, consumidores cross-org.
- BFF/API: límites públicos vs privados; rutas; autorización **por recurso**, lifecycle de contratos y compatibilidad.
- Bases de datos: naming, ownership, migraciones y versionamiento del esquema; convivencia/consistencia operacional vs analítica.
- Platform engineering: CI/CD, pipelines reutilizables, templates, SAST/SCA, IaC, despliegue GitOps/Helm, observabilidad.
- Frontend: Design System, accesibilidad, PWA, i18n y compatibilidad de dependencias cuando la elección los afecta.
- SSO: issuer/audience/scopes y verificación de tokens; no confundir token de API con identidad técnica.

Estos temas son lentes de evaluación, **no afirmaciones de que todos ya estén implementados**.
