# Rúbrica de revisión de cambios de agentes

Verificar diff real, no resumen generado:

- Feature contract y errores / código en layer correcto / server-client.
- SSO/Auth.js se invoca por fachada; scopes y permisos no inventados.
- No `src/app/api/` de negocio ni acoplamiento de features.
- DS React componentes verificados, no nombres alucinados.
- UI loading/empty/error y a11y/i18n; data fetch sin loops.
- Tests de regresión relevantes y logs sin secretos.
- package.json + lockfile, pipeline + build reproducibles cuando corresponda.
- El agente reconoce qué no corrió por Node24, feed privado o Entra.

Resultado: Hallazgo (severidad, evidencia, archivo, impacto, corrección) o pass justificado. Es aceptable detener cambios si falta contrato.
