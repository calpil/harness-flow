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

Cada AC es verificable por un tercero en Given/When/Then y declara su costura
publica de prueba (`[costura: endpoint|servicio|ui|integracion|manual]`).
Apunta a 2-5 AC por vertical slice; si necesita mas de 5, considera dividir la
feature en slices verticales mas chicos antes de aprobar.

- AC-1 [costura: endpoint]: dado <estado>, cuando <accion>, entonces <resultado observable>. `verificar: pytest tests/test_x.py -q`
- AC-2 [costura: servicio]: dado <estado>, cuando <accion>, entonces <resultado observable>.
  Comando: `npm test -- checkout`
- AC-3 [costura: manual]: <sin comando: lo verifica el reviewer a mano>

## Plan vertical

Maximo 5 pasos cortos (sin codigo ni nombres de archivos) que atraviesan las capas
(datos, backend, UI/contrato) con lo mas simple que cumpla los AC (YAGNI: sin
capas ni patrones "por si acaso"):

- Paso 1: <costura y caso principal de punta a punta>
- Paso 2: <persistencia o regla de dominio minima requerida>
- Paso 3: <integracion o validacion de borde observable>

## Fuera de alcance

Lo que esta feature NO hace, para que el reviewer no lo exija. Los no-objetivos
(NO-n) del PRD que la rozan van aqui.

## Sugerencias (decision del usuario)

Opcional ("sugiere, no decidas"): patrones o extracciones con su por que, SOLO si
hay una senal concreta en el codigo actual (por ejemplo, algo que ya se repite),
nunca por adelantado.

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
- **Vertical Slice y costuras (seams)**: cada AC declara donde se prueba usando la
  interfaz publica mas alta practica (`[costura: endpoint]`, `[costura: servicio]`,
  `[costura: ui]`, `[costura: integracion]`, `[costura: manual]`, o una linea
  `Costura: <seam>` debajo del AC). Nunca acoplado a detalles internos ni mocks
  de privados. Si el spec supera `rules.max_acs_por_slice` (por defecto 5 AC) o
  el `## Plan vertical` supera 5 pasos, `approve-spec` y `check` emiten `[!]`
  sugiriendo dividir en slices mas chicos.
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
