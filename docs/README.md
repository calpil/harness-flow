# Documentación Técnica de Harness Flow

Bienvenido al directorio de documentación técnica y memorias de arquitectura de **Harness Flow**. Este repositorio contiene los informes de auditoría, las memorias técnicas de hitos implementados y los marcos metodológicos que gobiernan la ejecución de los agentes.

---

## 1. Índice de Documentos en `docs/`

| Documento | Propósito y Alcance | Audiencia Principal |
| :--- | :--- | :--- |
| [`memoria-tecnica-implementaciones.md`](memoria-tecnica-implementaciones.md) | **Memoria técnica maestra** que documenta exhaustivamente todos los hitos implementados: stacks (.NET, Rust), metodologías (Karpathy/STE100, DDIA, Ousterhout, GoF/Fowler) y auditoría de los 8 stacks CALPIL. | Arquitectos, Líderes Técnicos e Ingenieros de Plataforma |
| [`principios-karpathy-ste100-harness-flow.md`](principios-karpathy-ste100-harness-flow.md) | Informe especializado sobre los **7 principios de Andrej Karpathy** y la norma aeroespacial **ASD-STE100** para comunicación de alta densidad y micro-reportes. | Implementers, Revisores y Diseñadores de Prompts |
| [`explicacion-y-diagnostico.md`](explicacion-y-diagnostico.md) | **Diagnóstico de salud y auditoría estructural** del arnés: verificación de gates, postmerge medido, scripts neutralizados y telemetría de procesos CBM. | Mantenedores del arnés y Administradores de Infraestructura |

---

## 2. Los Hitos Técnicos Implementados

El detalle exhaustivo y los componentes de cada hito se encuentran en [`memoria-tecnica-implementaciones.md`](memoria-tecnica-implementaciones.md):

```mermaid
flowchart TD
    H1["<b>Hito 1: Stack .NET Hexagonal</b><br/>C# 13 / .NET 10 LTS, Clean Architecture, 4 rules, 9 skills y check-architecture.py"]
    H2["<b>Hito 2: Principios Karpathy & ASD-STE100</b><br/>Prompts compactos, frases &le; 20 palabras, Mermaid prioritario y micro-reportes"]
    H3["<b>Hito 3: Patrones de Datos DDIA (Kleppmann)</b><br/>Transactional Outbox, OCC con version, Idempotency-Key y Expand-Contract"]
    H4["<b>Hito 4: Stack Rust Hexagonal</b><br/>Rust 2021/2024, Axum, Tokio, SQLx, 4 rules, 9 skills y check-architecture.py"]
    H5["<b>Hito 5: Filosofía Ousterhout (Stanford)</b><br/>Deep Modules, anti-classitis, inversión 10-20% y Design It Twice"]
    H6["<b>Hito 6: Auditoría Integral 8 Stacks</b><br/>Verificadores AST/regex para todos los stacks; 8/8 plantillas CALPIL COMPLIANT"]
    H7["<b>Hito 7: Patrones GoF & Fowler Refactoring</b><br/>GoF por capa hexagonal, regla de Dos Sombreros (Beck/Fowler) y 24 Code Smells"]
    H8["<b>Hito 8: Auto-Normalización y Feature #0</b><br/>Auto-instala Nivel 1 (reglas/skills) y crea F-0 prioritaria bloqueando features de negocio si hay violaciones"]
    H9["<b>Hito 9: Algoritmos y Estructuras CLRS</b><br/>Complejidad asintótica, DAG de features (DFS 3-color/Kahn) y prevención de N+1 y O(N^2)"]
    H10["<b>Hito 10: AI Engineering (Chip Huyen)</b><br/>Pipeline 5 capas, Structured Outputs, Golden Datasets, Bounded Reflection y AI-as-a-Judge"]
    H11["<b>Hito 11: Microservicios y Sistemas Distribuidos (Sam Newman)</b><br/>Database per Service, Monolith-First, comunicación síncrona/EDA bajo YAGNI, resiliencia y Expand-Contract"]

    H1 --> H2 --> H3 --> H4 --> H5 --> H6 --> H7 --> H8 --> H9 --> H10 --> H11
```

