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
* **GPT / Codex** (`~/.codex/config.toml`):
  ```toml
  [mcp_servers.context7]
  url = "https://mcp.context7.com/mcp"
  ```
* **Gemini CLI** (`~/.gemini/settings.json`, dentro de `mcpServers`):
  ```json
  { "context7": { "httpUrl": "https://mcp.context7.com/mcp" } }
  ```
* **AGY / Antigravity** (su archivo de configuración MCP, dentro de `mcpServers`):
  ```json
  { "context7": { "serverUrl": "https://mcp.context7.com/mcp" } }
  ```
* **Grok:**
  ```bash
  grok mcp add --transport http context7 https://mcp.context7.com/mcp
  ```
  Queda en `~/.grok/config.toml` como `[mcp_servers.context7]` con `url = "..."`.
* **Hermes** (`~/.hermes/config.yaml`):
  ```yaml
  mcp_servers:
    context7:
      url: https://mcp.context7.com/mcp
  ```
* **Kimi Code:** no está verificado en una instalación real. Context7 documenta que cualquier
  cliente MCP se conecta con la URL de arriba; sigue la guía de servidores MCP de Kimi.

Cada host nombra la clave de la URL a su manera (`url`, `httpUrl`, `serverUrl`): copiar el bloque
de un host en otro deja el servidor sin conectar y sin error visible. Fuentes: la guía de clientes
de Context7 (Codex, Gemini CLI, Antigravity) y la documentación de MCP de Grok y de Hermes.

**Clave de API.** Con clave (límites más altos) va en el header `Authorization: Bearer <clave>`:
`http_headers` en Codex, `headers` en los demás. Es un secreto: va en la configuración personal
del host, NUNCA en el repo ni en un `AGENTS.md`.

### Cuando Context7 no está conectado
Reinicia el agente después de configurarlo. Si en un host no está disponible:

1. Usa la documentación oficial del stack (sección 3) por web.
2. Si tampoco hay acceso web, NO des la verificación por hecha: el implementer lo declara en
   `docs/impl-<id>.md` y el revisor en `docs/review-<id>.md`, con la lista de dependencias y APIs
   nuevas que quedaron sin contrastar. Una verificación que no se pudo hacer no cuenta como hecha.

### Herramientas Expuestas por Context7
1. `resolve-library-id`: Resuelve el nombre común de un paquete o framework a su ID de repositorio (ej. `Angular` -> `/angular/angular`, `Next.js` -> `/vercel/next.js`, `Go Chi` -> `/go-chi/chi`).
2. `query-docs`: Consulta documentación oficial focalizada y ejemplos de código para una versión específica o concepto particular.

---

## 3. Matriz de Fuentes Oficiales y Comandos de Seguridad por Stack

