# Checklist de integración BFF centralizada

- [ ] `bff-client.ts` real ubicado, exportaciones auditadas y reutilizadas.
- [ ] Flag `clientDirect` existente identificado; no duplicado.
- [ ] Browser/directo usa BFF público; browser/proxy usa proxy técnico Next.js; servidor usa transporte server-side.
- [ ] Todos los consumidores de negocio usan el cliente único; excepciones no BFF justificadas.
- [ ] Paths `/bff/v1/{api}/{resource}` y contratos OpenAPI comprobados.
- [ ] BFF público/interno y ambientes sb/np/prod resueltos sin secretos cliente.
- [ ] Access tokens delegados correctamente (no `id_token`); controles SSO, issuer, audience, scopes, roles.
- [ ] Correlation-id, query, body, headers custom, errores, binary/204, timeout/cancel, caching preservados.
- [ ] Proxy genérico sin reglas de negocio, destinos allowlisted y SSRF prevenido.
- [ ] SSR/RSC sin loopback y sin import de módulos server-only al navegador.
- [ ] Lint/reglas de arquitectura evitan `fetch` BFF paralelo en features.
- [ ] Matriz direct/proxy/server y pruebas de contrato ejecutadas con resultados reales.
- [ ] Documentados consumidores migrados, excepciones, riesgos y pendientes E2E.
