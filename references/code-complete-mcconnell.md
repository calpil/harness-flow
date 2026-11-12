# Code Complete (Steve McConnell) en Harness Flow

Guía operativa de *Code Complete, Second Edition* (Microsoft Press, 2004) aplicada a los roles del arnés. Resume criterios y los traduce a fases. No reproduce el libro.

**Lectura:** Cerrada. Partes I a VII (capítulos 1 a 35) están en este archivo.

Otras referencias siguen dueñas de su tema. Este archivo no las reescribe.

| Tema | Dueño | Qué aporta McConnell aquí |
| --- | --- | --- |
| Módulos, complejidad, design it twice | [`filosofia-diseno-ousterhout.md`](filosofia-diseno-ousterhout.md) | El SDD debe dejar evidencia de alternativas. El formato `D-n` / `Descartada:` no cambia. El largo de la rutina, la clase omnisciente y el tope de McCabe quedan en conflicto: manda el módulo profundo. |
| Design docs, no-objetivos, entrega de 1 a 3 días | [`ingenieria-software-gergely-orosz.md`](ingenieria-software-gergely-orosz.md) | El presupuesto de prerrequisitos y el costo de cambiar un requisito tarde. El diseño de la clase y de la rutina cabe en la feature, sin un segundo documento. |
| Datos, outbox, OCC, expand-contract | [`patrones-datos-ddia.md`](patrones-datos-ddia.md) | Nada sobre outbox, OCC ni expand-contract. El dinero y el folio se guardan en un tipo exacto. El almacén sigue siendo el subsistema que esconde el acceso. |
| Fronteras de servicio | [`microservicios-sam-newman.md`](microservicios-sam-newman.md) | Programar *hacia* el lenguaje cuando el framework empuja a mezclar capas. La barricada del capítulo 8 es el puerto del stack. |
| Patrones y dos sombreros | [`patrones-gof-y-refactoring.md`](patrones-gof-y-refactoring.md) | El patrón es vocabulario compartido. No se fuerza ni se inventa en el sombrero de feature. Una tabla de búsqueda puede ser más simple que una jerarquía. El catálogo de olores del capítulo 24 no se copia: sigue en Fowler. |
| Costuras, `F-n`, TDD, pair | [`vertical-slice.md`](vertical-slice.md) | La acreción incremental. El esqueleto del arnés sigue sin mocks. El pseudocódigo no reemplaza el test de la costura. El test-first del capítulo 22 refuerza el ciclo. La cobertura de cada rama privada no lo sustituye. La integración por feature y la rebanada en T del capítulo 29 son `F-n` y `F-1`. |

Cargar esta referencia en el rol 0 (PRD, SDD, candidatas), al sellar un spec si el terreno no está listo, en el implementer al diseñar, comentar y depurar, en el revisor al leer el diff, y al cerrar. El formateador del stack manda la sangría y las llaves. El comentario dice el porqué. La estrategia de errores (corrección vs robustez) y la barricada defensiva quedan fijadas en la plantilla `templates/sdd.md` y en el criterio de revisión del diff.

---

## Capítulo 1 — La construcción es el centro

Construcción es diseño detallado, codificación, depuración, integración y pruebas del propio desarrollador (unitarias y de integración). Fuera de ese círculo quedan la definición del problema, los requisitos, la arquitectura, la prueba de sistema independiente y el mantenimiento correctivo.

McConnell mide la construcción en el 30 % al 80 % del tiempo del proyecto, según el tamaño. Es la única actividad que ningún proyecto logra saltarse. El código suele ser la única descripción que no se desactualiza. Llamarla "coding" es engañoso: no es traducir un diseño ya cerrado.

| Actividad | Fase del arnés |
| --- | --- |
| Problema y requisitos | Rol 0, PRD |
| Arquitectura | Rol 0, SDD |
| Plan de construcción | Candidatas `F-n` y `## Plan vertical` del spec |
| Terreno listo antes de codificar | `gate.py check-spec` |
| Cómo se prueba | Costura pública de cada AC |
| Diseño detallado de rutinas | Capítulo 9, como guía. El implementer piensa la rutina antes del primer test de la costura. El ciclo sigue en Red-Green. |
| Codificación y prueba unitaria | Implementer, TDD vertical |
| Depuración | Capítulo 23, como guía. Estabilizar, una hipótesis, un experimento, la causa, el arreglo, el mismo defecto al lado. La parada a los dos intentos sin verde sigue. El depurador no es evidencia. |
| Revisión de diseño bajo y de código | Sí del usuario al spec, y después el revisor aislado sobre el diff |
| Integración | `close`, `--integrated`, `postmerge_medido.py` |
| Prueba de sistema independiente | Fuera del arnés |
| Mantenimiento | `--kind bug\|task`, enmienda, `leccion.py` |

`--kind bug|task` no exige PRD ni SDD. La construcción igual ocurre, y las reglas activas de spec, review, verify y lección siguen valiendo.

La calidad se decide durante la construcción. No se agrega otro gate después del revisor para "poner calidad al final".

---

## Capítulo 2 — Metáforas

Las metáforas son heurísticas. Iluminan el proceso. No son un algoritmo que una línea de código pueda violar. Se combinan. Ninguna metodología ocupa el 100 % de la caja de herramientas: Ousterhout, Orosz, DDIA, GoF, Newman y esta guía se eligen según el problema.

### Escribir

La metáfora de la carta (sentarse y redactar de principio a fin, originalidad, documento terminado al enviarlo) describe mal un sistema. Pigoski (1997) sitúa hasta el 90 % del esfuerzo después del primer release, con dos tercios como cifra típica. Reusar diseño, código y tests pesa más que la originalidad.

Brooks escribió "planea tirar uno; lo harás de todos modos". McConnell lo trata como mal consejo al extenderlo a un sistema grande. Zerouni responde que quien planea tirar uno tira dos. Brooks, años después, señaló el desarrollo incremental como el cambio que más mejoró su práctica.

En el arnés, `F-1` es un walking skeleton real. No es un prototipo para descartar.

### Cultivar

Hacer un poco cada vez es una buena técnica con una mala metáfora. Cultivar sugiere que el sistema sale si se planta y se espera. Las decisiones `D-n` se eligen. No "crecen".

### Acreción

La ostra agrega capas sobre un grano. El sistema crece por fuera, de a poco: incremental, iterativo, adaptativo. Primero un esqueleto que corre. Después se reemplaza cada función fingida por la real.

McConnell acepta clases dummy como grano de arena. El arnés no: `F-1` conecta UI o API, lógica, datos y tests sin mocks. Un dummy que nadie reemplaza deja la costura sin medir. La acreción que sí se adopta es una rebanada real por candidata, con `requiere:` solo cuando una historia no existe sin la otra.

### Construir

La metáfora que McConnell recomienda. El tamaño cambia el tipo de preparación, no solo la cantidad.

| Obra | Software | En el arnés |
| --- | --- | --- |
| Caseta (un error cuesta una tarde) | Un diseño malo en unas mil líneas se rehace | `--kind bug\|task`. PRD y SDD no se exigen. |
| Casa (mover un muro de carga es caro) | Problema, arquitectura y plano antes de construir. El acabado se decide después. | PRD con historia y `O-n` / `NO-n`. SDD con las decisiones caras. Cada `F-n` es una habitación, no otro rascacielos. |
| Rascacielos o reactor | Jones (1998): un sistema de un millón de líneas promedia 69 clases de documentos; el spec de requisitos ronda 4.000 a 5.000 páginas y el diseño lo duplica o triplica. | Ese volumen es del sistema entero, repartido en PRD maestro, SDD y specs. Un spec de feature sigue en 2 o 3 AC. |

Comprar lo ya construido (librerías, lenguaje de alto nivel) antes de fabricarlo. Lo hecho a medida se reserva para lo que el producto necesita distinto. Una pared de carga (decisión `D-n`, esquema, contrato público) cuesta más de mover que un tabique (un AC periférico).

La caja de herramientas cierra el capítulo: el artesano elige la herramienta. Un solo método para todo el mundo hace perder las demás.

---

## Capítulo 3 — Medir dos veces

El objetivo de la preparación es bajar el riesgo. Preparar de más también lo sube.

### Costo de llegar tarde al defecto

En proyectos grandes, un defecto de requisitos cuesta unas 3 veces más si se ve en arquitectura, de 5 a 10 veces si se ve al codificar, unas 10 en prueba de sistema y de 10 a 100 después del release, comparado con corregirlo en requisitos. En proyectos chicos el factor post-release baja a 5–10 (Boehm y Turner 2004). Un defecto de arquitectura de 1.000 durante la arquitectura cuesta unos 15.000 en prueba de sistema y de 25 a 100 veces más después del release. Un defecto de construcción cuesta unas 10 veces más en prueba de sistema.

El retrabajo y la depuración se llevan cerca de la mitad del ciclo en un proyecto típico. Corregir más cerca de la inserción ha recortado costo y calendario por factores de dos o más en mediciones que McConnell recoge.

Eso justifica el ritual de rol 0 y el sello de `approve-spec` contra la versión del PRD y del SDD. También justifica la enmienda: un AC que cambia con trabajo encima invalida review y verify, porque el defecto de especificación ya no se "arregla en el diff".

La iteración abarata el daño de saltarse prerrequisitos. No lo elimina. En las tablas ilustrativas del capítulo, un secuencial sin preparación termina más caro que uno iterativo sin preparación, y ambos salen más caros que cualquiera de los dos con preparación. Un walking skeleton no autoriza a saltarse el problema, los objetivos y las decisiones caras.

### Qué clase de software es esta feature

La clase se juzga por la feature, no por la empresa. Un portal puede tener una feature de negocio y otra que mueve dinero o datos personales.

| Clase (McConnell) | Ejemplos del libro | Cómo se construye | En el arnés |
| --- | --- | --- | --- |
| Sistemas de negocio | Sitio, intranet, inventario, nómina, MIS | Iterativo. Requisitos informales. Diseño y codificación juntos en el detalle. Test-first. Control de cambio informal. | Default CALPIL. PRD en historia de usuario. Pair automático en stack normativo. `close` a la rama de integración. |
| Misión crítica | Empaquetado, herramientas, web services, cierto embebido | Requisitos semiformales. Arquitectura explícita. Control de cambio formal. Prueba aparte del autor. | Multi-repo, folio, pago, datos personales. `D-n` con alternativa descartada. Enmienda. Revisor aislado. Postmerge medido. |
| Vida crítica | Aviónica, dispositivo médico, sistema operativo | Secuencial. Requisitos e inspecciones formales. QA separada. | Fuera de alcance. Los gates no son un caso de seguridad ni una certificación. Si una feature es de este tipo, se para y se pregunta. |

Regla del 80/20 que el libro ofrece, y la variante inversa: especificar cerca del 80 % de los requisitos al inicio y controlar el resto, o especificar el 20 % crítico y construir el resto en incrementos. El arnés usa la segunda en el cuerpo y la primera en el control del cambio. El PRD fija el problema, la historia, `O-n` / `NO-n` y el acuerdo. Cada `F-n` precisa el incremento. Un requisito nuevo pasa por producto o por enmienda, con el sí del usuario.

Los estudios que cita (Boehm, Jones) sitúan el cambio de requisitos durante el desarrollo cerca del 25 %, y ese cambio explica del 70 % al 85 % del retrabajo. Por eso un "ya que estamos" a mitad de feature no entra al código: se nombra el costo y se decide si es otra candidata.

### Definición del problema

Una definición de problema dice el problema y no nombra la solución. En lenguaje del usuario. Una o dos páginas bastan como prueba de que existe. "No damos abasto con los pedidos del Gigatron" es un problema. "Hay que optimizar el sistema de carga para dar abasto" ya es una solución.

El PRD cumple esto con la historia antes/después, con nombre y momento, y con los no-objetivos. El pseudo-código del acuerdo describe el comportamiento observable. Un bloque de código final en el PRD se rechaza por el gate, y también falla esta prueba: el requisito no debe fijar el diseño.

Sin esa definición se construye el problema equivocado. El doble costo es no haber construido el correcto.

### Requisitos

Los requisitos explícitos los conduce quien usa el sistema. Sin ellos, quien programa los inventa durante la construcción. También cortan la discusión de alcance: el desacuerdo se resuelve leyendo el escrito.

Lista de sanidad, traducida al PRD y al spec. En un bug no hace falta recorrerla entera. En una feature de negocio, las que apliquen se responden en el borrador o se preguntan, una a la vez.

* Entradas, salidas y formatos que el usuario ve, con origen y destino.
* Interfaces externas y protocolos, si la feature cruza un sistema.
* Tareas del usuario y datos que cada tarea lee y escribe.
* Tiempo de respuesta, seguridad, confiabilidad y qué pasa si falla, cuando el `O-n` lo promete.
* Éxito y fracaso definidos. Cada `O-n` comprobable. Cada AC comprobable en su costura.
* Escritos en lenguaje del usuario. Sin contradicciones. Sin fijar clases, tablas ni frameworks: eso es SDD.
* Cada ítem se traza al problema. Un ítem que no se puede probar no entra como AC.

Cambios durante la construcción, en este orden:

1. Si el requisito es flojo, se para y se corrige el PRD antes de seguir codificando.
2. Un deseo nuevo se costea: otra candidata, otra enmienda, o se deja fuera. La frase "horario y costo" del libro es, en el arnés, "esto no está en `O-n`; hace falta el sí y, si ya hay trabajo, una enmienda".
3. El control del cambio ya existe: `producto.py aprobar` para el cuerpo del PRD o del SDD, y `gate.py enmienda` para un spec con evidencia encima.
4. Los ciclos cortos (`F-n` de una rebanada) son la entrega evolutiva que el capítulo recomienda.
5. Si nada de eso estabiliza el problema, la opción honesta es no abrir la feature.

### Arquitectura

La arquitectura es el marco de alto nivel: restricciones de sistema, no el diseño de cada rutina. Buena arquitectura hace la construcción fácil. Mala arquitectura la vuelve casi imposible. El costo de cambiarla crece con cada línea escrita sobre el marco equivocado.

El SDD del arnés responde estas preguntas cuando aplican. Las cuatro decisiones caras (multi-tenant, permisos, offline, idioma o moneda) se preguntan solo si aplican. El resto sigue en YAGNI.

