# OpenAI GPT / Codex

## Formato

La skill usa el formato comun de Agent Skills: un directorio con `SKILL.md`, mas
`scripts/`, `references/`, `templates/` y metadata opcional. GPT/Codex puede
leerla sin fork porque el frontmatter `name` + `description` ya es compatible.

## Instalacion local

Personal, disponible para cualquier repo:

```bash
git clone https://github.com/calpil/harness-flow.git ~/.agents/skills/harness-flow
```

Por repo, versionado junto al proyecto (`<repo>/.agents/skills/harness-flow`):

```bash
git clone https://github.com/calpil/harness-flow.git .agents/skills/harness-flow
```

Codex tambien puede leer skills de `/etc/codex/skills` en entornos administrados.

## Autodeteccion

`entorno.py` detecta `gpt` cuando el script corre desde una ruta
`.agents/skills/<skill>/scripts`. Tambien puedes forzarlo:

```bash
python ~/.agents/skills/harness-flow/scripts/entorno.py --host gpt --shell
python ~/.agents/skills/harness-flow/scripts/entorno.py --host codex --shell
```

`codex` se normaliza a `gpt` para que el resto del arnes tenga un solo nombre de
host.

## Raices de lecciones

`leccion.py` busca skills en este orden:

1. `.agents/skills` desde el directorio actual hacia arriba.
2. `~/.agents/skills`.
3. `/etc/codex/skills`.

Si instalas `harness-flow` con symlink desde `~/.agents/skills` hacia el clone de
Hermes, no se agregan las raices de Hermes: GPT/Codex solo ve sus propias skills.

## Invocacion automatica

`agents/openai.yaml` deja `allow_implicit_invocation: true` y una descripcion
corta para que ChatGPT/Codex pueda activar la skill sin mencionarla explicitamente
cuando el pedido sea de flujo spec-driven, gates, PRD/SDD o Jira/Confluence.
