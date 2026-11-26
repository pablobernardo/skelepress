# Architecture — Multi-Repository PDF Generator (Pandoc)

This document describes the toolkit **as built**. The design it originated from
was a proposal; since version 1.0.0 it is the implemented architecture, and
this file keeps it up to date with the code.

## Problem solved

The original pipeline (a local `.pandoc/` directory) worked but was coupled to
local conventions (`chapters/`, `output/`, fixed paths inside the Lua
filters). That made it hard to reuse in other repositories and to maintain at
scale.

The solution, implemented and published since v1.0.0, is a **versioned global
toolkit** with declarative configuration per consuming repository, with no
local coupling.

## Configuration contract (per repository)

Each consuming repository keeps a `skelepress.config.yaml` file. The single source of
truth for the contract is `schemas/skelepress-config.schema.json`; there is no
defaults baseline to merge. The example below mirrors
`examples/ohmyfake/skelepress.config.yaml`:

```yaml
version: 1

project:
  name: sample-project
  base_dir: .

document:
  title: "Project Technical Documentation"
  subtitle: "Compliance and Operations"
  publisher: "ACME Corp"
  author: "Engineering Team"
  date: "2026-04-21"
  rights: "Internal Use"
  language: "en"
  titlepage: true
  metadata:
    keywords: "compliance, operations"

input:
  chapters_dir: "chapters"
  glob: "*.md"
  order: natural
  explicit_files: []

output:
  dir: "output"
  # Optional: without it the name is a slug of document.title.
  file_prefix: "report"
  suffix: "${date:YYYYMMDD}"
  keep_merged_markdown: true

pandoc:
  pdf_engine: xelatex
  toc: true
  toc_depth: 2
  number_sections: true
  template: "templates/default.tex"
  metadata_file: "metadata.yaml"
  resource_path:
    - "chapters"
    - "chapters/media"
    - "output/emoji"

filters:
  emoji:
    enabled: true
    emoji_dir: "output/emoji"
    include_ballot_icons: true
  mermaid:
    enabled: true
    output_dir: "output/mermaid"
    background: transparent
  extra_lua_filters: []

runtime:
  required_commands:
    - pandoc
    - python3
    - curl
    - mmdc
  strict: true

compat:
  legacy_clearpage_between_h1: true
```

The schema requires `version`, `project`, `document`, `input`, `output`,
`pandoc`, `filters` and `runtime`. The `compat` section is optional; when absent,
`legacy_clearpage_between_h1` defaults to `true`, and
`clearpage_between_heading_level` defaults to `1` (the same H1 rule). The
optional level widens the chapter boundary to any heading level from 1 to 6,
and the always-on `filters/heading-page-break.lua` filter honours a
`{.page-break}` heading class: `\clearpage` in LaTeX, a `break-before: page`
CSS hook kept as a class in HTML and EPUB. Both keep LaTeX out of the sources
and out of every EPUB plan.

### Contract rules

1. **`version` is mandatory**, so the contract can evolve without breaking
   older repositories.
