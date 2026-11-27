# WebP image conversion for HTML output

Opt-in conversion of raster images to WebP so the self-contained HTML artifact
embeds lighter copies. Artifacts stay in English (repo policy).

## Specs

- S1: "a la hora de embeber imagenes para el html deberíamos convertir aquellas que se pueda a un formato mas liviano y con poca pérdida para leer en pantallas, tipo webp" — the HTML render must embed WebP copies of convertible raster images when the option is on.
- S2 (user decision, later reversed): the first implementation used Pillow; after the user hit PEP 668/venv friction and decided for a system binary, the codec is `cwebp` (L6).
- S3 (user decision): `skelepress doctor` checks WebP capability in the machine ("en cmb-editorial lo añadimos a un doctor para comprobarlo en el equipo").
- S4 (approved design): the feature is opt-in via a new optional `output.html` config field; default behavior unchanged.
- S5 (approved design): when the option is on and the capability is missing, the render degrades with a note instead of failing; doctor is the place that flags the missing capability.
- S6: PDF and EPUB output must stay unchanged; only the HTML format is affected.
- S7: configuration contract compatibility per `AGENTS.md`: optional field, contract version stays 1, no consumer migration needed.
- S8: SVG images are never converted; already-WebP images are never re-converted.

## Tasks

| ID | Specs | Route | Commit |
| --- | --- | --- | --- |
| T1 | S4, S7 | Schema: optional `output.html.image_conversion` (boolean) in `schemas/skelepress-config.schema.json`; `reader` stops being required (renderer defaults it to `true`, so every previously valid config stays valid) | 3fe309b |
| T2 | S1, S2, S5, S6, S8 | Runtime: `scripts/runtime/image_runtime.py` (capability + conversion), renderer integration (plan flag, execution-time conversion, Lua src rewrite, degrade note, conversion summary) | 3fe309b |
| T3 | S3, S5 | Doctor: config-gated WebP capability check in `scripts/runtime/preflight.py` (cwebp since L6) | 3fe309b ✅ + L6 rework pending |
| T4 | — | i18n: new keys in all 12 locales (base `es.json`) | 3fe309b |
| T5 | S1, S5, S8 | Tests: L1 render tests for conversion, degradation, no-op; conformance expected update; i18n consistency | 454911a |
| T6 | — | Docs: `docs/user/usage.md` field documentation + `docs/dev/architecture.md` D22 + CHANGELOG Unreleased | a55932b |
| T7 | S2, S5 | L6 codec swap: cwebp subprocess in image_runtime, bootstrap.sh packages, i18n install hint, docs and tests adapted | 6c78c55, dcf23dc, a8c8b7b |

## Log

