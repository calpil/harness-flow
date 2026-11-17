---
name: prepare-release
description: Verificación final de un release del portal .NET MVC: validación completa, imagen Docker, compatibilidad con la versión de la API, versión SemVer, changelog y notas de despliegue.
---

# Prepare Release — CALPIL .NET MVC

## Objetivo y activación
Activar cuando se pide preparar una versión del portal. Confirma que está en condiciones de publicarse y deja versión, changelog y notas de despliegue listas. No crea tags, no hace push ni despliega salvo pedido explícito.

## Inspección obligatoria
Antes de escribir código, lee:
1. `CHANGELOG.md` y `TEMPLATE_VERSION`: última versión publicada.
2. `git log` desde el último release.
3. `src/Calpil.Template.Web/Services/`: operaciones de la API que el portal consume.
4. `Dockerfile`, `Directory.Packages.props` y `.env.example`.

## Procedimiento ejecutable
1. **Confirmar el árbol limpio** (`git status`) y la rama correcta.
2. **Ejecutar `make validate`:** build sin warnings, formato, pruebas, skills y auditoría de paquetes.
3. **Verificar compatibilidad con la API:** cada operación que el portal consume existe en la versión de la API que estará desplegada; si el portal necesita una API más nueva, la API se despliega primero.
4. **Construir y probar la imagen:** `make docker-build`, levantar la API local y `make up`; recorrer listado, alta y cambio de estado; `make down`.
5. **Decidir la versión SemVer:** mayor si cambian rutas públicas o variables obligatorias, menor si agrega pantallas, parche si corrige.
6. **Actualizar `CHANGELOG.md` y `TEMPLATE_VERSION`.**
7. **Escribir las notas de despliegue:** variables nuevas, URLs de retorno a registrar en el proveedor de identidad, versión mínima de la API, claves de Data Protection y vuelta atrás.

## Patrón de implementación
```bash
make validate
make docker-build && make up
curl -fsS http://localhost:8090/health/readiness
make down
git status --short            # solo CHANGELOG.md y TEMPLATE_VERSION
```

## Decisiones y anti-patrones
- **NO** publicar con pruebas fallando, saltadas o con warnings.
- **NO** crear tags, hacer `git push` ni desplegar sin pedido explícito.
- **NO** publicar el portal antes que la versión de la API de la que depende.
- **NO** declarar verificado el inicio de sesión OIDC si solo se probó `AUTH_MODE=dev`; decirlo como pendiente.
- **NO** reescribir entradas anteriores del changelog.

## Verificación / Definition of Done
- `make validate` completo en verde, con su salida.
- Imagen construida y flujo principal recorrido contra la API.
- `CHANGELOG.md` y `TEMPLATE_VERSION` actualizados y coherentes.
- Notas de despliegue con variables, versión mínima de la API y vuelta atrás.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Versión propuesta y por qué.
2. Resultado de cada paso de verificación; lo que no se ejecutó, dicho explícitamente.
3. Resumen del changelog.
4. Notas de despliegue y riesgos conocidos.