* Organización y bloques, con responsabilidad e interfaces. Cada objetivo del PRD cae en algún bloque, sin bloques de más.
* Alternativa considerada en cada `D-n`. McConnell pide esa evidencia en la arquitectura. El formato ya es el de Ousterhout y Orosz.
* El 20 % de las clases o puertos que cubren el 80 % del comportamiento. No todas las clases.
* Datos, tablas y la razón de un solo almacén o de uno por servicio. El detalle de outbox, OCC y expand-contract está en DDIA y Newman.
* Reglas de negocio que el sistema debe cumplir, y su efecto.
* UI sustituible sin mover las reglas. Encaja con el puerto de entrada del stack.
* Recursos escasos (conexiones, hilos, ancho de banda) cuando el volumen lo exige. CLRS cubre el orden de magnitud.
* Seguridad, presupuesto de espacio y tiempo, escalabilidad e interoperabilidad, si el problema los nombra.
* Internacionalización, si la cuarta decisión cara aplica.
* Una estrategia de errores coherente para todo el sistema. Queda integrada en `templates/sdd.md` (Componentes): declara si cada subsistema opera bajo corrección o robustez, la barricada en los puertos y el protocolo observable.
* Tolerancia a fallos, solo si el problema la pide.
* Factibilidad técnica. Comprar o construir. Cómo el código reutilizado cumple el resto de la arquitectura.
* Cambios probables anticipados, sin sobrediseñar. Integridad conceptual: pocas piezas añadidas a último momento.
* Motivación de cada decisión mayor. Independencia del lenguaje en el marco. Quien va a implementar lo entiende.
* Riesgos nombrados, con detección y mitigación. La sección `## Riesgos` del SDD es ese lugar.
* Varias vistas. El SDD ya pide un diagrama Mermaid. Una vista que no cabe en el diagrama se dice en una frase.

Ni de menos ni de más. Una parte sobrediseñada y otra ausente es el fallo que el capítulo marca.

### Cuánto tiempo

Un proyecto bien llevado dedica un 10 % a un 20 % del esfuerzo y un 20 % a un 30 % del calendario a problema, requisitos, arquitectura y plan inicial. El diseño detallado no entra en esa cuenta: es construcción.

Ese presupuesto es el rol 0, una vez por producto, no una vez por feature. Si los requisitos no se pueden nombrar, el trabajo de requisitos es su propio paso y el calendario de construcción se estima después. Pedir el costo de la casa antes del plano es el ejemplo del capítulo.

`require_docs_al_dia` mantiene ese presupuesto encendido. Apagarlo es decisión del usuario.

---

## Capítulo 4 — Decisiones de construcción

Con el terreno evaluado, cada proyecto elige prácticas. Hay más prácticas buenas que las que caben en un solo esfuerzo. El arnés ya eligió las suyas. Una feature no reabre el menú salvo que el tipo de software del capítulo 3 lo suba de clase.

### Lenguaje

La familiaridad pesa: Cocomo II estima cerca de un 30 % más de productividad con tres años o más en el lenguaje, frente a alguien nuevo de experiencia equivalente. Un estudio IBM anterior (Walston y Felix, 1977) hablaba de más del triple. Los lenguajes de alto nivel se han acreditado con factores de 5 a 15 frente a ensamblador y C en productividad y calidad (Brooks, Jones, Boehm). La tabla de líneas equivalentes a C (C++ y Java en 2,5, Python y Perl en 6, Visual Basic en 4,5) es de 1998–2000. No se usa para elegir stack en 2026.

El stack lo detecta `stack.py`. No se cambia de lenguaje porque una tabla vieja prometa más líneas por enunciado. Sí se exige conocer las fortalezas del lenguaje del repo y no imitar el lenguaje anterior dentro del nuevo (el Fortran disfrazado de C++ del capítulo).

### Convenciones antes de construir

La integridad conceptual llega hasta el nombre, el comentario y el formato. Sin una disciplina común, la variación arbitraria gasta atención. Las convenciones son casi imposibles de poner después, cuando el código ya está escrito.

`stack.py normalizar` las instala antes de las features de negocio. Si `check-architecture.py` reporta violaciones, la feature 0 bloquea `approve-spec` y `worktree.py start` hasta normalizar. Eso es este capítulo vuelto gate.

### Ola tecnológica

En la parte madura de la ola hay lenguaje, compilador, depurador y documentación. El día se va en funcionalidad. En la parte temprana el día se va en entender la herramienta, rodear defectos de la librería y perseguir releases que rompen código.

Los stacks CALPIL (Go, Angular, .NET, Rust, Next.js, Spring, NestJS, el data product Python) se tratan como ola madura. Context7 y `stack.py auditar` mantienen la API vigente. Una librería nueva, un SDK de modelo o un runtime inestable es ola temprana: se presupuesta tiempo de descubrimiento y se programa *hacia* el lenguaje.

Programar *en* el lenguaje es pensar solo lo que el framework sugiere (lógica de negocio en el componente, en el controller o en el `.frm` del ejemplo Visual Basic). Programar *hacia* el lenguaje es decidir el pensamiento primero y expresarlo con lo que el lenguaje da, inventando la convención que le falta. El ejemplo del capítulo separa UI, reglas y datos aunque Visual Basic empujaba a meterlo todo en el formulario. En el arnés esa convención ya está en los manifiestos de stack. Si el default del framework y la regla del stack discrepan, gana el stack.

### Prácticas mayores, ya elegidas

| Pregunta del capítulo | Respuesta del arnés |
| --- | --- |
| ¿Cuánto diseño antes y cuánto en el teclado? | Arquitectura en el SDD. Diseño de la rutina durante la construcción. El procedimiento es el capítulo 9. |
| ¿Convenciones de nombres, comentarios y layout? | Stack normativo y formateador. El capítulo 31 no abre un debate de estilo en el review. |
| ¿Errores, seguridad, interfaces, reuso, rendimiento? | SDD y skills del stack. El rendimiento se afina solo si un AC lo pide (capítulos 25 y 26). |
| ¿Dónde estás en la ola? | Stack maduro por defecto. Ola temprana se nombra en el SDD cuando la dependencia es nueva. |
| ¿Procedimiento de integración antes del master? | Worktree, `verify` en ese worktree, review, `close`, postmerge medido. |
| ¿Pareja o solo? | Pair por defecto en toda feature, con stack detectado o sin él. Implementer delegado solo si el usuario lo pide (`--delegado`) o la sesión no tiene usuario. |
| ¿Tests antes del código? | Sí. TDD vertical, un test en la costura pública. |
| ¿Tests unitarios aunque no sean primero? | Sí, en la costura. El valor esperado sale del AC. |
| ¿Pasar el depurador antes de integrar? | No es gate. La evidencia es el test. Exclusión consciente. |
| ¿Prueba de integración antes de integrar? | `verify` de los AC con comando, y postmerge en la rama destino. |
| ¿Revisión entre pares? | Revisor aislado, tope de dos rondas. Hallazgos menores no abren ronda. |
| ¿Control de versiones, lenguaje, framework, herramientas? | Git, worktree, stack detectado, test runner del stack. |

---

## Matriz de la Parte I

| Fase | Criterio |
| --- | --- |
| PRD | Suena a problema, en lenguaje de quien lo usa, con antes y después. Los `O-n` se pueden comprobar. Los `NO-n` frenan el alcance. El pseudo-código no es código. Cada candidata es una rebanada observable. |
| SDD | Marco, no rutinas. Cada `D-n` tiene alternativa descartada. Cubre el 20 % estructural que sostiene el 80 % del comportamiento. Nombra riesgos. Presupuesto del rol 0: 10–20 % del esfuerzo, 20–30 % del calendario, diseño detallado aparte. |
| Plan y alta de `F-n` | Acreción real. `F-1` sin mocks. `requiere` sin ciclos. La clase de software de la feature decide cuánto formalismo añade. |
| Spec | 2 o 3 AC, costura, plan vertical de hasta 5 pasos. Cita `O-n` y `D-n`. El sí del usuario es la revisión del plan antes de construir. |
| Implementer | `check-spec` primero. Test-first. No inventa requisitos. Una decisión de diseño que el SDD no cubre es parada de pair. |
| Revisor y cierre | La integración es parte de la construcción. El postmerge mide choques que el worktree no ve. |
| Bug o task | Caseta: se puede rehacer. Los prerrequisitos de producto no se exigen. Las prácticas de construcción elegidas en el capítulo 4 siguen. |

## Conflictos cerrados en esta parte

* Esqueleto con clases dummy (capítulo 2) frente a `F-1` sin mocks. Gana el arnés.
* Volumen de documentación de un sistema de un millón de líneas frente al tamaño del spec. El volumen es del sistema, repartido. El spec de una feature sigue corto.
* "Tira el primero" frente al walking skeleton real. No se adopta el descarte planificado.
* Tabla de lenguajes de 1998 frente al stack del repo. No elige lenguaje.
* Inspección formal de vida crítica frente a `gate.py`. El gate no certifica seguridad.
* Paso por depurador antes de integrar. Excluido a propósito. Manda el test de la costura.

## Huecos que la Parte I dejó y la Parte II cierra o mantiene

* Estrategia de errores del sistema, nombrada en el SDD. Cerrada en la guía de `templates/sdd.md` (Componentes): corrección o robustez, y la barricada en los puertos.
* Diseño detallado de la rutina antes del primer test. Cerrado como guía en el capítulo 9. No es gate.
* Depuración como método, no solo como parada a los dos intentos. Cerrado como guía en el capítulo 23. No es gate.

---

## Capítulo 5 — Diseño durante la construcción

En un proyecto chico, mucho diseño ocurre sentado al teclado. En uno grande, la arquitectura del capítulo 3 cubre el sistema y deja el resto para la construcción. El diseño rara vez llega tan cerrado que codificar sea mecánico. Tratarlo como actividad explícita es lo que saca provecho. El marco ya tiene que estar satisfecho: sin SDD sellado, este capítulo no arranca.

El diseño enlaza requisitos con código. Es un problema perverso: a menudo solo se define al resolver una parte. El puente de Tacoma Narrows aguantaba la carga prevista y se cayó por un efecto que el plano no había nombrado. En el arnés esa perversidad se recorre con rebanadas `F-n`, no saltándose el problema ni las decisiones caras.

El proceso es desordenado y el resultado tiene que verse ordenado. El error de diseño es más barato que el mismo error ya escrito en código. Una buena solución y una mala suelen diferir poco. Saber "cuánto basta" es parte del desorden: la respuesta floja es "cuando se acaba el tiempo". El diseño también restringe. Sin restricciones el sistema es un edificio con una habitación por zapato. `NO-n` y YAGNI son esas restricciones. Tres personas pueden devolver tres diseños aceptables del mismo problema. Por eso las técnicas son heurísticas, no un algoritmo que una línea de código viole. El diseño emerge: revisiones, la conversación del pair, escribir el código y corregirlo. Casi todo sistema cambia durante la primera construcción y más al extenderse. Cuánto cambio se acepta depende de la clase de software del capítulo 3.

### El imperativo técnico

El imperativo técnico primario es manejar la complejidad. Brooks separa dificultad esencial (el mundo real, las dependencias, el caso que tiene que ser exacto) y accidental (la que las herramientas ya fueron quitando). Cuando un proyecto falla por causa técnica, suele ser complejidad sin dueño: nadie puede decir qué rompe un cambio. Dijkstra: ningún cráneo contiene un programa moderno. El objetivo es poder ignorar el resto mientras se trabaja una parte.

Tres diseños salen caros: solución compleja para un problema simple, solución simple e incorrecta para un problema complejo, y solución compleja inapropiada para un problema complejo. El ataque es doble. Bajar la complejidad esencial que alguien tiene que tener en la cabeza a la vez. Impedir que la accidental se multiplique.

Características internas que el capítulo pide, traducidas. Varias se pisan entre sí: elegir el balance es el trabajo.

| Característica | En el arnés |
| --- | --- |
| Complejidad mínima | Una parte del código se entiende sin cargar el resto. Un diseño "ingenioso" que obliga a tenerlo todo presente falla esta prueba. |
| Fácil de mantener | El lector del diff es la audiencia. El revisor aislado es ese lector. |
| Acoplamiento bajo | Puertos del stack. Pocas mangueras entre subsistemas. |
| Extensión sin violencia | El cambio probable cae en una pieza. El resto no se entera. |
| Reuso | Sale de piezas ya factorizadas. No se diseña "por si otro sistema lo pide". |
| Fan-in alto | Muchas clases usan una utilidad baja. La utilidad es profunda. |
| Fan-out bajo o medio | Más de unas siete clases usadas desde una clase es señal de complejidad (Card y Glass 1990; Basili, Briand y Melo 1996). Señal, no gate. |
| Portabilidad y delgadez | Sin piezas de más. Lo extra hay que escribirlo, revisarlo, probarlo y mantenerlo compatible. |
| Estratificación | Una capa se lee sin bajar a la de abajo. El código viejo y malo se esconde detrás de una capa nueva. |
| Técnicas estándar | Lo exótico se reserva para lo que el problema pide distinto. |

### Niveles

| Nivel | Qué se decide | Dónde vive |
| --- | --- | --- |
| 1. Sistema | El producto entero | PRD y SDD |
| 2. Subsistemas o paquetes | Bloques y quién puede llamar a quién | SDD. Reglas, UI, acceso a datos, dependencias del sistema. El diagrama de sistema es un grafo sin ciclos. |
| 3. Clases | La interfaz de cada clase dentro del bloque | Construcción de la feature. Capítulo 6. |
| 4. Rutinas | La interfaz pública ya dicha, más las privadas | Implementer. Capítulo 7. Definir las rutinas suele corregir la interfaz de la clase. |
| 5. Interior de la rutina | Pseudocódigo, algoritmo, orden de los párrafos | Implementer, antes del primer test de esa rutina. Capítulos 8 y 9. |

El nivel 2 hace falta en cualquier trabajo de más de unas semanas. Sin reglas de comunicación, cada bloque habla con todos y separar deja de servir. La relación más simple es que un subsistema llame rutinas de otro. Contener clases de otro es más enredado. Heredar a través del subsistema es lo más enredado. En duda, restringir temprano y aflojar después. Saltar el nivel 2 es una decisión consciente, no un olvido. El nivel 3 hace falta en un trabajo de más de unos días. El 4, en uno de más de unas horas, aunque sea solo en la cabeza. El 5 siempre ocurre: o consciente y bien, o sin darse cuenta y mal.

Los subsistemas de siempre ya están en el stack: reglas de negocio, UI sustituible, acceso a datos, dependencias del sistema. `check-architecture.py` es la regla de quién habla con quién.

### Heurísticas, no un segundo método

Se prueban. Ninguna garantiza el resultado. Si una no ilumina, se deja y se prueba otra.

