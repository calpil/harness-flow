---
name: security-review
description: Guía de auditoría y revisión de seguridad estricta para aplicaciones móviles iOS, Keychain, ATS y protección de datos
---

# Auditoría de Seguridad en Aplicaciones iOS

## Objetivo y activación
Esta skill se activa para auditar la seguridad de la aplicación móvil iOS, asegurando el almacenamiento seguro de credenciales, la protección en tránsito con HTTPS y la ausencia de secretos o datos sensibles expuestos en el código o logs.

## Inspección obligatoria
Antes de emitir el informe de seguridad:
- Revisar el cliente de red en `Sources/CalpilData/Network/APIClient.swift`.
- Revisar que no se almacenen tokens o contraseñas en `UserDefaults`.
- Comprobar la inyección de la cabecera `x-correlation-id`.
- Verificar la configuración de App Transport Security (ATS).
- Consultar las reglas en `.agents/rules/security.md` (o `.agents/rules/security.md (o .claude/rules/security.md)`).

## Procedimiento ejecutable
1. **Auditar almacenamiento local:** Comprobar que ningún secreto, token de autenticación o información personal identificable (PII) se persista en `UserDefaults`, archivos de texto plano o caché no cifrada.
2. **Validar uso de Keychain Services:** Verificar que toda credencial sensible se almacene mediante Keychain Services con atributos de protección adecuados (`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`).
3. **Auditar comunicaciones y ATS:** Confirmar que todos los endpoints utilicen HTTPS estricto y que no existan excepciones globales de App Transport Security.
4. **Verificar trazabilidad de Correlation ID:** Confirmar que el cliente HTTP inyecte o propague la cabecera `x-correlation-id` en todas las peticiones salientes.
5. **Escanear secretos en el repositorio:** Escanear el código fuente y archivos de configuración para certificar que no existan API keys, contraseñas o certificados embebidos.
6. **Auditar sanitización de logs:** Verificar que los mensajes de log no impriman tokens, datos personales ni información financiera.

## Patrón de implementación
```swift
// Verificación de cabeceras seguras en peticiones de red
var request = URLRequest(url: secureURL)
request.setValue(correlationId, forHTTPHeaderField: "x-correlation-id")
request.setValue("application/json", forHTTPHeaderField: "Accept")
```

## Decisiones y anti-patrones
- **No almacenar secretos en `UserDefaults`:** `UserDefaults` almacena datos en listas de propiedades (.plist) sin cifrar fácilmente accesibles en dispositivos con jailbreak o copias de seguridad.
- **No deshabilitar ATS:** Mantener activas las restricciones de App Transport Security exigiendo TLS moderno.
- **No filtrar excepciones internas:** Ocultar detalles técnicos de infraestructura en las alertas y mensajes mostrados al usuario.

## Verificación / Definition of Done
- Revisión de almacenamiento local completada.
- Verificación de cabeceras HTTP y ATS aprobada.
- Cero secretos expuestos en código fuente o historial de commits.

## Contrato de entrega del agente
El agente entregará una lista de verificación de seguridad cubriendo almacenamiento, comunicaciones HTTPS, gestión de secretos y trazabilidad.
