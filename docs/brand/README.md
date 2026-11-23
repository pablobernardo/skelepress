# Skelepress — Brand assets

Skelepress is a CLI toolkit for generating PDF documents with Pandoc, declarative configuration, and CI workflows.

## Concept

The mark combines an **S** with a **folded document**. A blue central plane suggests transformation from source material to generated output. The folded page corner connects the abstract symbol to documentation.

This is a **vector reconstruction of the approved visual direction**, not an exact vector trace of the earlier raster concept. The geometry and optical balance should be reviewed before treating it as a final trademark or production identity.

## Colors

| Role | Hex |
| --- | --- |
| Accent blue | `#3B82F6` |
| Navy | `#0F172A` |
| Pale gray | `#E2E8F0` |

## Assets

- `logo/`: horizontal wordmarks, SVG masters and transparent PNG exports.
- `symbol/`: standalone vector marks in color, white and monochrome.
- `icons/`: raster sizes and favicon formats; small sizes omit the tiny page-corner detail for legibility.
- `guidelines/`: construction artwork and overview image.

## Previews

Each asset on the background it is designed for — the white variants sit on
navy, the standard ones on pale gray. The tiles are built with inline CSS
backgrounds instead of `<img>` tags: VitePress compiles HTML image sources
as bundler imports, and the assets live outside the site's bundler root.

| Asset | Preview |
| --- | --- |
| Logo (light surfaces) | <span style="display:inline-block;width:280px;height:76px;padding:12px;background:#E2E8F0 url('/skelepress/brand/logo/skelepress-logo-dark.svg') no-repeat center/contain;border-radius:8px"></span> |
| Logo (dark surfaces) | <span style="display:inline-block;width:280px;height:76px;padding:12px;background:#0F172A url('/skelepress/brand/logo/skelepress-logo-white.svg') no-repeat center/contain;border-radius:8px"></span> |
| Symbol (color) | <span style="display:inline-block;width:66px;height:84px;padding:10px;background:url('/skelepress/brand/symbol/skelepress-symbol.svg') no-repeat center/contain;border-radius:8px"></span> |
| Symbol (white) | <span style="display:inline-block;width:66px;height:84px;padding:10px;background:#0F172A url('/skelepress/brand/symbol/skelepress-symbol-white.svg') no-repeat center/contain;border-radius:8px"></span> |
| Symbol (mono) | <span style="display:inline-block;width:66px;height:84px;padding:10px;background:#E2E8F0 url('/skelepress/brand/symbol/skelepress-symbol-mono.svg') no-repeat center/contain;border-radius:8px"></span> |
| Favicon sizes | <span style="display:inline-block;width:48px;height:62px;padding:6px;background:url('/skelepress/brand/icons/icon-64.png') no-repeat center/contain"></span> <span style="display:inline-block;width:40px;height:52px;padding:6px;background:url('/skelepress/brand/icons/icon-32.png') no-repeat center/contain"></span> <span style="display:inline-block;width:34px;height:46px;padding:6px;background:url('/skelepress/brand/icons/icon-16.png') no-repeat center/contain"></span> |
| Construction | <span style="display:inline-block;width:200px;height:110px;padding:8px;background:url('/skelepress/brand/guidelines/construction.svg') no-repeat center/contain;border-radius:8px"></span> |

The raster icons carry their own transparent canvas, so no background tint is
applied to them.

## Usage

- Prefer SVG for web, documentation and scalable graphics.
- Use the standard logo on light backgrounds and the white logo on dark backgrounds.
- Keep clear space around the symbol of at least one quarter of its width.
- Do not stretch, rotate, recolor individual facets or add shadows.
- Test the symbol at actual favicon sizes before shipping.

## Typography and portability

The SVG wordmark uses the font stack `DejaVu Sans, Arial, sans-serif`. Text is **not converted to outlines**; appearance can vary where the font is unavailable. The PNG is a fixed reference rendering. For a final cross-platform identity, select and license a typeface, then outline the wordmark in a vector editor.

## Source of truth

The SVG files are the editable masters. PNG and ICO files are derived outputs. Keep exports synchronized when changing geometry.

## Suggested repository README usage

```html
<p align="center">
  <img v-pre src="docs/brand/logo/skelepress-logo.svg" alt="Skelepress" width="360">
</p>
```
