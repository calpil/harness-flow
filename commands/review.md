---
description: Rol reviewer de harness-flow — lanza el subagente revisor aislado sobre una feature y sella su veredicto con el gate.
argument-hint: <id-feature>
---

# harness-flow: review (rol reviewer)

Review de la feature `$1`. **El review no lo haces tu.** Un revisor que recuerda
haber escrito el codigo se aprueba solo; uno que solo ve spec + diff, no.

## 1. Arma el briefing

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/revision.py" --feature $1 --briefing
```

Esa salida es el paquete completo: rol, arbol a revisar, AC, formato del acta,
reglas de veredicto y diff. No la resumas ni la parafrasees.

## 2. Lanza el revisor aislado

Usa la tool `Agent` con `subagent_type: "harness-flow:revisor"`, pegando la
salida ENTERA del paso 1 en el prompt, y arriba una linea de goal:

> Revisa la feature #$1 y escribe `docs/review-$1.md`.

Reglas de esta delegacion:

- **No uses un fork de la sesion.** Un fork hereda tu historial, y con el, el
  sesgo que el aislamiento existe para evitar. `subagent_type: "fork"` aqui
  anula el punto del paso.
- No le cuentes al revisor lo que implementaste ni le adelantes que esperas que
  apruebe. Lee el codigo solo.
- Si no puedes lanzar un subagente, revisa tu mismo con el paquete de solo
  lectura y **dilo explicitamente en el chat**: el rigor baja y el usuario
  tiene que saberlo.

  ```bash
  eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/revision.py" --feature $1
  ```

## 3. Lee el acta tu mismo

Cuando vuelva, abre `docs/review-$1.md`. El veredicto del subagente es un
autoinforme, igual que la evidencia del implementer. Antes de sellar:

- cada fila cita un `archivo:linea` que **existe** y dice lo que la fila afirma;
- las citas salen del arbol de la feature, no de la raiz parada en integracion;
- hay una fila por CADA AC del spec, sin AC mudos.

Si una fila no aguanta, no selles: devuelve el hallazgo.

## 4. Sella

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" revision --feature $1 --veredicto approved|changes_requested|blocked
```

El script estampa la firma completa (veredicto · fecha ISO · autor · `estampado
por gate.py revision`). Un `Revisado: approved - ok` tipeado a mano NO cuenta, y
el gate de cierre lo rechaza.
