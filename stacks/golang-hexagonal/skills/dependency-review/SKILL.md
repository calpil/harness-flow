---
name: dependency-review
description: Evalúa, audita y actualiza dependencias de Go en go.mod garantizando compatibilidad, licencias corporativas permitidas y ausencia de vulnerabilidades.
---

# Dependency Review — CALPIL Golang Engineering Skill

## Objetivo y activación
Activar cuando se proponga agregar, actualizar o eliminar una dependencia en `go.mod`. Garantiza que cada paquete externo esté debidamente justificado, mantenga una licencia permisiva compatible y no introduzca vulnerabilidades de seguridad ni bloat en la aplicación.

## Inspección obligatoria
Antes de modificar dependencias, inspecciona:
1. `go.mod`: Módulos directos e indirectos actualmente registrados.
2. `go.sum`: Checksums criptográficos de dependencias.
3. El paquete candidato en `pkg.go.dev` para evaluar actividad, antigüedad, estrellas y licencias.

## Procedimiento ejecutable
1. **Evaluar Necesidad Real:** Determinar si la funcionalidad requerida puede resolverse limpiamente con la biblioteca estándar de Go (`net/http`, `encoding/json`, `context`, `sync`) antes de agregar un paquete externo.
2. **Revisar Licencia:** Comprobar que la licencia del módulo sea permisiva (MIT, Apache 2.0, BSD). Licencias restrictivas (GPL, AGPL) están prohibidas para código de producto.
3. **Instalar la Dependencia:** Ejecutar `go get <modulo>@vX.Y.Z` especificando una versión semántica estable (evitar pseudo-versiones o branches `main`).
4. **Limpiar el Módulo:** Ejecutar `go mod tidy` para actualizar `go.mod` y `go.sum` eliminando dependencias huérfanas.
5. **Verificar Compilación y Tests:** Asegurar que `go build ./...` y `go test ./...` continúen pasando limpiamente tras la instalación.
6. **Escanear Vulnerabilidades:** Ejecutar `go vet ./...` y herramientas de análisis de dependencias para verificar que la versión no tenga CVEs conocidos.

## Patrón de implementación
```bash
# Agregar una dependencia estable y auditarla
go get github.com/go-chi/chi/v5@v5.5.0
go mod tidy
go test -v ./...
```

## Decisiones y anti-patrones
- **NO** agregar librerías de "utilidades generales" (tipo lodash para Go) si se pueden escribir en 5 líneas de Go estándar.
- **NO** utilizar dependencias abandonadas sin commits en más de 2 años salvo que formen parte del core del lenguaje.
- **NO** ignorar discrepancias en `go.sum`.

## Verificación / Definition of Done
- `go mod tidy` ejecutado sin generar diffs pendientes.
- `go.sum` sincronizado.
- `go build ./...` exitoso.
- Licencia verificada y aprobada.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Nombre y versión exacta del módulo añadido o actualizado.
2. Justificación técnica de la inclusión.
3. Tipo de licencia del paquete.
4. Impacto en el tamaño del binario y estado de las pruebas.