2. Paths resolve against `project.base_dir` (which itself resolves relative to
   the config file's directory).
3. If `explicit_files` is not empty, it takes priority over `glob`.
4. If `pandoc.metadata_file` is set and exists, it takes priority over the
   `document.*` fields; otherwise `document.*` values are passed as pandoc
   variables. `document.language` and `document.titlepage` are typesetting
   decisions and apply either way. A declared `cover-image` (in the metadata
   file or in `document.metadata`) is resolved against `base_dir` for both
   formats and prints as an image page before the title page, independently of
   `document.titlepage`.
5. Filters (`emoji`, `mermaid`) can be disabled per document via their
   `enabled` flags.

### Example conventions in this toolkit

- Use neutral names (`sample-project`, `ACME Corp`).
- Avoid client- or repository-specific paths and naming.
- Keep examples reproducible on any standard structure.

## Toolkit structure (as built)

```text
skelepress/
  bin/
    skelepress               # main CLI
  templates/                 # the shipped styles: nine .tex files, one EPUB header
    default.tex              # article class, the PDF default
    book.tex                 # book class, A4
    book-novel.tex           # A4 fiction layout
    book-manual.tex          # A4 technical-manual layout
    book-kdp-5x8.tex         # KDP trim-size starting points
    book-kdp-digest.tex
    book-kdp-6x9.tex
    book-kdp-7x10.tex
    book-kdp-square.tex
    epub-header.html
  filters/
    emoji.lua
    emoji/
    mermaid.lua
    heading-page-break.lua   # always on: honours the {.page-break} heading class
    inline-code-breaks.lua
  scripts/
    runtime/                 # ships: what the CLI executes
      preflight.sh
      preflight.py
      validate-config.py
      render-native.py       # the single renderer
      prepare-emojis.py
      i18n.sh
      i18n_runtime.py
      schema_runtime.py      # YAML loading and the schema subset
      template_runtime.py    # what a pandoc.template value means
      top_level_division_runtime.py  # what a pandoc.top_level_division value means
    tools/
      bookkit/               # ships: the versioned book tool
    dev/                     # repository only, never shipped
      check-i18n.py
      check-docs.py
      check-plan-conformance.py
      check-release-candidate.py
      enforce-security-thresholds.py
    delivery/                # repository only, never shipped
      bootstrap.sh
      install.sh
      install-local.sh
      package-release.sh
      payload.sh             # the one list of what an installation carries
  schemas/
    skelepress-config.schema.json
  i18n/
    locales/                 # en.json, es.json, gl.json, pt.json
    schema/
  examples/
    book-kit/                # config + series + single: the bookkit fixtures
    documentation/skelepress.config.yaml
    manual/                  # config + chapters
    no-titlepage/            # config + chapters
    ohmyfake/                # config + chapters
    render-all.sh
  docs/
    README.md                # navigation index
    index.md                 # web-site landing page (site/, VitePress)
    user/                    # using the toolkit
      install.md
      dependencies.md
      usage.md
      books.md
      migration.md
    dev/                     # maintaining the toolkit
      architecture.md
      releasing.md
      dependency-policy.md
      i18n.md
    brand/                   # logo, symbol, icons and their usage rules
  tests/
    run.sh
    l1/
    integration/
```

The nine templates are eight selectable book styles plus the article
`default.tex`; `docs/user/books.md#built-in-book-styles` says what each style is for
and what paper it targets. A style name (`book-kdp-6x9`) selects the shipped
file, a path selects a consumer-owned one; `template_runtime.py` owns both
rules.

### Principles

- **Stable core + config per repository.**
- **Semantic versioning** of the toolkit, independent of the configuration
  contract version.
- **No hardcoded paths** inside filters: every path arrives from the config,
  resolved against `project.base_dir`.
- **Explicit preflight** of dependencies before rendering (`doctor` /
  `preflight`).

## Render pipeline

There is exactly one renderer: `scripts/runtime/render-native.py`. YAML is read with
PyYAML when available and otherwise through Ruby's stdlib in a subprocess.
`validate-config` and `doctor` read through the same module,
`schema_runtime.py`, so neither can disagree with the other about which parser a
configuration needs; Ruby resolves from the usual install locations first and
from `PATH` second, which is what keeps the validator working when `PATH` is
minimal. `doctor` keeps its own minimal reader for the few keys it needs, and
uses it only when the full parser is unavailable: it is a degradation path, not
a second definition of what a configuration says.

`skelepress render -c <config>` validates the config against the schema and
renders. There is no `defaults/default.yaml` and no baseline merge: the schema
is the only source of truth, and the renderer applies only its historical
code-level fallbacks for absent keys.

`pandoc.running_headers: true` is a PDF-only opt-in in configuration version 1.
The shipped templates use the existing title and top-level heading marks in two
bounded 8pt header regions; only those repeated strings are abbreviated with
`truncate`. The book class uses chapters, the default article uses sections,
and numbered/starred headings share the exception policy documented in
[usage](../user/usage.md#pdf-running-headers). Neither template changes its default-off
layout, class or hierarchy. Consumer-owned templates implement the variable
themselves and are never rewritten; EPUB receives no header metadata.

The optional `truncate.sty` dependency is selected by one shared preflight
predicate (PDF selected, option exactly true, shipped template resolved through
`template_runtime`). Doctor includes it in its normal localized missing list;
the renderer reuses the predicate, package lookup and error surface before
execution creates output. This is a narrow guard, not a new global doctor run:
absent/false, custom templates, EPUB-only and dry-run execution are unchanged.
It is not waivable with `runtime.strict: false`. See
[dependencies](../user/dependencies.md).

`skelepress render -c <config> --dry-run [--json]` computes a pure plan
(nothing is written or created) with `plan_version: 1`, containing the
selected chapters, output targets, the exact pandoc `argv`, and the filter
environment. `scripts/runtime/render-native.py` is split into `build_plan` (pure),
`execute_plan` (the single point with side effects) and `print_plan`.

`output.formats` selects an ordered list of artifacts (default `[pdf]`),
with duplicate formats rendered once. A single unique format retains the
version-1 plan: `pandoc.target` is `{markdown, pdf}` or `{markdown, epub}`.
Multiple formats use a version-2 envelope: `{"plan_version": 2, "jobs": [...]}`.
Each job is a full version-1 single-format plan, executed sequentially by the
same renderer. Preflight checks the union of requirements. Every job is
attempted; successful artifacts survive another job's failure, the overall
exit is nonzero on any failure, and intermediate Markdown is then retained.
There is no atomic multi-file transaction. Default PDF plans remain unchanged.

EPUB jobs omit TeX/template variables, use actual document metadata with
metadata-file precedence, and keep document.language authoritative. An
EPUB-only header overrides forced page breaks on initial headings without
replacing Pandoc's default CSS or affecting PDF. An existing cover image is
supported through `cover-image` in the metadata file or `document.metadata`;
Pandoc writes the image cover and keeps its typographic title page after it.
Relative assets resolve from `project.base_dir`, which every job appends last to
the resource path, and a relative `cover-image` is resolved the same way because
the EPUB writer reads the cover directly and ignores the resource path. PDF
plans resolve the same key with the same rule (one shared resolver,
`relative_cover_image`): LaTeX does not read the pandoc resource path either, so
the renderer passes the resolved absolute path to the template, which prints the
image page before the typographic title page through a
`\newgeometry`/`\restoregeometry` pair, independently of `document.titlepage`.
No EPUB
plan carries `\clearpage`: the compatibility switch is a typesetting decision,
so it only applies to the PDF. The emoji filter keeps heading emoji as characters
in EPUB as well: the navigation document reuses headings, and a link there must
carry text. Visual Apple Books acceptance is separate from structural archive
verification. The singular `output.format` was an unreleased
prototype and is replaced, not supported as a second alias; see
[migration](../user/migration.md).

The plan is a conformance contract: four recorded cases in `tests/conformance/`
cover minimal settings, metadata precedence, explicit chapter order, and custom
templates/resources/filters. Run `python3 scripts/dev/check-plan-conformance.py` to
compare normalized plans, or add `--update` to refresh expectations after an
intentional contract change. Set `SKELEPRESS_BIN` to compare another implementation;
an optional positional root selects a different tree of cases and expectations.
Machine-local paths are normalized as documented in the checker's docstring;
object key order is ignored, but array order and all non-path values are checked.

## Future implementation migration

The frozen render plan and its conformance suite provide the comparison boundary
for any future replacement implementation. Use `SKELEPRESS_BIN` as described above
rather than defining a second rendering contract. Any migration must preserve the CLI
and configuration compatibility rules in `AGENTS.md`.

## Decision record

### Option A — Global toolkit (CHOSEN AND IMPLEMENTED)
- ✅ Better maintainability and scalability
- ✅ Upgrades controlled by version
- ⚠️ Required designing the config contract up front (done: see
  `schemas/skelepress-config.schema.json`)

### Option B — Git submodule of `.pandoc` (rejected)
- ✅ Fast to implement
- ⚠️ Operational friction in teams
- ⚠️ Less flexibility for fine-grained overrides

### Option C — Copy per repository (rejected)
- ✅ Low initial cost
- ❌ Guaranteed technical drift
- ❌ High future maintenance cost

### Decisions taken during 2.0.0

| # | Decision |
| --- | --- |
| D1 | A single renderer (Python). Ruby stays only as an optional YAML parser in a subprocess; removing it entirely would require making PyYAML mandatory, and that was decided **against**. |
| D2 | `runtime.strict: false` waives auxiliary dependencies, never the TeX engine: without an engine there is no PDF, so it always fails. |
| D3 | `validate-config` rejects a missing `pandoc.metadata_file` and validates `input.order` against its `enum`. The validator implements a documented JSON Schema subset and a test fails if the schema uses any other keyword. |
| D4 | Shell i18n unified in `scripts/runtime/i18n.sh`: catalog loaded once, no fork per message, one precedence chain for both entry points. |
| D5 | Metadata precedence: when `pandoc.metadata_file` is set it wins and no `-V` variables are passed; when empty, the `document.*` fields become template variables. |
| D6 | The plan shape (`plan_version: 1`) is frozen as is: `cwd: null` (inherited), `env` with the toolkit's four variables, and `prepare_argv[0]` as the neutral `python3` token. Any shape change requires `plan_version: 2`. |
| D7 | `defaults/default.yaml` removed: the schema is the single source of truth. |
| D8 | Release postponed during the work and cut as **2.0.0**: a major release, because the output file name, the default typesetting language and the update path changed. Creating the tag triggers `release.yml`, a path no pull request exercises. |
| D9 | The repository is English, including this file and `odd/`; only the catalogs are translated. |
| D10 | Every action is pinned to a commit SHA with its tag in a comment. Dependabot tracks the `github-actions` ecosystem weekly, so the pins do not rot; a tag is a mutable pointer, and these workflows handle the token that publishes releases. |
| D11 | `mermaid-cli` is a **tested** version, not an enforced one: 10.9.1 is what the toolkit installs and CI renders with, any other version is accepted when `doctor` renders its test diagram, and this repository never pins a user's system-wide install. See `docs/dev/dependency-policy.md`. |
| D12 | `pandoc.metadata_file` is optional: the legacy side file stays supported and wins when present, but a configuration can now carry the cover through `document.*`, plus `document.language`, `document.titlepage` and a free-form `document.metadata` map. The file name still comes from `document.title`, so no consumer's output is renamed. |
| D13 | Relative assets resolve from `project.base_dir`, never from the directory the command was invoked in. Every job appends `base_dir` **last** to the pandoc resource path, so a declared `pandoc.resource_path` keeps its priority and existing resolution is only widened. A relative `cover-image` is resolved against `base_dir` before Pandoc sees it, because neither the EPUB writer nor LaTeX's `\includegraphics` reads the resource path; both branches share the same resolver. The plan keeps `cwd: null` as D6 requires: this is a resolution rule, not a plan shape change. No EPUB plan carries the generated `\clearpage`, which is LaTeX-only markup. |
| D14 | Missing Unicode symbols in PDFs are fixed as a glyph-only, template-level fallback. In the XeLaTeX/LuaLaTeX branch, exactly the six symbols of #83 (`☐ ☑ ☒ ✅ ❌ ⚠`) are mapped to GNU FreeSerif when it exists, looked up by standard file name first (`FreeSerif.ttf`, TeX Live) and then by family name (`FreeSerif`, fontconfig/luaotfload, e.g. Debian's `fonts-freefont-ttf`). The mapping applies in prose, inline code, untagged fenced code and highlighted fenced code. The prose and code font selections, the pdfLaTeX branch and the emoji filter are untouched: code stays textual and the symbols render as monochrome FreeSerif text glyphs, not as color-emoji images, so the fallback does not depend on the emoji filter; when the filter is enabled, it substitutes SVG in prose and leaves code alone (`Code`/`CodeBlock`), so in code contexts the fallback still applies. The mapping reaches fenced code because the six characters remain active inside fancyvrb's `Verbatim`/`Highlighting` environments, so their `newunicodechar` mappings execute there too; a consuming template that neutralizes those characters inside its verbatim environments loses the mapping; `tests/integration/unicode-symbols.sh` checks this, and it is optional and not part of `make gate`. The `newunicodechar` package is guarded together with the font: a TeX installation without either degrades instead of failing. The emoji presentation selector (U+FE0F), as in the issue's `⚠️`, is consumed only immediately after a mapped glyph, never globally. PDF text extraction keeps the base symbols but not the selector (`⚠️` extracts as `⚠`), so exact Unicode-sequence copy fidelity is not claimed. Without the font, rendering degrades to the previous behavior including the Missing-character diagnostics. No configuration contract or CLI change. |
| D15 | `skelepress draft` (3.2.0) adds a configuration-free path without a second renderer: the command accepts loose Markdown files only (a directory argument is rejected), synthesizes a minimal configuration that passes the same schema and the same `validate-config` code, and hands it to `scripts/runtime/render-native.py`. Preflight, the plan shape and the contract are untouched, so a draft PDF is produced by exactly the pipeline a configured render uses. |
| D16 | Page breaks became a compatibility decision instead of a hardcoded rule. The optional `compat.clearpage_between_heading_level` (integer 1-6) starts a new page at every chapter whose first non-empty heading is at that level or shallower, and naming the key subsumes the legacy H1 rule; a render that does not name it keeps `compat.legacy_clearpage_between_h1` and stays byte-compatible. The `{.page-break}` heading class is honoured by `filters/heading-page-break.lua`, which is always on: `\clearpage` in LaTeX, the class kept in HTML and EPUB, where the shipped stylesheet exposes `break-before: page`. No raw LaTeX reaches a Markdown source or an EPUB plan, and the effective decision is recorded in the plan as `side_effects.heading_break_level`. |
| D17 | The seven selectable book styles (3.3.0) are opt-in templates, not a new contract. `book-novel`, `book-manual` and five KDP trim sizes are additional `.tex` files chosen by `pandoc.template` or `skelepress book --template`; the default template selection, `version: 1` and existing publications are unchanged, so the toolkit version moves and the contract version does not. The KDP styles are editable starting points, not print-platform certification. |
| D18 | EPUB Mermaid diagrams get a legible background (3.3.1) inside the default path, not as a new option. For EPUB/HTML output with no explicit `filters.mermaid.background` in the configuration, `filters/mermaid.lua` renders the PNG with a light background baked in, because readers such as Apple Books override the document stylesheet in dark mode and a CSS card cannot be relied on. The effective background is part of the output file name, so the PDF path and the EPUB path never share a cached image. An explicit `filters.mermaid.background` is honoured in every format, and `transparent` remains the escape hatch. This is a visible, non-breaking behavior change with contract version `1` unchanged. |
| D19 | Cross-chapter link fragments resolve to the target section (3.5.0), not by reproducing Pandoc's `auto_identifiers` algorithm, which is fragile across versions and duplicates. The target heading receives an explicit id derived from the chapter file and the heading text via the toolkit's own `slugify`, deduplicated by the renderer because Pandoc does not deduplicate explicit ids. A fragment naming no heading falls back to the chapter anchor with a visible localized note instead of pointing at nothing, and the note follows `document.language` rather than the operator's environment. Chapter-only links, fenced-code examples, non-selected paths and no-cross-reference output are unchanged. |
| D21 | The web documentation (3.6.0 candidate) is a VitePress site whose `srcDir` is the repository's `docs/` tree, so the Markdown guides stay the single source of truth and nothing is duplicated. Node is contained as a dev-only dependency: everything lives in `site/` (npm, lockfile committed, `devDependencies` only), no runtime path reads `site/`, and the release artifact never carries Node. The VitePress sidebar in `site/.vitepress/config.mts` is the one canonical reading order; the PDF example derives its `explicit_files` from it and a test fails when web and PDF diverge. Deployment is one isolated Pages workflow that never runs in the gate and never gates a release. |
| D22 | The HTML reader gains an opt-in WebP conversion (`output.html.image_conversion`, 3.6.0) so the self-contained artifact embeds lighter images: the base64 inflation of `--embed-resources` would otherwise charge every PNG screenshot a third again. The conversion runs at execution time — the plan stays pure, so `doctor`, `--plan` and conformance cases never depend on machine state — reads the merged markdown (all targets in one place), and writes WebP copies into a working directory that pandoc embeds and the render removes; source images are never mutated. PNG (screenshots, diagrams) re-encodes lossless to protect text edges; JPEG re-encodes lossy at quality 85; a copy that is not smaller, SVG, GIF and already-WebP images stay untouched. The mapping reaches `filters/webp-image.lua` through an environment variable as `original<TAB>copy` lines — pandoc's Lua environment has no JSON decoder — and normalises each target against the working directory and the declared resource path exactly as pandoc resolves them, so reference-style and raw-HTML images simply keep their original bytes instead of failing the render. Pillow is the optional codec (wheels bundle libwebp; a subprocess probe keeps import warnings out of output), `skelepress doctor` checks it only when the configuration enables the option, and a render without it degrades with a note rather than failing. Contract version stays `1`: the field is optional, default `false`, no migration. |

## How we got here

The original three-phase migration plan was executed:

1. **Harden locally** — routes in `emoji.lua` and `mermaid.lua` were
   parameterised (read from metadata/vars), emoji preparation was consolidated
   in `scripts/runtime/prepare-emojis.py`, and preflight was completed.
2. **Extract the toolkit** — scripts, filters and templates moved to this
   repository and published by tag (v1.0.0 onwards). Each consuming repository
   keeps a `skelepress.config.yaml` and invokes the toolkit through `bin/skelepress`.
3. **Reuse across repositories** — the toolkit is consumed by tag/version;
   per-repository customisation is limited to `skelepress.config.yaml` plus an
   optional template. The toolkit and configuration contract are versioned
   independently; breaking changes follow the policy in `AGENTS.md`.

## Production criteria — what must keep holding

These were the "definition of done" criteria for 1.0.0. They now act as
invariants that future changes must preserve:

- [x] A single entry point (`bin/skelepress`).
- [x] Config validated against the JSON schema (`skelepress validate-config`,
      enforced by `render` before every run).
- [x] 100% declarative paths (no hardcoded paths in scripts, filters or
      templates).
- [ ] Compatibility proven in at least two repositories with different
      structures. The test suite covers three integration fixtures with
      different structures (`tests/integration/minimal-project/`,
      `tests/integration/enabled-filters-project/`,
      `tests/integration/l3-mermaid-project/`), and this criterion is stated
      in `AGENTS.md` as a delivery criterion, but adoption by external
      consuming repositories cannot be verified from this repository alone.
- [x] Consumer installation and CLI use documented (`docs/user/install.md`,
      `docs/user/usage.md`); future breaking changes require an explicit migration
      guide under `AGENTS.md`.
