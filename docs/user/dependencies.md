# Optional render dependencies

## Optional PDF layout dependencies

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
version policy remains in [dependency policy](../dev/dependency-policy.md).

See [running-header layout and page exceptions](usage.md#pdf-running-headers).

## Optional WebP image conversion

Enable `output.html.image_conversion: true` for the self-contained HTML only
when the system has the **`cwebp` codec** installed: `make bootstrap`
(`scripts/delivery/bootstrap.sh`) installs it alongside the other render
dependencies — the package is `webp` in apt and Homebrew, `libwebp` in pacman,
`libwebp-tools` in dnf/yum/apk, and the upstream binaries from Google's WebP
project cover the rest. Nothing is compiled from source.

`skelepress doctor` checks `cwebp` when the configuration enables the
option and reports the same way as any missing dependency, with the install
hint in the message. A render without the codec is not a failure: it
continues embedding the original images and says so in a localized note, so
CI cannot silently degrade a book the operator meant to ship lighter —
`doctor` is the check to trust before a release render.

See [lighter embedded images](usage.md#lighter-embedded-images-output-html-image-conversion).

