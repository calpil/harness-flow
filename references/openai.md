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

Codex moderno instala las skills en `$CODEX_HOME/skills` (por defecto
`~/.codex/skills`) -- es donde las deja su propio tooling -- y ademas lee
`.agents/skills`. En entornos administrados tambien mira `/etc/codex/skills`.
Si usas varios CLIs, `~/.agents/skills` es el minimo comun multiplo: Codex,
Gemini CLI, Grok y Kimi Code leen esa raiz. Grok, cuando el host detectado es
`grok`, crea las lecciones en `~/.grok/skills` (ver `references/grok.md`);
seguir buscandolas aqui no cambia.

## Autodeteccion

`entorno.py` detecta `gpt` por las marcas de sesion `CODEX_THREAD_ID` o
`CODEX_SESSION_ID`, aunque el script este en el clone de Hermes. Sin esas
marcas reconoce `.agents/skills`, `.codex/skills` y `$CODEX_HOME/skills` en la
ruta del script. `HARNESS_HOST` y `--host` tienen prioridad.

## Comandos de terminal

Cada llamada independiente de Codex abre un shell nuevo: los exports de la
llamada anterior no sobreviven. Inicializa y ejecuta en la **misma llamada**,
fijando `--host codex`. Sustituye `<skill>` por la ruta instalada (tambien sirve
la ruta real del clone de Hermes) y repite el bloque para cada comando:

```bash
eval "$(python3 <skill>/scripts/entorno.py --host codex --shell)"
"$PY" "$H/estado.py"
```

En Windows con PowerShell:

```powershell
python <skill>\scripts\entorno.py --host codex --powershell | Invoke-Expression
& $PY "$H/estado.py"
```

`codex` se normaliza a `gpt` para que el resto del arnes tenga un solo nombre de
host. Ejecuta los scripts con el interprete resuelto (`"$PY"` en bash/zsh,
`& $PY` en PowerShell); `python` puede no existir en macOS/Linux y otro
interprete puede no tener las dependencias del hub.

## Raices de lecciones

Hay que separar dos cosas: donde NACE una leccion y donde se la BUSCA.

**Crear** sigue la precedencia del host detectado (`leccion.py donde` imprime
primero esa raiz). En `gpt`:

1. `.agents/skills` desde el directorio actual hasta la raiz del repo.
2. `~/.agents/skills`.
3. `$CODEX_HOME/skills` (`~/.codex/skills`), si no existe una raiz anterior.
4. `/etc/codex/skills`.

Si instalas `harness-flow` con symlink desde `~/.agents/skills` hacia el clone de
Hermes, esa precedencia no se contamina: una skill nueva no nace en Hermes.

**Buscar** mira ademas las raices de los otros agentes, porque una leccion es
memoria procedural del usuario y no del CLI donde la tipeo: `~/.hermes/skills`,
`~/.claude/skills`, `$CODEX_HOME/skills` (`~/.codex/skills`), `~/.grok/skills` y
`$KIMI_CODE_HOME/skills` (`~/.kimi-code/skills`). Sin eso, escribir la leccion
donde tu CLI la instala bloqueaba un cierre legitimo con
"la leccion no existe como skill".

`HARNESS_SKILLS_DIR` sigue siendo exclusivo: si lo defines, mandas tu y no se
consulta ninguna otra raiz.

## Invocacion automatica

`agents/openai.yaml` deja `allow_implicit_invocation: true`. La invocacion
implicita se decide principalmente por el `description` del frontmatter de
`SKILL.md`, que nombra features, gates y Obsidian al principio. El
`short_description` de `openai.yaml` describe la skill en la interfaz; no
garantiza que se invoque en todo pedido. Para asegurarla, usa `$harness-flow`.

Esto cubre Codex y los hosts que descubren skills locales. Un modelo GPT
llamado directamente por API no escanea `~/.agents/skills` por si solo: la
aplicacion debe adjuntar la skill al entorno de shell de Responses API o
registrar el directorio de capacidades en un sandbox de Agents API, y darle
acceso a los scripts y al proyecto. El symlink local no configura esa API.
