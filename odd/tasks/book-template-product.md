# Ship the book template as a product
Branch: `feat/builtin-book-template`; scope: the shipped template, one resolution rule shared by the validator and the renderer, the removed example, tests and documentation.
Why it is one slice over the review budget: the move, the rule and the removal are one decision. Shipping a template that no configuration can name, or removing an example whose template has not moved yet, would leave the repository inconsistent in between.

## Specs

- S1: Ship the book template in the artifact and make it selectable by name from `pdf.config.yaml`, both in a checkout and in an installation.
- S2: Keep `book-kit`, remove the redundant `examples/book/` example, and promote its template to the built-in catalog. The single-volume example lives in `book-kit/single/`.
- S3: A bare name is a **product name, not a path**: `book` resolves inside the toolkit root; an unknown bare name fails naming the valid ones and is never read as a path; everything else keeps today's behaviour.
- S4: `pandoc-pdf render` validates before rendering, so the **validator and the renderer must share one rule**; two copies would let a configuration pass validation and fail to render, or the reverse.
- S5: No `pandoc-pdf book` subcommand: a subcommand should be a thin wrapper over a stabilised schema.

## Tasks

- T1 [S1, S3, S4] done; route: parent inline after two delegated workers failed to start; `scripts/runtime/template_runtime.py` as the single rule, `validate-config.py` accepting known names and rejecting unknown ones, `render-native.py` resolving the name against the toolkit root.
- T2 [S1, S2] done; route: parent; `git mv examples/book/templates/book.tex templates/book.tex`, `examples/book/` removed, `bookkit` defaulting to the builtin name and generating `template: "book"`.
- T3 [S3] done; route: parent; the new message in all four catalogs and the `CHANGELOG` `[Unreleased]` section.
- T4 [S3, S4] done; route: parent; five render assertions (name validates, plans, resolves inside the toolkit, unknown name rejected, failure names the valid ones) and four rewritten bookkit assertions.
- T5 [S4] done; route: parent; two test gaps closed — `template_runtime.py` copied into the four render sandboxes, and the examples test now reads only files a commit could publish instead of ignored run output.
- T6 [S1–S5] in progress; route: parent delivery; commit `5c4f623`, PR, squash merge and main verification.

## Log

L1 — The product template and example consolidation were approved. Deliver the isolated change through a PR and merge it into `main` only after the required checks pass.

L2 — Delivery evidence. Gate 473/0 with 4 locales and 174 keys, 66 markdown files and 4 conforming plans. The series renders 8 and 6 pages with `template: "book"`; the packaged archive carries `templates/book.tex` and **zero** files from `examples/`. Three failures were found and fixed on the way, all of them structural rather than of the feature: the render sandboxes copy runtime files explicitly and needed `template_runtime.py`; the examples test walked ignored run output and validated stale configurations pointing at the removed template; and the `--template` default of bookkit still pointed at a checkout-only path from the previous unit. Native review of this candidate was not started: the maintainer instructed to proceed directly to pull request and merge, and the reliability lens still cannot produce a report.
