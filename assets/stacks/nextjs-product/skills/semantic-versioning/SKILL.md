---
name: semantic-versioning
description: Gestiona versiones SemVer 2.0.0 y CHANGELOG.md para cambios de software, integrado con auto-git-commit.
---

# Semantic Versioning — CALPIL Next.js Golden Path

## Objetivo y activación

Aplicar esta skill en tareas que cambien comportamiento, contratos o artefactos versionados del producto.

Se ejecuta después de implementar y validar cambios, y antes de `auto-git-commit`.

Si la tarea no es versionable por política del repositorio, declarar explícitamente `sin bump`.

## Inspección obligatoria

Antes de clasificar el cambio:

1. Revisar política vigente en `AGENTS.md` y `.github/copilot-instructions.md`.
2. Confirmar versión actual en `package.json` y estado de `CHANGELOG.md`.
3. Analizar compatibilidad real del cambio (contrato público, UI, API, config).
4. Verificar si el repositorio versiona por tarea o por release.
5. Confirmar archivos derivados a sincronizar (lockfiles, manifests, pipelines ligados a versión).

## Procedimiento ejecutable

1. Determinar si el cambio requiere bump según política del repositorio.
2. Clasificar el impacto como MAJOR, MINOR, PATCH o sin bump.
3. Justificar clasificación con evidencia funcional y contractual.
4. Actualizar versión únicamente en unidades afectadas cuando corresponda.
5. Actualizar `CHANGELOG.md` con impacto real para consumidores.
6. Revalidar consistencia entre versión, changelog y lockfiles.
7. Integrar código + versionado + changelog en un único commit final.

## Patrón de implementación

Clasificación base:

- `MAJOR`: cambio incompatible de contrato público.
- `MINOR`: capacidad nueva compatible hacia atrás.
- `PATCH`: corrección compatible o mantenimiento sin ampliar contrato.
- `sin bump`: cambios no versionables o política de bump diferido por release.

Ejemplo de reporte:

```text
SemVer: PATCH 1.1.0 -> 1.1.1
Razon: correccion compatible sin ruptura contractual.
CHANGELOG: actualizada seccion Fixed.
```

## Decisiones y anti-patrones

- No inferir nivel SemVer solo por prefijo de commit.
- No crear un commit separado solo para versión/changelog.
- No generar tags, releases ni `push` desde esta skill.
- No forzar upgrades de dependencias para maquillar versionado.
- No declarar bump si la política vigente exige versionar en release.

## Verificación / Definition of Done

Se considera completo cuando:

- La clasificación SemVer está sustentada en impacto real.
- Versión y changelog están sincronizados cuando aplica.
- No hay cambios de versionado fuera de alcance.
- Lockfiles/manifests siguen coherentes.
- El commit final incluye código y versionado en una sola unidad.

Comandos típicos de verificación (si aplican):

```bash
npm run test:unit
npm run test:architecture
npm run lint
npm run build
```

## Contrato de entrega del agente

1. Informar versión previa y nueva, o declarar `sin bump`.
2. Indicar clasificación aplicada y evidencia utilizada.
3. Listar archivos de versionado/changelog modificados.
4. Reportar validaciones ejecutadas y resultado real.
5. Declarar riesgos o pendientes de release cuando existan.

## Guía adicional existente (preservada)

- Ante cambios combinados, aplicar el mayor nivel SemVer del conjunto.
- En ramas `0.y.z`, seguir la política explícita del repositorio.
- Mantener compatibilidad con la skill `auto-git-commit` en un único commit.
- No inventar historial ni resultados no verificados en `CHANGELOG.md`.
