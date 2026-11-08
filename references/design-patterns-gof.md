# Design Patterns (Gamma, Helm, Johnson, Vlissides) en Harness Flow

Guía operativa de *Design Patterns: Elements of Reusable Object-Oriented Software* (Addison-Wesley, 1994) aplicada a los roles del arnés. Resume criterios y los traduce a fases. No reproduce el libro.

**Lectura:** Cerrada. Capítulos 1 a 6 están en este archivo.

El catálogo de los 23 patrones, la capa hexagonal de cada uno, los dos sombreros y los olores de Fowler siguen en [`patrones-gof-y-refactoring.md`](patrones-gof-y-refactoring.md). Este archivo no los reescribe. Aquí va lo que el libro dice sobre cuándo un patrón entra, y en qué fase del arnés.

| Tema | Dueño | Qué aporta el libro aquí |
| --- | --- | --- |
| Catálogo, capa y olores | [`patrones-gof-y-refactoring.md`](patrones-gof-y-refactoring.md) | El nombre del patrón es vocabulario. La matriz de capa no cambia. Los capítulos 3 a 5 solo separan formas que la matriz junta. |
| Módulos y YAGNI | [`filosofia-diseno-ousterhout.md`](filosofia-diseno-ousterhout.md) | Componer gana a heredar. Una delegación que solo reenvía sigue siendo un middle man. |
| Costura y TDD | [`vertical-slice.md`](vertical-slice.md) | El patrón no entra en el primer verde. Entra en el sombrero de refactor, si el olor ya está. |
| Datos y fronteras | [`patrones-datos-ddia.md`](patrones-datos-ddia.md), [`microservicios-sam-newman.md`](microservicios-sam-newman.md) | El libro de 1994 no cubre concurrencia, sistemas distribuidos ni tiempo real. Esos temas no se buscan aquí. |

Cargar esta referencia al nombrar un patrón en un `D-n`, y en el implementer antes de extraer una jerarquía. El catálogo se consulta en la otra referencia, no en las muestras de C++ de 1994. Los apéndices del libro, glosario, notación y clases de fundación, no se mapean: el idioma del stack ya los cubre.

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

## Capítulo 2 — Lexi, ocho patrones y ni uno de más

El capítulo diseña un editor de documentos, Lexi. Sirve para ver los patrones en un problema, no para copiar un editor. Cada apartado es un problema de diseño, y al final nombra el patrón. El cierre enumera ocho. En el arnés esos ocho no entran juntos en `F-1`. El caso es un recorrido. Cada patrón espera a la candidata cuyo eje ya es real.

Los problemas, en lenguaje de quien usa el sistema, serían objetivos del PRD: armar el documento, partirlo en líneas, adornar una zona, verse como un estándar u otro, correr en otro sistema de ventanas, deshacer, y revisar ortografía o cortes de palabra. El nombre del patrón no está en el PRD.

### La estructura: un árbol, o una lista

El documento es una jerarquía. Un carácter, una imagen, una fila y una columna comparten interfaz: dibujarse, decir cuánto ocupan, decir si un punto cae dentro, y tener hijos. Una fila inserta y quita hijos. El cliente trata igual a la hoja y al grupo. Eso es Composite.

El libro se queda con un árbol estricto. Menciona que compartir glifos ahorraría memoria y formaría un grafo, y que Flyweight serviría, y lo deja para después. El índice entero para nombrar un hijo es flojo si los hijos viven en una lista enlazada. La estructura de datos no debería asomar en la operación.

En el arnés, Composite entra cuando el dominio es de verdad un árbol: reglas que se anidan, un documento que se recorre como árbol. Una lista de filas no lo es. El árbol de componentes de Angular o Next ya es el del framework. Una feature no inventa una clase `Glyph` con `Draw(Window)`. En estos stacks el dominio no recibe la ventana. La UI dibuja. El dominio guarda la estructura si la regla es de dominio. Flyweight espera una medición, igual que el afinado de Code Complete. Compartir nodos complica el padre. Hasta que el AC lo pida, el árbol no se comparte.

### El formateo: un algoritmo, o dos

Partir glifos en líneas es un algoritmo que puede cambiar: uno simple, o el de TeX. El libro separa el contenido (`Composition`) del algoritmo (`Compositor`). El primero le pide al segundo que componga, y el segundo inserta filas y columnas. Se puede cambiar el algoritmo sin tocar los glifos, y al revés. La interfaz de los hijos ya permite insertar y quitar. Eso es Strategy. La clave es que un algoritmo nuevo no obligue a cambiar esa interfaz.

Un solo algoritmo es una función. Strategy entra cuando hay un segundo algoritmo real y el producto elige entre ellos. Partir `Composition` y `Compositor` el primer día, con un solo corte de línea, es la clase de más.

### El adorno: envolver uno, no heredar el borde

Un borde puede contener al glifo, o el glifo puede saber que tiene borde. El libro elige lo primero: el código del borde no entra en cada subclase, y el cliente no distingue al glifo pelado del glifo con borde. Ambos reciben "dibújate". `MonoGlyph` guarda un componente y reenvía todas las operaciones. La subclase redefine una: dibujar el borde y luego pedir al interior que se dibuje. El scroll es otro envoltorio. El envoltorio tiene un hijo. El composite tiene muchos. Eso es Decorator.

Reenviar todo se parece al middle man. Aquí el envoltorio añade una conducta visible: el borde, la barra. Sin esa conducta, el reenvío se borra. Una clase abstracta de envoltorio con una sola subclase es generalidad especulativa. El segundo adorno, o la necesidad de apilar borde y scroll sin que el cliente lo note, es el momento. Hasta entonces, el borde se dibuja en el componente que el AC nombra. La costura observa el borde, no el tipo del envoltorio.

### El estándar visual: una familia, no una fábrica por costumbre

Subclases por cada control y cada estándar (scroll de Motif, botón de Presentation Manager) explotan y se mezclan: un menú de un estándar en medio de una aplicación de otro, porque un `new` se escapó. El libro crea los controles con una fábrica. El cliente pide "un scroll" y no nombra Motif. Una fábrica concreta produce toda la familia, y se usa siempre la misma. Cambiar de estándar es cambiar la fábrica al arranque y reconstruir la interfaz. Los tipos de producto se mantienen. Lo que cambia es la familia. Por eso es Abstract Factory y no una fábrica de un solo producto. Un registro de fábricas permite sumar una sin tocar el `if` del arranque. En una plataforma sin Motif, esa fábrica ni se enlaza.

