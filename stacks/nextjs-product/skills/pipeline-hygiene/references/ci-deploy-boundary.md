# CI vs deploy vs plataforma

| Responsabilidad                 | Dueño lógico                        | Ejemplo                      |
| ------------------------------- | ----------------------------------- | ---------------------------- |
| Lint, typecheck, tests, guards  | CI repo producto                    | azure-pipelines.yml          |
| OCI con secret ephemeral        | build de app                        | Dockerfile y task autorizada |
| Release/Helm frontend           | deploy de producto                  | pipelines/deploy.yml         |
| Front Door/WAF/AKS/Postgres/ACR | landing zone/platform engineering   | fuera del template           |
| Credenciales de Entra/feed      | conexiones y Key Vault corporativos | no PAT YAML ni ZIP           |

Sandbox, nonprod y prod deben diferenciar variables/identidades proporcionadas por plataforma sin crear infraestructura compartida durante deploy. Reportar gaps de acceso y permisos, no ampliar privilegios por comodidad.
