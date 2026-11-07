# Vertical Slice / Feature End-to-End — Playbook técnico de ejecución


## Contrato de una vertical slice

Antes del código completar:

| Escenario | Entrada | Invariante | Puerto externo | HTTP/evento | Prueba |
|---|---|---|---|---|---|
| crear | datos válidos | unicidad/estado inicial | save | 201/Location | domain, service, HTTP, DB |
| estado inválido | transición prohibida | nunca persiste cambio | ninguno | 409/422 según contrato | domain |
| recurso inexistente | ID válido desconocido | sin side effects | findById | 404 | service + web |
| actor no autorizado | ID de otro tenant | sin lectura/escritura | autorización previa | 403/404 por política | security E2E |
| retry idéntico | misma llave idempotente | no duplica efectos | idempotency store | misma respuesta | integración |

## Receta por capas

**Dominio**: aggregate constructor/factory recibe valores válidos y rechaza estado imposible. Representar IDs con value objects si justifican invariantes; estado solo cambia por métodos del aggregate. Eventos de dominio no referencian broker.

**Caso de uso**: interfaces por operación, tipos `record`/comandos sin anotaciones web. Orquestar validación de autorización por recurso, consistencia transaccional y excepciones; el caso de uso no genera `ResponseEntity`.

**Puerto de salida**: interfaz limitada a operaciones necesarias. Evitar `JpaRepository` heredado en application. `findById`, `save`, `count` y búsquedas orientadas al dominio solo cuando existen consumidores.

**Adaptador web**: valida `@Valid`, mapea DTO→command y domain→response explícitamente, produce status/Location. No importar JPA. El DTO nunca es fuente confiable de `tenant` sin reconciliar con identidad autenticada.

**Adaptador persistencia**: entity y repository Spring Data solo aquí; mapper verifica atributos nuevos y nulos existentes. Alinear migración Liquibase, índice y consulta.

**Configuración**: composition root cablea puertos e infraestructura con beans/transacciones, permite sustituir adapters en tests.

## Estructura sugerida (sustituir `assets` por contexto real)

```text
src/main/java/com/calpil/template/assets/
  domain/model/Asset.java
  domain/model/AssetId.java
  application/port/in/CreateAssetUseCase.java
  application/port/out/AssetRepository.java
  application/usecase/CreateAssetService.java
  adapter/in/web/{AssetController,CreateAssetRequest,AssetResponse}.java
  adapter/out/persistence/{AssetJpaEntity,AssetJpaRepository,AssetPersistenceAdapter}.java
  configuration/AssetsConfiguration.java
src/test/java/com/calpil/template/assets/{domain,application,adapter,...}/
```

Estos son *nombres sugeridos*, no clases presentes en el repo. No autogenerar archivos sin caso de uso.

## Concurrencia y eventos

- Si dos actores pueden editar el mismo aggregate, valorar `@Version` / optimistic locking y respuesta 409 con caso reproducido.
- Publicar evento antes del commit puede crear mensajes de transacción fallida; documentar política transaccional o usar outbox.
- Si el cliente reintenta create, política de deduplicación/idempotency key y período de retención si aplica.
- Estrategia de delete lógica vs física debe ser requisito explícito; jamás asumir cascada.

## Prueba de aceptación para la feature

- Regla de dominio válida e inválida probada sin contenedor Spring.
- Servicio probado con fake port saliente que registra lecturas/escrituras efectivas.
- Web probado para JSON, headers, validación y códigos de error estables.
- Integración real con Postgres; al usar Testcontainers confirmar cero skipped.
- `HexagonalArchitectureTest` limpio y sin dependencias a feature demo.

## Gate final

- [ ] domain accepts valid state and rejects invalid transition
- [ ] write path persists once and returns correct contract
- [ ] no effect on unauthorized resource or tenant
- [ ] DB migration compatible with old records
- [ ] concurrent or duplicate request behavior specified and tested
- [ ] events are atomic or have explicit reliability mitigation
