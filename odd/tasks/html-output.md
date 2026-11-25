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

## Log

- L1: User considered additional output formats beyond PDF and EPUB (Kindle, HTML with simulated page-turning or a compiled docs site).
- L2: After pros/cons analysis the user discarded Kindle.
- L3: User decided navigation should be by sections, dropping pagination.
- L4: Follow-up on loading decided: full text in one file, lazy images; per-chapter fetching rejected as complexity attacking the wrong weight.
- L5: User accepted the consolidated proposal (single self-contained file, section navigation, own stylesheet, minimal optional JS).
- L6: Launch authorized with the S11 restriction and a plan summary delivered; two-wave plan accepted.
- L7: Wave 1 implemented on `feat/html-output`. Evidence: `check-html-format.py` 8/8 (plan shape, reader-off, template note, format gating, real-pandoc artifact structure); conformance 5/5 cases; `check-docs` OK; help tests 15/15 after expectation update; full L1 suite 1058 PASS / 0 FAIL. Example artifact rendered from `examples/manual` for review.
- L8: User authorized the wave-1 commit and asked for issues to track the pending work (wave 2 scope, `--formats` override).
