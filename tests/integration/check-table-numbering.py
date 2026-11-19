#!/usr/bin/env python3
"""Render captionless and captioned tables through the public CLI."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
BUILTINS = ("default", "book", "book-novel", "book-manual", "book-kdp-5x8", "book-kdp-digest")
CHAPTER = """# Table checks

| Column | Value |
| ------ | ----- |
| First  | FirstCell |

: First numbered caption

| Column | Value |
| ------ | ----- |
| Middle | CaptionlessCell |

| Column | Value |
| ------ | ----- |
| Last   | LastCell |

: Second numbered caption
"""
CAPTION = re.compile(r"\bTable\s+([0-9]+(?:\.[0-9]+)*)\s*:\s+(First|Second) numbered caption")


def check(engine, style, project):
    output = project / "out"
    (project / "chapters").mkdir(parents=True)
    (project / "chapters/01-tables.md").write_text(CHAPTER, encoding="utf-8")
    pandoc = {"pdf_engine": engine, "toc": False, "toc_depth": 2,
              "number_sections": True, "resource_path": ["chapters"]}
    if style != "default":
        pandoc.update(template=style, top_level_division="chapter")
    config = {
        "version": 1,
        "project": {"name": "table-numbering", "base_dir": "."},
        "document": {"title": "Table numbering check"},
        "input": {"chapters_dir": "chapters", "glob": "*.md", "order": "natural",
                  "explicit_files": ["01-tables.md"]},
        "output": {"dir": output.name, "file_prefix": "tables", "suffix": "check",
                   "keep_merged_markdown": False},
        "pandoc": pandoc,
        "filters": {"emoji": {"enabled": False}, "mermaid": {"enabled": False},
                    "extra_lua_filters": []},
        "runtime": {"required_commands": ["pandoc", engine], "strict": True},
        "compat": {"legacy_clearpage_between_h1": False},
    }
    config_path = project / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    result = subprocess.run([ROOT / "bin/skelepress", "render", "-c", config_path],
                            cwd=project, env=dict(os.environ, SKELEPRESS_LANG="en"),
                            capture_output=True, text=True, timeout=120)
    case = f"{engine} / {style}"
    if result.returncode:
        print(f"FAIL: {case} render exited {result.returncode}", file=sys.stderr)
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return False
    pdf = output / "tables-check.pdf"
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], check=True, timeout=15,
                          capture_output=True, text=True).stdout
    captions = CAPTION.findall(text)
    cells = all(text.count(cell) == 1 for cell in ("FirstCell", "CaptionlessCell", "LastCell"))
    numbered = len(captions) == 2 and [label for _, label in captions] == ["First", "Second"]
    if numbered:
        first, second = (tuple(map(int, number.split("."))) for number, _ in captions)
        numbered = first[-1] == 1 and second == (*first[:-1], 2)
    if not (cells and numbered):
        print(f"FAIL: {case} table cells or numbering changed: {captions!r}\n{text}", file=sys.stderr)
        return False
    print(f"PASS: {case} renders all three tables; numbered captions {captions[0][0]} and {captions[1][0]}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", action="append", choices=("xelatex", "lualatex", "pdflatex"),
                        help="TeX engine; repeat to check more than one (default: xelatex)")
    parser.add_argument("--template", action="append",
                        help=f"shipped style; repeat to check more than one (default: {', '.join(BUILTINS)})")
    args = parser.parse_args()
    artifacts = ROOT / "examples/.output"
    artifacts.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="table-numbering-", dir=artifacts) as folder:
        results = []
        for engine in args.engine or ["xelatex"]:
            for style in args.template or BUILTINS:
                project = Path(folder) / str(len(results))
                results.append(check(engine, style, project))
    print(f"Table checks: PASS={sum(results)} FAIL={results.count(False)}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
