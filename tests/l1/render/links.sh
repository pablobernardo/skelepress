#!/bin/bash
# Links between selected chapters become internal anchors.
# Sourced by tests/run.sh (not run standalone).

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

# A cross-chapter link with a fragment must land on the target section (issue
# #111), not on the chapter start. The target heading carries an explicit id
# derived from the file and the heading, and the fragment-less sibling link of
# the same chapter keeps its chapter-wide anchor.
run_chapter_fragment_link_test() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP chapter fragment links (pandoc not available)"
    return 0
  fi

  local sandbox out epub md ch1 ch2 code=0
  sandbox="$(new_epub_sandbox)"
  out="$(mktemp)"
  epub="${sandbox}/work/out/epub-guide-manual.epub"
  md="${sandbox}/work/out/epub-guide-manual.md"
  ch1="${sandbox}/ch1.xhtml"
  ch2="${sandbox}/ch2.xhtml"

  printf '# First Chapter\n\nDetails: [Section A](chapter-2.md#section-a).\nAlso [the second chapter](chapter-2.md).\n' >"${sandbox}/work/chapters/chapter-1.md"
  printf '# Second Chapter\n\nIntro.\n\n## Section A\n\nBody.\n' >"${sandbox}/work/chapters/chapter-2.md"
  write_epub_config "${sandbox}/skelepress.config.yaml" epub "EPUB Sandbox Guide" es true

  (
    cd "${sandbox}/work" && "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml"
  ) >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "EPUB renders with a fragment link to a sibling section"
  assert_contains "$md" '\]\(#ch-chapter-2-section-a\)' "a fragment link points at an explicit id derived from file and heading"
  assert_contains "$md" '## Section A \{#ch-chapter-2-section-a\}' "the target heading carries the matching explicit id"
  assert_contains "$md" '\]\(#ch-chapter-2\)' "the fragment-less sibling link keeps its chapter-wide anchor"
  assert_contains "$md" '\[\]\{#ch-chapter-2\}' "the target chapter still carries its chapter-wide anchor"

  unzip -p "$epub" EPUB/text/ch001.xhtml >"$ch1" 2>/dev/null
  unzip -p "$epub" EPUB/text/ch002.xhtml >"$ch2" 2>/dev/null
  assert_not_contains "$ch1" 'chapter-2\.md' "no dead link to a chapter file survives in the EPUB"
  assert_contains "$ch1" 'ch002\.xhtml#ch-chapter-2-section-a|href="#ch-chapter-2-section-a"' "the fragment link resolves to the section inside the publication"
  assert_contains "$ch2" 'id="ch-chapter-2-section-a"' "the target section exists in the EPUB with the explicit id"

  rm -rf "$sandbox"
  rm -f "$out"
}

# A fragment naming no existing heading degrades visibly, not silently: the
# link falls back to the chapter anchor and the reader sees a localized note.
run_chapter_fragment_missing_heading_test() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP missing fragment degradation (pandoc not available)"
    return 0
  fi

  local sandbox out epub md ch1 code=0
  sandbox="$(new_epub_sandbox)"
  out="$(mktemp)"
  epub="${sandbox}/work/out/epub-guide-manual.epub"
  md="${sandbox}/work/out/epub-guide-manual.md"
  ch1="${sandbox}/ch1.xhtml"

  printf '# First Chapter\n\nDetails: [Section A](chapter-2.md#does-not-exist).\n' >"${sandbox}/work/chapters/chapter-1.md"
  printf '# Second Chapter\n\nIntro.\n\n## Section A\n\nBody.\n' >"${sandbox}/work/chapters/chapter-2.md"
  write_epub_config "${sandbox}/skelepress.config.yaml" epub "EPUB Sandbox Guide" es true

  (
    cd "${sandbox}/work" && "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml"
  ) >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "an unmatched fragment degrades instead of failing the render"
  assert_contains "$md" '\]\(#ch-chapter-2\)' "an unmatched fragment falls back to the chapter anchor"
  assert_contains "$md" 'sección no encontrada' "the unmatched fragment carries a visible localized note"
  assert_not_contains "$md" '\{#ch-chapter-2-section-a' "no explicit id is invented for a fragment that names no heading"

  unzip -p "$epub" EPUB/text/ch001.xhtml >"$ch1" 2>/dev/null
  assert_contains "$ch1" 'sección no encontrada' "the visible note reaches the publication"

  rm -rf "$sandbox"
  rm -f "$out"
}

