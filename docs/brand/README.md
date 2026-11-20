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
  <img src="docs/brand/logo/skelepress-logo.svg" alt="Skelepress" width="360">
</p>
```
