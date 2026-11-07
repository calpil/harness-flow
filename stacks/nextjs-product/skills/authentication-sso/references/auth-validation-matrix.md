# Matriz Entra ID / Auth.js

| Situación                   | Navegación            | Endpoint protegido (si es técnico/permitido) | Validación                       |
| --------------------------- | --------------------- | -------------------------------------------- | -------------------------------- |
| Anónimo                     | /login                | 401                                          | login page y guards              |
| Usuario autenticado sin rol | error/acceso denegado | 403                                          | roles server-side                |
| Usuario autorizado          | contenido             | 200                                          | session facade + pruebas         |
| Cookie manipulada           | sesión rechazada      | 401                                          | cookie en proxy NO es validación |
| Token expirado              | reautenticación       | 401                                          | Auth.js, no UI-only              |
| Health probe                | público               | 200                                          | AKS no debe depender de auth     |
| OAuth secreto inválido      | login falla sin leak  | n/a                                          | requiere entorno real            |

Referencias: `src/auth.ts`, `src/server/auth/session.ts`, `proxy.ts`, `src/app/api/auth/`.

Nunca exponer secretos de servidor, refresh tokens ni cookies HttpOnly al JavaScript del navegador. Para `clientDirect=true` solamente podrá utilizarse un access token delegado emitido para el BFF (audience/scopes verificados) mediante flujo aprobado y protección frente a XSS; si no existe, tratar el modo directo como bloqueo funcional sin inventar bypass. Para `clientDirect=false`, tokens privados permanecen en el transporte de servidor y el proxy aplica controles de sesión/CSRF. Para un BFF NestJS externo negociar delegación/OBO cuando aplique. Un `id_token` de login NO acredita acceso a una API arbitraria. Los tests de `E2E_TEST_AUTH=true` prueban guards, NO autenticación Microsoft real.
