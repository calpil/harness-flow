---
description: Arranque de sesion de harness-flow — features abiertas, gates pendientes y edad del grafo, contrastado contra el backlog.
---

# harness-flow: estado

Arranque de sesion en un proyecto con `harness/feature_list.json`. Corre esto
ANTES de responder nada sustantivo sobre el proyecto.

> **Shell.** Cada llamada Bash abre un shell nuevo: `$PY` y `$H` no sobreviven,
> asi que el bootstrap va pegado a cada comando, siempre. Los bloques de abajo
> usan bash (macOS, Linux, WSL, y Windows con Git for Windows). En **Windows sin
> Git for Windows la tool Bash es PowerShell**: ahi el interprete se llama
> `python` y el prefijo equivalente es
> `python "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --powershell | Invoke-Expression`,
> invocando despues con `& $PY ...`. Detalle en `references/claude.md`.

## Preflight

1. Comprueba que existe `harness/feature_list.json` desde el directorio actual
   hacia arriba. Si no existe, este proyecto no tiene arnes instalado: dilo y
   detente — no lo inicialices sin que el usuario lo pida.
2. Resuelve el entorno y mira el panorama:

   ```bash
   eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/estado.py"
   ```

   Si `entorno.py` sale con exit distinto de 0, correlo a secas
   (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py"`) para ver el diagnostico
   y arregla con `--instalar-deps`. No hardcodees rutas de interprete: cambian
   por host, SO y perfil.

## Que reportar

Del output de `estado.py`, al usuario le importan tres cosas y en este orden:

1. **Si hay una feature `in_progress`, retomala.** No arranques otra. Di cual es
   y en que paso del flujo quedo (spec / evidencia / review / cierre).
2. **Gates pendientes.** Cual es el proximo gate que toca correr y con que
   comando exacto.
3. **Edad del contexto.** Si `estado.py` dice que el grafo o el brief estan
   vencidos, avisa y ofrece refrescarlo. Un contexto viejo miente, y nadie lo
   refresca solo:

   ```bash
   eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/contexto.py" refrescar
   ```

   Si lo unico viejo es el vault (`vault: desactualizado` con el contexto
   fresco), no relances graphify ni el hub; basta regenerarlo. El vault es el
   panel de Obsidian del usuario; ningun rol lo lee.

   ```bash
   eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/vault.py" build
   ```

## Contraste obligatorio

No reportes el resumen de `estado.py` como si fuera el conteo. Contrastalo contra
un conteo programatico del backlog antes de afirmar cuantas features hay en cada
estado:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" -c "
import json,collections,pathlib
b=json.loads(pathlib.Path('harness/feature_list.json').read_text())
print(collections.Counter(f.get('status') for f in b.get('features',[])))"
```

Si los dos numeros no coinciden, el desacuerdo es el hallazgo: reportalo en vez
de elegir el que te guste mas.