En el arnés hay un kit de UI por stack. Una familia. No hay fábrica. Abstract Factory entra si el PRD exige dos estándares reales, intercambiables, con el mismo conjunto de controles. La fábrica vive en la raíz de composición, se elige una vez, y el dominio no menciona al estándar. Elegirla en cada pantalla vuelve a mezclar familias.

### El sistema de ventanas: un eje no es un puente

A primera vista, otro sistema de ventanas parece la misma fábrica. No lo es. Las jerarquías de los vendedores no comparten una clase base de producto, y no se puede reescribir el sistema de ventanas. Falta el producto abstracto que la fábrica necesita. El libro separa la ventana de la aplicación (`Window`) de la implementación de plataforma (`WindowImp`). Cada una tiene su jerarquía. La ventana guarda la implementación y le delega el rectángulo de dispositivo. Una fábrica del sistema crea la implementación concreta (X o Presentation Manager). Eso es Bridge: dos jerarquías que cambian por separado.

Si solo hay una plataforma, eso es un Adapter en el puerto, no un puente. El stack ya aísla HTTP, base de datos y ventana. Una feature no añade `Window` y `WindowImp`. Bridge espera dos ejes ya presentes: la abstracción propia y más de una implementación que no controlamos. Con un eje, el puente es una indirección vacía.

### Deshacer: si el AC lo pide

Las operaciones del usuario están repartidas, y deshacer no puede ser un caso especial en cada una. Guardar o salir no se deshacen. El número de niveles no debería tener un tope arbitrario. El libro encapsula la petición: ejecutar, deshacer, y saber en ejecución si esa petición se puede deshacer (un cambio de fuente que no cambió nada no entra en la historia). Una lista guarda lo ejecutado, con una marca en el presente. Deshacer camina a la izquierda. Rehacer, a la derecha. Una operación nueva que no es rehacer corta el tramo rehecho. Eso es Command.

Sin un AC de deshacer, no hay lista de comandos. Envolver cada clic "por si luego hay undo" adelanta el patrón. Si el PRD pide deshacer, el `D-n` es Command, y la historia es de esa feature. No es un bus de comandos del framework. Guardar y salir quedan fuera de la historia, como dice el capítulo.

### Recorrer y analizar: el visitante cuando la estructura ya no se mueve

Hace falta recorrer el árbol sin mezclar el recorrido con la ortografía. Un iterador guarda el estado del recorrido. Otro recorrido es otra subclase, sin tocar los glifos. Dos recorridos pueden estar vivos a la vez. El iterador no es solo para árboles: sirve para colecciones. El lenguaje de hoy ya trae el suyo. No se escribe `PreorderIterator` si el lenguaje recorre la estructura.

La ortografía no debe ser una cadena de `dynamic_cast` a carácter, fila e imagen. Ese código se rompe al sumar un tipo. Meter `CheckMe` en cada glifo también falla: cada análisis nuevo toca todas las clases, y la interfaz del glifo deja de verse como estructura. El libro saca el análisis del glifo. El glifo acepta un visitante y se identifica. Ortografía y guionado son dos visitantes. Sumar un análisis no toca los glifos.

La pregunta que el capítulo hace obligatoria: qué jerarquía cambia más a menudo. El visitante conviene cuando se suman análisis y la estructura está quieta. Un glifo nuevo obliga a actualizar la interfaz de todos los visitantes, con una operación `Visit` para ese tipo. Si cada feature trae un nodo nuevo y el análisis es uno, el visitante es el rediseño caro. En ese caso el análisis vive en un solo lugar, o en el nodo, y no se abre la jerarquía de visitantes. El algoritmo de ortografía, si hay más de uno, puede ser Strategy. Con uno, es una función.

### Lo que el cierre pide no hacer

Ninguno de los ocho es exclusivo de un editor. Un portafolio puede ser Composite. Un compilador puede cambiar de algoritmo con Strategy. Casi cualquier interfaz usa Decorator y Command. El libro invita a buscarles otro uso. En el arnés esa invitación no es una feature. Es la prueba de que el patrón se reconoce cuando el problema vuelve, no de que Lexi se copie entero.

| Problema de Lexi | Patrón | Entra cuando | No entra cuando |
| --- | --- | --- | --- |
| Árbol de piezas uniformes | Composite | El dominio se anida. | La colección es plana, o el árbol ya es el del framework. |
| Más de un algoritmo de armado | Strategy | El producto elige entre algoritmos reales. | Hay un solo algoritmo. |
| Adorno apilable y transparente | Decorator | El envoltorio añade conducta y se apila. | Un borde se dibuja en el propio componente. |
| Varias familias de controles | Abstract Factory | El PRD tiene dos estándares, con los mismos tipos de control. | El stack trae un solo kit. |
| Abstracción propia y varias plataformas ajenas | Bridge | Los dos ejes ya varían. | Hay una plataforma. Eso es un Adapter. |
| Deshacer y rehacer sin tope | Command | El AC pide la historia. | Cada clic se envuelve por si acaso. |
| Recorrer sin acoplar el recorrido | Iterator | El del lenguaje no alcanza. | El lenguaje ya recorre. |
| Muchos análisis, estructura quieta | Visitor | Se suman análisis y los nodos no. | Cada feature suma un tipo de nodo. |

---

## Matriz del capítulo 2

| Fase | Criterio |
| --- | --- |
| PRD | Los problemas de Lexi, si aplican, se escriben como comportamiento: deshacer, dos presentaciones, documento anidado. Sin los ocho nombres. |
| SDD | Un `D-n` por eje real. La fábrica o el puente, si existen, se eligen en la raíz de composición. El dominio no nombra la plataforma ni la ventana. |
| Candidatas | Una feature no instala los ocho. El eje que el PRD ya tiene es la candidata. El resto espera. |
| Implementer | El primer verde resuelve el AC sin el andamio del patrón. El patrón entra en el refactor cuando el segundo caso ya no cabe en el código simple. |
| Revisor | `Glyph` que recibe la ventana, fábrica de un solo producto, puente de una sola plataforma, visitante para un solo análisis, lista de comandos sin AC de deshacer. |

