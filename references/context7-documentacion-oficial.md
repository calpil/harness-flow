# Context7 y Documentación Oficial para Stacks Tecnológicos en Harness Flow

Esta referencia define el protocolo obligatorio para mantener todos los stacks tecnológicos, dependencias, patrones de código y versiones **actualizados, libres de APIs obsoletas y protegidos contra vulnerabilidades de seguridad (CVEs)** durante los ciclos de diseño, implementación y revisión de `harness-flow`.

---

## 1. El Problema que Resuelve

Los modelos de lenguaje (LLMs) tienen fechas de corte de entrenamiento fijas (*knowledge cutoff*). Al implementar código en stacks que evolucionan rápidamente (como Angular 19+, Go 1.24+, Next.js 15+, Spring Boot 3.4+, NestJS o FastAPI), los modelos tienden a:
1. Alucinar sintaxis o patrones deprecados (ej. `*ngIf` en Angular en lugar de `@if`; directivas antiguas en Next.js; imports obsoletos en Go o Spring).
2. Introducir versiones desactualizadas de paquetes con vulnerabilidades conocidas (CVEs).
3. Diseñar arquitecturas incompatibles con los cambios mayores recientes de las librerías.

---

## 2. Context7 (Upstash MCP): Documentación Versionada en Vivo

**Context7** es un servidor Model Context Protocol (MCP) especializado en proveer documentación actualizada y ejemplos de código específicos de versión directamente al contexto del LLM.

### Configuración de Context7 por Host
* **Endpoint HTTP estándar:** `https://mcp.context7.com/mcp`
* **Claude Code:**
  ```bash
  claude mcp add --transport http context7 https://mcp.context7.com/mcp
  ```
* **Cursor / Windsurf:** Añadir a `mcp.json`:
  ```json
  {
    "mcpServers": {
      "context7": {
        "url": "https://mcp.context7.com/mcp"
      }
    }
  }
  ```
* **AGY / Gemini:** Instalar el plugin `context7` desde el marketplace o usar el endpoint HTTP.

### Herramientas Expuestas por Context7
1. `resolve-library-id`: Resuelve el nombre común de un paquete o framework a su ID de repositorio (ej. `Angular` -> `/angular/angular`, `Next.js` -> `/vercel/next.js`, `Go Chi` -> `/go-chi/chi`).
2. `query-docs`: Consulta documentación oficial focalizada y ejemplos de código para una versión específica o concepto particular.

---

## 3. Matriz de Fuentes Oficiales y Comandos de Seguridad por Stack

| Stack Tecnológico | Context7 Library ID | Documentación Oficial | Scanner de Vulnerabilidades | Versión Mínima Soportada |
| :--- | :--- | :--- | :--- | :--- |
| **`golang-hexagonal`** | `/golang/go`, `/go-chi/chi` | [go.dev/doc](https://go.dev/doc/) | `govulncheck ./...` | Go 1.23+ (recomendado 1.24+) |
| **`angular-product`** | `/angular/angular` | [angular.dev](https://angular.dev) | `npm audit --audit-level=high` | Angular 19+ |
| **`nextjs-product`** | `/vercel/next.js` | [nextjs.org/docs](https://nextjs.org/docs) | `npm audit --audit-level=high` | Next.js 15+ / React 19 |
| **`springboot-hexagonal`** | `/spring-projects/spring-boot` | [docs.spring.io](https://docs.spring.io/spring-boot/) | `./mvnw org.owasp:dependency-check-maven:check` | Java 21 LTS / Spring Boot 3.4+ |
| **`nestjs-hexagonal`** | `/nestjs/nest` | [docs.nestjs.com](https://docs.nestjs.com) | `npm audit --audit-level=high` | NestJS 10+ |
| **`python-dataproduct`** | `/tiangolo/fastapi`, `/pola-rs/polars` | [fastapi.tiangolo.com](https://fastapi.tiangolo.com) | `pip-audit` o `safety check` | Python 3.12+ (recomendado 3.14) |

---

## 4. Protocolo Obligatorio por Rol de Harness Flow

### Rol 0: Producto (PRD y SDD)
- Al redactar el borrador del SDD (`docs/sdd.md`), la sección `## Contexto` y `## Decisiones` **debe declarar explícitamente las versiones mayores vigentes del stack**.
- Prohibido asumir o fijar versiones obsoletas sin verificar su estado de soporte y parches de seguridad (LTS).

### Rol 1: Leader (Spec y Criterios de Aceptación)
- Al definir dependencias de terceros o contratos de API, contrastar con la documentación oficial o Context7 para no solicitar métodos que fueron deprecados en la versión en uso.

### Rol 2: Implementer (TDD y Modo Pair)
- **Antes de escribir código nuevo o agregar dependencias:**
  1. Si Context7 MCP está conectado, consultar la documentación específica de la versión:
     - Prompt con sufijo: `"use context7"` o llamada directa a `query-docs`.
  2. Si Context7 no está disponible, consultar la documentación oficial vía `search_web`:
     - Consulta dirigida: `"[framework] [metodo] latest documentation and breaking changes"`.
  3. Ejecutar el escáner de seguridad correspondiente (`govulncheck`, `npm audit`, `pip-audit`) antes de registrar evidencia en `docs/impl-<id>.md`.
  4. Ningún commit debe introducir dependencias con severidad crítica o alta sin justificación explícita documentada en `docs/development/dependencies.md`.

### Rol 3: Reviewer (Revisión Independiente)
- El subagente revisor verifica que el diff:
  1. No utilice APIs marcadas como `@deprecated`.
  2. No introduzca librerías abandonadas o con reportes públicos de vulnerabilidad (CVEs).
  3. Cumpla los estándares de seguridad declarados en `.claude/rules/security.md` y `AGENTS.md`.
- **Cualquier vulnerabilidad de seguridad conocida o API obsoleta que comprometa la estabilidad DEBE ser clasificada como hallazgo BLOQUEANTE o MAYOR.**

---

## 5. Comando CLI de Auditoría en Harness Flow

Para auditar el estado de dependencias y versiones de cualquier proyecto o microservicio:

```bash
# Diagnóstico de stack y seguridad
$PY "$H/stack.py" auditar [--repo <ruta>]
```
