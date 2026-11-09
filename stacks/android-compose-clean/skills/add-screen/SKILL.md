---
name: add-screen
description: Procedimiento para crear una nueva pantalla en Jetpack Compose con ViewModel, StateFlow y componentes Material 3
---

# Creación de Pantallas en Jetpack Compose

## Objetivo y activación
Esta skill se activa cuando se solicita una nueva pantalla, flujo o vista principal en la aplicación Android (`presentation/`), integrándola con su ViewModel, el sistema de diseño Material 3 y Jetpack Navigation.

## Inspección obligatoria
Antes de codificar la pantalla:
- Revisar componentes compartidos en `core/ui/components/`.
- Revisar colores y tipografías en `core/ui/theme/`.
- Revisar los casos de uso disponibles en `features/*/domain/usecases/`.
- Inspeccionar pantallas existentes como `WorkItemListScreen.kt`.

## Procedimiento ejecutable
1. **Definir la data class UiState:** Declarar en `presentation/` una data class inmutable con los estados requeridos (`isLoading`, `errorMessage`, `data`).
2. **Crear el ViewModel:** Heredar de `androidx.lifecycle.ViewModel`, inicializar `MutableStateFlow(UiState())` y exponerlo como `StateFlow`.
3. **Crear la función Composable principal:** Diseñar la pantalla con `Scaffold`, `TopAppBar` y navegación por callbacks (`onNavigateBack`, etc.).
4. **Manejar los cuatro estados canónicos de UI:**
   - Estado de carga: Mostrar `CircularProgressIndicator` o `LoadingIndicator`.
   - Estado vacío: Mostrar mensaje instructivo cuando la lista esté vacía.
   - Estado de error: Mostrar mensaje de error con botón de reintento.
   - Estado de contenido: Renderizar los elementos usando `LazyColumn`, `Card` y componentes M3.
5. **Configurar la ruta de navegación:** Añadir el destino correspondiente en `MainActivity.kt` dentro de `NavHost`.
6. **Escribir pruebas de ViewModel:** Crear tests con `StandardTestDispatcher` y `runTest` verificando las emisiones de `UiState`.

## Patrón de implementación
```kotlin
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    onNavigateBack: () -> Unit
) {
    val state by viewModel.uiState.collectAsState()
    Scaffold(
        topBar = { TopAppBar(title = { Text("Configuración") }) }
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            if (state.isLoading) LoadingIndicator()
            else Text("Opciones")
        }
    }
}
```

## Decisiones y anti-patrones
- **No instanciar ViewModels dentro de sub-composables:** Pasar estados y lambdas de eventos (`onAction`) para favorecer recomposiciones y previews.
- **Evitar llamadas suspend directas en Composables:** Lanzar coroutines en el ViewModel o con `LaunchedEffect` controlado por claves.
- **Componentes desacoplados:** Utilizar modifiers externos para controlar tamaño y espaciado de componentes reutilizables.

## Verificación / Definition of Done
- Pantalla compilando sin errores en Compose.
- Manejo explícito de carga, error y reintento.
- Pruebas del ViewModel pasando en `app/src/test/`.

## Contrato de entrega del agente
El agente reportará el ViewModel y Composable creados, la ruta registrada en `MainActivity` y el resultado de las pruebas unitarias.
