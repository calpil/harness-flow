# Plantilla de spec

Copia esto a `docs/spec-feature-<id>-<slug>.md`. El `Estado:` arranca en `draft`
y SOLO lo cambia `gate.py approve-spec --yes` tras el sí del usuario.

```markdown
# Spec - Feature #<id>: <nombre>

Estado: draft

## Contexto

Qué problema resuelve y por qué ahora. Enlaza el PRD si existe.

## Criterios de aceptacion

Cada AC es verificable por un tercero. Given/When/Then.

- AC-1: dado <estado>, cuando <accion>, entonces <resultado observable>. `verificar: pytest tests/test_x.py -q`
- AC-2: dado <estado>, cuando <accion>, entonces <resultado observable>.
  Comando: `npm test -- checkout`
- AC-3: <sin comando: lo verifica el reviewer a mano>

## Fuera de alcance

Lo que esta feature NO hace, para que el reviewer no lo exija.

## Riesgos

Qué se puede romper. Cruzalo con `hub.py impacto`.
```

## Reglas del formato

- Los AC se numeran `AC-1`, `AC-2`, ... sin saltos. `gate.py` los extrae con
  `^\s*[-*]?\s*(AC-\d+)\s*:`.
- El comando de verificacion admite dos formas: dentro del backtick
  (`` `verificar: <cmd>` ``) o fuera (`Comando: `` `<cmd>` ``). Las dos se parsean.
- Un AC sin comando es legitimo: lo verifica el reviewer a mano y queda en su acta.
- Cambiar el spec despues de aprobarlo INVALIDA el sello (firma sha1 del cuerpo).
  Hay que volver a mostrarlo y re-aprobarlo. Esto es deliberado.
