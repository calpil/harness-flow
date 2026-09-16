"""Regresiones black-box: CLI publica, repos Git efimeros y Go REAL.

Ejecutar: python3 -m unittest discover -s tests -p test_postmerge_go.py -v
No importa postmerge, no fabrica eventos ni conoce el esquema de su base.
Cada negativo parte de una base creada y comprobada por la CLI. Si falla ese
control (por ejemplo, el script antiguo no entiende JSON), NO se atribuye ese
rojo al escenario que todavia no pudo ejercerse: el mensaje dice CONTROL BASE.

Los casos default permiten observar tambien los defectos originales del script
que usaba -v. Los custom exigen Go JSON desde el control positivo. El pequeno
wrapper solo ejecuta el Go real: puede cambiar el exit DESPUES de su salida o
redirigir sus streams; nunca genera texto que suplante eventos del runner.
"""

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "postmerge_medido.py"
MODULE = "example.invalid/postmergefixture"
GO_ARGS = ["test", "-tags", "integration", "-count=1", "-json", "./integration/..."]


def shell_command(args):
    return subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)


JSON_CMD = shell_command(["go", *GO_ARGS])
CURE = re.compile(r"\b(?:se\s+cur[oó]|curad[oa]s?|cured|healed)\b", re.IGNORECASE)


class PostmergeGoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.go = shutil.which("go")
        cls.git = shutil.which("git")
        if not cls.go or not cls.git:
            raise RuntimeError("Estas regresiones requieren Go y Git reales; no se omiten.")
        if not SCRIPT.is_file():
            raise RuntimeError(f"No existe el script bajo prueba: {SCRIPT}")
        cls.cache = tempfile.TemporaryDirectory(prefix="postmerge-go-cache-")
        cls.addClassCleanup(cls.cache.cleanup)
        # No heredar un index/worktree Git ajeno ni flags/workspaces Go del host.
        cls.clean_env = {
            k: v for k, v in os.environ.items()
            if not k.startswith("GIT_") and not k.startswith("GO")
        }
        cls.clean_env.update({
            "GOPROXY": "off", "GOSUMDB": "off", "GOWORK": "off",
            "GOTOOLCHAIN": "local", "GOENV": "off", "GOFLAGS": "",
            "GOPATH": str(Path(cls.cache.name) / "gopath"),
            "GOCACHE": str(Path(cls.cache.name) / "build"),
            "GOMODCACHE": str(Path(cls.cache.name) / "modules"),
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0", "PYTHONDONTWRITEBYTECODE": "1",
        })
        result = subprocess.run(
            [cls.go, "version"], env=cls.clean_env,
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode:
            raise RuntimeError(f"Go local no usable: {result.stderr}")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="postmerge-go-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo con espacios"
        self.repo.mkdir()
        self.env = self.clean_env.copy()
        self.hooks = self.root / "hooks-vacios"
        self.hooks.mkdir()
        self._git("init", "--initial-branch=main", f"--template={self.hooks}")
        self._configure_git(self.repo)
        self._write("go.mod", f"module {MODULE}\n\ngo 1.22\n")
        self._tests({"TestHealthy": ""})
        self._commit("fixture inicial")
        self.base_count = 0

    def _run(self, args, *, repo=None, shell=False):
        return subprocess.run(
            args, cwd=repo or self.repo, env=self.env, shell=shell,
            capture_output=True, text=True, timeout=120,
        )

    @staticmethod
    def _details(result):
        return (
            f"\ncomando={result.args!r}\nexit={result.returncode}"
            f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    def _exit(self, result, expected, label):
        self.assertEqual(result.returncode, expected, label + self._details(result))

    def _git(self, *args, repo=None):
        result = self._run([self.git, *args], repo=repo)
        self._exit(result, 0, "CONTROL FIXTURE GIT")
        return result.stdout.strip()

    def _configure_git(self, repo):
        # Configuracion SOLO local a los repos fixtures, nunca global.
        for name, value in (
            ("user.name", "Postmerge Fixture"),
            ("user.email", "fixture@example.invalid"),
            ("commit.gpgsign", "false"), ("tag.gpgsign", "false"),
            ("core.hooksPath", str(self.hooks)),
        ):
            self._git("config", "--local", name, value, repo=repo)

    def _write(self, relative, content):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _tests(self, cases, package="suite"):
        definitions = "\n\n".join(
            f"func {name}(t *testing.T) {{\n{body}\n}}"
            for name, body in cases.items()
        )
        return self._write(
            f"integration/{package}/suite_test.go",
            '//go:build integration\n\npackage fixture\n\nimport "testing"\n\n'
            + definitions + "\n",
        )

    def _commit(self, message):
        self._git("add", "--all")
        self._git("commit", "--quiet", "--allow-empty", "-m", message)
        return self._git("rev-parse", "HEAD")

    def _cli(self, action, base, *, cmd=None, repo=None):
        args = [sys.executable, "-B", str(SCRIPT), action,
                "--repo", str(repo or self.repo),
                "--guardar" if action == "base" else "--base", str(base)]
        if cmd is not None:
            args += ["--cmd", cmd]
        return self._run(args, repo=repo)

    def _probe(self, *, cmd=None, exit_code=0, repo=None, measured=True):
        """Control independiente: parsear SOLO stdout del Go real, no del gate."""
        result = self._run(
            cmd if cmd is not None else [self.go, *GO_ARGS],
            shell=cmd is not None, repo=repo,
        )
        self._exit(result, exit_code, "CONTROL GO REAL")
        try:
            events = [json.loads(line) for line in result.stdout.splitlines() if line]
        except json.JSONDecodeError:
            self.fail("CONTROL GO REAL: stdout no es Go JSON" + self._details(result))
        self.assertTrue(all(isinstance(event, dict) for event in events))
        terminals = {
            (event.get("Package"), event["Test"], event.get("Action"))
            for event in events if event.get("Test")
            and event.get("Action") in ("pass", "fail", "skip")
        }
        if measured:
            self.assertTrue(
                any(action in ("pass", "fail") for _, _, action in terminals),
                "CONTROL GO REAL: no hubo tests medidos" + self._details(result),
            )
        return terminals, result

    def _has_event(self, events, name, action, package="suite"):
        self.assertIn((f"{MODULE}/integration/{package}", name, action), events,
                      "CONTROL GO REAL: falta resultado esperado")

    def _no_cures(self, result, names):
        # Detectar declaraciones sobre tests concretos, no una cabecera '0 curados'
        # ni un diagnostico que explique por que NO se puede declarar curacion.
        lines = (result.stdout + "\n" + result.stderr).splitlines()
        claims = [line for line in lines if CURE.search(line)
                  and any(name in line for name in names)
                  and not re.search(r"\b(?:no|sin|not|cannot)\b", line, re.IGNORECASE)]
        self.assertEqual(claims, [], "NO CURACION SIN MEDICION" + self._details(result))

    def _valid_base(self, *, cmd=None, debt=()):
        events, _ = self._probe(cmd=cmd, exit_code=1 if debt else 0)
        for name in debt:
            self.assertTrue(any(test == name and action == "fail"
                                for _, test, action in events), name)
        self.base_count += 1
        base = self.root / f"base-{self.base_count}.json"
        result = self._cli("base", base, cmd=cmd)
        label = "CONTROL BASE VALIDA" + (" [CUSTOM GO JSON]" if cmd is not None else " [DEFAULT]")
        self._exit(result, 0, label)
        self.assertTrue(base.is_file(), label + ": la CLI no guardo la base")
        before = base.read_bytes()  # Opaca: no suponemos campos ni version internos.
        self.assertTrue(before, label + ": base vacia")
        for name in debt:
            self.assertIn(name, result.stdout + result.stderr,
                          "CONTROL BASE: la deuda debe ser visible")
        control = self._cli("check", base, cmd=cmd)
        self._exit(control, 0, label + " / CHECK SIN CAMBIOS")
        self.assertEqual(base.read_bytes(), before, "check no debe reescribir la base")
        self._no_cures(control, debt)
        if debt:
            self.assertRegex(control.stdout + control.stderr,
                             r"(?i)deuda|preexisten|debt",
                             "La deuda tolerada debe producir un aviso")
        return base

    def _reject_check(self, base, *, cmd=None, repo=None, names=()):
        before = base.read_bytes() if base.exists() else None
        result = self._cli("check", base, cmd=cmd, repo=repo)
        # Subtests independientes: el exit incorrecto no esconde escrituras/curas.
        with self.subTest(assertion="check exit 2"):
            self._exit(result, 2, "REGRESION: CHECK NO COMPARABLE/NO MEDIDO")
        with self.subTest(assertion="check no escribe base"):
            self.assertEqual(base.read_bytes() if base.exists() else None, before)
        with self.subTest(assertion="check no cura tests no medidos"):
            self._no_cures(result, names)
        return result

    def _reject_measurement(self, base, *, cmd=None, names=()):
        self._reject_check(base, cmd=cmd, names=names)
        fresh = self.root / "base-invalida-no-debe-existir.json"
        self.assertFalse(fresh.exists())
        before = base.read_bytes()
        for target in (fresh, base):
            result = self._cli("base", target, cmd=cmd)
            with self.subTest(assertion="base exit 2", overwrite=target == base):
                self._exit(result, 2, "REGRESION: BASE SIN MEDICION COMPLETA")
            with self.subTest(assertion="base no escrita", overwrite=target == base):
                if target == base:
                    self.assertEqual(target.read_bytes(), before,
                                     "Un exit 2 no debe destruir una base anterior valida")
                else:
                    self.assertFalse(target.exists(),
                                     "Un exit 2 no debe dejar una base, ni siquiera parcial")
            with self.subTest(assertion="base no cura", overwrite=target == base):
                self._no_cures(result, names)

    def _runner(self, *, as_go=False):
        """Wrapper sin eventos sinteticos; transmite la salida del Go instalado."""
        control = self.root / "control-runner"
        control.mkdir()
        script = self.root / "runner real.py"
        script.write_text(textwrap.dedent(f"""\
            import json
            import os
            from pathlib import Path
            import subprocess
            import sys

            control = Path({str(control)!r})
            args = sys.argv[1:] or {GO_ARGS!r}
            if (control / 'exec-empty').exists():
                args = [*args, '-exec=']
            if (control / 'cache-without-wrapper').exists():
                args = [a for a in args if a != '-count=1'] + ['-exec=']
            with (control / 'argv.jsonl').open('a') as log:
                log.write(json.dumps(args) + '\\n')
            out = sys.stderr if (control / 'solo-stderr').exists() else None
            result = subprocess.run([{self.go!r}, *args], stdout=out)
            if (control / 'damage-evidence').exists() and os.environ.get('POSTMERGE_EXEC_DIR'):
                directory = Path(os.environ['POSTMERGE_EXEC_DIR'])
                paths = list(directory.glob('*.jsonl'))
                mode = (control / 'damage-evidence').read_text()
                for path in paths:
                    if mode == 'missing':
                        path.unlink()
                    elif mode == 'incomplete':
                        path.write_text(path.read_text().splitlines()[0] + '\\n')
                    elif mode == 'duplicate':
                        path.write_text(path.read_text() + path.read_text().splitlines()[-1] + '\\n')
                    elif mode == 'wrong-id':
                        events = list(map(json.loads, path.read_text().splitlines()))
                        events[-1]['id'] = '0' * 32
                        path.write_text(''.join(json.dumps(e) + '\\n' for e in events))
                    elif mode == 'exit-bool':
                        events = list(map(json.loads, path.read_text().splitlines()))
                        events[-1]['returncode'] = False
                        path.write_text(''.join(json.dumps(e) + '\\n' for e in events))
                    elif mode == 'duplicate-key':
                        text = path.read_text()
                        path.write_text(text.replace('"returncode":', '"returncode": 23, "returncode":'))
                    elif mode == 'json-invalid':
                        path.write_text('{{\\n}}\\n')
            if (control / 'diagnostico-stderr').exists():
                subprocess.run(
                    [{self.go!r}, 'test', '-count=1', '-json', './diagnostic/...'],
                    stdout=sys.stderr,
                )
            sys.exit(23 if (control / 'exit23').exists() else result.returncode)
            """), encoding="utf-8")
        command = shell_command([sys.executable, str(script)])
        if as_go:
            bin_dir = self.root / "bin"
            bin_dir.mkdir()
            if os.name == "nt":
                launcher = bin_dir / "go.cmd"
                launcher.write_text(f"@echo off\n{command} %*\nexit /b %errorlevel%\n", encoding="utf-8")
            else:
                launcher = bin_dir / "go"
                launcher.write_text(f'#!/bin/sh\nexec {command} "$@"\n', encoding="utf-8")
                launcher.chmod(0o755)
            self.env["PATH"] = str(bin_dir) + os.pathsep + self.env.get("PATH", "")
        return command, control

    def test_default_green_and_canonical_repo_alias(self):
        base = self._valid_base()
        # Windows no exige privilegios de symlink para el alias canonico.
        if os.name == "nt":
            alias = self.repo / ".." / self.repo.name
        else:
            alias = self.root / "alias del mismo repo"
            alias.symlink_to(self.repo, target_is_directory=True)
        self._exit(self._cli("check", base, repo=alias), 0,
                   "El mismo repo canonical debe seguir siendo comparable")

    def test_default_command_is_uncached_integration_go_json(self):
        _, control = self._runner(as_go=True)
        self._valid_base()
        recorded = [json.loads(line) for line in
                    (control / "argv.jsonl").read_text().splitlines()]
        self.assertEqual(recorded, [GO_ARGS, GO_ARGS],
                         "CONTRATO DEFAULT: base y check deben ejecutar exactamente Go JSON")

    def test_fixture_wrapper_adapta_comando_y_launcher_para_windows(self):
        # Solo prueba generacion portable; no afirma ejecutar Windows desde POSIX.
        with mock.patch.object(os, "name", "nt"):
            command, _ = self._runner(as_go=True)
        self.assertEqual(command, subprocess.list2cmdline([sys.executable, str(self.root / "runner real.py")]))
        self.assertTrue((self.root / "bin" / "go.cmd").is_file())

    def _debt_flow(self, cmd):
        self._tests({"TestHealthy": "", "TestDebt": 't.Fatal("deuda medida")'})
        self._commit("deuda antes del merge")
        base = self._valid_base(cmd=cmd, debt=("TestDebt",))
        before = base.read_bytes()
        self._tests({"TestHealthy": "", "TestDebt": 't.Fatal("deuda medida")',
                     "TestNew": 't.Fatal("regresion nueva")'})
        self._commit("nuevo rojo despues del merge")
        events, _ = self._probe(cmd=cmd, exit_code=1)
        self._has_event(events, "TestNew", "fail")
        result = self._cli("check", base, cmd=cmd)
        self._exit(result, 1, "REGRESION: NUEVO ROJO DEBE BLOQUEAR")
        self.assertIn("TestNew", result.stdout + result.stderr)
        self._no_cures(result, ("TestDebt",))
        self.assertEqual(base.read_bytes(), before)
        self._tests({"TestHealthy": "", "TestDebt": "", "TestNew": ""})
        self._commit("curacion realmente medida")
        events, _ = self._probe(cmd=cmd)
        self._has_event(events, "TestDebt", "pass")
        healed = self._cli("check", base, cmd=cmd)
        self._exit(healed, 0, "CONTROL: DEUDA CURADA Y SUITE VERDE")
        self.assertTrue(any("TestDebt" in line and CURE.search(line)
                            for line in (healed.stdout + healed.stderr).splitlines()),
                        "Se debe informar la curacion medida" + self._details(healed))
        self.assertEqual(base.read_bytes(), before)

    def test_default_debt_new_red_and_measured_cure(self):
        self._debt_flow(None)

    def test_custom_go_json_debt_new_red_and_measured_cure(self):
        self._debt_flow(JSON_CMD)

    def test_homonymous_tests_in_different_packages_are_new_debt(self):
        self._tests({"TestSame": 't.Fatal("deuda a")'}, "a")
        self._tests({"TestSame": ""}, "b")
        self._commit("homonimos distintos")
        base = self._valid_base(debt=("TestSame",))
        self._tests({"TestSame": 't.Fatal("nuevo rojo b")'}, "b")
        self._commit("mismo nombre otro paquete rojo")
        events, _ = self._probe(exit_code=1)
        self._has_event(events, "TestSame", "fail", "a")
        self._has_event(events, "TestSame", "fail", "b")
        result = self._cli("check", base)
        self._exit(result, 1, "REGRESION ORIGINAL: HOMONIMO NO ES DEUDA TOLERADA")
        self.assertIn(f"{MODULE}/integration/b", result.stdout + result.stderr)
        self.assertIn("TestSame", result.stdout + result.stderr)
        self._no_cures(result, ("TestSame",))

    def test_homonymous_subtests_in_already_red_packages_are_distinct(self):
        def group(shared, private):
            return {"TestGroup":
                    f't.Run("shared", func(t *testing.T) {{ {shared} }})\n'
                    + f't.Run("private", func(t *testing.T) {{ {private} }})'}
        self._tests(group('t.Fatal("deuda a shared")', ""), "a")
        self._tests(group("", 't.Fatal("deuda b private")'), "b")
        self._commit("ambos padres rojos, hijos distintos")
        base = self._valid_base(debt=("TestGroup/shared", "TestGroup/private"))
        self._tests(group('t.Fatal("nuevo b shared")', 't.Fatal("deuda b private")'), "b")
        self._commit("rojo nuevo con nombre de hijo ya rojo en otro paquete")
        events, _ = self._probe(exit_code=1)
        self._has_event(events, "TestGroup/shared", "fail", "a")
        self._has_event(events, "TestGroup/shared", "fail", "b")
        result = self._cli("check", base)
        self._exit(result, 1, "REGRESION: IDENTIDAD PAQUETE + SUBTEST, NO SOLO PADRE")
        self.assertIn(f"{MODULE}/integration/b", result.stdout + result.stderr)
        self.assertIn("TestGroup/shared", result.stdout + result.stderr)
        self._no_cures(result, ("TestGroup/shared", "TestGroup/private"))

    def test_new_subtest_failure_under_an_already_red_parent(self):
        def source(new):
            return {'TestGroup': 't.Run("old", func(t *testing.T) { t.Fatal("deuda") })\n'
                    + f't.Run("new", func(t *testing.T) {{ {new} }})'}
        self._tests(source(""))
        self._commit("deuda en subtest")
        base = self._valid_base(debt=("TestGroup/old",))
        self._tests(source('t.Fatal("regresion")'))
        self._commit("nuevo subtest rojo mismo padre")
        events, _ = self._probe(exit_code=1)
        self._has_event(events, "TestGroup/new", "fail")
        result = self._cli("check", base)
        self._exit(result, 1, "Nuevo subtest rojo no debe quedar escondido por su padre")
        self.assertIn("TestGroup/new", result.stdout + result.stderr)

    def test_broken_build_plus_healthy_package_is_incomplete_not_cured(self):
        self._tests({"TestDebt": 't.Fatal("deuda del paquete")'}, "broken")
        self._commit("deuda y paquete sano medidos")
        base = self._valid_base(debt=("TestDebt",))
        self._write("integration/broken/broken.go", "package fixture\nvar Broken = missingSymbol\n")
        self._commit("romper compilacion de un solo paquete")
        events, result = self._probe(exit_code=1)
        self._has_event(events, "TestHealthy", "pass")
        self.assertFalse(any(name == "TestDebt" for _, name, _ in events))
        self.assertIn("missingSymbol", result.stdout + result.stderr)
        self._reject_measurement(base, names=("TestDebt",))

    def _binary_exit(self, expected):
        # Control independiente del exit: no deducirlo del JSON de go test.
        binary = self.root / ("suite.test.exe" if os.name == "nt" else "suite.test")
        built = self._run([self.go, "test", "-tags", "integration", "-c", "-o",
                           str(binary), "./integration/suite"])
        self._exit(built, 0, "CONTROL COMPILACION BINARIO REAL")
        result = self._run([str(binary), "-test.v=test2json"])
        self._exit(result, expected, "CONTROL EXIT BINARIO REAL")

    def _testmain_teardown(self, teardown, expected):
        self._tests({"TestHealthy": "", "TestDebt": 't.Fatal("deuda")'})
        base = self._valid_base(debt=("TestDebt",))
        self._binary_exit(1)  # El rojo normal del binario SI es deuda medible.
        self._write("integration/suite/main_test.go",
                    'package fixture\nimport ("testing"; "os")\n'
                    'var _ = os.Exit\n'
                    f'func TestMain(m *testing.M) {{ m.Run(); {teardown} }}\n')
        self._binary_exit(expected)
        self._reject_measurement(base, names=("TestDebt",))
        # Control causal: el mismo teardown sin deuda tambien debe dar 2.
        self._tests({"TestHealthy": "", "TestDebt": ""})
        self._binary_exit(expected)
        self._reject_measurement(base, names=("TestDebt",))

    def test_testmain_exit23_is_not_explained_by_debt(self):
        self._testmain_teardown("os.Exit(23)", 23)

    def test_testmain_panic_is_not_explained_by_debt(self):
        self._testmain_teardown('panic("teardown roto")', 2)

    def _exit23_flow(self, *, custom):
        command, control = self._runner(as_go=not custom)
        cmd = command if custom else None
        self._tests({"TestHealthy": "", "TestDebt": 't.Fatal("deuda medida")'})
        self._commit("deuda antes del fallo externo al runner")
        base = self._valid_base(cmd=cmd, debt=("TestDebt",))
        self._tests({"TestHealthy": "", "TestDebt": ""})
        self._commit("Go pasa pero el comando envolvente termina mal")
        (control / "exit23").touch()
        # Siempre demostrar JSON Go valido seguido por exit 23, incluso cuando
        # el default del script antiguo solicita -v al wrapper.
        events, _ = self._probe(cmd=command, exit_code=23)
        self._has_event(events, "TestHealthy", "pass")
        self._has_event(events, "TestDebt", "pass")
        self._reject_measurement(base, cmd=cmd, names=("TestDebt",))

    def test_default_runner_exit23_after_real_go_output_is_incomplete(self):
        self._exit23_flow(custom=False)

    def test_custom_exit23_after_valid_go_json_is_incomplete(self):
        self._exit23_flow(custom=True)

    def test_real_attr_is_informative_not_a_result(self):
        # Attr requiere Go 1.25: el modulo de ESTE fixture debe declararlo.
        self._write("go.mod", f"module {MODULE}\n\ngo 1.25\n")
        self._commit("fixture: declarar version minima para Attr")
        base = self._valid_base()
        self._tests({"TestHealthy": 't.Attr("key", "value")'})
        events, raw = self._probe()
        self._has_event(events, "TestHealthy", "pass")
        self.assertTrue(any(e.get("Action") == "attr" and e.get("Key") == "key"
                            for e in map(json.loads, raw.stdout.splitlines())))
        self._exit(self._cli("check", base), 0, "ATTR REAL NO INVALIDA CHECK")
        self._exit(self._cli("base", self.root / "attr-base.json"), 0, "ATTR REAL NO INVALIDA BASE")

    def test_base_without_process_evidence_is_rejected_before_execution(self):
        command, control = self._runner()
        base = self._valid_base(cmd=command)
        data = json.loads(base.read_text())
        data.pop("ejecucion", None)  # Unica mutacion: contrato prepublicacion viejo.
        base.write_text(json.dumps(data))
        before = (control / "argv.jsonl").read_bytes()
        self._reject_check(base, cmd=command)
        self.assertEqual((control / "argv.jsonl").read_bytes(), before)

    def test_exec_override_without_wrapper_is_not_measurement(self):
        command, control = self._runner()
        base = self._valid_base(cmd=command)
        (control / "exec-empty").touch()
        self._probe(cmd=command)  # Go sano de verdad, pero falta el wait lateral.
        result = self._reject_check(base, cmd=command)
        self.assertIn("evidencia de terminacion real", result.stdout)
        self._reject_measurement(base, cmd=command)

    def test_real_cache_without_wrapper_is_not_measurement(self):
        command, control = self._runner()
        base = self._valid_base(cmd=command)
        (control / "cache-without-wrapper").touch()
        self._probe(cmd=command)
        _, raw = self._probe(cmd=command)
        self.assertIn("(cached)", raw.stdout, "CONTROL: cache Go REAL precalentada")
        result = self._reject_check(base, cmd=command)
        self.assertIn("evidencia de terminacion real", result.stdout)
        self._reject_measurement(base, cmd=command)

    def test_missing_incomplete_or_ambiguous_process_record_is_exit2(self):
        # Mutaciones de evidencia REAL, no registros fabricados para el control.
        command, control = self._runner()
        self._tests({"TestHealthy": "", "TestDebt": 't.Fatal("deuda")'})
        base = self._valid_base(cmd=command, debt=("TestDebt",))
        for mode in ("missing", "incomplete", "duplicate", "wrong-id", "exit-bool", "json-invalid"):
            with self.subTest(damage=mode):
                (control / "damage-evidence").write_text(mode)
                self._reject_measurement(base, cmd=command, names=("TestDebt",))

    def test_duplicate_json_keys_in_process_record_are_ambiguous(self):
        command, control = self._runner()
        base = self._valid_base(cmd=command)
        (control / "damage-evidence").write_text("duplicate-key")
        self._reject_measurement(base, cmd=command)

    def test_binary_is_never_run_twice_for_process_evidence(self):
        self._tests({"TestHealthy": "", "TestDebt": 't.Fatal("deuda")'})
        base = self._valid_base(debt=("TestDebt",))
        counter = self.root / "binary-runs"
        self.env["POSTMERGE_FIXTURE_COUNT"] = str(counter)
        for exit_expression, expected in (("code", 0), ("23", 2)):
            with self.subTest(binary_exit=exit_expression):
                self._write("integration/suite/main_test.go", '''package fixture
import ("os"; "testing")
func TestMain(m *testing.M) {
    f, err := os.OpenFile(os.Getenv("POSTMERGE_FIXTURE_COUNT"), os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0600)
    if err != nil { panic(err) }
    if _, err = f.WriteString("run\\n"); err != nil { panic(err) }; f.Close()
    code := m.Run(); _ = code
    os.Exit(''' + exit_expression + ''')
}
''')
                counter.unlink(missing_ok=True)
                self._exit(self._cli("check", base), expected, "UNA SOLA CORRIDA DEL BINARIO")
                self.assertEqual(counter.read_text().splitlines(), ["run"], "No repetir tests para recuperar el exit")

    def test_no_test_files_package_can_coexist_with_real_measurement(self):
        self._write("integration/empty/empty.go", "package empty\n")
        self._valid_base()

    def test_paths_with_spaces_for_python_helper_and_repo(self):
        # Sin shebang: Go ejecuta Python directamente con argv bien delimitado.
        portable = self.root / "paquete portable con espacios"
        portable.mkdir()
        for name in ("postmerge_medido.py", "postmerge_exec.py"):
            shutil.copyfile(SCRIPT.with_name(name), portable / name)
        interpreter = self.root / ("python con espacios.exe" if os.name == "nt" else "python con espacios")
        if os.name == "nt":
            # El launcher Python de Windows necesita su instalacion: no copiarlo.
            interpreter = Path(sys.executable)
        else:
            interpreter.symlink_to(sys.executable)
        base = self.root / "portable-base.json"
        for action, flag in (("base", "--guardar"), ("check", "--base")):
            self._exit(self._run([str(interpreter), "-B", str(portable / "postmerge_medido.py"), action,
                                 "--repo", str(self.repo), flag, str(base)]), 0, "RUTAS PORTABLES CON ESPACIOS")

    def test_command_identity_is_exact_not_normalized(self):
        base = self._valid_base(cmd=JSON_CMD)
        for changed in (JSON_CMD + " ", JSON_CMD.replace("-count=1", "-count 1")):
            with self.subTest(command=changed):
                self._probe(cmd=changed)  # Mismos tests y mismo resultado Go real.
                self._reject_check(base, cmd=changed, names=("TestHealthy",))

    def test_other_repo_with_same_branch_sha_and_tests_is_not_comparable(self):
        base = self._valid_base()
        clone = self.root / "otro repo identico"
        self._git("clone", "--quiet", "--no-hardlinks", f"--template={self.hooks}",
                  str(self.repo), str(clone))
        self._configure_git(clone)
        self.assertEqual(self._git("rev-parse", "HEAD"), self._git("rev-parse", "HEAD", repo=clone))
        self.assertEqual(self._git("branch", "--show-current"),
                         self._git("branch", "--show-current", repo=clone))
        self._probe(repo=clone)
        self._reject_check(base, repo=clone, names=("TestHealthy",))

    def test_other_branch_at_same_sha_is_not_comparable(self):
        base = self._valid_base()
        self._git("checkout", "--quiet", "-b", "otra-rama")
        self._probe()
        self._reject_check(base, names=("TestHealthy",))

    def test_base_sha_must_be_ancestor_even_on_same_repo_and_branch(self):
        initial = self._git("rev-parse", "HEAD")
        self._write("marker.txt", "no modifica tests\n")
        base_sha = self._commit("commit de la base")
        base = self._valid_base()
        self._git("reset", "--hard", initial)
        ancestry = self._run([self.git, "merge-base", "--is-ancestor", base_sha, "HEAD"])
        self._exit(ancestry, 1, "CONTROL GIT: el SHA base NO es ancestro")
        self.assertEqual(self._git("branch", "--show-current"), "main")
        self._probe()
        self._reject_check(base, names=("TestHealthy",))

    def test_total_skip_is_not_measurement_and_must_not_cure_debt(self):
        self._tests({"TestHealthy": "", "TestDebt": 't.Fatal("deuda")'})
        self._commit("base medida antes de skips")
        base = self._valid_base(debt=("TestDebt",))
        self._tests({"TestHealthy": 't.Skip("omitido")', "TestDebt": 't.Skip("omitido")'})
        self._commit("todos omitidos")
        events, _ = self._probe(measured=False)
        self._has_event(events, "TestDebt", "skip")
        self._has_event(events, "TestHealthy", "skip")
        self.assertFalse(any(action in ("pass", "fail") for _, _, action in events))
        self._reject_measurement(base, names=("TestDebt",))

    def _omission_flow(self, *, skipped, was_red):
        self._tests({"TestHealthy": "", "TestTracked": 't.Fatal("deuda")' if was_red else ""})
        self._commit("tests medidos antes del cambio")
        base = self._valid_base(debt=("TestTracked",) if was_red else ())
        cases = {"TestHealthy": ""}
        if skipped:
            cases["TestTracked"] = 't.Skip("no fue medido")'
        self._tests(cases)
        self._commit("omitir uno entre tests sanos")
        events, _ = self._probe()
        self._has_event(events, "TestHealthy", "pass")
        if skipped:
            self._has_event(events, "TestTracked", "skip")
        else:
            self.assertFalse(any(name == "TestTracked" for _, name, _ in events))
        # La nueva foto aislada podria ser valida (todavia mide TestHealthy).
        # Lo que NO es valido es comparar contra la foto que media TestTracked.
        self._reject_check(base, names=("TestTracked",))

    def test_deleted_debt_between_healthy_tests_is_not_cured(self):
        self._omission_flow(skipped=False, was_red=True)

    def test_skipped_debt_between_healthy_tests_is_not_cured(self):
        self._omission_flow(skipped=True, was_red=True)

    def test_deleted_previously_green_test_is_incomplete(self):
        self._omission_flow(skipped=False, was_red=False)

    def test_skipped_previously_green_test_is_incomplete(self):
        self._omission_flow(skipped=True, was_red=False)

    def test_omitted_subtest_is_incomplete_even_when_its_parent_passes(self):
        self._tests({"TestGroup": 't.Run("tracked", func(t *testing.T) {})'})
        self._commit("subtest medido")
        base = self._valid_base()
        self._tests({"TestGroup": ""})
        self._commit("padre permanece hijo desaparece")
        events, _ = self._probe()
        self._has_event(events, "TestGroup", "pass")
        self.assertFalse(any(name == "TestGroup/tracked" for _, name, _ in events))
        self._reject_check(base, names=("TestGroup/tracked",))

    def test_empty_run_selector_after_valid_selected_base_is_incomplete(self):
        cmd = shell_command(["go", *GO_ARGS[:-1], "-run", "^TestSelected$", GO_ARGS[-1]])
        self._tests({"TestSelected": "", "TestHealthy": ""})
        self._commit("selector con coincidencia positiva")
        base = self._valid_base(cmd=cmd)
        self._tests({"TestHealthy": ""})
        self._commit("selector ya no encuentra tests aunque otro existe")
        self._probe()  # El repo sigue teniendo un test sano fuera del selector.
        events, _ = self._probe(cmd=cmd, measured=False)
        self.assertEqual(events, set())
        self._reject_measurement(base, cmd=cmd, names=("TestSelected",))

    def test_empty_package_selector_after_valid_selected_base_is_incomplete(self):
        cmd = shell_command(["go", *GO_ARGS[:-1], "./integration/selected/..."])
        self._tests({"TestSelected": ""}, "selected")
        self._commit("paquete seleccionado existe")
        base = self._valid_base(cmd=cmd)
        shutil.rmtree(self.repo / "integration" / "selected")
        self._commit("selector de paquetes ya no tiene coincidencias")
        self._probe()
        # Go puede usar 0 o 1 para un wildcard de paquetes sin coincidencias;
        # ambos deben volverse 2 en el gate, nunca una foto de cero rojos.
        raw = self._run(cmd, shell=True)
        self.assertIn(raw.returncode, (0, 1), self._details(raw))
        self.assertFalse(any(json.loads(line).get("Test")
                             for line in raw.stdout.splitlines() if line), self._details(raw))
        self._reject_measurement(base, cmd=cmd, names=("TestSelected",))

    def test_default_package_with_no_test_files_is_incomplete(self):
        base = self._valid_base()
        (self.repo / "integration" / "suite" / "suite_test.go").unlink()
        self._write("integration/suite/suite.go", "package fixture\n")
        self._commit("paquete existe pero no tiene tests")
        events, _ = self._probe(measured=False)
        self.assertEqual(events, set())
        self._reject_measurement(base, names=("TestHealthy",))

    def test_go_json_only_on_stderr_is_not_measurement(self):
        command, control = self._runner()
        base = self._valid_base(cmd=command)
        (control / "solo-stderr").touch()
        events, raw = self._probe(cmd=command, measured=False)
        self.assertEqual(events, set())
        stderr_events = [json.loads(line) for line in raw.stderr.splitlines() if line]
        self.assertTrue(any(e.get("Test") == "TestHealthy" and e.get("Action") == "pass"
                            for e in stderr_events))
        self._reject_measurement(base, cmd=command, names=("TestHealthy",))

    def test_valid_stdout_is_not_polluted_by_real_go_json_on_stderr(self):
        self._write("diagnostic/diagnostic_test.go", 'package diagnostic\nimport "testing"\n'
                    'func TestDiagnostic(t *testing.T) { t.Fatal("solo stderr") }\n')
        self._commit("diagnostico fuera del alcance de integration")
        command, control = self._runner()
        base = self._valid_base(cmd=command)
        (control / "diagnostico-stderr").touch()
        events, raw = self._probe(cmd=command)
        self._has_event(events, "TestHealthy", "pass")
        stderr_events = [json.loads(line) for line in raw.stderr.splitlines() if line]
        self.assertTrue(any(e.get("Test") == "TestDiagnostic" and e.get("Action") == "fail"
                            for e in stderr_events))
        result = self._cli("check", base, cmd=command)
        self._exit(result, 0, "JSON de stderr no es evidencia de la suite en stdout")
        self._no_cures(result, ("TestDiagnostic",))

    def test_missing_base_is_exit2_not_traceback_or_new_base(self):
        control = self._valid_base()
        before = control.read_bytes()
        absent = self.root / "base-ausente.json"
        self.assertFalse(absent.exists())
        result = self._reject_check(absent, names=("TestHealthy",))
        with self.subTest(assertion="diagnostico controlado"):
            self.assertNotIn("Traceback", result.stdout + result.stderr)
        self.assertFalse(absent.exists())
        self.assertEqual(control.read_bytes(), before)

    def test_corrupt_or_wrong_shape_base_is_exit2_without_overwriting_it(self):
        control = self._valid_base()
        before = control.read_bytes()
        for index, corrupt in enumerate((b"{not-json", b"{}", b"[]", b"null")):
            with self.subTest(corruption=corrupt):
                bad = self.root / f"base-corrupta-{index}.json"
                bad.write_bytes(corrupt)  # Unica excepcion: base corrupta intencional.
                result = self._reject_check(bad, names=("TestHealthy",))
                with self.subTest(assertion="diagnostico controlado"):
                    self.assertNotIn("Traceback", result.stdout + result.stderr)
                self.assertEqual(bad.read_bytes(), corrupt)
        self.assertEqual(control.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
