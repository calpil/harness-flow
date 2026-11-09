---
name: add-api-endpoint
description: Diseña e implementa endpoints REST versionados en Go con Chi Router sobre puertos hexagonales, validación de DTOs, RFC 7807 ProblemDetail y contratos OpenAPI.
---

# Add API Endpoint — CALPIL Golang Engineering Skill

## Objetivo y activación
Activar cuando el usuario o la historia requiera agregar o modificar un endpoint HTTP REST en el servicio Go. Guía la creación de rutas, DTOs de request/response, validaciones estructuradas, códigos de estado HTTP y mapeo hacia los casos de uso correspondientes.

## Inspección obligatoria
Antes de escribir código, inspecciona:
1. `internal/<feature>/adapter/in/http/handler.go`: Estructura actual de rutas y handlers.
2. `internal/<feature>/adapter/in/http/dto.go`: DTOs existentes y patrones de validación.
3. `internal/<feature>/application/ports/in.go`: Casos de uso disponibles para consumir.
4. `internal/platform/httputil/problem_detail.go`: Utilidades para emisión de errores RFC 7807.
5. `api/openapi.yaml`: Especificación de la API para mantener el contrato actualizado.

## Procedimiento ejecutable
1. **Definir el contrato:** Especificar método HTTP, ruta bajo `/api/v1/...`, payload esperado, query params y códigos de respuesta (200, 201, 204, 400, 404, 422).
2. **Crear DTOs:** Declarar en `dto.go` la estructura de request y response con etiquetas `json:"..."`. Implementar método `Validate() []httputil.InvalidParam`.
3. **Mapear a Use Case:** Identificar o declarar el comando de entrada en `ports/in.go` y adaptar los datos limpios del DTO al comando.
4. **Implementar el Handler:** Agregar la función handler en `handler.go`, decodificar JSON, validar input, invocar el caso de uso y escribir respuesta con `httputil.WriteJSON` o `httputil.WriteProblem`.
5. **Registrar la Ruta:** Enlazar el nuevo handler dentro de `RegisterRoutes(r chi.Router)`.
6. **Actualizar OpenAPI:** Documentar el endpoint, parámetros y esquemas en `api/openapi.yaml`.
7. **Escribir Pruebas:** Crear casos de prueba en `handler_test.go` cubriendo caso exitoso (2xx), payload inválido (400) y caso no encontrado o error de negocio (4xx/5xx).

## Patrón de implementación
```go
// En dto.go
type CreateResourceRequest struct {
    Name string `json:"name"`
}

func (r *CreateResourceRequest) Validate() []httputil.InvalidParam {
    var errs []httputil.InvalidParam
    if strings.TrimSpace(r.Name) == "" {
        errs = append(errs, httputil.InvalidParam{Name: "name", Reason: "name is required"})
    }
    return errs
}

// En handler.go
func (h *Handler) Create(w http.ResponseWriter, r *http.Request) {
    var req CreateResourceRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        httputil.WriteProblem(w, http.StatusBadRequest, "Invalid Request Body", "Malformed JSON", r.URL.Path)
        return
    }
    if params := req.Validate(); len(params) > 0 {
        httputil.WriteProblem(w, http.StatusBadRequest, "Validation Failed", "Invalid input", r.URL.Path, params...)
        return
    }
    // Invocar use case y responder 201
}
```

## Decisiones y anti-patrones
- **NO** colocar lógica de negocio ni transacciones de base de datos dentro de los handlers HTTP.
- **NO** exponer estructuras o entidades de dominio directamente en la respuesta JSON; usar siempre DTOs de salida.
- **NO** responder errores genéricos en texto plano; usar siempre el estándar RFC 7807 (`application/problem+json`).
- **NO** omitir validación de longitud o formato de strings en los requests entrantes.

## Verificación / Definition of Done
- `go test -v ./internal/<feature>/adapter/in/http/...` ejecutado y pasando al 100%.
- El endpoint responde con cabeceras `Content-Type: application/json` o `application/problem+json`.
- `api/openapi.yaml` refleja fielmente el nuevo recurso.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Método y ruta añadida o modificada.
2. DTOs y validaciones incorporadas.
3. Casos de prueba añadidos y resultado de ejecución.
4. Sección actualizada en `api/openapi.yaml`.
