# Patrones de Diseño y la Raíz de Composición en Arquitectura Hexagonal

Este documento aclara la relación dialéctica entre la **centralización en la Raíz de Composición (*Composition Root*)** y la **aplicación de Patrones de Diseño (GoF)** dentro de las arquitecturas hexagonales y limpias de Harness Flow.

---

## 1. La Aparente Paradoja

Al establecer que:
1. *La creación e instanciación de dependencias se centraliza en un único lugar: la Raíz de Composición (`main.go`, `Program.cs`, `main.ts`, arranque de Spring).*
2. *El dominio y los casos de uso no instancian infraestructura ni adaptadores, recibiendo interfaces construidas vía inyección de dependencias.*

Surge con frecuencia la duda: **¿Significa esto que no se pueden aplicar patrones de diseño en el código de la feature o del dominio?**

**La respuesta es no: los patrones de diseño se aplican profusamente.** El malentendido proviene de asumir que todos los patrones son *creacionales* o que todos los patrones sirven para instanciar bases de datos y clientes de red.

De los 23 patrones canónicos de GoF (1994):
* Solo **5 son creacionales** (Abstract Factory, Builder, Factory Method, Prototype, Singleton).
* **7 son estructurales** (Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy).
* **11 son de comportamiento** (Strategy, State, Command, Observer, Template Method, Iterator, Visitor, Mediator, Memento, Chain of Responsibility, Interpreter).

La arquitectura hexagonal no elimina los patrones de diseño; define **el lugar exacto y la capa de responsabilidad donde cada patrón debe vivir**.

---

## 2. Mapa de Patrones por Capa Hexagonal

```
+--------------------------------------------------------------------------+
| 1. CAPA DE DOMINIO (Reglas de Negocio Puras - 0 frameworks, 0 BD)        |
|    • Strategy: Algoritmos de cálculo (descuentos, tarifas, impuestos).   |
|    • State: Ciclo de vida de entidades (Pedido: Creado -> Pagado -> Env).|
|    • Composite: Jerarquías de árbol (catálogos, combos de productos).    |
|    • Domain Factory: Métodos estáticos puros para fabricar entidades.    |
|    • Iterator: Recorrido uniforme de colecciones de dominio.             |
+--------------------------------------------------------------------------+
                                    ▲
                                    │ (Usa casos de uso)
+--------------------------------------------------------------------------+
| 2. CAPA DE APLICACIÓN (Casos de Uso / Orquestación)                      |
|    • Command: Encapsular la intención de un caso de uso como objeto.     |
|    • Observer / Mediator: Suscripción y despacho de eventos de dominio.  |
|    • Chain of Responsibility: Pipelines de validación o middleware.      |
+--------------------------------------------------------------------------+
                                    ▲
                                    │ (Implementa puertos)
+--------------------------------------------------------------------------+
| 3. CAPA DE ADAPTADORES (Infraestructura / I/O / Red / BD)                |
|    • Adapter: Implementar un puerto del dominio para PostgreSQL o Kafka. |
|    • Decorator / Proxy: Envolver un adaptador para agregar Outbox,       |
|      Circuit Breakers, métricas o caching sin tocar el dominio.          |
|    • Facade: Simplificar APIs de librerías o SDKs externos complejos.    |
+--------------------------------------------------------------------------+
                                    ▲
                                    │ (Construye y enlaza todo)
+--------------------------------------------------------------------------+
| 4. RAÍZ DE COMPOSICIÓN (main.go, Program.cs, main.ts, Assembly Root)     |
|    • Abstract Factory / Builder: Ensamblar el grafo de infraestructura   |
|      y seleccionar implementaciones según el ambiente o configuración.   |
+--------------------------------------------------------------------------+
```

---

## 3. Ejemplo Práctico: División de Responsabilidades en Código

### A. En el Dominio: Patrón Strategy (Puro, sin dependencias)
El cálculo de envíos cambia según la modalidad de despacho. Esto se modela con el patrón **Strategy** dentro del dominio:

```typescript
// Dominio: Interfaz y estrategias de negocio
export interface TarifaStrategy {
  calcular(pesoKg: number): Dinero;
}

export class TarifaNacional implements TarifaStrategy {
  calcular(pesoKg: number): Dinero {
    return Dinero.pesos(pesoKg * 1000);
  }
}

export class TarifaInternacionalExpress implements TarifaStrategy {
  calcular(pesoKg: number): Dinero {
    return Dinero.dolares(pesoKg * 25);
  }
}

// Entidad de negocio que utiliza la estrategia
export class Envio {
  constructor(private readonly tarifa: TarifaStrategy) {}

  public cotizar(peso: number): Dinero {
    return this.tarifa.calcular(peso);
  }
}
```
*El dominio contiene y ejecuta el patrón Strategy con lógica pura de negocio, inmune a bases de datos y librerías externas.*

