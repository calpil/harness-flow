# Plantillas de evidencia y review

## Evidencia — `docs/impl-<id>.md`

La escribe el implementer. Un AC se considera cubierto si su seccion contiene una
cita `archivo:linea`.

```markdown
# Evidencia - Feature #<id>

## AC-1
Qué se hizo y donde: `poc-ui/src/checkout.ts:42`.
Como se comprobo: salida de `pytest -q` en verde.

## AC-2
`ms-orders-service/internal/order.go:77`.

## Reproduccion (obligatorio si la feature es --kind bug)
<!-- Comando, paso de Feature Map o traza con la que el agente reprodujo el fallo en ROJO antes del fix y lo confirmo en VERDE despues. -->
Reproducido antes del fix con `npx playwright test e2e/checkout.spec.ts` (fallo HTTP 500 en `poc-ui/src/checkout.ts:42`); tras el fix pasa en verde.
```

Tambien vale la forma compacta, con la cita en la misma linea:

```markdown
- AC-1: descuento aplicado en `poc-ui/src/checkout.ts:42`
```

Lo que NO cuenta: "lo implemente y funciona" sin `archivo:linea`. El gate lo rechaza.

## Review — `docs/review-<id>.md`

La escribe el reviewer. Necesita una fila por CADA AC del spec, nombrandolo y
citando. Si falta uno, `gate.py revision` se niega a sellar.

```markdown
# Review - Feature #<id>

| AC | Veredicto | Cita |
|----|-----------|------|
| AC-1 | ok | poc-ui/src/checkout.ts:42 |
| AC-2 | ok | poc-ui/src/checkout.ts:58 |
| AC-3 | ok | ms-orders-service/internal/order.go:77 |

## Observaciones

Deuda tecnica o riesgos que no bloquean el cierre.
```

El sello `Revisado: <veredicto> · <quien> · <cuando> · estampado por gate.py revision` lo estampa el script.
Escribirlo a mano no cuenta: el gate valida el sello, no la prosa.
