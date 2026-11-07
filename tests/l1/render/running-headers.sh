#!/bin/bash
# Public contract/routing only; visible PDF headers are tested with the layout.
run_render_running_headers_test() {
  local scratch
  scratch="$(mktemp -d)"
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