---

### B. En la Infraestructura: Patrón Decorator (Cross-Cutting Concerns)
El dominio define el puerto de persistencia `EnvioRepository`. En la capa de adaptadores, implementamos el adaptador concreto de PostgreSQL y lo envolvemos con un **Decorator** para registrar métricas de observabilidad sin contaminar el dominio:

```typescript
// Adaptador Decorator: envuelve cualquier EnvioRepository
export class EnvioRepositoryConMetricas implements EnvioRepository {
  constructor(private readonly decorado: EnvioRepository) {}

  async guardar(envio: Envio): Promise<void> {
    const inicio = Date.now();
    await this.decorado.guardar(envio);
    metricas.registrarLatencia("envio.guardado", Date.now() - inicio);
  }
}
```

---

### C. En la Raíz de Composición (`main`): Ensamblado Unificado
En el punto de entrada de la aplicación (`main.ts`, `Program.cs` o `main.go`), es donde se instancian las clases concretas y se tejen las dependencias:

```typescript
// main.ts (Composition Root)
function bootstrap() {
  // 1. Instanciación de infraestructura concreta
  const dbPool = new PostgresPool(config.databaseUrl);
  const repoBase = new PostgresEnvioRepository(dbPool);
  const repoDecorado = new EnvioRepositoryConMetricas(repoBase); // Patrón Decorator

  // 2. Selección de estrategia de negocio según configuración
  const estrategia: TarifaStrategy = config.esInternacional
    ? new TarifaInternacionalExpress()
    : new TarifaNacional();

  // 3. Caso de uso ensamblado vía inyección de dependencias
  const casoDeUso = new CrearEnvioUseCase(repoDecorado, estrategia);

  // 4. Iniciar servicio / controladores HTTP
  iniciarServidorHttp(casoDeUso);
}
```

---

## 4. Reglas Operativas para el Implementer y el Revisor

| Concepto | Permitido y Alentado | Prohibido y Rechazado por el Revisor |
| :--- | :--- | :--- |
| **Instanciación** | Hacer `new` de infraestructura y adaptadores únicamente en la Raíz de Composición (`main`). | Hacer `new PostgresRepository()` o `new HttpClient()` dentro de entidades, servicios o casos de uso. |
| **Patrones de Dominio** | Usar Strategy, State, Composite, Domain Factories y Value Objects para encapsular lógica de negocio. | Dispersar lógica condicional compleja en escaleras infinitas de `if/else` en vez de usar polimorfismo o tablas. |
| **Patrones de Infraestructura**| Usar Adapter para puertos y Decorator/Proxy para Outbox, OCC, Circuit Breakers, caching y métricas. | Acoplar el caso de uso a librerías de infraestructura concretas (AWS SDK, Redis client, RabbitMQ). |
| **Singleton** | Crear una única instancia en la Raíz de Composición y pasarla por inyección de dependencias (constructor). | Crear métodos estáticos globales (`Clase.getInstance()` / `Clase.Instance()`) que ocultan dependencias. |

---

## 5. Conclusión

Centralizar la creación en la Raíz de Composición no elimina los patrones de diseño; **los desintoxica del acoplamiento accidental**. 

Permite que:
1. **Los patrones de dominio** permanezcan 100% puros y testeables en memoria en microsegundos, sin necesidad de levantar bases de datos ni mocks pesados.
2. **Los patrones estructurales de infraestructura** añadan resiliencia y observabilidad alrededor de los puertos de forma transparente.
3. **El código cumpla los principios SOLID** al tener dependencias explícitas declaradas en constructores en lugar de accesos globales ocultos.

---
*Referencias complementarias en el arnés:*
* [`references/patrones-gof-y-refactoring.md`](../references/patrones-gof-y-refactoring.md): Matriz de los 23 patrones GoF por capa hexagonal y catálogo de Code Smells.
* [`references/design-patterns-gof.md`](../references/design-patterns-gof.md): Guía operativa de cuándo entra cada patrón en el ciclo de vida del arnés.
