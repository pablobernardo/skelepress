# #223 — Advisory triage: 3.4.1 native review findings

Small cleanup cycle closing issue #223 (three informational, non-blocking
advisories from the native review of the 3.4.1 committed range). No release
cut: the fixes travel to main and ride the next release cycle.

## Scope

- R3-001 (WARNING, CHANGELOG): the 3.4.1 release note claimed a declared
  template "can no longer point outside the project", but the implementation
  only rejects absolute values; an ../ traversal whose target exists still
  resolves outside the declaring directory. Reworded the release-note sentence
  to the implemented boundary ("no longer points outside the project through
  an absolute value"). The `docs/books.md` wording ("an absolute path is
  rejected") was already accurate and stays untouched. Extending rejection to
  escaping relative paths would be #219 option 3 territory and is out of scope.
- R2-001 (WARNING, build.py): the `emit_config` comment named
  `LATEX_ONLY_FORMAT` as the coupling marker while the check hardcoded
  `"pdf"`. Applied the issue option "use the constant":
  `pdf_requested = LATEX_ONLY_FORMAT in formats`. Behavior-neutral; the
  coupling comments at the `format_gated_entry` docstring and `emit_config`
  are now true to the code.
- R2-002 (SUGGESTION, render-native.py): a blank `file: ""` entry received the
  "missing its 'file' value" message, which names the wrong defect. Split the
  check: a non-string `file` keeps the missing-field message, a blank string
  gets the new catalog key `render.error.explicit_file_blank`
  ("Explicit file entry has an empty 'file' value: {entry}") in en/es/gl/pt.

## Verification

- Test-first for R2-002: new L1 test `run_render_blank_explicit_file_test`
  (fixture `tests/fixtures/render-blank-explicit.config.yaml`) asserted the
  new message and that the missing-field message is not reused; RED observed,
  then GREEN, with the preexisting malformed-entry test still passing (the
  split check shares its source with the unrequested behavior it guarded).
- CHANGELOG follow-up found while adding the post-release note: the 3.4.1
  release had left its section below 3.4.0, so the file was not in descending
  version order. Restored the order (3.4.1 above 3.4.0) and added the
  `[Unreleased]` section above both, after the header preamble.
- Native review of the committed 4-commit range (review-d0a31e5945bf1843,
  high tier, lenses reliability/readability, budget 110) approved and
  acknowledged. Its three advisory findings reported real candidate-caused
  slips, all verified and fixed in a follow-up commit: the catalog insertion
  also added an identical duplicate `render.error.explicit_file_missing`
  member in en/es/gl/pt (removed), and the S1 section title in the tests
  banner comment was lost when the blank-file test was inserted above it
  (restored). Focused blank/malformed/missing explicit-file tests re-run
  green after the fix, then the full gate was re-run.
- Full gate: `tests/run.sh` before and after the follow-up commit.

## Out of scope

- #90 (documentation-authoring skill evaluation) waits on the maintainer's
  product decision.
- #111 stays parked until the exact provider-repair artifact exists; no
  retries.
