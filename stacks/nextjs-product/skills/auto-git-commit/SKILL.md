---
name: auto-git-commit
description: Finaliza automáticamente cada solicitud de desarrollo con un git add selectivo y un commit local descriptivo, tras validar los cambios, sin push. Se ejecuta al concluir cada prompt que modifica archivos del repositorio.
---

# Auto Git Commit — cierre obligatorio de prompts

## Objetivo y activación

Aplicar esta skill al cierre de todo prompt que modifique archivos versionados del repositorio.

La autorización cubre únicamente `git add` selectivo y `git commit` local. No autoriza `git push`, creación de PR, tags, releases ni despliegues.

Si el prompt no produce cambios de archivos, no crear commits vacíos.

## Inspección obligatoria

Antes de commitear, inspeccionar estado y diferencias reales:

- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short`
- `git diff --name-status`
- `git diff --cached --name-status`

Identificar cambios preexistentes y mantenerlos fuera del commit de la tarea actual, salvo instrucción explícita del usuario.

## Procedimiento ejecutable

1. Finalizar implementación y ejecutar validaciones aplicables existentes en `package.json`.
2. Revisar `git diff --check` para detectar conflictos de formato, espacios y errores básicos.
3. Confirmar que no se incluyan secretos o artefactos no deseados (`.env`, `.npmrc` autenticado, binarios accidentales).
4. Hacer stage selectivo con rutas explícitas (`git add -- <ruta...>` o `git add -p` cuando aplique).
5. Verificar staging final con `git diff --cached --stat` y `git diff --cached`.
6. Crear commit con mensaje detallado tipo Conventional Commit y cuerpo con contexto, cambios y validación real.
7. Confirmar resultado con `git log -1 --format='%h %s'` y `git status --short`.

## Patrón de implementación

Plantilla recomendada:

```text
<tipo>(<scope>): <resumen>

Contexto:
- <problema principal>

Cambios:
- <cambio 1>
- <cambio 2>

Validación:
- <comando>: <resultado real>
```

Tipos sugeridos: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`, `ci`, `perf`, `security`.

## Decisiones y anti-patrones

- No usar `git add .` o `git add -A` de forma indiscriminada.
- No mezclar cambios ajenos preexistentes en el mismo commit.
- No usar comandos destructivos automáticos (`git reset --hard`, `git clean -fd`, `git stash`).
- No evadir hooks con `--no-verify` salvo autorización explícita del usuario.
- No declarar validaciones no ejecutadas como aprobadas.

## Verificación / Definition of Done

Esta skill queda completa cuando:

- Existe un commit local con solo cambios de la tarea.
- El mensaje del commit es trazable y describe contexto + cambios + validación.
- Las validaciones ejecutadas están reportadas con resultado real.
- Los cambios preexistentes no fueron arrastrados por accidente.
- Si no hubo cambios, se reporta explícitamente que no se creó commit.

## Contrato de entrega del agente

1. Reportar hash corto y título del commit creado.
2. Listar archivos incluidos y motivo de cada grupo.
3. Informar comandos de validación ejecutados y resultado.
4. Declarar validaciones no ejecutadas y motivo.
5. Señalar bloqueos (hooks, permisos, conflictos, identidad Git) cuando existan.
