# Optional PDF layout dependencies

Enable `pandoc.running_headers: true` for the shipped default or book PDF
template only when the TeX toolchain provides **`truncate.sty`** and
**`kpsewhich`**. The `truncate` package bounds repeated header text without
shrinking it below the fixed 8pt header size, including a single long word.
It does not shorten source titles, contents entries or body text.

Check the selected toolchain before rendering:

```bash
skelepress doctor -c skelepress.config.yaml
```

Doctor probes `kpsewhich truncate.sty`. A missing lookup tool, unsuccessful
lookup or empty result is reported through the localized missing-dependency
list as `truncate.sty`. Actual render performs the same narrow dependency guard
before it creates merged Markdown or invokes Pandoc. `runtime.strict: false`
cannot waive a package needed by the selected layout. No tool installs a
package automatically.

The extra dependency is **not** required for omitted/false `running_headers`,
EPUB-only output, or a consumer-owned template, which may implement the variable
without `truncate`. Dry-run plans do not probe the package. Explicit paths to
the actual shipped templates use the same requirement as their built-in form;
a copied consumer template remains consumer-owned.

TeX Live and other distributions can provide the package through their normal
package management. Follow the distribution's documentation if it is missing;
the toolkit does not change a host installation. The broader installation and
version policy remains in [dependency policy](dependency-policy.md).

See [running-header layout and page exceptions](usage.md#pdf-running-headers).