## Conflictos cerrados en este capítulo

* Recorrer Lexi e instalar los ocho patrones en el esqueleto frente a un eje por candidata. El caso es un recorrido didáctico. Gana el arnés: `F-1` no es Lexi.
* El glifo se dibuja solo en una `Window` frente al dominio separado de la UI. Gana el stack. El dominio no recibe la ventana.
* Abstract Factory ante cualquier variación visual frente a un solo kit. Con un kit no hay fábrica.
* Bridge ante cualquier plataforma frente a Adapter. Un solo sistema ajeno es un adaptador en el puerto.
* `MonoGlyph` que reenvía todo frente al middle man. El reenvío se queda si el envoltorio añade una conducta que se apila. Si no, se dibuja en el componente.
* Visitor como forma por defecto de recorrer un árbol frente a la pregunta del propio capítulo. Si los nodos cambian más que los análisis, el visitante no se usa.
* Flyweight para compartir nodos desde el principio frente a medir. El libro lo pospone. El arnés también.

## Capítulo 3 — Crear sin nombrar la clase concreta

Los patrones de creación esconden qué clase concreta se instancia, quién la crea, cómo y cuándo. El de clase usa herencia para variar el producto. El de objeto le pasa la creación a otro objeto. Importan cuando el sistema ya se compone más de lo que hereda: el comportamiento sale de armar piezas, y crear deja de ser un `new` fijo.

Dos temas se repiten. Encapsulan el conocimiento de qué clases concretas usa el sistema. Esconden cómo se arman las instancias. El resto del programa solo ve interfaces. A veces compiten. A veces se combinan: un Builder puede usar otro patrón para las partes, y un Prototype puede guardar su registro como Singleton. El capítulo los compara con un mismo ejemplo, un laberinto de juego. El laberinto no se copia. Lo que se copia es la diferencia entre las cinco formas.

La matriz del arnés ya dice el lugar: la raíz de composición, no una fábrica suelta en el dominio. Este capítulo dice cuál de las cinco, si es que hace falta alguna.

| Si esto ya es cierto | Patrón | Si no |
| --- | --- | --- |
| Hay varias familias, y los productos de una no se mezclan con los de otra. El conjunto de tipos de producto está quieto. | Abstract Factory | Un solo kit. Se construye en `main`. Sumar un tipo de producto obliga a tocar la fábrica y todas sus concretas. |
| El mismo proceso arma un objeto complejo, paso a paso, y el resultado cambia de representación. | Builder | El objeto se arma de un golpe, o la representación es una sola. Una interfaz de builder con métodos vacíos para partes que nadie construye es generalidad de más. |
| Quien crea no puede saber la clase, y la subclase ya tenía que existir por otra razón. | Factory Method | La clase concreta no cambia. Un `new` en la raíz basta. No se abre una subclase solo para devolver otro producto. |
| El producto se elige en ejecución, o hace falta no duplicar una jerarquía de fábricas, o el estado inicial es una de pocas combinaciones. | Prototype | Copiar es un riesgo: la copia superficial comparte lo que debía ser propio. Sin un AC de duplicar o de registrar prototipos, no hay `Clone` en cada tipo. |
| Tiene que haber una sola instancia. | Ninguno de estos cinco como acceso global. Se construye una vez en la raíz y se inyecta. | `Instance()` estático. Es el global que el capítulo 13 de Code Complete ya rechazó. |

### Abstract Factory

El cliente pide "un scroll" y no nombra Motif. Una fábrica concreta entrega toda la familia, y el uso de una sola fábrica impide mezclar un scroll de un estándar con un botón de otro. Cambiar de familia es cambiar la fábrica donde se instancia, una vez, y reconstruir. El conjunto de operaciones de creación queda fijo: sumar un tipo de producto nuevo obliga a cambiar la fábrica abstracta y todas las concretas.

Eso ya se dijo en Lexi. El delta es el costo, que el capítulo numera: aislar las clases concretas, cambiar la familia de un golpe, y forzar la coherencia. El pasivo es el conjunto cerrado de productos. En el arnés, con un kit de UI, no hay familia que cambiar. Si el PRD trae dos familias reales, la fábrica vive en la raíz. No se llama desde cada pantalla.

### Builder

El lector de un documento y el conversor no son la misma cosa. El lector avisa cada parte. El conversor la acumula en su representación: texto plano, TeX, o un control editable. El mismo lector, con otro conversor, produce otra representación. El cliente recupera el producto del builder cuando el director terminó, no a medio camino. A diferencia de la fábrica, que devuelve el producto de un golpe, aquí el proceso manda y se puede controlar cada paso.

Hace falta cuando el algoritmo de armado es independiente de las partes y de cómo se juntan, y cuando el mismo proceso debe poder dejar representaciones distintas. Si solo hay una representación, el builder es un objeto de más entre el lector y el resultado. Los métodos que el builder deja vacíos, para las partes que esa representación no usa, no se copian como estilo: una interfaz con huecos es el olor de una abstracción que todavía no tiene dos concretos.

### Factory Method

El framework sabe cuándo crear un documento y no sabe de qué subclase. La aplicación redefine la operación que crea el documento. El código del framework solo ve la interfaz del producto. El patrón es de clase: la subclase decide.

El capítulo mismo marca el límite. Hace falta cuando la clase no puede anticipar lo que crea, cuando las subclases ya especifican el producto, o cuando hay que localizar cuál ayudante se usa. El inconveniente es subclasificar al creador solo para elegir el producto. Si el cliente ya subclasificaba al creador, el gancho es barato. Si no, aparece un punto de evolución de más. Una jerarquía de creadores paralela a la de productos es el classitis que el arnés ya prohíbe.

No hace falta cuando la clase instanciada no cambia, ni cuando la creación ya está en una operación que la subclase puede redefinir, como la inicialización. En estos stacks esa operación es `main`. Un método de fábrica "por si una subclase quiere otro producto" no se agrega en el primer verde.

### Prototype

En vez de una subclase de herramienta por cada figura, la herramienta guarda un ejemplar y lo clona. Notas redondas y blancas pueden ser la misma clase con otro mapa de bits y otra duración. Sumar un producto es registrar un ejemplar, incluso en ejecución, sin una jerarquía de fábricas al lado. Si el objeto compuesto implementa la copia profunda, una estructura armada por el usuario puede volver a la paleta como prototipo.

