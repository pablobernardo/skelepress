# Split the render and epub test areas by subject
Branch: `refactor/split-render-epub-tests`; scope: test files only, plus the orchestrator glob, the registration guard glob and three documentation sentences.
Why it is one slice over the review budget: splitting a 1288-line file into eleven means the diff is mostly moved text. The change cannot be smaller without leaving half the file in two places, and splitting it across commits would leave the suite unsourced or unregistered in between.

## Specs

- S1: Organize render and EPUB tests by subject rather than leaving each area in one file.
- S2: Keep two levels: one directory per artifact type and one file per subject, approximately 100–200 lines per file.
- S3: A pure move: every function body stays byte-identical, and the number of assertions does not change.
- S4: The structural contracts of a test tree must be updated in the same change: what the orchestrator sources, what the registration guard scans, and every document that names the old paths.

## Tasks

- T1 [S3] done; route: parent; a script split the two files by function, wrote 18 files and verified **per-function sha256 before and after**: 44 functions, none lost, none altered.
- T2 [S4] done; route: parent; the registration guard now scans `tests/l1/*.sh` and `tests/l1/*/*.sh`, and `tests/run.sh` sources both levels.
- T3 [S4] done; route: parent; `AGENTS.md`, `CONTRIBUTING.md` and `docs/dependency-policy.md` describe the nesting and no longer name the removed files.
- T4 [S1, S2] in progress; route: parent delivery; commit `6781cd2`, PR, squash merge and main verification.

## Log

L1 — Approved the two-level, subject-based split with no test behavior change.

L2 — Delivery evidence. Gate 473/0 with 174 keys, 67 markdown files and 4 conforming plans — **the same assertion count as before the split**, which is the signal that the move lost nothing: the functions moved, so the number cannot move with them. Three wiring failures were found and fixed, each caught by a different guard: the suite aborted at 13 seconds because `run.sh` never sourced the nested files; the registration guard would have gone blind on them because it only globbed one level; and `check-docs` failed on two backticked references in `docs/dependency-policy.md` that named the removed files. The first two are exactly the failure modes the guard exists to prevent, which is why widening its glob was the first change rather than the last.
