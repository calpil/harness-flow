#!/usr/bin/env node
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';

const defaultSkillsDir = existsSync('.agents/skills') ? '.agents/skills' : '.claude/skills';
const ROOT = resolve(process.argv[2] ?? defaultSkillsDir);
const errors = [];
const names = new Set();
const required = [
  '## Objetivo y activación',
  '## Inspección obligatoria',
  '## Procedimiento ejecutable',
  '## Patrón de implementación',
  '## Decisiones y anti-patrones',
  '## Verificación / Definition of Done',
  '## Contrato de entrega del agente',
];
for (const folder of readdirSync(ROOT).filter((f) => statSync(resolve(ROOT, f)).isDirectory())) {
  const file = resolve(ROOT, folder, 'SKILL.md');
  if (!existsSync(file)) {
    errors.push(`${folder}: no SKILL.md`);
    continue;
  }
  const s = readFileSync(file, 'utf8');
  const fm = s.match(/^---\n([\s\S]+?)\n---\n/);
  if (!fm) {
    errors.push(`${folder}: falta YAML frontmatter`);
    continue;
  }
  const name = fm[1].match(/^name:\s*(.+)$/m)?.[1]?.trim();
  const description = fm[1].match(/^description:\s*(.+)$/m)?.[1]?.trim();
  if (!name || name !== folder || !/^[a-z0-9-]{1,64}$/.test(name))
    errors.push(`${folder}: name inválido`);
  if (!description || description.length < 35 || description.length > 1024)
    errors.push(`${folder}: descripción demasiado breve/larga`);
  if (names.has(name)) errors.push(`${folder}: nombre duplicado`);
  names.add(name);
  if (s.split('\n').length < 45)
    errors.push(`${folder}: skill no suficientemente operativa (<45 líneas)`);
  for (const section of required)
    if (!s.includes(section)) errors.push(`${folder}: falta sección ${section}`);
  if (/\.tools(?:\/|\b)/.test(s)) errors.push(`${folder}: referencia a carpeta portable prohibida`);
  for (const m of s.matchAll(/\]\(((?:\.\.\/|\.\/)[^\s)]+)\)/g)) {
    const target = resolve(dirname(file), m[1]);
    if (!existsSync(target)) errors.push(`${folder}: referencia relativa rota ${m[1]}`);
  }
}
if (names.size < 28) errors.push(`Se esperaban al menos 28 skills; encontradas ${names.size}`);
if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log(
  `[SKILLS] OK: ${names.size} runbooks con frontmatter, contenido, enlaces y sin .tools.`,
);
