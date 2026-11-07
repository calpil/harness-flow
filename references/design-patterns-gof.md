# Design Patterns (Gamma, Helm, Johnson, Vlissides) en Harness Flow

Guía operativa de *Design Patterns: Elements of Reusable Object-Oriented Software* (Addison-Wesley, 1994) aplicada a los roles del arnés. Resume criterios y los traduce a fases. No reproduce el libro.

**Lectura:** Capítulo 1 cerrado. Capítulos 2 a 6 pendientes en este mismo archivo.

El catálogo de los 23 patrones, la capa hexagonal de cada uno, los dos sombreros y los olores de Fowler siguen en [`patrones-gof-y-refactoring.md`](patrones-gof-y-refactoring.md). Este archivo no los reescribe. Aquí va lo que el libro dice sobre cuándo un patrón entra, y en qué fase del arnés.

| Tema | Dueño | Qué aporta el libro aquí |
| --- | --- | --- |
| Catálogo, capa y olores | [`patrones-gof-y-refactoring.md`](patrones-gof-y-refactoring.md) | El nombre del patrón es vocabulario. La matriz de capa no cambia. |
| Módulos y YAGNI | [`filosofia-diseno-ousterhout.md`](filosofia-diseno-ousterhout.md) | Componer gana a heredar. Una delegación que solo reenvía sigue siendo un middle man. |
| Costura y TDD | [`vertical-slice.md`](vertical-slice.md) | El patrón no entra en el primer verde. Entra en el sombrero de refactor, si el olor ya está. |
| Datos y fronteras | [`patrones-datos-ddia.md`](patrones-datos-ddia.md), [`microservicios-sam-newman.md`](microservicios-sam-newman.md) | El libro de 1994 no cubre concurrencia, sistemas distribuidos ni tiempo real. Esos temas no se buscan aquí. |

Cargar esta referencia al nombrar un patrón en un `D-n`, y en el implementer antes de extraer una jerarquía. El catálogo se consulta en la otra referencia, no en las muestras de C++ de 1994.

---

## Capítulo 1 — Qué es un patrón, y cuándo no

Diseñar software orientado a objetos es difícil. Diseñarlo para reusarlo es más difícil. Quien ya diseñó no resuelve cada problema desde cero: reconoce una forma que ya le sirvió. El libro registra esas formas. Ninguna es un diseño nuevo. Entran las que se usaron más de una vez, en sistemas distintos. No entran concurrencia, distribución, tiempo real, interfaces de usuario, drivers ni bases orientadas a objetos. Cada uno de esos temas tiene su propio catálogo. En el arnés, distribución y datos ya tienen dueño.

Un patrón no es una lista enlazada ni una tabla hash: eso se codifica y se reusa tal cual. Tampoco es el diseño de una aplicación o de un subsistema entero. Es una descripción de clases y objetos que se hablan, ajustada a un problema general en un contexto. El punto de vista importa: lo que para uno es un patrón, para otro es una pieza primitiva.

### Los cuatro elementos

| Elemento | Qué fija | En el arnés |
| --- | --- | --- |
| Nombre | Una o dos palabras para el problema, la solución y el costo. Sube el nivel de la conversación. | Vocabulario del `D-n` y del review. No es un sufijo obligatorio en cada clase. |
| Problema | Cuándo aplica, y qué estructura rígida lo delata. A veces, condiciones que tienen que cumplirse antes. | El olor ya está en el código verde, o el eje de cambio ya está en el PRD. Sin eso, el patrón no aplica. |
| Solución | Roles, responsabilidades y colaboraciones. Una plantilla, no un diseño concreto ni una implementación. | La matriz de la otra referencia dice la capa. El código de muestra del libro es C++ y Smalltalk de 1994. No se copia. Manda el idioma del stack. |
| Consecuencias | Espacio, tiempo, lenguaje, flexibilidad, extensión, portabilidad. Sin nombrarlas, la alternativa no se puede juzgar. | El `Descartada:` del `D-n` es esa consecuencia. Un patrón sin costo dicho no es una decisión. |

Nombrar sube la conversación. También la baja si el nombre reemplaza al dominio. `DomesticTax` dice el negocio. `TaxStrategy` dice el libro. El `D-n` puede decir "Strategy". La clase dice el negocio, salvo que el stack ya use el rol en el nombre.

### MVC, como ejemplo y no como tarea

El libro abre el catálogo con Model/View/Controller. El modelo no conoce sus vistas. Las vistas se suscriben y se enteran del cambio. La vista puede cambiar cómo responde al usuario sin cambiar cómo se dibuja: eso es Strategy sobre el controlador. El mismo modelo sirve a varias vistas.

En los stacks de UI (Angular, Next.js) ese corte ya está en el manifiesto: dominio sin framework, UI sustituible, estado de la pantalla aparte de la regla. Una feature no redescubre MVC. Si el framework empuja la regla al componente, gana el stack, no el componente.

