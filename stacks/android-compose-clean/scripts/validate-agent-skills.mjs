#!/usr/bin/env node
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';

const ROOT = resolve(process.argv[2] ?? '.claude/skills');
const errors = [];
const names = new Set();
const requiredSections = [
  '## Objetivo y activación',
  '## Inspección obligatoria',
  '## Procedimiento ejecutable',
  '## Patrón de implementación',
  '## Decisiones y anti-patrones',
  '## Verificación / Definition of Done',
  '## Contrato de entrega del agente',
];

if (!existsSync(ROOT)) {
  console.error('[SKILLS] ERROR: Directorio .claude/skills ausente');
  process.exit(1);
}

for (const folder of readdirSync(ROOT).filter((f) => statSync(join(ROOT, f)).isDirectory())) {
  const file = join(ROOT, folder, 'SKILL.md');
  if (!existsSync(file)) {
    errors.push(`${folder}: SKILL.md ausente`);
    continue;
  }

  const content = readFileSync(file, 'utf8');
  const front = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!front) {
    errors.push(`${folder}: YAML frontmatter ausente`);
    continue;
  }

  const name = front[1].match(/^name:\s*(.+)$/m)?.[1]?.trim();
  const description = front[1].match(/^description:\s*(.+)$/m)?.[1]?.trim();

  if (!name || name !== folder || !/^[a-z0-9-]{1,64}$/.test(name)) {
    errors.push(`${folder}: 'name' inválido o no coincide con el directorio (${name})`);
  }

  if (!description || description.length < 35 || description.length > 1024) {
    errors.push(`${folder}: 'description' inválida (longitud ${description?.length || 0})`);
  }

  if (names.has(name)) {
    errors.push(`${folder}: nombre duplicado '${name}'`);
  }
  names.add(name);

  const lines = content.split(/\r?\n/).length;
  if (lines < 45) {
    errors.push(`${folder}: skill demasiado superficial (<45 líneas, tiene ${lines})`);
  }

  for (const section of requiredSections) {
    if (!content.includes(section)) {
      errors.push(`${folder}: falta sección obligatoria '${section}'`);
    }
  }

  if (content.includes('.' + 'tools')) {
    errors.push(`${folder}: contiene referencia prohibida a ruta portable eliminada`);
  }

  const stepsMatch = content.match(/## Procedimiento ejecutable\r?\n+([\s\S]*?)\r?\n+## Patrón de implementación/);
  const steps = stepsMatch ? stepsMatch[1] : '';
  const stepCount = (steps.match(/^\d+\.\s+/gm) || []).length;
  if (stepCount < 5) {
    errors.push(`${folder}: procedimiento ejecutable insuficiente (<5 pasos, encontrados ${stepCount})`);
  }

  for (const match of content.matchAll(/\]\((\.{1,2}\/[^\s)#]+)(?:#[^\s)]*)?\)/g)) {
    const target = resolve(dirname(file), match[1]);
    if (!existsSync(target)) {
      errors.push(`${folder}: enlace markdown roto '${match[1]}'`);
    }
  }
}

if (errors.length > 0) {
  console.error('[SKILLS] ERROR: Se encontraron infracciones en los contratos de skills:\n' + errors.join('\n'));
  process.exit(1);
}

console.log(`[SKILLS] OK: ${names.size} skills validadas correctamente con frontmatter YAML, 7 secciones obligatorias, procedimientos verificables y sin enlaces rotos.`);
