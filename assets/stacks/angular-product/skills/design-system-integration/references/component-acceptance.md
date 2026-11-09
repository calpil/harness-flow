# Ficha de adopción de componente CALPIL Design System Angular

## Verificación técnica previa

- Paquete y versión resuelta en `npm ls @calpil-ds/angular @calpil-ds/tokens` cuando el feed está autenticado.
- Export **real** en el paquete Angular instalado, selector/import exactos.
- Inputs/Outputs, types, CSS tokens, dependencia de módulo standalone, ejemplos de API.
- Comparación: la exportación React del DS NO demuestra disponibilidad Angular.

## Aceptación funcional/visual

| Estado   | Comprobar                                        |
| -------- | ------------------------------------------------ |
| Default  | labels, hints, variaciones aprobadas             |
| Focus    | ring visible y navegación natural                |
| Disabled | semántica, razón y contrastes                    |
| Error    | mensaje legible y anunciado                      |
| Loading  | feedback perceptible y no interacción accidental |
| Empty    | texto útil y acción siguiente                    |
| Móvil    | layout sin overflow, zoom y touch target         |
| Idiomas  | expansión de cadenas y números/fechas            |

## Política de ownership

- UI base/branding → equipo Design System.
- Composición de páginas, layout de feature y adaptación a flujo de negocio → template/producto.
- Bug de DS → issue upstream y workaround transitorio accesible, no fork invisible.
- CSS global: importar tokens/estilos una vez y evitar duplicados.

## Si el componente NO existe

1. Explicar vacío y alternativa sin prometer API imaginaria.
2. Usar elemento HTML nativo semántico si corresponde, estilizado con tokens disponibles.
3. Registrar necesidad y ownership.
4. Dejar ruta de sustitución por componente oficial.

## Evidencia antes del merge

- Build con paquete del feed, test interacción, foco/teclado, móvil, revisión de snapshot/screenshot si aplica, y nombre del export verificado.
