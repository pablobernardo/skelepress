# Migration guides

What a consuming repository has to act on when the toolkit version changes,
newest first. Configuration contract `version: 1` is unchanged in every section
here, so a validated configuration never has to be rewritten for a migration.

## 3.3.1 — EPUB Mermaid background default

EPUB and HTML renders bake a light background into the generated Mermaid images
by default, so diagrams stay legible in readers whose dark mode ignores the
document stylesheet. PDF output keeps the transparent image, and an explicit
`filters.mermaid.background` is honoured in every format.

A project that prefers transparent diagrams in its EPUB sets the value itself:

```yaml
filters:
  mermaid:
    background: transparent
```

This is a visible, non-breaking change in default behaviour: it changes how
shipped diagrams look, not what a configuration has to declare.

## 3.0.0 — clean break from pandoc-pdf

3.0.0 replaced the `pandoc-pdf` toolkit identity and its managed installation
layout with `skelepress`. There is no in-place upgrade from 2.5.2: no old
command shim, no environment-variable alias, no fallback configuration loader
and no duplicate release assets. The 2.5.2 updater hardcodes the old artifact
names and cannot reach 3.0.0.

Install 3.x as described in [docs/user/install.md](install.md), then remove the old
2.5.2 managed installation by hand; the new installation leaves it untouched.
Configuration contract `version: 1` is unchanged, and `skelepress.config.yaml`
remains the generated configuration file name.

## 2.1.0 — EPUB output and asset resolution

2.1.0 adds EPUB output and changes where relative assets are resolved. Published
2.0.1 configurations need no edits: `output.formats` is optional, omitting it
keeps the PDF behaviour, and configuration contract `version: 1` is unchanged.

### EPUB output

`output.formats: [epub]` produces an EPUB3 publication. It carries an existing
cover image declared through `cover-image` in the metadata file or in
`document.metadata`, embeds emoji and Mermaid resources, keeps cross-references
between chapters working as internal anchors — including a link fragment, which
lands on the target section rather than the chapter start — and drops LaTeX-only
markup such as the generated `\clearpage`. Nothing generates a cover, and PDF
output is unchanged.

### Relative assets resolve from the project base

`project.base_dir` is now appended last to the Pandoc resource path, so a
relative image or cover resolves regardless of the directory the command runs
from; a declared `pandoc.resource_path` keeps its priority, so anything that
resolved before still resolves. A project that relied on being invoked from a
particular directory should either run from the project base or declare that
entry explicitly.

### If you used the prototype format key

The singular `output.format` was a prototype on `main` and never shipped in a
release. If you used it, replace it. Before:

```yaml
output:
  format: epub
```

After (retain the other output fields):

```yaml
output:
  formats: [epub]
```

Use `formats: [pdf, epub]` to produce both in declared order, or omit the field
for the unchanged PDF default. An empty list, an unknown format, or the old
singular key fails validation before rendering. Duplicate formats run once.
Configuration contract `version: 1` is unchanged.

Multi-output is not transactional: preflight checks all requirements first;
after it passes, each format is attempted. A failed format causes exit 1,
successful files remain, and merged Markdown is retained for diagnosis.

### Integrations reading JSON plans

A single unique format retains the version-1 plan. A multi-format request
returns a version-2 envelope with ordered `jobs`, each a version-1 plan.
Check `plan_version` before reading the top-level `pandoc` object. No CLI
flags have changed. Existing PDF-only integrations keep their recorded plans.
