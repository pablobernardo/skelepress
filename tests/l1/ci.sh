#!/bin/bash
# CI dependency declarations; real package installation/rendering runs in L2/L3.

run_ci_render_dependencies_test() {
  local rule
  for rule in fonts svg existing template browser; do
    if python3 - "${ROOT_DIR}/.github/workflows/ci.yml" "$rule" <<'PY'
import re
import shlex
import sys
from pathlib import Path

workflow = Path(sys.argv[1]).read_text().replace("\\\n", " ")
previous = {
    "l2-render-integration": {"pandoc", "texlive-latex-base"},
    "l3-render-full": {"pandoc", "texlive-latex-base", "texlive-xetex", "nodejs", "npm"},
}
for job, old_packages in previous.items():
    block = re.search(r"^  " + job + r":\n(.*?)(?=^  [\w-]+:|\Z)", workflow, re.M | re.S)
    assert block, f"Missing integration job: {job}"
    commands = re.findall(r"^\s+sudo apt-get install -y (.+)$", block[1], re.M)
    packages = {package for command in commands for package in shlex.split(command)}
    rule = sys.argv[2]
    if rule == "browser":
        if job == "l3-render-full":
            assert "chromium-browser" not in packages, "Do not install Snap Chromium in L3"
            assert 'chrome_path="$(command -v google-chrome)"' in block[1]
            assert 'test -x "$chrome_path"' in block[1]
            assert 'test -r "$(npm root -g)/@mermaid-js/mermaid-cli/dist/index.html"' in block[1]
            assert 'PUPPETEER_EXECUTABLE_PATH="$chrome_path" bash tests/l3-local.sh' in block[1]
            assert "@mermaid-js/mermaid-cli@10.9.1" in block[1]
            assert "--no-sandbox" not in block[1]
        continue
    required = {
        "fonts": {"texlive-fonts-recommended"}, "svg": {"librsvg2-bin"},
        "existing": old_packages, "template": {"texlive-latex-extra"},
    }[rule]
    assert required <= packages, f"{job}: missing {sorted(required - packages)}"
    if rule == "template":
        assert "kpsewhich" in block[1] and "templates/default.tex" in block[1]
PY
    then
      pass "CI render dependencies: ${rule} in both L2 and L3"
    else
      fail "CI render dependencies: ${rule} in both L2 and L3"
    fi
  done
}

run_ci_full_gate_test() {
  if python3 - "${ROOT_DIR}/.github/workflows/ci.yml" <<'PY'
import re
import sys
from pathlib import Path

workflow = Path(sys.argv[1]).read_text()
inputs, jobs = workflow.split("jobs:\n", 1)
flag = re.search(r"^      run_full_gate_macos:\n(.*?)(?=^      [\w-]+:|\Z)", inputs, re.M | re.S)
assert flag, "Missing optional full-gate input"
assert "default: false" in flag[1] and "type: boolean" in flag[1]
job = re.search(r"^  full-gate-macos:\n(.*?)(?=^  [\w-]+:|\Z)", jobs, re.M | re.S)
assert job, "Missing disposable full-gate job"
block = job[1]
assert re.search(r"github.event_name == 'workflow_dispatch' &&\s+inputs.run_full_gate_macos == true", block)
assert "runs-on: macos-15" in block and "timeout-minutes: 20" in block
assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in block
assert "persist-credentials: false" in block
assert 'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"' in block
assert 'mktemp -d "${RUNNER_TEMP%/}/skelepress-gate.XXXXXXXX"' in block
for name in ("HOME", "TMPDIR", "XDG_CACHE_HOME", "NODE_COMPILE_CACHE"):
    assert f'export {name}="${{scratch}}/' in block, name
assert 'git -C "$TMPDIR" rev-parse --show-toplevel' in block
assert 'test "$discovery" -eq 128' in block
assert re.search(r"^\s+make gate$", block, re.M)
assert block.count('test -z "$(git status --porcelain)"') == 2
assert not re.search(r"\b(?:sudo|docker)\b|bootstrap\.sh", block)
provision = block.index("HOMEBREW_NO_AUTO_UPDATE=1 brew install pandoc")
gate = block.index("\n          make gate\n")
for required in ("command -v pandoc", "pandoc --version"):
    assert provision < block.index(required) < gate, required
PY
  then
    pass "manual full gate uses a disposable Git-backed macOS VM without changing defaults"
  else
    fail "manual full gate must preserve native allocation inside a disposable Git-backed macOS VM"
  fi
}
