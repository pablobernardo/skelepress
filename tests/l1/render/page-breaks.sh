#!/bin/bash
# Page breaks at heading boundaries (issue #194):
# compat.clearpage_between_heading_level and the {.page-break} heading class.
# Sourced by tests/run.sh (not run standalone).

# Contract config with a variable compat section and optional output formats.
# Arguments: path, heading level ("" omits the key), legacy flag, formats ("" = pdf default).
write_page_break_config() {
  local path="$1"
  local level="$2"
  local legacy="$3"
  local formats="$4"
  {
    cat <<EOF
version: 1

project:
  name: pb-contract
  base_dir: ./work

document:
  title: "PB Document"

input:
  chapters_dir: "chapters"
  glob: "*.md"
  order: natural
  explicit_files: []

output:
EOF
    if [[ -n "$formats" ]]; then
      printf '  formats: [%s]\n' "$formats"
    fi
    cat <<EOF
  dir: "out"
  file_prefix: "pb"
  suffix: "manual"
  keep_merged_markdown: true

pandoc:
  pdf_engine: lualatex
  toc: false
  toc_depth: 2
  number_sections: false
  metadata_file: ""
  resource_path:
    - "chapters"

filters:
  emoji:
    enabled: true
    emoji_dir: "out/emoji"
    include_ballot_icons: true
  mermaid:
    enabled: false
    output_dir: "out/mermaid"
    background: "transparent"
  extra_lua_filters: []

runtime:
  required_commands:
    - pandoc
  strict: true

compat:
  legacy_clearpage_between_h1: ${legacy}
EOF
    if [[ -n "$level" ]]; then
      printf '  clearpage_between_heading_level: %s\n' "$level"
    fi
  } >"$path"
}

# Line number of the last \clearpage before the given line (0 when none precedes it).
last_clearpage_before() {
  local file="$1"
  local heading_line="$2"
  awk -v h="$heading_line" 'NR < h && /^\\clearpage$/ { last = NR } END { print last + 0 }' "$file"
}

clearpage_count() {
  grep -c '^\\clearpage$' "$1" || true
}

