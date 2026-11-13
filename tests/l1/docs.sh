# Exercise the consumer's files through the public CLI, not a second renderer.
run_consumer_extension_tests() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP consumer media/filter output (pandoc not available)"
    return 0
  fi

  local scratch code
  scratch="$(new_test_tmpdir)" || return
  set +e
  PYTHONDONTWRITEBYTECODE=1 "${REAL_PYTHON3}" - "$ROOT_DIR" "$CLI" "$scratch" <<'PY'
import copy
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import zipfile
import xml.etree.ElementTree as ET

root, cli, scratch = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
sys.path.insert(0, str(root / "scripts/runtime"))
from schema_runtime import load_yaml

manual = root / "examples/manual"
config = load_yaml(manual / "skelepress.config.yaml")
chapter = "05a-visual-check.md"
for name in ("home", "config", "cache", "tmp", "unrelated"):
    (scratch / name).mkdir()
env = {"PATH": os.environ["PATH"], "HOME": str(scratch / "home"),
       "XDG_CONFIG_HOME": str(scratch / "config"),
       "XDG_CACHE_HOME": str(scratch / "cache"), "TMPDIR": str(scratch / "tmp"),
       "SKELEPRESS_PROJECT_ENV": str(scratch / "absent-project-env"),
       "SKELEPRESS_LANG": "en", "PYTHONDONTWRITEBYTECODE": "1"}

class ConsumerExtension(unittest.TestCase):
    def render(self, enabled):
        import tempfile
        project = Path(tempfile.mkdtemp(prefix="enabled-" if enabled else "disabled-", dir=scratch))
        for directory, filename in (("chapters", chapter), ("media", "indicator.svg"),
                                    ("filters", "mark-check.lua")):
            (project / directory).mkdir()
            shutil.copyfile(manual / directory / filename, project / directory / filename)
        derived = copy.deepcopy(config)
        derived["project"]["base_dir"] = "."
        derived["input"]["explicit_files"] = [chapter]
        derived["output"].update(formats=["epub"], dir="out", file_prefix="probe", suffix="fixed")
        derived["filters"]["emoji"] = {"enabled": False}
        derived["filters"]["mermaid"] = {"enabled": False}
        if not enabled:
            derived["filters"]["extra_lua_filters"] = []
        derived["runtime"]["required_commands"] = ["pandoc", "python3"]
        # JSON is YAML too, using the same public version-1 contract.
        import json
        path = project / "skelepress.config.yaml"
        path.write_text(json.dumps(derived), encoding="utf-8")
        result = subprocess.run([cli, "render", "-c", str(path)], cwd=scratch / "unrelated",
                                env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        publication = project / "out/probe-fixed.epub"
        self.assertTrue(publication.is_file(), result.stdout)
        return publication

    def text(self, publication):
        with zipfile.ZipFile(publication) as archive:
            bodies = [ET.fromstring(archive.read(name)).find("{http://www.w3.org/1999/xhtml}body")
                      for name in archive.namelist() if name.endswith(".xhtml")]
            return " ".join(" ".join("".join(body.itertext()) for body in bodies).split())

    def test_declared_consumer_paths_and_reading_order(self):
        self.assertIn("media", config["pandoc"]["resource_path"])
        self.assertEqual(config["filters"]["extra_lua_filters"], ["filters/mark-check.lua"])
        order = config["input"]["explicit_files"]
        self.assertLess(order.index("05-maintenance.md"), order.index(chapter))
        self.assertLess(order.index(chapter), order.index("06-appendix.md"))
        source = (manual / "chapters" / chapter).read_text()
        self.assertIn("![Indicator panel][indicator-panel]", source)
        self.assertIn("[indicator-panel]: indicator.svg", source)

    def test_authored_figure_is_embedded_and_referenced(self):
        publication = self.render(True)
        with zipfile.ZipFile(publication) as archive:
            images = [name for name in archive.namelist() if name.endswith(".svg")]
            self.assertEqual(len(images), 1)
            self.assertEqual(archive.read(images[0]), (manual / "media/indicator.svg").read_bytes())
            import posixpath
            references = []
            for name in archive.namelist():
                if name.endswith(".xhtml"):
                    for node in ET.fromstring(archive.read(name)).iter():
                        if node.tag.endswith("}img"):
                            references.append(posixpath.normpath(posixpath.join(
                                posixpath.dirname(name), node.attrib["src"])))
            self.assertIn(images[0], references)

    def test_lua_source_references_do_not_escape_the_publication(self):
        import posixpath
        from urllib.parse import unquote, urlsplit
        publication = self.render(True)
        self.assertIn("mark-check.lua", self.text(publication))
        with zipfile.ZipFile(publication) as archive:
            for name in archive.namelist():
                if not name.endswith(".xhtml"):
                    continue
                for anchor in ET.fromstring(archive.read(name)).iter("{http://www.w3.org/1999/xhtml}a"):
                    href = urlsplit(anchor.get("href", ""))
                    if not href.scheme and not href.netloc and href.path.endswith(".lua"):
                        target = posixpath.normpath(posixpath.join(
                            posixpath.dirname(name), unquote(href.path)))
                        self.assertIn(target, archive.namelist(),
                                      f"{name}: Lua-source href {anchor.get('href')} is not packaged")

    def test_opt_in_filter_has_named_visible_effect(self):
        text = self.text(self.render(True))
        self.assertIn("CHECK: Inspect the indicator before operation.", text)
        self.assertIn("Ordinary text stays unchanged.", text)

    def test_disabled_filter_preserves_original_phrase(self):
        text = self.text(self.render(False))
        self.assertIn("Inspect the indicator before operation.", text)
        self.assertNotIn("CHECK: Inspect the indicator before operation.", text)
        self.assertIn("Ordinary text stays unchanged.", text)

try:
    result = unittest.main(argv=["consumer-extension"], verbosity=2, exit=False).result
    code = 0 if result.wasSuccessful() else 1
finally:
    shutil.rmtree(scratch)
sys.exit(code)
PY
  code=$?
  set -e
  assert_exit_code "0" "$code" "consumer media and opt-in filter survive public EPUB rendering"
}

