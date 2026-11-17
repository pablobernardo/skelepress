# Implement the `skelepress draft` command

Objective: one-shot PDF drafts from loose Markdown files, additive to the existing CLI.

## Specs

S1: New subcommand `skelepress draft` accepts one or more Markdown files and renders a single PDF without any configuration file. (Human: "mi idea era igual hacer un comando para borradores o impresiones rápidas de documentos md, sin indice ni nada, solo con paginación e igual un titulo que le pases por ejemplo o algo así muy simple".)

S2: Default output name is `skeledraft-YYYYMMDD-HHMM.pdf` (timestamp). (Human: "podría ser incluso draft-xxxxxxx"; later: "o skeledraft-xxxxx incluso" — resolved to skeledraft- prefix + timestamp.)

S3: `-t "Title"` sets the title manually; the output is then named from the title slug. (Human: "igual un titulo que le pases por ejemplo".)

S4: `-o /path/out.pdf` sets an explicit output path. (Issue #195 design.)

S5: No TOC, no book title page; pagination with a simple footer. (Human: "sin indice ni nada, solo con paginación".)

S6: Same single renderer underneath: the command synthesizes a minimal valid config in memory (`toc: false`, `titlepage: false`, `explicit_files`), validates it, and runs the existing `render-native.py` pipeline. No second renderer.

S7: Preflight still applies (fast automatic check; silent when fine). (Issue #195 design + AGENTS.md non-negotiable 4.)

S8: Fully additive: config-driven `render` behavior unchanged; no schema or contract changes; `version` stays mandatory in the synthesized config.

S9: User-facing strings come from the i18n catalogs (`i18n/locales/`), not hardcoded in code.

S10: Docs (`docs/usage.md`) and CLI help updated; focused L1 tests cover single file, multiple files, `-t`, `-o` and the missing-`pandoc` failure path.

## Tasks

T1 [S1-S10] Write RED L1 test for draft subcommand. Route: inline. Commit: feature slice 1.
T2 [S1-S9] Implement `draft` case in bin/skelepress with config synthesis, timestamp/slug naming, i18n strings. Route: inline. Commit: feature slice 1.
T3 [S10] GREEN: focused tests pass; bash -n, ShellCheck, YAML checks. Route: inline. Commit: feature slice 1.
T4 [S10] Update docs/usage.md and CLI help. Route: inline. Commit: feature slice 2.
T5 [S1-S10] Open PR against main WITHOUT merging; CI hosted validates (PDF generation only in hosted VMs). Route: inline. Commit: n/a (delivery).

## Log

L1 (user, verbatim): "me interesa darle prioridad al draft es posible? y lanzar ya una pr contra main antes de sacar la release para ya irlo probando en dev"
L2 (user, verbatim): "me parece bien, pero dejamos opción de ponerlo a mano también? o mejor dejarlo ya así total es un borrador podría ser incluso draft-xxxxxxx o algo así no?"
L3 (user, verbatim): "o skeledraft-xxxxx incluso" — S2 resolved: prefix skeledraft-.
L4: Issue #195 updated with skeledraft- prefix, timestamp example, -t/-o.

L5: Docs slice done. docs/usage.md gained "Quick drafts without a configuration" under CLI commands: usage examples (skeledraft-YYYYMMDD-HHMM default, -t slug naming, -o explicit path), draft-vs-book defaults (no TOC/title page/numbered sections), input resolution, mandatory preflight, additive guarantee. check-docs 83 files OK. CLI help shows the localized draft line in en/es (gl/pt via catalogs). Full suite 789/0 after docs; check-i18n OK; bash -n + ShellCheck (draft.sh clean) OK.

L6: User error report led to the real root cause: synthesized config missed schema-required sections (filters, runtime, document.title always, non-empty suffix, pandoc.toc_depth). Fixed in 6564824: complete config synthesis (emoji/mermaid disabled, runtime pandoc/xelatex/python3 strict), naming split across file_prefix+suffix (default name unchanged, -o renders <stem>-draft.pdf then renames to the exact requested path), new schema-validation regression for default/-t/-o shapes. Suite 795/0; ShellCheck bin 0 findings; docs OK; i18n 210 keys. Manual validation of all three shapes via the real validate-config.py passed.
