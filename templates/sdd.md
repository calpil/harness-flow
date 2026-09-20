# SDD - {{PROYECTO}}

Estado: draft

<!-- Borrador del rol producto (diseno de arquitectura). Vive en
     docs/borrador-sdd.md; docs/sdd.md solo lo escribe `producto.py aprobar
     --yes` tras el SI del usuario. Las guias en comentarios HTML como este se
     reemplazan por contenido o se borran: una seccion que solo tiene guia cuenta como vacia
     y la aprobacion se niega. El bloque generado por feature lo agrega
     documentacion.py sync al cerrar cada una; no lo escribas aqui. -->

## Contexto

<!-- Que sistema existe hoy y que restricciones hereda: stack, repos,
     datos, despliegue. Cruzalo con `contexto.py estado` y `hub.py impacto`
     en vez de suponerlo. -->

## Componentes

<!-- Microservicios / repos con la responsabilidad de cada uno, sus
     fronteras y los contratos entre ellos (API, eventos, tablas). El flujo,
     los datos y el pseudo-codigo de cada cambio ya estan en el PRD: aqui va
     lo que el PRD no fija, la arquitectura que los sostiene. -->

## Datos e integraciones

<!-- Esquemas, migraciones, colas y sistemas externos. Si hay migraciones
     numeradas, decir aqui contra que rama se reserva el numero. -->

## Decisiones

<!-- Cada decision con la alternativa descartada y el porque. Una decision
     sin alternativa no es una decision, es una descripcion. -->

## Riesgos

<!-- Que puede romperse, como se detecta y que lo mitiga. -->
