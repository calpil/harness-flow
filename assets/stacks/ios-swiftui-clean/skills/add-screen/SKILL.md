---
name: add-screen
description: Procedimiento para crear una nueva pantalla o vista en SwiftUI con ViewModel, estados de carga y navegación reactiva
---

# Creación de Pantallas en SwiftUI

## Objetivo y activación
Esta skill se activa cuando se solicita una nueva pantalla, flujo o vista principal en la aplicación iOS (`Sources/CalpilUI`), integrándola con el ViewModel y el sistema de navegación de SwiftUI.

## Inspección obligatoria
Antes de codificar la vista:
- Revisar componentes compartidos en `Sources/CalpilUI/Core/Components/`.
- Revisar el sistema de colores y estilos en `Sources/CalpilUI/Core/Theme/CalpilTheme.swift`.
- Revisar los casos de uso necesarios en `Sources/CalpilDomain/UseCases/`.
- Inspeccionar pantallas similares en `Sources/CalpilUI/Features/WorkItems/Views/`.

## Procedimiento ejecutable
1. **Definir el ViewModel:** Crear `Sources/CalpilUI/Features/{Feature}/ViewModels/{Screen}ViewModel.swift` anotado con `@MainActor`, exponiendo propiedades `@Published` para datos, `isLoading` y `errorMessage`.
2. **Crear la vista SwiftUI principal:** Crear `Sources/CalpilUI/Features/{Feature}/Views/{Screen}View.swift` recibiendo el ViewModel mediante `@ObservedObject` o `@StateObject`.
3. **Manejar los cuatro estados canónicos de UI:**
   - Estado de carga: Mostrar `ProgressView` o componente `LoadingView`.
   - Estado vacío: Mostrar ilustración o texto instructivo cuando la lista o entidad no contenga datos.
   - Estado de error: Mostrar mensaje comprensible con botón de reintento.
   - Estado de contenido: Renderizar los datos organizados en listas, formularios o scrolls.
4. **Integrar navegación y toolbar:** Configurar `NavigationStack`, `navigationTitle` y botones de acción en `toolbar`.
5. **Añadir soporte multiplataforma:** Asegurar compatibilidad en modificadores condicionales entre iOS y macOS (`#if os(iOS)`).
6. **Escribir pruebas de ViewModel:** Crear tests unitarios en `Tests/CalpilPresentationTests/` verificando las transiciones de estado al invocar las acciones del ViewModel.

## Patrón de implementación
```swift
public struct ProfileView: View {
    @ObservedObject public var viewModel: ProfileViewModel

    public var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading {
                    LoadingView(message: "Cargando perfil...")
                } else if let error = viewModel.errorMessage {
                    Text(error).foregroundColor(.red)
                } else {
                    Text("Bienvenido")
                }
            }
            .navigationTitle("Mi Perfil")
        }
    }
}
```

## Decisiones y anti-patrones
- **No colocar llamadas de red dentro de la vista:** Toda lógica asíncrona debe residir en el ViewModel o en los Casos de Uso.
- **Evitar vistas monolíticas:** Dividir pantallas complejas en sub-vistas modulares y reutilizables.
- **Acciones desacopladas:** Usar closures o inyección de dependencias para delegar acciones hacia vistas padre o navegadores.

## Verificación / Definition of Done
- La pantalla compila limpiamente sin advertencias de concurrencia en Swift 6.
- Manejo explícito de carga, error y reintento.
- Pruebas del ViewModel pasando en `Tests/CalpilPresentationTests/`.

## Contrato de entrega del agente
El agente reportará el ViewModel y la vista creados, el resultado de las pruebas asociadas y la confirmación de compilación.
