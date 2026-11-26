# Feature: HTML output format with chapter navigation

Single self-contained HTML artifact with section-based navigation (TOC + prev/next + hash links).
Pagination was analyzed and explicitly rejected during scoping; a Kindle format was rejected outright.

## Specs

- S1: `html` becomes a third value of `output.formats` (additive contract change; contract `version` stays 1).
- S2: Navigation is by chapter/section (sidebar TOC, prev/next pager, hash anchors). Pagination is out of scope by decision: the browser is already a reader and the PDF owns the page model.
- S3: One self-contained `.html` artifact per render, matching the toolkit's one-artifact-per-format model; document text is complete in the file (browser search covers the book), images embed as data URIs.
- S4: Images carry `loading="lazy"` and `decoding="async"` in the HTML target; loaded assets stay in the reader's memory.
- S5: The reader shell renders navigation without JS where possible (`<details>` mobile TOC would be wave 2; base wave keeps static sidebar); optional small JS adds active-section highlight and the pager; everything degrades to a fully readable document without JS.
- S6: Own toolkit stylesheet (custom properties, dark mode via `prefers-color-scheme`, print stylesheet); no framework, no CDN, no Node, no build step.
- S7: Layout uses Pandoc `--section-divs`; cross-chapter links keep working as same-document anchors (D19 compatible).
- S8: `output.html.reader` (default `true`) opts out of the reader shell, producing bare Pandoc HTML.
- S9: Kindle format discarded (no writer supported; KDP accepts EPUB; conversion-only path rejected for now).
- S10: User-facing strings come from `i18n/locales/`; never inline in code.
- S11: User restriction recorded for the whole feature: no commits without explicit authorization; each commit proposed before it is made.

## Tasks

| ID | Linked | Route | What | Commit |
| --- | --- | --- | --- | --- |
| T1 | S1,S8,S10 | inline | Contract first: schema enum + `output.html.*` key + validator; catalog updates | (wave-1 commit) |
| T2 | S1,S3,S7 | inline | Renderer HTML job in `build_single_plan` (argv, template resolution, naming, metadata branch, `side_effects.html`) | (wave-1 commit) |
| T3 | S5,S6 | inline | `templates/reader.html` shell + stylesheet + optional JS (wave 1 = template-lite) | (wave-1 commit) |
| T4 | S4 | inline | `filters/lazy-images.lua`, HTML-gated | (wave-1 commit) |
| T5 | S1,S3,S5,S8 | inline | `tests/integration/check-html-format.py` (8 cases) registered; conformance case `html.yaml` + expectation; two test expectations updated with the product change (help description, rerun case count) | (wave-1 commit) |
| T6 | S8,S10 | inline | Docs: `usage.md` HTML section, optional-settings table, `index.md`, CHANGELOG Unreleased, 4 locale catalogs | (wave-1 commit) |

Wave 2 scope (tracked in issues after the wave-1 commit): manual light/dark toggle, local chapter-scoped
search, `content-visibility: auto` polish, visual refinement from artifact feedback, optional `<details>`
mobile TOC. Related CLI follow-up: `render --formats` override (issue filed separately).

## Wave 2

- Scope (issue #253): manual theme toggle (localStorage recall, no first-paint
  flash, storage-failure degradation), chapter search box (~150 lines ceiling,
  results in chapter order, native Ctrl+F unaffected), content-visibility
  render deferral guarded by an @supports query, mobile contents drawer as a
  zero-JS `<details>` duplicate of the TOC.
- Review (ordinary native review, lineage review-72a0ce6f7dac32fc): the
  reviewers confirmed three deterministic defects introduced during wave 2 —
  two dead dark-palette selectors built on a descendant combinator that can
  never match the root element, and a drawer whose only display rule hid it at
  every width. All three were corrected inside the bounded correction budget
  (selectors re-anchored on the root element itself; narrow-screen display
  rule restored), the targeted validator approved, and the acknowledgement
  burned. Advisory findings R3-003 (drawer links shadowing the sidebar in the
  active-chapter highlight) and R2-5 (a comment misdescribing the mechanism
  as a class) were also fixed; the remaining advisories stay recorded as later
  work (R2-6 palette duplication, R2-7/R3-005 substring-only tests, R3-004
  inert controls without JS).
- Evidence: check-html-format.py 9/9 incl. the wave-2 artifact test; full L1
  suite 1065 PASS / 0 FAIL on the wave-2 tree; `reader: false` re-verified as
  bare HTML; example artifact re-rendered for review.

## Fold-toggle alignment (wave 2, eighth iteration, reverted)

