# PostgreSQL / Liquibase Expand-Contract — Playbook técnico de ejecución


## Diagnóstico del repositorio

La autoridad es `src/main/resources/db/changelog/db.changelog-master.yaml`, que referencia scripts bajo `db/changelog/sql`. También existen rutas bajo `db/changelog/changes`: **no asumir** que todos son aplicados. Leer referencias recursivamente desde master; no editar archivos históricos ejecutados.

## Plan expand-contract concreto

**R1 (expand)**: agregar columna nullable + índice concurrente cuando sea compatible con Liquibase/PG y con la política de transacciones del changeset; desplegar app capaz de leer antigua y nueva representación. Evitar índice concurrente dentro de transacción (`runInTransaction: false` si aplica y se probó).

**Backfill**: en batches acotados con keyset pagination, checkpoint y logs mínimos; confirmar recuentos, nulos, locks y performance. Ejecutar fuera del boot normal si implica minutos/horas.

**R2 (switch)**: habilitar nuevo write/read path (posible feature flag), monitorear y permitir coexistencia con versión antigua de app.

**R3 (contract)**: eliminar columna previa solo después de comprobar 100% adopción, backup y ventana de cambio; registrar irreversibilidad de datos cuando corresponda.

## Convención de columnas y esquema

- IDs: `_id`, códigos `_code`, nombre `_name`, estado `_status`, contador `_count`.
- Marca temporal `*_at` (instante con zona consistente) vs `*_date` (fecha lógica), JSON `_json`, URL `_url`, versión `_version` cuando corresponda.
- Declarar `NOT NULL`, FK, UK, CHECK, defaults e índices basados en consultas reales, no por estética.
- Usar `timestamptz` para instantes de negocio/auditoría cuando corresponda; documentar UTC en contratos.
- Campos `is_active` si delete lógico es una regla de negocio; índices parciales de activos si respaldados por queries.

## Ejemplo orientativo de registro de cambios

```yaml
databaseChangeLog:
  - changeSet:
      id: 003-add-asset-code
      author: equipo
      changes:
        - sqlFile:
            path: sql/003-add-asset-code.sql
            relativeToChangelogFile: true
            splitStatements: true
            stripComments: true
```

**Atención:** es ejemplo, añadir al master real con ID global único y path que realmente exista; no editar 001/002 ya aplicados. Si implementación requiere rollback explícito Liquibase, definir SQL inverso comprobado sobre una DB de prueba; no borrar datos arbitrariamente.

## Test de migración

1. DB vacía: changelog master completo pasa y Hibernate valida modelo JPA.
2. DB desde release anterior: migra con filas antiguas, conserva integridad y acceso.
3. Reaplicación: no vuelve a crear estructuras ni explota por duplicados.
4. Falla en mitad de backfill: puede reanudar desde checkpoint sin corromper filas.
5. Plan rollback/forward-fix documentado con tiempos estimados basados en ambiente, no inventados.
6. Vistas/reportes consumers y permisos DB no quedan obsoletos.

## Peligros PostgreSQL

- `ALTER TABLE .. SET NOT NULL` y FK validación pueden escanear tabla y bloquear; usar validación por etapas cuando volumen lo exige.
- `CREATE INDEX CONCURRENTLY` necesita manejo especial por transacciones.
- Rollback de `DROP COLUMN` no recupera valores perdidos: restauración desde backup, dual-write o forward fix.
- Cambios de JSON y numeric coercions requieren `USING`/comprobación antes de aplicar.

## Gate final

- [ ] master includes exactly intended SQL once
- [ ] fresh DB and prior release both migrate
- [ ] reapply idempotent via changeSet tracking
- [ ] null/data backfill and constraints tested
- [ ] locking/backfill plan documented for target volume
- [ ] rollback or forward fix with data loss warning
