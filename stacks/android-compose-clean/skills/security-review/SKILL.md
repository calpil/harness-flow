---
name: security-review
description: Guía de auditoría y revisión de seguridad estricta para aplicaciones móviles Android, almacenamiento cifrado, ATS y protección de datos
---

# Auditoría de Seguridad en Aplicaciones Android

## Objetivo y activación
Esta skill se activa para auditar la seguridad de la aplicación móvil Android, asegurando el almacenamiento seguro de credenciales, comunicaciones seguras mediante HTTPS, trazabilidad y protección de backups.

## Inspección obligatoria
Antes de emitir el reporte de seguridad:
- Revisar `AndroidManifest.xml` y la configuración de `data_extraction_rules.xml`.
- Revisar que no se almacenen secretos en `SharedPreferences` sin cifrar.
- Verificar el uso de HTTPS y la propagación de la cabecera `x-correlation-id`.
- Verificar que `allowBackup="false"` esté configurado en el manifiesto.
- Consultar las directrices en `.claude/rules/security.md`.

## Procedimiento ejecutable
1. **Auditar almacenamiento local:** Comprobar que ningún secreto, token de autenticación o información personal identificable (PII) se guarde en `SharedPreferences` sin cifrar.
2. **Validar uso de EncryptedSharedPreferences:** Verificar que las credenciales de sesión se almacenen usando Jetpack Security con claves administradas en el Android Keystore.
3. **Auditar comunicaciones de red:** Confirmar que todos los endpoints utilicen HTTPS estricto y que no se permita tráfico en texto plano (`usesCleartextTraffic="false"`).
4. **Verificar trazabilidad de Correlation ID:** Confirmar que las peticiones HTTP al backend propaguen la cabecera `x-correlation-id`.
5. **Escanear secretos en el repositorio:** Escanear archivos Kotlin, recursos XML y scripts de Gradle para certificar la ausencia de claves privadas, tokens o contraseñas.
6. **Auditar políticas de backup:** Verificar que `allowBackup="false"` y `data_extraction_rules.xml` eviten la extracción no autorizada de datos mediante ADB o servicios de copia en la nube.

## Patrón de implementación
```xml
<!-- En AndroidManifest.xml -->
<application
    android:allowBackup="false"
    android:dataExtractionRules="@xml/data_extraction_rules"
    android:fullBackupContent="false"
    android:usesCleartextTraffic="false">
```

## Decisiones y anti-patrones
- **No almacenar secretos en SharedPreferences sin cifrar:** `SharedPreferences` guarda datos en archivos XML en texto plano accesibles en dispositivos con root.
- **No habilitar cleartext traffic:** Bloquear el tráfico HTTP en texto claro en todos los entornos excepto en testing controlado de localhost.
- **No exponer trazas de error al usuario:** Ocultar stack traces y detalles de red en los mensajes de la interfaz de usuario.

## Verificación / Definition of Done
- Manifiesto verificado con `allowBackup="false"` y sin cleartext traffic.
- Almacenamiento seguro confirmado.
- Cero secretos expuestos en código fuente o historial de Git.

## Contrato de entrega del agente
El agente entregará una lista de verificación de seguridad cubriendo almacenamiento, comunicaciones de red, protección de backups y gestión de secretos.
