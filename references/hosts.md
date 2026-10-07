# Raices de skills por host

`leccion.py donde` indica la primera raíz disponible para crear una lección;
`leccion.py list` y el gate de cierre también buscan en raíces compartidas de
otros agentes. Si defines `HARNESS_SKILLS_DIR`, esa raíz es exclusiva.

| Host | Raíces para crear lecciones, en orden |
| --- | --- |
| Hermes | La raíz de la instalación activa (incluye perfiles), luego las rutas de Hermes del sistema |
| Claude Code | `~/.claude/skills`, luego `.claude/skills` del proyecto |
| GPT/Codex | `.agents/skills` y `.codex/skills` del proyecto, `~/.agents/skills`, `$CODEX_HOME/skills` (`~/.codex/skills`) y `/etc/codex/skills` |
| Gemini / AGY | `.gemini/skills` y `.agents/skills` del proyecto, luego `~/.gemini/config/skills` y `~/.agents/skills` |
| Grok | `~/.grok/skills` |
| Kimi Code | `$KIMI_CODE_HOME/skills` (`~/.kimi-code/skills`), luego `~/.agents/skills` |

Para crear o editar una lección, usa la primera ruta que indica el comando
`leccion.py donde`. En Hermes usa `skill_manage`; los demás hosts escriben el archivo
`<raiz>/<clase>/SKILL.md` con frontmatter `name` y `description`. Corrige la
lección aplicable antes de crear otra.

Guarda reglas reutilizables por clase de trabajo, nunca por id de feature.
No captures fallas transitorias de entorno, narraciones de una tarea unica o
negativas sobre herramientas como lecciones.

La skill `harness-flow` puede estar enlazada desde el clone de Hermes. La
detección debe seguir al host que la carga, no al destino del symlink. En Codex
se puede instalar en `.agents/skills` para compartirla con otros agentes o en
`.codex/skills` para usar la raíz nativa del proyecto. En ambos casos
`leccion.py` ofrece las dos raíces locales antes de las personales.

Detalles específicos de cada host:

- [OpenAI GPT / Codex](openai.md)
- [Claude Code](claude.md)
- [Grok](grok.md)
- [Kimi Code](kimi.md)