- L1: "no crees que a la hora de embeber imagenes para el html deberíamos convertir aquellas que se pueda a un formato mas liviano y con poca pérdida para leer en pantallas, tipo webp ?" Original request.
- L2: Dependency question answered: Pillow recommended over `cwebp` (bundled libwebp in PyPI wheels, no system binary, single code path, fits the PyYAML→Ruby optional-dependency precedent). User accepted: "aplicalo, me parece buena idea".
- L3 (explorer evidence, `path:line`): HTML argv assembly at `scripts/runtime/render-native.py:448-473` (`--embed-resources`, lazy-images filter, `html_plan_side_effects`); merged markdown written only at execution (`merged_markdown()` defined at :875, written from `execute_single_plan` :1020-1029, pandoc run :1059); note precedent `render.error.html_template_conflict` print at :1012-1018 and degrade precedent `render.warn.emoji_prepare` at :1045-1048; doctor check shape `running_headers_need_truncate()` preflight.py:331-352; test registration `tests/run.sh:22-27` + `tests/l1/suite.sh:10-42` (defined-but-unregistered fails); i18n base is `es.json`, missing AND extra keys fail (`scripts/dev/check-i18n.py:62-94`); `output.html` schema block `schemas/skelepress-config.schema.json:92-98` keeps `reader` required; conformance expectation `tests/conformance/expected/html.plan.json:43-58` pins `side_effects.html`.
- L4 (decisions): conversion happens at execution time (plan stays pure), copies written to a temp directory, original files never mutated. PNG/JPEG/JPG → WebP (JPEG lossy q85, PNG lossless q90, skip result if larger than source); SVG/GIF/WebP untouched. Mapping handed to a new `filters/webp-image.lua` through an environment-variable map (`original<TAB>copy` lines; pandoc's Lua env has no JSON decoder) so only actual pandoc image elements get rewritten. Doctor reports the missing capability as a missing dependency only when the config enables the option. The schema no longer requires `reader` inside `output.html` (renderer already defaulted it); this relaxation keeps every previously valid config valid. Verified: `tests/run.sh` 1073 PASS / 0 FAIL with and without Pillow on PATH (56 subjective-check runs; capability-dependent cases skip explicitly). Commits: 3fe309b (feat), 454911a (test), a55932b (docs), e6b30c4 (fix: collision-proof WebP copy names).
- L5 (native review, lineage review-7a20225af8b613cb): two corroborated CRITICAL findings
  (R3-WEBP-COLLISION, R4-001): stem-named WebP copies in one shared work dir collide for
  same-stem sources and can dangle a live mapping. Bounded correction (22 diff lines of a 24-line
  plan): copies named with a sha256 digest of the resolved absolute path plus the source name;
  regression test pins two same-named images rendering two distinct WebP embeddings. Validated,
  approved and acknowledged (authority burned). Advisory-only findings recorded for later work:
  PNG_BYTES dead code (R2-001), duplicated path-resolution between image_runtime and the Lua
  filter (R2-002), console padding inside the skipped-message catalog strings (R2-003),
  capability probe in a separate interpreter (R3-WEBP-INTERPRETER), angle-bracketed destinations
  with spaces never collected (R3-WEBP-PATH-SPACES), and the converted-count summary counting
  mappings instead of verified embeddings (R4-002).
- L6 (user decision): "entonces igual es mejor utilizar cwebp no?" … "lo que esta claro es que haciendo un make install-local-dev no carga el conversor" — the codec becomes the system binary cwebp (never compiled in-tree: packaged by apt `webp`, brew `webp`, pacman `libwebp`, dnf/yum/apk `libwebp-tools`), integrated into the existing dependency installer `scripts/delivery/bootstrap.sh` rather than `install-local-dev`, which stays a payload linker.

- L7 (review resumed/resumed-paused): the cwebp-swap candidate review (lineage `review-6c5ad67896e00e8c`, tier high, 22 files/374 lines, budget 187) stopped at the reviewer collect stage on two provider-side relay failures: risk reviewer (deepseek-v4-flash) exceeded the 120000ms first-output bound; resilience reviewer (glm5.3-flash) exhausted its 49037-token output budget on reasoning with no verdict. STATUS reoffers the same 3-slot collect set (risk/resilience/reliability, revisions pinned on `sha256:dde2de30b0d795c5e43009a11e2f58d84cb1f17f97939f490cd61237d4d3a12c`). Resolution adopted by the user: restart the Pi host with a raised relay first-output bound (GENTLE_PI_REVIEW_RELAY_FIRST_OUTPUT_TIMEOUT_MS), then resume by fresh bound STATUS and captures exactly as reoffered. Delivery (push of 9 commits) stays blocked until this review resolves.
- L8 (review resumed and closed): after the Pi restart with a raised relay first-output bound, the cwebp-swap review (lineage review-6c5ad67896e00e8c) completed: 3 lens reviewers (risk/resilience/reliability) plus refuter corroborated one CRITICAL introduced finding (R3-001): the degradation test PATH still appended /usr/bin//bin, so on a Linux host with the bootstrap-installed webp package the missing-codec tests would take the available-codec path. Bounded correction (17 of 27 planned diff lines, commit 6984a70): the mock bin mirrors every executable of the runner's own PATH except cwebp and is the whole child PATH. Validated, approved, acknowledged (authority burned); suite 1073 PASS / 0 FAIL including the correction. Advisory-only follow-ups: mocked_env recurses when neither pandoc nor python3 exists (R3-002); TimeoutExpired from the new cwebp subprocess timeout is not visibly caught by the unchanged per-image guard (R4-001); which-based doctor probing accepts a non-executable cwebp file where the old in-process Pillow probe ran the codec for real (R4-002).

