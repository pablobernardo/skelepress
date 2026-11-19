#!/usr/bin/env python3
"""Public CLI regressions for book-style acceptance."""
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().with_name("check-book-styles.py")


def snapshot(root):
    state = {}
    for path in (root, *root.rglob("*")):
        mode = path.lstat().st_mode
        data = path.read_bytes() if stat.S_ISREG(mode) else None
        state[path.relative_to(root)] = (mode, data)
    return state


class BookStylesEvidenceTest(unittest.TestCase):
    def test_existing_evidence_is_refused_without_changes(self):
        with tempfile.TemporaryDirectory(prefix="test-book-styles-") as tmp:
            root = Path(tmp)
            work = root / "work directory"
            evidence = work / "book-styles"
            nested = evidence / "unrelated"
            nested.mkdir(parents=True)
            nested.chmod(0o750)
            marker = nested / "marker.txt"
            marker.write_bytes(b"unrelated evidence\x00\n")
            marker.chmod(0o640)
            (evidence / "book-styles-evidence.json").write_bytes(b'{"styles": []}\n')
            (work / "sibling.txt").write_bytes(b"outside the evidence directory\n")
            before = snapshot(root)

            result = subprocess.run(
                [sys.executable, str(RUNNER), "--work", str(work)],
                cwd=root, env={"PATH": ""}, capture_output=True, timeout=10,
            )

            with self.subTest("exit status"):
                self.assertEqual(result.returncode, 2)
            with self.subTest("stdout"):
                self.assertEqual(result.stdout, b"")
            with self.subTest("stderr"):
                self.assertEqual(
                    result.stderr,
                    f"evidence directory already exists: {evidence}; "
                    "choose a fresh --work directory\n".encode(),
                )
            after = snapshot(root)
            with self.subTest("existing paths, data and modes"):
                self.assertEqual({path: after.get(path) for path in before}, before)
            with self.subTest("directory entries"):
                self.assertEqual(after.keys(), before.keys())


class BookStylesOutputTest(unittest.TestCase):
    def assert_rejected(self, text, sizes, diagnostic):
        with tempfile.TemporaryDirectory(prefix="test-book-styles-pdf-") as tmp:
            root = Path(tmp)
            # Keep the runner's normal CLI lookup but control the rendered observations.
            runner = root / "tests" / "integration" / RUNNER.name
            runner.parent.mkdir(parents=True)
            shutil.copyfile(RUNNER, runner)
            tools = root / "bin"
            tools.mkdir()
            render = tools / "skelepress"
            render.write_text('#!/bin/sh\nif [ "$1" = render ]; then\n'
                              '  /bin/mkdir "${3%/*}/output" || exit\n'
                              '  printf "%%PDF-fixture" > "${3%/*}/output/sample.pdf"\nfi\n')
            box = "".join(f'<page width="{w}" height="{h}"></page>\n' for w, h in sizes)
            extract = tools / "pdftotext"
            extract.write_text('#!/bin/sh\nif [ "$1" = -bbox ]; then\n'
                               f'  printf %s {shlex.quote(box)}\nelse\n'
                               f'  printf %s {shlex.quote(text)}\nfi\n')
            for tool in (render, extract):
                tool.chmod(0o700)
            work = root / "work"
            result = subprocess.run(
                [sys.executable, str(runner), "--work", str(work)],
                cwd=root, env={"PATH": str(tools)}, capture_output=True, timeout=10,
            )
            with self.subTest("exit and streams"):
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (1, b"", (diagnostic + "\n").encode()))
            with self.subTest("no success evidence"):
                self.assertEqual(list(work.rglob("*evidence.json")), [])

    def test_mixed_or_missing_paper_sizes_are_rejected(self):
        text = "".join(f"Chapter {n}\n735021{n}490586\n\f" for n in range(1, 5))
        for sizes, reported in (([("595.276", "841.890"), ("612", "792")],
                                 "['595.276 841.89', '612 792']"), ([], "[]")):
            with self.subTest(sizes=sizes):
                self.assert_rejected(text, sizes, "book-novel: expected all pages within "
                                     f"0.01pt of 595.28 841.89pt, got {reported}")

    def test_chapter_heading_does_not_substitute_for_body_text(self):
        text = "Chapter 1\nChapter 2\nChapter 3\nChapter 4\n\f"
        text += "7350211490586\n\f7350212490586\n\f7350214490586\n\f"
        self.assert_rejected(text, [("595.276", "841.890")],
                             "book-novel: body text for chapter 3 missing from the output")


if __name__ == "__main__":
    unittest.main()
