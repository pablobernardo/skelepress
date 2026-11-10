#!/bin/bash
# Links between selected chapters become internal anchors.
# Sourced by tests/run.sh (not run standalone).

run_section_link_fragment_tests() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP section link fragments (pandoc not available)"
    return 0
  fi

  local sandbox out result message code=0
  sandbox="$(new_epub_sandbox)"
  out="${sandbox}/render.log"
  cp "${FIXTURES_DIR}/chapter-section-links/"*.md "${sandbox}/work/chapters/"
  write_epub_config "${sandbox}/skelepress.config.yaml" epub "Section Link Guide" en true
  "${REAL_PYTHON3}" - "${sandbox}/skelepress.config.yaml" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
path.write_text(path.read_text().replace('explicit_files: []',
    'explicit_files: [chapter-1.md, chapter-2.md, migration.md]'))
PY
  "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml" >"$out" 2>"${sandbox}/stderr" || code=$?
  assert_exit_code "0" "$code" "public render accepts cross-chapter section links"
  assert_not_contains "$out" 'section unavailable' "missing-section annotation does not add CLI diagnostics"
  if [[ ! -s "${sandbox}/stderr" ]]; then
    pass "section-link render leaves stderr empty"
  else
    fail "section-link render unexpectedly writes stderr"
  fi
  if "${REAL_PYTHON3}" "${FIXTURES_DIR}/chapter-section-links/check-epub.py" \
    "${sandbox}/work/out/epub-guide-manual.epub" >"${sandbox}/checks"; then
    while IFS=$'\t' read -r result message; do
      if [[ "$result" == "0" ]]; then pass "$message"; else fail "$message"; fi
    done <"${sandbox}/checks"
  else
    fail "section link EPUB checker failed"
  fi
  # A missing-section annotation inside a heading changes its canonical ID.
  # This must invalidate the map, not leave links pointing at stale IDs.
  printf '\n## [heading-link](migration.md#not-a-heading)\n' >>"${sandbox}/work/chapters/chapter-1.md"
  code=0
  "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml" >"$out" 2>"${sandbox}/stderr" || code=$?
  assert_exit_code "0" "$code" "public render handles a heading-map mismatch visibly"
  if "${REAL_PYTHON3}" "${FIXTURES_DIR}/chapter-section-links/check-epub.py" \
    "${sandbox}/work/out/epub-guide-manual.epub" --heading-mismatch >"${sandbox}/checks"; then
    while IFS=$'\t' read -r result message; do
      if [[ "$result" == "0" ]]; then pass "$message"; else fail "$message"; fi
    done <"${sandbox}/checks"
  else
    fail "heading-map mismatch EPUB checker failed"
  fi
  rm -rf "$sandbox"
}

# Default-off: a hosted VM supplies TeX and pypdf; never render PDF on shared hosts.
run_section_link_pdf_destination_test() {
  if [[ "${SKELEPRESS_SECTION_LINK_PDF:-0}" != "1" ]] || \
    ! command -v pandoc >/dev/null 2>&1 || ! command -v xelatex >/dev/null 2>&1 || \
    ! "${REAL_PYTHON3}" -c 'import pypdf' >/dev/null 2>&1; then
    echo "SKIP section link PDF destination (opt-in hosted Pandoc/XeLaTeX/pypdf required)"
    return 0
  fi
  local sandbox code=0
  sandbox="$(new_epub_sandbox)"
  cp "${FIXTURES_DIR}/chapter-section-links/pdf/"*.md "${sandbox}/work/chapters/"
  cp "${FIXTURES_DIR}/chapter-section-links/pdf/default.tex" "${sandbox}/templates/default.tex"
  write_epub_config "${sandbox}/skelepress.config.yaml" pdf "Section Link Guide" en true
  "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml" >"${sandbox}/render.log" 2>&1 || code=$?
  assert_exit_code "0" "$code" "hosted public PDF section-link render succeeds"
  code=0
  "${REAL_PYTHON3}" "${FIXTURES_DIR}/chapter-section-links/check-pdf.py" \
    "${sandbox}/work/out/epub-guide-manual.pdf" "${sandbox}/destinations.json" || code=$?
  assert_exit_code "0" "$code" "PDF annotations resolve to the section, not the chapter start"
  if [[ -n "${SKELEPRESS_SECTION_LINK_EVIDENCE:-}" ]]; then
    mkdir -p "$SKELEPRESS_SECTION_LINK_EVIDENCE"
    cp "${sandbox}/work/out/epub-guide-manual.pdf" "${sandbox}/destinations.json" \
      "${sandbox}/render.log" "$SKELEPRESS_SECTION_LINK_EVIDENCE/"
  fi
  rm -rf "$sandbox"
}

run_chapter_link_rewrite_test() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP chapter links (pandoc not available)"
    return 0
  fi

  local sandbox out epub md ch1 code=0
  sandbox="$(new_epub_sandbox)"
  out="$(mktemp)"
  epub="${sandbox}/work/out/epub-guide-manual.epub"
  md="${sandbox}/work/out/epub-guide-manual.md"
  ch1="${sandbox}/ch1.xhtml"

  printf '# First Chapter\n\nSee [the second chapter](chapter-2.md).\n' >"${sandbox}/work/chapters/chapter-1.md"
  printf '# Second Chapter\n\nText only.\n' >"${sandbox}/work/chapters/chapter-2.md"
  write_epub_config "${sandbox}/skelepress.config.yaml" epub "EPUB Sandbox Guide" es true

  (
    cd "${sandbox}/work" && "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml"
  ) >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "EPUB renders with a link to a sibling chapter"
  assert_contains "$md" '\]\(#ch-chapter-2\)' "a sibling chapter link becomes an in-document anchor"
  assert_contains "$md" '\[\]\{#ch-chapter-2\}' "the target chapter carries the matching anchor"

  unzip -p "$epub" EPUB/text/ch001.xhtml >"$ch1" 2>/dev/null
  assert_not_contains "$ch1" 'chapter-2\.md' "no dead link to a chapter file survives in the EPUB"
  assert_contains "$ch1" 'ch002\.xhtml#ch-chapter-2|href="#ch-chapter-2"' "the link resolves inside the publication"

  rm -rf "$sandbox"
  rm -f "$out"

  # A project with no sibling links must stay byte-identical: no anchors, no rewrites.
  local plain_md
  sandbox="$(new_epub_sandbox)"
  out="$(mktemp)"
  plain_md="${sandbox}/work/out/epub-guide-manual.md"
  printf '# First Chapter\n\nPlain text.\n' >"${sandbox}/work/chapters/chapter-1.md"
  printf '# Second Chapter\n\nText only.\n' >"${sandbox}/work/chapters/chapter-2.md"
  write_epub_config "${sandbox}/skelepress.config.yaml" epub "EPUB Sandbox Guide" es true
  code=0
  (
    cd "${sandbox}/work" && "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml"
  ) >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "EPUB renders without sibling links"
  assert_not_contains "$plain_md" '\[\]\{#' "a project without sibling links gets no injected anchors"

  rm -rf "$sandbox"
  rm -f "$out"
}
