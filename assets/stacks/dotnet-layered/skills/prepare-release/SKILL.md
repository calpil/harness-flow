---
name: prepare-release
description: Verificación final de un release de la API .NET layered: validación completa, migraciones, imagen Docker, versión SemVer, changelog y notas de despliegue.
---

# Prepare Release — CALPIL .NET Layered

## Objetivo y activación
Activar cuando se pide preparar una versión. Confirma que el repositorio está en condiciones de publicarse y deja versión, changelog y notas de despliegue listas. No crea tags, no hace push ni despliega salvo pedido explícito.

## Inspección obligatoria
Antes de escribir código, lee:
1. `CHANGELOG.md` y `TEMPLATE_VERSION`: última versión publicada.
2. `git log` desde el último release: qué cambió.
3. `db/migrations/`: migraciones nuevas desde el último release.
4. `Dockerfile`, `Directory.Packages.props` y `.env.example`: cambios de entrega y configuración.

## Procedimiento ejecutable
1. **Confirmar el árbol limpio** (`git status`) y la rama correcta.
2. **Ejecutar `make validate`:** build sin warnings, formato, pruebas sin Docker, pruebas con SQL Server, skills y auditoría de paquetes.
3. **Revisar las migraciones nuevas:** numeración correlativa, un lote por archivo, compatibles con la versión anterior de la aplicación durante el despliegue (expandir antes de contraer).
4. **Construir y probar la imagen:** `make docker-build` y `make up`; comprobar `/health/readiness` y un request real; luego `make down`.
5. **Decidir la versión SemVer:** mayor si cambia el contrato HTTP de forma incompatible, menor si agrega capacidad, parche si corrige.
6. **Actualizar `CHANGELOG.md` y `TEMPLATE_VERSION`** con cambios agregados, modificados, corregidos y de seguridad.
7. **Escribir las notas de despliegue:** variables nuevas, migraciones a aplicar, permisos SQL nuevos y plan de vuelta atrás.

## Patrón de implementación
```bash
make validate
make docker-build && make up
curl -fsS http://localhost:8080/health/readiness   # {"status":"UP"}
make down
git status --short                                  # solo CHANGELOG.md y TEMPLATE_VERSION
```

## Decisiones y anti-patrones
- **NO** publicar con pruebas fallando, saltadas o con warnings.
- **NO** crear tags, hacer `git push` ni desplegar sin pedido explícito.
- **NO** incluir en un release una migración destructiva junto con el código que aún usa lo que elimina.
- **NO** declarar el release listo si `make test-integration` no se ejecutó; decirlo como pendiente.
- **NO** reescribir entradas anteriores del changelog.

## Verificación / Definition of Done
- `make validate` completo en verde, con su salida.
- Imagen construida y verificada con readiness y un request real.
- `CHANGELOG.md` y `TEMPLATE_VERSION` actualizados y coherentes.
- Notas de despliegue con variables, migraciones, permisos y vuelta atrás.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Versión propuesta y por qué.
2. Resultado de cada paso de verificación; lo que no se ejecutó, dicho explícitamente.
3. Resumen del changelog.
4. Notas de despliegue y riesgos conocidos.
