#!/usr/bin/env python3
"""Public-CLI PDF acceptance; retain page/position evidence for visual review.

Run with --work pointing to an excluded evidence directory. --disabled captures
legacy output without applying the enabled-layout assertions (also useful for
same-path, before/after pixel comparisons). No git history or private API used.
Requires pandoc, xelatex and Poppler's pdftotext/pdftoppm.
"""
import argparse
import json
import os
import struct
import subprocess
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/running-headers/pages.md"
MARKERS = {
    "FrontBeforeHeading": "front", "FrontContinuation": "front",
    "OpeningFirst": "opening-first", "OpeningSecond": "opening-second",
    "BodyFirstOdd": "first-body", "BodyFirstEven": "first-body",
    "BodySecondOdd": "second-body", "BodySecondEven": "second-body",
}


def run(argv, cwd, env, log=None):
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=180)
    if log:
        log.with_suffix(".stdout").write_bytes(result.stdout)
        log.with_suffix(".stderr").write_bytes(result.stderr)
        log.with_suffix(".exit").write_text(str(result.returncode) + "\n")
    assert result.returncode == 0, (argv, result.returncode, result.stdout, result.stderr)
    return result.stdout


def cover_png(path):
    """A neutral, generated cover; no image library or external assets needed."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = b"".join(b"\0" + bytes([38, 76, 94]) * 120 for _ in range(170))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">2I5B", 120, 170, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def check_pdf(case, pdf, template, title, first, second, enabled, unbroken, env):
    layout = run(["pdftotext", "-layout", str(pdf), "-"], case, env).decode()
    (case / "pages.txt").write_text(layout)
    bbox = run(["pdftotext", "-bbox", str(pdf), "-"], case, env)
    (case / "bbox.html").write_bytes(bbox)
    # Trusted local Poppler output from our own fixture, not an input XML file.
    pages = ET.fromstring(bbox).findall(".//{*}page")  # noqa: S314
    threshold = 58 if template == "book" else 45
    manifest = []
    found = set()
    content = {}
    for number, page in enumerate(pages, 1):
        words = [(w.text or "", float(w.attrib["xMin"]), float(w.attrib["yMin"]),
                  float(w.attrib["xMax"]), float(w.attrib["yMax"]))
                 for w in page.findall(".//{*}word")]
        header = [w for w in words if w[2] < threshold]
        body_text = " ".join(w[0] for w in words if threshold <= w[2] < 790)
        raster = run(["pdftoppm", "-f", str(number), "-l", str(number), "-r", "72",
                      "-gray", "-singlefile", str(pdf)], case, env)
        # Poppler emits binary PGM without comment lines. Inspect image content
        # rather than assuming a cover/title page number (TeX can insert blanks).
        magic, size, maximum, pixels = raster.split(b"\n", 3)
        assert magic == b"P5" and maximum == b"255"
        width, height = map(int, size.split())
        role = next((role for marker, role in MARKERS.items() if marker in body_text), None)
        if role:
            found.update(marker for marker in MARKERS if marker in body_text)
        elif "Contents" in body_text:
            role = "contents"
        elif not body_text and sum(v < 180 for v in pixels) > width * height / 2:
            role = "cover"
        elif body_text:
            role = "title"
        else:
            role = "intentional-blank"
        content.setdefault(role, []).append(body_text)
        png = case / f"page-{number:02}.png"
        run(["pdftoppm", "-f", str(number), "-l", str(number), "-scale-to", "1100",
             "-singlefile", "-png", str(pdf), str(png.with_suffix(""))], case, env)
        entry = {"page": number, "physical_parity": "odd" if number % 2 else "even",
                 "role": role, "png": str(png), "header_words": header}
        manifest.append(entry)
        # Write incrementally so a genuine RED still leaves useful evidence.
        (case / "page-roles.json").write_text(json.dumps(manifest, indent=2) + "\n")
        if not enabled:
            continue
        if role in ("first-body", "second-body", "front"):
            left = [w for w in header if w[1] < float(page.attrib["width"]) / 2]
            right = [w for w in header if w[1] >= float(page.attrib["width"]) / 2]
            assert left, (case.name, number, role, "missing book-title header", header)
            assert title.startswith(left[0][0].rstrip(".…")), (title, left)
            if role == "front":
                assert not right, ("chapter side must be empty before first heading", right)
            else:
                current = first if role == "first-body" else second
                assert right and current.startswith(right[0][0].rstrip(".…")), (current, right)
                right_text = " ".join(w[0] for w in right)
                assert "Subordinate" not in right_text, ("subheading replaced chapter", right)
                if role == "second-body":
                    assert first.split()[0] not in right_text, ("previous chapter leaked", right)
            assert max(w[3] for w in left) < float(page.attrib["width"]) / 2 - 5, header
            assert all(w[3] <= float(page.attrib["width"]) - 50 for w in right), header
            assert all(6 <= w[4] - w[2] <= 12 for w in header), ("legibility", header)
            assert "…" in " ".join(w[0] for w in left), ("long book title not abbreviated", left)
            if role != "front":
                assert "…" in " ".join(w[0] for w in right), ("long chapter not abbreviated", right)
            body = [w for w in words if w not in header and w[2] < 790]
            assert not body or max(w[4] for w in header) + 8 < min(w[2] for w in body), words
        else:
            assert not header, (case.name, number, role, "exception must have no header", header)
        # Detect an unwanted header rule from actual raster pixels, not text.
        if role not in ("cover", "title") and role not in ("first-body", "second-body", "front"):
            for y in range(15, threshold + 7):
                row = pixels[y * width:(y + 1) * width]
                assert sum(value < 180 for value in row) < width * .5, (role, "header rule", y)
        if role == "intentional-blank":
            assert not words, ("intentional blank is not empty", words)
        elif role not in ("cover", "title"):
            assert any(w[0].isalnum() and w[2] > 750 for w in words), ("missing preserved footer", role)
    assert found == set(MARKERS), ("missing fixture pages", found)
    assert all(role in content for role in ("cover", "title", "contents", "intentional-blank")), content
    if enabled:
        for role in ("first-body", "second-body"):
            assert {p["physical_parity"] for p in manifest if p["role"] == role} == {"odd", "even"}
        # Ordinary long titles must remain complete in each relevant content
        # region, not merely somewhere else in the PDF. The unbroken stress
        # isolates HEADER overflow: legacy title/heading typography can clip a
        # single synthetic word (confirmed with a disabled pixel-identical control).
        if not unbroken:
            for role, texts in (("title", (title,)), ("contents", (first, second)),
                                ("opening-first", (first,)), ("opening-second", (second,))):
                full_text = " ".join(" ".join(content[role]).split())
                for text in texts:
                    assert text in full_text, ("full title missing from content", role, text)
    (case / "assertions.json").write_text(json.dumps({"passed": True, "enabled": enabled,
                                                     "pages": len(pages), "unbroken_header_stress": unbroken,
                                                     "full_content_titles_checked": enabled and not unbroken}, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--disabled", action="store_true")
    parser.add_argument("--unbroken", action="store_true")
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    home, tmp = work / "home", work / "tmp"
    home.mkdir(exist_ok=True)
    tmp.mkdir(exist_ok=True)
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home), TMPDIR=str(tmp),
               PYTHONDONTWRITEBYTECODE="1", SKELEPRESS_LANG="en", SOURCE_DATE_EPOCH="1700000000",
               FORCE_SOURCE_DATE="1", SKELEPRESS_PROJECT_ENV=str(work / "no-project-env"))
    all_roles = {}
    for template in ("book", "default"):
        case = work / template
        case.mkdir(exist_ok=True)
        title = "Atlas of Quiet Observations Across the Many Distant Islands and Their Changing Seasons"
        first = "First Passage Through the Northern Archipelago and Its Many Extraordinary Harbours"
        second = "Second Passage Beyond the Southern Horizon and Its Remarkable Constellations"
        if args.unbroken:
            title = "mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm"
            first = "nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn"
        text = FIXTURE.read_text().replace("@MAIN@", r"\mainmatter" if template == "book" else "")
        text = text.replace("@FIRST@", first).replace("@SECOND@", second)
        (case / "pages.md").write_text(text)
        cover_png(case / "cover.png")
        (case / "metadata.json").write_text(json.dumps({"title": title, "cover-image": "cover.png"}))
        config = {
            "version": 1, "project": {"name": "running-header-review", "base_dir": "."},
            "document": {"title": "Ignored configuration title", "language": "en", "titlepage": True},
            "input": {"chapters_dir": ".", "glob": "*.md", "order": "natural", "explicit_files": ["pages.md"]},
            "output": {"dir": ".", "file_prefix": "headers", "suffix": "review", "keep_merged_markdown": True},
            "pandoc": {"pdf_engine": "xelatex", "toc": True, "toc_depth": 2, "number_sections": True,
                       "metadata_file": "metadata.json", "resource_path": ["."]},
            "filters": {"emoji": {"enabled": False}, "mermaid": {"enabled": False}, "extra_lua_filters": []},
            "runtime": {"required_commands": ["pandoc", "xelatex"], "strict": True},
            "compat": {"legacy_clearpage_between_h1": False},
        }
        if template == "book":
            config["pandoc"].update(template="book", top_level_division="chapter")
        if not args.disabled:
            config["pandoc"]["running_headers"] = True
        config_path = case / "config.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        # Public doctor checks the configured toolchain; render independently
        # guards its opt-in layout dependency before creating any output.
        run([str(ROOT / "bin/skelepress"), "doctor", "-c", str(config_path)], case, env, case / "doctor")
        run([str(ROOT / "bin/skelepress"), "render", "-c", str(config_path)], case, env, case / "render")
        pdf = case / "headers-review.pdf"
        all_roles[template] = check_pdf(case, pdf, template, title, first, second,
                                        not args.disabled, args.unbroken, env)
    (work / "page-roles.json").write_text(json.dumps(all_roles, indent=2) + "\n")
    print(f"PASS: both shipped templates; PDF, PNG, bbox and page roles in {work}")


if __name__ == "__main__":
    main()