run_documentation_skill_test() {
  local out err code
  out="$(new_test_tmpfile)" || return
  err="$(new_test_tmpfile)" || return
  set +e
  python3 - "${ROOT_DIR}" >"$out" 2>"$err" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
path = root / "skills/skelepress-documentation/SKILL.md"
text = path.read_text(encoding="utf-8")
frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
assert frontmatter, "skill needs YAML frontmatter"
fields = dict(line.split(": ", 1) for line in frontmatter[1].splitlines())
assert fields["name"] == path.parent.name
assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields["name"])
assert len(fields["name"]) <= 64
# A JSON-quoted scalar is valid YAML without requiring a YAML parser in CI.
description = json.loads(fields["description"])
assert isinstance(description, str) and 0 < len(description) <= 1024
assert "Markdown" in description and "PDF" in description
links = re.findall(r"\]\(([^)]+)\)", text[frontmatter.end():])
assert links and all(link.startswith("https://github.com/pablobernardo/skelepress/") for link in links), "references must survive installation outside the toolkit"
print("skill structure OK")
PY
  code=$?
  set -e
  assert_exit_code "0" "$code" "consumer skill has portable Agent Skills metadata and references"
  if [[ "$(<"$out")" == "skill structure OK" ]]; then
    pass "skill structural check reports its result"
  else
    fail "skill structural check reports its result"
  fi
  if [[ ! -s "$err" ]]; then
    pass "skill structural check has no diagnostics"
  else
    fail "skill structural check has no diagnostics"
  fi
  rm -f "$out" "$err"
}