El libro lo prefiere, en el editor de dibujo, frente a Factory Method y frente a Abstract Factory: aquellos multiplican clases que no hacen casi nada. Prototype pide una operación de clonado en cada producto. En un lenguaje estático el clonado no sale gratis, y inicializar el clon después de copiarlo es incómodo. La copia superficial comparte estado que el clon debía tener propio.

En el arnés, clonar entra si el AC es duplicar, o si el producto se elige en ejecución entre ejemplares ya armados. No se añade `Clone` a cada tipo del dominio para evitar un `new`. El registro de prototipos, si existe, vive en la raíz, no como un singleton al que cualquiera acude.

### Singleton

Algunas cosas del ejemplo son únicas: el spooler, el sistema de archivos, el gestor de ventanas. Una variable global las hace accesibles y no impide crear otra. El libro hace que la clase guarde su única instancia, impida otra, y la entregue por una operación de clase. Las consecuencias que enumera: acceso controlado, menos nombres globales, poder sustituir la instancia por una subclase en ejecución, y poder pasar de una instancia a varias tocando solo esa operación.

Ese último punto es el problema. Quien llama a `Instance()` no declara la dependencia. Cambiar a varias instancias, o a una de prueba, obliga a cazar llamadas escondidas. El acceso global que el libro presenta como mejora sobre la variable global sigue siendo un global. En el arnés la unicidad se cumple construyendo el objeto una vez en la raíz y pasándolo por el constructor. El test recibe el doble por el mismo sitio. No hay `getInstance`. Subclasificar el singleton para cambiar el proceso, como permite el patrón, no se usa: la variante entra por inyección.

### Cómo se elige entre ellos

Hay dos maneras de parametrizar qué clases crea el sistema. Subclasificar a quien crea es Factory Method. El defecto es la cascada: si el creador también nace de un método de fábrica, hay que redefinir al creador del creador. La otra manera es composición: un objeto sabe qué clases de producto hay, y ese objeto es un parámetro del sistema. Abstract Factory produce varios productos de una familia. Builder arma un producto complejo con un protocolo de pasos. Prototype arma copiando, y el prototipo es a la vez la fábrica.

En el editor de dibujo del capítulo, Factory Method es lo más fácil al principio y llena el programa de subclases de herramienta que no hacen nada. Abstract Factory no mejora si la jerarquía de fábricas es igual de grande. Prototype gana ahí porque solo pide clonar. El libro dice que mucha gente usa Factory Method como forma estándar de crear, y que no hace falta cuando la clase no cambia. También dice que los diseños suelen empezar en Factory Method y mudarse a los otros cuando descubren que necesitan más flexibilidad.

En el arnés el orden es el inverso de ese hábito. Se empieza en el `new` de la raíz. Se muda a un patrón de creación cuando el segundo concreto ya no cabe. No se abre el método de fábrica "porque complica poco". Los tres de composición son más flexibles y más complejos. Esa complejidad se paga cuando el eje ya está en el PRD o en el olor, y se escribe en el `Descartada:` cuál de los otros se dejó.

---

## Matriz del capítulo 3

| Fase | Criterio |
| --- | --- |
| PRD | "Hay dos familias que no se mezclan", "el mismo proceso deja dos representaciones", "se duplica este objeto". Sin nombrar la fábrica. |
| SDD | Un `D-n` elige una de las cinco y nombra la descartada. La construcción queda en la raíz de composición. |
| Implementer | El primer verde construye con el lenguaje, en `main` o en el caso de uso. El patrón de creación entra en el refactor, cuando el segundo concreto ya está. |
| Revisor | Fábrica de un solo producto, builder con métodos vacíos, subclase que solo existe para hacer `new`, `Clone` en cada tipo, `Instance()` o un singleton de dominio. |

## Conflictos cerrados en este capítulo

* Factory Method como forma estándar de crear frente a un `new` en la raíz. El libro dice que no hace falta cuando la clase no cambia. Gana ese límite. La subclase solo para elegir el producto no se crea.
* Empezar por Factory Method y evolucionar, frente a empezar por el código simple. Gana el arnés. La flexibilidad de Abstract Factory, Builder o Prototype se añade cuando el eje ya duele.
* Singleton con operación de clase frente a una sola instancia inyectada. La unicidad se queda. El punto de acceso global no. El capítulo 13 de Code Complete ya cerró el mismo conflicto.
* Prototype para no tener fábricas, con `Clone` en todos los productos, frente a copiar solo lo que el AC duplica. La copia superficial que comparte estado no se adopta como atajo.
* Builder con métodos vacíos por defecto, al estilo del ejemplo en C++, frente a una interfaz que solo tiene los pasos que las representaciones reales usan.

## Capítulo 4 — Envoltorios que se parecen y no son lo mismo

Los patrones de estructura arman objetos más grandes a partir de otros. El de clase usa herencia, y el ejemplo simple es la herencia múltiple. El de objeto compone, y la composición se puede cambiar en ejecución. El arnés se queda con el de objeto. La herencia múltiple del adaptador de clase no está en estos stacks.

El capítulo junta siete. Lexi ya mostró Composite, Decorator y Bridge en un editor. La matriz ya pone Adapter en el puerto, Facade como módulo profundo, y Decorator o Proxy en el corte transversal. Aquí va lo que esa matriz no separa: la intención, no el dibujo. Varios comparten la misma figura, un objeto que guarda a otro y reenvía. Se distinguen por para qué.

| Si la intención ya es esta | Patrón | No es |
| --- | --- | --- |
| Dos interfaces ya existen y no coinciden. Hay que hacerlas trabajar sin copiar la librería. | Adapter de objeto | Bridge, que se diseña antes, cuando abstracción e implementación van a variar las dos. Facade, que inventa una interfaz nueva en vez de reconciliar dos viejas. |
| Hay varias abstracciones y varias implementaciones, y el producto de las dos explota en subclases. | Bridge | Un Adapter. Con una sola plataforma no hay segunda jerarquía. |
| Hoja y grupo se tratan igual, y el grupo contiene grupos. | Composite | Decorator. El grupo representa. No adorna. |
| Se añade una conducta, la interfaz no cambia, y se puede apilar. | Decorator | Proxy. El proxy no apila adornos: sustituye el acceso a un solo sujeto. |
| Un subsistema entero se usa por una puerta simple, y quien está detrás no conoce esa puerta. | Facade | Un Adapter de una sola clase, ni una fachada que reenvía una llamada. |
| Hay muchísimos objetos casi iguales, el estado propio es poco, y la identidad no importa. Medido. | Flyweight | Una entidad de dominio con identidad. Compartirla miente el `==`. |
| Conviene no tocar al sujeto directo: está lejos, es caro de crear, o el acceso se controla. | Proxy | Decorator. El proxy no añade la otra mitad de la conducta. |

