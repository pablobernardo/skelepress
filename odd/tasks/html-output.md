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

Wave 2 scope (issue #253): manual light/dark toggle, local chapter-scoped
search, `content-visibility: auto` polish, visual refinement from artifact
feedback, optional `<details>` mobile TOC. Related CLI follow-up:
`render --formats` override (issue #254), proposed as its own `feat(cli)`
commit after the wave-1 commit (`fd35be8`).

## Log

- L1: User considered additional output formats beyond PDF and EPUB (Kindle, HTML with simulated page-turning or a compiled docs site).
- L2: After pros/cons analysis the user discarded Kindle.
- L3: User decided navigation should be by sections, dropping pagination.
- L4: Follow-up on loading decided: full text in one file, lazy images; per-chapter fetching rejected as complexity attacking the wrong weight.
- L5: User accepted the consolidated proposal (single self-contained file, section navigation, own stylesheet, minimal optional JS).
- L6: Launch authorized with the S11 restriction and a plan summary delivered; two-wave plan accepted.
- L7: Wave 1 implemented on `feat/html-output`. Evidence: `check-html-format.py` 8/8 (plan shape, reader-off, template note, format gating, real-pandoc artifact structure); conformance 5/5 cases; `check-docs` OK; help tests 15/15 after expectation update; full L1 suite 1058 PASS / 0 FAIL. Example artifact rendered from `examples/manual` for review.
- L8: User authorized the wave-1 commit and asked for issues to track the pending work. The commit was made as `fd35be8` on `feat/html-output` (728 insertions, 19 files); issues #253 (reader wave 2) and #254 (`--formats` override) were filed. No push made; the branch stays local until the user decides.
- L9: Full L1 suite green after wave 1: 1058 PASS / 0 FAIL. Two test expectations were updated with the product change (the help description in tests/l1/help.sh and the conformance rerun count, which is always cases+1).
- L11: PR #256 failed CI on Linux: the real-render case of the override suite lacked the pandoc availability guard every other real-render test carries (the local macOS run had pandoc, so the gap was invisible). Guard added and verified; the fix rides with the PR branch.
- L10: #254 implemented on the same branch as its own commit, RED first (6-case suite in tests/l1/render/formats-override.sh, 5 failing), then GREEN. Design: the CLI flag forwards through SKELEPRESS_FORMATS; the renderer validates against the format enum and dedupes; preflight applies the same override to its dependency-union check. Differential check confirmed no-override behavior is unchanged and invalid values fail with the localized contract message. Docs (usage.md, README, help text), CHANGELOG and 4 catalogs updated. Two incidental test fixes ride along, both verified: formats-override.sh exit codes now captured under the orchestrator's set -e (the missing capture aborted the whole suite on expected failures), and tests/l1/render/links.sh carried a broken grep pattern since #242 that made a not-contains assertion silently pass (grep errored and the assertion counted it as clean); fixed and confirmed the pattern now actually detects the dead link. Final suite: 1064 PASS / 0 FAIL. Commit: separate feat(cli) per the two-unit rule.
