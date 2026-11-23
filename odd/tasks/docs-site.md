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

T1 [S2,S3] done; route: inline; commit `351603a`. docs/ split into user/ and dev/
    (git mv, all live cross-references updated: README, AGENTS, CONTRIBUTING,
    SECURITY, example READMEs, i18n catalogs, suite tests, CHANGELOG links),
    site/ scaffolded (package.json, config.mts with the canonical sidebar,
    srcDir ../docs), docs/index.md landing, coverage test extended to nested
    guides. Full suite 1039/0.
T2 [S3] done; route: inline; commit `5c86ea5`; RED first: books.md sat fourth
    in the PDF order but last in the sidebar (assertion failed with the exact
    diff), GREEN after mirroring the sidebar order in the example. Full suite
    1040/0.
T3 [S1,S5] done; route: inline; commit `8762940`. dependency-policy Node entry
    (dev-only, npm chosen and recorded, vitepress@1.6.3 exact), decision row
    D21, CHANGELOG [Unreleased] entry.
T4 [S4] done; route: inline; commit `8a5039d`. docs.yml isolated Pages workflow
    (paths-filtered, not in the gate, does not touch ci.yml/release.yml),
    actions pinned to full SHAs, npm ci, build, deploy. Site build verified
    locally: 12 pages, local search present, preview serving 200 for landing,
    /user/ and /dev/.
T5 [S1-S5] done; route: parent. Gate green (1040 PASS, exit 0) before push.
    Native review per work-unit slice (the whole branch exceeded the reviewer
    context budget; split per provider stop): slice A approved after a
    deterministic correction (srcDir ../../docs -> ../docs, validated by a
    targeted validator); slice B approved (advisories only); slice C passive
    (docs-only, structural readback); one intermediate candidate stopped
    escalated (unknown causality; the refuter probe is unavailable on this
    host) and was not retried — its actionable findings became the hardening
    commit `6c7c143` (Pages permissions scoped to the deploy job, prepreview
    hook, ignoreDeadLinks comment) reviewed as a new candidate D'; that review
    caught a real deterministic blocker (lockfile out of sync with the exact
    1.6.3 pin, npm ci would fail) corrected in `d0ff4ab` and validated; final
    state approved with authority burned. PR opened; merge and live Pages
    verification follow ordinary repository policy per maintainer instruction.

## Log

L1. Origin (this session, maintainer dialogue): after publishing 3.5.0 and
    pruning the v1.x legacy, the maintainer asked whether VitePress would
    provide a user + developer manual. Assessment: existing docs are ~2200
    lines across 11 guides with a reading-order test and a PDF example that
    dogfoods skelepress; VitePress adds web navigation/search without
    duplicating content. The maintainer confirmed VitePress despite the Node
    dependency ("más elegante"), accepted the containment design (`site/`
    dev-only), and asked for a clean-session prompt to start it.
L2. T1 execution evidence: the plan normally resolves chapters as absolute
    paths, so `explicit_files` entries are relative to `input.chapters_dir`
    (`user/install.md`, not `docs/user/install.md`); the suite failed with
    doubled `docs/docs/` paths before the example was fixed. The npm option
    name is `srcExclude` (singular); `srcExcludes` silently ignores the list.
    VitePress resolves page sources outside the npm root with no visible
    node_modules, so `site/scripts/ensure-docs-link.mjs` creates a relative
    symlink `docs/node_modules -> ../site/node_modules` before every
    dev/build/preview run; `docs/node_modules` and site build output are
    gitignored. npm resolves `^1.6.3` to vitepress 1.6.4: after pinning the
    exact version the lockfile had to be regenerated, which the native review
    caught as a deterministic blocker. yamllint only honors inline
    `# yamllint disable-line` (a `disable-next-line` on its own line inside a
    step failed for this version); the two Pages actions use it because the
    full SHA pin exceeds the line budget.
L5. Post-merge maintainer review round (two commits, `d6883eb` and `7d61027`):
    brand returned to `docs/brand/` (identity surface, not a dev-manual page;
    raw-HTML image references the move had broken point at real files again),
    books moved to `docs/user/` between usage and migration (RED observed in
    the sidebar-PDF test, then GREEN — the example's explicit_files followed
    the canonical order as designed), the site gained the navbar logo, hero
    logo and a Brand nav entry at the clean /brand/ URL (rewrites: VitePress
    renders a directory README.md as README.html), and brand assets serve
    through a refreshed copy under docs/public/brand because VitePress 1.6.x
    copies static assets only from srcDir/public and ignores a configured
    publicDir. Gate 1040/0 before each push; live site re-verified (brand
    page, logo and favicon all HTTP 200).
L4. Delivery evidence: PR #239 merged into main at `7e03fc4` after remote CI
    green (L1 ubuntu, security scans; manual L2/L3 skipped as designed). The
    first Pages run failed at deploy (404) because Pages was not enabled with
    the GitHub Actions source; enabled with `build_type=workflow` via the API
    and the deploy rerun green. Live site verified at
    https://pablobernardo.github.io/skelepress/ (HTTP 200 on the landing,
    /user/install.html and /dev/architecture.html, hero content present).
L3. Review evidence: the branch-wide candidate exceeded the native reviewer
    context budget (81 files), so review ran per work-unit slice in detached
    worktrees. Findings applied as ordinary engineering: Pages/id-token
    permissions moved from workflow level to the deploy job (the build job
    must never hold deployment credentials), checkout runs with
    `persist-credentials: false` matching the ci.yml convention, prepreview
    hook added, ignoreDeadLinks comment states the regex is wide. Advisories
    left as follow-ups: dangling-symlink handling in ensure-docs-link
    (existsSync follows symlinks and the EEXIST fallthrough reports before
    the script's own message), the shared docs-path normalization helper in
    tests/l1/docs.sh, and the duplicated canonical-order prose between the
    config comment and docs/README.md.
