#!/bin/bash
# The --formats CLI override: one flag selects the rendered formats without
# editing the configuration. Sourced by tests/run.sh (not run standalone).

# Shared fixture: one chapter project with a worker config.
html_formats_fixture() {
  local root="$1"
  mkdir -p "$root/chapters"
  printf '# One\n\nHello.\n' >"$root/chapters/one.md"
  cat >"$root/skelepress.config.yaml" <<'EOF'
version: 1
project: {name: formats-override, base_dir: .}
document: {title: Override}
input: {chapters_dir: chapters, glob: "*.md", order: natural, explicit_files: []}
output: {dir: out, suffix: t, keep_merged_markdown: false, formats: [pdf, epub]}
pandoc: {pdf_engine: xelatex, toc: false, toc_depth: 2, number_sections: false, resource_path: [chapters]}
filters: {emoji: {enabled: false}, mermaid: {enabled: false}, extra_lua_filters: []}
runtime: {required_commands: [], strict: false}
EOF
}

run_render_formats_override_test() {
  local root out code

  # The override wins over the config for the plan shape.
  root="$(mktemp -d)"
  html_formats_fixture "$root"
  out="$(mktemp)"
  code=0
  "$CLI" render -c "$root/skelepress.config.yaml" --formats html --dry-run --json >"$out" 2>"$out.err" || code=$?
  if [[ "${code:-0}" == "0" ]] && grep -q '"html"' "$out" \
    && ! grep -q '"epub"' "$out" && ! grep -q '"pdf"' "$out"; then
    pass "--formats html names pdf-config but plans only an html job"
  else
    fail "--formats html should plan only html for a pdf+html config (exit ${code:-?})"
    tail -5 "$out" "$out.err"
  fi
  # Dedup + metadata, not files: no output directory exists after a dry run.
  [[ -d "$root/out" ]] && fail "--formats dry run must not create output"
  rm -rf "$root" "$out" "$out.err"

  # The -f alias behaves exactly like the long form.
  root="$(mktemp -d)"
  html_formats_fixture "$root"
  out="$(mktemp)"
  "$CLI" render -c "$root/skelepress.config.yaml" -f html --dry-run --json >"$out" 2>/dev/null
  if grep -q '"html"' "$out" && ! grep -q '"epub"' "$out" && ! grep -q '"pdf"' "$out"; then
    pass "-f html aliases --formats for the plan"
  else
    fail "-f html should plan only html exactly like --formats"
    tail -5 "$out"
  fi
  rm -rf "$root" "$out"

  # Multiple comma-separated formats keep the declared order.
  root="$(mktemp -d)"
  html_formats_fixture "$root"
  out="$(mktemp)"
  "$CLI" render -c "$root/skelepress.config.yaml" --formats epub,html --dry-run --json >"$out" 2>/dev/null
  if grep -q '"plan_version": 2' "$out" && [[ "$(python3 - "$out" <<'PY'
import json, sys
plan = json.load(open(sys.argv[1]))
print(",".join(next(k for k in j["pandoc"]["target"] if k != "markdown") for j in plan["jobs"]))
PY
)" == "epub,html" ]]; then
    pass "--formats epub,html plans those two jobs in that order"
  else
    fail "--formats epub,html should plan exactly epub then html"
    tail -5 "$out"
  fi
  rm -rf "$root" "$out"

  # An invalid value fails with the format message and plans nothing.
  root="$(mktemp -d)"
  html_formats_fixture "$root"
  out="$(mktemp)"
  code=0
  "$CLI" render -c "$root/skelepress.config.yaml" --formats mobi --dry-run >"$out" 2>"$out.err" || code=$?
  if [[ "$code" != "0" ]] && grep -q "Supported values" "$out" "$out.err"; then
    pass "--formats mobi is rejected naming the supported values"
  else
    fail "--formats mobi should fail with the supported-values message (exit $code)"
    tail -5 "$out" "$out.err"
  fi
  rm -rf "$root" "$out" "$out.err"

  # doctor honours the override: a needed pdf engine is not required for html.
  root="$(mktemp -d)"
  html_formats_fixture "$root"
  sed -i.bak 's/pdf_engine: xelatex/pdf_engine: missing-test-engine/' "$root/skelepress.config.yaml"
  out="$(mktemp)"
  code=0
  "$CLI" doctor -c "$root/skelepress.config.yaml" --formats html >"$out" 2>&1 || code=$?
  if [[ "$code" == "0" ]]; then
    pass "doctor --formats html skips the pdf engine the config declares"
  else
    fail "doctor --formats html should not require the config's pdf engine"
    tail -5 "$out"
  fi
  code=0
  "$CLI" doctor -c "$root/skelepress.config.yaml" >"$out" 2>&1 || code=$?
  if [[ "$code" != "0" ]] && grep -q "missing-test-engine" "$out"; then
    pass "doctor without override still requires the config's pdf engine"
  else
    fail "doctor without --formats must keep requiring the declared pdf engine"
    tail -5 "$out"
  fi
  rm -rf "$root" "$out"

  # A real html render through the override produces the artifact.
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP --formats html real render (pandoc not available)"
    rm -rf "$root" "$out"
    return 0
  fi
  root="$(mktemp -d)"
  html_formats_fixture "$root"
  out="$(mktemp)"
  if "$CLI" render -c "$root/skelepress.config.yaml" --formats html >"$out" 2>&1 \
    && [[ -f "$root/out/override-t.html" ]]; then
    grep -q "skelepress reader" "$root/out/override-t.html" \
      && pass "--formats html renders the real reader artifact" \
      || fail "--formats html artifact should carry the reader shell"
  else
    fail "--formats html should render the artifact through the public CLI"
    tail -10 "$out"
  fi
  rm -rf "$root" "$out"
}
