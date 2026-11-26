# Changelog

All notable changes to this toolkit are documented in this file.

The project follows semantic versioning and keeps two versioned contracts:

- `VERSION` for the toolkit version
- `skelepress.config.yaml -> version` for the configuration contract

## [3.6.0] - 2026-11-26

### Added

- `fr`, `de`, `it`, `ca`, `nl`, `da`, `nb` and `sv` as values for
  `document.language` and CLI locales: eight full message catalogs enter the
  toolkit alongside en/es/pt/gl, with the babel and EPUB language maps
  extended to match. Russian stays out for now: it needs a transliteration
  policy for slugs (Cyrillic collapses under the ASCII slug) before it can
  ship.

### Fixed

- `skelepress book` accepts `html` in a series/volume `formats` list: the
  schemas gate the vocabulary, an HTML job joins the LaTeX-switch gate (the
  generated configuration demands no TeX engine for an HTML-only volume),
  and the volume plans the self-contained reader artifact (#258).

### Added

- `html` as a third value for `output.formats`: one self-contained HTML file
  with a reader shell — sidebar table of contents with the active-chapter
  highlight, previous/next chapter pager, dark mode via the system preference
  and a print stylesheet. The artifact embeds its images as data URIs, so it
  needs nothing from the project tree; the document text is complete from the
  start, so browser search covers the whole book. There is no pagination: the
  reader navigates by chapter, the structure the three formats share.
- `output.html.reader` (default `true`): switching it off hands the document to
  Pandoc's default HTML template instead of the toolkit reader shell.
- `filters/lazy-images.lua`, always on for HTML: images are marked
  `loading="lazy"` and `decoding="async"` in the HTML target; other formats are
  unchanged.
- Reader conveniences: a full-width reading bar above sidebar and content
  with a contents-panel toggle, a chapter search box, a chapter/scroll mode
  switch (chapter mode is the default; scroll keeps one continuous document),
  a manual theme toggle that remembers the choice and the toolkit credit. The
  title sits fixed over the reading column, which widens further with the
  sidebar folded; off-screen chapters defer rendering under
  `content-visibility: auto` where the browser supports it. The mobile
  contents drawer completes navigation; all of it degrades to the wave-1
  static reader.

### Changed

- `skelepress render` help text and the localized `Output:` label now include
  the HTML target alongside PDF and EPUB. Configurations are unchanged.
- `skelepress render --formats <list>` and `skelepress doctor --formats <list>`
  override the configured `output.formats` for one invocation: a comma-separated
  list validated against the same enum, applied to the plan and to doctor's
  union-of-dependencies check, so regenerating one format no longer requires
  editing the configuration (#254).

## [3.5.3] - 2026-11-24

### Fixed

- A single-volume target inside a series (`skelepress book <series>/volume-2`)
  now joins the series contract: the parent's `series.yaml` supplies the
  volume's position, so the generated name carries the composed
  `<series-slug>-vol-<n>-` opener exactly as building the whole series
  produces, and the #230 ordinal cross-check applies. A standalone project
  (no `series.yaml` in the parent, or its parent series does not list the
  directory) keeps the title-only name (#247).

## [3.5.2] - 2026-11-24

### Fixed

- A same-chapter self-link (`](#heading)`) to a heading that the cross-chapter
  fragment resolver renames no longer dangles: the self-link follows the
  renamed explicit id like any cross-chapter link, so the EPUB validates
  (#241, regression found by EPUBCheck RSC-012 during the 3.5.1 acceptance).
  The self-link removed from `docs/user/books.md` for 3.5.1 is back.
- A bookkit project whose title carries accented Latin characters now gets
  the documented generated name: the slug transliterates (`Informe Ñandú` →
  `informe-nandu`) instead of silently dropping the accented characters
  (#243). The generated name follows the rule `docs/user/usage.md` has
  always documented.
- A **series** volume's generated file name now identifies its series:
  `<series-slug>-vol-<n>-<title-slug>` (e.g. `the-riverbank-club-vol-2-the-`
  `lantern-field-20261124.pdf`), composed from the series directory slug and
  the volume's 1-based position, so one series's artifacts sort together and
  are glob-friendly (`the-riverbank-club-vol-2-*`). Single-volume projects
  keep the title-only name, and both rules honor the transliteration above
  (#243).

### Compatibility

- The composed series prefix changes where a freshly built series volume
  writes its output: the new name replaces the title-only one and prior
  builds stay where they were. Configurations already generated (or saved)
  keep their recorded `file_prefix` and render as before; to keep a specific
  name, declare `file_prefix` explicitly. The accented-title naming change
  scopes to titles with accents for the same reason. No CLI,
  configuration-contract or schema change. Updating from 3.5.1 is recommended
  for anyone rendering EPUBs whose chapters cross-link with fragments or
  building books with accented titles or series; otherwise it can wait for
  the next scheduled update.

## [3.5.1] - 2026-11-23

### Added

- Web documentation site built with VitePress over the existing `docs/` Markdown: the guides move into `docs/user/` (install, dependencies, usage, migration) and `docs/dev/` (architecture, releasing, dependency-policy, i18n, books, brand), `docs/` stays the single source of truth, and `site/.vitepress/config.mts` holds the one canonical navigation whose order the PDF example mirrors (a test fails when web and PDF diverge). Node is a dev-only dependency: everything lives in `site/` with npm, the release artifact never carries it, and deployment is one isolated GitHub Pages workflow that does not run in the gate. The site lives at https://pablobernardo.github.io/skelepress/ and deploys on its own from `main` (#docs-site).

### Compatibility

- Documentation-only release: no toolkit behavior, CLI command, config contract or default change, and updating from 3.5.0 is **not necessary** for consumers. The configuration contract version is unchanged. Only user-visible documentation references move to their relocated paths (`docs/user/...` instead of `docs/...`): the four catalogs (`en`, `es`, `gl`, `pt`) and the installer's fallback strings now point at files that exist, nothing else changes, and no migration or configuration edit is required. Installing the documentation site does not affect the toolkit; it deploys independently from `main`.

## [3.5.0] - 2026-11-22

### Added

- Cross-chapter link fragments resolve to the target section: a link to another selected chapter with a `#heading` fragment lands on the matching heading in the PDF and the EPUB, with an explicit id derived from file and heading; a fragment naming no heading falls back to the chapter anchor with a visible localized note (#111).
- A serialized work declares which volume it is per volume: optional `volume` (integer position) and `volume_label` (free text) in a volume's `manifest.yaml` reach templates as the `$volume$` and `$volume_label$` metadata variables. `volume` is per-volume by contract — `series.yaml` may not declare it — and a series build cross-checks a declared `volume` against the volume's position in `series.yaml`'s `volumes` list, failing with a message that names the volume, the declared value and the expected position (#230).

### Fixed

- Apple Books mis-positions internal-link jumps in EPUBs built by the toolkit (blank pages until repaginating). The bundled EPUB header neutralizes the default stylesheet's forced initial-heading break with `page-break-before: avoid` instead of an explicit `auto`, which Apple Books mishandles when resolving anchors. Pandoc-only EPUBs were unaffected.

## [3.4.3] - 2026-11-22

### Fixed

- Repeated `skelepress book` builds preserve earlier artifacts. The first build
  keeps the date-only name; if a planned path is taken, all volumes and formats
  in the new build share a time suffix and, if needed, a counter (#226).

### Compatibility

- No configuration contract change. The date-only name remains the default
  when there is no collision, and saved configurations still resolve the date
  at render time. Run one build at a time per output root.

## [3.4.2] - 2026-11-21

### Fixed

- A blank `file: ""` entry in `input.explicit_files` now fails with its own
  message naming the empty value instead of reusing the missing-field error
  (#223).

### Compatibility

- No contract change: the message change affects only rejections that already
  failed before this release; a message naming the empty value replaces a
  message naming a missing field. Configurations accepted by the validator
  behave as before.

## [3.4.1] - 2026-11-21

### Fixed

- A `template` path declared in `manifest.yaml` or `series.yaml` no longer
  points outside the project through an absolute value: absolute values are
  rejected with an error naming the field and the relative-path rule, aligning
  the behavior with the documented contract ("relative to the directory
  holding the file"). The
  `--template` flag keeps its one-shot semantics for a file outside the
  checkout (#219).
- A malformed `input.explicit_files` object entry without its `file` value now
  fails naming the missing field instead of surfacing as
  `Explicit file not found: .../None` (#220).

### Compatibility

- No contract change: the rejection enforces the documented relative-path rule
  for declared templates; configurations accepted by the validator behave as
  before.

## [3.4.0] - 2026-11-20

### Added

- A volume can declare its output formats: `skelepress book` renders a PDF and
  a valid EPUB per volume in one run when the manifest or the series default
  asks for `formats: [pdf, epub]`. Values come from the formats the render
  contract already allows (`pdf`, `epub`); `[pdf]` stays the default and a
  manifest that declares nothing or only `pdf` produces exactly what it
  produced before. An unknown value fails naming the field and the accepted
  values (#163).
- Per-volume and per-series template selection: an optional `template` field in
  `manifest.yaml` and `series.yaml` picks the book template where the book
  structure lives. A bare name selects a shipped builtin; any other value is a
  path relative to the file that declares it. Precedence: `--template` flag >
  volume manifest template > series.yaml template > builtin default (#216).
- The generated configuration for a volume that renders an EPUB gates its
  LaTeX switch files (`\mainmatter`, `\appendix`, contents guards) to the PDF
  job through a new optional `{file, formats}` entry shape on
  `input.explicit_files`, so the EPUB carries no raw LaTeX markup.

### Compatibility

- The bookkit manifest contract (`manifest_version: 1`) gains two optional
  fields; the main configuration contract version stays `1`. Consumers that
  declare neither field generate byte-identical configurations to 3.3.1.
- A volume that asks only for EPUB omits `xelatex` from
  `runtime.required_commands`, so preflight no longer demands a TeX engine for
  it; `pandoc.pdf_engine` stays for PDF jobs.

## [3.3.1] - 2026-11-20

### Fixed

- Markdown strikethrough renders in all shipped book templates with Pandoc
  3.14, which emits `\st` while the templates expected `\sout`: the templates
  now load `ulem` with the existing `normalem` handling only when strikeout
  is detected (#210). The published 3.3.0 release does not include this fix.
- Mermaid diagrams in EPUB render legibly in readers whose dark mode ignores
  the document stylesheet (#112). The EPUB path bakes a light background into
  the generated diagram images by default, with a separate image-cache
  identity so nothing is reused from the transparent PDF artifacts; PDF and
  LaTeX output are unchanged. An explicit `filters.mermaid.background` in the
  configuration is honoured in every format.

### Compatibility

- The EPUB Mermaid background is default behavior of the shipped pipeline,
  visible to consumers, and non-breaking; contract version `1` is unchanged.
  Consumers who prefer transparent EPUB diagrams keep an escape hatch with
  `filters.mermaid.background: transparent`.

## [3.3.0] - 2026-11-19

### Added

- Seven selectable PDF book templates: A4 `book-novel` and `book-manual`,
  plus `book-kdp-5x8`, `book-kdp-digest` (5.5 × 8.5 in), `book-kdp-6x9`,
  `book-kdp-7x10`, and `book-kdp-square` (8.5 × 8.5 in). Select them with
  `pandoc.template` or `skelepress book --template`. The square style leaves
  running headers off unless explicitly enabled with `pandoc.running_headers`.
- A contributor acceptance check renders all seven styles and verifies page
  sizes and chapter body text. The KDP templates supply editable trim-size
  starting points, not certification for a print platform.

### Fixed

- Captionless Pandoc longtables render in the shipped book templates on TeX
  installations that expect the dummy `none` counter, without advancing the
  numbered captions.

### Compatibility

- The new styles are opt-in. Configuration contract version `1` and existing
  default template selection are unchanged.

## [3.2.0] - 2026-11-17

### Added

- `skelepress draft` renders loose Markdown files into a PDF without a
  configuration file: point it at files, and a synthesized,
  schema-validated configuration drives the same single renderer. The default
  output name is timestamped and collision-free (`skeledraft-YYYYMMDD-HHMMSS-NNNN`);
  `-t` names the document and `-o` selects an explicit output. The existing
  render flow, preflight and contract are unchanged. [Corrected 2026-11-20:
  draft has only ever accepted files; this entry overstated it.]
- Page breaks at heading boundaries. `compat.clearpage_between_heading_level`
  (optional, integer 1-6) starts a new page at every chapter whose first
  non-empty heading is at that level or shallower; naming the key subsumes the
  legacy H1 rule, and renders that do not name it keep
  `compat.legacy_clearpage_between_h1` unchanged, so existing publications are
  byte-compatible. The `{.page-break}` heading class is honoured by an always-on
  filter: `\clearpage` in LaTeX output, the class kept in HTML and EPUB where the
  shipped EPUB stylesheet exposes `break-before: page`. No raw LaTeX reaches the
  Markdown sources and no EPUB plan carries any.
- The render plan records the effective chapter-boundary decision as
  `side_effects.heading_break_level`, and the conformance expectations follow it.
- `skelepress update` confirms that the artifact matched the published checksum
  before extraction, with localized output in English, Spanish, Galician and
  Portuguese. Verification mechanics and failure messages are unchanged.
- The manual demonstrates an original consumer-owned SVG through a declared
  resource path and an opt-in Lua instruction marker with a visible **CHECK:**
  prefix. Focused EPUB checks cover image embedding and a filter-disabled control.
- Default-off `run_example_acceptance` CI input retains manual and documentation
  PDFs and page PNGs for visual inspection, without release acceptance or a
  version change.

### Compatibility

- Configuration contract version `1`, existing CLI commands/options and default
  rendering behavior remain unchanged: `compat.clearpage_between_heading_level`
  is optional, defaults to `1` (the legacy H1 rule) and is validated to 1-6;
  configurations without it behave exactly as before.

## [3.1.0] - 2026-11-07

### Added

- Optional PDF running headers through `pandoc.running_headers: true`, including
  book/series inheritance and an explicit per-volume `false` override. The shipped
  templates place bounded book and current top-level heading text above body
  pages; covers, title pages, intentional blanks and top-level openings omit the
  header. EPUB output is unaffected.
- Expanded, translated `skelepress --help` with command discovery and examples.
  `skelepress book --help` now explains its options, defaults and examples without
  changing argument forwarding or error behavior.
- Default-off CI profiles for a Pandoc-backed disposable macOS full gate and
  Ubuntu release-candidate acceptance. The latter checks real archives,
  reproducibility, isolated installation/update/rollback and retains logs plus
  PDF/PNG evidence for separate visual inspection; it never publishes a release.

### Fixed

- Rendering with omitted or false running headers no longer imports the optional
  header preflight path. The added template dependency check applies only to
  enabled PDF headers using the shipped templates.
- Header preflight handles YAML boolean aliases consistently through the shared
  Ruby fallback when PyYAML is unavailable.
- The documentation example includes its dependency reference. Affected L1
  fixtures honor caller-owned temporary roots while retaining native behavior
  when `TMPDIR` is unset or empty.

### Compatibility and dependencies

- Configuration contract version `1`, existing CLI commands/options and default
  rendering behavior remain unchanged; omitted or false running headers are inert.
- Enabled running headers in shipped PDF templates require `truncate.sty` and its
  preflight lookup. Custom templates remain responsible for their own requirements.
  Pandoc and TeX remain distribution-provided, not newly pinned. The acceptance
  profile's FreeSerif font is still optional for consumers and ordinary CI.

## [3.0.0] - 2026-11-05

### Changed — breaking

- The toolkit and repository are now **Skelepress**. The command is
  `skelepress` (`skelepress-dev` for development), configuration files generated
  by bookkit are `skelepress.config.yaml`, and the schema is
  `schemas/skelepress-config.schema.json`. The configuration structure and its
  `version` field are unchanged, as are commands, flags and rendering semantics.
- `skelepress book` defaults to `.skelepress/` instead of `.output/bookkit/`,
  relative to the invoking working directory. Per-project/per-volume layout and
  explicit `--out` overrides are unchanged; existing artifacts are not migrated.
- All `PANDOC_PDF_*` variables become `SKELEPRESS_*`. Managed installations use
  `~/.local/share/skelepress`, global locale settings use
  `~/.config/skelepress/config.env`, and project locale settings use
  `.skelepress.env`. The repository and documentation URLs use `skelepress`.
  Release assets are named `skelepress_<os>_<arch>.tar.gz`; the documentation
  skill is `skelepress-documentation`.
- This is a clean break with no migration path: no old command shim, environment
  aliases, fallback configuration loader, duplicate release assets or managed
  root adoption. Existing installations and their settings are left untouched;
  the maintainer removes them manually and installs 3.0.0 cleanly. The 2.5.2
  updater hardcodes the old artifact names and cannot update to 3.0.0. No
  compatibility upgrade from 2.5.2 is supported. Explicit `--config` paths remain
  arbitrary filenames; rendering and validation still require that flag.

## [2.5.2] - 2026-11-05

### Fixed

- Rendering no longer crashes on Python 3.9, the interpreter macOS ships
  (`/usr/bin/python3`, 3.9.6). `render-native.py` called `zip(..., strict=True)`,
  which needs Python 3.10, so a stock macOS died mid-render with
  `TypeError: zip() takes no keyword arguments`. The merge now checks the chapter
  and text counts explicitly and fails loudly with
  `render.error.chapter_count_mismatch` when they disagree, keeping the guarantee
  `strict=True` provided.

### Added

- `pandoc-pdf doctor` enforces the declared Python minimum (3.9): it probes the
  `python3` resolved from `PATH` — the interpreter the renderer actually runs
  under — and refuses an older one, naming the version found and the required
  minimum through the catalogs in `en`, `es`, `gl` and `pt`. The refusal is not
  waivable by `runtime.strict=false`. The minimum is documented in
  `docs/dependency-policy.md` and `docs/install.md`.

## [2.5.1] - 2026-11-05

### Fixed

- `pandoc-pdf update` honours `PANDOC_PDF_INSTALL_HOME` and
  `PANDOC_PDF_INSTALL_DIR`, the variables `install.sh` and `install-local.sh`
  already declare. An installation in a non-standard location no longer finds
  the updater silently writing to `~/.local/share/pandoc-pdf`. Resolution order:
  managed root `PANDOC_PDF_UPDATE_HOME` → `PANDOC_PDF_INSTALL_HOME` →
  `~/.local/share/pandoc-pdf`; binary directory `--install-dir` →
  `PANDOC_PDF_INSTALL_DIR` → the writable directory of the `pandoc-pdf` found on
  `PATH` → `~/.local/bin`, so a declared location beats the `PATH` heuristic.
  Installations that declare neither variable resolve exactly as before.
- The release packager builds its payload from the committed tree instead of the
  working copy. An untracked file inside a shipped directory no longer travels
  into the artifact, and an uncommitted edit no longer changes the hash a release
  is accepted on, so packaging the same commit yields the same bytes whoever
  builds it. The local installer still packages the working tree, which is what a
  development install exists for.
- The documentation no longer links to a repository file from inside a
  publication. `docs/usage.md` and `docs/books.md` pointed at
  `scripts/tools/bookkit/README.md` with a repository-relative path, which is a
  valid link on the web and an unresolvable resource in the EPUB, so EPUBCheck
  rejected the `documentation` publication with two `RSC-007` errors. They now use
  the public URL, and a test fails if a document listed in the documentation
  example links outside the publication again.

## [2.5.0] - 2026-11-04

### Changed

- The documentation has one page per question again for books: `docs/books.md`
  describes the whole flow — the template, `pandoc-pdf book`, the volume layout,
  the fields that shape a book, the cover image and the contents separation —
  and `docs/usage.md` points at it instead of telling half of it. The contents
  fields were documented nowhere under `docs/` until now.

### Fixed

- `make install-local` installs the **released payload**: the packager and the
  local installer now take it from one list, so a local install no longer ships
  `examples/`, `Makefile` or the repository tooling, and no longer omits
  `LICENSE` and `README.md`. It also names its directory after the release tag,
  `versions/v<version>`, matching what the network installer writes; a
  development install goes to `versions/v<version>-dev` and leaves `current`
  alone instead of taking over the stable binary of the same version.

### Added

- `bookkit` volumes accept `toc_separators`, so the contents stop reading as one
  run of front matter, chapters and appendices: `space` (the default), `rule`,
  `label` — with the words in `toc_labels` — or `none` for the previous output.
  The block is written at the two boundaries the adapter already controls and
  defines the LaTeX it uses, so a volume built with its own template compiles
  unchanged. The examples declare `label` with `Chapters` and `Appendices`, which
  leaves their page counts at 8 and 6 while the contents stops reading as one
  run of entries.

### Changed

- A `bookkit` volume no longer carries a `content/` level: `front-matter/`,
  `chapters/` and `back-matter/` sit at the volume root, beside `manifest.yaml`.
  The folder added nesting and travelled into every project that copied the
  example, without carrying meaning the manifest did not already state.
  `chapters_dir` now defaults to `chapters`; a manifest that relied on the old
  default and uses `chapters: ordered` must declare
  `chapters_dir: "content/chapters"` or move its files. The layout remains a
  convention, never validated by the tool.

## [2.4.0] - 2026-11-04

### Added

- An image cover page for the PDF. Declare `cover-image` in the metadata file or
  in `document.metadata` — the same key the EPUB path already reads, no new
  configuration field — and the shipped templates (`templates/default.tex`,
  `templates/book.tex`) print the image on a full-bleed page **before** the
  typographic title page, through a `\newgeometry`/`\restoregeometry` pair. A
  cover is not a title page: the image page prints even with `titlepage: false`.
  A relative `cover-image` resolves against `project.base_dir` in the PDF branch
  too, reusing the resolver (`relative_cover_image`) the EPUB path already had;
  documents without the key render exactly as before.
- `pandoc-pdf book`, a first-class subcommand that forwards to the shipped
  bookkit tool (`scripts/tools/bookkit/build.py`): every argument passes
  through unchanged and stdout, stderr and the exit code are exactly what
  invoking the tool directly produces. `--help` lists the command and its
  note. The `examples/book-kit/build.sh` runner is removed; the example README
  and `docs/usage.md` use the subcommand instead, and `examples/toPDF.sh`
  renders the book example through it, so one runner covers every example.
  Adding the command is free under the breaking-change policy; no
  existing command changed.
- `pandoc.top_level_division`, an optional, PDF-only field mapping one to one to
  Pandoc's own `--top-level-division` flag: `default`, `section`, `chapter` or
  `part`. Absent (or `default`), the renderer passes no flag and existing
  configurations keep Pandoc's behaviour; any other value fails in
  `validate-config` and in the renderer, naming the four valid values. `default`
  is not equivalent to `chapter`: with the `book` class, `chapter` is what
  produces chapters, while `default` lets Pandoc infer the division and does
  not guarantee it. The valid values, the error message and how a value becomes
  an argument live in one shared module
  (`scripts/runtime/top_level_division_runtime.py`), so the validator and the
  renderer cannot disagree.

### Changed

- `templates/book.tex` no longer shifts heading levels with a `\let` chain:
  top-level headings reach it as `\chapter` because the bookkit adapter now
  emits `top_level_division: chapter` in every generated book configuration.
  Chapter numbering, the table of contents and `\appendix` behaviour are
  unchanged.
- `examples/test/` is now `examples/no-titlepage/`. The old name said "fixture
  for the tests" about the example that is neither: it is the smallest valid
  configuration, and it demonstrates `document.titlepage: false`, which the new
  name states. Every configuration example now declares `output.formats: [pdf,
  epub]`, so `examples/toPDF.sh` produces the PDFs its name promises.

### Fixed

- `pandoc-pdf validate-config` no longer dies with a Python traceback on a
  machine whose `PATH` has no `ruby`: it reads through the same YAML module as
  `pandoc-pdf doctor`, which resolves Ruby from the usual install locations
  before falling back to `PATH`, and when no parser is reachable at all it
  reports the documented "No YAML parser available" error instead of crashing.

## [2.3.0] - 2026-11-04

### Added

- `pandoc.template` accepts a **builtin name** besides a path: a value with no
  separator and no dot names a template that ships with the toolkit, so a
  configuration written once works in a checkout and in an installation. `book`
  resolves to `templates/book.tex`, a `book`-class template with roman-numeral
  front matter, numbered chapters and lettered appendices. An unknown bare name
  fails naming the valid ones instead of being read as a path. The validator and
  the renderer share one rule, so both agree on what a value means.
- A bookkit entry accepts `toc: false`, so a page can print without being listed
  in the table of contents. It is the right choice for a dedication and the
  wrong one for a prologue, which is why it is a per-entry option rather than a
  rule about front matter. Listed by default.

### Changed

- `examples/book/` is gone: its template became the builtin `book`, and its
  single-volume case is covered by `examples/book-kit/single/`. `bookkit` now
  points the configurations it generates at the builtin name, so its output
  builds from an installed CLI.
- A published artifact now carries only what an installed toolkit runs:
  `scripts/runtime` and the `bookkit` tool. The repository's own tooling
  (`scripts/dev` for the documentation and catalog checks, `scripts/delivery`
  for building and installing) is no longer packaged, so an installation no
  longer looks like it carries supported developer commands.

## [2.2.0] - 2026-11-03

### Added

- Two book examples. `examples/book/` lays out a single volume with front
  matter, numbered chapters and lettered appendices through a `book`-class
  template, and `examples/book-kit/` turns a content manifest into one PDF per
  volume, including a volume whose chapters continue the previous numbering.
  The manifest and its adapter live with the book: the toolkit still receives a
  `pdf.config.yaml` and nothing else, so a change in a book format never becomes
  a toolkit contract change.

### Changed

- `scripts/` is split into `scripts/runtime` (what the renderer executes),
  `scripts/dev` (repository and CI tooling) and `scripts/delivery` (building and
  installing). The packaged artifact carries the new layout, so anything that
  called `scripts/<name>.py` or `scripts/<name>.sh` directly moves with it.
  `bin/pandoc-pdf`, the configuration contract and the default behaviour are
  unchanged, which is why this is a minor release and not a major one. The
  entrypoint file itself only follows the moved script paths: its commands,
  options, output and exit codes are untouched.

### Fixed

- Release artifacts are reproducible: packaging the same commit twice produces
  the same hash, so a published checksum can be compared with the approved
  candidate. Packaging is documented to run from a clean checkout, because the
  archive copies `templates/` wholesale.
- The documentation check only inspects files a commit could publish, so build
  output and local scratch no longer decide whether it passes or how much it
  reports covering.
- The test suite fails when a test is defined but never registered in the
  orchestrator, instead of silently dropping that coverage.

## [2.1.1] - 2026-11-02

### Fixed

- PDFs render the six ballot and warning symbols (`☐ ☑ ☒ ✅ ❌ ⚠`) in prose,
  inline code, untagged fenced code and highlighted fenced code. The shared
  template maps exactly those glyphs to GNU FreeSerif when the font exists,
  leaving the surrounding prose and mono fonts, the pdfLaTeX branch and the
  code-as-text behavior untouched; the emoji presentation selector of `⚠️` is
  consumed only right after a mapped glyph. The fallback does not depend on
  the emoji filter. Without the font — or the `newunicodechar` package —
  rendering degrades to the previous behavior and keeps the Missing-character
  diagnostics (#83).

## [2.1.0] - 2026-11-01

### Fixed

- A link between selected chapters becomes an internal anchor instead of a
  reference to a file the merged publication does not contain. It resolves in
  the PDF and in the EPUB, and a project without cross-references keeps a
  byte-identical merged document (#94).
- EPUB keeps emoji as characters inside headings. The generated navigation
  document reused them as images, which is not valid link text, with a path that
  escaped the package. Emoji in paragraph text stay images, and PDF output is
  unchanged (#94).
- Relative assets resolve from `project.base_dir` in both formats, so a content
  image or a cover declared against the project no longer breaks when the
  command runs from another directory. The project base is appended last to the
  resource path, so a declared `pandoc.resource_path` keeps its priority (#94).
- EPUB output no longer carries the generated `\clearpage` between chapters. The
  compatibility switch still applies to the PDF, which is unchanged (#94).
- EPUB tables retain table layout with visible overflow and wrapping cell text,
  instead of scrollable blocks that can interfere with reader pagination. PDF
  table styling is unchanged (#94).
- EPUB internal title pages now separate title/subtitle, credits and rights with
  relative spacing and typographic hierarchy, without changing chapter or PDF
  styling (#94).
- EPUB initial headings no longer request a redundant page break before title,
  navigation or split chapters. PDF styling and plans are unaffected (#94).
- EPUB publications now carry the configured author and respect metadata-file
  precedence for document text fields, instead of appearing as unknown author.
  The configured document language remains authoritative (#94).

### Added

- EPUB publications carry an existing cover image declared through `cover-image`
  in the metadata file, or through `document.metadata` when no file is
  configured. Nothing generates a cover, and PDF styling is unchanged (#94).
- Optional `output.formats: [pdf, epub]` selects one or both artifacts in one
  invocation. Omitted means `[pdf]`, preserving recorded PDF plans. Successful
  files remain if another format fails; the command returns nonzero. EPUB-only
  requests need no implicit TeX engine; explicit runtime requirements apply.
  This replaces the unreleased singular `format` field; see
  [migration](docs/user/migration.md). Multi-output JSON plans use version 2 (#94).
- Visible emoji compatibility samples in the ohmyfake example's heading,
  paragraph, list and table, with regression coverage for those contexts (#93).
- An optional installable Agent Skill for configuring, checking and reviewing
  PDFs from existing Markdown in consuming repositories, using the Agent Skills
  format (#86).

## [2.0.1] - 2026-10-30

The configuration contract remains at `1`; these fixes require no consumer
migration.

### Added

- A documentation-as-PDF example using the toolkit's own `docs/` as input, with
  filters disabled and a numbered table of contents (#73).

### Changed

- Documentation now separates the user-focused README from contributor CI
  instructions, removes obsolete migration and self-update guides, and updates
  the documentation PDF's reading order to cover the current guides. Removes
  unused OpenCode guidance, the duplicate operational-context summary and local
  agent skills; contributor and security guidance now have one home each.
- Installation guidance now leads with the no-clone, token-free release install
  and explains the managed layout and update path (#72).
- Release documentation clarifies that the four platform tarball names are
  aliases of one platform-independent artifact, with identical checksums (#71).

### Fixed

- L2/L3 CI rendering jobs explicitly install the template's LaTeX prerequisites,
  font metrics and SVG converter, and check declared styles before rendering.
  L3 uses the hosted image's Chrome instead of a Chromium Snap, with explicit
  browser and Mermaid HTML checks; no runtime or browser-sandbox changes.
- Configuration validation no longer requires the `compat` section or optional
  emoji/Mermaid settings. Disabled filters need only `enabled: false`; enabled
  filters can use the renderer's existing defaults (#76).
- The packaging test accepts the CLI entry with or without a `./` prefix in the
  archive listing and reports diagnostics when it is missing (#77).
- Apply code wrapping to Pandoc's actual highlighted-block environment as well as
  untagged blocks. Wrap at spaces and separators without splitting arbitrary
  letters. Inline code can wrap after `/`, `.` and `=`; long unbreakable
  identifiers can still exceed the available width.
- Disable automatic syllable hyphenation in prose so words move whole to the
  next line.
- Reserve space for H1–H5 and their following content to avoid headings stranded
  at the foot of a page, while retaining consecutive-heading protection.

### Known limits

- H6 is emitted as plain text by Pandoc's LaTeX writer and does not receive the
  H1–H5 heading protection.
- Arbitrary unbreakable content can still overflow; wrapping does not split
  every identifier or guarantee that all content fits.
- Missing Unicode glyphs remain tracked in #83; these layout fixes do not
  resolve font coverage.

## [2.0.0] - released

The first release since 1.1.3, and a major one because **defaults changed**: the
output file name, the typesetting language and the update path. Every one of them
has its section in `docs/user/migration.md`. The configuration contract version stays
at `1`: no key was removed or made stricter, so existing files keep validating.

### Added

- Three runnable examples, each covering a different branch of the contract and
  documented by what it demonstrates in `docs/usage.md`: a six-chapter narrative
  with a diagram per chapter, an operator's manual with H1 to H4, tables and
  footnotes, and the smallest valid configuration. `examples/toPDF.sh` renders all
  three and the suite validates their configs.
- `pandoc-pdf render -c <config> --dry-run` prints the render plan and writes
  nothing; `--dry-run --json` emits it as JSON (`plan_version: 1`) with the
  chapters in effective order, the targets, the pandoc `argv` and the environment.
  The plan is pure: `execute_plan` is the only place with side effects.
- `document.language` (`en`, `es`, `pt`, `gl`) selects the babel language, so the
  template no longer hardcodes one.
- `document.titlepage` disables the cover page, which used to be unconditional.
- `document.metadata` carries arbitrary Pandoc metadata (`keywords`, `subject`,
  any template variable) without a side YAML file.
- `doctor` names the detected `mermaid-cli` version when a diagram fails, next to
  the two documented fixes.
- A conformance suite over the render plan: four recorded cases compared after
  normalizing machine-local paths, runnable against another implementation through
  `PANDOC_PDF_BIN`.
- `make gate`: the suite, the catalogs, the documentation references and the plan
  conformance in one command, so a pull request can be verified without CI.
- `scripts/check-docs.py`: fails when a document points at something that does not
  exist, or when a published file contains an absolute home path.

### Changed

- The output file name is a **slug**: `output.file_prefix` when declared, a slug of
  `document.title` otherwise. It used to be the raw title, spaces and accents
  included, while `file_prefix` was required and ignored.
- The default typesetting language is **English**. It used to be Spanish, the
  language of the first consumer, which made the toolkit Spanish by omission for
  everyone else.
- `pandoc.metadata_file` and `output.file_prefix` are **optional**. Without a
  metadata file, `document.*` reaches the template; with one, the file wins as
  before.
- The five contract fields the schema already required and the runtime never read
  now take effect:
  - `input.order`: `natural` compares numeric runs as numbers (`chapter-2.md`
    before `chapter-10.md`); `alphabetical` keeps lexicographic order. Any other
    value is rejected.
  - `output.keep_merged_markdown`: `false` deletes the merged `.md` after a
    successful pandoc run and keeps it when pandoc fails, for diagnosis.
  - `document.*`: with `pandoc.metadata_file` empty, `title`, `subtitle`,
    `publisher`, `author`, `date` and `rights` reach pandoc as template variables
    (`-V field=value`) and fill the cover page `templates/default.tex` already
    expected.
  - `filters.emoji.include_ballot_icons`: `false` leaves Markdown task boxes
    (`☐`, `☑`, `☒`) as characters instead of substituting images.
  - `runtime.strict`: `false` reports missing dependencies as warnings and exits 0,
    including on the minimal YAML path used when PyYAML is absent. The TeX engine
    is never waived: without it there is no PDF, so its absence always fails.
- `pandoc-pdf locale set --project <lang>` writes `.pandoc-pdf.env` in the
  directory it runs from, and the CLI finds it by walking up, so each consuming
  repository has its own locale instead of sharing the toolkit's.
- One shell i18n runtime (`scripts/i18n.sh`) shared by `bin/pandoc-pdf` and
  `scripts/bootstrap.sh`: locale resolution and `t` are no longer duplicated and
  translating a message spawns no process. Measured on the same machine,
  `pandoc-pdf --help` went from 0.188 s to 0.080 s and from five `python3`
  processes to one. `bootstrap.sh` now also honours the language set with
  `pandoc-pdf locale set`, which it used to ignore.
- The locale error no longer suggests `--team`, an option that never existed: it
  names the real one, `pandoc-pdf locale set --project <lang>`.
- `--resource-path` is joined with the platform separator instead of a hardcoded
  `:`.
- `scripts/package-release.sh` builds the tree once and publishes the same
  artifact under the four platform names instead of packing four times.
- The updater fetches release metadata and artifacts **without credentials**, and
  says which of three things happened when it fails: no release published yet
  (404), the anonymous quota exhausted (403 or 429, 60 requests per hour per
  address), or an unreachable host. All three used to report "could not fetch
  latest release metadata" and then suggest a token.
- The toolkit is **MIT** from this version onwards (see the Legacy summary at
  the bottom for the Apache 2.0 boundary).
- The default branch is `main`.
- Documentation: an index that maps every document to the question it answers,
  `CONTRIBUTING.md` for humans, `docs/releasing.md` for the release process, and
  the numbered decisions in the `Decision record` of `docs/architecture.md`
  instead of in the state file.

### Fixed

- A dropped Mermaid diagram no longer hides behind a successful render. When
  `mmdc` is installed but cannot launch a browser, the filter records the loss and
  the render fails; `doctor` renders a test diagram and prints both remediations.
- `validate-config` silently ignored any JSON Schema keyword outside its own
  subset (`enum`, `pattern`, `$ref`…). It now implements `enum` and a test fails
  if the schema starts using an unsupported keyword.
- `input.order` is validated against its `enum` in `validate-config`, not only in
  the renderer: an unsupported value is rejected with a message naming the field,
  the allowed values and the received one.
- `validate-config` rejects a `pandoc.metadata_file` that does not exist. The
  renderer used to skip it silently, so a typo produced a PDF without the declared
  metadata and without any warning.
- `filters/emoji.lua` no longer wraps text without emojis in a `Span`. Plain
  headings stop emitting `\texorpdfstring` (a macro `hyperref` defines) and the
  filter stops breaking minimal templates.
- The emoji source that no longer exists: the Noto assets moved to `2D/svg/` and
  every download was failing silently against the fallback.

### Removed

- `PANDOC_PDF_UPDATE_TOKEN` and `GH_TOKEN` support, and with it the private-mirror
  path: `release_asset_api_url_from_json`, the API-asset upgrade on install, and
  the test that exercised it. A private mirror of the releases is no longer
  supported by this updater.
- `scripts/render-native.rb`: a single renderer remains, in Python. The duplicate
  cost 398 lines of parallel logic and existed only because the CLI picked it when
  PyYAML was missing; the renderer now parses YAML with PyYAML when available and
  otherwise delegates to Ruby's stdlib in a subprocess, the same resource
  `validate-config` already used. It only affects callers that invoked that script
  directly.
- `defaults/default.yaml`: the schema is the single source of truth. The file was
  unreachable through the validated path and only a test that bypassed the CLI
  exercised it.
- `defaults_path` / `defaults_exists` from `pandoc-pdf info` (text and `--json`),
  since the file no longer exists.
- The duplicate `filters/emoji/emoji_u{2610,2611,2612}.svg` assets, byte-identical
  to `2610.svg`, `2611.svg` and `2612.svg`, unreferenced and copied into the emoji
  directory on every run.
- `scripts/__pycache__` and `.pyc` files from the release artifact.

### Tests

- The L1 suite grew from **145 assertions to 300** and stopped being a single file:
  2,365 lines became `tests/lib.sh` with the shared assertions and fixture
  helpers plus one file per area under `tests/l1/`, with `tests/run.sh`
  orchestrating them.
- New assertions pin every behaviour above: `input.order` (both values and the
  rejected one), `output.keep_merged_markdown` on success and on pandoc failure,
  `document.*` versus `pandoc.metadata_file`, `include_ballot_icons`,
  `runtime.strict` with and without the TeX engine, `metadata_file` validation,
  the schema keyword guard, the render plan, the emoji filter in headings,
  paragraphs, table cells, captions and list items, the naming rules including
  accents and path traversal, and the three update diagnostics.
- The two Python/Ruby parity tests were retired together with the duplicate
  renderer and replaced by a structural pin: `render-native.rb` must not come
  back.
- `tests/integration/*` templates no longer carry their own copy of the template,
  so L2 exercises the real one; they also load `graphicx` and `hyperref`.
- Test-only YAML double (`tests/fixtures/yaml_shim/yaml.py`) so the Python
  renderer path can be exercised on machines without PyYAML installed.

## Legacy (pandoc-pdf 1.0.0 - 1.1.3, archived April-October 2026)

The toolkit's first stable line, published under the `pandoc-pdf` name with the
`pandoc-pdf` CLI and the Apache 2.0 license; **those releases remain Apache 2.0**
(a license is not retroactive), while everything from 2.0.0 onward is MIT. Their
tags and GitHub release assets were removed by the maintainer in 2026, so no
download path remains; this summary preserves the license fact and the version
boundary. The 2.0.0 entry below records the full breaking-change story.
