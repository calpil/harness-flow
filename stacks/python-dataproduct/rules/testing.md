---
description: Estándares de pruebas automatizadas deterministas en Python con Pytest
globs: ["tests/**", "test_*.py"]
---

# Reglas de Pruebas en Python Data Product

- Todas las pruebas deben ser deterministas y ejecutarse con `pytest -q`.
- PROHIBIDO el uso de `time.sleep` en pruebas unitarias; emplear `freezegun`, `FakeClock` o sincronización determinista.
- **Pruebas de Dominio:** Probar transformaciones, validaciones e invariantes directamente sobre modelos de dominio sin mocks pesados.
- **Pruebas de Ingesta y Pipelines:** Emplear DataFrames en memoria (Polars) o mocks de conectores para asegurar rapidez de ejecución.
- **Pruebas de API:** Usar `TestClient` de FastAPI para probar contratos HTTP, validaciones de esquemas y códigos de estado.
