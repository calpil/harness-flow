---
name: readme-evolution
description: Mantener README.md como descripción viva y declarativa del aplicativo al desarrollar, revisar cambios funcionales y preparar commits, sin convertirlo en changelog ni documentación técnica profunda.
---

# README Evolution — descripción viva del producto CALPIL

## Objetivo y activación

Esta skill mantiene `README.md` alineado con **el estado actual verificable del aplicativo**. Su audiencia son desarrolladores nuevos, Product Owners, líderes y consumidores de la solución. Debe explicar **qué ofrece, para quién, cómo usarlo y qué está disponible realmente**, no cómo está implementado internamente.

**Activación obligatoria:** antes de cerrar una tarea o crear un commit con cambios que podrían modificar capacidades, pantallas, recorridos, comportamientos observables, acceso, integraciones efectivas, limitaciones relevantes o el onboarding del producto. También al eliminar o renombrar funcionalidades. Consultarla incluso si finalmente se decide que el README no requiere cambios.

**No** es un generador de notas de versión, cronología, resumen de commits ni catálogo de clases/APIs.

## Inspección obligatoria

1. Leer `README.md` completo y detectar afirmaciones no sustentadas o desactualizadas.
2. Examinar el cambio real con `git diff --cached --name-status` y `git diff --cached`; si aún no se ha hecho `git add`, incluir `git diff --name-status` y `git diff`.
3. Inspeccionar la UI, las rutas, los casos de uso, los estados visibles, los permisos y las integraciones afectados. No deducir capacidades solo por nombres de archivos ni mensajes de commit.
4. Contrastar con `AGENTS.md`, la documentación específica y, cuando aplique, la evidencia de pruebas/contratos; evitar trasladar esos detalles al README.
5. Leer [criterios y ejemplos](./references/product-readme-guide.md) antes de reescribir una sección sustancial.

## Procedimiento ejecutable

1. **Clasificar impacto.** Preguntar: ¿el cambio altera lo que una persona puede hacer, comprender, configurar o esperar de este aplicativo? Distinguir funcionalidades reales, demos, experimentos y placeholders.
2. **Identificar estado previo.** Señalar la frase, tabla o sección del README que actualmente representa esa capacidad; revisar contradicciones en el resto del documento.
3. **Comprobar el estado nuevo.** Basarse en rutas/comportamiento implementado y pruebas disponibles. Si depende de un BFF, scope, flag, tenant o entorno no validado, expresarlo con precisión.
4. **Decidir modificar o mantener.** Si solo cambian tests, dependencias, código interno, arquitectura o refactor sin impacto perceptible, no editar por obligación. Dejar constancia de «README revisado; no corresponde cambio» en la respuesta del agente.
5. **Editar por sustitución semántica.** Cambiar la descripción anterior, agregar o quitar la capacidad dentro de la sección temática, actualizar recorridos y limitaciones; eliminar afirmaciones obsoletas. No anexar un párrafo de «cambios recientes».
6. **Priorizar lectura de producto.** Inicio breve, valor/alcance, capacidades actuales, experiencia de usuario, acceso y puesta en marcha mínima, límites reales y enlaces a documentación; los títulos se adaptan al producto.
7. **Verificar consistencia.** No prometer producción ni permisos backend por existir una vista demo. Evitar referencias rotas, URLs inventadas, versiones copiadas de memoria y jerga innecesaria.
8. **Preparar commit.** Ejecutar los controles aplicables y, si se solicitó crear el commit, incluir en el staging la edición del README junto con el cambio correspondiente. No hacer commits automáticamente si el usuario no lo ha pedido.

## Patrón de implementación

**En vez de** «2026-10-18: se añadió filtro a Work Items» o «Se implementó `FooAdapter` mediante señales/React state», escribir algo como: «Work Items permite consultar y filtrar elementos por estado y acceder a su detalle», **solo si esas acciones existen**.

**En vez de** añadir un historial al final, integrar la capacidad bajo «Qué puedes hacer» o la descripción de la pantalla. Si una funcionalidad desaparece, retirarla; si pasa de demo a servicio real, sustituir la aclaración de demo por el alcance comprobado.

**Ejemplo de precisión:** «La administración de usuarios ofrece pantallas demostrativas, sin alta/baja real ni autorización de backend» es mejor que «Administración de usuarios disponible» cuando todavía no hay operación real.

Usar las particularidades de cada stack solo como evidencia, no como contenido del README: para Angular, rutas y feature UI; para Next.js, App Router y features. Reservar detalles de MSAL/Auth.js, providers, adapters y pipelines para `docs/` o documentación técnica.

## Decisiones y anti-patrones

- PROHIBIDO `## Changelog`, `## Últimos cambios`, tabla de fechas/SHAs, listado de tickets, «en este commit», «ahora se añadió» o repeticiones de release notes.
- PROHIBIDO copiar indiscriminadamente nombres de funciones, imports, DTOs, carpetas, versiones de cada dependencia o decisiones de código.
- No inflar el README con rutas internas, secretos, configuraciones sensibles ni detalles de deploy; conservar instrucciones mínimas reales para iniciar cuando sean útiles.
- No documentar prototipos como funciones listas para clientes. Rotular DEMO/LOCAL y dependencias de entornos de forma visible.
- No incrementar la longitud por defecto: editar, condensar, unir y eliminar, antes que añadir nuevas secciones.
- No exigir cambios de README si no se modificó el producto observable; el commit no justifica un párrafo nuevo.
- No reescribir el documento entero por cambios triviales. Mantener voz, enlaces útiles y descripción vigente del producto.

## Verificación / Definition of Done

- `README.md` responde qué es, qué resuelve, qué puede hacer la persona hoy, cómo acceder o arrancar y qué no está disponible.
- Capacidad nueva = integrada en la sección temática; capacidad removida = retirada; capacidad modificada = texto reemplazado sin contradicciones.
- No se introdujeron anuncios, roadmaps hipotéticos, changelog ni deep dive técnico.
- Las demos, permisos, integraciones no verificadas y restricciones se representan fielmente.
- Si hay cambios funcionales staged, ejecutar `npm run readme:check` (aviso heurístico) y `npm run test:skills` al modificar la skill; lint/format/validación del proyecto cuando corresponda.
- El chequeo de Git solo detecta **posible necesidad** de revisión: no prueba semánticamente si el README es correcto ni ejecuta esta skill como IA.

## Contrato de entrega del agente

Al cerrar una tarea que incluya o prepare cambios de producto:

1. Indicar `README.md: actualizado` con las secciones afectadas, **o** `README.md: revisado, sin cambios necesarios` con una razón breve.
2. Si se pidió commit: reflejar la edición de README en el mismo commit, nunca en un post-commit que altere el árbol después.
3. Distinguir «funcional», «demo» y «requiere integración» sin inventar aceptación productiva.
4. Declarar las validaciones realmente ejecutadas y cualquier limitación para comprobar la funcionalidad.
