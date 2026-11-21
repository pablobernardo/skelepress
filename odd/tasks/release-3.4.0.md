# Release 3.4.0 — bookkit declarative surface (#163 + #216)

A minor release grouping two issues that extend the bookkit manifest contract.
Both add optional, per-overridable fields to `series.yaml` / `manifest.yaml` and
share schema + validator + `build.py`.

## Specs

Requirements come from open issues #163 and #216 (public issue text) and the
maintainer's session brief: one contract change, schema first, then `build.py`,
then CLI/bookkit, then tests and docs.

- S1 (Issue #163): "A `formats` field accepted where the volume's output is
  decided — on the volume, and on the series defaults so a whole series can say
  it once."
- S2 (Issue #163): "Values drawn from the formats the contract already allows,
  so no new vocabulary is invented; `[pdf]` stays the default so nothing changes
  for existing manifests."
- S3 (Issue #163): "bookkit writes that list into the generated configuration
  and passes it through the existing render call. No second renderer, no
  parallel code path."
- S4 (Issue #163): "A manifest that asks for EPUB must not silently receive only
  a PDF: an unknown or unsupported format fails with a message naming the field
  and the accepted values."
- S5 (Issue #163): "An EPUB volume needs no TeX engine, and the generated
  configuration should not make the preflight demand one for it."
- S6 (Issue #163, acceptance): "A book project declaring both formats produces a
  PDF and an EPUB per volume in one run, and the EPUB is valid: EPUBCheck clean
  on the shipped examples."
- S7 (Issue #163, acceptance): "A manifest declaring only `pdf`, or declaring
  nothing, produces exactly what it produces today — proven by a differential
  against the current behaviour." (Out of scope: series-level single EPUB,
  EPUB-only books that skip the PDF, changes to the PDF pipeline.)
- S8 (Issue #163, acceptance): "The generated configuration keeps being
  canonical text, so a `--check` run and a real run agree."
- S9 (Issue #163, acceptance): "Tests and `docs/books.md` alongside the
  behaviour, in the same change." + "Unknown formats fail through the catalogs
  in `en`, `es`, `gl` and `pt`." (The message source is the bookkit tool's
  `die()` f-strings, following the toc_separators precedent; the catalogs cover
  the CLI help surface.)
- S10 (Issue #216): Add optional `template` field to both `series.yaml` (series
  default) and `manifest.yaml` (per-volume override).
- S11 (Issue #216, precedence verbatim): "--template flag > manifest.yaml
  template > series.yaml template > builtin default ("book")"
- S12 (Issue #216): "A value that is a bare name (no separator, no dot) resolves
  to a shipped builtin template, exactly like the flag does today." Any other
  value is a path relative to the directory holding `series.yaml` (for the
  series default) / the volume's `manifest.yaml` (for the volume override),
  validated at plan-construction time.
- S13 (Contract decision, session brief): Both fields are additive optional properties on the existing bookkit schemas: `manifest_version` stays
  `enum: [1]`; no new contract version. The main `skelepress-config.schema.json` gains one additive optional form: `input.explicit_files` items may
  be an object `{file, formats}` (string form unchanged), so LaTeX-only generated files can be gated to formats without a parallel code path.
  Main config `version: 1` stays.
- S14 (Session brief / #163): Build order — schema change first, then
  `build.py`, then CLI/bookkit surface, then tests and docs
  (`docs/books.md`, `docs/usage.md`, `scripts/tools/bookkit/README.md`).
- S15 (Release): `VERSION` 3.4.0 + `CHANGELOG.md` entry. Out of scope for this
  session's work units: #111 (parked) and #90 (product decision pending). Tag
  and publication only on explicit maintainer order.

## Tasks

| ID | Specs | Route | Commit |
| --- | --- | --- | --- |
| T1 | S13, S10, S1-S2 | Parent inline: schema fields (`formats`, `template`) in `series.schema.json` + `manifest.schema.json`; main schema `explicit_files` object form | (fill) |
| T2 | S3-S5, S8, S10-S12 | Parent inline: renderer `select_chapter_files` per-format gating; `build.py` plan construction (`merge_defaults` shared tuple gains `template`/`formats`), template resolution, format-aware `emit_config` (mode files gated to `pdf` when EPUB is requested) | (fill) |
| T3 | S4, S12 | Parent inline: error surface (die messages naming field and accepted values; catalogs only if any help/user surface changes) | (fill) |
| T4 | S6, S7, S8 | Parent inline: L1 tests in `tests/l1/bookkit.sh` (+ epub fixtures where applicable), sway/differential for declared-nothing path | (fill) |
| T5 | S9, S14 | Writer or inline: docs — `docs/books.md`, `docs/usage.md`, `scripts/tools/bookkit/README.md` (PDF-only sentence at README 168-170 must not go stale) | (this change, uncommitted) |
| T6 | S15 | Parent inline: release prep — `VERSION` 3.3.1 -> 3.4.0, `CHANGELOG.md` | (this change, release-prep commit) |
| T7 | S15 | Parent inline: publication per `docs/releasing.md` (tag + release only on explicit maintainer order) | (fill) |

## Log

- L1 (session brief): New session for skelepress from origin/main 75f58a9.
  Goal: define and launch the minor release 3.4.0 grouping issues #163
  (bookkit: a volume declares its output formats, book as EPUB) and #216
  (per-volume/per-series template via series.yaml/manifest.yaml). Both touch
  the same declarative bookkit surface (schema + validate-config + build.py);
  treat them as one contract scope: schema first (contract version 1 intact if
  nothing breaks), then build.py, then CLI/bookkit, then tests and docs.
  Before any code: review #216 (proposal of precedence manifest > series) and
  the current schema; evaluate whether the two fields fit one contract change
  or whether #163 needs a new contract version. Out of scope: #111 (parked
  until the exact provider-repair artifact exists, no retries), #90 (pending
  product decision). 3.3.1 is published and verified; nothing of that release
  reopens.
- L2 (exploration evidence, main 75f58a9): Explorer verified `formats` is
  hardcoded at `build.py:530` with `pdf_engine: xelatex` at :534 and
  `required_commands` including xelatex at :563-567; preflight gates TeX on
  `FORMAT_PDF in output_formats` (`preflight.py:413`) but engine checks skip
  only under `needs_tex` (:435-441), so an EPUB volume must drop xelatex from
  `required_commands`. `--template` resolves at `build.py:648-659` (bare name
  pass-through, path -> resolve + is_file + die); unknown bare names are caught
  later by `validate-config.py:81-99`. Series defaults propagate only through
  the closed `shared` tuple at `build.py:351-360` (volume wins over series).
  Mode files contain raw LaTeX (`build.py:404-431`), and the README states the
  rendered document is PDF-only (`scripts/tools/bookkit/README.md:168-170`):
  EPUB-by-mode-file conditioning is part of implementing #163, not a scope
  extension, and the PDF path must stay byte-identical (S7).
- L3 (contract decision): Both fields fit one additive contract change under
  `manifest_version: 1` — optional properties, `additionalProperties: false`
  schemas only widen acceptance for new content, existing manifests validate
  unchanged, and the bookkit manifest version is documented as independent of
  both toolkit VERSION and the main config contract version. No contract
  version bump; main schema untouched.
- L4 (implementation decisions, agent-owned): `formats` accepts a non-empty
  list drawn from the renderer's accepted values (`pdf`, `epub`); an unknown
  value fails a plan-construction time with a message naming the field and the
  accepted values. Precedence for `template` follows S11 verbatim. EPUB-only
  (no `pdf`) stays out of scope per S7: what happens when a volume asks only
  EPUB is decided during T2 and pinned by tests either way; no silent TeX
  demand is ever generated.
- L5 (design decision, evidence from main 75f58a9): The renderer merges one
  Markdown document per format (`build_plan` -> `build_single_plan` per format,
  `render-native.py:200-208`, `:261`) and establishes the principle "an EPUB
  plan carries no LaTeX-only markup" (`render-native.py:285-293`). bookkit's
  generated mode files hold raw LaTeX (`\mainmatter`, `\appendix`,
  `\setcounter`, separator blocks with `\protect\vspace`), so relying on
  pandoc silently dropping raw LaTeX in EPUB would leak markup and contradict
  the established principle. Decision: `input.explicit_files` items gain an
  optional object form `{file, formats}` (main schema, additive, version 1
  unchanged); `select_chapter_files` filters per format; bookkit emits its mode
  files as `formats: [pdf]`-gated entries only when the volume requests format
  values beyond `pdf`, and keeps string entries otherwise so declared-nothing
  and declared-`[pdf]` manifests produce byte-identical generated configs
  (S7). `required_commands` drops `xelatex` when `pdf` is not requested (S5).
  An `[epub]`-only volume is not part of the advertised scope (S7 out-of-scope
  line) but flows through the same paths without a demand for TeX.
- L6 (T5, documentation): The three user-facing docs now describe the shipped
  behaviour of commit 0f10ea9. `scripts/tools/bookkit/README.md` gains `formats`
  and `template` rows in both field tables, replaces the stale PDF-only
  sentence in "How the mode files work" with the format-gated
  `input.explicit_files` shape, extends the `--template` section with the two
  declared forms, their per-file path bases and the precedence order, and notes
  the TeX consequence in Requirements. `docs/books.md` gains the two field rows
  plus "Producing a PDF, an EPUB, or both" and "Choosing the template", each
  with config examples. `docs/usage.md` mentions the fields in the Books
  section and states in `output.formats` that a bookkit volume's `formats` is
  what the generated configuration declares. Verification is grep-based: there
  is no docs runner, and the wording avoids any EPUBCheck claim, which stays
  with the separate S6 acceptance item and is not yet run.
- L7 (S6 acceptance, evidence): EPUBCheck acceptance run against the shipped
  examples rendered through the real bookkit flow. Copies of
  examples/book-kit/single and examples/book-kit/series in a temp run
  directory, each declaring formats: [pdf, epub] (manifest for single,
  series.yaml default for the series); skelepress book rendered all 3 volumes
  in one run, each producing a PDF and an EPUB. EPUBCheck (local binary) on
  all 3 EPUBs: 0 fatal errors, 0 errors, 0 warnings, 0 hints. S6 covered.
- L9 (advisory fixes, pre-merge): Two of the six #220 advisories fixed as
  test-only changes before the merge: R2-001 (the volume-b xelatex assertion
  now anchors on the runtime list form, not pdf_engine) and R3-003 (new
  series-path fixture proves an inherited series template path resolves
  against the series directory). Gate 924 PASS / 0 FAIL. The remaining four
  advisories (R2-002, R2-003, R2-004, R2-005) stay in #220.