# Repeated headings in the target chapter must not emit duplicate explicit ids:
# the first occurrence keeps the derived id and later ones get a suffix.
run_chapter_fragment_duplicate_heading_test() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP duplicate fragment targets (pandoc not available)"
    return 0
  fi

  local sandbox out md code=0
  sandbox="$(new_epub_sandbox)"
  out="$(mktemp)"
  md="${sandbox}/work/out/epub-guide-manual.md"

  printf '# First Chapter\n\nDetails: [Section A](chapter-2.md#section-a).\n' >"${sandbox}/work/chapters/chapter-1.md"
  printf '# Second Chapter\n\n## Section A\n\nFirst.\n\n## Section A\n\nSecond.\n' >"${sandbox}/work/chapters/chapter-2.md"
  write_epub_config "${sandbox}/skelepress.config.yaml" epub "EPUB Sandbox Guide" es true

  (
    cd "${sandbox}/work" && "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml"
  ) >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "duplicate headings in a fragment target render"
  assert_contains "$md" '\]\(#ch-chapter-2-section-a\)' "the fragment link targets the first occurrence's unsuffixed id"
  assert_contains "$md" '\{#ch-chapter-2-section-a-1\}' "the second occurrence gets a deduplicated explicit id"

  rm -rf "$sandbox"
  rm -f "$out"
}

# In the PDF the fragment link must land on the page that carries the target
# section, not on the chapter start (issue #111 acceptance, PDF side).
run_chapter_fragment_pdf_destination_test() {
  if ! command -v pandoc >/dev/null 2>&1 || ! command -v xelatex >/dev/null 2>&1 \
    || ! command -v pdftohtml >/dev/null 2>&1; then
    echo "SKIP PDF fragment destination (pandoc/xelatex/pdftohtml not available)"
    return 0
  fi

  local sandbox out pdf xml code=0
  sandbox="$(new_epub_sandbox)"
  out="$(mktemp)"
  pdf="${sandbox}/work/out/epub-guide-manual.pdf"
  xml="${sandbox}/out.xml"

  printf '# First Chapter\n\nDetails: [Section A](chapter-2.md#section-a).\n\n[The second chapter](chapter-2.md).\n\n' >"${sandbox}/work/chapters/chapter-1.md"
  {
    printf '# Second Chapter\n\nIntro.\n\n'
    for _ in $(seq 1 120); do
      printf 'Filler paragraph with several words to consume vertical space on the page.\n\n'
    done
    printf '## Section A\n\nBody.\n'
  } >"${sandbox}/work/chapters/chapter-2.md"
  # The sandbox LaTeX stub lacks hyperref, which every internal link needs.
  cat >"${sandbox}/templates/default.tex" <<'EOF'
\documentclass{article}
\usepackage{hyperref}
\begin{document}
$body$
\end{document}
EOF
  write_epub_config "${sandbox}/skelepress.config.yaml" pdf "EPUB Sandbox Guide" es false

  (
    cd "${sandbox}/work" && "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml"
  ) >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "PDF renders with a fragment link to a sibling section"

  pdftohtml -xml -stdout "$pdf" >"$xml" 2>/dev/null
  python3 - "$xml" <<'PYEOF'
import re
import sys

xml = open(sys.argv[1], encoding="utf-8", errors="replace").read()


def heading_page(text):
    """Page of the rendered heading whose text is exactly `text`."""
    page = None
    for line in xml.splitlines():
        page_match = re.search(r'<page number="(\d+)"', line)
        if page_match:
            page = int(page_match.group(1))
        if page is not None and re.search(r'<b>' + re.escape(text) + r'</b>', line):
            return page
    return None


def anchor_dest_page(text):
    """Destination page of the internal link whose visible text starts with `text`."""
    match = re.search(r'<a href="[^"]*#(\d+)">[^<]*' + re.escape(text), xml)
    return int(match.group(1)) if match else None


section_page = anchor_dest_page("Section A")
chapter_page = anchor_dest_page("The second chapter")
target_page = heading_page("Section A")
problems = []
if section_page is None:
    problems.append("the fragment link is not an internal PDF link to a page")
if chapter_page is None:
    problems.append("the chapter-start link is not an internal PDF link to a page")
if target_page is None:
    problems.append("the target section heading was not found in the PDF")
if problems:
    sys.exit("; ".join(problems))
if section_page != target_page:
    sys.exit(f"fragment link lands on page {section_page}, but the section heading is on page {target_page}")
if section_page == chapter_page:
    sys.exit(f"fragment link and chapter-start link both land on page {section_page}")
PYEOF
  code=$?
  assert_exit_code "0" "$code" "the fragment link lands on the target section page, not on the chapter start"

  rm -rf "$sandbox"
  rm -f "$out" "$xml"
}
