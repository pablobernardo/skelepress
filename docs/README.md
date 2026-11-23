# Documentation

One page per question. If you are not sure where to start, read the two rows
marked with an arrow. These pages are also published as a documentation site:
`site/` builds them with VitePress, and the sidebar in
`site/.vitepress/config.mts` is the one canonical reading order — the PDF
example in `examples/documentation/` derives its order from that same list.

## Using the toolkit (`docs/user/`)

| Document | Answers |
| --- | --- |
| → [`user/install.md`](user/install.md) | How do I install it, and which system dependencies does it need? |
| [`user/dependencies.md`](user/dependencies.md) | Which optional PDF layout features need additional dependencies? |
| → [`user/usage.md`](user/usage.md) | How do I configure a repository, run the commands and wire it into CI? |
| [`user/books.md`](user/books.md) | How do I build a book: the template, manifests, `skelepress book`, the cover and the contents. |
| [`user/migration.md`](user/migration.md) | What a consuming repository has to do when a toolkit version changes. |

## Maintaining the toolkit (`docs/dev/`)

| Document | Answers |
| --- | --- |
| [`dev/architecture.md`](dev/architecture.md) | Why is it built this way, what does the render pipeline do, and which decisions were taken? |
| [`dev/releasing.md`](dev/releasing.md) | How is a version cut, published and verified? |
| [`dev/dependency-policy.md`](dev/dependency-policy.md) | Which versions are pinned, how are they updated, and why is the Mermaid CLI different? |
| [`dev/i18n.md`](dev/i18n.md) | How do the catalogs, the keys and the two runtimes fit together? |

## Brand assets (`docs/brand/`)

| Document | Answers |
| --- | --- |
| [`brand/README.md`](brand/README.md) | Brand assets: logo, symbol and icons, with their palette and usage rules. |

## Outside `docs/`

| File | For |
| --- | --- |
| [`../README.md`](../README.md) | What the project is, and the shortest path to a first PDF. |
| [`../AGENTS.md`](../AGENTS.md) | The stable rules: contract, compatibility, language policy, where to change what. |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | How to set up, test and submit a change. |
| [`../CHANGELOG.md`](../CHANGELOG.md) | What changed in each version. A record, not current documentation. |
| [`../.github/SECURITY.md`](../.github/SECURITY.md) | How to report a vulnerability. |

Pending work lives in issues; verification evidence belongs in pull requests.
The repository is written in English. Keep guides aligned with actual behaviour
rather than appending status reports.
`python3 scripts/dev/check-docs.py` fails the suite if a reference points at
something that no longer exists.