| Stack Tecnológico | Context7 Library ID | Documentación Oficial | Scanner de Vulnerabilidades | Versión Mínima Soportada |
| :--- | :--- | :--- | :--- | :--- |
| **`golang-hexagonal`** | `/golang/go`, `/go-chi/chi` | [go.dev/doc](https://go.dev/doc/) | `govulncheck ./...` | Go 1.23+ (recomendado 1.24+) |
| **`angular-product`** | `/angular/angular` | [angular.dev](https://angular.dev) | `npm audit --audit-level=high` | Angular 19+ |
| **`dotnet-hexagonal`** | `/dotnet/runtime` | [learn.microsoft.com/dotnet](https://learn.microsoft.com/en-us/dotnet/) | `dotnet list package --vulnerable` | .NET 8.0 LTS / .NET 10.0+ |
| **`rust-hexagonal`** | `/tokio-rs/axum`, `/rust-lang/rust` | [doc.rust-lang.org](https://doc.rust-lang.org/) | `cargo audit` | Rust 2021+ (recomendado 2024) |
| **`nextjs-product`** | `/vercel/next.js` | [nextjs.org/docs](https://nextjs.org/docs) | `npm audit --audit-level=high` | Next.js 15+ / React 19 |
| **`springboot-hexagonal`** | `/websites/spring_io_spring-boot` | [docs.spring.io](https://docs.spring.io/spring-boot/) | `./mvnw org.owasp:dependency-check-maven:check` | Java 21 LTS / Spring Boot 3.4+ |
| **`nestjs-hexagonal`** | `/nestjs/docs.nestjs.com` | [docs.nestjs.com](https://docs.nestjs.com) | `npm audit --audit-level=high` | NestJS 10+ |
| **`python-dataproduct`** | `/websites/fastapi_tiangolo` (Polars: resolver con `resolve-library-id`) | [fastapi.tiangolo.com](https://fastapi.tiangolo.com) | `pip-audit` o `safety check` | Python 3.12+ (recomendado 3.14) |
| **`ios-swiftui-clean`** | `/swiftlang/swift` | [developer.apple.com/documentation/swift](https://developer.apple.com/documentation/swift) | `osv-scanner --lockfile=Package.resolved` | Swift tools 6.0+ |
| **`android-compose-clean`** | `/websites/developer_android_develop_ui_compose` | [developer.android.com/docs](https://developer.android.com/docs) | `./gradlew dependencyCheckAnalyze` | Kotlin 2.0.0+ |

---

## 4. Protocolo Obligatorio por Rol de Harness Flow

**Cómo llega esto a cada rol, en cualquier host.** No depende de que el agente abra esta
referencia. Por cada stack que la feature toca, `contexto.py brief` (leader e implementer) y
`revision.py --briefing` (revisor) imprimen el bloque `DOCUMENTACION VIGENTE DEL STACK`:
documentación oficial, id de librería de Context7, consultas sugeridas y escáner de dependencias,
tomados del `manifest.json` del stack. El rol producto lo recibe de todos los repos del proyecto
al crear el borrador del SDD (`producto.py borrador --doc sdd`, o `contexto.py stacks`). La norma
`[documentacion]` del bloque `NORMAS DE INGENIERIA` dice qué hacer con ello, y es la misma que el
revisor audita. La consulta a Context7 la hace el agente con el MCP de su host: ningún script se
conecta a Context7.

**`stack.py auditar --repo <ruta>` mide, no informa.** Corre el escáner del stack y sale con
exit 0 si está limpio, exit 1 si reporta hallazgos y exit 2 si no pudo medir (escáner no
instalado, stack sin escáner declarado o repo sin stack). Un exit 2 no es un verde: instala el
escáner o deja escrito en la evidencia que la auditoría no se hizo.

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
  3. Si el cambio agrega o sube una dependencia, ejecutar `stack.py auditar --repo <ruta>` (corre el escáner del stack: `govulncheck`, `npm audit`, `pip-audit`...) antes de registrar evidencia en `docs/impl-<id>.md`. Exit 1 o exit 2 no se dan por buenos.
  4. Ningún commit debe introducir dependencias con severidad crítica o alta sin justificación explícita documentada en `docs/development/dependencies.md`.

### Rol 3: Reviewer (Revisión Independiente)
- El subagente revisor verifica que el diff:
  1. No utilice APIs marcadas como `@deprecated`.
  2. No introduzca librerías abandonadas o con reportes públicos de vulnerabilidad (CVEs).
  3. Cumpla los estándares de seguridad de `security.md` del stack (su texto va en el briefing; en el repo vive en `.claude/rules/`, `.agents/rules/` o `.gemini/rules/`) y de `AGENTS.md`.
- **Cualquier vulnerabilidad de seguridad conocida o API obsoleta que comprometa la estabilidad DEBE ser clasificada como hallazgo BLOQUEANTE o MAYOR.**

---

## 5. Comando CLI de Auditoría en Harness Flow

Para auditar el estado de dependencias y versiones de cualquier proyecto o microservicio:

```bash
# Diagnóstico de stack y seguridad
$PY "$H/stack.py" auditar [--repo <ruta>]
```
