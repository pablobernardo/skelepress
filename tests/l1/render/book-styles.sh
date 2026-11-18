#!/bin/bash
# Check built-in style selection through the public validator and render plan.

run_book_styles_selection_test() {
  local sandbox cfg style code out err
  local styles=(book book-novel book-manual book-kdp-5x8)
  sandbox="$(new_contract_sandbox)"
  cfg="${sandbox}/skelepress.config.yaml"
  out="$(new_test_tmpfile)"
  err="$(new_test_tmpfile)"
  printf '# Chapter One\n\nSample text.\n' >"${sandbox}/work/chapters/01-one.md"

  for style in "${styles[@]}"; do
    cp "${ROOT_DIR}/templates/${style}.tex" "${sandbox}/templates/${style}.tex"
    write_contract_config "$cfg" natural true "" true
    "${REAL_PYTHON3}" - "$cfg" "$style" <<'PY'
import sys
from pathlib import Path

path, style = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
path.write_text(text.replace("  resource_path:", f"  template: {style}\n  resource_path:", 1), encoding="utf-8")
PY
    code=0
    "${sandbox}/bin/skelepress" validate-config -c "$cfg" >"$out" 2>"$err" || code=$?
    assert_exit_code "0" "$code" "$style validates as a shipped style name"
    if [[ "$(<"$out")" == '✅ Config valid' ]]; then
      pass "$style validation reports a valid configuration"
    else
      fail "$style validation did not report a valid configuration"
    fi
    if [[ -s "$err" ]]; then
      fail "$style validation writes unexpected stderr"
    else
      pass "$style validation leaves stderr empty"
    fi

    code=0
    "${sandbox}/bin/skelepress" render --dry-run --json -c "$cfg" >"$out" 2>"$err" || code=$?
    assert_exit_code "0" "$code" "$style plans a render"
    if [[ "$code" -eq 0 ]] && "${REAL_PYTHON3}" - "$out" "${sandbox}/templates/${style}.tex" <<'PY'
import json
import sys
from pathlib import Path

with Path(sys.argv[1]).open(encoding="utf-8") as stream:
    argv = json.load(stream)["pandoc"]["argv"]
expected = f"--template={Path(sys.argv[2]).resolve()}"
assert expected in argv, argv
PY
    then
      pass "$style selects the matching shipped template"
    else
      fail "$style does not select the matching shipped template"
    fi
    if [[ "$(<"$err")" == '✅ Config valid' ]]; then
      pass "$style plan writes only preflight success to stderr"
    else
      fail "$style plan stderr differs from preflight success"
    fi
  done

  rm -rf "$sandbox"
  rm -f "$out" "$err"
}