### Cómo está armado el catálogo

Dos ejes. El propósito: creación, estructura o comportamiento. El alcance: de clase (herencia, fijada al compilar) o de objeto (composición, que puede cambiar en ejecución). Casi todo el catálogo es de objeto. El de clase existe, y el arnés ya se inclina al de objeto: componer, no heredar para reusar.

Los patrones de creación existen para que el resto del sistema hable con una interfaz y la clase concreta se elija en un solo lugar. Ese lugar, en estos stacks, es la raíz de composición. No es una fábrica dentro del dominio.

### Dos principios, y el límite de cada uno

Programar contra la interfaz, no contra la clase concreta. El cliente no declara la variable como la implementación. En algún sitio hay que construir el objeto concreto. Los patrones de creación hacen ese sitio explícito. En el arnés la interfaz es el puerto, cuando hay más de una implementación real o un adaptador de test que el stack ya pide. Una interfaz con un solo implementador, sin ese motivo, es generalidad especulativa. El checklist del revisor ya la marca.

Preferir composición a herencia. Heredar es reuso de caja blanca: la subclase ve el interior del padre, el vínculo se fija al compilar, y un cambio del padre arrastra a la hija. Componer es reuso de caja negra: se ve la interfaz, y el objeto se puede cambiar en ejecución si el tipo coincide. La herencia deja jerarquías chicas en teoría y monstruos en la práctica. La composición deja más objetos y menos clases, y el comportamiento queda en cómo se conectan, no en una sola clase. Las dos se ayudan: a veces se hereda de una abstracción para poder componer. La experiencia del libro es que se hereda de más, y el diseño sale más simple al componer más.

Delegar es componer con la fuerza de la herencia: el receptor pasa el trabajo a otro objeto, y a veces se pasa a sí mismo para que el otro pueda volver. Sirve para cambiar el comportamiento al cambiar el delegado (State, Strategy, Visitor). Cuesta: un sistema muy parametrizado se entiende peor que uno estático, y ese costo humano pesa más que el de ejecución. Delegar conviene cuando simplifica, y sobre todo cuando la forma ya es un patrón conocido. Una ventana que guarda un rectángulo y le reenvía cada llamada, sin variar nada, es el middle man que el arnés ya rechaza.

### Ocho motivos de rediseño

El capítulo lista lo que obliga a tocar muchas clases. Cada motivo señala una familia de patrones. En el arnés el motivo solo cuenta si el eje ya es real: está en el PRD, en un `D-n`, o apareció como olor con el test en verde. Anticiparlo "por si el día de mañana" es el rediseño que el libro quiere evitar, hecho por adelantado.

| Si esto ya duele | La familia, no la obligación |
| --- | --- |
| Cada creación nombra la clase concreta | Creación, en la raíz de composición. |
| El cliente depende de una operación concreta | Encapsular la petición. Command o una cadena solo si hay más de un manejador real. |
| El código depende de la plataforma o de la librería | Adapter en el puerto. Bridge si hay dos ejes de variación ya presentes. |
| El cliente depende de cómo está representado el dato | Esconder la representación. Memento y Proxy no se estrenan por el nombre. |
| El algoritmo cambia, o cambia la estructura que recorre | Strategy, Iterator del lenguaje, o una tabla. Visitor cuando el capítulo 5 lo merezca, no antes. |
| El acoplamiento es una masa: no se puede sacar una clase sin entender las demás | Fachada, mediador u observador si el eje es real. Si no, partir la responsabilidad. |
| Cada extensión pide otra subclase, y las subclases explotan | Componer. Decorator o Strategy cuando ya hay más de una variante. |
| No se puede modificar la clase (librería cerrada, o el cambio tocaría a todas las hijas) | Adapter o Decorator alrededor. No se fork de la librería. |

### Aplicación, toolkit y framework

Una aplicación (el producto de una feature) cuida el reuso interno, el mantenimiento y la extensión. El reuso interno quiere decir no diseñar de más. Los patrones que cortan dependencias ayudan a eso. No autorizan piezas para un requisito que no está.

Un toolkit es una biblioteca: listas, mapas, el I/O. No impone el diseño de la aplicación. Quien escribe llama al toolkit. El arnés no fabrica toolkits dentro de una feature.

Un framework impone la arquitectura: el corte en clases, las responsabilidades, la colaboración y el hilo de control. Quien lo usa escribe lo que el framework llama, no al revés. Eso es inversión de control. Los stacks CALPIL son ese framework. Una feature escribe el caso de uso y el adaptador que el puerto ya nombró. No rediseña el framework. Cambiar el framework se paga en todas las aplicaciones que cuelgan de él. Por eso un patrón nuevo en el manifiesto del stack es una decisión de producto, no un refactor de una feature.

