# Plantilla de spec

`add.py` copia el bloque de abajo a `docs/spec-feature-<id>-<slug>.md` y rellena
los `{{...}}` con los datos de la feature. El `Estado:` arranca en `draft` y SOLO
lo cambia `gate.py approve-spec --yes` tras el sí del usuario.

```markdown
# Spec - Feature #{{ID}}: {{NAME}}

Estado: draft

## Contexto

Qué problema resuelve y por qué ahora.

PRD: `{{PRD}}` · candidata: {{CANDIDATA}} · cumple: <O-n del PRD, o ninguno>
SDD: `docs/sdd.md` · decisiones que aplica: <D-n del SDD, o ninguna>

## Criterios de aceptacion

Cada AC es verificable por un tercero. Given/When/Then.

- AC-1: dado <estado>, cuando <accion>, entonces <resultado observable>. `verificar: pytest tests/test_x.py -q`
- AC-2: dado <estado>, cuando <accion>, entonces <resultado observable>.
  Comando: `npm test -- checkout`
- AC-3: <sin comando: lo verifica el reviewer a mano>

## Fuera de alcance

Lo que esta feature NO hace, para que el reviewer no lo exija. Los no-objetivos
(NO-n) del PRD que la rozan van aqui.

## Riesgos

Qué se puede romper. Cruzalo con `hub.py impacto`.
```

## Reglas del formato

- Los AC se numeran `AC-1`, `AC-2`, ... sin saltos. `gate.py` los extrae con
  `^[^\S\n]*[-*]?[^\S\n]*(AC-\d+)[^\S\n]*(?:\((?:[^()\n]|\([^()\n]*\))*\))?[^\S\n]*:`:
  el id admite un título corto entre paréntesis, con un nivel de anidamiento,
  y todo tiene que caber en UNA línea (`- AC-1 (cola por estado): ...`). Ese mismo parser alimenta
  el PRD, el brief y el briefing del revisor. (La evidencia y el review usan
  además `declara_ac`, que reconoce la *sección* de un AC — `## AC-1`, una fila
  de tabla — no su declaración en el spec.)
- El comando de verificacion admite dos formas: dentro del backtick
  (`` `verificar: <cmd>` ``) o fuera (`Comando: `` `<cmd>` ``). Las dos se parsean.
- Un AC sin comando es legitimo: lo verifica el reviewer a mano y queda en su acta.
- El Contexto cita lo que la feature cumple del PRD (`cumple: O1`) y las
  decisiones del SDD que aplica (`decisiones que aplica: D2`). `approve-spec`
  avisa si no cita ninguno de los que el documento declara, o si cita uno que no
  existe; `cumple: ninguno` / `decisiones que aplica: ninguna` lo dicen a
  proposito. Es un aviso: que la cita sea la correcta lo decide el usuario.
- Cambiar el spec despues de aprobarlo INVALIDA el sello (firma sha256 del cuerpo).
  Hay que volver a mostrarlo y re-aprobarlo. Esto es deliberado.
- Si ya hay evidencia, review o verify, no se re-aprueba: se enmienda con
  `gate.py enmienda` y una propuesta (`templates/enmienda.md`). La seccion
  `## Enmiendas posteriores a la aprobacion` la escribe ese comando.