### Adapter

Convierte la interfaz de una clase en la que el cliente espera. Hace falta cuando la clase ya existe y no coincide, cuando se quiere cooperar con clases que no se diseñaron juntas, o cuando hay varias subclases y no conviene adaptarlas una por una. El adaptador de objeto envuelve y sirve para toda la familia. El de clase hereda del adaptado, puede redefinir, y no cubre a las subclases. El de objeto es el que usa el arnés: el puerto es el objetivo, la librería es lo adaptado, la infraestructura es el adaptador. Si las dos interfaces son nuestras y podemos cambiar una, no hay nada que adaptar.

El adaptador llega después del diseño, cuando se descubre que dos clases incompatibles deben trabajar juntas. El puente se entiende de antemano. El libro lo dice así: el adaptador hace que las cosas funcionen después de diseñadas. El puente las hace funcionar antes. Ninguno es mejor. Resuelven problemas distintos. Una fachada no es un adaptador de un conjunto: la fachada define una interfaz nueva. El adaptador hace coincidir dos que ya estaban.

### Bridge

Si cada tipo de ventana se hereda por cada plataforma, el número de clases es el producto de los dos ejes, y quien crea la ventana nombra la plataforma. El puente parte las jerarquías: una para la abstracción, otra para la implementación, y la primera delega en la segunda. Hace falta cuando el vínculo no debe ser permanente, cuando las dos se extienden por separado, o cuando un cambio de implementación no debe recompilar a los clientes. Esconder la representación por una limitación de C++ no es motivo en estos lenguajes.

Lexi ya cerró el caso de una sola plataforma. Este capítulo añade el otro: las dos dimensiones ya están creciendo. Si no, el puente es la indirección vacía.

### Composite

La hoja y el compuesto comparten interfaz para que el cliente no pregunte el tipo. El libro discute dónde viven las operaciones de hijos. Ponerlas en la raíz da transparencia y quita seguridad: alguien puede añadir un hijo a una hoja. Ponerlas solo en el compuesto da seguridad, el compilador lo rechaza, y quita transparencia: las interfaces ya no son iguales. El capítulo se inclina por la transparencia.

En estos stacks se puede tener las dos cosas que importan. La operación de dominio, evaluar o dibujar el resultado, es común. Añadir hijos existe solo en el tipo compuesto. Una hoja con `Add` que falla en ejecución es la opción que el libro acepta y el arnés no. Un `GetComposite` seguido de un cast es el mismo olor. Si el lenguaje obliga a un solo tipo, la operación de hijos en la hoja no se llama, y el revisor lo marca.

### Decorator

Añade conducta sin subclasificar, con la misma interfaz, y se anida. La explosión que evita es la de una subclase por cada combinación de adornos. El costo que el capítulo nombra y Lexi no cerró: el objeto decorado ya no es el mismo objeto. Una comparación de identidad falla. Quien dependa de la identidad tiene que referirse al componente de dentro. Muchos decoradores pequeños pueden salir más caros que el componente. La conducta de negocio no entra en el decorador. Si el adorno es uno solo y no se apila, se queda en el componente.

### Facade

Una puerta simple sobre un subsistema que se fue haciendo más complejo. La mayoría de los clientes no necesita cada clase de dentro. Quienes sí, pueden seguir entrando: la fachada no las esconde por completo. Las clases de dentro no conocen a la fachada. Sirve para desacoplar clientes, para una entrada por capa, y para que dos subsistemas se hablen solo por sus fachadas.

En el arnés esa puerta, cuando de verdad agrupa varios puertos, es el caso de uso. Una clase que llama a un solo repositorio y no traduce nada es la fachada microscópica que la matriz ya prohíbe. No se añade para "cumplir el patrón".

### Flyweight

Compartir objetos chicos para ahorrar espacio, no para que sean consistentes. El estado intrínseco vive en el objeto compartido. El extrínseco, el que depende del contexto, se pasa en cada llamada. Sin estado de contexto, se puede compartir. Hace falta que se cumplan juntas estas condiciones: muchísimos objetos, el almacenamiento duele por la cantidad, casi todo el estado puede salir del objeto, al sacarlo quedan pocos objetos compartidos, y la aplicación no depende de la identidad. Si el estado extrínseco es tan numeroso como los objetos originales, no hay ahorro. El ejemplo del capítulo: un documento largo no necesita un objeto por carácter y por posición. El código del carácter se comparte. La posición viaja aparte.

Una orden, un usuario o un folio tienen identidad. No son flyweight. Compartirlos hace que dos cosas distintas comparen igual. El capítulo 2 ya dejó el compartir glifos para después de medir. Aquí se queda igual. Sin una medición de memoria, no se parte el estado en intrínseco y extrínseco.

### Proxy

Un sustituto que controla el acceso a un sujeto, con la misma interfaz. El remoto representa a un objeto en otro espacio de direcciones. El virtual crea al sujeto caro cuando hace falta. El de protección decide si la llamada pasa. El inteligente cuenta referencias o carga al persistir. No está pensado para anidar adornos ni para cambiar la interfaz. El sujeto tiene la conducta. El proxy da o niega el acceso. La identidad tiene el mismo problema que el decorador: el sustituto no es el sujeto.

El proxy remoto de objetos distribuidos no es el corte entre servicios de estos stacks. Esa frontera ya tiene dueño. Un proxy de protección por cada regla de acceso duplica lo que el puerto y el stack ya hacen. El virtual, o una caché que está delante de un sujeto lento sin cambiar el contrato, entra si el costo está medido o el AC lo pide. Añadir telemetría u outbox, que es conducta nueva alrededor, sigue siendo decorador, como dice la matriz. No se bautiza la misma clase con los dos nombres.

