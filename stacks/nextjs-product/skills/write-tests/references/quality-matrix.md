# Quality gates por tipo de cambio

| Cambio             | Gate mínimo                  | Ampliar con                   |
| ------------------ | ---------------------------- | ----------------------------- |
| Domain/application | unit + architecture          | typecheck                     |
| UI client          | component + lint             | a11y, E2E                     |
| Routing/RBAC       | auth tests + architecture    | E2E navegación/guard          |
| Entra/Auth.js      | security + E2E seam          | SSO real con app registration |
| BFF externo        | contract fixtures + security | integración real BFF          |
| Design System      | component + build            | revisión visual/teclado       |
| Tooling/skills     | test:skills + repo-hygiene   | smoke runner                  |
| Docker/CI          | test:repo-hygiene + build    | OCI build y scanning          |

**Regla**: no confundir tests simulados con integración real, no reportar ejecuciones no realizadas. Antes de PR importante: `npm run validate`; para release: `npm run build` y journeys E2E correspondientes.

### BFF central y proxy técnico

| Cambio                           | Gate mínimo                                      | Ampliar con                                |
| -------------------------------- | ------------------------------------------------ | ------------------------------------------ |
| `bff-client.ts` / `clientDirect` | unit + architecture + integración de transportes | E2E directo/proxy bajo entorno configurado |
| Route Handler proxy BFF técnico  | integración HTTP + security + architecture       | E2E sesión/CSRF, SSRF y streaming          |
| Adaptador BFF en feature         | contrato DTO + architecture                      | E2E de funcionalidad real                  |

No bloquear un proxy técnico genérico por las restricciones de APIs de negocio Next.js.
