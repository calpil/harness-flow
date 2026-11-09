---
name: form-validation
description: Implementar formularios Next.js/React seguros y accesibles con reglas dominio, errores, guardado y prevención de duplicados.
---

# Form Validation — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/features/operations/ui/new-operation-form.tsx`
- `src/features/operations/domain/operation.ts`
- `tests/component/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Inventariar campos, defaults, formatos, labels y validación funcional derivada de dominio.
2. Normalizar/validar input en frontera adecuada; usar tipos o Zod solo donde contrato lo exija.
3. Evitar doble submit; representar guardando, éxito, error, conflicto y reintento de forma accesible.
4. Mantener composición del lado de servidor para datos y componente client mínimo para UI interactiva.
5. Preservar foco, resumen de errores, aria-describedby e indicadores de campo obligatorio.
6. Probar borde vacío, textos largos, error servidor, request tardía y submit repetido.

## Patrón de implementación

createOperation verifica invariantes; NewOperationForm muestra UI y entrega input a caso de uso/adaptador demo válido.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No confiar únicamente en validación del navegador.
- No llamar DB ni credenciales desde use client.
- No bloquear indefinidamente formulario tras error.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:component
npm run test:unit
npm run test:architecture
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.