* Objetos del mundo real y objetos sintéticos. Atributos, qué se les puede hacer, qué pueden hacerse entre sí, qué queda público. El dominio del stack es ese lugar. El mapeo uno a uno con el mundo es el arranque, no la última palabra.
* Abstracción consistente y detalles escondidos. Dueño: Ousterhout. La pregunta que cierra muchos nudos es "¿qué escondo?".
* Heredar cuando simplifica. El capítulo 6 afina esto: la contención es el default.
* Zonas que van a cambiar, aisladas. Eso ya es un `D-n` cuando el cambio es caro. Un cambio local no abre otro documento.
* Acoplamiento flojo. El acoplamiento semántico (un módulo que sabe el orden interno de otro, un cast al tipo derivado, un dato global que "ya fue inicializado") no lo ve el compilador y rompe lejos del cambio.
* Patrones comunes. Ver abajo. El catálogo no se copia aquí.
* Cohesión fuerte, contrato de la clase, responsabilidades, diseño pensado para probarse. La prueba del arnés es la costura pública del AC.
* Momento de enlace elegido a propósito. Atar temprano simplifica. Atar tarde flexibiliza. La pregunta es cuál de los dos pide el problema.
* Un solo lugar correcto para cada conocimiento no trivial (Plauger). Una constante con nombre ya es ese lugar.
* Fuerza bruta que funciona, antes que una solución elegante que no funciona. La búsqueda binaria se publicó en 1946 y tardó 16 años en ser correcta para todos los tamaños (Knuth). El orden de magnitud lo cubre CLRS. No se inventa un algoritmo en la feature.
* Un diagrama. El SDD ya pide Mermaid. El spec no abre un segundo dibujo.
* Caja negra: se sabe qué entra y qué sale. Si hace falta saber el interior para predecir la salida, el módulo no está haciendo su trabajo.

### Patrones

McConnell trata el patrón como núcleo de solución ya hecha: baja complejidad, guarda los matices que la primera vez se descubren tarde, sugiere alternativas y sube la conversación de nivel. La trampa es forzar el código hasta que parezca el patrón, y la otra es usarlo por ganas de probarlo. Las dos suben la complejidad que el capítulo quiere bajar.

El dueño sigue siendo [`patrones-gof-y-refactoring.md`](patrones-gof-y-refactoring.md). En el sombrero de feature se escribe el código más simple que pone el test en verde. El patrón entra en el sombrero de refactor, cuando un smell del código ya escrito lo pide. Nombrar Adapter, Factory o Strategy en el plan vertical solo si el SDD o el stack ya lo usan. Una feature no estrena un patrón que el spec no necesitaba.

### Cuánto diseño, y cómo se practica

Se itera. El segundo intento suele mejorar al primero, y cada intento enseña algo que el otro no veía. Arriba y abajo a la vez: el panorama ordena el detalle, y el detalle impide que el panorama flote. Se parte el problema (Dijkstra: el cráneo no alcanza) y se sigue descomponiendo hasta que codificar el siguiente nivel sea más fácil que seguir partiéndolo. Si ahora ya es un poco tramposo, después será inaguantable para quien lo lea.

De arriba hacia abajo se difieren los detalles de construcción y se esconden abajo. De abajo hacia arriba se ven pronto las utilidades y las piezas que el hardware o el contrato ya dictan. Usar solo una de las dos deja cajas con piezas sueltas o una cima que el detalle de abajo desmiente. Se prueban las dos.

El prototipo experimental del capítulo es el mínimo código desechable que responde una pregunta concreta. "¿Este almacén sostiene 1.000 transacciones por segundo bajo los supuestos X, Y y Z?" es una pregunta. "¿El framework sirve?" no lo es. Si quien escribe cree que el código va a quedar en producción, deja de escribir el mínimo y empieza a construir el sistema. McConnell sugiere otro lenguaje, o un prefijo que delate el descarte.

Eso choca con `F-1`. El esqueleto del arnés es producto, se mide en la costura y no se tira. Un spike que responde una pregunta de diseño no es la candidata, no se mergea y no se bautiza como código de producción. Si la pregunta ya está respondida por el stack o por una decisión `D-n`, no hay spike.

El diseño de a dos ya existe: el sí del usuario al spec, el pair por defecto en toda feature, la parada cuando aparece una decisión que el plan no tenía. La inspección formal es el capítulo 21. No se agrega un gate. Capturar el diseño es el `## Plan vertical`, los `D-n` y el propio código. Wiki, tarjetas CRC o un UML aparte no son artefactos del arnés.

Cuánto detalle antes de codificar, según la tabla del capítulo, pesada con la clase de software:

| Situación | Detalle antes de construir | Formalidad |
| --- | --- | --- |
| Equipo ducho en el dominio, feature de negocio, vida corta | Bajo. El plan vertical de hasta 5 pasos. | Baja. El spec. |
| Equipo ducho en el oficio y nuevo en el dominio | Medio. | Media. |
| Misión crítica (dinero, folio, datos personales), vida larga | Medio, con la decisión cara ya en el SDD. | Media-alta. Enmienda. |
| Vida crítica | Alto. | Alta. Fuera de alcance. |

Si los factores se contradicen, pesa el que más daño hace al equivocarse. McConnell se inclina a detallar de más cuando duda: los peores huecos son las zonas que parecían fáciles y se dejaron sin diseño. En el arnés ese "de más" es pensar la costura y la clase que la sostiene, dentro de la feature. No es un segundo documento de diseño. El diseño de la clase y de la rutina es construcción. La arquitectura sigue en el SDD.

---

## Capítulo 6 — Clases que se pueden ignorar

Una clase es datos y rutinas con una responsabilidad cohesiva, o un conjunto cohesivo de servicios aunque no compartan datos. Su trabajo es ampliar la parte del programa que se puede ignorar con seguridad mientras se toca otra. Una clase que no permite eso no está haciendo su trabajo.

El fundamento es el tipo abstracto de datos: datos más las operaciones que los tocan, con la representación escondida. Sin esa idea se crean clases que solo lo son de nombre, bolsas de datos y rutinas. Con ella, el resto del programa habla de la fuente, el empleado o la tasa, no del arreglo o del entero que hay debajo. Hasta un ítem simple (una luz, una tarifa) gana con esa envoltura si el nombre y el lugar del cambio quedan en un solo sitio. La clase, en el sentido del capítulo, es ese tipo abstracto más herencia y polimorfismo.

### Interfaz

La interfaz presenta una abstracción consistente. Esconder algo: una interfaz de sistema, una decisión de diseño o un detalle de implementación. Muchos problemas salen de romper esa sola regla. La abstracción y la cohesión se miran juntas. Si la cohesión es débil y no se ve el corte, la pregunta útil es si la abstracción es una sola.

El dato miembro no se publica. Quien lee el código importa más que quien lo escribe: el atajo de escritura se paga cada vez que alguien lee. La parte semántica de la interfaz (hay que inicializar antes de llamar, el llamador cumple un orden que el compilador no exige) es la que se malusa. Donde se pueda, esa regla pasa a ser programática. Ousterhout ya marca el mismo olor: que el llamador ejecute varios métodos en un orden fijo para que la operación exista.

Más de unos siete datos miembro es señal de que la clase está haciendo de más (Miller 1956). Señal, no tope de gate.

### Contención y herencia

Se escribe más sobre herencia que sobre contención, y la contención es la que conviene por defecto. "Tiene un" se modela conteniendo. "Es un" es el único caso en que heredar dice la verdad. Heredar de un contenedor de lista para un censo de empleados miente: el censo no es una lista. Si se quiere la implementación y no la interfaz, se contiene.

La herencia suma complejidad, en contra del imperativo del capítulo 5. Se usa cuando simplifica y cuando se cumple la sustitución de Liskov: un programa escrito contra la clase base sigue siendo correcto si recibe la derivada (Liskov 1988; el resumen de Hunt y Thomas). Si no, la herencia está de adorno. Los stacks hexagonales ya prefieren composición. Las reglas de constructores, destructores, `virtual` y `final` cambian con el lenguaje: las responde el stack y Context7, no una tabla de C++, Java o Visual Basic copiada a otro repo.

### Cuándo crear una, y cuándo no

La razón principal es reducir complejidad: escribirla una vez y después usarla sin saber el interior. También sirven aislar un algoritmo o un protocolo, esconder un detalle (aunque sea mundano), limitar el efecto de un cambio, esconder un dato global detrás de acceso, reunir rutinas que se pasan el mismo parámetro una y otra vez, y tener un solo lugar que controla una tabla, un archivo o una conexión.

El reuso que el capítulo cuenta (NASA SEL, McGarry, Waligora y McDermott 1989: los proyectos siguientes orientados a objetos reutilizaron más del 70 % del código, frente a cerca del 35 % en diseño funcional) no autoriza a dorar la feature. El núcleo de ese enfoque identifica candidatos al final del proyecto, como trabajo aparte, no "por si acaso" durante la construcción. Empaquetar operaciones relacionadas (las trigonométricas, las de cadena) puede ser una clase, un paquete o un namespace, según el lenguaje. Un refactor concreto del capítulo 24 también crea clases. El catálogo de olores sigue en GoF y Fowler. Este archivo no lo repite.

Clases que se evitan:

* La clase dios, que todo lo sabe y todo lo manda, y vive de leer y escribir a las demás. Esa conducta vuelve a las clases que tienen los datos (Riel 1996).
* La clase que solo tiene datos y ninguna conducta. Pasa a ser atributo de otra.
* La clase bautizada con un verbo y sin datos (`DatabaseInitialization`). Es una rutina de otra clase.

Por encima de la clase, el paquete agrupa y declara qué paquetes pueden usar a cuáles, y si ese uso es herencia, contención o las dos. En el arnés ese paquete es el módulo del stack, y la regla de uso es `check-architecture.py`.

---

## Capítulo 7 — Rutinas de una sola cosa

Una rutina es un método o procedimiento invocable para un solo propósito. La razón principal para crearla es que el programa quepa en la cabeza. Leer mejor, fallar menos y poder cambiarla pesan más que ahorrar espacio. A veces la operación que más gana al extraerse es una simple. Eso no autoriza el método de tres líneas que solo pasa la llamada: ese corte está cerrado en el conflicto de largo, más abajo.

### Cohesión, nombre, parámetros

La cohesión funcional es la meta: hace una cosa y la hace bien. Un estudio de Card, Church y Agresti (1986) encontró las rutinas de cohesión funcional libres de defectos con más frecuencia. Otro (Selby y Basili) encontró que las de peor razón acoplamiento/cohesión tenían unas 7 veces más errores y costaban unas 20 veces más de corregir. La cohesión secuencial, comunicacional o temporal es más débil. La procedural, lógica o coincidental se reescribe. Un `Startup` con un solo propósito claro puede ser funcional. El mismo cuerpo bautizado por el reloj ("todo lo que pasa al arrancar, junto") no lo es.

El nombre delata la calidad. Si es malo y es exacto, la rutina está mal diseñada. Si es malo y es inexacto, no dice lo que el programa hace. En los dos casos se cambia el código, no se acostumbra el lector. Un procedimiento se nombra verbo más objeto. Una función se nombra por el valor que devuelve, y ese valor existe en todos los caminos. Las operaciones repetidas comparten la convención del stack. Inventar cuatro formas de leer el mismo identificador obliga a todo el equipo a recordar un detalle que no importa.

Los parámetros son de las zonas más defectuosas. Basili y Perricone (1984) atribuyen el 39 % de los errores a interfaces internas entre rutinas. El tope comprensible ronda los siete. Once es el ejemplo malo del capítulo. El orden es entrada, luego entrada-y-salida, luego salida, alineado con las rutinas hermanas. Cada parámetro se usa. Uno de entrada no se recicla como variable de trabajo. La lista, tomada entera, presenta una abstracción. La lista larga ya es un smell de Fowler (`Long Parameter List`): se trata en el sombrero de refactor, con un objeto de parámetros cuando el dato viaja junto. No es un gate nuevo.

### Cuánto puede medir

McConnell recoge el debate y no lo cierra con un número mágico. El ideal teórico que se cita a menudo es una pantalla o una o dos páginas, unas 50 a 150 líneas. IBM llegó a limitar a 50. TRW, a dos páginas. Los estudios que resume:

* Al crecer la rutina, hasta 200 líneas, bajaban los errores por línea (Basili y Perricone 1984).
* El tamaño no correlacionó con errores cuando sí lo hacían la complejidad estructural y la cantidad de datos (Shen y otros 1985).
* Las rutinas de 32 líneas o menos no salieron más baratas ni con menos defectos. Las de 65 o más salían más baratas por línea (Card, Church y Agresti 1986; Card y Glass 1990).
* Por debajo de 143 enunciados, un 23 % más de errores por línea, y a la vez 2,4 veces más baratas de arreglar (Selby y Basili 1991).
* Menos cambios cuando el promedio rondaba 100 a 150 líneas (Lind y Vairavan 1989).
* Las más defectuosas pasaban de 500 líneas. Desde ahí la tasa sigue al tamaño (Jones 1986a).

La conclusión del libro: en un programa orientado a objetos muchas rutinas son de acceso y serán cortas. Un algoritmo complejo puede crecer de forma orgánica hasta 100–200 líneas de código no vacías y no comentario. La cohesión, el anidamiento, las variables, los puntos de decisión y los comentarios que hagan falta mandan sobre un tope artificial. Pasar de unas 200 líneas pide cuidado: los estudios que ven ventaja en la rutina larga no distinguen tamaños por encima de eso.

Ousterhout, y el implementer del arnés, prefieren la función profunda y cohesiva de unas 30 a 80 líneas, con un solo nivel de abstracción, y prohíben partirla en micro-métodos de 3 a 5 líneas. Los dos textos tienen razón en lo que atacan y se pisan en el número.

Resolución: ningún número es gate. Una rutina de tres líneas que solo reenvía la llamada sigue siendo un olor, y gana Ousterhout. Una rutina de 200 líneas no queda absuelta por el estudio de 1984: se mira anidamiento, decisiones y si hace más de una cosa. El criterio es una responsabilidad, un nivel de abstracción, módulo profundo. La parada de pair a unas 50 líneas o 3 archivos es el tamaño de un ciclo TDD, no el tamaño de la rutina terminada.

Macros e inline, solo como último recurso. El inline rompe el encapsulamiento (el cuerpo queda en el encabezado) y puede inflar el código. Afinarlo por rendimiento exige medirlo. Sin un AC que pida ese rendimiento, no se toca. Los capítulos 25 y 26 siguen siendo el lugar de esa medición.

---

## Capítulo 8 — Programación defensiva

La idea es la del conductor defensivo: si a la rutina le llega un dato malo, no resulta herida, aunque la culpa sea de otra. En producción, "entra basura, sale basura" es programa flojo. Las respuestas aceptables son no dejar entrar la basura, no sacar nada, o sacar un error definido.

Eso viene después de no insertar el defecto. Diseño iterativo, pensar la rutina, escribir el test antes del código y la revisión pesan más que el código defensivo. El código defensivo también tiene defectos, y de más engorda y ralentiza. Se elige dónde hace falta. No se chequea cada parámetro en cada rincón.

