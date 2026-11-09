#!/usr/bin/env node
/** Contract test: discovers ALL features and resolves file and alias imports. No fixed feature list. */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, normalize, resolve, sep } from 'node:path';
const ROOT = resolve('src/app/features');
const errors = [];
const TS = /\.(ts|tsx)$/;
function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const file = join(dir, name);
    return statSync(file).isDirectory()
      ? walk(file)
      : TS.test(name) && !name.endsWith('.spec.ts')
        ? [file]
        : [];
  });
}
function resolveImport(file, spec) {
  if (spec.startsWith('.')) return normalize(resolve(dirname(file), spec));
  if (spec.startsWith('@work-items/'))
    return normalize(resolve(ROOT, 'work-items', spec.slice('@work-items/'.length)));
  if (spec.startsWith('@core/')) return normalize(resolve('src/app/core', spec.slice(6)));
  if (spec.startsWith('@shared/')) return normalize(resolve('src/app/shared', spec.slice(8)));
  if (spec.startsWith('@env/')) return normalize(resolve('src/environments', spec.slice(5)));
  if (spec.startsWith('src/app/')) return normalize(resolve(spec));
  return null;
}
function featureArea(path) {
  const rel = path.slice(ROOT.length + 1).split(sep);
  return { feature: rel[0], layer: rel[1] ?? '', relative: rel };
}
const files = walk(ROOT);
for (const file of files) {
  const { feature, layer } = featureArea(file);
  if (
    !['domain', 'application', 'data-access', 'ui'].includes(layer) &&
    !['index.ts', 'work-items.routes.ts'].includes(file.split(sep).at(-1))
  ) {
    // Extension points, route files and feature-owned composition roots are acceptable.
    continue;
  }
  const source = readFileSync(file, 'utf8');
  const imports = [
    ...source.matchAll(/(?:from\s*|import\s*|export\s*\*\s*from\s*)['"]([^'"]+)['"]/g),
  ].map((m) => m[1]);
  for (const spec of imports) {
    const target = resolveImport(file, spec);
    if (
      layer === 'domain' &&
      (spec.startsWith('@angular/') ||
        spec.startsWith('rxjs') ||
        spec.startsWith('@core/') ||
        spec.startsWith('@shared/') ||
        spec.startsWith('@env/') ||
        spec.startsWith('@calpil-ds/'))
    ) {
      errors.push(`${file}: domain no permite dependencia ${spec}`);
    }
    if (!target || !(target === ROOT || target.startsWith(`${ROOT}${sep}`))) continue;
    const dest = featureArea(target);
    if (dest.feature !== feature) {
      errors.push(`${file}: acceso directo a otra feature ${dest.feature} (${spec})`);
      continue;
    }
    if (layer === 'domain' && dest.layer !== 'domain')
      errors.push(`${file}: domain -> ${dest.layer}`);
    if (layer === 'application' && ['ui', 'data-access'].includes(dest.layer))
      errors.push(`${file}: application -> ${dest.layer}`);
    if (layer === 'ui' && dest.layer === 'data-access') errors.push(`${file}: ui -> data-access`);
    if (layer === 'data-access' && dest.layer === 'ui') errors.push(`${file}: data-access -> ui`);
  }
}
if (!existsSync(resolve('src/app/app.routes.ts'))) errors.push('No existe composition root routes');
if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log(
  `[ARCH] OK: ${files.length} archivos de ${readdirSync(ROOT).length} features; límites verificados.`,
);
