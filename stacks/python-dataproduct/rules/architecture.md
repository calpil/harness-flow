---
description: Límites de Clean Architecture y Data Product en Python / FastAPI / Polars
globs: ["src/**", "tests/**"]
---

# Reglas de Arquitectura en Python Data Product

- **Capa Dominio (`src/**/domain/**/*.py`):**
  - Python estándar independiente de frameworks.
  - PROHIBIDO importar FastAPI, Pydantic (en entidades puras), SQLAlchemy, SQL connectors, requests o adaptadores de infraestructura.
  - El modelo canónico representa datos transformados de negocio, no payloads crudos de fuentes.
- **Capa Aplicación (`src/**/application/**/*.py`):**
  - Orquestación de casos de uso y definición de puertos de origen (`sources`), transformación y destino (`destinations`).
  - PROHIBIDO acoplarse a librerías concretas de bases de datos o transporte HTTP.
- **Capa Adaptadores / Plataforma (`src/**/adapters/**/*.py` o `sources/`):**
  - Implementación de conectores de ingesta (Polars, SQLAlchemy, DuckDB, APIs externas) y publicadores.
  - Mapeo bidireccional estricto entre esquemas de origen y entidades de dominio.
- **Composition Root (`src/**/main.py` o `app.py`):**
  - Arranque de FastAPI, configuración de rutas, middlewares y cableado de dependencias.