Tres movimientos. Comprobar todo dato que llega de archivo, usuario, red u otra fuente externa, sobre todo si puede ser desborde, SQL, HTML o un entero que no cabe. Comprobar las entradas en la frontera, no en cada rutina privada. Decidir una sola vez qué se hace con la entrada mala.

### Aserciones y errores esperados

La aserción documenta una suposición durante el desarrollo y dispara cuando el programa se contradice. El manejo de errores es para lo que se espera que ocurra. La aserción es para el bug. No llevan código con efecto: si el build de producción las retira, ese efecto desaparece con ellas. Precondiciones y postcondiciones de datos internos ya saneados caben en aserciones. El dato externo no se "afirma": se valida.

Una aserción no es evidencia de AC. La evidencia sigue siendo el test de la costura. El usuario de producción no ve el texto de una aserción.

Técnicas para lo esperado, y cuándo no:

| Técnica | Cuándo se considera | Cuándo se descarta |
| --- | --- | --- |
| Valor neutro, siguiente válido, último valor, valor legal más cercano | Un sensor, un color de juego, un dato donde seguir es inocuo. | Un resultado que alguien va a creer. La radiografía y el cajero del capítulo no inventan un valor. |
| Registrar y seguir | Junto con otra técnica, si el registro no ayuda a un atacante. | Como única respuesta de un dato que cambia dinero o un folio. |
| Código de error o excepción hacia arriba | La frontera reporta y un nivel alto decide. | Ignorar el código. En los lenguajes que lo permiten, se mira igual. |
| Manejador central | Ya existe en el stack. | Crearlo "por el capítulo". Acopla el reuso, y tras un desborde de búfer la dirección del manejador puede estar comprometida (Howard y LeBlanc). |
| Mensaje en el punto del fallo | Casi nunca, en estos stacks. | Esparce UI, rompe el idioma y le cuenta el sistema a quien ataca. |
| Cada quien decide en local | Solo si el SDD ya fijó el criterio. | Como política: la corrección del conjunto deja de ser predecible. |
| Apagar | Vida crítica. Fuera de alcance. | Un portal de negocio. |

Corrección: no devolver un resultado inexacto. Devolver nada es mejor que devolver algo mal. Robustez: seguir operando aunque a veces el resultado sea inexacto. Seguridad e instrumentos médicos se inclinan a la corrección. Aplicaciones de consumo, a la robustez. En CALPIL la feature de negocio se inclina a un fallo explícito en el puerto, visible para quien usa el sistema. Dinero, folio y datos personales se inclinan a la corrección: no hay folio inventado ni fila de más. Cuál de las dos vale en este producto es la estrategia de errores del SDD, incorporada en la plantilla `templates/sdd.md` bajo Componentes para guiar el borrador sin crear un gate rígido.

Ousterhout manda cuando el "error" es un caso ordinario: colección vacía, borrado idempotente. Ese caso es flujo normal. Inventarle un código de error crea el error que el diseño podía no tener. El dato no confiable que cruza la frontera sigue siendo manejo de errores, no un caso definido fuera de existencia.

### La barricada

Unas clases trabajan con dato sucio. Otras solo ven dato ya limpio. Las públicas del borde comprueban, convierten al tipo correcto en el momento de entrar (un "sí" no viaja como texto hasta el fondo) y rechazan. De ahí hacia adentro, un dato malo es un defecto del programa, y la herramienta es la aserción, no otra copia de la validación. Puede hacer falta más de un borde (UI y API). Decidir qué queda dentro es decisión de arquitectura: en estos stacks, el puerto.

La excepción se reserva para lo verdaderamente excepcional. Usada con tino baja complejidad, porque el fallo no se puede ignorar. Usada por costumbre la sube: el llamador tiene que conocer lo que la rutina lanza, y eso rompe el encapsulamiento. No se relanza si se puede resolver ahí. No se lanza desde un constructor o un destructor salvo que se atrape en el mismo sitio: en C++ el destructor no corre si el constructor no terminó, y las reglas se vuelven las que solo un especialista recuerda. Se lanza al nivel de la abstracción de la interfaz. Un fin de archivo del disco no sale por la puerta de empleado: sale "dato de empleado no disponible". El mensaje lleva el dato que la causó (el índice ilegal y los límites) y no lleva una pista de ataque. Un `catch` vacío dice que el `try` no debía lanzar o que el `catch` no hace su trabajo. Si de verdad corresponde callar, queda registrado por qué. Hay que conocer las excepciones de la librería aunque el lenguaje no obligue a declararlas.

Elegir la excepción solo porque el lenguaje la tiene es programar *en* el lenguaje. Go, Rust, ProblemDetails o el tipo de error del stack ganan sobre una doctrina copiada de Java. El capítulo 4 ya cerró ese criterio.

### Qué queda en producción

En desarrollo el fallo tiene que ser imposible de pasar por alto: la aserción aborta, el caso no previsto hace ruido. En producción el mismo fallo se recupera o cae con gracia, sin perder el trabajo de quien usa el sistema. Se dejan las comprobaciones de los errores que importan (el cálculo, no el pixel). Se retiran del binario de producción, por build o por bandera, las que solo sirven para cazar y las que tumban el proceso en un descuido trivial. Un auxilio que permitió diagnosticar después del release puede quedarse, cambiando el aborto por un registro. El texto que ve el usuario dice "error interno" y cómo reportarlo, no un insulto al puntero.

Eso no crea un gate de depurador ni una bandera `DEBUG` obligatoria. La evidencia del AC sigue siendo el test. El método para cazar el defecto, más allá de parar a los dos intentos sin verde, está en el capítulo 23.

La seguridad de la entrada (desborde, inyección, entero) la cubren las skills del stack. Este capítulo recuerda el criterio: comprobar, no confiar, y no informar de más.

---

## Capítulo 9 — Pensar la rutina antes del primer test

Construir una clase es iterativo. Se diseña en general (responsabilidad, secreto, abstracción de la interfaz, si alguien hereda, métodos públicos, datos no triviales). Se construye cada rutina. Al construirla aparecen rutinas que el diseño general no tenía, y eso corrige la clase. Al final se revisa la clase entera por lo que una rutina suelta no muestra. El test de cada rutina ocurre mientras se construye. En el arnés ese test es el de la costura del AC, no un test por método privado.

La rutina complicada sigue cuatro pasos: diseñarla, revisar el diseño, codificarla, revisar el código. El proceso de pseudocódigo es el favorito de McConnell para el diseño. El test-first (Beck 2003), el refactor y el diseño por contrato son alternativas o complementos. El arnés ya eligió el test-first como ciclo. Este capítulo no lo sustituye.

### Cómo se escribe el pseudocódigo

Enunciados precisos, en idioma de quien lee, sin sintaxis del lenguaje de destino. Al nivel de la intención: qué significa el paso, no cómo lo escribirá el lenguaje. Lo bastante bajo para que codificar sea casi automático. Si un renglón esconde un problema, se baja otro nivel. Si bajar ya es más lento que escribir el código, se para.

El pseudocódigo malo del capítulo mete `malloc`, punteros y códigos de retorno del lenguaje. Solo se podría implementar en ese lenguaje y no dice la intención. El bueno dice "si hay otro recurso, reservar la estructura, anotar que hay uno más en uso, inicializar, guardar el número donde el llamador indicó, devolver si se creó".

Beneficios que el capítulo atribuye: se revisan unas pocas líneas y se ven suposiciones que en código quedan escondidas (el ejemplo habla de 11 líneas de pseudocódigo frente a 35 de C++ o Java); el error se caza en el momento de menor costo; cambiar una línea de plano es más barato que mover el muro; y, en el libro, el pseudocódigo se convierte en comentario y el comentario nace alineado con el código.

Ese último paso choca con la regla de comentarios del implementer: se documenta contrato, invariante e intención, y se prohíbe parafrasear el código. McConnell mismo pide quitar el comentario que resultó redundante. Resolución: el pseudocódigo es pensamiento, no un estilo de comentario obligatorio. Se queda escrito en el código solo donde dice el porqué. Lo que repite el cómo se borra al codificar.

### El orden dentro del ciclo

Antes de la rutina se confirma que el trabajo está definido, que encaja en el diseño y que el requisito lo pide, aunque sea de forma indirecta. Eso ya es `check-spec` más el AC. Si el dato es el protagonista, se piensa antes que las ramas.

Se escriben varias ideas y se guarda la mejor. En cuanto hay código, cuesta tirar el diseño malo: uno se encariña. Si aparece dato global, o una operación que pertenece a otra clase, se vuelve al diseño. Se aplica el mismo proceso de forma recursiva cuando un renglón se convierte en demasiado código.

En el arnés ese pensamiento ocurre antes de escribir el primer test de la costura, o en la parada de pair cuando el diseño no estaba en el plan. No es un artefacto nuevo. No es un comentario obligatorio. No abre otro gate. El primer ejecutable que demuestra la rutina sigue siendo el test en rojo. McConnell presenta el pseudocódigo como método principal y el test-first como alternativa. Gana el arnés: las dos cosas conviven, y el rojo no se pospone hasta tener la rutina diseñada en comentario.

Al revisar el código se recorren el camino nominal, los extremos y las excepciones. Si la rutina sale mal, se vuelve al pseudocódigo en vez de parchar. El verde de la costura es esa revisión hecha ejecutable. El revisor aislado mira el diff, no un documento de pseudocódigo aparte.

---

## Matriz de la Parte II

| Fase | Criterio |
| --- | --- |
| SDD | Nivel de sistema y de subsistema. Grafo de bloques sin ciclos. Estrategia de errores (corrección o robustez) y barricada en puertos guiadas en la plantilla. |
| Spec | El plan vertical deja la costura obvia de implementar. Una decisión que no cabe en cinco pasos y no está en un `D-n` es parada, no un segundo diseño. |
| Patrones | Vocabulario del dueño GoF. Entran en el sombrero de refactor. No se fuerzan ni se estrenan por ganas. |
| Implementer, clase | Una responsabilidad, un secreto, interfaz que se puede usar sin conocer el interior. Contención por defecto. Herencia solo si es "es un" y sustituye (Liskov). Sin clase dios, sin clase verbo, sin dato público. |
| Implementer, rutina | Una cosa, cohesión funcional, nombre que dice la verdad, parámetros en el orden entrada / modificación / salida, alrededor de siete como olor. Largo: módulo profundo. Ni micro-método ni rutina de 200 líneas absuelta. |
| Implementer, ciclo | Pensar la rutina (varias ideas, quedarse con la mejor) y enseguida el test de la costura en rojo. El pseudocódigo no reemplaza el TDD ni se queda como comentario que repite el código. |
| Defensivo | El borde valida y convierte. Adentro, el dato malo es un bug. La aserción no demuestra el AC. El caso ordinario no se vuelve error. El caso no confiable sí se rechaza. |
| Revisor | Barricada rota, `catch` vacío, excepción del disco que cruza el puerto, lista de parámetros que no abstrae, clase que no deja ignorar el resto. Hallazgo sobre el diff. Sin gate nuevo. |
| Spike | Pregunta concreta, código mínimo, no se mergea. `F-1` sigue siendo producto. |

## Conflictos cerrados en esta parte

* Largo de rutina. McConnell deja crecer hasta unas 100–200 líneas de código no vacías y no comentario, con cuidado al pasar de 200, y dice que el tope artificial estorba. Ousterhout y el implementer prefieren unas 30 a 80 y prohíben el corte de 3 a 5 líneas. Ningún número es gate. Gana el criterio de una responsabilidad y un nivel de abstracción. La parada de ~50 líneas es el ciclo TDD, no la rutina terminada.
* "Heredar cuando se pueda" (lista del capítulo 5) frente a "la contención suele ser preferible" (puntos clave del capítulo 6). Manda el capítulo 6, y ya es la composición de los stacks.
* Pseudocódigo como método principal, convertido en comentarios, frente al TDD vertical y a los comentarios que no parafrasean el código. Gana el arnés. El pseudocódigo es el pensamiento previo al primer rojo. El comentario se queda solo si dice el porqué.
* Prototipo experimental desechable frente a `F-1` sin mocks. El spike no es la candidata y no se mergea. El esqueleto sigue siendo producto.
* Código de error para un caso ordinario frente a definir el error fuera de existencia. Gana Ousterhout en el caso ordinario. El dato que cruza la barricada sigue validándose.
* Patrón como herramienta de diseño desde el primer intento frente a los dos sombreros. El patrón entra con el código ya en verde, cuando un smell lo pide.
* Manejador global de errores y aserciones que abortan en producción. No se adoptan como pieza obligatoria. El stack manda. La evidencia del AC es el test.

## Huecos que siguen abiertos

* Estrategia de errores del sistema, nombrada en el SDD: corrección o robustez, barricada y protocolo. Cerrada como guía en `templates/sdd.md`.
* Depuración como método, más allá de la parada a los dos intentos sin verde. Cerrado como guía en el capítulo 23.
* Colaboración formal y refactor como catálogo. Cerrados como guía en los capítulos 21 y 24. El revisor aislado y los dos sombreros siguen siendo los dueños.

## Partes III y IV — Datos y control, en checklist

Estas dos partes bajan al enunciado: la variable, el nombre, el tipo, el orden de las líneas, el `if`, el bucle y la complejidad del flujo. El formateador del stack ya fija llaves, indentación y el orden que una herramienta puede imponer. Eso no se reabre aquí ni en el review. Lo que sigue es criterio de construcción. El implementer lo aplica mientras escribe. El revisor lo cita en el diff cuando el código lo rompe. No es un gate nuevo ni un linter distinto del que el stack ya corre.

El layout, el comentario que explica el cómo y el carácter del oficio siguen en los capítulos 31 a 34.

---

## Capítulo 10 — Cada variable, un propósito

La construcción rellena huecos chicos del requisito y de la arquitectura. Este capítulo es ese relleno: cómo se usa el dato. "Variable" incluye el objeto y el tipo de lenguaje. El repertorio de tipos es el del stack, más CLRS cuando la estructura cambia el orden de magnitud.

* Se inicializa en la declaración, con el valor que el camino va a usar. Un dato sin valor inicial es una fuente típica de error. No se cuenta con que el lenguaje ponga cero si el cero no es el significado.
* El alcance es el más corto que el uso permite: el bloque, la rutina, la clase. Las referencias a la misma variable quedan juntas. El tramo (líneas entre dos usos) y la vida (de la primera referencia a la última) se mantienen cortos. Una vida larga es el síntoma de que la rutina está haciendo de más, y enlaza con el corte del capítulo 7.
* Una variable, un solo propósito. Reciclar `total` para otra suma a mitad de la rutina miente el nombre.
* Lo que debe sobrevivir a la llamada no se esconde en un estático local. Eso es un global disfrazado. El estado de la feature vive en el objeto que el puerto ya definió.
* Atar temprano simplifica. Atar tarde flexibiliza. La elección es consciente, la misma del capítulo 5. Un valor que el AC fija se ata en el código o en la configuración del stack, no se deja para "ver luego".

