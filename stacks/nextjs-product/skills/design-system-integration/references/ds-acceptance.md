# Design System `@calpil-ds/react` — aceptación

1. Inspect installed exports/types and package version; no inventar nombre de componente.
2. Login usa ventana corporativa oficial y Auth.js maneja invocación SSO, no DS.
3. Tokens DS se respetan en colores, spacing, typography y estados.
4. Estados empty/loading/error, foco y navegación teclado probados.
5. Textos traducidos, long labels, navegación móvil, reduced motion cubiertos.
6. Si una API del DS falla o no está instalada, registrar bloqueante, no falsificar implementación.
7. DS React se consume solo desde UI/composición; jamás domain/application.
