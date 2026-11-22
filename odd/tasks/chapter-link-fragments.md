# Resolve cross-chapter link fragments (#111)

Resolve a cross-chapter link `migration.md#section-slug` to the target section
instead of dropping the fragment, using explicit ids derived from file and
heading (issue option 2). Base: `main` at `dbc6566` (v3.4.2). Delivery: single
PR below the ~400 review-line budget; release as 3.5.0 (minor).

## Specs

S1. Issue 111: "A link with a fragment lands on the target section in both the
    PDF and the EPUB."
S2. Issue 111: "A fragment that names no existing heading degrades visibly, not
    silently."
S3. Issue 111 problem statement (verbatim example):

```text
`[migration](migration.md#version-1-to-2)`
```

    "becomes a link to the start of
    the migration chapter and the fragment is dropped". The rewritten link must
    point at the matching section, not at the chapter start.
S4. Plan (maintainer-validated): use issue option 2 — target headings get an
    explicit id derived from file and heading — and do NOT reproduce Pandoc's
    `auto_identifiers` algorithm (option 1) nor keep a soft-fallback-only link
    (option 3). Existing chapter-wide anchors, chapter-only links, fenced-code
    examples, non-selected paths and byte-identical no-cross-reference output
    are preserved. New user-facing strings come from the i18n catalogs; any new
    key must be added to all four locales (`en`, `es`, `gl`, `pt`). Release
    will be 3.5.0 (minor), not a patch.

## Tasks

T1 [S1-S3] RED: tests pinning (a) a fragment link rewritten to a per-heading
   id that exists on the target heading in the merged Markdown and EPUB,
   (b) an unmatched fragment degrading visibly in the reader-facing output.
   Route: inline.
T2 [S1-S4] GREEN: renderer fragment resolution (parse fragment from
   SIBLING_LINK matches, map to a target heading via the toolkit's own slug
   derivation, inject a deduped explicit `{#id}` on the target heading,
   rewrite the link to that id, visible degradation when no heading matches),
   plus catalog keys in the four locales. Route: inline.
T3 [S1-S4] docs (`docs/usage.md` semantics bullet list, `docs/migration.md`
   EPUB note, `docs/dependency-policy.md` anchor paragraph, one decision row in
   `docs/architecture.md`) and CHANGELOG `[Unreleased]` entry. Route: inline.
T4 [S1-S4] verification: focused checks, risk item 3 (shared link-rewrite code
   also serves chapter-only links) needs one independent verifier; commit in
   reviewable work-unit slices on `feat/chapter-link-fragments`. Route:
   independent verify + parent.

## Log

L1. The maintainer asked to start issue #111 in this session ("arranca #111"),
   resuming the closed-session plan for release 3.5.0. The full live issue body
   is stored at `.git/issue111/request.json`; its acceptance criteria and
   example are quoted in S1-S3.
L2. Exploration (read-only): mechanism at
   `scripts/runtime/render-native.py:560-662` (SIBLING_LINK, sibling_link_markers,
   rewrite_sibling_links with fence skip, with_marker after the first heading,
   merged_markdown wiring; the same merged Markdown feeds both writers).
   `slugify` at `:46-51` is the filename helper pinned by
   `tests/l1/render/naming.sh` and must not be repurposed. No existing test
   pins fragment discard. Fragment-correctness docs live in
   `docs/usage.md:133-137`; `scripts/dev/check-docs.py:79` strips fragments, so
   no checker validates fragment targets today. No `[Unreleased]` CHANGELOG
   section exists.
L3. Implemented and verified on `main`-descendant commits ffee8e0 (renderer +
   catalogs), 5180ed8 (tests), 548c3e6 (docs/CHANGELOG); 12 files, 369 authored
   insertions, 12 deletions, in three reviewable slices. Observed RED first:
   focused driver 2/16 then 9/18 passes with fragment assertions failing
   (including the PDF diagnosis "lands on page 1, but the section heading is on
   page 3"); then GREEN focused 18/18 with empty stderr, and full
   `bash tests/run.sh` PASS=953 FAIL=0 (the `truncate.sty` doctor-fallback
   lines are expected stdout). Static checks: bash -n ok; shellcheck clean on
   the new test code and byte-identical baseline warnings (SC2034/SC1091) on
   tests/run.sh; `git diff --check` clean; AST + tokenizer guard Python 3.9
   clean on both changed Python files; check-docs OK (90 files); catalogs
   key-aligned four locales with the new `render.fragment.section_not_found`
   key. Design notes: only fragments that resolve get explicit ids injected
   (planned slugs that a fenced/absent heading does not own inject nothing);
   unmatched fragments keep the chapter anchor plus a localized note following
   `document.language` via the new `t_for` helper in i18n_runtime.py; the PDF
   test template adds `hyperref` (the sandbox stub lacks it) and asserts the
   link's destination page, not the anchor's own page.
L4. Independent verifier (risk item 3, shared sibling-link code) was attempted
   but the admission check did not recognize the risk declaration format in the
   launch text; per the admission instruction it was not retried and the risk
   line was not re-engineered to force admission. Inline verification covered
   the shared-code risk: the full suite exercises the unrequested consumers of
   the changed helpers (chapter-only links, EPUB publication guard,
   no-cross-reference byte-identity, fence skipping) and passed 953/953.
   Deferred to hosted CI if the maintainer wants a hosted run before the PR:
   the PDF destination test needs pandoc/xelatex/pdftohtml and skips locally
   when any is absent (it ran here; it skips in the minimal CI L1 job).
L5. The task-document example fence keeps the literal issue example inert for
   `scripts/dev/check-docs.py`, which otherwise reads it as a broken reference.
L6. Release-versioning decision confirmed with the maintainer: 3.5.0 minor,
   not a patch. Rationale: the injected explicit ids and the fragment
   resolution are new observable behavior beyond the documented chapter-anchor
   limit of #106, so the `[Unreleased]` `Added` entry stands; the maintainer
   chose to keep the minor bump after weighing the defect-fix framing.
L7. Real-reader defect found during maintainer evaluation and fixed: Apple
   Books mis-positioned internal-link jumps in toolkit EPUBs (blank pages
   until repaginating). Single-variable bisect with maintainer feedback
   isolated the bundled `templates/epub-header.html` first-heading override;
   Pandoc's default stylesheet forces `h1 { page-break-before: always }` and
   the toolkit's explicit `auto` override breaks Apple Books anchor jumps.
   Fix 0c56ae2 neutralizes with `avoid`; structure test 5180ed8-pinned check
   replaced (RED observed, then GREEN 39/39); full suite 956/956; EPUBCheck
   clean; CHANGELOG entry 7c3d318. End-to-end maintainer evaluation passed on
   the rebuilt evaluation EPUB: fragment link lands on the target section,
   chapter link on the chapter start, unmatched fragment degrades visibly
   with the localized note, and no unrelated section receives a jump.
L8. Native ordinary review (lineage review-106de3c34aaf965c): four lens
   results admitted; the refuter corroborated five introduced CRITICAL
   findings — the fragment planner and the id injector disagreed on heading
   ownership (author-written {#id} headings and heading-shaped lines inside
   fences were planned as resolvable but never injected, so a fragment link
   aimed at them was rewritten to an anchor no element carries, exit 0).
   Bounded correction accepted at 50 diff lines and committed: the planner
   now tracks fences and skips author-owned headings exactly like the
   injector, with regression test run_chapter_fragment_author_id_and_fence_test
   (RED observed, GREEN 21/21 focused, full suite PASS=961 FAIL=0).
L9. The targeted-validator capture route then dead-ended on a provider
   defect: `capture-route-registration-rejected` / `selector-mismatch`,
   deterministic across a fresh-STATUS re-offer, later also refused by bare
   STATUS. Reported with maintainer consent as one occurrence comment on the
   canonical issue Gentleman-Programming/gentle-ai#5206 (no published fix;
   issue closed NOT_PLANNED by stale automation). No captured decline
   invocation existed, so the candidate-scoped continuation fails closed:
   native operations stopped, all state preserved, delivery (push/PR) remains
   gated pending provider disposition or an explicit maintainer decision.
L10. Cycle closure decision: the maintainer rechecked native STATUS once (still
   `capture-route-registration-rejected`) and explicitly chose NOT to disable
   RDD clone-scope. The cycle holds: commits stay local, the lineage stays
   preserved, delivery waits on the provider's published fix or an explicit
   later maintainer decision. Resumption paths per the provider-defect skill:
   an installed published fix, or a maintainer-authorized native recovery.
L11. Retained-authority continuation: bound STATUS re-offered the supported
   targeted-validation transition with the exact collection binding (no
   selector-mismatch; the provider defect resolved upstream). Binding passed
   capture validation; its one-run forecast (`review-validator`, host relay)
   was acknowledged. Outcome: review APPROVED with 10 non-blocking advisory
   findings (residual planner/injector drift, t_for duplicating t,
   plan_document_language SystemExit handling, duplicate-id injection risk,
   catalog note wording vs docs, no operator-facing signal for unresolved
   fragments) and acknowledge-approved consumed; authority burned. Delivery
   then follows ordinary repository policy: PR with `Refs #111`, no auto-close.
   Supersedes the blocked-continuation state of L10 on this lineage; no code
   or authority reset was involved.