run_docs_consistency_test() {
  local out code tree covered
  out="$(new_test_tmpfile)" || return
  tree="$(new_test_tmpdir)" || return

  set +e
  python3 "${ROOT_DIR}/scripts/dev/check-docs.py" "${ROOT_DIR}" >"$out" 2>&1
  code=$?
  set -e
  assert_exit_code "0" "$code" "every markdown reference points at something that exists"
  assert_contains "$out" "markdown files" "the check reports how much it covered"

  covered=$(sed -n 's/.*docs OK: \([0-9]*\) markdown files.*/\1/p' "$out" | head -1)
  if [[ "${covered:-0}" -ge 20 ]]; then
    pass "the check covers the tracked tree (${covered} markdown files)"
  else
    fail "the check must cover the tracked tree, it covered ${covered:-0}"
  fi

  # Build artifacts and local scratch must not decide the result: a stale file
  # under a gitignored directory once failed the gate over a document that was
  # never published, and the reported coverage drifted with whatever scratch
  # happened to be on the machine.
  local repo
  repo="$(new_test_tmpdir)" || return
  git -C "$repo" init --quiet
  printf 'out/\n' >"$repo/.gitignore"
  printf '# Doc\n\nSee [the other doc](other.md).\n' >"$repo/tracked.md"
  printf '# Other\n' >"$repo/other.md"
  git -C "$repo" add .gitignore tracked.md other.md
  mkdir -p "$repo/out"
  printf '# Stale\n\nSee [gone](missing.md).\n' >"$repo/out/stale.md"
  set +e
  python3 "${ROOT_DIR}/scripts/dev/check-docs.py" "$repo" >"$out" 2>&1
  code=$?
  set -e
  assert_exit_code "0" "$code" "an ignored markdown file does not decide the check"

  # A rename in progress: git's index still lists a path that is absent
  # from disk (an uncommitted rename deletes the file while the index keeps
  # the old path). Staging a path without writing it reproduces exactly that
  # state. The checker must skip the git-listed path instead of crashing.
  blob=$(printf '# Gone\n' | git -C "$repo" hash-object -w --stdin)
  git -C "$repo" update-index --add --cacheinfo "100644,${blob},vanished.md"
  set +e
  python3 "${ROOT_DIR}/scripts/dev/check-docs.py" "$repo" >"$out" 2>&1
  code=$?
  set -e
  assert_exit_code "0" "$code" "a git-listed file missing from disk is skipped, not fatal"
  assert_not_contains "$out" "Traceback" "a rename in progress does not crash the check"

  # Untracked but not ignored still counts: that is what a commit would add.
  printf '# New\n\nSee [gone](missing.md).\n' >"$repo/new.md"
  set +e
  python3 "${ROOT_DIR}/scripts/dev/check-docs.py" "$repo" >"$out" 2>&1
  code=$?
  set -e
  assert_exit_code "1" "$code" "an untracked markdown file is still checked"
  rm -rf "$repo"

  # A relative link whose target is gone must fail.
  mkdir -p "${tree}/docs"
  printf '# Doc\n\nSee [the other doc](missing.md).\n' >"${tree}/docs/a.md"
  set +e
  python3 "${ROOT_DIR}/scripts/dev/check-docs.py" "$tree" >"$out" 2>&1
  code=$?
  set -e
  assert_exit_code "1" "$code" "a broken link fails the check"
  assert_contains "$out" "missing.md" "the failure names the missing target"

  # A backticked path in prose must fail too: no link checker sees those.
  printf '# Doc\n\nThe file `docs/gone.md` was removed.\n' >"${tree}/docs/a.md"
  set +e
  python3 "${ROOT_DIR}/scripts/dev/check-docs.py" "$tree" >"$out" 2>&1
  code=$?
  set -e
  assert_exit_code "1" "$code" "a backticked path that does not exist fails the check"
  assert_contains "$out" "docs/gone.md" "the failure names the backticked path"

  # Commands inside fenced blocks are examples, not references.
  printf '# Doc\n\n```bash\ncat docs/not-there.md\n```\n' >"${tree}/docs/a.md"
  set +e
  python3 "${ROOT_DIR}/scripts/dev/check-docs.py" "$tree" >"$out" 2>&1
  code=$?
  set -e
  assert_exit_code "0" "$code" "paths inside fenced code blocks are not references"

  # History is allowed to name what was removed: that is what it records.
  rm -f "${tree}/docs/a.md"
  printf '# Changelog\n\nRemoved `scripts/gone.rb` in 1.2.0.\n' >"${tree}/CHANGELOG.md"
  set +e
  python3 "${ROOT_DIR}/scripts/dev/check-docs.py" "$tree" >"$out" 2>&1
  code=$?
  set -e
  assert_exit_code "0" "$code" "a history file may name what was removed"

  # An absolute home path would publish a machine's layout.
  rm -f "${tree}/CHANGELOG.md"
  # Built at run time so this test file does not itself contain the pattern.
  local leaky="/Users"
  printf '# Doc\n\nSee `%s/someone/code/repo/.env`.\n' "$leaky" >"${tree}/docs/a.md"
  set +e
  python3 "${ROOT_DIR}/scripts/dev/check-docs.py" "$tree" >"$out" 2>&1
  code=$?
  set -e
  assert_exit_code "1" "$code" "an absolute home path fails the check"
  assert_contains "$out" "absolute home path" "the failure names the leak"

  rm -rf "$tree"
  rm -f "$out"
}

