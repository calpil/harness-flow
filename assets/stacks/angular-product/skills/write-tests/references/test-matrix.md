# Matriz mínima de verificación de vertical Angular

| Capa        | Happy path                   | Bordes                 | Fallas                         | Herramienta         |
| ----------- | ---------------------------- | ---------------------- | ------------------------------ | ------------------- |
| Domain      | creación válida/transición   | blanco/máximo/terminal | regla inválida                 | Jasmine TS          |
| Application | comandos/Signals             | paginación/vacío       | adapter error/latencia         | fake port + TestBed |
| Data-access | GET/POST/PATCH + mapper      | nulls/query            | 401/403/404/409/timeout        | Http testing        |
| UI          | render/submit/navigate       | keyboard/móvil/empty   | loading/error/retry            | component tests     |
| SSO         | guard/allowlist              | origin/path/scope      | interaction required/401       | MSAL fake           |
| Runtime     | config parse antes bootstrap | URL same-origin        | secret/tenant/esquema inválido | unit                |
| E2E         | login mock + workflow        | deep link/reload       | error y retorno                | Playwright          |

## Disciplina de evidencia

- Si `npm ci` falló por Artifacts, ningún comando posterior basado en dependencias puede marcarse como aprobado.
- No usar `it.skip`, snapshots masivos ni fixtures de producción para alcanzar cobertura.
- Tests unitarios no prueban que exista endpoint real.
- E2E con bypass local NO valida Entra tenant ni BFF.

## Ejemplo de reportabilidad honesta

| Comprobación                | Resultado | Evidencia                             |
| --------------------------- | --------- | ------------------------------------- |
| `npm run test:architecture` | Pass      | stdout del validador                  |
| `npm run test`              | Blocked   | feed privado no accesible             |
| `npm run test:e2e`          | Not run   | navegador/dependencias no disponibles |
| SSO real                    | Pending   | requiere tenant+backend               |

Un PR de seguridad debe añadir pruebas **negativas** de que el bearer no llega a orígenes no autorizados.
