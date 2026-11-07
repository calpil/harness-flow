# ADR Quality Gate — Checklist para revisión humana y asistida

## Bloqueante

- [ ] Se identifica una sola decisión verificable, y la sección `Decisión` no es contradictoria con el resumen.
- [ ] No presenta como `Aprobado` una propuesta sin evidencia de autorización.
- [ ] No contradice una política/ADR vigente sin excepción formal y trazada.
- [ ] ID, nombre de archivo, enlaces `Reemplaza a` y `Reemplazado por` consistentes.
- [ ] No hay credenciales, claves, PII injustificada ni contratos restringidos copiados indebidamente.
- [ ] Se consideraron riesgos críticos de seguridad/compliance y aislamiento multi-tenant, cuando corresponde.

## Mayor

- [ ] Contexto basado en hechos verificables y alcance de la decisión explícito.
- [ ] Se analizan dos o más cursos de acción creíbles (statu quo cuando proceda).
- [ ] Criterios, restricciones y trade-offs justifican la alternativa seleccionada.
- [ ] Consecuencias negativas y costos no se esconden.
- [ ] Impacto sobre APIs, datos, seguridad, plataforma y consumidores analizado en las partes aplicables.
- [ ] Evidencias mínimas para costos, riesgos y capacidad; vacíos marcados como tales.
- [ ] Plan de adopción, compatibilidad, responsables, medición y rollback/irreversibilidad.
- [ ] Metadatos/ownership y estándares relacionados claramente trazados.

## Menor

- [ ] Título claro, lenguaje preciso y sin marketing.
- [ ] Referencias de PR, historias, contratos y diagramas cuando existan.
- [ ] Fechas, glosario y formato consistentes.
- [ ] Indicadores y disparadores de revisión realistas.
- [ ] No hay tablas y listas vacías ni placeholders genéricos en decisiones aprobadas.

## Veredicto

- **Requiere ajustes**: uno o más bloqueantes o mayores sin resolver.
- **Apto para revisión**: no hay bloqueantes/mayores y los riesgos abiertos están explícitos.
- **No verificable**: no hay fuentes suficientes para confirmar una afirmación crítica.

Nunca imprimir "Aprobado" como veredicto del asistente: esa palabra es un **estado de gobierno** documentado por autoridad real.

## Formato de hallazgo

```text
[BLOQUEANTE | MAYOR | MENOR] Título
- Archivo/sección: ...
- Evidencia: ...
- Impacto: ...
- Remediación: ...
- Owner sugerido: ...
```
