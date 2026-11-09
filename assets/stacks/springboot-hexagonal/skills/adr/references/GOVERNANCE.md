# Gobierno de ADR — Alcance, estados y relaciones

## 1. Alcance y autoridad

Una decisión debe residir donde su alcance es gobernable:

| Nivel | Cuándo usar | Propietario y aprobación |
|---|---|---|
| Corporativo | Estándar transversal: lenguaje, patrón, identidad, seguridad, plataforma | Arquitectura empresarial / autoridad designada por organización |
| Plataforma / capacidad | Contratos comunes, gateway, BFF, data platform, observabilidad | Owner de plataforma, con revisión de arquitectura transversal |
| Dominio / producto | Elección específica de un bounded context o producto | Owner/arquitecto del producto y responsables afectados |
| País / tenant | Requisitos locales excepcionales, soberanía o proceso local | Owner local + gobierno central si contradice estándar |

Los aprobadores anteriores son **roles orientativos**, no una autorización implícita. El repositorio/organización define los responsables reales. Escalar a arquitectura empresarial si una decisión local cambia contratos compartidos, seguridad corporativa, modelo canónico de datos o capacidades comunes.

## 2. Estados permitidos

- `Propuesto`: texto en evaluación. Puede contener pendientes marcados. **No es una orden de implementación**.
- `Aprobado`: existe aprobación trazable de quien tiene autoridad. No basta que la IA considere buena la solución.
- `Rechazado`: se evaluó y descartó; conservar por aprendizaje, incluyendo motivo y fecha.
- `Obsoleto`: la decisión ya no aplica y no existe necesariamente sucesora directa; explicar desactivación.
- `Reemplazado`: hay otra decisión vigente, explícitamente enlazada.

Flujos típicos: `Propuesto → Aprobado → Reemplazado`, `Propuesto → Rechazado`, `Aprobado → Obsoleto`. El cambio a `Aprobado`/`Rechazado` se hace solo con evidencia de autoridad.

## 3. Identificación y ubicación

- Convención de nombre: `docs/adr/ADR-0001-titulo-corto.md`.
- ID monotónico dentro de cada repositorio, de 4 dígitos como mínimo. No reciclar un ID de ADR retirado; mantener históricos.
- Si existe una convención del repositorio distinta, conservarla; no renombrar masivamente.
- El índice es `docs/adr/README.md`, con estados y enlaces. La herramienta `index` protege la información manual fuera de sus marcadores.
- Si se copia una skill a varios repos, la numeración es **por repositorio**, no global de CALPIL. Para una autoridad global, mantener los ADR corporativos en un repositorio corporativo canónico y referenciarlos desde los repos de producto.

## 4. Cambios sin borrar historia

Aprobados son semánticamente inmutables: no reescribir el contexto histórico para ajustarlo al presente. Se admiten arreglos tipográficos, enlaces, metadatos de vigencia y anotaciones editoriales claramente fechadas. Cambiar tecnología, límites, consecuencias sustantivas o motivos requiere nuevo ADR.

Ejemplo de reemplazo:

```text
ADR-0008 (Aprobado)
  ↓ propuesta nueva
ADR-0017 (Propuesto; Reemplaza a: ADR-0008)
  ↓ aprobación real
ADR-0008 (Reemplazado; Reemplazado por: ADR-0017)
ADR-0017 (Aprobado; Reemplaza a: ADR-0008)
```

## 5. Excepciones y herencia

Un ADR local que se desvíe de una norma corporativa debe incluir: norma base, motivación excepcional, impacto, vigencia, mitigación, riesgo residual, owner y autorización de excepción real. La skill no concede excepciones.

Una tecnología corporativa preferida no implica que todos los repos la implementen actualmente. Documentar el **estado observado** y el **estado objetivo** por separado.

## 6. ADR ≠ otros artefactos

- ADR: la **decisión y su razonamiento**, duradera e históricamente rastreable.
- RFC: propuesta abierta de discusión/diseño, útil antes del ADR.
- Diseño C4 / documento técnico: estructura de solución y contratos completos.
- Historia/PR: cambio ejecutable, criterios de aceptación, tests y entrega.
- Estándar: regla repetible obligatoria; puede derivar de uno o más ADR corporativos.

No forzar contratos extensos ni documentos operativos completos dentro de un ADR: enlazar los artefactos de detalle.

## 7. Reglas de cumplimiento

En revisiones y PR de cambios arquitectónicos significativos, verificar si existe ADR aplicable, si sigue vigente y si la implementación lo contradice. Documentar excepciones reales. No obligar a un ADR por cada issue o cambio de código.
