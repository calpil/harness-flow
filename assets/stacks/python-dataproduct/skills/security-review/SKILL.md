---
name: security-review
description: Review a scoped source, API, persistence or configuration change for concrete security issues.
---

# Security Review — CALPIL Python Data Product

Sigue `AGENTS.md` y la regla de seguridad del stack (`rules/security.md` en `.agents/rules/`, `.claude/rules/`, `.gemini/rules/` o `.grok/rules/`). Delimita primero la superficie de ataque y las fronteras de confianza; reporta hallazgos respaldados por `archivo:línea`, no listas genéricas.

## Inspección obligatoria por vector OWASP

1. **Control de acceso (A01):** confirmar que cada endpoint FastAPI verifica autenticación, rol/permiso y filtro por `tenant_id`/propietario en queries (cero IDOR ni tenant crossing).
2. **Secretos y transporte (A02):** buscar credenciales, API keys, tokens o cadenas de conexión hardcodeadas en `src/`, `tests/` y configuración; verificar carga vía `pydantic-settings` y TLS validado (`verify=True`, prohibido `verify=False`).
3. **Inyección SQL y de comandos (A03):** confirmar consultas parametrizadas al 100% (prohibidos f-strings o concatenación en SQL) y llamadas a subprocesos sin `shell=True`.
4. **Configuración y errores (A05):** validar esquemas Pydantic estrictos en la frontera, cabeceras de seguridad (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Content-Security-Policy`; sin `X-XSS-Protection`), y respuestas RFC 7807 sin stack traces ni detalles de BD.
5. **Dependencias (A06):** ejecutar `stack.py auditar --repo <repo>` (`pip-audit`) y verificar cero CVEs altos/críticos.
6. **Autenticación y JWT (A07):** validar firma, algoritmo explícito (`alg != "none"`), `iss`, `aud` y `exp`; prohibido omitir verificación de firma.
7. **Deserialización e integridad (A08):** prohibido `pickle.loads`, `marshal`, `eval`, `exec` o `yaml.load` sin `SafeLoader` sobre datos externos o de red; usar JSON/Pydantic o Parquet validado.
8. **Logs y privacidad (A09):** confirmar que los logs estructurados incluyen `correlation_id` pero jamás imprimen contraseñas, tokens, secretos ni PII.
9. **Anti-SSRF (A10):** en clientes HTTP salientes (`httpx`/`requests`) hacia URLs externas, validar whitelist de dominios y bloquear IPs privadas/loopback/metadata cloud (`169.254.169.254`).
10. **Tests negativos:** comprobar al menos un test de rechazo (`401`/`403`/`422`) por endpoint protegido.

## Reglas y entrega

- **NO** imprimir el valor real de un secreto encontrado: reportar solo `archivo:línea`, severidad (`BLOQUEANTE`/`MAYOR`/`MENOR`), impacto y remediación mínima.
- **NO** modificar código salvo que se solicite explícitamente; separar hallazgos confirmados de supuestos que requieren verificación en entorno.
