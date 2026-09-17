---
description: Arranque de sesion de harness-flow — features abiertas, gates pendientes y edad del grafo, contrastado contra el backlog.
---

# harness-flow: estado

Arranque de sesion en un proyecto con `harness/feature_list.json`. Corre esto
ANTES de responder nada sustantivo sobre el proyecto.

## Preflight

1. Comprueba que existe `harness/feature_list.json` desde el directorio actual
   hacia arriba. Si no existe, este proyecto no tiene arnes instalado: dilo y
   detente — no lo inicialices sin que el usuario lo pida.
2. Resuelve el entorno. **En Claude Code cada llamada Bash abre un shell nuevo:
   `$PY` y `$H` no sobreviven entre llamadas**, asi que el `eval` va pegado al
   comando en la MISMA llamada, siempre:

   ```bash
   eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/estado.py"
   ```

   Si `entorno.py` sale con exit≠0, corre `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py"`
   a secas para ver el diagnostico y arregla con `--instalar-deps`. No hardcodees
   rutas de interprete.

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
