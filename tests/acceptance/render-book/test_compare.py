"""Small fake-CLI wiring tests; these do not render or validate publications."""

import io
import json
import shlex
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="cli-acceptance-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name).resolve()
        self.calls = self.root / "calls"

    def payload(self, variant, changed=False):
        archive = self.root / (variant + ".tar")
        script = f'''#!/bin/sh
set -eu
n=0
if [ -f "$HOME/counter" ]; then read -r n < "$HOME/counter"; fi
n=$((n + 1)); printf '%s\\n' "$n" > "$HOME/counter"
printf '%s|%s|%s|%s|%s\\n' {shlex.quote(variant)} "$1" "$PWD" "$HOME" "$n" >> {shlex.quote(str(self.calls))}
case "$1" in
  render) test ! -f book-state; mkdir -p work/out; printf 'fake EPUB' > work/out/epub-guide-manual.epub;;
  book) printf 'changed project' > book-state; mkdir -p "$3/project"; printf 'fake PDF' > "$3/project/neutral-guide.pdf";;
esac
if [ "$1" = book ] && [ {str(changed).lower()} = true ]; then
  printf 'changed\\n'
else
  printf '%s\\n' "$1"
fi
printf 'fixture stderr\\n' >&2
'''
        with tarfile.open(archive, "w") as output:
            data = script.encode()
            member = tarfile.TarInfo("bin/skelepress")
            member.mode = 0o755
            member.size = len(data)
            output.addfile(member, io.BytesIO(data))
        return archive

    def compare(self, candidate):
        base = self.payload("base")
        originals = [p.read_bytes() for p in (base, candidate)]
        result = subprocess.run(
            [sys.executable, str(HERE / "compare.py"), str(base),
             str(candidate), "--evidence", str(self.root / "evidence")],
            capture_output=True,
        )
        self.assertEqual([p.read_bytes() for p in (base, candidate)], originals)
        return result

    def summary(self):
        names = []
        for command in ("render", "book"):
            names.extend(command + "." + stream for stream in ("stdout", "stderr", "exit"))
            names.extend(variant + "." + command + ".artifact" for variant in ("base", "candidate"))
        return "".join("PASS " + name + "\n" for name in names).encode()

    def test_public_commands_streams_artifacts_and_cold_environment(self):
        result = self.compare(self.payload("candidate"))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, self.summary(), b""))
        report = json.loads((self.root / "evidence/result.json").read_text())
        self.assertTrue(all(report["checks"].values()), report)
        calls = [line.split("|") for line in self.calls.read_text().splitlines()]
        self.assertEqual([(c[0], c[1], c[4]) for c in calls],
                         [("base", "render", "1"), ("base", "book", "2"),
                          ("candidate", "render", "1"), ("candidate", "book", "2")])
        self.assertEqual(len({(c[2], c[3]) for c in calls}), 1)
        for variant in ("base", "candidate"):
            for command, extension in (("render", ".epub"), ("book", ".pdf")):
                path = self.root / "evidence" / variant / command
                self.assertEqual((path / "stdout").read_bytes(), (command + "\n").encode())
                self.assertEqual((path / "stderr").read_bytes(), b"fixture stderr\n")
                self.assertEqual((path / "exit").read_bytes(), b"0\n")
                self.assertEqual(len(list((path / "generated").rglob("*" + extension))), 1)

    def test_raw_stream_regression_fails_and_retains_evidence(self):
        result = self.compare(self.payload("candidate", changed=True))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (1, self.summary().replace(b"PASS book.stdout", b"FAIL book.stdout"), b""))
        checks = json.loads((self.root / "evidence/result.json").read_text())["checks"]
        self.assertEqual([name for name, passed in checks.items() if not passed], ["book.stdout"])
        self.assertEqual((self.root / "evidence/candidate/book/stdout").read_bytes(), b"changed\n")
        self.assertEqual(len(self.calls.read_text().splitlines()), 4)

    def test_unsafe_candidate_rejected_before_any_command(self):
        candidate = self.root / "unsafe.tar"
        with tarfile.open(candidate, "w") as output:
            member = tarfile.TarInfo("../escape")
            member.size = 1
            output.addfile(member, io.BytesIO(b"x"))
        result = self.compare(candidate)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (1, b"", b"ERROR: unsafe archive member: ../escape\n"))
        self.assertFalse(self.calls.exists())
        self.assertFalse((self.root / "escape").exists())


if __name__ == "__main__":
    unittest.main()
