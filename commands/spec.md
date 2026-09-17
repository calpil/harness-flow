---
description: Rol leader de harness-flow — escribe el spec de una feature con AC verificables y lo lleva al ritual de aprobacion del usuario.
argument-hint: <id-feature>
---

# harness-flow: spec (rol leader)

Escribe el spec de la feature `$1` ANTES de tocar codigo. Si no te dieron id,
pregunta cual, o corre `/harness-flow:estado` para listarlas.

Recordatorio de shell: en Claude Code cada llamada Bash abre un shell nuevo, asi
que el `eval` de entorno va en la misma llamada que el script, siempre.

## 1. Contexto antes de leer archivos a ciegas

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/contexto.py" brief --feature $1
```

Ese brief trae AC, reglas, lecciones, impacto del hub y superficie de contacto
del grafo. Si dice que el contexto esta vencido, refresca antes de disenar:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/contexto.py" refrescar
```

Para una pregunta puntual que el brief no cubre,
`graphify query "<pregunta>" --graph <combinado>`.

Despues, los dos que el brief no reemplaza:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/hub.py" impacto --microservicio <proyecto>/<servicio>
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/leccion.py" list
```

Las lecciones se leen **antes** de disenar, no despues de romper algo.

## 2. Escribe el spec

`docs/spec-feature-$1-<slug>.md`, con `Estado: draft`, siguiendo
`${CLAUDE_PLUGIN_ROOT}/templates/spec.md`. Lo que no es negociable:

- AC numerados `AC-1`, `AC-2`, … sin saltos, en Given/When/Then, cada uno
  verificable por un tercero.
- El comando de verificacion va `` `verificar: <cmd>` `` dentro del backtick o en
  una linea `Comando: `` `<cmd>` `` debajo del AC. Un AC sin comando es legitimo:
  lo verifica el reviewer a mano.
- **Los comandos apuntan al worktree de la feature**, nunca a la carpeta
  compartida del repo. Con varias features vivas, `/ruta/ms-foo` esta parado en
  la rama de quien hizo checkout ultimo: el AC mediria un arbol ajeno y da verde
  falso si el `-run` no engancha nada, o rojo falso si la rama vecina tiene otro
  codigo. Crea el worktree ANTES de sellar el spec:

  ```bash
  eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/worktree.py" start --feature $1
  ```
- Si la feature trae migracion numerada, **reserva el numero contra la rama de
  integracion**, no contra el worktree: cada rama ve "el siguiente libre" en un
  arbol distinto y la colision esta garantizada.

## 3. Ritual de aprobacion

Este paso es del USUARIO, no tuyo.

1. MUESTRA el spec en el chat.
2. PREGUNTA explicitamente si lo aprueba.
3. Solo con un SI explicito:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" approve-spec --feature $1 --yes
```

Nunca corras eso por tu cuenta ni "para agilizar". El script se niega sin
`--yes`, y `--yes` significa que el usuario dijo que si — no que tu lo asumiste.

Cambiar el spec despues de aprobarlo invalida el sello (firma sha1 del cuerpo).
Eso es deliberado: hay que volver a mostrarlo y re-aprobarlo.
