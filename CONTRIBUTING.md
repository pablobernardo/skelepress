# Contributing

The toolkit produces PDFs with Pandoc for consuming repositories, so a change
usually lands in one of three places: the configuration contract, the renderer,
or the documentation a consumer reads. This page is the practical path; the
stable rules live in [`AGENTS.md`](AGENTS.md).

## Setup

```bash
git clone <your fork>
cd skelepress
make bootstrap   # pandoc, a TeX engine, mermaid-cli and the Python helpers
make test        # the whole suite
```

`make bootstrap` installs system dependencies and is slow the first time. For
everything except an actual render, `make test` needs no extra setup.

For managed local installations, the `skelepress-dev` development symlink and
bootstrap options (dry-run, non-interactive and CI), see
[development installation](docs/install.md#development-installation-from-the-repo).
`make install-release` installs the latest published release instead of the
working copy.

## Commands you will use

| Command | What it does |
| --- | --- |
| `make test` | Runs `bash tests/run.sh`, the whole suite |
| `make gate` | Everything a pull request is verified with: suite, catalogs, docs, plan conformance |
| `make validate CONFIG=path/to/skelepress.config.yaml` | Validates a configuration against the schema |
| `make doctor` | Checks the local toolchain |
| `make epubcheck FILE=path/to/publication.epub` | Validates a finished publication with EPUBCheck. Optional, needs a JVM; see [dependency policy](docs/dependency-policy.md) |
| `make install-local-dev` | Puts the working copy on `PATH` for manual testing |
| `python3 scripts/dev/check-i18n.py` | Catalog parity and placeholders |
| `python3 scripts/dev/check-docs.py` | No document points at something missing |

`make gate` is the gate: run it before opening a pull request. When CI cannot start
(an account without Actions minutes is the usual reason), it is the verification:
put its output in the pull request so the decision to merge is recorded rather
than assumed.

The suite is one process: `tests/run.sh` sources every area file under `tests/l1/`
(and, for rendering and EPUB, every file in their subject directories) and
runs them in order. There is no per-area flag, so when you touch one area, read
its file and expect the whole suite to tell you what else broke.

### Opt-in real EPUB reader proof

The isolated [Calibre/Xvfb probe](tests/acceptance/epub-reader/README.md) uses
Docker to observe the four prepared public EPUB fixtures, activate actual native
TOC items and live links, and capture paginated evidence without accessing the
host desktop. It is opt-in and
separate from the normal suite; it does not replace EPUBCheck or establish
four-publication visual acceptance by itself. See its guide for safe mounts,
sandbox prerequisites, bounded execution and evidence interpretation.

## Temporary test allocations

`new_test_tmpfile` and `new_test_tmpdir` in `tests/lib.sh` honor a nonempty
`TMPDIR` using an explicit template. Supply an existing, caller-owned absolute
root; spaces and a trailing slash are supported. An invalid root fails with
native diagnostics, without creating the root or falling back elsewhere.
Unset or empty `TMPDIR` preserves native `mktemp` / `mktemp -d` behavior.

This contract covers `new_contract_sandbox` in `tests/lib.sh` and direct shell
allocations in `tests/l1/render/native.sh`, `tests/l1/render/running-headers.sh`,
and `tests/l1/docs.sh`. It is not a global isolation guarantee: unconverted L1,
Python, and runtime allocations remain outside this scope.

## Test first

A behaviour change comes with a test that fails before it. The suite is shell,
with the assertions in `tests/lib.sh`:

- one assertion per rule the change introduces;
- for every existing command or option the change touches, one assertion that its
  previous behaviour still holds;
- observed red before the fix, green after it.

Documentation needs no behaviour test, but it must keep `check-docs.py` green.
When the guides change, regenerate the documentation PDF for visual review:

```bash
bin/skelepress render -c examples/documentation/skelepress.config.yaml
```

Running-header layout changes also need actual PDF acceptance (Pandoc, XeLaTeX
and Poppler required):

```bash
python3 tests/integration/check-running-headers.py --work .git/pdf-running-headers/review/normal
python3 tests/integration/check-running-headers.py --unbroken --work .git/pdf-running-headers/review/unbroken
```

The checker invokes public doctor/render commands and retains PDFs, per-page
PNGs, text/bbox assertions and a page-role manifest. Inspect both parities,
transitions and exceptional pages, not just extracted strings. The unbroken
stress tests header bounds; the ordinary fixture additionally checks complete
titles in title/TOC/heading content. Use `--disabled` for a default-off control;
compare same-path text and raster output against a capture made before edits.
Raw PDF hashes can differ even when text and pixels agree.

For configuration input, subprocesses or dependency changes, follow the review
guidance and trust model in [the security policy](.github/SECURITY.md).

## Messages

Never write a user-facing string in code. Add the key to **all four** catalogs in
`i18n/locales/` (`en`, `es`, `pt`, `gl`) with identical placeholders, then run
`python3 scripts/dev/check-i18n.py`. English is the wording that is written first;
the others are translations, not copies.

## Where a change belongs

| Changing | Touch |
| --- | --- |
| The configuration contract | `schemas/skelepress-config.schema.json`, then `scripts/runtime/validate-config.py`, then `tests/l1/validate.sh` |
| The CLI surface | `bin/skelepress` and its catalog keys, then `tests/l1/help.sh`, then `docs/usage.md` |
| Rendering | `scripts/runtime/render-native.py`, plus the checks in `scripts/runtime/preflight.py`; the matching file under `tests/l1/render/` |
| A filter | `filters/<name>.lua`; a failure must be loud, never silent |
| Dependencies | `scripts/delivery/bootstrap.sh`, `.github/workflows/`, `docs/dependency-policy.md` |
| A breaking change | The affected areas, an explicit migration guide when the change reaches a consumer other than the maintainer, updated examples and a `CHANGELOG.md` entry; apply the toolkit and contract version rules in `AGENTS.md` |

[`docs/README.md`](docs/README.md) maps every document to the question it answers.

## Commits and pull requests

- Branch from `main`, one branch per change.
- Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `ci:`, `refactor:`.
- Tests and documentation belong in the same commit as the behaviour.
- Keep a pull request reviewable, around 400 changed lines; beyond that, split it.
- Pull requests are squash-merged, so the commit message is the record, not the
  branch history.

## Language

The repository is written in English: code, comments, documentation, commit
messages and pull request descriptions. The only Spanish in the tree is the
message catalogs (`i18n/locales/es.json` and friends) and the example chapters,
which exist to prove that accents and punctuation render.

## Releasing

Maintainers cut versions. The gates, the commands and what CI does not exercise
are in [`docs/releasing.md`](docs/releasing.md).

## CLI tests and CI levels

`make test` runs the suite. The integration runners, which the table above does
not list because they need a fuller stack:

```bash
bash tests/l2-local.sh
bash tests/l3-local.sh
```

Notes:
- `l2-local.sh` runs semi-real integration (without the full Mermaid stack).
- `l3-local.sh` requires `mmdc` and Chromium (`PUPPETEER_EXECUTABLE_PATH` if it is not auto-detected).

The assertions under `tests/l1/` are the source of truth for suite coverage.
The suite runs automatically in GitHub Actions on Linux for every pull request
and push as **L1**. The same suite runs on macOS **weekly and on demand**, not on
every pull request: hosted macOS capacity can leave a job unacquired for fifteen
minutes and then fail it without running a single test, so it does not sit in the
path of a merge. A release candidate dispatches it and records the result.

CI levels:

- **L1 (fast, mandatory on PR/push):** `tests/run.sh` on Linux; the macOS job is
  weekly and on demand, and mandatory evidence for a release.
- **L2 (semi-real, manual):** real render on Ubuntu against integration fixtures.
- **L3 (full, manual or scheduled):** integration with the extended stack (includes the Mermaid CLI).
  - includes a real Mermaid fixture in `tests/integration/l3-mermaid-project/`.

Workflow and manual inputs:

- Workflow: `.github/workflows/ci.yml`
- `run_full_gate_macos=true` to run the [isolated full gate](#isolated-full-gate)
- `run_render_integration=true` to run **L2**
- `run_render_full=true` to run **L3**

In the GitHub UI, open **Actions → CI → Run workflow** and enable the input
for the level you need. Or run from the CLI:

```bash
gh workflow run ci.yml -f run_render_integration=true
# or
gh workflow run ci.yml -f run_render_full=true

# Watch the runs
gh run list --workflow ci.yml
gh run view --log
```

### Hosted section-link destination proof

Use `run_section_link_acceptance=true` to run the existing L3 job plus the
minimal public PDF probe in `tests/l1/render/links.sh`. This input defaults to
false and does not run release acceptance or change ordinary/release jobs.
The hosted VM additionally provisions `python3-pypdf` for artifact inspection;
consumers and the normal suite do not need that optional dependency.

```bash
gh workflow run ci.yml -f run_section_link_acceptance=true
```

The probe follows actual PDF GoTo annotations to named destinations. Its fixture
puts the requested section on a different page from the chapter introduction,
so a chapter-start destination cannot pass. Download `section-links-<head-sha>`
to inspect the PDF, render log and `destinations.json` report, including target
pages and coordinates. A successful local EPUB test does not prove this PDF path.

The PDF test is default-off and reports **SKIP**, not PASS, unless
`SKELEPRESS_SECTION_LINK_PDF=1`, Pandoc, XeLaTeX and pypdf are available. Set
`SKELEPRESS_SECTION_LINK_EVIDENCE` to a caller-owned absolute output directory
to retain its PDF/report/log. Run this opt-in only in disposable hosted VMs,
never on a shared development machine.

### Portable public CLI compatibility proof

Use `run_public_cli_acceptance=true` and `compatibility_base_ref=<ref>` on the
candidate branch to compare actual `render` (EPUB) and `book` (PDF). The existing
L3 job supplies Pandoc/TeX; no Codespace or developer-machine installation is
needed. This option defaults to false and does not select release acceptance.

```bash
gh workflow run ci.yml --ref <candidate-branch> \
  -f run_public_cli_acceptance=true -f compatibility_base_ref=<baseline-ref>
```

The workflow resolves and records both commit/tree IDs and archives only public
runtime files, never `.git`, private configuration or credentials. The portable
harness receives these prepared payloads; it does not select revisions or read
Git history. With the required rendering dependencies on a disposable runner,
its standalone interface is:

```bash
python3 tests/acceptance/render-book/compare.py base.tar candidate.tar \
  --evidence <new-external-evidence-directory>
```

Both versions run at identical paths with freshly recreated project/toolkit,
cold HOME/XDG/temp state, neutral fixtures, English messages and system PATH.
Public archives are limited to 4 MiB each and 2 MiB unpacked; scratch/evidence
mounts need at least 1 GiB free before setup. Either command failing,
a missing publication or any raw stdout/stderr/exit difference fails the check;
nothing normalizes unexpected changes away. Download `public-cli-<head-sha>` for
resolved revisions, payload hashes, raw streams/statuses and generated artifacts,
including partial failure evidence. Publication byte equality is not required;
this compatibility check does **not** inspect PDF destinations or validate EPUB
structure. Use the section-link proof above and the EPUB suite for those claims.

The ordinary Ubuntu job also runs the four tiny fake-CLI wiring tests. These
exercise isolation, evidence retention, rejection and dispatch controls without
rendering; they are not publication evidence. Run them locally with
`python3 tests/acceptance/render-book/test_compare.py -v`. Actual rendering and
PDF generation belong only on disposable hosted runners, not the shared Mac.

### Isolated full gate

For the complete `make gate` in a disposable hosted macOS VM, select the
opt-in input on the branch containing the workflow:

```bash
gh workflow run ci.yml --ref <branch> -f run_full_gate_macos=true
```

The input defaults to false and does not change the existing CI levels.
The job installs Homebrew's available Pandoc package inside the disposable VM,
then requires the executable and logs its version before running the gate.
Dependencies installed in L2/L3 or on a developer machine are not inherited by
this job. Missing Pandoc must fail preparation, not silently omit its tests.
The job uses a real Git checkout: example enumeration and packaging require
Git metadata, and packaging intentionally reads committed `HEAD`. An archive
export is not a substitute. Temporary documentation fixtures use a fresh root
outside the checkout so negative checks cannot inherit its Git index.

The isolation boundary is the whole fresh hosted VM, not just `TMPDIR`.
Native-default tests intentionally unset or empty `TMPDIR`; their allocations
and the release tests' temporary checkout edits stay inside that VM. The job
isolates home/cache directories, records the commit, tree and platform, runs
the complete gate, and requires a clean checkout afterward. It does not install
or publish a release, alter temporary-allocation contracts, or establish all
release acceptance on its own. Record the exact run, head SHA and test results;
a runner that never starts is missing evidence, not a passed check.

### Candidate acceptance without publication

For an unpublished version newer than the latest stable release, dispatch the
candidate ref with the explicit release levels and acceptance input:

```bash
gh workflow run ci.yml --ref <candidate> \
  -f run_full_gate_macos=true -f run_l1_macos=true \
  -f run_render_integration=true -f run_render_full=true \
  -f run_release_acceptance=true -f run_epub_acceptance=true
```

`run_release_acceptance` defaults to false and enables L3 when selected. Its
additional step installs PDF inspection tools and the optional symbol font,
runs the complete gate with the Ubuntu rendering toolchain, then executes
`scripts/dev/check-release-candidate.py --out <external-evidence-directory>`.
The script refuses execution outside a disposable GitHub-hosted VM. It checks
four committed archives/checksums and a second build, installs real archives,
exercises upgrade from the published stable artifact, checksum rejection and
post-version-validation rollback over a local HTTP release-API fixture, and
retains PDF/PNG smoke evidence. No candidate tag or release is created.

Download the `candidate-<commit>` Actions artifact to inspect the PDFs and
review `result.json` and the exact command logs. Successful generation does not
establish visual acceptance. The actual candidate download path can only be
checked after publication; these checks do not claim otherwise.

## Repository housekeeping

To keep the toolkit clean and reusable:

- **Do not** add local system artifacts (`.DS_Store`, etc.).
- **Do not** reintroduce legacy scripts coupled to the consumer repository.
- Always use the official entrypoint: `bin/skelepress`.
- Keep examples and docs neutral (no private data or client paths).
