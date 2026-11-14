# Grok: rules y skills del stack en la sesion

Grok carga rules y skills desde el disco de la sesion. No las recibe porque el
brief las imprima. Este documento dice que copia el arnes, cuando, con que
nombre y que no toca.

## Por que

Grok descubre, en el repo de la sesion y desde la raiz hasta el directorio de
trabajo:

- `.grok/rules/*.md` (siempre)
- `.grok/skills/<nombre>/SKILL.md` (siempre)
- `.agents/skills/` (siempre)
- `.claude/rules/` y `.claude/skills/` si la compatibilidad Claude esta activa

No entra a un repo hermano. Una sesion parada en el front no ve las skills del
servicio que vive fuera. Un enlace cuyo destino queda fuera del repo no se
sigue. Por eso imprimir el indice en el brief no basta: la skill no queda
invocable.

`stack.py normalizar` sigue instalando `.claude/`, `.agents/` y `.gemini/`.
No escribe `.grok/` y no versiona esta copia. Las lecciones de Grok siguen en
`~/.grok/skills`.

## Cuando

Solo si `entorno.py` resuelve el host `grok` (`GROK_AGENT` encendido, la ruta
bajo `.grok/skills`, o `HARNESS_HOST=grok`). En otro host no se escribe nada.

| Rol | Comando | Conjunto |
| --- | --- | --- |
| Leader e implementer | `contexto.py brief --feature <id>` | Stacks de los repos de la feature (front y backend) |
| Revisor | `revision.py --feature <id> --briefing` | El mismo conjunto. El briefing llama a `lineas_reglas` |
| Producto, SDD | `producto.py borrador --doc sdd` y `contexto.py stacks` | Stacks de todos los repos del proyecto |
| Producto, PRD | `producto.py borrador --doc prd` y `contexto.py stacks --resumen` | No copia. El rol recibe el resumen |

El rol siguiente sustituye el conjunto. Lo que esa llamada no nombra se
retira. Una feature sin stack normativo no crea la sesion; si una llamada
anterior dejo copias marcadas, las retira.

## Donde

En cada uno de estos directorios, si existe:

- la raiz del arnes (`harness/feature_list.json`)
- cada repo del conjunto
- el worktree de la feature y los worktrees del mapa multi-repo

```
<destino>/.grok/rules/harness-flow-sesion.md
<destino>/.grok/rules/<stack>--<regla>.md
<destino>/.grok/skills/<stack>--<skill>/SKILL.md
```

Ejemplo con un front Angular y un servicio Go:

```
.grok/rules/angular-product--architecture.md
.grok/rules/golang-hexagonal--architecture.md
.grok/skills/angular-product--add-ui-component/SKILL.md
.grok/skills/golang-hexagonal--add-api-endpoint/SKILL.md
```

El nombre lleva el stack porque varios stacks repiten `security-review`,
`write-tests` o `add-feature`. Sin el prefijo, Grok se queda con una y calla
la otra. El `name` del frontmatter queda `<stack>--<nombre>`. La descripcion
empieza por `Stack <id>.` La skill aplica solo al repo de ese stack. Lo dice
tambien `harness-flow-sesion.md`.

La regla es el texto vigente: la copia del repo si esta al dia o el proyecto
la edito; si quedo vieja, la plantilla. El cuerpo no arrastra el frontmatter
de globs de Claude: Grok carga el archivo entero.

La skill sale de la misma fuente (`contexto._skill_md`). Se copia el
directorio y se parchea el `SKILL.md`. Una skill de
`rules.stack_skills_excluidas` no entra. Un nombre con `--` no entra: el
separador es el del prefijo.

## Que no se toca

- Una skill o regla que el usuario creo en `.grok/` y no lleva la marca.
- `.grok` si es un enlace, o si lo son `rules/` o `skills/`. No se escribe a
  traves del enlace.
- El PRD.
- Los otros hosts.
- Lo que `stack.py normalizar` instala en `.claude/`, `.agents/` y `.gemini/`.

La marca es el comentario `<!-- harness-flow-grok -->` en las reglas y en el
`SKILL.md`, y el archivo `.harness-flow-generada` dentro de la skill. Solo se
borra lo que tiene marca y ya no pertenece al conjunto.

## Git

La copia no se commitea. Cada destino git recibe en `info/exclude`, relativo a
la raiz de ese repo:

```
.grok/rules/*--*
.grok/rules/harness-flow-sesion.md
.grok/skills/*--*
```

`close` no ve el arbol sucio. Grok descubre esas rutas aunque git las ignore.
Si el destino es un subdirectorio del mismo repo (`api/` dentro del front), el
patron lleva ese prefijo. Un destino sin repo git solo recibe los archivos.

Si el contenido no cambio, no se reescribe. Grok recarga las skills cuando el
archivo cambia; una llamada que no cambia bytes no dispara otra carga.

## Limites

- La sesion los ve despues de correr el comando del rol. Abrir Grok no los
  publica.
- Un worktree que la feature ya no declara no se vuelve a visitar: ahi puede
  quedar la copia anterior.
- La ultima llamada manda. Dos features en paralelo, en la misma sesion, se
  pisan: queda el conjunto de la ultima.
- El texto completo sigue saliendo en el brief y en el briefing. La copia en
  `.grok/` es para que Grok las invoque; no reemplaza ese texto.
- `stack.py skill <nombre>` sigue imprimiendo la skill canonica, sin el
  prefijo.

## Codigo y pruebas

- `scripts/grok_sesion.py`: `publicar`.
- `scripts/contexto.py`: `_para_grok`. `lineas_reglas` publica el rol
  `feature`. `lineas_stacks_proyecto` publica el rol `sdd` cuando no es
  resumen.
- Pruebas: `tests/test_grok_sesion.py`. Un front Angular, un Go fuera y un
  worktree; la copia no ensucia git; una skill excluida no entra y una del
  usuario se queda; el rol siguiente retira el stack que ya no toca; el SDD
  publica y el PRD no; otro host no escribe `.grok/`.
