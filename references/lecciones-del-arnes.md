# Lecciones del arnes sobre si mismo

Leelas antes de tocar un gate o de escribir uno nuevo: cada una nacio de un
falso verde que ya paso en este repo. Salieron de auditar sus propios
gates y todas tienen repro verificada.

- **Un gate que deduce el veredicto de un regex sobre texto no es un gate.** El
  `postmerge.py` viejo parseaba `--- FAIL:` de la salida `-v` y nunca leía el
  exit code: daba verde con build roto, con `panic` en `init()` y con tests
  borrados. Si un runner puede fallar sin imprimir la línea que buscás, medí el
  exit code y el inventario, no el texto.
- **Cuando existan dos versiones de un gate, la doc tiene que mandar a la buena.**
  Este SKILL.md documentaba el roto mientras `medicion_destino.py` usaba el
  medido: quien seguía la doc al pie de la letra usaba el que miente.
- **Un identificador de test sin su paquete colapsa tests distintos.** Identificá
  por `(paquete, test)`, o un rojo nuevo se confunde con deuda tolerada de otro.
- **Contar sólo los rojos nuevos deja pasar los tests que desaparecen.** Sin
  inventario de lo medido antes, borrar un test es indistinguible de arreglarlo.
- **Un conteo parcial nunca se reporta como total.** `verify` medía sólo los AC
  con comando y anunciaba `1/1 en verde` con 3 AC en el spec. Si mediste 3 de 12,
  decilo en la misma línea del verde.
- **Una medición vale para la firma con la que se tomó.** Si el spec cambia
  después del `verify`, el verde viejo habla de otro documento: re-medir.
  Contar AC no es comparar firmas: reescribir un AC ("no cobra dos veces" ->
  "cobra dos veces") y re-aprobar con `approve-spec` dejaba cerrar con el review
  y el verify del texto anterior, porque `close` solo miraba cuántos AC había.
  Por eso un spec con trabajo encima ya no se re-aprueba: se enmienda.
- **Un sello contra falsificación debe exigir la firma entera.** Un
  `Revisado: approved - ok` tipeado a mano pasaba como sellado por el gate.
- **Una mención no es una declaración.** Al parsear documentos por secciones, una
  frase que nombra `AC-1` de pasada abría sección y heredaba la cita del AC
  vecino: daba por cubierto un AC sin evidencia y truncaba el que sí la tenía.
- **`exists()` no es `is_file()`**, y un glob de un solo nivel no ve las skills
  anidadas (`mlops/inference/llama-cpp`): el gate de lección bloqueaba cierres
  legítimos y aceptaba un directorio llamado `SKILL.md`.
- **Un valor del backlog que termina en una ruta necesita `slugify` + chequeo de
  contención.** Una lección `../../../README` pisaba archivos del repo.
- **En un cliente HTTP, el fallo de red debe tratarse como fallo en TODAS las
  ramas.** `code == 0` faltaba sólo en la creación de issue: persistía
  `jira_key: null` y el reintento duplicaba la issue en Jira.

