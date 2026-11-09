---
description: Reglas de seguridad móvil en Android, almacenamiento seguro, HTTPS, data extraction y secrets
globs: ["app/src/**", ".env*"]
---

# Reglas de Seguridad en Aplicaciones Móviles Android

- **Almacenamiento Local Seguro:**
  - Prohibido guardar tokens JWT, contraseñas, secretos o información personal identificable (PII) en `SharedPreferences` sin cifrar.
  - Usar `EncryptedSharedPreferences` (Jetpack Security) o Android Keystore para almacenamiento de credenciales y claves criptográficas.
- **Seguridad en Red y Transporte:**
  - Todas las comunicaciones con servidores backend deben forzar HTTPS con TLS 1.3 / 1.2.
  - Prohibido habilitar `android:usesCleartextTraffic="true"` en `AndroidManifest.xml` salvo para pruebas en localhost debidamente aisladas.
  - Inyección y retorno mandatorio de la cabecera `x-correlation-id` en todas las peticiones salientes.
- **Protección contra Extracción de Datos:**
  - `AndroidManifest.xml` debe configurar `android:allowBackup="false"` y definir reglas en `res/xml/data_extraction_rules.xml` para evitar copias de datos sensibles mediante ADB o backups en la nube.
- **Cero Secretos en Código:**
  - Prohibido dejar API keys, tokens o contraseñas en archivos Kotlin, recursos XML o archivos de propiedades de Gradle.
  - Utilizar variables de entorno o `BuildConfig` inyectado en tiempo de compilación para la configuración.
