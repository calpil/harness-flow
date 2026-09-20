# PRD - {{PROYECTO}}

Estado: draft
Dueño: {{DUENO}}
Creado: {{FECHA}}
Alcance: <!-- una linea: que toca y que NO toca. "Llamada de voz al cerrar la venta; NO toca correos ni recordatorios" -->

<!-- Borrador del rol producto. Vive en docs/borrador-prd.md, que NO es ruta
     protegida; docs/prd/PRD-master.md solo lo escribe `producto.py aprobar
     --yes` tras el SI del usuario. Las guias en comentarios HTML como este se
     reemplazan por contenido o se borran: una seccion que solo tiene guia
     cuenta como vacia y la aprobacion se niega.

     Un PRD cuenta una historia y raya la cancha de lo que hay que construir.
     Contiene: la historia (antes y despues), hoy -> manana, las tablas y
     entidades a tocar, pseudo-codigo y la explicacion de los cambios.
     NUNCA contiene: codigo final, la implementacion exacta, pantallas
     terminadas ni configuracion. Eso se escribe despues, en el spec y en el
     codigo; un bloque ```go, ```sql o ```ts aqui hace que la aprobacion se
     niegue. Si el razonamiento esta bien en papel, el codigo es la parte
     facil; si esta mal, ningun codigo lo arregla.

     El tamano lo decide el cambio: un ajuste cabe en una pagina, una
     funcionalidad en 3-8, una grande en 10 o mas, y un producto nuevo son
     varios PRDs anidados que cuentan cada uno su propia historia. Aqui cada
     "Feature candidata" es uno de esos PRDs anidados: entra al backlog y su
     spec, con AC, cuenta la suya. Las secciones van en este orden. -->

## Resumen

<!-- El antes y el despues en dos lineas: el dibujo mas barato que existe.
       Hoy: se cierra una venta y no pasa nada. Alguien tiene que acordarse.
       Despues: al marcar la venta cerrada, se agenda una llamada que agradece. -->

Hoy:
Despues:

## La historia

<!-- El corazon del documento. Contala en palabras, sin tecnicismos, con
     nombre y momento: quien es el usuario, como lo usa, cual es el dolor y
     que experiencia quiere vivir. Si la historia no convence, el resto no
     importa.
       Asi NO: "escuchar el cambio de estado, agendar una tarea de llamada".
       Asi SI: "Marta cerro su compra un viernes a las 6 de la tarde. Nadie la
       llamo. El lunes le llego la misma plantilla de siempre, y esa confianza
       recien ganada se enfrio justo cuando mas cerca estaba de recomendarnos." -->

Antes:
Despues:

## Objetivos y no-objetivos

<!-- Con nombre y apellido, para que las secciones siguientes los citen
     ("cumple O2"). Los no-objetivos frenan el "ya que estamos".
       - O1: toda venta cerrada recibe su llamada en menos de 5 segundos
       - O2: reversible: interruptor por cliente, se apaga en 1 clic
       - NO1: no vende ni reagenda nada, solo agradece -->

## Como funciona hoy y como va a funcionar

<!-- El flujo, dibujado dos veces. Reusa lo que ya existe: el cambio de
     estado, las colas, el pipeline.
       Hoy:     venta cerrada -> (nada)
       Despues: venta cerrada -> agenda la llamada
                                 -> el agente agradece
                                 -> el pipeline guarda el resultado -->

## Los datos

<!-- El plano de los datos: que dispara el cambio, que entidades o tablas se
     tocan y como cambian, el interruptor por cliente y el candado que evita
     hacerlo dos veces.
       disparador    el lead pasa al estado "venta cerrada"
       por cliente   llamada_gracias: apagado | prueba | activo   <- interruptor
       por lead      agradecido_en: fecha                          <- candado -->

## Pseudo-codigo: el acuerdo

<!-- La receta en palabras: que lo dispara, que lo frena y que promete. Sin
     una sola linea de codigo.
       CUANDO se cierra una venta
         el cliente activo "las gracias"?      -> si no, no hacemos nada
         ya lo llamamos por esta venta?         -> si si, no hacemos nada
         tenemos su numero?                     -> si no, no hacemos nada
       ENTONCES lo llamamos en 5 segundos, con un guion que agradece,
                solo en horario habil
       Promesas: una sola llamada por venta; nunca fuera de horario;
                 si no contesta, no insiste. -->

## Features candidatas

<!-- Los PRDs anidados de este producto: una por linea, en orden de
     prioridad, con el formato exacto
       - F-1: <nombre>: <resultado observable para el usuario> (cumple O1)
     Cada una entra al backlog con
       add.py --name "<nombre>" --prd docs/prd/PRD-master.md
     y recibe su spec con AC en el rol leader. -->