run_render_heading_page_break_level_test() {
  local sandbox tmpbin capture out merged
  sandbox="$(new_contract_sandbox)"
  tmpbin="$(mktemp -d)"
  write_pandoc_capture_mock "$tmpbin"
  capture="$(mktemp)"
  out="$(mktemp)"
  merged="${sandbox}/work/out/pb-manual.md"

  printf '# Chapter A\n\ntext a\n' >"${sandbox}/work/chapters/01-a.md"
  printf '## Chapter B\n\ntext b\n' >"${sandbox}/work/chapters/02-b.md"
  printf '## Chapter C\n\ntext c\n' >"${sandbox}/work/chapters/03-c.md"
  printf '### Chapter D\n\ntext d\n' >"${sandbox}/work/chapters/04-d.md"

  # Level 2: chapters whose first non-empty heading is level 2 or shallower
  # start a page; level 3 runs on. LaTeX stays out of the sources: the merge
  # inserts the break exactly like the legacy H1 behavior does.
  write_page_break_config "${sandbox}/skelepress.config.yaml" 2 false ""
  if TMP_PANDOC_CAPTURE="$capture" PATH="${tmpbin}:$PATH" "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml" >"$out" 2>&1; then
    pass "render accepts compat.clearpage_between_heading_level"
  else
    fail "render should accept compat.clearpage_between_heading_level ($(tail -2 "$out"))"
  fi

  local line_b line_c line_d
  line_b="$(line_of_match "$merged" '^## Chapter B')"
  line_c="$(line_of_match "$merged" '^## Chapter C')"
  line_d="$(line_of_match "$merged" '^### Chapter D')"

  local break_b break_c break_d break_a
  break_b="$(last_clearpage_before "$merged" "$line_b")"
  break_c="$(last_clearpage_before "$merged" "$line_c")"
  break_d="$(last_clearpage_before "$merged" "$line_d")"
  break_a="$(last_clearpage_before "$merged" "$(line_of_match "$merged" '^# Chapter A')")"

  if [[ "$break_b" -gt 0 && "$((line_b - break_b))" -eq 3 ]]; then
    pass "level 2 breaks the page before a chapter starting at ##"
  else
    fail "level 2 must break the page before Chapter B (break=${break_b}, heading=${line_b})"
  fi
  if [[ "$break_c" -gt 0 && "$((line_c - break_c))" -eq 3 ]]; then
    pass "level 2 breaks the page before a second chapter starting at ##"
  else
    fail "level 2 must break the page before Chapter C (break=${break_c}, heading=${line_c})"
  fi
  if [[ "$break_d" -eq "$break_c" ]]; then
    pass "a deeper chapter does not break the page"
  else
    fail "Chapter D starts at ### and must not get its own page"
  fi
  if [[ "$break_a" -eq 0 ]]; then
    pass "the first chapter never starts with a page break"
  else
    fail "the first chapter must not start with a page break"
  fi

  # The same merged markdown drives every format, so a PDF-only break must
  # never leak into EPUB, whatever the compat section says.
  write_page_break_config "${sandbox}/skelepress.config.yaml" 2 true "epub"
  rm -f "$merged"
  if TMP_PANDOC_CAPTURE="$capture" PATH="${tmpbin}:$PATH" "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml" >"$out" 2>&1; then
    pass "render accepts an epub-only run with heading breaks"
  else
    fail "render should accept an epub-only run ($(tail -2 "$out"))"
  fi
  assert_not_contains "$merged" '^\\clearpage$' "an EPUB merged markdown never carries LaTeX page breaks"

  # Defaults are byte-compatible: without the new key, behavior matches the
  # legacy flag alone, and explicit level 1 is the same contract.
  printf '# Chapter A\n\ntext a\n' >"${sandbox}/work/chapters/01-a.md"
  printf '# Chapter B\n\ntext b\n' >"${sandbox}/work/chapters/02-b.md"
  printf '# Chapter C\n\ntext c\n' >"${sandbox}/work/chapters/03-c.md"
  write_page_break_config "${sandbox}/skelepress.config.yaml" "" true ""
  rm -f "$merged"
  if TMP_PANDOC_CAPTURE="$capture" PATH="${tmpbin}:$PATH" "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml" >"$out" 2>&1; then
    pass "render accepts the default compat section"
  else
    fail "render should accept the default compat section ($(tail -2 "$out"))"
  fi
  local default_count
  default_count="$(clearpage_count "$merged")"
  if [[ "$default_count" -eq 2 ]]; then
    pass "the legacy flag alone keeps breaking pages between H1 chapters"
  else
    fail "the default compat section must keep exactly the legacy H1 breaks (count=${default_count})"
  fi

  write_page_break_config "${sandbox}/skelepress.config.yaml" 1 true ""
  rm -f "$merged"
  if TMP_PANDOC_CAPTURE="$capture" PATH="${tmpbin}:$PATH" "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml" >"$out" 2>&1; then
    pass "render accepts explicit level 1"
  else
    fail "render should accept explicit level 1 ($(tail -2 "$out"))"
  fi
  if [[ "$(clearpage_count "$merged")" -eq "$default_count" ]]; then
    pass "explicit level 1 matches the default H1 behavior"
  else
    fail "explicit level 1 must match the default H1 behavior"
  fi

  rm -rf "$sandbox" "$tmpbin"
  rm -f "$capture" "$out"
}

run_render_heading_page_break_plan_test() {
  if [[ -z "${REAL_PYTHON3}" ]]; then
    echo "SKIP heading page-break plan (python3 not available)"
    return 0
  fi

  local sandbox tmpbin capture plan out code
  sandbox="$(new_contract_sandbox)"
  tmpbin="$(mktemp -d)"
  write_pandoc_capture_mock "$tmpbin"
  capture="$(mktemp)"
  plan="$(mktemp)"
  out="$(mktemp)"

  printf '# Chapter A\n\ntext a\n' >"${sandbox}/work/chapters/01-a.md"
  write_page_break_config "${sandbox}/skelepress.config.yaml" 2 false ""

  set +e
  TMP_PANDOC_CAPTURE="$capture" PATH="${tmpbin}:$PATH" "${sandbox}/bin/skelepress" render \
    -c "${sandbox}/skelepress.config.yaml" --dry-run --json >"$plan" 2>"$out"
  code=$?
  set -e
  assert_exit_code "0" "$code" "render --dry-run --json exits 0 with heading breaks"
  assert_json_expr "$plan" 'd["side_effects"]["heading_break_level"] == 2' "plan declares the heading break level"
  assert_json_expr "$plan" 'd["side_effects"]["clearpage_between_h1"] is True' "plan reports the effective breaking decision"
  assert_json_expr "$plan" 'any("heading-page-break.lua" in a for a in d["pandoc"]["argv"])' "plan passes the heading page-break filter"

  write_page_break_config "${sandbox}/skelepress.config.yaml" "" true ""
  rm -f "$plan" "$out"
  set +e
  TMP_PANDOC_CAPTURE="$capture" PATH="${tmpbin}:$PATH" "${sandbox}/bin/skelepress" render \
    -c "${sandbox}/skelepress.config.yaml" --dry-run --json >"$plan" 2>"$out"
  code=$?
  set -e
  assert_exit_code "0" "$code" "render --dry-run --json exits 0 with defaults"
  assert_json_expr "$plan" 'd["side_effects"]["heading_break_level"] == 1' "plan defaults the heading break level to 1"
  assert_json_expr "$plan" 'd["side_effects"]["clearpage_between_h1"] is True' "plan keeps the legacy key true by default"

  rm -rf "$sandbox" "$tmpbin"
  rm -f "$capture" "$plan" "$out"
}

