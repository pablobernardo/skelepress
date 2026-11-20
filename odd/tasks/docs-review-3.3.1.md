# Docs review and cleanup before tagging 3.3.1

Consolidate the accumulated documentation drift since 3.2.0 (`draft`, page
breaks, seven book styles, bookkit, strikethrough fix, EPUB Mermaid default,
brand kit) per a full read-only audit. Release tag 3.3.1 waits for this.

## Specs

- S1. User request: review and clean up `README.md` and the `docs/` tree
  before publishing the release, given that accumulated functionality since
  earlier releases has changed the toolkit; the user confirmed the review
  should gate the 3.3.1 tag.
- S2. Scope: documentation-only changes (Markdown) plus tag comments in
  `.github/workflows/ci.yml`; no behavior, schema, CLI or catalog changes.
- S3. Findings authority: the parent audit list (23 findings, P1/P2/P3) held
  in the parent task delegation; workers fix only the findings assigned to
  their surface, quoting each finding's file context before editing.
- S4. Language policy: all edited docs stay English; `CHANGELOG.md` records
  stay a record — only a factually wrong statement (draft accepting
  directories, which the CLI rejects) may be corrected, marked dated.
- S5. After the units land: `make gate` green on the resulting candidate
  before the release docs PR merges; CHANGELOG 3.3.1 text already merged on
  main is NOT reopened (entries describe the release; docs fixes get their
  own note only if the maintainer asks).

## Tasks

- T1 | S1-S4 | Writer A (nav/architecture/housekeeping). Files:
  `docs/README.md` (fix duplicated `## Outside docs/` heading + headerless
  table; add `migration.md` row), `docs/architecture.md` (example tree with
  current examples list; templates/filters listing per shipped styles pointing
  at `docs/books.md#built-in-book-styles`; decision records D15-D18 for draft,
  page breaks, 3.3.0 styles, EPUB Mermaid background; docs/scripts listing
  completeness), `docs/dependency-policy.md` (drop or update the historical
  "examples are documentation, manual, test, ohmyfake" paragraph at the
  2.1.0 candidate line), `docs/releasing.md` (mark the 3.0.0 clean-break
  exception as a historical one-time check), `docs/i18n.md` (`.skelepress.env`
  lookup is upward from `$PWD`; drop the hand-maintained "157 keys" or make it
  structural; mark the planned `docs/<lang>/` layout as not implemented;
  reconcile "reference catalog is es.json" with AGENTS.md: es.json is the
  structural key base, not a privileged language), `docs/install.md` (payload
  list must include `filters/`, `VERSION`, `README.md`, `LICENSE`), and one
  added line in `CHANGELOG.md` 3.2.0 fixing "files or directories" -> files
  only, with a dated bracketed note (draft never accepted directories).
- T2 | S1-S4 | Writer B (feature coverage). Files: `README.md` (feature
  summary must mention EPUB output, `skelepress book` with the eight built-in
  styles and `skelepress draft`; keep quickstart minimal, link
  `docs/usage.md`, `docs/books.md`), `docs/usage.md` ("six top-level guides"
  -> nine with the current real count and the `brand/README.md` exclusion;
  "future conformance suite" -> shipped, link `tests/conformance/`;
  `pandoc.template` row links to `docs/books.md#built-in-book-styles`;
  `skeledraft-20261116-1745.pdf` -> `skeledraft-YYYYMMDD-HHMMSS-NNNN.pdf`;
  `filters.mermaid.background` table row gains the EPUB/HTML white-bake note),
  `docs/books.md` (keep as narrative home), `scripts/tools/bookkit/README.md`
  (Usage: `--template` accepts a builtin style name or a path, matching
  `build.py` and the CLI message), `examples/book-kit/README.md` (dedupe the
  duplicated model/convention sections against the tool README; example keeps
  "what this shows + how to run").
- T3 | S2 | Inline parent: add the missing tag-in-a-comment pin annotations to
  `.github/workflows/ci.yml` (D10) or reconcile D10 wording; parent decides
  after T1/T2 land. RESOLVED: false positive — both `uses:` lines already
  carry the standard previous-line comment `# actions/upload-artifact v7.0.2`
  (inline comments exceed the 80-column yamllint limit; the auditor grepped
  only the `uses:` lines). No change needed; finding 17 closed as not-a-gap.
- T4 | S5 | Parent: verify (make gate), work-unit commits, PR, and re-run
  candidate acceptance only if the release content changes; merge, then tag
  3.3.1 on explicit maintainer order.

## Log

- L1. User request (session 2026-11-20): review and clean up README.md and
  docs/ before the 3.3.1 release, because the accumulated functionality has
  outgrown the current documentation.
- L2. Evidence: audit returned 23 findings — P1: 1 (docs/README.md broken
  index: duplicate "Outside docs/" + headerless table + missing migration.md
  row), 2-4 (dependency-policy stale example list; architecture stale
  examples tree and template/filter listing), 5 (bookkit README --template
  path-only claim contradicts build.py builtin support), 6 (README missing
  EPUB/books/draft). P2: 7 (usage.md "six guides" wrong count), 8 (future
  conformance suite already shipped), 9 (pandoc.template missing style list
  pointer), 10 (architecture decision records stop at D14), 11 (migration.md
  still "Migrating to 2.1.0"), 12 (install.md payload list incomplete), 13
  (draft output name pattern wrong), 14 (CHANGELOG draft files-or-directories
  false), 15 (mermaid background table missing EPUB note), 16 (releasing.md
  3.0.0 exception stale as recurring), 17 (D10 pin comments missing in
  ci.yml; all other pins verified current). P3: 18 (book model triplicated),
  19 (README duplicated install block, kept as-is), 20 (architecture tree
  omits shipped docs/scripts), 21 (i18n.md env-file location wrong), 22
  (i18n.md key count and planned locale layout), 23 (i18n.md es.json wording
  vs AGENTS.md). Negative result: no doc still claims a limitation that
  already shipped. - L3. T1 landed as commit 8530c59 (Writer A: 8/8 findings; check-docs 86/0);
  T2 landed as commit ef10239 (Writer B: 9/9 findings; check-docs 86/0);
  T3 closed as false positive (finding 17) after verification against
  ef10239 content. Residual known gaps deliberately deferred: migration.md
  still titled "Migrating to 2.1.0" (finding 11, needs its own versioned-page
  decision), stale PROJECT_ENV_FILE comment at scripts/runtime/i18n.sh:5
  (outside the docs-only scope of this change). Status: T4 pending (gate
  re-run, PR).