### Juntarlos

El cierre del capítulo insiste en que la figura parecida no autoriza a tratarlos como uno, y que a veces se usan juntos: un compuesto puede ser el componente de un decorador. Juntarlos en el arnés exige que las dos intenciones ya sean reales. Armar una aplicación enchufando objetos sin clases nuevas es el ideal del libro en este tramo, y es el classitis si se hace antes de que el segundo caso exista.

---

## Matriz del capítulo 4

| Fase | Criterio |
| --- | --- |
| PRD | La interfaz que no coincide, las dos plataformas, el árbol, el adorno apilable, el subsistema que el cliente no debe recorrer, el volumen medido, el acceso que no puede ser directo. Sin los siete nombres. |
| SDD | Un `D-n` con la intención y el patrón descartado de la tabla de arriba. El adaptador y la fachada no se intercambian por gusto. |
| Implementer | El puerto del stack ya es el adaptador. No se añade otro envoltorio en el primer verde. |
| Revisor | Adaptador de clase, puente de un eje, `Add` en la hoja, fachada de un solo método, flyweight de una entidad con identidad, proxy remoto entre servicios, decorador que cambia la regla de negocio. |

## Conflictos cerrados en este capítulo

* Transparencia del Composite, con `Add` en la hoja, frente a seguridad. El libro prefiere la transparencia. Gana la seguridad cuando el lenguaje puede expresar el hijo solo en el compuesto. La operación de dominio sigue siendo común.
* Adaptador de clase por herencia múltiple frente al adaptador de objeto. Gana el de objeto, que ya es el puerto.
* Proxy remoto como forma de distribuir objetos frente a la frontera de servicio. Gana el dueño de microservicios. El proxy remoto no se copia.
* Flyweight en cuanto hay muchos objetos parecidos frente a las cinco condiciones y una medición. Sin identidad estable y sin ahorro medido, no se comparte.
* Decorador y proxy como sinónimos porque los dos reenvían. La matriz puede citarlos en la misma capa. La intención no se mezcla: o se añade conducta, o se controla el acceso.

## Capítulo 5 — Quién habla con quién

Los patrones de comportamiento reparten algoritmos y responsabilidades, y describen cómo se hablan los objetos. El flujo de control en ejecución es difícil de seguir. El patrón deja ver la conexión y esconde ese flujo. Los de clase usan herencia. En este capítulo son dos: Template Method, el esqueleto de un algoritmo con pasos que redefine la subclase, e Interpreter, una gramática hecha de clases. Los de objeto componen. Unos coordinan a varios pares. Otros meten una conducta en un objeto y le delegan.

El tema que el cierre repite es encapsular lo que varía. Strategy guarda un algoritmo. State guarda la conducta que depende del estado. Mediator guarda el protocolo entre objetos. Iterator guarda la forma de recorrer. Si no fuera por el patrón, ese código viviría dentro del objeto que ya existe. No todos parten así la funcionalidad. Chain of Responsibility reparte la petición entre candidatos que ya están, y el número no está fijo.

La matriz ya tiene Strategy y State en el dominio, e Iterator es el del lenguaje desde Lexi. Command, Observer y Visitor ya tuvieron su condición. Este capítulo separa los que se confunden y nombra los que la matriz no lista.

| Si la intención ya es esta | Patrón | No es |
| --- | --- | --- |
| Más de un objeto puede atender la petición, no se sabe cuál, y la cadena ya existe. | Chain of Responsibility | Una cadena nueva para dos `if`. Si nadie atiende, el silencio no vale: el puerto responde el error. |
| La petición se guarda, se pasa o se deshace. | Command | Strategy. El comando es una petición con historia. La estrategia es un algoritmo intercambiable, sin deshacer. |
| El usuario escribe frases de un lenguaje chico, y la eficiencia no es el problema. | Interpreter | Una clase por cada regla de una gramática grande. Eso lo hace un parser, no una jerarquía. |
| Hay que recorrer sin fijar el recorrido al agregado. | Iterator del lenguaje | Una clase de iterador propia. |
| Varios objetos se enredan entre sí y el protocolo es uno, explícito. | Mediator | Observer. El observador reparte el aviso. El mediador lo concentra. Un mediador que lo sabe todo es la clase dios. |
| Hay que guardar el estado interno para restaurarlo, sin abrirlo a quien lo guarda. | Memento | El snapshot público de todo el agregado en cada clic. Si deshacer es la operación inversa, basta Command. |
| Un cambio debe avisar a varios, y el número de avisados varía. | Observer | Una llamada directa. El framework de UI ya observa. Una lista de observadores en el dominio, no. |
| La conducta cambia con el estado, y el estado decide la transición. | State | Strategy. La estrategia la elige el cliente y no se transiciona sola. Dos booleanos no son una máquina. |
| Hay una familia de algoritmos intercambiables. | Strategy | Template Method. El esqueleto heredado ata los pasos a una clase base. |
| El esqueleto ya está en una clase que la subclase tenía que heredar. | Template Method | Una clase abstracta nueva con una sola hija para compartir tres líneas. |
| Se suman análisis y los tipos de nodo no. | Visitor | Un análisis único, o un nodo nuevo en cada feature. |

### Chain of Responsibility

El emisor no nombra al receptor. La petición recorre candidatos hasta que uno la atiende. El conjunto se arma en ejecución. El acoplamiento es más flojo que en los otros, y el precio es que la petición puede caerse del final sin que nadie la atienda. El libro lo da como adecuado cuando la cadena ya es parte de la estructura y uno de varios puede hacerse cargo.

En el arnés, el middleware del stack ya es esa cadena. No se añade otra en el dominio para dos condiciones. Si la petición no tiene dueño, eso es un error del puerto, no un éxito silencioso. La estrategia de errores del sistema, cuando exista en el SDD, dice cuál.

### Command, y el memento al lado

Command ya quedó en Lexi: la petición es un objeto, con ejecutar y deshacer, si el AC pide historia. El capítulo añade el contraste. El comando desacopla emisor y receptor con una operación polimórfica, y en la forma ingenua pide una subclase por cada conexión. Memento también es una ficha que se guarda y se usa después, pero no es una petición: es el estado interno en un momento, con una interfaz tan estrecha que quien la guarda no la lee. Sirve para restaurar sin romper el encapsulamiento.

