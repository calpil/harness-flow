# Sincronizacion remota de features en desarrollo (multi-dev)

Cuando varias personas trabajan en paralelo sobre el mismo proyecto, `harness-flow` coordina que features se estan desarrollando en local para que nadie pise el trabajo de otro.

## Como funciona

1. **Activacion automatica (`rules.require_sync_remoto`):**
   - `"auto"` (por defecto): se activa automaticamente en cuanto el repo donde vive `harness/feature_list.json` tiene un remoto Git `origin` (configurable con `rules.remoto_sync`). En repos puramente locales sin remoto no realiza llamadas de red.
   - `true`: obligatorio siempre (falla incluso si falta el remoto, salvo `--offline`).
   - `false`: desactivado para el proyecto.
   - `HARNESS_SIN_SYNC_REMOTO=1`: variable de entorno para pruebas/CI aisladas.

2. **Estado en `harness/feature_list.json` (compatibilidad total):**
   - Mantiene `status: "in_progress"` para compatibilidad con todos los gates y herramientas existentes.
   - Agrega el bloque `desarrollo` con propietario e informacion de seguimiento:
     ```json
     "desarrollo": {
       "estado": "desarrollando",
       "por": "Alan",
       "email": "alan@empresa.com",
       "id": "alan@empresa.com",
       "host": "macbook-alan",
       "branch": "feature/5-cobro",
       "desde": "2026-11-21T18:05:00Z"
     }
     ```
   - La identidad se resuelve por `--por` / `HARNESS_DEV` > `git config user.name` + `user.email` > usuario del SO. Dos desarrolladores se distinguen por email canonico (o nombre si no hay email).

3. **Publicacion atomica en Git (`origin/<rama_base>`) + espejo en Memory Hub Postgres:**
   - Al ejecutar `worktree.py start --feature <id>`, el arnes **primero valida** contra `origin/<rama_base>` y contra el Memory Hub Postgres que nadie mas tenga tomada la feature ni este cerrada.
   - Crea el worktree desde el tip mas reciente de `origin/<rama_base>` y construye un commit limpio sobre `origin/<rama_base>` tocando **solo** `harness/feature_list.json` (sin cambiar tu rama actual ni mezclar archivos sucios locales), usando control optimista (OCC con reintento ante `non-fast-forward`).
   - Si el push falla o otro dev reclamo la misma feature en la ventana de carrera, hace rollback automatico del worktree recien creado y aborta con `exit != 0`.
   - Si tu rama local `<rama_base>` esta limpia y detras de `origin/<rama_base>`, hace `merge --ff-only` automaticamente para mantener `git status` limpio.
   - Refleja el estado en el Memory Hub Postgres (`graph_nodes` label `Feature` / `Desarrollador` y arista `DESARROLLANDO`) si `~/.harness-hub/.env` esta configurado y `HARNESS_SIN_HUB` no esta activo. Si se configura `rules.require_hub_sync: true`, un fallo del espejo Postgres tambien bloquea.

4. **Validacion previa obligatoria en los gates:**
   - **`estado.py`**: consulta `origin/<rama_base>` y el Hub al arrancar, muestra quien esta desarrollando cada feature (incluso antes de hacer `git pull`), alerta conflictos y **no sugiere** retomar ni iniciar features ajenas.
   - **`gate.py approve-spec` / `check-spec`**: bloquea si otro dev tiene la feature tomada o si falla el sync remoto.
   - **`worktree.py start` / `register`**: bloquea si otro dev la tomo o si falla el sync remoto.
   - **`gate.py check`**: valida el remoto primero, reporta conflictos o features locales `in_progress` sin publicar en remoto, y delega la validacion de worktrees/evidencia de features **ajenas** a su dueno (sin fallar por rutas locales de otra maquina).
   - **`gate.py close`**: valida propiedad y libera el reclamo en `feature_list.json` y en el Memory Hub Postgres.

5. **Modo emergencia `--offline`:**
   - Todos los comandos anteriores aceptan `--offline` para trabajar sin conexion.
   - Aun en `--offline`, nunca se permite pisar una feature cuyo dueño ajeno ya figure en el backlog local.
   - Al recuperar conexion, `gate.py check` avisa que falta publicar y puedes subir el estado con `worktree.py sync --feature <id>`.

## Comandos

```bash
$PY "$H/estado.py" [--offline]                                        # valida remoto + Hub y muestra equipo
$PY "$H/worktree.py" start --feature <id> [--por <dev>] [--offline]   # valida, crea worktree y sube estado
$PY "$H/worktree.py" sync [--feature <id>] [--offline]                # sincroniza estado o publica uno offline
$PY "$H/worktree.py" liberar --feature <id> [--forzar --yes]          # libera la feature -> todo (Git + Hub)
$PY "$H/hub.py" desarrollo [--proyecto <nombre> | --todos]            # lista desarrollos activos en Postgres
$PY "$H/sync_remoto.py" estado|publicar ...                           # CLI directo de diagnostico/publicacion
```

## Liberar una feature

- Si es **tuya**: `worktree.py liberar --feature <id>` quita el worktree local (salvo `--mantener-worktree`), vuelve la feature a `todo`, limpia `desarrollo` y lo publica en `origin/<rama_base>` y en el Memory Hub Postgres.
- Si es de **otro desarrollador**: el comando se niega salvo que pases `--forzar --yes` tras acordarlo con el equipo.
