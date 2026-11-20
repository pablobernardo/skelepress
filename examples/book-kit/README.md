# Book kit example

One tool, two book shapes. This example proves that a single-volume book
and a multi-volume series are the same pattern: a series is a book with more
than one volume, and both render through the same public `skelepress` CLI
with the same template, the same configuration shape and the same shipped
tool.

The model itself is documented once, not here: the shipped tool's reference
([`scripts/tools/bookkit/README.md`](https://github.com/pablobernardo/skelepress/blob/main/scripts/tools/bookkit/README.md))
is the contract — what a book project and a volume are, the folder
convention, the entry rules and the generated mode files — and
[`docs/books.md`](../../docs/books.md) is the narrative. This page says what
this example demonstrates and how to run it.

## Run it

```bash
skelepress book --out ../.output/book-kit single series
```

The command above runs from this directory and writes everything into
`../.output/book-kit/` (gitignored): one `skelepress.config.yaml` per volume, the
generated mode files, and one PDF per volume. From any other working
directory, pass the project paths and `--out` as you would to the tool
itself — the subcommand forwards them unchanged.

## What this example demonstrates

- **Both project shapes.** `single/` is a directory with a `manifest.yaml` and
  no `series.yaml`: the project directory *is* the volume, so its manifest
  carries every field — `subtitle`, `isbn`, `collection`, `audience` and the
  rest — with no defaults to merge. `series/` declares the shared facts and an
  ordered `volumes` list in `series.yaml`, and each volume manifest overrides
  only what it needs.
- **Numbering that continues across volumes.** `series/volume-2` declares
  `chapter_start: 4`, so its chapters print as Chapter 4 and Chapter 5 instead
  of restarting at 1. Each volume stays an independent PDF: the continuity is a
  typesetting decision the tool implements, not state the toolkit keeps.
- **The volume-root folder convention.** The volumes use `front-matter/`,
  `chapters/` and `back-matter/` beside the manifest, with no `content/` level.
  The manifests name every file, so this is the documented convention and not
  something the tool validates.
- **Markers kept out of the prose.** `\mainmatter`, `\appendix` and
  `\setcounter{chapter}{N-1}` are generated into the run output, so the content
  files carry no LaTeX markers and stay PDF/EPUB-neutral prose.

### The three entry rules

Exercised here, not just described:

| Entry rule | Where this example exercises it |
| --- | --- |
| A declared entry whose printable file is missing **fails** the build, naming the volume, the logical name and the path. | No manifest here breaks on purpose; the rule and its exact message are in the tool's reference. |
| An `optional: true` entry whose file is missing is **skipped with a warning** and the volume still renders. | `series/volume-2` declares its excerpt entry `optional` and the file deliberately does not exist. |
| A `print: false` entry is excluded **silently**. | `series/volume-1` ships a real review-request page in `back-matter/` that the build leaves out. |

## Files

- `single/` — a single-volume project without `series.yaml`.
- `series/` — a two-volume project with `series.yaml`; `volume-2` continues
  the chapter numbering of `volume-1` with `chapter_start`.
- `single/manifest.yaml`, `series/series.yaml`,
  `series/volume-*/manifest.yaml` — content-only manifests; edit these,
  never the generated configuration.

## Requirements

The same as any `skelepress` render (`pandoc`, a TeX engine, `python3`).
The tool reuses the toolkit's own YAML loader: PyYAML when importable,
otherwise Ruby's stdlib YAML through a subprocess — exactly like the
toolkit's own fallback. Without either, the tool fails with a clear
message.
