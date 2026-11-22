# Expose per-volume ordinal/label to templates (#230)

Expose each volume's position in the series to generated configuration and
templates, so consumers can print "Volume 2" without hardcoding or spending
the subtitle. Base: `e0f12b8` (origin/main after #231). Delivery: own PR, then
one release 3.5.0 bundling #111 + #230 (maintainer decision, minor bump).

## Specs

S1. Issue 230 proposal (verbatim): "Add an optional, **per-volume** field to
    `manifest.yaml`:

    - `volume` — an integer, the position of this volume in the series, or
    - `volume_label` — free text (e.g. "Volume 2", "Tome II") when the ordinal
      alone is not enough.

    Expose it to the generated configuration the same way `collection` and
    `isbn` already are (metadata), so `$volume$` / `$volume_label$` are
    available to consumer templates."
S2. Issue 230 (verbatim): "`volume` differs for every volume, so it must not
    join the inherited shared keys (a series-level default would give every
    volume the same number). It also has to be declared on the volume itself:
    a build that targets a single volume directory does not read
    `series.yaml`, so a series-only source could not be resolved there."
S3. Issue 230 optional cross-check (verbatim): "When both are available,
    validate that the declared value matches the volume's position in
    `series.yaml`'s `volumes:` list and fail with a clear message when it does
    not." Scope gate: design the validation interaction first (see L2); it
    decides whether S3 ships in this change or is split out.
S4. Issue 230 scope limit (verbatim): "`file_prefix` ... Exposing an optional
    prefix override would help consumers ..., but this is explicitly *not* the
    reason for the request — the per-volume directory layout already
    disambiguates builds." Out of scope here.
S5. Contract discipline (AGENTS.md): new manifest fields are schema changes —
    `schemas/skelepress-config.schema.json` (or the manifest-side equivalent)
    is the source of truth; mandatory preflight unchanged; new product strings
    come from the four locale catalogs; no client data in examples.

## Tasks

T1 [S1] RED: tests pinning that a volume manifest's `volume` / `volume_label`
   reach the generated configuration and the template variables the way
   `collection` and `isbn` do, including file_prefix-free behavior. Route: tbd.
T2 [S1-S3] GREEN: schema + bookkit plumbing + template exposure + (per S3
   design decision) the cross-check with its clear failure message and
   localized strings. Route: tbd.
T3 [S1-S5] docs (usage/config reference, architecture decision row) and
   CHANGELOG `[Unreleased]` entries. Route: tbd.
T4 [S1-S5] verification: focused checks; risk lines at close; commit in
   reviewable slices; native ordinary review for the candidate. Route: parent.

## Log

L1. Original request (maintainer, summarized): resume #111 for release 3.5.0;
   after #231 was merged the maintainer chose to bundle issue #230 (volume
   ordinal/label per volume) into the same 3.5.0 release. The full live issue
   body was read from GitHub (issue 230, open) and its acceptance-relevant
   text is quoted in S1-S4.
L2. Design gate noted: S3's cross-check is unproven design (stale-value risk
   vs strictness for consumers who keep manifests in separate branches);
   decide it before implementation, record the decision here.
L3. Design decisions (recorded before implementation):
   (a) Cross-check S3 ships as the issue words it: strict fail, series shape
   only, declared integer != 1-based position -> fail naming series, volume,
   declared value and expected position. Single-volume shape has no
   series.yaml, so nothing is checked there; volume_label is free text and is
   never checked. Non-breaking: the fields are new and optional and no
   existing consumer declares them.
   (b) S2 is enforced structurally, not just by convention: series.yaml's
   schema keeps additionalProperties false and does not gain volume, so a
   series-level volume key is a contract error (test pins it), and
   merge_defaults' shared tuple stays untouched.
   (c) Exposure follows collection/isbn exactly: generated config's
   document.metadata, which the renderer passes to pandoc so $volume$ and
   $volume_label$ work in any consumer template; integer volume is stringified
   (booleans excluded defensively).
   (d) Messages follow build.py's existing plain-English tool-diagnostic
   pattern; the i18n catalogs cover the CLI surface, not this tool's internals.
L4. T1/T2 implemented: RED observed (schema rejection of the not-yet-existing
   fields; 7 failures), then GREEN: suite PASS=1038 FAIL=0, make gate green.
   Committed as one work-unit slice (schema + build.py plumbing + cross-check
   + 2 test functions + registration).
