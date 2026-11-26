"""Optional WebP conversion for the HTML render.

The codec is the system binary `cwebp` (packaged by apt as `webp`, brew as
`webp`, pacman as `libwebp`, dnf/yum/apk as `libwebp-tools`; the toolkit's
`bootstrap.sh` installs it). When it is absent the HTML render degrades with
a note instead of failing; `skelepress doctor` is the surface that names the
missing capability before a render.

Conversion never mutates source images: the WebP copies land in a working
directory owned by the render, and the original paths stay as declared.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

# Sources worth converting. SVG is vector and already light; GIF may be
# animated (WebP animation is out of scope); WEBP needs no conversion.
CONVERTIBLE_SUFFIXES = {".jpg", ".jpeg", ".png"}

# Lossless for diagrams and screenshots (PNG: text edges do not survive lossy
# quantisation, and the same pixels shrink reliably), lossy for photographs.
PNG_LOSSLESS_QUALITY = 90
JPEG_QUALITY = 85


def cwebp_available() -> bool:
    """The codec is a system command; no probe run is needed to know."""
    return shutil.which("cwebp") is not None


# Inline images only: `![alt](path)` and its empty-alt form. Reference-style
# images and HTML <img> tags are rare in consumer chapters; an unconverted one
# keeps the original bytes, which is the same result as a skipped entry, and
# the render is never wrong.
_MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")


def image_targets_in_markdown(markdown: str) -> list[str]:
    """The image targets the merged markdown declares, once, in order."""
    targets: list[str] = []
    seen: set[str] = set()
    for match in _MARKDOWN_IMAGE.finditer(markdown):
        target = match.group(1).strip()
        if target and target not in seen:
            seen.add(target)
            targets.append(target)
    return targets


def _resolve_target(raw: str, base_dir: Path, resource_dirs: list[Path]) -> Path | None:
    """One declared target against pandoc's search order, or None.

    A relative target is resolved against the project base first and then the
    declared resource path entries, mirroring how the merged markdown's
    asset references resolve during the render.
    """
    stripped = raw.strip()
    if not stripped or stripped.startswith(("data:", "http://", "https://")):
        return None
    suffix = Path(stripped).suffix.lower()
    if suffix not in CONVERTIBLE_SUFFIXES:
        return None
    path = Path(stripped)
    if path.is_absolute():
        return path.resolve() if path.is_file() else None
    candidates = [base_dir / path, *(entry / path for entry in resource_dirs)]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _convert_one(source: Path, target: Path) -> None:
    """One cwebp invocation: lossless PNG, lossy JPEG at the set quality."""
    if source.suffix.lower() == ".png":
        argv = ["cwebp", "-quiet", "-lossless", "-q", str(PNG_LOSSLESS_QUALITY), str(source), "-o", str(target)]
    else:
        argv = ["cwebp", "-quiet", "-q", str(JPEG_QUALITY), str(source), "-o", str(target)]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError(detail[0] if detail else f"cwebp exited {proc.returncode}")


def convert_images_for_html(
    sources: list[str],
    work_dir: Path,
    base_dir: Path,
    resource_dirs: list[Path],
) -> tuple[dict[str, str], list[str], str | None]:
    """Convert convertible raster images the merged markdown declares.

    Returns `(mapping, skipped, capability_error)`: the mapping from
    absolute original paths (posix strings) to WebP copy paths, the targets
    deliberately not converted (each with its reason), and the capability
    error string when `cwebp` is missing (mapping and skipped are then
    empty). A missing source, an unreadable file, or a WebP encode that
    saves nothing smaller is a skipped entry, never a render failure.
    """
    if not cwebp_available():
        return {}, [], "cwebp"

    seen: set[str] = set()
    mapping: dict[str, str] = {}
    skipped: list[str] = []
    work_dir.mkdir(parents=True, exist_ok=True)

    for raw in sources:
        stripped = str(raw).strip()
        if stripped in seen:
            continue
        source = _resolve_target(stripped, base_dir, resource_dirs)
        if source is None:
            if stripped and not stripped.startswith(("data:", "http://", "https://")):
                skipped.append(f"{stripped} (skipped: not a convertible local image)")
            seen.add(stripped)
            continue
        seen.add(stripped)

        absolute = source.as_posix()
        if absolute in mapping:
            continue

        # One unique copy per source: same-stem sources must never share a target.
        digest = hashlib.sha256(absolute.encode("utf-8")).hexdigest()[:12]
        target = work_dir / f"{digest}-{source.name}.webp"
        try:
            _convert_one(source, target)
            # A copy as heavy as its source would be a regression, so it
            # stays out of the mapping and the original is embedded instead.
            if not target.is_file() or target.stat().st_size >= source.stat().st_size:
                skipped.append(f"{stripped} (webp not smaller)")
                target.unlink(missing_ok=True)
                continue
            mapping[absolute] = target.resolve().as_posix()
        except Exception as e:  # noqa: BLE001 - one bad image must not kill a render
            skipped.append(f"{stripped} ({e.__class__.__name__})")
            target.unlink(missing_ok=True)
    return mapping, skipped, None


def webp_map_environment(mapping: dict[str, str], resource_search: list[str]) -> dict[str, str]:
    """The env vars `filters/webp-image.lua` reads, only set when needed.

    The pandoc Lua environment exposes no JSON decoder, so the map travels
    as one `original<TAB>copy` pair per line: tabs and newlines cannot
    appear in a path.
    """
    if not mapping:
        return {}
    pairs = "\n".join(f"{original}\t{copy}" for original, copy in mapping.items())
    return {
        "SKELEPRESS_WEBP_MAP": pairs,
        # One resource-path entry per line, matching the pandoc argv order.
        "SKELEPRESS_WEBP_RESOURCE_PATH": "\n".join(resource_search),
    }
