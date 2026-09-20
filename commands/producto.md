---
description: Rol producto de harness-flow — redacta el PRD inicial o el SDD de arquitectura en un borrador sin proteger y lo lleva al ritual de aprobacion del usuario, que lo sella en docs/prd o docs/sdd.md.
argument-hint: prd|sdd
---

# harness-flow: producto (rol producto)

Redacta el documento `$1` (`prd` o `sdd`) ANTES de que existan features en el
backlog, o cuando el usuario pide cambiarlo. Si no te dijeron cual, pregunta.
Si `/harness-flow:estado` ya muestra `prd:`/`sdd:` aprobados y nadie pidio
cambiarlos, este rol no corre: pasa a `/harness-flow:spec`.

> **Shell.** Cada llamada Bash abre un shell nuevo: `$PY` y `$H` no sobreviven,
> asi que el bootstrap va pegado a cada comando, siempre. Los bloques de abajo
> usan bash (macOS, Linux, WSL, y Windows con Git for Windows). En **Windows sin
> Git for Windows la tool Bash es PowerShell**: ahi el interprete se llama
> `python` y el prefijo equivalente es
> `python "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --powershell | Invoke-Expression`,
> invocando despues con `& $PY ...`. Detalle en `references/claude.md`.

## Lo que no es negociable

- **Nunca escribes `docs/prd/**` ni `docs/sdd.md` a mano.** Son del usuario y
  `gate.py check` marca en rojo cualquier edicion de agente fuera de contrato.
  Tu archivo es `docs/borrador-$1.md`, que no esta protegido.
- El bloque `<!-- harness-flow:features -->` no va en el borrador: lo mantiene
  `documentacion.py sync` al cerrar cada feature. Con ese bloque, `aprobar` se niega.
- Cada seccion lleva contenido real. Las guias `<!-- -->` de la plantilla se
  reemplazan o se borran; una seccion que solo tiene guia cuenta como vacia y
  `aprobar` se niega nombrandola.

## 1. Contexto antes de escribir

Para el PRD, la fuente es lo que cuente el usuario: pregunta problema,
usuarios, objetivos y que queda fuera antes de inventar nada. Para el SDD,
cruza el arbol real en vez de suponerlo:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/contexto.py" estado
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/hub.py" impacto --microservicio <proyecto>/<servicio>
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/leccion.py" list
```

Para una pregunta puntual sobre el codigo, `graphify query "<pregunta>" --graph <combinado>`.

## 2. Borrador

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/producto.py" borrador --doc $1
```

Crea `docs/borrador-$1.md` desde `${CLAUDE_PLUGIN_ROOT}/templates/$1.md`, o
desde el cuerpo manual que ya tenga el destino (para cambiar un documento
existente sin perder lo que el usuario escribio). Si el borrador ya existe, no
lo toca. Rellenalo con las tools de archivo.

- PRD: sigue la anatomia de la plantilla, en orden. **Todo empieza con una
  historia** contada en palabras, con nombre y momento ("Marta cerro su compra
  un viernes a las 6 de la tarde. Nadie la llamo."), no con tecnicismos
  ("escuchar el cambio de estado"). Despues el resumen `Hoy:`/`Despues:`, los
  objetivos y no-objetivos con nombre (`- O1:`, `- NO1:`) para citarlos, el
  flujo dibujado dos veces, los datos (disparador, entidades, interruptor,
  candado) y el pseudo-codigo como acuerdo. **Nunca codigo final**: un bloque
  ` ```go ` o ` ```sql ` hace que `aprobar` se niegue; el codigo se escribe en
  el spec y en el repo. El tamano lo decide el cambio: un ajuste, una pagina;
  una funcionalidad, 3-8; un producto nuevo, varios PRDs anidados.
- PRD: `## Features candidatas` lleva una linea por PRD anidado con el formato
  exacto `- F-1: <nombre>: <resultado observable> (cumple O1)`. Es lo que
  despues entra al backlog.
- SDD: cada decision con la alternativa descartada y el porque. Si hay
  migraciones numeradas, di contra que rama se reserva el numero.

## 3. Ritual de aprobacion

Este paso es del USUARIO, no tuyo.

1. MUESTRA el borrador completo en el chat.
2. PREGUNTA explicitamente si lo aprueba.
3. Solo con un SI explicito:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/producto.py" aprobar --doc $1 --yes
```

Copia el cuerpo a `docs/prd/PRD-master.md` o `docs/sdd.md` conservando el bloque
generado si ya existia, y sella `documentos.$1` en `harness/feature_list.json`.
Nunca lo corras por tu cuenta ni "para agilizar": el script se niega sin
`--yes`, y `--yes` significa que el usuario dijo que si, no que tu lo asumiste.

Si `aprobar` se niega porque hay features multi-repo registradas abiertas, no
las toques: su registro fijo los bytes del PRD y nada lo reautoriza. Diselo al
usuario; se aprueba cuando cierren.

## 4. Despues de aprobar

- El PRD sellado lo acepta `gate.py check` aunque no este commiteado. Recuerdale
  al usuario que commitee `docs/prd/PRD-master.md`; tu no lo commiteas.
- Cada `F-n` del PRD entra al backlog con el comando que imprime `aprobar`:

  ```bash
  eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/add.py" --name "<nombre>" --prd docs/prd/PRD-master.md
  ```

  y su spec se escribe con `/harness-flow:spec <id>`.
- Cambiar el borrador despues de aprobarlo no cambia el destino: hay que volver
  a mostrarlo y re-aprobar. `estado.py` lo marca como "borrador cambiado despues".