Tres diferencias que el capítulo fija, para no confundir los nombres:

* Un patrón es más abstracto que un framework. El framework se ejecuta. Del patrón solo se ejecutan los ejemplos. El patrón además dice la intención y el costo.
* Un patrón es más chico. Un framework contiene varios patrones. Al revés no ocurre.
* Un patrón es menos especializado. El framework tiene dominio. El patrón de este catálogo no dicta la arquitectura de la aplicación. El stack sí.

Documentar el framework con los patrones que usa acorta la curva. En el arnés esa documentación ya es la matriz de capa. No se añade un ensayo por feature.

### Cómo se elige, y cómo se aplica

Elegir, en este orden práctico:

1. Qué tiene que poder variar sin rediseñar. Si la respuesta es "nada de este PRD", no hay patrón.
2. Si el motivo de rediseño de la tabla de arriba ya ocurrió.
3. Leer la intención en la matriz de la otra referencia, no las veintitrés del libro en cada feature.
4. Si dos patrones se parecen, mirar el costo. Esa diferencia es el `Descartada:`.

Aplicar, cuando el sombrero de refactor ya tiene el verde:

1. Confirmar que el problema y las consecuencias coinciden con esta feature. Si no, no es el patrón.
2. Entender roles y colaboraciones. La estructura del libro no se copia en C++.
3. El ejemplo de código se lee en el idioma del stack, en la otra referencia o en Context7. No en la muestra de 1994.
4. Los nombres de los roles del libro son demasiado abstractos para quedar tal cual. El nombre de la clase es el del dominio. El `D-n` guarda el nombre del patrón.
5. Se declaran las interfaces que el puerto ya necesitaba. No se abre una jerarquía nueva en el sombrero de feature.
6. La operación que el patrón trae se implementa con la responsabilidad del AC. Si el patrón pide una operación que ningún AC usa, sobra.

El libro dice que quien conoce el patrón decide varias cosas de una vez, y que un diseño reusable casi nunca sale bien a la primera: se intenta reusar y se corrige. Eso coincide con probar más de un diseño en el `D-n`, y con no congelar la jerarquía en el primer verde.

---

## Matriz del capítulo 1

| Fase | Criterio |
| --- | --- |
| PRD | El problema y el eje que varía, en lenguaje de quien usa el sistema. Sin nombre de patrón y sin clases. |
| SDD | Un `D-n` nombra el patrón solo si el eje ya es real, con la alternativa descartada y el costo. La raíz de composición es el único lugar de las clases concretas. |
| Plan vertical | Hasta cinco pasos de comportamiento. Sin participantes del patrón y sin archivos. |
| Implementer, sombrero de feature | El código más simple que pone la costura en verde. Sin fábrica, sin estrategia y sin jerarquía. |
| Implementer, sombrero de refactor | El patrón entra si el olor está y el verde se mantiene. Nombres de dominio. Muestras del stack, no del libro. |
| Revisor | Interfaz de un solo uso, delegación que solo reenvía, herencia para reusar, patrón cuyo eje no está en el PRD ni en el diff. |
| Stack | El framework ya contiene los patrones de la arquitectura. Una feature no los reinventa. |

## Conflictos cerrados en este capítulo

* "Aplicar el patrón en siete pasos en cuanto se elige" frente a los dos sombreros. Gana el arnés. La elección puede quedar en el `D-n`. Las clases entran con el test ya verde, o no entran.
* El nombre del rol (`LayoutStrategy`) en la clase frente al nombre del dominio. Gana el dominio. El patrón se nombra en el `D-n`.
* Programar siempre contra una interfaz frente a la interfaz de un solo implementador. Gana el puerto real o el adaptador que el stack pide. La interfaz ornamental no se crea.
* Delegar para que sea flexible frente al middle man. Delegar solo si el delegado se cambia de verdad y eso simplifica. Reenviar cada método sin variación se rechaza.
* Diseñar reusable por si el futuro cambia frente a YAGNI. El motivo de rediseño cuenta cuando ya ocurrió. Anticipar los ocho motivos en cada feature no se hace.
* Muestras de C++ y Smalltalk frente al idioma del stack. Gana el stack, con Context7 si la API importa.

## Pendiente

| Capítulo | Qué es | Dónde pegará |
| --- | --- | --- |
| 2 Caso Lexi | Un editor, y cómo se eligen siete patrones juntos | SDD y plan, como ejemplo de no adelantar el patrón |
| 3 Creación | Abstract Factory, Builder, Factory Method, Prototype, Singleton | Delta sobre la matriz. No se copia el catálogo |
| 4 Estructura | Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy | Igual |
| 5 Comportamiento | Once patrones, de Chain of Responsibility a Visitor | Igual |
| 6 Cierre | Qué espera el libro de un diseño que usa patrones | Revisor y lecciones |
