#!/bin/bash
# Public contract/routing and conditional dependency checks. Actual PDF page
# acceptance lives in tests/integration/check-running-headers.py.
run_render_running_headers_test() {
  local scratch
  scratch="$(new_test_tmpdir)" || return
  mkdir -p "$scratch/work/chapters" "$scratch/home"
  printf '# First chapter\n\nText.\n' >"$scratch/work/chapters/01.md"
  write_contract_config "$scratch/config.yaml" natural true "" false false
  if "$REAL_PYTHON3" - "$CLI" "$scratch" <<'PY'
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

cli, scratch = sys.argv[1], Path(sys.argv[2]).resolve()
# Derive variants from the shared YAML fixture without requiring a YAML parser
# in the test process; parsing is exercised through the public CLI.
base_text = (scratch / "config.yaml").read_text()
(scratch / "work/meta.yaml").write_text("title: Metadata title\n")
env = dict(os.environ, HOME=str(scratch / "home"),
           XDG_CONFIG_HOME=str(scratch / "home"), SKELEPRESS_LANG="en",
           SKELEPRESS_PROJECT_ENV=str(scratch / "no-project-env"))


class RunningHeaders(unittest.TestCase):
    def invoke(self, text, command="render"):
        config = scratch / "config.yaml"
        config.write_text(text)
        before = {str(p): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
        args = [cli, command, "-c", str(config)]
        if command == "render":
            args += ["--dry-run", "--json"]
        result = subprocess.run(args, cwd=scratch, env=env, capture_output=True, text=True)
        after = {str(p): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
        self.assertEqual(before, after, "validation/planning must not write inputs or outputs")
        return result

    def plan(self, text):
        result = self.invoke(text)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "✅ Config valid\n")
        return json.loads(result.stdout)

    def test_pdf_routing_and_previous_defaults(self):
        for template in ("", "  template: book\n", "  template: ./custom.tex\n"):
            (scratch / "work/custom.tex").write_text("Consumer-owned template\n")
            for metadata in ("", "meta.yaml"):
                with self.subTest(template=template, metadata=metadata):
                    (scratch / "work/meta.yaml").write_text("title: Metadata title\n")
                    text = base_text.replace('metadata_file: ""', f'metadata_file: "{metadata}"')
                    text = text.replace("pandoc:\n", "pandoc:\n" + template)
                    baseline = self.plan(text)
                    disabled = self.plan(text.replace("pandoc:\n", "pandoc:\n  running_headers: false\n"))
                    self.assertEqual(baseline, disabled)
                    enabled = self.plan(text.replace("pandoc:\n", "pandoc:\n  running_headers: true\n"))
                    argv = enabled["pandoc"]["argv"]
                    index = argv.index("running-headers=true")
                    self.assertEqual(argv[index - 1], "-V")
                    del argv[index - 1:index + 1]
                    self.assertEqual(enabled, baseline, "only the dedicated PDF variable may change")
                    self.assertEqual("title=S1 Document" in argv, not bool(metadata))
                    self.assertEqual((scratch / "work/custom.tex").read_text(), "Consumer-owned template\n")

    def test_epub_and_multi_format_isolation(self):
        for metadata in ("", "meta.yaml"):
            for formats in ("[epub]", "[pdf, epub]", "[epub, pdf]"):
                with self.subTest(metadata=metadata, formats=formats):
                    text = base_text.replace('metadata_file: ""', f'metadata_file: "{metadata}"')
                    text = text.replace("output:\n", f"output:\n  formats: {formats}\n")
                    baseline = self.plan(text)
                    for value in ("false", "true"):
                        changed = self.plan(text.replace("pandoc:\n", f"pandoc:\n  running_headers: {value}\n"))
                        jobs = changed.get("jobs", [changed])
                        originals = baseline.get("jobs", [baseline])
                        for job, original in zip(jobs, originals):
                            if "pdf" in job["pandoc"]["target"] and value == "true":
                                argv = job["pandoc"]["argv"]
                                index = argv.index("running-headers=true")
                                self.assertEqual(argv[index - 1], "-V")
                                del argv[index - 1:index + 1]
                            self.assertEqual(job, original, "EPUB args, metadata and plan remain unchanged")

    def test_boolean_validation(self):
        for value in (None, "true", "false", '"false"', "1", "null", "[]", "{}"):
            for command in ("validate-config", "render"):
                with self.subTest(value=value, command=command):
                    text = base_text if value is None else base_text.replace(
                        "pandoc:\n", f"pandoc:\n  running_headers: {value}\n")
                    result = self.invoke(text, command)
                    valid = value in (None, "true", "false")
                    self.assertEqual(result.returncode, 0 if valid else 1)
                    if not valid:
                        error = "❌ 'pandoc.running_headers' must be of type boolean\n"
                        self.assertEqual(result.stdout, error if command == "validate-config" else "")
                        self.assertEqual(result.stderr, "" if command == "validate-config" else error)
                    elif command == "validate-config":
                        self.assertEqual(result.stdout, "✅ Config valid\n")
                        self.assertEqual(result.stderr, "")


unittest.main(argv=[sys.argv[0]])
PY
  then
    pass "running_headers validates booleans and routes only enabled PDF jobs without changing defaults"
  else
    fail "running_headers public validation/routing contract"
  fi
  rm -rf "$scratch"
}

run_running_headers_preflight_test() {
  local scratch
  scratch="$(mktemp -d)"
  mkdir -p "$scratch/work/chapters" "$scratch/home"
  printf '# Heading\n\nText.\n' >"$scratch/work/chapters/01.md"
  write_contract_config "$scratch/config.yaml" natural true "" false false
  if "$REAL_PYTHON3" - "$CLI" "$scratch" <<'PY'
import json
import os
import subprocess
import sys
import shutil
from pathlib import Path

cli, scratch = sys.argv[1], Path(sys.argv[2]).resolve()
base = (scratch / "config.yaml").read_text().replace("    enabled: true", "    enabled: false")
bindir = scratch / "bin"
bindir.mkdir()
real_python = sys.executable
(bindir / "bash").symlink_to("/bin/bash")
for name, content in {
    "python3": f'#!/bin/bash\nexec "{real_python}" "$@"\n',
    "pandoc": f'#!/bin/bash\nprintf called >>"{scratch}/compile-count"\nexit 0\n',
    "lualatex": '#!/bin/bash\nexit 0\n',
    "kpsewhich": '#!/bin/bash\nexit 1\n',
}.items():
    target = bindir / name
    target.write_text(content)
    target.chmod(0o755)
(scratch / "work/custom.tex").write_text("Consumer-owned template\n")
env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"], HOME=str(scratch / "home"),
           SKELEPRESS_LANG="en", SKELEPRESS_PROJECT_ENV=str(scratch / "absent-env"))
missing = "❌ Doctor detected missing dependencies:\n   - truncate.sty\n"
# Build the isolated fixture completely before any CLI probe. No inherited PATH
# can accidentally supply kpsewhich; locale/bootstrap helpers must still work.
isolated = scratch / "isolated-bin"
isolated.mkdir()
helpers = ("bash", "ruby", "tr", "sort", "dirname", "basename", "readlink", "uname")
resolved = {name: shutil.which(name) for name in helpers}
assert all(resolved.values()), ("missing fixture prerequisites", resolved)
for name, executable in resolved.items():
    (isolated / name).symlink_to(executable)
for name in ("python3", "pandoc", "lualatex"):
    (isolated / name).symlink_to(bindir / name)
shadow = scratch / "without-pyyaml"
shadow.mkdir()
(shadow / "yaml.py").write_text('raise ImportError("PyYAML deliberately unavailable")\n')
fallback_env = dict(env, PYTHONPATH=str(shadow), PYTHONDONTWRITEBYTECODE="1",
                    XDG_CONFIG_HOME=str(scratch / "home"))
isolated_env = dict(fallback_env, PATH=str(isolated))
assert shutil.which("kpsewhich", path=isolated_env["PATH"]) is None
ruby_probe = subprocess.run([str(isolated / "ruby"), "-e",
                             "require 'yaml'; require 'json'; puts JSON.generate(YAML.safe_load('flag: yes'))"],
                            env=isolated_env, capture_output=True, text=True)
assert (ruby_probe.returncode, ruby_probe.stdout, ruby_probe.stderr) == (0, '{"flag":true}\n', ""), ruby_probe
print("Fixture prerequisites: Python, Bash, Ruby YAML/JSON, tr, sort, dirname, basename, readlink, uname; isolated PATH has no kpsewhich", flush=True)


def unchanged_call(text, command, call_env):
    config = scratch / "config.yaml"
    config.write_text(text)
    before = {str(p): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
    directories = {str(p) for p in scratch.rglob("*") if p.is_dir()}
    result = subprocess.run([cli, command, "-c", str(config)], cwd=scratch,
                            env=call_env, capture_output=True, text=True)
    assert before == {str(p): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}, command
    assert directories == {str(p) for p in scratch.rglob("*") if p.is_dir()}, command
    return result.returncode, result.stdout, result.stderr


# Missing lookup is distinct from an installed lookup reporting no package.
for template in ("", "  template: book\n"):
    text = base.replace("pandoc:\n", "pandoc:\n  running_headers: true\n" + template)
    for command in ("doctor", "render"):
        actual = unchanged_call(text, command, isolated_env)
        assert actual == (1, ("✅ Config valid\n" if command == "render" else "") + missing, ""), actual
        print(f"PASS no-kpsewhich {command} {template.strip() or 'default'}: exit 1, exact streams, unchanged state", flush=True)

# Exercise full-parser boolean semantics with PyYAML unavailable, through the
# public interface only. Collect mismatches so RED records every named alias.
fallback_failures = []
for value in ("true", "TRUE", "yes", "Yes", "on", "ON"):
    text = base.replace("pandoc:\n", f"pandoc:\n  running_headers: {value}\n")
    valid = unchanged_call(text, "validate-config", fallback_env)
    assert valid == (0, "✅ Config valid\n", ""), (value, valid)
    actual = unchanged_call(text, "doctor", fallback_env)
    expected = (1, missing, "")
    print(f"Fallback {value}: validate={valid!r}; doctor={actual!r}; unchanged state", flush=True)
    if actual != expected:
        fallback_failures.append((value, actual, expected))
for setting, formats in (("", "pdf"), ("  running_headers: false\n", "pdf"),
                         ("  running_headers: true\n", "epub"),
                         ("  running_headers: true\n  template: ./custom.tex\n", "pdf")):
    text = base.replace("pandoc:\n", "pandoc:\n" + setting).replace("output:\n", f"output:\n  formats: [{formats}]\n")
    actual = unchanged_call(text, "doctor", fallback_env)
    assert actual == (0, "✅ Doctor OK: dependencies available\n", ""), (setting, formats, actual)
print("PASS fallback default/false/EPUB/custom exemptions: exit 0, exact streams, unchanged state", flush=True)
for template in ("", "  template: book\n", "  template: ./custom.tex\n"):
    for value in (None, False, True):
        for formats in ("[pdf]", "[epub]", "[pdf, epub]"):
            for strict in (True, False):
                text = base.replace("pandoc:\n", "pandoc:\n" + template)
                if value is not None:
                    text = text.replace("pandoc:\n", f"pandoc:\n  running_headers: {str(value).lower()}\n")
                text = text.replace("output:\n", f"output:\n  formats: {formats}\n")
                text = text.replace("  strict: true", f"  strict: {str(strict).lower()}")
                config = scratch / "config.yaml"
                config.write_text(text)
                before = {str(p): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
                directories = {str(p) for p in scratch.rglob("*") if p.is_dir()}
                result = subprocess.run([cli, "doctor", "-c", str(config)], env=env,
                                        capture_output=True, text=True)
                required = value is True and formats != "[epub]" and "custom" not in template
                assert (result.returncode, result.stdout, result.stderr) == (
                    1 if required else 0, missing if required else "✅ Doctor OK: dependencies available\n", ""
                ), (template, value, formats, strict, result)
                after = {str(p): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
                assert before == after, "doctor must not change files or compile counters"
                assert directories == {str(p) for p in scratch.rglob("*") if p.is_dir()}
# Public render must reject before merge/output/compilation, even in lax mode.
for template in ("", "  template: book\n"):
    for strict in ("true", "false"):
        text = base.replace("pandoc:\n", "pandoc:\n  running_headers: true\n" + template)
        text = text.replace("strict: true", "strict: " + strict)
        (scratch / "config.yaml").write_text(text)
        before = {str(p): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
        directories = {str(p) for p in scratch.rglob("*") if p.is_dir()}
        result = subprocess.run([cli, "render", "-c", str(scratch / "config.yaml")], env=env,
                                capture_output=True, text=True)
        assert (result.returncode, result.stdout, result.stderr) == (1, "✅ Config valid\n" + missing, ""), result
        assert before == {str(p): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
        assert directories == {str(p) for p in scratch.rglob("*") if p.is_dir()}
# Prove existing render streams and side effects still match the public plan.
# Missing optional truncate must not affect default/false/EPUB/custom execution.
for setting, formats in (("", "pdf"), ("  running_headers: false\n", "pdf"),
                         ("  running_headers: true\n", "epub"),
                         ("  running_headers: true\n  template: ./custom.tex\n", "pdf"),
                         ("  running_headers: true\n", "pdf")):
    if setting == "  running_headers: true\n" and formats == "pdf":
        (bindir / "kpsewhich").write_text('#!/bin/bash\nprintf "/tex/truncate.sty\\n"\n')
    text = base.replace("pandoc:\n", "pandoc:\n" + setting).replace("output:\n", f"output:\n  formats: [{formats}]\n")
    config = scratch / "config.yaml"
    config.write_text(text)
    plan_result = subprocess.run([cli, "render", "-c", str(config), "--dry-run", "--json"],
                                 env=env, capture_output=True, text=True)
    assert (plan_result.returncode, plan_result.stderr) == (0, "✅ Config valid\n"), plan_result
    plan = json.loads(plan_result.stdout)
    targets = plan["pandoc"]["target"]
    label = "PDF" if formats == "pdf" else "EPUB"
    expected = ("✅ Config valid\n✅ Native mode enabled\n"
                f"📄 Merged markdown: {targets['markdown']}\n"
                f"🖨️  Output {label}: {targets[formats]}\n"
                f"▶ Running: {' '.join(plan['pandoc']['argv'])}\n")
    counter = scratch / "compile-count"
    old_count = counter.read_text() if counter.exists() else ""
    result = subprocess.run([cli, "render", "-c", str(config)], env=env, capture_output=True, text=True)
    assert (result.returncode, result.stdout, result.stderr) == (0, expected, ""), result
    assert counter.read_text() == old_count + "called"
    assert Path(targets["markdown"]).read_text().strip() == "# Heading\n\nText."
    assert config.read_text() == text
    assert (scratch / "work/custom.tex").read_text() == "Consumer-owned template\n"
result = subprocess.run([cli, "doctor", "-c", str(config)], env=env, capture_output=True, text=True)
assert (result.returncode, result.stdout, result.stderr) == (0, "✅ Doctor OK: dependencies available\n", "")
print("PASS: 54 doctor cases, 4 render rejections, 5 preserved/successful executions; exact streams and file/counter state", flush=True)
assert not fallback_failures, fallback_failures
print("PASS: 6 fallback boolean aliases, 4 fallback exemptions, 4 no-kpsewhich rejections")
PY
  then
    pass "running-header dependency is mandatory only for enabled shipped PDF layouts"
  else
    fail "running-header conditional preflight"
  fi
  rm -rf "$scratch"
}