---

## Capítulo 11 — El nombre es la variable

El nombre y el dato son la misma cosa para quien lee. El ejemplo malo del capítulo (`x`, `xx`, `xxx`, `fido`) no deja saber cuál cifra es la factura de las compras nuevas. El nombre específico sí.

Gorla, Benander y Benander (1990) vieron menos esfuerzo de depuración con nombres que promediaban 10 a 16 caracteres. De 8 a 20 salía casi igual. Eso no es un largo obligatorio. Si el diff está lleno de nombres de una o dos letras, se mira si dicen lo que son. `i`, `j` y `k` se reservan al índice de un bucle corto. Un bucle con significado lleva el nombre de lo que recorre.

* El nombre sirve para una sola cosa. Si vale para dos, está flojo.
* Los opuestos se usan en pareja y con la palabra que el idioma ya tiene: abrir/cerrar, primero/último, mínimo/máximo, origen/destino, anterior/nuevo. Una pareja inventada se olvida.
* Un booleano se lee como pregunta o como estado: `encontrado`, `listo`, `tieneSaldo`. `flag` no dice nada. `status` y `sourceFile` tampoco son booleanos.
* Un estado es un enumerado o una constante con nombre. `statusFlag = 0x80` obliga a recordar una tabla que el código no muestra.
* Se evitan nombres que mienten, que significan casi lo mismo, que se distinguen por una letra, que suenan igual, que meten un número para diferenciarlos, que están mal escritos a propósito, o que pisan un nombre de la librería.
* Se abrevia poco. Con los lenguajes de ahora casi nunca hace falta. Si un dominio usa una sigla, es la sigla que el PRD ya usa, no un diccionario paralelo.

La convención distingue local, campo y global, y distingue tipo, constante, enumerado y variable. El capítulo ofrece prefijos estandarizados (la notación húngara y los `ps` / `ach` del C). En estos stacks gana el idioma del repo: exportación de Go, tipos de Rust, Pascal público de C#, el nombre de dominio de Angular. No se instala un esquema de prefijos encima del formateador.

El código se lee muchas más veces de las que se escribe. El nombre favorece a quien lee. Eso ya lo decía el capítulo 6.

---

## Capítulo 12 — El tipo que el problema pide

Cada tipo tiene sus fallos propios. El checklist reemplaza la memoria.

| Tipo | Qué se cuida | En el arnés |
| --- | --- | --- |
| Entero | `7/10` es 0, no 0,7. El desborde de 32 bits existe. | La división que el AC promete se hace en el tipo que conserva el resto. Un contador que puede pasar el máximo usa el ancho del stack. |
| Flotante | `0,1` sumado diez veces casi nunca es `1,0`. `1.000.000 + 0,1` puede perder el `0,1`. No se comparan con `==`. | Dinero, folio, tasa que alguien va a creer: unidades enteras menores o el decimal del stack. El binario de punto flotante no cierra una cuenta. |
| Mezcla | Comparar flotante con entero promociona y miente. | El borde convierte una vez, capítulo 8. Adentro el tipo ya es el del dominio. |
| Carácter y cadena | Literales mágicos (`"A"`, un título de programa). Índices que se salen. En C, el puntero a cadena. | El texto de usuario sale del requisito o del recurso de idioma. El corte de una subcadena se prueba en el extremo. |
| Booleano | `0` y `1` como verdad. | `true` y `false` del lenguaje. La expresión se lee sola. |
| Enumerado | Un entero con significado escondido. | El estado de un caso de uso es un tipo del dominio, no un `int` comentado. |
| Constante con nombre | El literal `100` o `47524` en medio del código. | El `0` y el `1` de un índice pueden quedar. Cualquier otro literal de negocio tiene nombre. |
| Arreglo | El primero y el último, el off-by-one. | El iterador del lenguaje recorre la colección. El índice a mano se reserva al caso que el AC mide. |

Crear un alias de tipo documenta y localiza el cambio. Si el alias no tiene invariante, se pregunta si basta el tipo del lenguaje. Si el alias protege una regla (un identificador, un importe, un periodo), es un tipo del dominio: el value object que el sombrero de refactor ya extrae ante *primitive obsession*. No se crea una clase por cada alias.

---

## Capítulo 13 — Estructuras, punteros y globales

Una estructura agrupa datos que viajan juntos. Cambiar un campo se ve en quien usa el grupo, no en cada variable suelta que casualmente se llamaba `title`. En Java y C++ una clase de solo datos públicos es una estructura con otro nombre.

Se prefiere la clase cuando hay conducta o un secreto. Un DTO de borde, sin invariante, puede ser el registro o la estructura del stack. Meterle métodos "por si acaso" es la clase que el capítulo 6 manda evitar cuando solo tiene datos.

El puntero es de las zonas más defectuosas. Muchos fallos de seguridad, en especial el desborde de búfer, salen de un puntero mal usado (Howard y LeBlanc 2003). Java, C# y Visual Basic del libro ya no ofrecen el tipo. Go y Rust lo tienen con otras reglas, y esas reglas las dice el stack. No se adopta aritmética de punteros, ni marcas manuales en el bloque, ni un preprocesador de depuración de punteros. La propiedad del dato es la del lenguaje. El desborde de entrada sigue siendo la barricada del capítulo 8.

El global se evita. No solo porque es peligroso: porque hay algo mejor. Un dato de proceso que de verdad es uno (la configuración leída al arrancar) entra por la raíz de composición, inmutable después del arranque. Esconder un global detrás de rutinas de acceso, o detrás de un singleton, sigue siendo un global: todo el programa queda acoplado a ese lugar. El capítulo 6 ya lo decía. El patrón Singleton no se estrena para guardar estado de la feature.

---

## Capítulo 14 — El orden de las líneas

La dependencia manda. Leer, calcular, imprimir va en ese orden porque cada paso consume el anterior. Si el nombre y los parámetros no dejan ver la dependencia (`ComputeQuarterly` antes de `ComputeAnnual` sin decirlo), el lector tiene que saber contabilidad para no invertirlos. En código crítico, el libro sugiere una variable de control que falle si el paso anterior no ocurrió. En el arnés esa comprobación es el test de la costura: el AC fija el orden observable. No se añade una bandera de "ya calculé el mes" salvo que el dominio la necesite.

Donde el orden no importa, lo relacionado queda junto. Cajas que se solapan son el síntoma. Un grupo independiente, con una responsabilidad propia, puede ser su rutina. Un grupo de tres líneas que solo reenvía no se extrae: el conflicto de largo del capítulo 7 sigue cerrado.

El código se lee de arriba abajo. Un comentario que existe solo para explicar una dependencia escondida dice el porqué. Si hace falta, la dependencia no está en el nombre.

---

## Capítulo 15 — Condiciones

El camino normal se escribe primero. Los casos raros no lo tapan. El caso normal va en el `if`. El `else` queda para lo que se sale de eso. Poner el error adelante y el éxito en el `else` obliga a leer el fallo para encontrar el negocio.

La igualdad es el off-by-one del condicional. `>` donde iba `>=` falla en el borde. Ese borde es un caso del test de la costura cuando el AC lo nombra.

Cadenas de `if` y `case` se ordenan para que se lean: por frecuencia, por el orden del dominio, o por una tabla si la cadena ya confunde (capítulo 18). El `default`, o el último `else`, atrapa lo que no estaba previsto. En desarrollo hace ruido. En producción sigue la estrategia del capítulo 8. No se traga el caso desconocido.

El constructo se elige. Un `if` de dos caminos no se escribe como `switch` de veinte. Un conjunto cerrado de estados no se escribe como una escalera de `if` que el siguiente estado deja incompleta.

---

## Capítulo 16 — Bucles

El bucle es de lo más complejo del control. Se elige por flexibilidad y por dónde está la prueba de fin.

| Clase | Cuándo | Prueba |
| --- | --- | --- |
| Contado | Se sabe cuántas veces. Una por empleado, una por ítem. | El índice no se altera dentro. No es flotante. |
| Evaluado cada vuelta | No se sabe el número. Mientras quede saldo, hasta que quien usa sale, hasta un error. | La condición de salida se ve. El cuerpo que está antes de una prueba a mitad se ejecuta al menos una vez. |
| Iterador | Una vez por elemento de una colección. | Es el default al recorrer. El índice a mano pide una razón. |
| Sin fin | Un proceso que vive mientras el servicio vive. | Fuera de una feature de negocio. Un `for` infinito en un caso de uso es un defecto. |

El índice tiene un propósito y un nombre. No se usa fuera del bucle para guardar un resultado: se copia a una variable con el significado. No se cruzan índices de dos bucles anidados.

El bucle termina en todas las condiciones, también en la vacía y en la de un elemento. Esas dos son extremos del AC cuando el conjunto puede llegar vacío. Un contador de seguridad (un tope para no colgarse) solo si la salida no es obvia y el dominio puede no avanzar. Puesto por costumbre, añade un camino más que también falla.

`break` cerca de la condición que lo causa puede leerse mejor que una bandera booleana que simula la salida. Muchos `break` repartidos vuelven opaca la terminación. `continue` es un `if` invertido: si el cuerpo se entiende menos, se escribe el `if`. Entrar al medio del bucle con `goto` es el ejemplo malo del capítulo. Se reescribe con la estructura del lenguaje.

La correspondencia entre bucle y arreglo se mantiene: el mismo rango, el mismo extremo. Un off-by-one aquí es el defecto clásico. El test del extremo lo caza.

---

## Capítulo 17 — Salidas, recursión y goto

Varios `return` ayudan cuando, al saber la respuesta, no queda limpieza pendiente y un solo retorno hundiría el camino normal en anidamiento. En Go el retorno temprano es el idioma. En un lenguaje con `defer` o `using`, la limpieza no se salta. Un retorno a mitad que deja un recurso abierto es el caso que el capítulo pide evitar.

La recursión resuelve bien un conjunto chico de problemas (un árbol, una estructura que se contiene). Para el resto, la iteración se entiende mejor. Tiene que haber un caso que pare. Si ese caso puede no llegar (un grafo con ciclo, una ruta que vuelve a sí misma), hace falta un tope. La recursión cíclica, A llama a B llama a C llama a A, es difícil de ver y se evita. El algoritmo y su costo siguen en CLRS. No se reescribe un recorrido como recursión elegante si el stack ya tiene el iterador, ni se añade un contador ceremonial cuando el caso base es obvio y el test lo cubre.

El `goto` queda como último recurso, en los pocos casos en que el lenguaje no tiene otra salida legible. En estos stacks ese caso casi no aparece. Un `goto` en el diff se mira como defecto salvo que el idioma del stack lo use para un fin ya aceptado, y hoy ninguno de los ocho lo pide.

---

## Capítulo 18 — Tablas en vez de lógica enredada

Lo que se elige con una cadena de `if` o con un `case` se puede elegir en una tabla. En lo simple, el `if` es más directo. Cuando la cadena confunde, la tabla es más simple de cambiar y esconde la clasificación en un solo lugar.

Tres accesos: directo (la clave es el índice), por índice (una clave se traduce al índice) y por escalones (rangos: de 0 a 10, de 11 a 50). Hay que decidir qué se guarda: un valor, una acción, o las dos. Una tabla de mensajes o de tarifas que el negocio cambia es dato, no una jerarquía de clases. El capítulo lo dice con claridad: un diseño orientado a objetos no es mejor solo por serlo.

Eso encaja con los dos sombreros. En el sombrero de feature, el `if` corto que el AC describe se queda. Cuando la cadena o la herencia existen para elegir un valor, la tabla o el mapa del lenguaje es el refactor. No se crea una subclase por cada carácter, cada tarifa o cada código de error. El día que la tabla sea un algoritmo con costo (búsqueda, orden), manda CLRS, no este capítulo.

---

## Capítulo 19 — Complejidad del flujo

La expresión booleana se lee en positivo. `true` y `false`, no `1` y `0`. Un número se compara con su valor. Un booleano no se compara con `== true` si el lenguaje ya lo evalúa. Las negaciones encadenadas se simplifican con De Morgan hasta que la frase dice lo que se quiere, no lo que se descarta. Si la expresión no cabe en la cabeza, una variable booleana con nombre, o una función booleana, le pone el significado. La tabla del capítulo 18 es la otra salida.

El anidamiento hondo se domina sin partir la rutina en migajas: retorno temprano del caso que no aplica, el camino normal al frente, una tabla, o extraer un trozo que ya es una responsabilidad. Un bloque vacío, o un enunciado nulo que parece un error de llave, se borra o se explica. El formateador equilibra las llaves. El revisor no discute el estilo del bloque.

La programación estructurada sigue siendo el cimiento: cualquier flujo se arma con secuencia, selección e iteración. Las salidas del capítulo 17 se suman con cuidado. No reemplazan el cimiento.

La complejidad de McCabe cuenta puntos de decisión: se empieza en 1 y se suma cada `if`, `while`, `for`, `and`, `or` y cada caso de un `case`. Guía del capítulo:

| Puntos | Qué hacer |
| --- | --- |
| 0 a 5 | La rutina está holgada. |
| 6 a 10 | Se piensa cómo simplificar. |
| Más de 10 | Señal de partir. El propio texto dice que no es un límite absoluto: un `case` largo puede pasar de 10 y partirlo sería peor. |

Mover decisiones a otra rutina no baja la complejidad del programa. Baja la que alguien tiene en la cabeza a la vez. Partir solo para que el número caiga, dejando un método de tres líneas, choca con el módulo profundo. Gana el criterio ya cerrado en el capítulo 7: una responsabilidad, un nivel de abstracción. El número de McCabe es una señal para el revisor, igual que el fan-out de siete. No es un gate ni un tope que el implementer persiga.

Otras señales del mismo capítulo, ya usadas antes: datos que la rutina toca, niveles de anidamiento, líneas, tramo y vida de cada variable, entradas y salidas.

---

## Matriz de las Partes III y IV

| Fase | Criterio |
| --- | --- |
| Implementer, datos | Un propósito por variable. Alcance corto. Inicializada con su significado. Tipo del problema: enumerado para el estado, decimal o entero menor para el dinero, iterador para la colección. |
| Implementer, nombres | Específicos, leíbles, opuestos del idioma. Sin húngaro encima del stack. Sin `flag`, sin literal de negocio desnudo. |
| Implementer, control | Dependencias visibles de arriba abajo. Camino normal en el `if`. Bucle que termina, índice intacto. Tabla cuando la cadena de `if` ya confunde. |
| Implementer, flujo | Retorno temprano si no deja limpieza colgada. Recursión solo con parada clara. Sin `goto`. Sin global de feature. |
| Revisor | Off-by-one, float comparado con `==` en una cifra que se cree, `catch` o `default` que traga, bucle que no termina, nombre que miente, McCabe alto en una rutina que además hace dos cosas. Hallazgo sobre el diff. |
| Layout | Del formateador. Estas partes no lo discuten. |