Si deshacer es aplicar la inversa, el comando basta y guarda lo mínimo para esa inversa. Si deshacer es volver a una foto del interior, el comando puede guardar esa foto sin publicar una clase Originator y otra Caretaker. Una foto del agregado entero en cada clic no se toma. Quien guarda la foto no puede leer los campos.

### Interpreter

Si el mismo tipo de problema se repite, puede valer la pena un lenguaje chico: la gramática es una jerarquía y cada nodo sabe interpretarse. El libro avisa que conviene cuando la gramática es simple y la eficiencia no es crítica. Una gramática grande produce una clase por regla y un intérprete lento. Ahí manda un generador de parsers, no este patrón.

En el arnés, un filtro que el usuario escribe es un AC de lenguaje. Si son tres operadores fijos, es una función o una tabla. El árbol AND/OR de reglas de negocio sigue siendo Composite, no un intérprete, mientras nadie escriba frases.

### Mediator y Observer

Compiten. Observer reparte: no hay un objeto que guarde la restricción. Sujeto y observadores cooperan, un sujeto suele tener muchos, y a veces un observador es sujeto de otro. El flujo se arma al crearlos y después cuesta verlo. Mediator concentra: los colegas solo hablan por él, y la restricción vive en un sitio. El libro encuentra más reutilizables a los observadores, y más fácil de entender al mediador. También dice que la indirección del observador sigue haciendo el sistema más difícil de seguir, y que el despacho a medida del mediador pierde tipo.

En el arnés no se elige el más reusable por deporte. Si dos objetos deben enterarse, y el framework de UI ya tiene señales o un flujo, se usa ese. Una lista de observadores dentro del dominio abre cascadas: un aviso dispara otro y el ciclo no se ve en el diff. Si varios colaboradores de un caso de uso se llaman en red, el caso de uso ya es el mediador. No se crea otro objeto que todos conocen y que termina sabiendo el negocio entero.

### State y Strategy

State cambia la conducta cuando cambia el estado interno. El objeto parece cambiar de clase. Las transiciones las decide el estado, y los estados se conocen entre sí. Strategy la elige quien llama. Los algoritmos no se transicionan solos. La matriz ya los separa: la máquina de vida de una orden es State. El cálculo intercambiable es Strategy. El delta es no cruzarlos. Un `if` sobre el estado, repetido, es el olor que justifica State. Dos booleanos no lo justifican. Un solo algoritmo no justifica Strategy.

### Template Method

El esqueleto vive en la clase base y nombra los pasos. La subclase llena los que varían. Es el patrón de clase más común del capítulo, y el que más empuja a heredar. En el arnés ese esqueleto, si los pasos son lo que varía, es una Strategy o una función compuesta. Template Method entra solo cuando la clase base ya existía y el framework obliga a redefinir el paso. Una base abstracta creada para una sola hija, para no repetir tres líneas, es la herencia que el capítulo 1 ya dejó en segundo lugar.

### Iterator y Visitor

Siguen como en Lexi. El iterador es el del lenguaje. El visitante entra si se suman análisis y la estructura está quieta. El cierre de este capítulo lo trata como un argumento que se pasa, nunca como parte del objeto visitado. Sumar un tipo de elemento obliga a tocar a todos los visitantes. Esa factura no cambia.

### Juntarlos

El resumen dice que casi todos se refuerzan, y que un sistema bien diseñado lleva varios patrones aunque nadie los haya nombrado al diseñarlo. La composición al nivel del patrón, no al de la clase suelta, es lo que el libro celebra. En el arnés esa frase no autoriza a sembrar los once. Describe lo que se reconoce después, cuando cada eje ya dolió. Ponerlos juntos en el primer verde, para que el diseño se parezca al párrafo final, es el exceso.

---

## Matriz del capítulo 5

| Fase | Criterio |
| --- | --- |
| PRD | El comportamiento: deshacer, avisar a varias pantallas, estados de la orden, un lenguaje que el usuario escribe. Sin los once nombres. |
| SDD | Un `D-n` elige una fila de la tabla y nombra la descartada. El caso de uso no se duplica con un mediador. |
| Implementer | El primer verde es el `if`, la llamada o el iterador del lenguaje. El patrón entra en el refactor cuando el segundo caso ya no cabe. |
| Revisor | Cadena que se traga la petición, observadores en el dominio, mediador omnisciente, State de dos booleanos, Template Method de una sola hija, intérprete de tres `if`, foto completa del agregado en cada clic. |

## Conflictos cerrados en este capítulo

* Observer más reusable que Mediator, como criterio para elegirlo siempre. El libro dice que el flujo del observador cuesta de seguir. Gana la llamada explícita o el mecanismo del stack. La lista de observadores no entra en el dominio.
* Template Method como forma habitual de compartir un algoritmo frente a componer los pasos. Gana la composición. La plantilla heredada solo si la clase base ya estaba.
* Combinar los once porque un buen diseño los lleva todos. El libro describe lo que se reconoce después. No es una lista de instalación para `F-1`.
* Chain of Responsibility que deja caer la petición frente a un error explícito en el puerto. El silencio no es éxito.
* Memento como ceremonia de tres clases frente a la foto mínima dentro del comando, cuando el AC pide restaurar. Quien guarda la foto no lee el interior.

## Capítulo 6 — Un vocabulario, no un método

El cierre no añade patrones. Dice qué se puede esperar de los que ya están, de dónde salió el catálogo, y qué no promete. El catálogo no es un lenguaje que, aplicado en orden, genere el programa. Alexander da un orden y pretende generar el edificio. Este libro no da orden y no pretende generar la aplicación. El diseño no queda determinado ni repetible. La creatividad sigue. En el arnés el orden ya está elegido: el eje real, el verde, y después el patrón. No se abre un proceso nuevo porque el libro no trajo el suyo.

### Para qué sirven

Sirven para hablar más arriba que el diagrama y que el lenguaje. Quien los conoce dice el nombre y el otro entiende el problema, la solución y el costo, sin repetir la estructura. En el review y en el `D-n` eso es el uso. "Usemos un Observer aquí", dicho antes de que haya varios avisados de verdad, es el nombre usado como orden de construcción. El nombre entra cuando el eje ya está. Quien no lo conoce lo busca en la matriz, no en el código de 1994.

