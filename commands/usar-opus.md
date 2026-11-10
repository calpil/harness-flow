---
description: Fija Claude Opus 5.5 con esfuerzo xhigh para el resto del turno. Lo invocan los roles producto y spec cuando el usuario eligio ese modelo.
model: claude-opus-5-5
effort: xhigh
---

# harness-flow: usar Claude Opus 5.5

Desde este punto, y hasta que termine este turno, corres en **Claude Opus 5.5** con
esfuerzo **xhigh**. El usuario lo eligio para este rol; no hace falta que
escriba `/model` ni `/effort`.

Compruebalo: tu system prompt dice en que modelo corres. Si sigue siendo otro,
este comando no se aplico (pasa en sesiones sin interfaz, `claude -p`): dilo y
sigue la regla del rol para ese caso.

Este comando no hace nada mas. Continua el rol que estabas ejecutando
(`/harness-flow:producto` o `/harness-flow:spec`) desde el paso siguiente al
de la eleccion de modelo, con las instrucciones que ya tienes cargadas. No
vuelvas a preguntar el modelo ni a invocar este comando en el mismo turno.

El modelo vuelve al de la sesion cuando el usuario envia su siguiente mensaje.
Si en ese turno el rol sigue redactando o disenando, invoca este comando otra
vez al empezar; para un paso mecanico (sellar con el gate) no hace falta.
