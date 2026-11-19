#!/usr/bin/env python3
"""Book styles acceptance (#179): every builtin style renders multipage and
distinct, and each style carries its promised paper.

Run with --work pointing to an excluded evidence directory. Requires pandoc,
xelatex and Poppler's pdftotext. No git history or private API used.
"""
import argparse
import hashlib
import json
import re
import subprocess
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STYLES = {
    # name: (expected paper points, what the style promises)
    "book-novel": ("595.28 841.89", "A4 reading typography"),
    "book-manual": ("595.28 841.89", "A4 dense manual typography"),
    "book-kdp-5x8": ("360 576", "KDP pocket trim, 5x8in"),
    "book-kdp-digest": ("396 612", "KDP digest trim, 5.5x8.5in"),
    "book-kdp-6x9": ("432 648", "KDP standard trim, 6x9in"),
    "book-kdp-7x10": ("504 720", "KDP large trim, 7x10in"),
    "book-kdp-square": ("612 612", "KDP square trim, 8.5x8.5in"),
}
CHAPTERS = 4
# PDF engines can round the same trim size differently (e.g. 595.276 vs 595.28).
PAPER_TOLERANCE_PT = Decimal("0.01")


def run(argv, log=None):
    result = subprocess.run(argv, capture_output=True, timeout=300)
    if log:
        log.with_suffix(".stdout").write_bytes(result.stdout)
        log.with_suffix(".stderr").write_bytes(result.stderr)
        log.with_suffix(".exit").write_text(str(result.returncode) + "\n")
    assert result.returncode == 0, (argv, result.returncode, result.stdout, result.stderr)
    return result.stdout


def page_sizes(pdf: Path, work: Path) -> set[tuple[Decimal, Decimal]]:
    """Page widths and heights in points from the public Poppler bbox output."""
    xml = run(["pdftotext", "-bbox", str(pdf), "-"], work / "pdftotext-bbox").decode()
    return {
        (Decimal(width), Decimal(height))
        for width, height in re.findall(r'<page width="([\d.]+)" height="([\d.]+)"', xml)
    }


def chapter_body_marker(chapter: int) -> str:
    # A unique plain-text token that survives layout and cannot appear in the TOC.
    return f"735021{chapter}490586"


def check_style(work: Path, cli: Path, style: str, expected: str, promise: str) -> dict:
    case = work / style
    case.mkdir(parents=True)
    chapters = case / "chapters"
    chapters.mkdir()
    # A representative multipage book: enough prose per chapter to spill over
    # one page, plus the features every style must support.
    for i in range(1, CHAPTERS + 1):
        body = " ".join(
            f"Paragraph {j} of chapter {i} keeps the style's rhythm and stays "
            "legible across pages with a reasonably long line of prose."
            for j in range(40)
        )
        (chapters / f"{i:02d}-chapter.md").write_text(
            f"# Chapter {i}\n\n{chapter_body_marker(i)}\n\n{body}"
            f"\n\n## Section {i}.1\n\n{textwrap_body(body)}\n",
            encoding="utf-8",
        )
    config = case / "skelepress.config.yaml"
    config.write_text(
        "version: 1\n\nproject:\n  name: style-check\n  base_dir: .\n"
        + "document:\n  title: Book Style Check\n  language: en\n"
        + "input:\n  chapters_dir: chapters\n  glob: '*.md'\n"
        + "  order: natural\n  explicit_files:\n"
        + "".join(f"    - '{i:02d}-chapter.md'\n" for i in range(1, CHAPTERS + 1))
        + "output:\n  dir: output\n  file_prefix: style-check\n"
        + "  suffix: check\n  keep_merged_markdown: true\n"
        + "pandoc:\n  pdf_engine: xelatex\n  toc: true\n  toc_depth: 2\n"
        + "  number_sections: true\n  metadata_file: ''\n"
        + "  resource_path:\n    - chapters\n"
        + f"  template: {style}\n  top_level_division: chapter\n"
        + "filters:\n  emoji:\n    enabled: false\n"
        + "    emoji_dir: output/emoji\n    include_ballot_icons: true\n"
        + "  mermaid:\n    enabled: false\n    output_dir: output/mermaid\n"
        + "    background: transparent\n  extra_lua_filters: []\n"
        + "runtime:\n  required_commands:\n    - pandoc\n    - xelatex\n"
        + "  strict: true\n"
        + "compat:\n  legacy_clearpage_between_h1: true\n",
        encoding="utf-8",
    )

    run([str(cli), "validate-config", "-c", str(config)], case / "validate")
    run([str(cli), "render", "-c", str(config)], case / "render")
    pdfs = list((case / "output").glob("*.pdf"))
    assert pdfs, f"{style}: the render produced no PDF"
    pdf = pdfs[0]

    layout = run(["pdftotext", str(pdf), "-"], case / "pdftotext").decode()
    (case / "pages.txt").write_text(layout)
    pages = layout.count("\f")
    assert pages >= CHAPTERS, f"{style}: expected at least {CHAPTERS} pages, got {pages}"
    for i in range(1, CHAPTERS + 1):
        assert f"Chapter {i}" in layout, f"{style}: chapter {i} missing from the output"
        if chapter_body_marker(i) not in layout.split():
            raise SystemExit(f"{style}: body text for chapter {i} missing from the output")

    sizes = page_sizes(pdf, case)
    expected_width, expected_height = map(Decimal, expected.split())
    # Keep the evidence format and deduplication independent of the numeric check.
    reported_sizes = sorted({
        f"{float(width):g} {float(height):g}" for width, height in sizes
    })
    if not sizes or not all(
        abs(width - expected_width) <= PAPER_TOLERANCE_PT
        and abs(height - expected_height) <= PAPER_TOLERANCE_PT
        for width, height in sizes
    ):
        raise SystemExit(f"{style}: expected all pages within {PAPER_TOLERANCE_PT}pt "
                         f"of {expected}pt, got {reported_sizes}")

    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    (case / "evidence.json").write_text(
        json.dumps({"style": style, "promise": promise, "pages": pages,
                    "page_sizes": reported_sizes, "sha256": digest}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"style": style, "pages": pages, "sha256": digest}


def textwrap_body(body: str) -> str:
    import textwrap

    return textwrap.fill(body, width=78)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work", required=True, type=Path,
        help="evidence root (its book-styles/ subdirectory must not exist)",
    )
    args = parser.parse_args()

    work = args.work / "book-styles"
    try:
        work.mkdir(parents=True)
    except FileExistsError:
        parser.exit(2, f"evidence directory already exists: {work}; choose a fresh --work directory\n")
    results = [
        check_style(work, ROOT / "bin/skelepress", style, expected, promise)
        for style, (expected, promise) in STYLES.items()
    ]
    digests = {r["sha256"] for r in results}
    evidence = work / "book-styles-evidence.json"
    evidence.write_text(json.dumps({"styles": results}, indent=2) + "\n", encoding="utf-8")
    assert len(digests) == len(STYLES), f"the styles produced identical PDFs: {digests}"
    print(f"✅ book styles render distinct multipage output with the promised paper ({evidence})")


if __name__ == "__main__":
    main()
