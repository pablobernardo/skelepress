# Documentation site with VitePress (#docs-site)

A web documentation site (user + developer manuals) built with VitePress over
the existing `docs/` Markdown, without duplicating content and without shipping
Node into the toolkit artifact. Base: `main` at `6e805a2` (post-3.5.0, v1.x
legacy pruned). Deliverable: one PR; release unaffected (docs-only feature).

## Specs

S1. Maintainer decision (verbatim intent): the maintainer wants a **VitePress**
    site — "no crees que es más elegante vitepress aunque nos meta dependencia
    de node?" — with the toolkit's dependency cost **contained**: Node is
    dev-only (maintainer + docs CI), never shipped in the release tarball, and
    recorded in `docs/dependency-policy.md` as such.
S2. Layout (agreed): a self-contained `site/` directory holding `package.json`
    (vitepress + build scripts) and `.vitepress/config.mts`; its `srcDir`
    points at the existing `docs/`, so **`docs/*.md` remain the single source
    of truth** — no content duplication. Content is organized into `/user/`
    (install, usage, migration, dependencies) and `/dev/` (architecture,
    releasing, i18n, books, brand), with `index.md` as a landing page offering
    both entries. Do not create two separate sites.
S3. Single canonical navigation: the VitePress `sidebar` in
    `site/.vitepress/config.mts` is the one canonical reading order. The PDF
    example `examples/documentation/skelepress.config.yaml` must derive its
    `explicit_files` order from that same list, and the existing test that
    fails when a doc under `docs/` is missing from the reading order must be
    extended to assert that the site sidebar and the PDF reading order agree
    (web and PDF must never diverge).
S4. Deployment: one isolated workflow (`docs.yml` or similar) that installs,
    builds and publishes to GitHub Pages on push to `main`. It must not run in
    the gate and must not gate the release.
S5. Docs hygiene (repo rules): every new/changed doc sentence stays in
    English; `docs/dependency-policy.md` gains the Node/VitePress entry
    (dev-only, versions, rationale); `docs/architecture.md` gains one decision
    row recording the docs-site decision and its containment; CHANGELOG
    `[Unreleased]` gets the feature entry.

## Tasks

T1 [S2,S3] Scaffold `site/` (package.json, config.mts with user/dev sidebar,
    srcDir), landing page, and the docs reorganization into `user/`/`dev/`
    (git mv, update internal links, keep docs/README.md navigation accurate).
    Route: inline.
T2 [S3] Derive `examples/documentation/skelepress.config.yaml` order from the
    sidebar; extend the reading-order test to pin sidebar ↔ PDF order
    agreement. RED first. Route: inline.
T3 [S1,S5] `docs/dependency-policy.md` Node entry (dev-only), architecture
    decision row, CHANGELOG entry. Route: inline.
T4 [S4] `docs.yml` Pages workflow; verify a manual run builds and publishes;
    confirm the gate and release workflows are untouched. Route: inline.
T5 [S1-S5] Verification: `make gate` green; `pnpm build` clean; visual check
    of the built site locally (user and dev sections, search); native review
    per RDD; PR, merge, Pages deployment verified live. Route: parent.

## Log

L1. Origin (this session, maintainer dialogue): after publishing 3.5.0 and
    pruning the v1.x legacy, the maintainer asked whether VitePress would
    provide a user + developer manual. Assessment: existing docs are ~2200
    lines across 11 guides with a reading-order test and a PDF example that
    dogfoods skelepress; VitePress adds web navigation/search without
    duplicating content. The maintainer confirmed VitePress despite the Node
    dependency ("más elegante"), accepted the containment design (`site/`
    dev-only), and asked for a clean-session prompt to start it.
L2. Design constraints carried from the maintainer dialogue: no content
    duplication (`docs/` stays canonical); one canonical nav list shared by
    web and PDF (S3); Node never in the shipped artifact (S1); one isolated
    deploy workflow (S4); package manager choice (npm/pnpm) is an
    implementation decision for T1 — pick one and record the choice in
    `docs/dependency-policy.md`.
