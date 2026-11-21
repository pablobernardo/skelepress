# release-3.4.1

Patch release grouping the #219 bookkit fix and the remaining #220 advisory
cleanups, both from the 3.4.0 native review follow-ups. Technical summary in
English; no conversation transcripts.

## Specs

- S1. Ask #219: `resolve_template` (scripts/tools/bookkit/build.py) must reject
  an absolute value in the manifest/series `template` fields with an error
  naming the field and the relative-path rule ("relative to the directory
  holding the file"). The advisory: "`Path(base / value)` discards base when
  value is absolute, and the only check is `is_file`. A manifest can therefore
  reference an arbitrary absolute template file outside the project, contrary
  to the relative-path contract."
- S2. The `--template` flag keeps its current semantics (absolute values
  allowed) — another resolution branch, untouched by S1.
- S3. docs/books.md states the rejection in its template-path wording so the
  behavior and the documentation stay aligned.
- S4. R2-003: `select_chapter_files` (scripts/runtime/render-native.py) must
  guard the dict-entry `file` access like it guards `formats`; a malformed
  object entry dies with a message naming the missing field, never
  "Explicit file not found: .../None".
- S5. R2-002: the coupling `modes_gated`/`format_gated_entry`/`pdf_requested`
  in build.py is made explicit in naming structure so a maintainer extending
  the format vocabulary sees the LaTeX gating rule without archaeology.
- S6. R2-004: tests/l1/bookkit.sh loses the dead `local tool=` assignment and
  the duplicated `mkdir -p checkout` in the series test.
- S7. R2-005: odd/tasks/release-3.4.0.md task row T1 names the plural `formats`
  field, matching the shipped schema.
- S8. Every new rejection path is covered by a test that asserts the exact
  observable behavior through the public interface (`skelepress book --check`:
  exit code, stderr message, and no generated configuration).
- S9. Release: VERSION 3.4.1 + CHANGELOG entry covering #219 and #220 (the
  previously shipped advisory fixes R2-001/R3-003 rode 3.4.0). Full gate green
  (make gate) and PR delivery per ordinary repository policy.

## Tasks

| ID | Specs | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1-S3 | Parent inline: RED test for absolute template rejection, fix `resolve_template`, docs sentence | (fill) |
| T2 | S4, S8 | Parent inline: RED test for malformed dict entry, guard file field, catalog strings in i18n/locales/* | (fill) |
| T3 | S5 | Parent inline: build.py gating naming/structure clarification | (fill) |
| T4 | S6 | Parent inline: test cleanup in tests/l1/bookkit.sh | (fill) |
| T5 | S7 | Parent inline: feature-doc row fix in odd/tasks/release-3.4.0.md | (fill) |
| T6 | S9 | Parent inline: VERSION + CHANGELOG, make gate, PR closes #219 and #220 | (fill) |

## Log

- L1 (user request, summarized): define and close patch release 3.4.1 from
  origin/main 0e24a74 with the #219 fix (option 1: reject absolute values in
  the manifest/series template fields, naming the field and the relative-path
  rule; the flag keeps its semantics) and, in the same cycle, the #220
  cleanups R2-002, R2-003, R2-004, R2-005. Out of scope: #111 (parked until
  the exact provider-repair artifact exists, no retries) and #90 (product
  decision). The 3.4.0 release stays published; nothing reopens. Maintainer
  delegated the decision on whether #219 options 2/3 deserve separate issues.
- L2: option analysis for #219 done. Option 1 aligns with the documented
  contract (docs/books.md "path to your own template, relative to the file
  that declares it"). Options 2 (document absolute values as allowed) and 3
  (resolve against project root and reject escapes) change documented behavior
  without a product need: no separate issues warranted; noted in the PR and
  the issues are closed with the release. Option 3's intent (block escapes) is
  a consequence of option 1 plus the existence check.
- L3: T1 evidence — RED observed with the new L1 test (absolute manifest and
  series template values planned successfully, exit 0, and the generated
  configuration named `../outside/custom.tex`, escaping the checkout); GREEN
  after the fix, 6/6 new assertions plus the focused bookkit suite 79/0.
  docs/books.md and both schema descriptions now state the rejection.
- L4: T2 evidence — RED observed (the malformed entry surfaced as the
  confusing "Explicit file not found: .../None"); GREEN after the guard added
  the `file` field check with a new catalog string
  (render.error.explicit_file_missing_field) in the four locales. The renderer
  endpoint runs before the validator, so naming the field is its own duty.
