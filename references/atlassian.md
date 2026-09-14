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

**Con token** → push directo por REST:

```bash
python "$H/atlassian.py" status              # verifica que Jira responde
python "$H/atlassian.py" push --feature 3    # Jira + Confluence
```

`push` crea o actualiza automaticamente:

- la historia Jira (Story/Bug/Task segun el binding) y sus subtasks por AC;
- una pagina Confluence `Feature #<id> - <nombre>` en el space configurado, con
  PRD/SDD si existen, spec, evidencia, review y AC embebidos.

Para que el cierre publique al terminar:

```bash
python "$H/gate.py" close --feature 3 --status done --to main \
  --leccion <clase> --publicar-atlassian
```

Sin `--publicar-atlassian`, `close` solo avisa. Asi no hay escrituras remotas
accidentales.

**Sin token** → el push deja intents JSON en `harness/outbox/`, para drenarlos con
tu MCP de Atlassian. Luego liga la clave Jira:

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

| Harness | Confluence |
| --- | --- |
| feature | Pagina `Feature #<id> - <nombre>` |
| spec/evidencia/review | Secciones dentro de la pagina |
| `docs/prd/PRD-master.md` / `docs/sdd.md` | Secciones embebidas si existen |
| AC-n | Lista de criterios de aceptacion |
| `confluence_page_id` | id de la pagina remota |

Las claves creadas quedan en `feature_list.json` (`jira_key`, `jira_ac_keys`,
`confluence_page_id`), asi que un segundo `push` actualiza en vez de duplicar.

## Regla

El push remoto es explicito: `atlassian.py push --feature <id>` o
`gate.py close ... --publicar-atlassian`. `close` sin esa bandera no publica por
su cuenta.