## Conflictos cerrados en esta parte

* Prefijos húngaros y diccionario de abreviaturas frente a la convención del stack. Gana el stack. El estudio de 10 a 16 caracteres no fija un largo.
* McCabe por encima de 10 como orden de partir la rutina frente al módulo profundo. El número es señal. No se extrae un método para bajar la cuenta. El `case` largo puede quedarse.
* Estructura de solo datos frente a "siempre una clase". El DTO de borde puede ser un registro. El dominio con invariante es un tipo con conducta.
* Rutinas de acceso o singleton que envuelven un global frente al estado inyectado en la raíz de composición. El envoltorio sigue siendo global. No se adopta.
* Variable de control para dependencias secuenciales frente al test de la costura. El AC demuestra el orden. La bandera de "paso ya corrido" no se añade por el capítulo.
* Contador de seguridad en toda recursión o todo bucle frente al caso base ya obvio y probado. El tope entra cuando la parada puede no llegar.

## Huecos que las Partes III y IV dejaron y la Parte V cierra

* Estrategia de errores del sistema, nombrada en el SDD. Cerrada en `templates/sdd.md`. El `default` de un `case` la obedece.
* Depuración como método. Cerrado como guía en el capítulo 23.
* Colaboración, pruebas del desarrollador, refactor y afinado. Cerrados como guía en los capítulos 21, 22, 24, 25 y 26.
* Layout y comentarios. Capítulos 31 y 32. El formateador y la regla de no parafrasear el código siguen vigentes.

---

## Capítulo 20 — La calidad se decide en el proceso

Quien usa el sistema ve las características externas: corrección, usabilidad, eficiencia, confiabilidad, integridad, adaptabilidad, exactitud y robustez. Quien lo construye ve además las internas: facilidad de cambio, flexibilidad, portabilidad, reuso, lectura, capacidad de probarse y de entenderse. Las externas son las únicas que le importan a quien usa el producto. Las internas importan porque sin ellas no se sostiene la corrección ni la confiabilidad. Empujar una suele mover otra. Corrección y robustez se estorban: ya quedó dicho en el capítulo 8. La clase de software del capítulo 3 elige cuál manda en esta feature. La eficiencia entra solo si un AC la nombra.

Ninguna técnica, sola, pasa de una moda de cerca del 75 % de defectos detectados. El promedio de las técnicas ronda el 40 %. La prueba unitaria tiene una moda del 30 % y la de integración del 35 %. La inspección formal de código tiene una moda del 60 % (Jones 1986, 1996; Shull y otros 2002). Una organización que solo prueba se queda cerca del 85 % de remoción. Las que combinan técnicas pasan del 95 % (Jones 2000). Myers (1978) dio el mismo programa, con 15 defectos conocidos, a programadores de unos once años de oficio: encontraron de 1 a 9, con media de 5. La prueba y la lectura encuentran defectos distintos. Hacen falta las dos.

El arnés ya las combina: el sí del usuario al spec, el test de la costura, el revisor aislado y el postmerge. No se añade un plan de aseguramiento al estilo IEEE ni un porcentaje de remoción como gate. La prueba de sistema independiente, la beta y la aceptación del cliente siguen fuera.

El principio general del capítulo: mejorar la calidad baja el costo de desarrollo. El retrabajo y la depuración se llevan cerca de la mitad de un ciclo ingenuo. En 50 proyectos y casi 3 millones de líneas, más aseguramiento se asoció con menos defectos y sin subir el costo total (Card 1987, NASA SEL). Los proyectos con menos defectos tuvieron los calendarios más cortos (Jones 2000). En el estudio de DeMarco y Lister (1985), 166 programadores escribieron el mismo encargo: quienes tardaron el tiempo mediano produjeron más defectos. Los más rápidos y los más lentos produjeron menos. Ir más despacio no compra calidad. Prevenir el defecto, en el requisito, en el diseño y en el test de antes, sí. El rol 0, el test-first y el review son esa reasignación. No es una fase nueva al final.

---

## Capítulo 21 — Mostrarle el trabajo a otro

Quien escribe no ve algunos de sus propios fallos. Otro no tiene los mismos puntos ciegos. El SEI midió de 1 a 3 defectos por hora en diseño y de 5 a 8 en código (Humphrey 1997). Toda la colaboración del capítulo formaliza el gesto de enseñar el problema y, a mitad de la frase, verlo uno mismo.

| Práctica del capítulo | Qué mide | En el arnés |
| --- | --- | --- |
| Pair | Calidad parecida a la inspección, con un costo del orden del 10 % al 25 % por encima de ir solo y una reducción de tiempo del orden del 45 % en los informes tempranos (Shull y otros 2002; Boehm y Turner 2004). | Ya elegido en el capítulo 4. Automático en stack CALPIL. `--pair` si se pide. Estas cifras no reabren la política. |
| Inspección formal | Lista, preparación, roles, mejora del proceso. Encuentra más que un walk-through. IBM: una hora de inspección evitaba unas 100 de trabajo relacionado. Raytheon bajó el retrabajo de cerca del 40 % a cerca del 20 % (Haley 1996). | No se adopta el ritual Fagan: sin moderador, sin formularios, sin métrica de defectos por hora. |
| Review técnico informal | Alguien lee el trabajo con un propósito. | El revisor aislado, sobre spec y diff, sin haber escrito el código. Tope de dos rondas. Un menor no abre ronda. |
| Lectura en voz alta, o dejarlo y volver | El propio autor ve el fallo al explicarlo. | La parada de pair cuando el diseño no estaba en el plan. |

La inspección de todos los requisitos, de toda la arquitectura y de cada diseño crítico que el capítulo recomienda para un programa de calidad alta es, en el arnés, el ritual de rol 0 y el sí al spec. No es una reunión con roles. El revisor no es el autor. Eso conserva lo que la inspección aporta (otro par de ojos, defectos distintos de los del test) y deja fuera el aparato que el arnés no tiene.

---

## Capítulo 22 — La prueba del que escribe

La prueba del desarrollador cubre la unidad, el componente y la integración que él mismo puede ejecutar. La de sistema, la beta, la de aceptación, la de estrés y la de usabilidad de un equipo aparte quedan fuera, igual que en el capítulo 1. Caja negra: no se ve el interior. Caja blanca: se ve. Quien escribió el código hace la segunda. Las dos tienen huecos. El capítulo se concentra en la blanca.

McConnell recomienda escribir los casos antes del código. No cuesta más: cambia el orden. El defecto se ve antes, el requisito flojo se atasca al intentar escribir el test, y los casos guardados sirven otra vez al final. Lo llama una de las prácticas más útiles de la década, y no un remedio total, porque la prueba del autor tiene límites. Eso coincide con el TDD vertical. El primer ejecutable sigue siendo el rojo de la costura.

Límites que el capítulo marca, y cómo se traducen:

* El autor prueba que funciona y se olvida de cómo se rompe. Una organización inmadura tiene unos cinco tests limpios por cada uno sucio. Una madura, al revés, y no lo consigue borrando los limpios sino multiplicando los sucios (Beizer, en Johnson 1994). En la costura, el AC nominal no basta si el dato puede venir vacío, repetido, en el borde o mal formado. Esos casos son del mismo AC, no una feature nueva.
* Quien prueba cree cubrir cerca del 95 %. En el mejor caso ronda el 80 %, en el peor el 30 %, y el promedio anda por el 50 % al 60 % (Beizer). Cubrir enunciados no alcanza. Cubrir ramas es mejor y tampoco es un gate. El revisor mira si los bordes que el AC nombra están en el test. No pide un porcentaje.
* La base estructurada (un caso por cada decisión, el mínimo que recorre los caminos) y el flujo de datos suman casos dentro de la costura. No autorizan un test por método privado ni un TDD horizontal.
* El valor esperado sale del AC o de una cuenta hecha a mano con números limpios. Un esperado calculado con la misma fórmula que el código, o con una cifra incómoda que el autor también puede sumar mal, es un defecto del test. El capítulo advierte que el dato de prueba tiene más densidad de errores que el código que prueba. Cazar eso no mejora el producto.
* Los defectos se agrupan. Cerca del 80 % está en el 20 % de las clases o rutinas (Endres, Gremillion, Boehm, Shull). Cerca del 50 % está en el 5 % de las clases (Jones 2000). En IMS, reparar 31 de 425 clases bajó los defectos reportados diez a uno y el mantenimiento cerca de un 45 %. Si la misma clase vuelve a fallar, se rediseña. No se le suma otro parche. La lección registra la clase de fallo.
* La regresión es automática: `verify` en el worktree y el postmerge en la rama destino. Un verde que no engancha ningún test no cuenta.

El andamiaje del capítulo, para probar una rutina aislada, no autoriza un mock de la lógica. `F-1` sigue sin mocks. El adaptador en memoria que el stack ya prescribe es la segunda implementación del puerto, no un sustituto del caso de uso.

---

## Capítulo 23 — Encontrar la causa

Depurar es diagnosticar. No mejora la calidad por sí mismo. La calidad se construye antes: requisito, diseño, código. Depurar es el último recurso. En algunos proyectos se lleva hasta la mitad del tiempo, y la diferencia entre quien depura bien y quien depura mal es de al menos diez a uno. Encontrar el defecto, y entenderlo, es cerca del 90 % del trabajo. El arreglo es el resto.

El defecto no se cuela solo. Lo puso quien escribió. Asumir que es de otro alarga la búsqueda. El método del capítulo:

1. Estabilizar. El fallo ocurre de la misma manera cada vez. En el arnés, el test de la costura que está rojo es esa estabilización. Si no se puede repetir, todavía no hay un defecto que arreglar: hay un experimento que diseñar.
2. Localizar la causa. Reunir el dato que lo produce. Formar una hipótesis que explique ese dato, no solo el primer síntoma. Diseñar un experimento que la confirme o la descarte: el mismo test, un caso vecino, o una lectura del código. Si el dato no cabe en la hipótesis, no se tira el dato. Se cambia la hipótesis.
3. Arreglar la causa, no el síntoma. Un parche que hace pasar este caso y deja el mecanismo intacto no es el arreglo.
4. Probar el arreglo. El test que estaba rojo pasa, y los que ya pasaban siguen pasando. No se debilita la aserción para conseguir el verde.
5. Buscar el mismo defecto al lado. El error que se agrupó en un sitio suele tener un hermano.

Reglas que evitan empeorar el código: una hipótesis a la vez, un cambio a la vez, el aviso del compilador en el nivel más estricto del stack se atiende antes de cazar lo sutil. Adivinar y recompilar deja el programa peor que al empezar.

El depurador, el chequeo de memoria y el log son herramientas para reunir el dato del paso 2. No son la evidencia del AC. El capítulo 4 ya excluyó el paso obligatorio por el depurador antes de integrar. Esa exclusión se mantiene. Usar la herramienta durante la búsqueda no la convierte en gate.

La parada de pair a los dos intentos sin verde es el freno contra la hipótesis única y el callejón. Esos dos intentos son dos experimentos. Al segundo fallo se vuelve al último verde y se replantea, que es el "repetir el método" del capítulo cuando la hipótesis quedó descartada. No es un tercer parche al azar.

---

## Capítulo 24 — Que el cambio mejore el interior

El código cambia durante la construcción, no solo después del release. Codificar, depurar y probar la unidad se llevan del 30 % al 65 % del esfuerzo. Si fuera un trámite, bastaría el 20 % o el 30 %. Los requisitos se mueven cerca de un 1 % a un 4 % al mes (Jones 2000) y el código se mueve con ellos.

La regla cardinal: la evolución mejora la calidad interna. El refactor, en la definición de Fowler que el capítulo adopta, cambia la estructura para que se entienda y se modifique más barato, sin cambiar el comportamiento observable. Los dos sombreros ya separan ese cambio del cambio de conducta. El commit de `refactor:` no toca el test. El commit de la feature no aprovecha para "ordenar".

Los olores que el capítulo lista (duplicado, rutina larga, bucle hondo, cohesión pobre, interfaz que ya no abstrae, lista de parámetros larga, cambios que siempre tocan las mismas clases distantes, subclase que usa poco del padre) tienen dueño en [`patrones-gof-y-refactoring.md`](patrones-gof-y-refactoring.md). No se copian aquí. "Más larga que una pantalla" choca con el largo ya cerrado en el capítulo 7: se parte si hay dos responsabilidades, no si el número de líneas incomoda.

El refactor seguro del capítulo cabe en el ciclo que ya existe:

* Chico, y de uno en uno. Se recompila y se vuelve a probar antes del siguiente.
* Con la red de tests verde. Sin red, no es refactor: es una reescritura, y esa pide un AC o una enmienda.
* El comportamiento observable no se mueve. Si el AC deja de cumplirse, el cambio era de feature.
* La oportunidad buena es durante la construcción, con el test todavía fresco. Dejarlo para "después del release" es dejar que la calidad interna baje.

El objeto nulo, para no preguntar por ausencia en cada llamada, es una opción del capítulo. Se usa cuando el caso ordinario puede definirse fuera de la existencia, que es la regla de Ousterhout. No se instala un Null Object por el catálogo.

---

## Capítulo 25 — Medir antes de afinar

Afinar el código es una forma de ir más rápido, y suele no ser la primera. Más pecados se cometen en nombre de la eficiencia, sin conseguirla, que por cualquier otra causa (Wulf). El orden del capítulo, de mayor palanca a menor:

1. Requisitos y arquitectura. Un `D-n` que elige el almacén, el corte del servicio o el momento del cálculo mueve más que un bucle reescrito.
2. El algoritmo y la estructura de datos. El orden de magnitud está en CLRS. Un \(O(N^2)\) o un \(N+1\) se corrige ahí, antes de tocar el cuerpo del bucle.
3. El compilador y sus opciones. El stack ya las trae. No se reescribe en ensamblador lo que el compilador hace.
4. El afinado de código, al final, y solo en el punto caliente.

El principio de Pareto: el 20 % de las rutinas consume el 80 % del tiempo (Boehm). Knuth encontró, con un perfilador de líneas, que la mitad del tiempo de su programa estaba en un 4 % del código, y lo mejoró en menos de una hora después de medir. Bentley cuenta un programa de unas mil líneas que pasaba el 80 % del tiempo en un sitio. Medir, cambiar ese sitio, volver a medir.