Sirven para leer un sistema que ya los tiene. Gran parte de lo que parece herencia enredada es un patrón que no se reconoció. Describir el stack con los patrones que usa evita que cada lector los desentierre. Esa descripción ya es la matriz de capa. Una feature no escribe un ensayo de patrones. Nombra el que aplicó, en el `D-n`, y sigue.

Sirven como complemento de un método, no como el método. Un método de diseño trae notación y reglas, y no guarda la experiencia de quien ya diseñó. El patrón muestra cómo se usan los objetos, la herencia y el polimorfismo, y deja el porqué en la aplicabilidad y en las consecuencias. El paso del modelo de análisis a la implementación no es liso. Un diseño reusable tiene objetos que el análisis no tenía. El lenguaje y las librerías cambian el diseño. Eso, en el arnés, es el sombrero de refactor: aparecen piezas que el PRD no nombró como clases. No es una fase de rediseño del PRD.

Sirven de blanco del refactor. El libro cita el ciclo de Foote. Primero el prototipo: actividad rápida, jerarquías que copian el dominio, reuso de caja blanca por herencia. Luego la expansión: más requisitos, más clases, hasta que la jerarquía ya no calza con un solo problema y el cambio se vuelve artrítico. Entonces la consolidación: se parten clases, se suben o bajan operaciones, y la composición reemplaza a la herencia. El ciclo se repite. Los patrones capturan estructuras que salen de esa consolidación. Usarlos pronto puede evitar un refactor posterior. Y si no se vieron hasta después de construir, igual indican cómo cambiar.

Esa última frase es la que manda aquí. La primera, usarlos pronto para no refactorizar después, anticipa un cambio que puede no llegar. Gana el ciclo: el primer verde se parece al problema, con herencia o con código plano si eso es lo simple. La consolidación llega cuando la expansión ya duele. El patrón es el destino del refactor, no el andamio del primer commit. Un buen diseñador sabe qué requisitos van a moverse. Esa lista es el eje del PRD y del SDD, no los veintitrés por si acaso.

### Lo que no son

No son un lenguaje de patrones completo. Por la variedad de sistemas, el libro duda de que alguna vez exista uno que dé instrucciones paso a paso para cualquier aplicación. Se puede para una clase estrecha de programas, un generador de informes o un sistema de formularios. Este catálogo es una colección relacionada. Habría que sumar frameworks, interfaz, análisis y el resto del desarrollo para acercarse a un lenguaje. Los patrones de diseño son una parte.

En el arnés esa parte ya está repartida. El framework es el stack. La interfaz tiene sus skills. El análisis es el PRD. El rendimiento, cuando un AC lo pide, es la medición. No se completa el lenguaje de Alexander dentro de una feature, ni se formaliza el catálogo en una herramienta. El libro mismo dice que, en ese momento, importaba más explorar el espacio que automatizarlo. No se añade un generador de patrones.

La historia del catálogo no cambia el arnés. Los nombres se movieron: Wrapper pasó a Decorator, Glue a Facade, Solitaire a Singleton, Walker a Visitor. Descubrir que algo es un patrón es lo fácil. Describirlo para quien no lo vio es lo difícil. El conjunto quedó estable a fines de 1992. Las descripciones siguieron moviéndose. Aquí no se rebautiza lo que la matriz ya llama.

### La invitación, y la frase final

Usarlos y buscar otros que encajen con cómo se diseña de verdad. Ser un lector crítico: el patrón saca la decisión de la intuición vaga y deja el costo a la vista, así se puede discutir. Escribir los que uno usa, con otra persona que los apriete.

En el arnés escribir un patrón nuevo no es una feature. Si la misma lección nombra el mismo eje varias veces, esa lección puede volverse una línea del stack. No un catálogo privado en el repositorio de la feature.

La frase final cita a Alexander. Se pueden ensartar patrones de forma floja y obtener un montón de patrones, no algo denso. También se pueden superponer en el mismo espacio, y ahí el conjunto dice más de lo que dice cada pieza. En el arnés la densidad es un módulo profundo que resulta ser dos patrones porque las dos intenciones están en el mismo código. La sarta floja es una clase por patrón, con el nombre del libro en cada una. El primero no se busca. El segundo es el que el revisor deja pasar.

---

## Matriz del capítulo 6

| Fase | Criterio |
| --- | --- |
| PRD | El eje que va a moverse en la vida del producto. Sin catálogo y sin orden de aplicación. |
| SDD | El `D-n` nombra el patrón y el costo. No describe la estructura entera. |
| Implementer | El primer verde es la fase de prototipo: se parece al problema. El patrón es el blanco del refactor, cuando la expansión ya no entra. |
| Revisor | Una sarta de clases con nombre de patrón, o un "usemos X" sin el segundo caso. La densidad en el mismo módulo, con las dos intenciones reales, se queda. |
| Lección | El eje que se repite puede subir al stack. No abre un catálogo en la feature. |

## Conflictos cerrados en este capítulo

* Aplicar los patrones pronto para no refactorizar después, frente a esperar el dolor. El libro dice las dos cosas. Gana la segunda: el patrón es el destino del refactor. Anticipar los veintitrés no evita trabajo. Lo adelanta.
* "Usemos un Observer aquí" como primer movimiento de diseño frente al nombre dicho cuando el eje ya existe. El vocabulario se usa en el `D-n` y en el review. No sustituye al código simple del primer verde.
* Un lenguaje de patrones que genere el programa, al estilo de Alexander, frente al proceso del arnés. El libro niega esa generación. El catálogo no diseña la feature.
* Ensartar patrones en cadena para que el diseño se vea completo, frente a superponerlos en el mismo módulo cuando las dos intenciones son reales. Gana la densidad. La sarta floja es classitis.

## Cierre de la lectura

Los seis capítulos están en este archivo. El catálogo de los veintitrés, la capa y los olores siguen en [`patrones-gof-y-refactoring.md`](patrones-gof-y-refactoring.md). Ningún gate, plantilla ni agente cambió por esta guía. Un patrón entra con el eje ya real, en el sombrero de refactor, con nombre de dominio en la clase y nombre del patrón en el `D-n`.
