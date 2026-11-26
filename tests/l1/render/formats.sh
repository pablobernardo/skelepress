#!/bin/bash
# Several output formats from one configuration.
# Sourced by tests/run.sh (not run standalone).

run_multi_format_export_test() {
  local out code=0
  out="$(mktemp)"
  "${REAL_PYTHON3}" "${ROOT_DIR}/tests/integration/check-multi-format.py" >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "public multi-format selection, ordering and partial failure checks"
  if [[ "$code" != "0" ]]; then
    tail -60 "$out"
  fi
  rm -f "$out"
}

run_html_format_test() {
  local out code=0
  out="$(mktemp)"
  "${REAL_PYTHON3}" "${ROOT_DIR}/tests/integration/check-html-format.py" >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "html format plan shape and real reader artifact checks"
  if [[ "$code" != "0" ]]; then
    tail -80 "$out"
  fi
  rm -f "$out"
}

run_webp_html_conversion_test() {
  local out code=0
  out="$(mktemp)"
  "${REAL_PYTHON3}" "${ROOT_DIR}/tests/integration/check-webp-html.py" >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "opt-in webp html conversion: plan shape, artifact, degradation and doctor"
  if [[ "$code" != "0" ]]; then
    tail -80 "$out"
  fi
  rm -f "$out"
}
