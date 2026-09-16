// Evidencia de Vitest REAL, no un recibo de PASS aportado por el proyecto.
import { appendFileSync } from 'node:fs';
const emit = data => appendFileSync(process.env.HARNESS_FRONTEND_EVENTS, JSON.stringify(data) + '\n');
const item = test => ({name: test.name, fullName: test.fullName, options: test.options,
  result: test.result()});
export default class {
  ready = new Set();
  onInit(ctx) {
    // Vitest reescribe .only a mode=run: impedirlo ANTES de recolectar.
    ctx.config.allowOnly = false;
    for (const project of ctx.projects) project.config.allowOnly = false;
  }
  onTestCaseReady(test) { this.ready.add(test.id); }
  onTestRunStart(specifications) {
    emit({event: 'start', files: specifications.map(s => s.moduleId)});
  }
  onTestRunEnd(modules, errors, reason) {
    emit({event: 'end', reason, errors, modules: modules.map(m => ({
      file: m.moduleId, state: m.state(), errors: m.errors(),
      suites: [...m.children.allSuites()].map(s => ({name: s.fullName,
        options: s.options, state: s.state(), errors: s.errors()})),
      tests: [...m.children.allTests()].map(t => ({...item(t), started: this.ready.has(t.id)})),
    }))});
  }
}
