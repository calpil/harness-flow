---
description: Cierre de harness-flow — verify, base pre-merge medida, close hacia la rama destino y chequeo postmerge de rojos nuevos.
argument-hint: <id-feature> [rama-destino]
---

# harness-flow: cierre

Cierra la feature `$1` hacia `$2`. Si no te dieron rama destino, **preguntale al
usuario a que rama integra**: el gate se niega sin `--to` y adivinarla es
exactamente lo que no debe pasar.

> **Shell.** Cada llamada Bash abre un shell nuevo: `$PY` y `$H` no sobreviven,
> asi que el bootstrap va pegado a cada comando, siempre. Los bloques de abajo
> usan bash (macOS, Linux, WSL, y Windows con Git for Windows). En **Windows sin
> Git for Windows la tool Bash es PowerShell**: ahi el interprete se llama
> `python` y el prefijo equivalente es
> `python "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --powershell | Invoke-Expression`,
> invocando despues con `& $PY ...`. Detalle en `references/claude.md`.

## 1. Verify en el arbol correcto

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" verify --feature $1
```

`verify` corre en el WORKTREE de la feature. Si el worktree declarado no existe,
bloquea — no cae a la raiz. Antes de creerle a un rojo, comprueba en que rama
esta cada repo que el AC toca (`git -C <ruta> branch --show-current`): un rojo
sobre el arbol equivocado no es un veredicto sobre el codigo, y un verde tampoco.

**Un conteo parcial no se reporta como total.** `verify` solo mide los AC que
declaran comando. Si el spec tiene 12 AC y 3 traen `verificar:`, un `3/3 en
verde` no dice nada de los otros 9 — el script los lista como `NO se midieron` y
tienes que repetirlo en la misma linea del verde. Ese hueco lo cubre la revision,
no el verify.

## 2. Foto medida ANTES del merge

Los AC de una feature miden SU worktree, asi que por construccion no ven los
choques ENTRE features: dos migraciones que toman el mismo numero, una que
inserta una fila donde otra fija un conteo exacto, un CHECK que choca con un
vocabulario ampliado. Por eso la base se toma antes:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/postmerge_medido.py" base --repo <ruta> --guardar /tmp/base-<svc>.json
```

Usa siempre `postmerge_medido.py`. El viejo `postmerge.py` deduce el veredicto de
un regex `--- FAIL:` sobre la salida `-v` y nunca lee el exit code: da VERDE con
un paquete que no compila, con un `panic` en `init()` y con tests borrados.

## 3. Close

Pregunta primero si la raiz es multi-repo sin `.git` (registro estricto, cierre
`--integrated`) o monorepo legacy. La diferencia esta en
`${CLAUDE_PLUGIN_ROOT}/references/multirepo.md` y no se improvisa.

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" close --feature $1 --status done --to $2 --leccion <clase>
```

Si la feature BORRO tests a proposito (retiro de una integracion, un spec movido),
el cierre `--integrated` los ve desaparecidos y bloquea. No edites la base:
declaralos con `--retirados <json>` (el mismo archivo sirve en
`postmerge_medido.py check` y en `postmerge_frontend.py check`, con
`--microservicio <svc>`). Un destino Go se declara `<paquete>::<TestX>`; uno
frontend, el id medido `[proyecto, archivo, nombre completo]`, y cruzarlos se
rechaza. El gate exige que la base los midiera, que la declaracion la haya
borrado la feature -- un `//go:build`, un `.skip`/`.todo`, renombrar solo el
describe o dejar el titulo escrito tras un wrapper NO son bajas -- y que el
review sellado los DECLARE: en frontend, la ruta del spec y el titulo entre
comillas en una misma linea que no sea la del sello. Contrato en
`references/multirepo.md`.

Sin `--integrated`, `close` **ejecuta el merge de verdad** (`git merge --no-ff`).
Aborta sin tocar el backlog si el arbol esta sucio o el merge conflictua.
`start` puede dejar `harness/` y `docs/vault/` sucios. `approve-spec` y
`revision` no regeneran el vault: tocan el spec o el review en `docs/` y el
backlog en `harness/`. Muestralos con `git status` y pregunta antes de
commitearlos; no los descartes.
Despues del `done`, el close sincroniza PRD/SDD y regenera el vault: vuelven a
quedar cambios en `docs/` y hay que reportarlos, no darlos por publicados. Agrega
`--publicar-atlassian` SOLO si existe `harness/atlassian.json` y el usuario pidio
publicar remoto.

## 4. Postmerge sobre la rama destino

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/postmerge_medido.py" check --repo <ruta> --base /tmp/base-<svc>.json
```

Compara `(paquete, test)` contra la base y falla (exit 2) por rojos NUEVOS, build
roto o tests desaparecidos. Al verificar el exit a mano **no uses un pipe**
(`| tail`): te devuelve el status del tail, no el del gate.

Si aparecen rojos nuevos: ficha el choque, no bajes la asercion que lo detecto.

## 5. Comprueba que el merge existe

```bash
git -C <ruta> log --oneline -1 $2
```

El mensaje de un script no es evidencia de que el merge ocurrio. Y un `15/15 en
verde` de `verify` es un veredicto sobre la rama de la feature, NO sobre la
integracion: no lo reportes como si lo fuera.

## 6. Cierre historico (sin base preintegracion medible)

Si la feature ya esta integrada y su base preintegracion NO se puede medir con
el contrato vigente (contrato de tests que cambio desde entonces, o tests que
otras features renombraron/movieron/borraron y que el cierre normal veria como
"desaparecidos" sin poder declararlos bajas de ESTA feature), pregunta al
usuario si autoriza un cierre historico: muestrale por que no hay base
medible y esperale el SI antes de pasar `--yes`. Diseno completo:
`docs/diseno-arnes-cierre-historico.md` (raiz del proyecto); contrato y
garantias en `references/multirepo.md`, seccion "Cierre historico".

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" close --feature $1 --status done --to $2 \
  --integrated --historico --yes --motivo "<por que no hay base medible>" --leccion <clase> [--retirados <json>]
```

`--yes` y `--motivo` son la autorizacion explicita -- igual que `approve-spec`,
SOLO se pasan despues del SI del usuario en el chat, nunca por cuenta propia
del agente -- y quedan escritos en el backlog (`cierre_historico`). Es una
barrera de PROCESO, no una restriccion tecnica de antiguedad: el gate no
verifica que la feature sea vieja ni que se haya intentado medir una base
antes de aceptar `--historico`. NO uses este camino en una feature nueva con
base medible solo porque es mas corto: el camino normal (`--postmerge`) sigue
siendo el que corresponde ahi. `--historico` y `--postmerge` son mutuamente
excluyentes: no se puede pedir las dos cosas.
Sigue exigiendo spec aprobado/fresco, review sellado y verify verde del
contexto vigente, leccion y registro multi-repo validos: NO es un atajo, solo
cambia COMO se mide el destino (exige medicion COMPLETA en cero, sin comparar
contra una base). Si el repo agrego tests que otra feature borro despues,
declaralos en `--retirados` con la MISMA sintaxis que el cierre normal -- el
gate distingue solo por el modo si exige "medido en la base" (normal) o
"declarado en la fuente" (historico).
