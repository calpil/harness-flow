# Jira / Confluence

## Apagado por defecto

Sin `harness/atlassian.json` el flujo corre igual y no toca nada. Si el usuario
quiere integrar, PREGÚNTALE el sitio, el proyecto Jira y el space: no lo adivines.

```bash
python "$H/atlassian.py" bind --site tuempresa.atlassian.net \
    --jira-project ADR --confluence-space ARQ
```

Ese archivo es **versionable**: contiene sitio/proyecto/space, nunca credenciales.

## Credenciales

Fuera del repo, en `~/.harness-hub/.env` o el entorno:

```
ATLASSIAN_EMAIL=tu@correo.com
ATLASSIAN_API_TOKEN=...
```

Token en https://id.atlassian.com/manage-profile/security/api-tokens

## Modos

**Con token** → push directo por REST v3:

```bash
python "$H/atlassian.py" status              # verifica que Jira responde
python "$H/atlassian.py" push --feature 3    # crea/actualiza la historia + subtasks por AC
```

**Sin token** → el push deja un intent JSON en `harness/outbox/`, para drenarlo con
tu MCP de Atlassian. Luego liga la clave:

```bash
python "$H/atlassian.py" outbox
python "$H/atlassian.py" ack --feature 3 --key ADR-142
```

## Mapeo

| Harness | Jira |
| --- | --- |
| feature | Story (o `issue_type` del binding) |
| bug | Bug |
| task | Task |
| AC-n | Subtask de la historia |
| `jira_key` en el backlog | clave de la issue |

Las claves creadas quedan en `feature_list.json` (`jira_key`, `jira_ac_keys`), así
que un segundo `push` actualiza en vez de duplicar.

## Regla

El push es una decisión del usuario, no un efecto secundario del cierre. `close`
no publica nada por su cuenta.
