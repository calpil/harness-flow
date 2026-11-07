# ADR-XXXX — [Título de la decisión]

> **Architecture Decision Record (ADR)**  
> Una decisión arquitectónica por documento. Este registro explica **por qué** se tomó, las alternativas consideradas y sus consecuencias.

## 1. Metadatos

| Campo | Valor |
|---|---|
| **ID** | ADR-XXXX |
| **Estado** | Propuesto / Aprobado / Rechazado / Obsoleto / Reemplazado |
| **Fecha** | AAAA-MM-DD |
| **Última revisión** | AAAA-MM-DD |
| **Responsable** | [Nombre / equipo] |
| **Aprobadores** | [Roles / comité, si aplica] |
| **Dominio / capacidad** | [Dominio de arquitectura / capacidad de negocio] |
| **Alcance** | [Corporativo / plataforma / producto / servicio / país] |
| **Sistemas afectados** | [Sistemas / repositorios / componentes] |
| **Decisión relacionada** | [ADR-XXXX, RFC o iniciativa] |
| **Reemplaza a** | [ADR-XXXX o N/A] |
| **Reemplazado por** | [ADR-XXXX o N/A] |

## 2. Resumen ejecutivo

**Decisión:** [Una o dos frases indicando lo que se decidió, sin ambigüedad.]

**Motivo principal:** [Por qué esta decisión es necesaria ahora.]

## 3. Contexto y problema

[Describir la situación actual, el problema, las restricciones y el impacto de no decidir. Incluir hechos verificables y enlaces a evidencias.]

### Supuestos y restricciones

- **Supuestos:** [Supuestos explícitos que deben validarse.]
- **Restricciones:** [Seguridad, regulación, presupuesto, plazo, tecnología, operaciones, compatibilidad, etc.]
- **Fuera de alcance:** [Aspectos que este ADR no resuelve.]

## 4. Objetivos y criterios de decisión

| Criterio | Prioridad | Cómo se evaluará |
|---|---|---|
| Seguridad y cumplimiento | Alta | [Requisitos verificables] |
| Operación y mantenibilidad | Alta | [SLO, soporte, observabilidad] |
| Integración y compatibilidad | Alta | [Contratos, interoperabilidad] |
| Costo total (TCO) | Media | [Implementación + operación] |
| Escalabilidad y evolución | Media | [Límites, crecimiento esperado] |

> Ajustar prioridades y criterios al contexto; evitar asignar puntuaciones sin evidencia.

## 5. Alternativas consideradas

### Opción A — [Nombre]
- **Descripción:** [En qué consiste.]
- **Ventajas:** [Beneficios comprobables.]
- **Desventajas y riesgos:** [Costos, compromisos, restricciones.]
- **Esfuerzo / impacto:** [Estimación y supuestos.]

### Opción B — [Nombre]
- **Descripción:** [...]
- **Ventajas:** [...]
- **Desventajas y riesgos:** [...]
- **Esfuerzo / impacto:** [...]

### Opción C — Mantener el estado actual (si aplica)
- **Consecuencias de no cambiar:** [...]

### Comparación resumida

| Criterio | Opción A | Opción B | Estado actual |
|---|---|---|---|
| Seguridad | [Evaluación] | [Evaluación] | [Evaluación] |
| Operación | [Evaluación] | [Evaluación] | [Evaluación] |
| Costo | [Evaluación] | [Evaluación] | [Evaluación] |
| Evolución | [Evaluación] | [Evaluación] | [Evaluación] |

## 6. Decisión

**Se adopta:** **[Opción elegida]**.

**Alcance preciso:** [Dónde se aplica y dónde no.]

**Reglas de implementación:**
1. [Regla obligatoria y comprobable.]
2. [Regla obligatoria y comprobable.]
3. [Excepciones autorizadas, si existen, y cómo se gestionan.]

**Justificación:** [Explicar el trade-off: por qué esta opción supera a las demás conforme a los criterios y evidencias.]

## 7. Consecuencias y trade-offs

### Positivas
- [Beneficio esperado y, si es posible, cómo medirlo.]

### Negativas / costos aceptados
- [Deuda técnica, complejidad, costo de migración o dependencia asumida.]

### Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación | Responsable |
|---|---|---|---|
| [Riesgo] | [Alto/Medio/Bajo] | [Acción concreta] | [Equipo] |

## 8. Implicancias de arquitectura

- **Aplicaciones y APIs:** [Servicios, contratos, BFF, versionado, compatibilidad.]
- **Datos:** [Modelo, ownership, residencia, migración, retención.]
- **Seguridad:** [Autenticación, autorización, secretos, auditoría.]
- **Infraestructura y despliegue:** [Cloud, redes, Kubernetes, IaC, CI/CD.]
- **Operación:** [Observabilidad, SLO, soporte, respaldo, recuperación.]
- **Dependencias:** [Equipos, proveedores, decisiones previas y futuras.]

> Completar únicamente los apartados relevantes; usar N/A cuando corresponda.

## 9. Plan de adopción y validación

| Etapa | Entregable / criterio de aceptación | Responsable | Fecha objetivo |
|---|---|---|---|
| Diseño | [Diseño / contrato aprobado] | [Equipo] | [Fecha] |
| Implementación | [Cambio desplegable] | [Equipo] | [Fecha] |
| Validación | [Pruebas y métricas] | [Equipo] | [Fecha] |
| Adopción | [Migración / retiro de legado] | [Equipo] | [Fecha] |

**Indicadores de éxito:** [Métricas, umbrales y evidencia requerida.]

**Reversibilidad / rollback:** [Cómo revertir o qué impide hacerlo.]

**Disparadores de revisión:** [Cambios en regulación, volumen, tecnología, costos, incidentes, etc.]

## 10. Referencias y trazabilidad

- **Diagramas (C4, secuencia, despliegue):** [Enlaces]
- **Historias / épicas / backlog:** [Enlaces]
- **Repositorios / PR / pipelines:** [Enlaces]
- **Estándares, políticas y contratos:** [Enlaces]
- **Evidencia / benchmark / PoC:** [Enlaces]

## 11. Historial de decisiones

| Fecha | Autor | Cambio |
|---|---|---|
| AAAA-MM-DD | [Nombre] | Creación del ADR (Propuesto) |

---

### Reglas de uso

- Un ADR registra **una decisión concreta**; no reemplaza un documento de diseño detallado.
- Una vez **Aprobado**, no reescribir retrospectivamente el razonamiento: crear un nuevo ADR que lo reemplace y enlazar ambos.
- Mantener estados, fechas, responsables y referencias consistentes con el repositorio.
- Nombre sugerido: `docs/adr/ADR-0001-titulo-corto.md`.