run_heading_page_break_filter_test() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP heading page-break filter (pandoc not available)"
    return 0
  fi

  local md tex html
  md="$(mktemp)"
  tex="$(mktemp)"
  html="$(mktemp)"
  printf '# Opening\n\nIntro.\n\n# Marked {.page-break}\n\nBody.\n' >"$md"

  if pandoc "$md" -t latex --lua-filter="${ROOT_DIR}/filters/heading-page-break.lua" >"$tex" 2>&1; then
    pass "heading page-break filter produces latex output"
  else
    fail "heading page-break filter should produce latex output ($(tail -2 "$tex"))"
  fi

  local marked plain
  marked="$(line_of_match "$tex" '^\\section\{Marked\}')"
  plain="$(line_of_match "$tex" '^\\section\{Opening\}')"
  if [[ "$marked" -gt 0 ]]; then
    local before_marked
    before_marked="$(last_clearpage_before "$tex" "$marked")"
    if [[ "$before_marked" -gt 0 && "$before_marked" -lt "$marked" ]]; then
      pass "a marked heading gets \\clearpage right before it"
    else
      fail "a marked heading must get \\clearpage right before it"
    fi
  else
    fail "a marked heading must survive as a section in LaTeX output"
  fi
  assert_not_contains "$tex" 'page-break' "the marker class never reaches LaTeX"
  if [[ "$plain" -gt 0 && "$(last_clearpage_before "$tex" "$plain")" -eq 0 ]]; then
    pass "an unmarked heading stays where it is"
  else
    fail "an unmarked heading must not get a page break"
  fi
  if pandoc "$md" -t html --lua-filter="${ROOT_DIR}/filters/heading-page-break.lua" >"$html" 2>&1; then
    pass "heading page-break filter produces html output"
  else
    fail "heading page-break filter should produce html output ($(tail -2 "$html"))"
  fi
  assert_contains "$html" 'class="page-break"' "html and EPUB keep the class as a CSS hook"
  assert_not_contains "$html" 'clearpage' "html output never carries LaTeX commands"

  rm -f "$md" "$tex" "$html"
}

run_heading_page_break_validate_test() {
  local out_tmp
  out_tmp="$(mktemp)"

  # A level inside 1..6 validates alongside the legacy flag.
  sed 's/^  legacy_clearpage_between_h1: true$/  legacy_clearpage_between_h1: true\n  clearpage_between_heading_level: 3/' \
    "${FIXTURES_DIR}/valid.config.yaml" >"${FIXTURES_DIR}/valid-heading-page-break.config.yaml"
  if "$CLI" validate-config -c "${FIXTURES_DIR}/valid-heading-page-break.config.yaml" >"$out_tmp" 2>&1; then
    pass "validate-config accepts clearpage_between_heading_level"
  else
    fail "validate-config should accept clearpage_between_heading_level ($(tail -2 "$out_tmp"))"
  fi

  local invalid
  for invalid in 0 7; do
    sed "s/^  legacy_clearpage_between_h1: true$/  legacy_clearpage_between_h1: true\n  clearpage_between_heading_level: ${invalid}/" \
      "${FIXTURES_DIR}/valid.config.yaml" >"${FIXTURES_DIR}/invalid-heading-page-break-${invalid}.config.yaml"
    set +e
    "$CLI" validate-config -c "${FIXTURES_DIR}/invalid-heading-page-break-${invalid}.config.yaml" >"$out_tmp" 2>&1
    local code=$?
    set -e
    assert_exit_code "1" "$code" "validate-config rejects heading level ${invalid}"
    assert_contains "$out_tmp" "clearpage_between_heading_level" "validate-config names the offending key for level ${invalid}"
  done

  rm -f "${FIXTURES_DIR}/valid-heading-page-break.config.yaml"
  rm -f "${FIXTURES_DIR}/invalid-heading-page-break-0.config.yaml"
  rm -f "${FIXTURES_DIR}/invalid-heading-page-break-7.config.yaml"
  rm -f "$out_tmp"
}