---

## 3. Conexión con Referencias Normativas en `references/`

Los documentos de `docs/` complementan y fundamentan las guías operativas que los agentes cargan en tiempo de ejecución:

* [`references/microservicios-sam-newman.md`](../references/microservicios-sam-newman.md): Principios de microservicios y sistemas distribuidos (Sam Newman), Database per Service, resiliencia y contratos.
* [`references/ai-engineering-chip-huyen.md`](../references/ai-engineering-chip-huyen.md): Arquitectura de AI Engineering (Chip Huyen), pipeline de 5 capas, Structured Outputs y mitigación de sesgos en AI-as-a-Judge.
* [`references/algoritmos-y-estructuras-clrs.md`](../references/algoritmos-y-estructuras-clrs.md): Fundamentos de algoritmos y estructuras de datos (CLRS), análisis asintótico, ordenación topológica y prevención de anti-patrones.
* [`references/patrones-gof-y-refactoring.md`](../references/patrones-gof-y-refactoring.md): Matriz de patrones GoF por capa hexagonal, regla de los dos sombreros y catálogo de 24 *Code Smells*.
* [`references/filosofia-diseno-ousterhout.md`](../references/filosofia-diseno-ousterhout.md): Guía de diseño de software de John Ousterhout (*Deep Modules*, combate a la *classitis*, *Design It Twice*).
* [`references/patrones-datos-ddia.md`](../references/patrones-datos-ddia.md): Patrones de datos distribuidos basados en Martin Kleppmann (Transactional Outbox, OCC, Idempotencia).
* [`references/comunicacion-ste100-y-prompts.md`](../references/comunicacion-ste100-y-prompts.md): Norma de redacción técnica ASD-STE100 y optimización de prompts de Karpathy.
* [`references/context7-documentacion-oficial.md`](../references/context7-documentacion-oficial.md): Integración con Context7 MCP, enlaces oficiales por stack y escáneres de seguridad CVE.
* [`references/vertical-slice.md`](../references/vertical-slice.md): Metodología de desarrollo vertical, costuras públicas y modo Pair interactivo.

---

## 4. Estado de los 8 Stacks Tecnológicos

Todos los stacks se encuentran auditados, normalizados y gobernados mediante sus correspondientes manifiestos, reglas modulares, habilidades y verificadores ejecutables:

1. [`stacks/golang-hexagonal/`](../stacks/golang-hexagonal/): Go estándar puro en dominio, puertos Driving/Driven, `check-architecture.py`.
2. [`stacks/angular-product/`](../stacks/angular-product/): Angular 17+ Zoneless, Signals, componentes standalone, `check-architecture.py`.
3. [`stacks/dotnet-hexagonal/`](../stacks/dotnet-hexagonal/): C# 13 / .NET 10 LTS, Clean Architecture, xUnit, `check-architecture.py`.
4. [`stacks/rust-hexagonal/`](../stacks/rust-hexagonal/): Rust 2021/2024, Axum 0.8, Tokio, SQLx, `check-architecture.py`.
5. [`stacks/nextjs-product/`](../stacks/nextjs-product/): Next.js App Router, React Server Components, `check-architecture.py`.
6. [`stacks/springboot-hexagonal/`](../stacks/springboot-hexagonal/): Spring Boot 3 Java, arquitectura hexagonal, `check-architecture.py`.
7. [`stacks/nestjs-hexagonal/`](../stacks/nestjs-hexagonal/): NestJS TypeScript, módulos desacoplados, `check-architecture.py`.
8. [`stacks/python-dataproduct/`](../stacks/python-dataproduct/): Python Data Product, FastAPI, Polars, `check-architecture.py`.