run_examples_validate_test() {
  local f code count=0
  # Only files a commit could publish: ignored run output under examples/.output
  # is regenerated on demand and can reference paths that no longer exist, so it
  # must not decide whether the examples validate.
  while IFS= read -r f; do
    [[ -f "$f" ]] || continue
    count=$((count + 1))
    set +e
    SKELEPRESS_LANG=en "$CLI" validate-config -c "$f" >/dev/null 2>&1
    code=$?
    set -e
    assert_exit_code "0" "$code" "example config validates: ${f#"${ROOT_DIR}/"}"
  done < <(git -C "$ROOT_DIR" ls-files -z --cached --others --exclude-standard -- examples \
             | tr '\0' '\n' | grep -E '^examples/(.+/)?skelepress\.config[^/]*\.yaml$' \
             | sed "s|^|${ROOT_DIR}/|" | sort)

  if [[ "$count" -ge 1 ]]; then
    pass "the examples are exercised (${count} config(s))"
  else
    fail "no example config was found: the test would pass without checking anything"
  fi
}

# A hand-written reading order goes stale the moment a document is added, which is
# exactly the drift this example exists to demonstrate a guard against.
run_documentation_example_coverage_test() {
  local planned expected missing

  # The documentation example declares two formats, so its plan is the version-2
  # envelope with one version-1 job per format; a single-format configuration
  # would be a bare version-1 plan. Read both shapes instead of assuming one, and
  # never let a failing helper abort the suite silently: an empty result is
  # reported by the assertion below.
  planned="$(SKELEPRESS_LANG=en "$CLI" render -c "${ROOT_DIR}/examples/documentation/skelepress.config.yaml" \
    --dry-run --json 2>/dev/null \
    | "${REAL_PYTHON3}" -c '
import json
import sys

plan = json.load(sys.stdin)
jobs = plan["jobs"] if "jobs" in plan else [plan]
print("\n".join(sorted({path.split("/")[-1] for job in jobs for path in job["chapters"]})))
' 2>/dev/null)" || planned=""

  expected="$(cd "${ROOT_DIR}/docs" && ls -1 *.md | grep -v '^README\.md$' | sort)"
  missing="$(comm -13 <(printf '%s\n' "$planned" | sort) <(printf '%s\n' "$expected" | sort) | tr -d ' ')"

  if [[ -z "$missing" ]]; then
    pass "the documentation example includes every document under docs/"
  else
    fail "the documentation example is missing: ${missing//$'\n'/, }"
  fi

  if [[ -n "$planned" ]]; then
    pass "the documentation example plans at least one document"
  else
    fail "the documentation example plans nothing: the check above would pass vacuously"
  fi
}

run_emoji_showcase_example_test() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP emoji showcase contexts (pandoc not available)"
    return 0
  fi

  local out code context
  out="$(new_test_tmpfile)" || return
  set +e
  "${REAL_PYTHON3}" - "${ROOT_DIR}/examples/ohmyfake/chapters/06-a-fake-that-tells-the-truth.md" >"$out" 2>&1 <<'PY'
import json
import subprocess
import sys

parsed = subprocess.run(["pandoc", sys.argv[1], "-f", "markdown", "-t", "json"],
                        capture_output=True, text=True, check=True)
blocks = json.loads(parsed.stdout)["blocks"]
glyphs = {"\U0001f9ea", "\U0001f50d"}

def has_emoji(node):
    if isinstance(node, dict):
        if node.get("t") == "Str" and any(g in node["c"] for g in glyphs):
            return True
        return any(has_emoji(value) for value in node.values())
    return isinstance(node, list) and any(has_emoji(value) for value in node)

for name, kind in (("heading", "Header"), ("paragraph", "Para"),
                   ("list", "BulletList"), ("table", "Table")):
    present = any(block["t"] == kind and has_emoji(block) for block in blocks)
    print(f"{name}={'PASS' if present else 'FAIL'}")
PY
  code=$?
  set -e
  assert_exit_code "0" "$code" "the public emoji example parses through Pandoc"
  for context in heading paragraph list table; do
    assert_contains "$out" "^${context}=PASS$" "the public example shows emoji in a ${context}"
  done
  rm -f "$out"
}