An edge-aligned fold toggle (fixed spacer slot) with a capped search box was
implemented and passed native review review-f6060114216e82b5 (three layout
advisories recorded as future work), but the result mis-weighted the header:
the toggle drifted toward the middle and the search box lost its reach. The
user reverted the alignment; the reader keeps the toggle at the bar start
with the search box stretching to the view/theme/credit controls. The
review lineage stays closed; implementation notes remain in this record.

## Highlight-as-state (wave 2, seventh iteration)

The view switch settled: one fixed stacked-sheets icon, and the button's
highlight carries the mode — unlit while reading chapter by chapter, accent
while the whole book is one view. aria-pressed now semantics the full view;
two SVG-platform traps were found on the way: the UA [hidden] rule does not
reach SVG-namespace elements, and .hidden as a property is a silent expando
on SVG (the attribute is the only interface CSS reacts to, so swaps must go
through toggleAttribute). Records: skeptic probes in headless Chrome with
fresh browser contexts.

## WYSIWYG icon state (wave 2, sixth iteration)

The two-icon offer design was replaced after review with one in-state icon:
chapter mode shows the single page, full view shows the stacked sheets, and
the click swaps view and icon together (like a play/pause control). The
sidebar default (expanded) was confirmed; the fold is a persisted reader
choice, never a default.

## View switch as a two-state icon (wave 2, fifth iteration)

The Chapter/Full button replaced its changing text with two drawn states: a
single outlined page for the chapter view and three stacked, offset pages for
the full view; the pressed state and the hidden attribute decide which shows,
JS swaps them, and without script the chapter-state icon leads. The label
traffic ("names the view it offers next") stays in the accessible name and
tooltip. Verified in headless Chrome across the full toggle cycle.

## Header layout (wave 2, fourth iteration, user direction)

The reading bar became a full-width header above sidebar and content
(user-directed layout): icon-only ☰ panel toggle first (mobile drives the
contents drawer; desktop folds the column), the document title next to it,
then the search box, then the chapter-mode and theme switches. The mobile
drawer starts closed and remembers nothing; without script it opens through
its own summary. The sidebar masthead keeps subtitle/author/date; the title
lives in the header to answer "where am I". Browser-verified in headless
Chrome at both widths (1100px title + fold 820->1100; 700px toggle opens the
drawer with synced aria-pressed).

## Browser-level verification (wave 2, third iteration)

Two user-reported defects after the reading-bar rework were fixed and then
proved in a real browser (Chrome via the mermaid-cli puppeteer installation,
not a repo dependency):

1. Chapter mode started blank when the URL carried a hash: the tangled
   conditional passed an undefined id to showChapter, marking no chapter
   current. Fixed with chapterForHash() (closest chapter section, null fallback)
   plus a stale-id guard that can never leave the reader empty.
2. Sidebar/drawer/search clicks navigated to hidden chapters: anchor handling
   was wired only for pager and search. Fixed with one delegated document-level
   click handler for every in-page anchor plus a hashchange listener (back and
   forward restore the chapter the hash names).
3. Browser run also caught the per-chapter pager install loop missing after a
   prior edit, and a leftover updatePager reference that threw a page-level
   ReferenceError killing later wiring. Both removed/restored.

Smoke evidence (headless Chrome, file:// artifact): scroll mode 8/8 visible;
toggle -> exactly one visible chapter; last sidebar link reveals its chapter;
pager next advances overview -> installation; drawer present; zero page errors.

## Log

- L1: Additional output formats beyond PDF and EPUB were requested for evaluation (Kindle, HTML with simulated page-turning or a compiled docs site).
- L2: Kindle was discarded after the pros/cons analysis.
- L3: Section navigation replaced simulated pagination by decision.
- L4: Loading follow-up decided: full text in one file, lazy images; per-chapter fetching rejected as complexity attacking the wrong weight.
- L5: The consolidated proposal was accepted (single self-contained file, section navigation, own stylesheet, minimal optional JS).
- L6: Launch authorized with the S11 restriction and a plan summary delivered; two-wave plan accepted.
- L7: Wave 1 implemented on `feat/html-output`. Evidence: `check-html-format.py` 8/8 (plan shape, reader-off, template note, format gating, real-pandoc artifact structure); conformance 5/5 cases; `check-docs` OK; help tests 15/15 after expectation update; full L1 suite 1058 PASS / 0 FAIL. Example artifact rendered from `examples/manual` for review.
- L8: User authorized the wave-1 commit and asked for issues to track the pending work (wave 2 scope, `--formats` override).