La experiencia de otra máquina, otro lenguaje u otro compilador no transfiere. La tabla de costos relativos del capítulo (llamada, aritmética, acceso a arreglo) es de su entorno y el propio texto dice que cambió desde la primera edición y que hay que volver a medirla. No se usa para decidir en 2026.

Sin un AC que nombre un presupuesto de tiempo o de memoria, no se afina. Sin una medición de antes y de después, el cambio es una apuesta: el daño a la lectura es seguro y la ganancia no. Cada optimización se vuelve a perfilar. Una que ayudó con un dato puede empeorar con otro.

---

## Capítulo 26 — Las técnicas, solo con el perfil en la mano

El capítulo recorre lógica, bucles, transformaciones de datos, expresiones, rutinas y el salto a un lenguaje de más bajo nivel: salir temprano de un caso, desenrollar, bajar la fuerza de una operación, aplanar un arreglo, guardar un valor ya calculado, reescribir en línea, pasar a punteros. Los resultados varían con el lenguaje, el compilador, la librería y las opciones. Sin medir esa combinación, no se sabe si ayuda o empeora. La primera idea casi nunca es la mejor, y tampoco la segunda hasta que el perfil lo diga.

El propio cierre del capítulo baja el tono: en esta edición hubo que repetir muchas pruebas de un millón a cien millones de veces para ver una diferencia. En un programa de escritorio o en un servicio de negocio, esa diferencia no se nota. Sigue importando donde hay un presupuesto duro de tiempo o de espacio. El afinado cambia complejidad, lectura y mantenimiento por velocidad, y obliga a reprofilar siempre.

Esas técnicas no entran al sombrero de feature ni al de refactor. Entran, de una en una, cuando se cumplen las tres: el AC pide el presupuesto, el perfil señala el punto, y la medición de después muestra la mejora. La aritmética de punteros y el ensamblador a mano quedan fuera de estos stacks. El arreglo de un \(N+1\) o de un algoritmo cuadrático no es afinado de código: es el paso 2 del capítulo 25, y ya tiene dueño en CLRS.

---

## Matriz de la Parte V

| Fase | Criterio |
| --- | --- |
| Rol 0 y spec | La clase de software dice qué característica externa manda. El sí al spec es la revisión del diseño. No hay un plan de calidad aparte. |
| Implementer, test | Primero el caso de la costura, en rojo. Nominal, borde y dato malo del mismo AC. El valor esperado no sale de la fórmula del código. Sin mock de la lógica. |
| Implementer, depuración | El rojo estabiliza el fallo. Una hipótesis, un cambio, el test como experimento. A los dos intentos, volver al verde y replantear. Buscar el defecto hermano. |
| Implementer, refactor | Con la red verde, de a uno, sin mover el comportamiento. Commit distinto del de la feature. Si la misma clase acumula defectos, se rediseña. |
| Implementer, afinado | Solo con AC de presupuesto y con medición de antes y de después. Antes, el algoritmo y el acceso a datos. |
| Revisor | Defectos que el test no ve: el borde que falta, el test que calcula el esperado con la misma lógica, el parche que no toca la causa, el refactor mezclado con la feature, el micro-afinado sin perfil. |
| Cierre | `verify` y postmerge son la regresión. La prueba de sistema independiente sigue fuera. |

## Conflictos cerrados en esta parte

* Inspección formal con roles, listas y métricas frente al revisor aislado y el tope de dos rondas. Gana el arnés. Se conservan el otro par de ojos y la separación entre quien escribe y quien revisa.
* Cubrir cada enunciado o cada rama de cada rutina frente al test de la costura. Gana la costura. Los bordes y el dato malo se prueban ahí. El porcentaje de cobertura no es gate.
* Andamiaje y dobles de prueba frente a `F-1` sin mocks. El adaptador en memoria del stack es el puerto. Un mock de la lógica no se añade.
* Paso obligatorio por el depurador frente a la evidencia del test. El depurador puede reunir datos. No demuestra el AC y no es requisito de cierre.
* "Partir toda rutina más larga que una pantalla" (capítulo 24) frente al módulo profundo. Sigue cerrado como en el capítulo 7.
* Catálogo de micro-afinados (desenrollar, punteros, bajar la fuerza, ensamblador) frente a medir y frente a CLRS. Sin AC de presupuesto y sin perfil, no se aplican. La tabla de costos del libro no elige técnica en 2026.

## Huecos que la Parte V dejó y la Parte VI cierra

* Estrategia de errores del sistema, nombrada en el SDD. Cerrada en `templates/sdd.md`.
* Layout y comentarios. Capítulos 31 y 32. El formateador y la regla de no parafrasear el código siguen vigentes.
* Tamaño, gestión, integración y herramientas. Cerrados como guía en los capítulos 27 a 30.

---

## Capítulo 27 — El tamaño no escala en línea recta

Hacer el sistema diez veces más grande no lo hace diez veces más caro. El ejemplo del capítulo: un paquete de 25.000 líneas, hecho en 20 personas-mes, con 500 errores en campo. La versión de 250.000 líneas no cuesta 10 veces. Cuesta del orden de 30 veces el esfuerzo total, unas 25 veces la construcción y unas 40 veces la arquitectura y la prueba de sistema, y trae unas 15 veces los errores, o más. Es una ilustración de cómo crece el trabajo, no una fórmula para estimar una feature.

Los caminos de comunicación crecen con el cuadrado de la gente. Dos personas tienen un camino. Cinco, diez. Un proyecto de 50 programadores tiene al menos unos 1.200. Cada camino de más es un lugar donde el requisito se desalinea. El recorte sensato es limitar quién habla con quién: el contrato del SDD entre repos, no una conversación de todos con todos. El multi-repo existe para eso. No se añade un método de comunicación encima.

| Tamaño | Qué cambia | En el arnés |
| --- | --- | --- |
| Por debajo de unas 2.000 líneas | Manda la habilidad de quien escribe (Jones 1998). Cerca del 75 % de los errores son de construcción. | Una feature, aunque viva en un sistema grande. El spec sigue corto. |
| Mediano | La construcción baja hacia la mitad del esfuerzo. Arquitectura, integración y prueba de sistema crecen más rápido que el código. | El rol 0, una vez por producto. Cada `F-n` sigue siendo construcción. |
| Grande, hacia cientos de miles de líneas | La densidad de defectos sube: el doble de líneas trae más del doble de errores. En algunos sistemas de 500.000 líneas la construcción sigue causando hasta el 75 % (Grady 1987). | Sube la formalidad del producto (SDD, enmienda, postmerge). No sube el número de AC. |

Las bandas de densidad del capítulo (de 0–25 errores por mil líneas por debajo de 2.000, hasta rangos más anchos por encima de 64.000) describen proyectos enteros. No se usan para predecir los defectos de una feature ni para poner un cupo.

La productividad en un proyecto chico puede ser de 2 a 3 veces la de uno grande, y de 5 a 10 veces entre el más chico y el más grande. La tabla de líneas por persona-año (de unos miles a unas decenas de miles, según el tamaño) depende de cómo se cuente la línea, del lenguaje y de si entra el tiempo de quien no programa. No estima el arnés. Un equipo de dos rindió un 39 % más que uno de tres en el experimento de Boehm, Gray y Seewaldt (1984). Eso no cambia la política de pair.

Boehm y Turner (2004) vieron el costo más bajo con cerca de un 5 % del esfuerzo en requisitos y arquitectura alrededor de 10.000 líneas, y con un 15 % a un 20 % alrededor de 100.000. El 10 % a 20 % del capítulo 3 es esa banda, gastada una vez en el rol 0, según el tamaño del producto. Una feature no abre su propio presupuesto de arquitectura.

Crece más que la línea: comunicación, planificación, gestión, requisitos, diseño funcional, contratos entre partes, arquitectura, integración, quita de defectos, prueba de sistema y documentos. Esas actividades viven en el PRD, el SDD, `close` y el postmerge. La feature se mantiene chica para que no las arrastre.

En cualquier tamaño siguen valiendo las mismas cuatro: código con disciplina, que otro lea el diseño y el diff, herramientas que de verdad se usan, y un lenguaje de alto nivel. Ya están elegidas.

---

## Capítulo 28 — Controlar el cambio sin parar el trabajo

El estándar lo pone quien el equipo respeta por el oficio, no un manual bajado desde la gestión. Si el grupo resiste una norma rígida, el capítulo ofrece guías flexibles, una colección de ejemplos y la revisión, que con el tiempo alinea el estilo. El libro mismo pide que no se use para justificar un reglamento rígido.

En el arnés esa norma es el manifiesto del stack, instalado por `stack.py normalizar` antes de las features de negocio. No se escribe un manual de estilo por producto. El revisor cita el stack. No inventa otro.

La gestión de configuración es el control del cambio: saber qué piezas existen, evaluar un cambio propuesto, y poder volver a una copia que sí funcionaba. Cubre requisitos, código, documentos y datos de prueba. Sin eso, se escribe código para un requisito que ya no existe, dos personas pisan la misma rutina, y la versión probada no es la que se integró. El exceso también para el trabajo: la forma segura de evitar choques es no dejar cambiar nada.

Dos niveles, y los dos ya existen:

| Qué cambia | Control | Qué no se hace |
| --- | --- | --- |
| Problema, objetivo o decisión de arquitectura | `producto.py aprobar`, con el sí. | Reescribir el PRD o el SDD dentro de la feature. |
| Un AC con evidencia encima | `gate.py enmienda`. Invalida review y verify. | "Arreglar el spec en el diff". |
| Código de la feature | Worktree y rama propios. `verify` antes de `close`. | Dos construcciones editando el mismo árbol. Un estimado de pasillo, de los que fallan por un factor de dos o más. |

El worktree es el aislamiento que el capítulo pide para que el cambio de uno no pise el del otro. La copia que se integró es la que pasó `verify`. Si hace falta volver, git tiene la anterior. En un trabajo de una persona el capítulo basta con copias periódicas. En uno de cincuenta pide un esquema completo. El arnés no abre un departamento de configuración: git, el sello del documento y la enmienda cubren los dos extremos. Apretar más sería el exceso que el capítulo advierte.

Estimar es difícil. El desarrollador se queda corto un 20 % a un 30 % (van Genuchten 1991). Un número dicho al pasar se equivoca por un factor de dos o más. El capítulo pide varios métodos, apretar el número a medida que se sabe más, y guardar el estimado contra lo que ocurrió. El arnés no estima en personas-mes ni guarda una libreta de estimados. El tamaño de la feature es el de Orosz: cabe en unos días, con un plan vertical de hasta cinco pasos. Si no cabe, se parte en otra candidata. Esa es la corrección del estimado. No es un documento nuevo.

Medir algo gana a no medir. Lo que el arnés ya mide es el test de la costura, el postmerge y la lección. No se añade un tablero de líneas ni de defectos por hora.

La gente del capítulo, oficinas, motivación y cómo hablar con quien gestiona, no cambia los roles. Quien decide sigue siendo el usuario. No se crea un proceso de gestión de personas.

---

## Capítulo 29 — Integrar en rebanadas, no de un golpe

El estadio se cayó durante la obra porque el orden de construcción no aguantaba el peso de ese paso, aunque el edificio terminado sí habría aguantado. El software igual: si nada corre hasta que todo corre, el conteo de fallos parece imposible y el avance no se ve. El orden de integración es el orden en que se diseñan, se escriben y se prueban las clases.

La integración por fases, el "big bang", junta todo al final. Solo se justifica en un programa minúsculo, de dos o tres clases. En cualquier otro, la integración incremental es mejor. El fallo nuevo está en lo que acaba de entrar o en la junta con lo que ya corría. El sistema se puede usar en cada paso.

| Estrategia del capítulo | Qué aporta | En el arnés |
| --- | --- | --- |
| De arriba abajo, pura | Prueba pronto el control. Exige stubs en cada nivel, y el orden rígido por capas no se cumple en la práctica. | No. El stub que se queda es el mock que `F-1` prohíbe. |
| De abajo arriba, pura | Prueba pronto las interfaces de sistema. Deja el diseño de arriba para el final, y el detalle de abajo acaba mandando. | No es el plan de una feature. El puerto del stack puede existir antes. La costura pública se prueba igual desde el primer AC. |
| Sándwich | Arriba y abajo primero, el medio después. | No es un plan distinto. El medio entra en la rebanada que lo necesita. |
| Por riesgo | Lo más incierto primero. | Si un `D-n` está en duda, la candidata que lo toca va antes. No es una fase aparte. |
| Por feature | Una función identificable por vez. Casi sin andamiaje. Cada paso añade algo que se puede mostrar. Encaja con objetos. | Esta es `F-n`. El incremento puede tener varias clases. Se prueban en la costura antes de `close`. |
| En T | Una rebanada de punta a punta primero, para comprobar el diseño. Después el ancho. | Esta es `F-1`, el esqueleto real, y luego el resto de las candidatas. |
| Rebanada vertical | De arriba abajo, pero por una función, no por toda una capa. | El mismo corte. El nombre del capítulo y el de [`vertical-slice.md`](vertical-slice.md) dicen lo mismo. |

El esqueleto del capítulo a veces necesita un poco de andamiaje, o partes que no operan hasta que llega la feature. El arnés no: `F-1` conecta la costura de verdad. Un hueco que nadie reemplaza no cuenta como integrado.

El build diario con prueba de humo compila todo cada día y lo recorre de punta a punta. Si ayer corría y hoy no, el fallo está en lo que entró. El build roto se arregla antes de seguir. La prueba de humo crece con el sistema y se automatiza. Quien va a integrar prueba en privado antes de tocar el árbol común.

Eso ya tiene forma, sin un cron nuevo:

* La prueba privada es `verify` en el worktree, antes de `close`. El código que no pasa no entra en la rama de integración.
* La prueba de humo del conjunto es `postmerge_medido.py` sobre esa rama. Un rojo ahí es el build roto del capítulo: se entiende y se corrige antes de apilar otro cierre encima.
* La prueba crece porque cada feature deja sus tests de costura. No hace falta un guion de humo paralelo que se pudra.
* El capítulo pide integrar al menos cada día. Una feature que cabe en unos días se integra al cerrarla, no cada tarde. Partirla es la defensa contra el árbol que se desalinea. Un merge diario a la rama común no se añade como ritual.

En multi-repo, cada repo integra en su rama. El contrato entre repos está en el SDD. Una feature que cruza repos sigue siendo una `F-n`, con el orden en el plan vertical. No se inventa un build diario que levante todos los servicios a la vez.

---

## Capítulo 30 — Las herramientas que sí se usan

