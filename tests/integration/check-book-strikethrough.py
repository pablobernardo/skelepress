#!/usr/bin/env python3
"""Check visible strikethroughs in PDFs rendered by the public CLI."""

import html
import json
import math
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
BOOKS = ("book", "book-novel", "book-manual", "book-kdp-5x8", "book-kdp-digest",
         "book-kdp-6x9", "book-kdp-7x10", "book-kdp-square")
CUSTOM = r"""\documentclass{article}
\newcommand{\st}[1]{#1}
\let\sout\st
\begin{document}
Custom template

$body$
\end{document}
"""
PIXELS_PER_POINT = 3


def run_cli(project, env, action, config):
    argv = [ROOT / "bin/skelepress", action, "-c", config]
    with subprocess.Popen(argv, cwd=project, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            # The public CLI starts Pandoc and TeX as child processes.
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


def render(project, engine, template, body, custom=False):
    (project / "chapters").mkdir(parents=True)
    (project / "chapters/main.md").write_text(body, encoding="utf-8")
    if custom:
        (project / template).write_text(CUSTOM, encoding="utf-8")
    pandoc = {"pdf_engine": engine, "toc": False, "toc_depth": 2,
              "number_sections": True, "resource_path": ["chapters"]}
    if template:
        pandoc["template"] = template
    if template in BOOKS:
        pandoc["top_level_division"] = "chapter"
    config = {
        "version": 1,
        "project": {"name": "strike-check", "base_dir": "."},
        "document": {"title": "Strike check"},
        "input": {"chapters_dir": "chapters", "glob": "*.md", "order": "natural",
                  "explicit_files": ["main.md"]},
        "output": {"dir": "out", "file_prefix": "strike", "suffix": "check",
                   "keep_merged_markdown": False},
        "pandoc": pandoc,
        "filters": {"emoji": {"enabled": False}, "mermaid": {"enabled": False},
                    "extra_lua_filters": []},
        "runtime": {"required_commands": ["pandoc", engine], "strict": True},
        "compat": {"legacy_clearpage_between_h1": False},
    }
    config_path = project / "skelepress.config.yaml"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    env = dict(os.environ, SKELEPRESS_LANG="en", PYTHONDONTWRITEBYTECODE="1",
               TMPDIR=str(project))
    pdf = project / "out/strike-check.pdf"
    statuses = []
    for action in ("validate-config", "render"):
        result = run_cli(project, env, action, config_path.name)
        statuses.append(f"{action}={result.returncode}")
        if result.returncode or (action == "render" and not pdf.is_file()):
            raise AssertionError(f"{', '.join(statuses)}, PDF present={pdf.is_file()}"
                                 f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    if custom and (project / template).read_bytes() != CUSTOM.encode():
        raise AssertionError("the consumer template changed on disk")
    return pdf


def word_positions(pdf):
    bbox = subprocess.run(["pdftotext", "-bbox", pdf, "-"], check=True, timeout=15,
                          capture_output=True, text=True).stdout
    pages = re.findall(r"<page\b[^>]*>(.*?)</page>", bbox, re.DOTALL)
    for number, page in enumerate(pages, 1):
        for attrs, word in re.findall(r"<word\s+([^>]+)>(.*?)</word>", page):
            box = dict(re.findall(r'(\w+)="([\d.]+)"', attrs))
            yield html.unescape(word), number, box


def darkest_row(pdf, page, box):
    # Use the inside of the word, not its edges or adjacent whitespace. At
    # 216 dpi a 0.4pt rule has enough coverage to register in the raster.
    left, top, right, bottom = (float(box[key]) for key in ("xMin", "yMin", "xMax", "yMax"))
    x = math.ceil((left + 1) * PIXELS_PER_POINT)
    y = math.ceil((top + (bottom - top) / 4) * PIXELS_PER_POINT)
    width = math.floor((right - 1) * PIXELS_PER_POINT) - x
    height = math.floor((bottom - (bottom - top) / 4) * PIXELS_PER_POINT) - y
    pgm = subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r",
                          str(72 * PIXELS_PER_POINT), "-x", str(x), "-y", str(y),
                          "-W", str(width), "-H", str(height), "-singlefile", "-gray", pdf],
                         check=True, timeout=15, capture_output=True).stdout
    magic, size, depth, pixels = pgm.split(b"\n", 3)
    if (magic, size, depth) != (b"P5", f"{width} {height}".encode(), b"255") or len(pixels) != width * height:
        raise AssertionError("unexpected Poppler grayscale raster dimensions or format")
    return max(sum(pixel < 160 for pixel in pixels[i:i + width]) / width
               for i in range(0, len(pixels), width))


def check(project, engine, template, *, strike=True, custom=False, legacy=False):
    label = f"{engine} / {template or 'default article'}"
    if not strike:
        label += " (no strikeout markup)"
    body = "# Text check\n\n"
    if strike:
        body += "~~Revision marker~~\n\n"
    body += "Revision marker\n"
    if legacy:
        body += "\n\\sout{LegacyMarker}\n"
    try:
        pdf = render(project, engine, template, body, custom)
        words = list(word_positions(pdf))
        text = " ".join(word for word, _, _ in words)
        if text.count("Revision marker") != (2 if strike else 1):
            raise AssertionError(f"revision text missing from the PDF: {text!r}")
        if custom and "Custom template" not in text:
            raise AssertionError("the custom template's output is missing")
        markers = [(page, box) for word, page, box in words if word in ("marker", "LegacyMarker")]
        expected = ([not custom] if strike else []) + [False] + ([True] if legacy else [])
        scores = [darkest_row(pdf, page, box) for page, box in markers]
        # A strike is a near-continuous band; ordinary glyphs leave gaps.
        if [score >= 0.9 for score in scores] != expected:
            raise AssertionError(f"expected strike lines {expected}, darkest row coverage {scores}")
    except (AssertionError, OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"FAIL: {label}: {error}", file=sys.stderr)
        return False
    print(f"PASS: {label}: validate-config=0, render=0, PDF present; "
          f"darkest row coverage {', '.join(f'{score:.0%}' for score in scores)}", flush=True)
    return True


def main():
    with TemporaryDirectory(prefix="book-strikethrough-") as folder:
        work = Path(folder)
        results = [check(work / style, "pdflatex", style, legacy=style == "book") for style in BOOKS]
        results.extend(check(work / engine, engine, "book-novel") for engine in ("xelatex", "lualatex"))
        results.append(check(work / "article", "pdflatex", None))
        results.append(check(work / "custom", "pdflatex", "custom.tex", custom=True))
        results.append(check(work / "no-strike", "pdflatex", "book-novel", strike=False))
    print(f"Strikethrough checks: PASS={sum(results)} FAIL={results.count(False)}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
