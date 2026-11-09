---
name: write-tests
description: Diseña e implementa pruebas unitarias, de integración y de concurrencia en Go sin mocks frágiles, con fakes deterministas y httptest.
---

# Write Tests — CALPIL Golang Engineering Skill

## Objetivo y activación
Activar cuando se añada nueva funcionalidad, se repare un defecto o se requiera aumentar la cobertura de pruebas en el servicio Go. Guía la escritura de pruebas unitarias puras para el dominio, pruebas con fakes en memoria para use cases y pruebas HTTP con `httptest`.

## Inspección obligatoria
Antes de escribir pruebas, inspecciona:
1. `internal/<feature>/domain/model_test.go`: Patrón existente de pruebas unitarias para entidades de dominio.
2. `internal/<feature>/adapter/in/http/handler_test.go`: Patrón de pruebas para rutas, headers y respuestas JSON/RFC 7807 con `httptest.ResponseRecorder`.
3. `internal/<feature>/adapter/out/persistence/inmemory/`: Uso del repositorio en memoria como fake en las pruebas de casos de uso.

## Procedimiento ejecutable
1. **Determinar el Nivel de Prueba:** Identificar si el cambio requiere prueba de dominio (invariantes y transiciones de estado), prueba de caso de uso (orquestación y eventos) o prueba de integración HTTP (rutas, DTOs y status codes).
2. **Escribir Pruebas de Dominio:** En `domain/<entity>_test.go`, probar exhaustivamente casos válidos e inválidos invocando constructores y métodos de entidad. No usar mocks.
3. **Escribir Pruebas de Caso de Uso:** En `services/service_test.go`, instanciar el servicio inyectando el repositorio `inmemory.NewRepository()` y un reloj fijo para validar fechas deterministas.
4. **Escribir Pruebas de Handler HTTP:** En `adapter/in/http/handler_test.go`, crear un router Chi local, registrar el handler y usar `httptest.NewRequest` y `httptest.NewRecorder` para verificar status code, `Location` header, campos del body y casos de error (400 con `invalidParams`, 404, 422).
5. **Verificar Concurrencia y Race Conditions:** Ejecutar la suite con la bandera de carreras de Go (`go test -race ./...`).
6. **Medir Cobertura:** Comprobar la cobertura de código ejecutando `go test -coverprofile=coverage.out ./...`.

## Patrón de implementación
```go
func TestHandler_CreateWorkItem(t *testing.T) {
    repo := inmemory.NewRepository()
    clock := &fixedClock{now: time.Date(2026, 11, 7, 12, 0, 0, 0, time.UTC)}
    svc := services.NewService(repo, nil, clock)
    h := NewHandler(svc, svc, svc, svc)

    r := chi.NewRouter()
    h.RegisterRoutes(r)

    payload := `{"title":"Refactor Hexagonal","description":"Keep tests clean"}`
    req := httptest.NewRequest(http.MethodPost, "/api/v1/work-items/", strings.NewReader(payload))
    req.Header.Set("Content-Type", "application/json")
    rec := httptest.NewRecorder()

    r.ServeHTTP(rec, req)

    if rec.Code != http.StatusCreated {
        t.Fatalf("expected 201 Created, got %d", rec.Code)
    }
}
```

## Decisiones y anti-patrones
- **NO** usar `time.Sleep()` para sincronizar pruebas asíncronas; usar channels o fakes controlados.
- **NO** depender de servicios de infraestructura externos (ej. base de datos PostgreSQL real activa) para las pruebas unitarias y de handlers HTTP.
- **NO** crear tests que dependan del orden de ejecución de otros tests.

## Verificación / Definition of Done
- Todas las pruebas pasan limpiamente con `go test -v ./...`.
- `go test -race ./...` no detecta ninguna condición de carrera.
- Cobertura de la nueva lógica superior al 80%.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Archivos de test añadidos o actualizados.
2. Escenarios cubiertos (éxito, validación, errores de negocio).
3. Evidencia de paso de `go test -race ./...`.