Un juego de herramientas bueno, y conocerlo, puede subir la productividad un 50 % o más (Jones 2000; Boehm y otros 2000). El 20 % de las herramientas hace el 80 % del uso (Boehm 1987). Faltar una de esas pocas duele más que faltar diez que no se abren. El capítulo habla de clases de herramienta, no de marcas: las marcas envejecen antes de que se seque la tinta.

El 20 % del arnés, el que se usa en cada feature:

| Clase del capítulo | Qué es aquí |
| --- | --- |
| Versión y diff | Git y el worktree. Comparar con lo último que funcionaba es `git diff`, no un comparador aparte. |
| Edición, formato, aviso del compilador | El IDE de quien escribe y el formateador del stack. El review no debate la sangría. |
| Build | El del stack. No se instala un `make` genérico encima. |
| Prueba | El test runner del stack, enganchado por `verify` y por el postmerge. |
| API vigente | Context7 cuando la librería importa. La ola temprana se nombra en el SDD. |
| Calidad de arquitectura | `check-architecture.py` del stack. |

Lo que el checklist del capítulo pregunta y el arnés no adopta: un depurador interactivo como requisito, generadores de tests, monitores de cobertura, perturbadores del sistema y un tracker de defectos distinto de la feature y de la lección. La cobertura y el depurador ya quedaron fuera como gates en la Parte V.

Diseñar no pide una herramienta nueva. El diagrama del SDD es Mermaid. Un UML aparte no entra.

Construir una herramienta propia vale cuando automatiza una repetición del proyecto. El arnés es esa herramienta, hecha una vez. Una feature no se detiene a fabricar un script privado. Si el stack ya tiene el gancho, se usa ese.

El cierre del capítulo: las herramientas quitan trabajo tedioso y siguen cambiando lo que significa programar. No quitan el diseño, la prueba ni la revisión.

---

## Matriz de la Parte VI

| Fase | Criterio |
| --- | --- |
| Rol 0 | El presupuesto de requisitos y arquitectura es del producto, una vez, y crece con el tamaño del sistema. Una feature no lo repite. |
| Alta de `F-n` | El orden de las candidatas es el orden de integración. Lo incierto que un `D-n` dejó abierto va antes. `F-1` es la rebanada en T, real. |
| Worktree | Aísla el cambio. Dos features no editan el mismo árbol. |
| `verify` y `close` | La prueba privada antes de tocar la rama común. Sin verde no hay integración. |
| Postmerge | La prueba de humo del conjunto. Un rojo se corrige antes de apilar otro cierre. |
| Multi-repo | Cada repo integra en su rama. El contrato entre ellos está en el SDD. |
| Herramientas | Git, stack, gates, Context7. Sin lista de compras de 2004 y sin script nuevo por feature. |

## Conflictos cerrados en esta parte

* Diez veces más líneas implican treinta veces más esfuerzo, y las tablas de líneas por persona-año, frente a estimar una feature. Esas cifras describen proyectos enteros. Una feature se parte si no cabe. No se estima en personas-mes.
* El 5 % o el 15–20 % de Boehm y Turner frente al 10–20 % del capítulo 3. Es el mismo presupuesto del rol 0, según el tamaño del producto. No es un porcentaje por feature.
* Integrar de arriba abajo con stubs, o de abajo arriba por capas, frente a `F-1` sin mocks y al corte vertical. Gana la rebanada real. El andamiaje del esqueleto no se adopta.
* Build y humo cada día, con check-in al menos diario, frente a integrar al cerrar la feature. `verify` es la prueba privada y el postmerge es el humo del conjunto. No se añade un cron ni un merge diario.
* Manual de estilo impuesto por la gestión, y el propio libro como reglamento, frente al manifiesto del stack. Gana el stack.
* Cobertura, generadores de tests y depurador obligatorio, otra vez, en el checklist de herramientas. Siguen fuera. La evidencia es el test de la costura.

## Huecos que la Parte VI dejó y la Parte VII cierra

* Estrategia de errores del sistema, nombrada en el SDD. Cerrada en `templates/sdd.md`.
* Layout, comentarios, carácter y temas de oficio. Cerrados como guía en los capítulos 31 a 35.

---

## Capítulo 31 — La forma muestra la estructura

El layout no cambia la velocidad ni la memoria. Cambia si alguien puede leer el código, revisarlo y modificarlo meses después. El teorema del capítulo: un buen layout muestra la organización lógica. Se juzga por exactitud, consistencia, lectura y mantenimiento. Que se vea bonito viene después. Si la estructura es clara, el aspecto sale solo.

La herramienta es el espacio en blanco. La sangría sigue el anidamiento. Una línea en blanco separa un párrafo de código del siguiente. Si la sangría dice que tres enunciados están dentro del `if` y solo uno lo está, el layout miente, y ese es el defecto. El detalle de llaves, de dónde cortar la línea y de cuántos espacios es la guerra de religión que el propio capítulo reconoce. El formateador del stack la terminó. Se corre al escribir. El revisor no comenta el estilo que la herramienta ya fijó. Si una mano y el formateador discrepan, gana el formateador. No se reindenta a mano para "que se vea como en el libro".

Eso se decide una vez, en `stack.py normalizar`, antes de las features. No se reabre por feature ni se vota en el review. La programación literaria de Knuth, mezclar el ensayo y el código en un solo tejido, no se adoptó. El spec dice qué se prometió. El código dice cómo está hecho.

---

## Capítulo 32 — El comentario que el código no puede decir

El código que corre es la descripción que más probabilidad tiene de seguir al día. Por eso lo importante que solo vive en un documento aparte se desfasa. En el arnés, el qué prometido está en el PRD, el SDD y el spec. El cómo está en el código. La evidencia de que el AC se cumplió está en `docs/impl-<id>.md`, con cita `archivo:linea`. No se adopta la carpeta de unidad del IEEE ni un encabezado con nombre, correo y teléfono del autor. El autor está en git.

El código bueno es su mejor documentación. Si hace falta un comentario largo para entenderlo, el primer movimiento es mejorar el código: el nombre, el corte, la tabla, el retorno temprano. El comentario entra cuando dice algo que el código no puede decir.

| El comentario | Cuándo se queda | Cuándo se borra |
| --- | --- | --- |
| Intención | El porqué de una decisión que no es obvia: un orden, un límite, una unidad, la fuente de un algoritmo. | Cuando repite el nombre de la función. |
| Resumen | Un bloque cuyo conjunto no se lee en las primeras líneas. | Cuando parafrasea el `if` de abajo. |
| Contrato | Una precondición o un invariante que el tipo no expresa. | Cuando el tipo o el test de la costura ya lo dicen. |
| Marcador (`TODO`, `FIXME`) | Mientras la rutina está a medias, en el worktree. | En el cierre. Si queda trabajo, el AC no está cumplido. |
| Final de bloque | Casi nunca, con las sangrías del formateador y los bloques cortos. | "fin del if" al lado de un `if` de cuatro líneas. |

Hecho mal, el comentario estorba: se desfasa, y el lector no sabe si creer el texto o el código. Si discrepan, manda el código y se corrige o se borra el comentario. El revisor puede citar esa discrepancia. No es un gate de densidad de comentarios.

El capítulo 9 quería convertir el pseudocódigo en comentarios. Ya quedó cerrado: el pseudocódigo es el pensamiento de antes del primer rojo. Se conserva la frase que dice el porqué. El resto, que repite el cómo, no se deja. La regla del implementer es esta: contratos, invariantes e intención. Prohibido parafrasear la sintaxis.

Un estudio que el capítulo cita: quien mantiene dedica del 50 % al 60 % del tiempo a entender el código que tiene que tocar, y un programa promedio pasa por unas diez generaciones antes de reescribirse (Parikh y Zvegintzov 1983; Thomas 1984). Por eso el nombre y la costura pesan más que el volumen de comentarios. El código del repo es público aunque hoy lo escriba una sola persona. Lo privado que después se comparte se vuelve público sin avisar.

---

## Capítulo 33 — El oficio es un hábito

El material de la programación es el intelecto de quien escribe, y ese cráneo no alcanza para un programa mediano. Dijkstra, en "The Humble Programmer": los mejores aceptan lo chico que es el cerebro y se organizan para compensarlo. Los peores no lo aceptan, y el ego les impide mejorar. La humildad aquí no es un rasgo que se califique. Es usar las prácticas que existen porque uno se equivoca: el revisor, el test, la parada a los dos rojos, partir el problema.

La inteligencia bruta, los años, la persistencia y el coraje ayudan y también estorban. La persistencia que no suelta una hipótesis falsa es el callejón del capítulo 23. El coraje que empuja otro parche después de dos rojos es el hábito equivocado. Importa más el compromiso con la práctica que el talento. No es un criterio de contratación ni un perfil del agente. Es la razón de que los gates no dependan del ánimo del día.

| Hábito del capítulo | En el arnés |
| --- | --- |
| Curiosidad | Leer el código que ya está y la API vigente (Context7, el doc del stack) antes de inventar desde el recuerdo. |
| Honestidad intelectual | Decir qué AC no quedó. No debilitar el test para verlo verde. Prosa sin cita no es evidencia. |
| Comunicación | Español, frases cortas, el usuario decide. El diff es el mensaje hacia quien lee después. |
| Creatividad y disciplina | Probar más de un diseño es la creatividad. El gate, el plan vertical y los dos sombreros son la disciplina. Las dos. |
| Pereza ilustrada | Automatizar lo repetido. `verify` y el postmerge existen para no recorrer la prueba a mano. No fabricar una herramienta por feature. |
| Cooperación | El revisor no es el autor. El pair existe para el punto ciego, no para lucirse. |

---

## Capítulo 34 — Los temas, ya elegidos

Este capítulo junta lo que las partes anteriores dejaron suelto. No abre un método nuevo.

* Manejar la complejidad. Es el imperativo del capítulo 5. El módulo profundo, el alcance corto y la barricada existen para que el cráneo no cargue el programa entero.
* Elegir el proceso, y después no reabrirlo en cada feature. El arnés ya eligió. La clase de software del capítulo 3 es la única razón para subir la formalidad.
* Escribir para personas primero. El lector del diff es la audiencia. Unas diez generaciones van a leerlo. "Solo lo veo yo" no aplica a un repo compartido.
* Programar hacia el lenguaje, no dentro de lo que el framework sugiere. Si la regla del stack y el default discrepan, gana el stack. Capítulo 4.
* Las convenciones liberan atención. El nombre, el formateador y los límites del stack se cumplen para no gastar cabeza en lo arbitrario.
* Hablar el dominio del problema. El PRD está en lenguaje de quien usa el sistema. El tipo del dominio no se sustituye por el tipo del transporte en el núcleo.
* Mirar las piedras que caen. "Esto está muy tramposo" es una señal, no un elogio. La misma clase que acumula fallos se rediseña. Mucho código en un día, sin un verde de costura, no es avance. Una métrica disparada (McCabe, fan-out, un postmerge rojo) hace dudar de la calidad. No dicta el arreglo por sí sola.
* Iterar. Otra vez el diseño, otra vez la rebanada, el sombrero de refactor con la red verde.
* Soltar la religión. Las técnicas de este archivo son heurísticas. Ninguna ocupa el 100 % de la caja. Experimentar, en el nivel que toca: dos alternativas en un `D-n`, un perfil si el AC pide velocidad, no un proceso nuevo a mitad de la feature.

---

## Capítulo 35 — Dónde seguir leyendo

Hay más escrito de lo que cabe en un proyecto, y casi todos los errores de hoy ya los cometió alguien. Los manuales de un lenguaje, un sistema o una librería duran cerca de un proyecto. No se copian a esta guía. La API vigente se consulta en Context7 o en el doc del stack en el momento de usarla.

El núcleo que el arnés ya separó por tema, y que este archivo no reescribe:

| Tema | Dónde está |
| --- | --- |
| Módulos, complejidad, design it twice | [`filosofia-diseno-ousterhout.md`](filosofia-diseno-ousterhout.md) |
| Entrega corta, design docs, review | [`ingenieria-software-gergely-orosz.md`](ingenieria-software-gergely-orosz.md) |
| Datos, outbox, OCC, expand-contract | [`patrones-datos-ddia.md`](patrones-datos-ddia.md) |
| Fronteras de servicio | [`microservicios-sam-newman.md`](microservicios-sam-newman.md) |
| Patrones y dos sombreros | [`patrones-gof-y-refactoring.md`](patrones-gof-y-refactoring.md) |
| Costura, `F-n`, TDD, pair | [`vertical-slice.md`](vertical-slice.md) |
| Algoritmos y costo | [`algoritmos-y-estructuras-clrs.md`](algoritmos-y-estructuras-clrs.md) |
| Construcción, de esta guía | Este archivo |

El plan de lectura y las revistas de 2004 no se adoptan como lista. Quien escribe una feature lee el spec, el stack y la referencia del tema que esa feature toca. No lee las siete partes otra vez.

---

## Matriz de la Parte VII

| Fase | Criterio |
| --- | --- |
| Implementer, layout | Corre el formateador. No reindenta a mano. No discute llaves en el review. |
| Implementer, comentario | Porqué, contrato, invariante. Sin parafrasear el código. Sin `TODO` al cerrar. Si comentario y código discrepan, se arregla el comentario. |
| Revisor | Cita un comentario que miente, un marcador de trabajo a medias, o un bloque cuya sangría no es la del formateador porque alguien lo forzó. No cita el estilo que la herramienta ya cumple. |
| Lección | Una clase que vuelve a fallar, o un "está tramposo" que se empujó igual, queda registrada. |
| Lectura | El spec, el stack y la referencia del tema. Context7 para la API de ahora. |

## Conflictos cerrados en esta parte

* Guerra de llaves, ancho de línea y estilo visual del capítulo 31 frente al formateador del stack. Gana el formateador. El review no reabre el debate.
* Comentario en cada control, encabezado con el teléfono del autor, y el pseudocódigo dejado como comentario, frente a la regla del implementer. Gana la regla: intención y contrato. El cómo lo dice el código. El autor lo dice git.
* Carpeta de documentación IEEE frente a PRD, SDD, spec e `impl`. Ganan los documentos del arnés. No se añade una carpeta por unidad.
* Programación literaria frente a spec más código. No se adopta.
* Persistencia y coraje como virtudes sin freno frente a la parada a los dos rojos. El hábito que compensa el ego gana. Empujar el tercer parche no es carácter.

## Cierre de la integración

* La estrategia de errores del sistema y la barricada defensiva (capítulos 3 y 8) quedan incorporadas como directriz STE100 en `templates/sdd.md` (sección `## Componentes`). El revisor aislado audita el respeto a la barricada y a la política de corrección/robustez sobre el diff.

La integración de *Code Complete* en este arnés cubre las siete partes en este archivo, conectada a la plantilla del SDD, el implementer y el revisor sin añadir burocracia de gates vacíos.
