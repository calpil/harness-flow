---
description: Evidencia y estándares de pruebas deterministas en Golang
globs: ["**/*_test.go", "tests/**"]
---

# Reglas de Pruebas en Golang

- Todas las pruebas deben ser deterministas, ejecutables en paralelo (`t.Parallel()`) y libres de `time.Sleep()` arbitrarios.
- Pruebas de Dominio: probar entidades y reglas de negocio puras sin mocks ni dependencias de red o base de datos.
- Pruebas de Use Cases: utilizar implementaciones fake de puertos en memoria (`inmemory.NewRepository()`) o relojes controlados (`Clock`).
- Pruebas de Adaptadores HTTP: utilizar `net/http/httptest` con routers chi aislados verificando status codes, DTOs y problem details.
- Ejecutar suite con detector de condiciones de carrera: `go test -race ./...`.
- Cobertura verificable: no dar por terminada una tarea sin pruebas automatizadas que cubran el cambio.
