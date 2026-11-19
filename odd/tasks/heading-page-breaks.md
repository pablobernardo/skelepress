# heading-page-breaks (issue #194, release 3.2.0)

Worktree: `pandoc-toolkit-feat-heading-page-breaks`, branch `feat/heading-page-breaks` from `origin/main` c0c7fb7.
PR #197 open against main; no merge until the human's own controls pass.

## Specs

- S1: A chapter starting with `##` gets a page break in PDF when enabled by configuration, without raw LaTeX in the sources.
- S2: `{.page-break}` on any heading is honoured in PDF and exposes an HTML/EPUB hook (class preserved, or an equivalent documented marker).
- S3: Defaults keep current publications byte-for-byte: `legacy_clearpage_between_h1` alone still produces the same output.
- S4: A heading marked for a break does not produce a blank page when the previous chapter already broke the page.
- S5: Documented in the configuration schema and in the render/authoring docs, with an example.
- S6 (user session rules): tests first (RED→GREEN), artifacts in English, no local PDF generation, no force-push or deletions, nothing marked done without real verification.

## Tasks

- T1 (S1, S3): chapter-boundary level in `merged_markdown`, render-time range guard, schema key — commit 5697928.
- T2 (S2): `filters/heading-page-break.lua`, always-on argv entry, EPUB CSS hook — commit 5697928.
- T3 (S1-S5): plan contract `heading_break_level`, conformance expectations regenerated, 30 L1 assertions, docs + 4 i18n locales — commit 5697928.
- T4 (S5): docs wording corrections from native review advisories R2-001/R2-004/R3-004 — commit 0edd7c3.
- T5 (S3): PR #197 merged by the human as squash eac6a5e (#194 closed); post-merge CI 44133270648 success; hosted L2 render integration run 44129382449 success on the PR head.

## Log

- L1 (2026-11-17) — Implement #194 test-first in a fresh worktree on `origin/main`; keep docs and all four catalogs aligned, open a PR to `main`, and defer merging.
- L2: Native ordinary review `review-5ecb51a09e312bdf` (readability + reliability) APPROVED, acknowledged/burned. 8 advisory findings; the two factual docs ones corrected in 0edd7c3; the rest recorded as later work (plan key naming, regex assembly, EPUB CSS proof, later-H1 coverage, render-time guard test).
- L3: Rediscovered EPUB nuance: `templates/epub-header.html` is inlined into every chapter, so a literal `\clearpage` in a CSS comment fails the EPUB purity test; wording avoids the token.
- L4: Release preparation: CHANGELOG [3.2.0] section and VERSION 3.2.0 on branch chore/release-3.2.0 (PR #198); tag and GitHub release remain the human's explicit decisions.
