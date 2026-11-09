---
description: Reglas de dependencias y gobierno de paquetes Python con Poetry / Pip
globs: ["pyproject.toml", "requirements*.txt"]
---

# Reglas de Dependencias en Python Data Product

- Versión base de Python: 3.12+ (recomendado 3.14).
- Toda adición de dependencias debe justificar su necesidad técnica frente a la biblioteca estándar.
- Fijar versiones semver estrictas en `pyproject.toml`.
- Cero dependencias externas de I/O en la capa `domain/`.
- Escaneo obligatorio de vulnerabilidades conocidas mediante `pip-audit` o `safety check`.
- PROHIBIDO introducir dependencias sin licencia compatible con uso empresarial.
