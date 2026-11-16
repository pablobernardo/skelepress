#!/bin/bash
# draft area tests. Sourced by tests/run.sh (not run standalone).
# Local CLI behavior only: argument handling, config synthesis and naming.
# Actual PDF generation runs in disposable hosted VMs, never in unit tests.

run_draft_requires_at_least_one_file_test() {
  local out
  out="$(mktemp)"
  if /bin/bash "$CLI" draft >"$out" 2>&1; then
    fail "draft without files should fail"
  else
    pass "draft without files fails with usage error"
  fi
  local expected="draft requires at least one Markdown file."
  if grep -qF "$expected" "$out"; then
    pass "draft empty-input error message is exact"
  else
    fail "draft empty-input error message mismatch"
  fi
  rm -f "$out"
}

run_draft_rejects_missing_file_test() {
  local out tmp
  out="$(mktemp)"
  tmp="$(mktemp -d)"
  if /bin/bash "$CLI" draft "$tmp/does-not-exist.md" >"$out" 2>&1; then
    fail "draft with a missing file should fail"
  else
    pass "draft with missing file fails"
  fi
  local expected="File not found:"
  if grep -qF "$expected" "$out"; then
    pass "draft missing-file error message is prefixed"
  else
    fail "draft missing-file error message mismatch"
  fi
  rm -rf "$out" "$tmp"
}

run_draft_rejects_repeated_options_test() {
  local out tmp
  out="$(mktemp)"
  tmp="$(mktemp -d)"
  if /bin/bash "$CLI" draft -t "One" -t "Two" "$tmp/a.md" >"$out" 2>&1; then
    fail "repeated -t should fail"
  else
    pass "repeated -t rejected"
  fi
  local expected="Repeated option:"
  if grep -qF "$expected" "$out"; then
    pass "repeated option error is exact"
  else
    fail "repeated option error mismatch"
  fi
  rm -rf "$out" "$tmp"
}

run_draft_rejects_unknown_option_test() {
  local out
  out="$(mktemp)"
  if /bin/bash "$CLI" draft --bogus x.md >"$out" 2>&1; then
    fail "unknown option should fail"
  else
    pass "unknown option rejected"
  fi
  rm -f "$out"
}

run_draft_synthesized_config_shape_test() {
  # Inspect the synthesized config through a non-rendering debug hook so the
  # test never needs pandoc or a TeX engine locally.
  local out tmp
  out="$(mktemp)"
  tmp="$(mktemp -d)"
  printf '# Hello\n' >"$tmp/a.md"
  printf '# World\n' >"$tmp/b.md"
  if ! SKELEPRESS_DEBUG_DRAFT_CONFIG=1 /bin/bash "$CLI" draft -t "My Draft" "$tmp/a.md" "$tmp/b.md" >"$out" 2>&1; then
    fail "draft config debug hook should succeed"
    rm -rf "$out" "$tmp"
    return 0
  fi
  assert_contains "$out" 'toc: false' "synthesized config disables TOC"
  assert_contains "$out" 'titlepage: false' "synthesized config disables titlepage"
  assert_contains "$out" 'title: "My Draft"' "synthesized config carries -t title"
  if grep -qE -- 'formats: \[pdf\]' "$out"; then
    pass "synthesized config requests pdf only"
  else
    fail "synthesized config requests pdf only"
  fi
  if grep -q '"epub"' "$out"; then
    fail "synthesized config must not request epub"
  else
    pass "synthesized config is pdf-only"
  fi
  rm -rf "$out" "$tmp"
}
