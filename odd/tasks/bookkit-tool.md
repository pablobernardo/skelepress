# Ship the book adapter as a versioned tool
Branch: `feat/bookkit-tool` (worktree `pandoc-toolkit-feat-bookkit-tool`); scope: the tool, its schemas, the shared runtime it reuses, the examples converted to it, tests and documentation.
Why it is one slice over the review budget: the tool only proves anything with its schemas, the examples and the tests that run it, and the shared runtime it reuses had to be extracted first — a partial delivery would leave the adapter duplicated or the validator untested.

## Specs

- S1: Ship the adapter as a supported tool. Its manifest uses `manifest_version`, separate from the toolkit configuration `version`.
- S2: Use `content/front-matter`, `content/chapters`, and `content/back-matter`; the names are publication terminology, not frontend/backend terminology.
- S3: Use a closed `profile` enum with `book` as its only value. Profiles select rules, not executable scripts.
- S4: Provide a schema and canonical example for the book manifest instead of a longer prose template.
- S5: Decisions taken with the maintainer: `manifest_version` plus `profile`, entries with `file`/`print`/`optional`, `chapters_dir` defaulting to `content/chapters`, `--check` for cheap validation, and English tool messages for now with the catalog decision deferred.
- S6: `pandoc-pdf book build` is deliberately not added yet: a subcommand must be a thin wrapper over a stable schema, not the place where the schema stabilises.

## Tasks

- T1 [S1, S5] done; route: delegated worker (context backstop); `scripts/tools/bookkit/{build.py,manifest.schema.json,series.schema.json,README.md}`, one adapter for both shapes, `--check`, the three entry rules, generated LaTeX mode files.
- T2 [S5] done; route: same worker; `scripts/runtime/schema_runtime.py` extracted (YAML loader plus the JSON-Schema subset validator) and `validate-config.py` refactored onto it, verified differentially on nine cases with identical output, errors and exit codes; `preflight.py` deliberately untouched.
- T3 [S2, S4] done; route: worker plus parent; examples converted to the shipped tool with `manifest_version`, `profile` and the publishing folders, the canonical manifests made complete (`audience`, `isbn`, `collection`), and `examples/book-kit/build.py` replaced by a thin runner.
- T4 [S3] done; route: worker; `anyOf` added to the validator subset because entries accept either a path string or a map, with the message keyed as `validate.error.no_any_of_match`.
- T5 [S5] done; route: parent; the i18n key added to all four catalogs (174 keys) and `AGENTS.md` keyword list updated to include `anyOf` and to name the shared runtime.
- T6 [S2] done; route: parent; `tests/l1/bookkit.sh` with 21 assertions and no PDF renders, plus four `schema_runtime.py` copies in the `tests/l1/render.sh` sandboxes, which the refactor required.
- T7 [S1–S6] in progress; route: parent delivery; gate 463/0, commit `da84e43`, PR, squash merge and main verification.

## Log

L1 — The distribution includes the adapter as a supported tool with a dedicated manifest contract, a fixed set of profiles, and conventional publication directory names. A canonical manifest example demonstrates the contract.

L2 — Delivery evidence. Gate 463/0 with 4 locales and 174 keys, 79 markdown files and 4 conforming plans. Parent verification of the tool's behaviour: `--check` validates one volume for the single project and two for the series; a manifest without `title` reports `❌ In 'root' required fields must be missing: title`; `profile: article` is rejected with `❌ 'profile' must be one of: book (got 'article')`; the volume that starts at chapter 4 generates `\setcounter{chapter}{3}`; `print: false` entries are absent from the generated configuration; and a real series render exits 0 producing two PDFs. Two findings carried out of this unit as separate work: `check-docs.py` raises `FileNotFoundError` when the git index lists tracked paths that no longer exist on disk, which any uncommitted rename triggers, and the tool's `--template` default points at `examples/book/templates/book.tex`, so an installed artifact must pass one explicitly.
