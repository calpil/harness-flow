# Plantilla de enmienda

Copia esto a `docs/propuesta-<id>-enmienda-<slug>.md` cuando haya que cambiar un
spec que ya tiene evidencia, review o verify encima. El `Estado:` arranca en
`draft` y SOLO lo cambia `gate.py enmienda --yes` tras el sí del usuario.

```markdown
# Enmienda - Feature #<id>: <que cambia, en una linea>

Estado: draft
Origen: <decision del usuario, hallazgo del review (R-n) o bloqueo>, con fecha.

## Por que

<!-- Que se supo despues de aprobar el spec que obliga a cambiarlo. -->

## Cambios al spec

<!-- Cada AC que cambia, se agrega o se retira, con su texto nuevo ENTERO
     (comando incluido). Si cambia texto fuera de los AC (fuera de alcance,
     riesgos), tambien. Esto es lo que el usuario aprueba. -->

## Lo que NO cambia

<!-- Los AC y comandos que siguen igual, y lo que la enmienda NO dispensa. -->
```

## Reglas

- La propuesta nombra CADA AC que el spec cambió, agregó o retiró.
  `gate.py enmienda` compara el spec contra la huella por AC del último sello y
  se niega si cambió un AC que la propuesta no nombra: el usuario aprueba la
  propuesta, no el diff. Las guías `<!-- -->` no cuentan como mención.
- Las tres secciones son obligatorias y no pueden quedar solo con la guía. Se
  aceptan variantes del encabezado (`## Cambio al spec`, `## Por qué`). Puedes
  agregar otras, por ejemplo lo que pasa a otra feature.
- Los cambios se aplican al spec ANTES de sellar. La sección `## Enmiendas
  posteriores a la aprobacion` del spec no se toca a mano: el gate agrega ahí
  `### E-n`, con quién, cuándo, la propuesta y los AC tocados.
- Una propuesta sella una sola enmienda. Si después cambia algo más, escribe
  otra propuesta.
- Sellar la enmienda deja sin valor para `close` el review y el verify
  anteriores: hay que lanzar un review nuevo (re-sellar el mismo archivo se
  niega) y volver a correr `verify`.
