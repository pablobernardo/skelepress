#!/usr/bin/env python3
"""Public CLI regression for protecting existing book-style evidence."""
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


if __name__ == "__main__":
    unittest.main()
