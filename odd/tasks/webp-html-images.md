# WebP image conversion for HTML output

Opt-in conversion of raster images to WebP so the self-contained HTML artifact
embeds lighter copies. Artifacts stay in English (repo policy).

## Specs

- S1: "a la hora de embeber imagenes para el html deberíamos convertir aquellas que se pueda a un formato mas liviano y con poca pérdida para leer en pantallas, tipo webp" — the HTML render must embed WebP copies of convertible raster images when the option is on.
- S2 (user decision): implementation uses Pillow ("el usuario tenga que `pip install Pillow`"), not the `cwebp` binary; no binaries added to the repo.
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
| T3 | S3, S5 | Doctor: config-gated WebP capability check in `scripts/runtime/preflight.py` | 3fe309b |
| T4 | — | i18n: new keys in all 12 locales (base `es.json`) | 3fe309b |
| T5 | S1, S5, S8 | Tests: L1 render tests for conversion, degradation, no-op; conformance expected update; i18n consistency | 454911a |
| T6 | — | Docs: `docs/user/usage.md` field documentation + `docs/dev/architecture.md` D22 + CHANGELOG Unreleased | a55932b |

## Log

- L1: "no crees que a la hora de embeber imagenes para el html deberíamos convertir aquellas que se pueda a un formato mas liviano y con poca pérdida para leer en pantallas, tipo webp ?" Original request.
- L2: Dependency question answered: Pillow recommended over `cwebp` (bundled libwebp in PyPI wheels, no system binary, single code path, fits the PyYAML→Ruby optional-dependency precedent). User accepted: "aplicalo, me parece buena idea".
- L3 (explorer evidence, `path:line`): HTML argv assembly at `scripts/runtime/render-native.py:448-473` (`--embed-resources`, lazy-images filter, `html_plan_side_effects`); merged markdown written only at execution (`merged_markdown()` defined at :875, written from `execute_single_plan` :1020-1029, pandoc run :1059); note precedent `render.error.html_template_conflict` print at :1012-1018 and degrade precedent `render.warn.emoji_prepare` at :1045-1048; doctor check shape `running_headers_need_truncate()` preflight.py:331-352; test registration `tests/run.sh:22-27` + `tests/l1/suite.sh:10-42` (defined-but-unregistered fails); i18n base is `es.json`, missing AND extra keys fail (`scripts/dev/check-i18n.py:62-94`); `output.html` schema block `schemas/skelepress-config.schema.json:92-98` keeps `reader` required; conformance expectation `tests/conformance/expected/html.plan.json:43-58` pins `side_effects.html`.
- L4 (decisions): conversion happens at execution time (plan stays pure), copies written to a temp directory, original files never mutated. PNG/JPEG/JPG → WebP (JPEG lossy q85, PNG lossless q90, skip result if larger than source); SVG/GIF/WebP untouched. Mapping handed to a new `filters/webp-image.lua` through an environment-variable map (`original<TAB>copy` lines; pandoc's Lua env has no JSON decoder) so only actual pandoc image elements get rewritten. Doctor reports the missing capability as a missing dependency only when the config enables the option. The schema no longer requires `reader` inside `output.html` (renderer already defaulted it); this relaxation keeps every previously valid config valid. Verified: `tests/run.sh` 1073 PASS / 0 FAIL with and without Pillow on PATH (56 subjective-check runs; capability-dependent cases skip explicitly). Commits: 3fe309b (feat), 454911a (test), a55932b (docs).
