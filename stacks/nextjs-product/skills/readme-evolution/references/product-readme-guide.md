# Guía editorial de README para aplicativos CALPIL

## Principio

El README representa una **fotografía útil del producto en este momento**, no la biografía del repositorio. Si se puede entender el aplicativo sin conocer su framework, el documento está en el nivel correcto.

## Estructura orientativa (no obligatoria)

1. **Nombre y propósito:** qué problema aborda, para quién y cuál es su alcance.
2. **Qué permite hacer:** 3 a 7 capacidades comprobadas, agrupadas por objetivo del usuario.
3. **Recorridos / pantallas:** solo cuando ayudan a una persona a descubrir la navegación.
4. **Acceso y puesta en marcha:** instrucciones mínimas y verificadas para probar la aplicación; enlazar detalles a docs.
5. **Estado y limitaciones:** demos, funciones aún no conectadas, servicios o permisos requeridos.
6. **Documentación adicional:** enlaces de arquitectura, seguridad, operación y contribución fuera del README.

No crear encabezados vacíos; si es un producto pequeño, condensar.

## Ejemplos de transformación (solo si el código lo demuestra)

### Incorporar capacidad

**No:** «feat(work-items) agregó filtro 2026-10-18. Nuevo WorkItemFilterService».  
**Sí:** «En Work Items puedes consultar elementos, filtrarlos por estado y abrir su detalle».

### Renombrar una sección

**No:** «Se cambió /operations por /services».  
**Sí:** Actualizar en la descripción de navegación el nombre de la sección **Servicios** y retirar el nombre anterior de toda la guía, si la UI realmente lo cambió.

### Pasar de maqueta a integración real

**Antes:** «La lista de usuarios utiliza datos de ejemplo».  
**Después:** «La lista de usuarios consulta el servicio corporativo; su disponibilidad depende del acceso y permisos del entorno». Solo afirmar esto con contrato y funcionamiento verificados.

### Feature retirada

Quitarla del mapa de capacidades, revisar links y ajustar el texto de alcance. Nunca agregar «deprecada en fecha…» salvo que sea una limitación útil y actual.

### Cambio puramente interno

«README revisado; no cambia porque el ajuste de repositorios y tests no modifica la experiencia ni los requisitos de operación». No tocar el archivo solo para superar un gate.

## Lenguaje y límites

- Español claro, en presente, desde lo que hace la aplicación.
- No usar vocabulario de implementación salvo términos imprescindibles para arrancar (Node, SSO, comandos).
- No presentar pantallas vacías como módulos funcionales ni mezclar demo con producción.
- Una persona debe poder identificar qué obtiene al ejecutar el producto en menos de dos minutos.
- Los tutoriales extensos, decisiones, matrices de permisos y pipelines deben vivir en `docs/` y enlazarse cuando haga falta.

## Señales de activación por repo

- **Angular:** cambios en `src/app/features/`, `app.routes.ts`, shell, login, configuración pública de runtime o navegación.
- **Next.js:** cambios en `src/features/`, páginas bajo `src/app/`, portal, sesión, permisos o flags que afectan lo visible.
- Ambas: cambios en instrucciones reales de inicio, integración, disponibilidad o limitaciones del aplicativo.

## Checklist de revisión de la descripción

- [ ] Propósito y audiencia siguen correctos.
- [ ] No falta ninguna capacidad nueva de valor para el usuario.
- [ ] Las capacidades retiradas no continúan mencionadas.
- [ ] Ejemplos/demo/pendiente/producido son distinguibles.
- [ ] Las instrucciones de arranque siguen siendo válidas.
- [ ] No aparecen detalles técnicos innecesarios ni cronología de cambios.
- [ ] Se validaron enlaces y no hay contradicciones entre secciones.
