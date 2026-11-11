#!/usr/bin/env python3
"""Exercise the actual L3 preparation body using isolated command fakes only."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
MESSAGE = (
    "::error::L3 dependency preparation failed; see errors above. "
    "Publication checks have not started.\n"
)
FAKE = r'''
import json
import os
import sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
with Path(os.environ["TEST_CALLS"]).open("a") as stream:
    stream.write(json.dumps([name, args]) + "\n")
if name == "sudo":
    os.execvp(args[0], args)
if name == "apt-get":
    operation = "update" if "update" in args else "install"
    print("apt " + operation)
    if operation == "update" and os.environ["TEST_MODE"] == "dns":
        print("Temporary failure resolving 'archive.ubuntu.com'", file=sys.stderr)
        sys.exit(100 if "--error-on=any" in args else 0)
    if operation == "install" and os.environ["TEST_MODE"] == "download":
        print("Package download failed.", file=sys.stderr)
        sys.exit(100)
elif name == "kpsewhich":
    print(args[0])
elif name == "npm":
    print("mermaid ready")
'''


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        step = re.search(
            r"^      - name: Install full runtime dependencies\n"
            r"(.*?)(?=^      - name:|\Z)", workflow, re.M | re.S
        )
        if not step:
            raise AssertionError("Missing L3 dependency preparation")
        cls.metadata, body = step[1].split("        run: |\n", 1)
        cls.body = textwrap.dedent(body)

    def invoke(self, mode="success"):
        bash = shutil.which("bash")
        if bash is None:
            raise RuntimeError("Bash is required for the workflow test")
        with tempfile.TemporaryDirectory(prefix="skelepress-ci-prep-") as name:
            scratch = Path(name)
            bins = scratch / "bin"
            bins.mkdir()
            for command in ("sudo", "apt-get", "kpsewhich", "npm"):
                fake = bins / command
                fake.write_text("#!" + sys.executable + "\n" + FAKE)
                fake.chmod(0o755)
            (bins / "python3").symlink_to(sys.executable)
            for directory in ("home", "temp", "cache", "templates"):
                (scratch / directory).mkdir()
            template = scratch / "templates/default.tex"
            authored = "\\usepackage{alpha,beta}\n\\usepackage[option]{gamma}\n"
            template.write_text(authored)
            calls = scratch / "calls.jsonl"
            result = subprocess.run(
                [bash, "-e", "-o", "pipefail", "-c", self.body],
                cwd=scratch,
                env={
                    "PATH": str(bins), "HOME": str(scratch / "home"),
                    "TMPDIR": str(scratch / "temp"),
                    "XDG_CACHE_HOME": str(scratch / "cache"),
                    "LANG": "C", "LC_ALL": "C", "PYTHONNOUSERSITE": "1",
                    "PYTHONDONTWRITEBYTECODE": "1", "TEST_MODE": mode,
                    "TEST_CALLS": str(calls),
                },
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(template.read_text(), authored)
            recorded = [json.loads(line) for line in calls.read_text().splitlines()]
            return result, recorded

    def test_success_preserves_packages_styles_and_mermaid(self):
        result, calls = self.invoke()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (
            0, "apt update\napt install\nalpha.sty\nbeta.sty\ngamma.sty\nmermaid ready\n", ""
        ))
        install = next(args for tool, args in calls if tool == "apt-get" and "install" in args)
        packages = []
        index = 2  # install -y
        while index < len(install):
            if install[index] == "-o":
                index += 2
            else:
                packages.append(install[index])
                index += 1
        self.assertEqual(packages, [
            "pandoc", "texlive-latex-base", "texlive-latex-extra",
            "texlive-fonts-recommended", "librsvg2-bin", "texlive-xetex", "nodejs", "npm"
        ])
        self.assertEqual([args for tool, args in calls if tool == "kpsewhich"],
                         [["alpha.sty"], ["beta.sty"], ["gamma.sty"]])
        self.assertEqual([args for tool, args in calls if tool == "npm"],
                         [["install", "-g", "@mermaid-js/mermaid-cli@10.9.1"]])

    def test_dns_warning_stops_before_install_and_checks(self):
        result, calls = self.invoke("dns")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (
            100, "apt update\n", "Temporary failure resolving 'archive.ubuntu.com'\n" + MESSAGE
        ))
        self.assertEqual([tool for tool, _ in calls], ["sudo", "apt-get"])

    def test_download_failure_stops_before_styles_and_mermaid(self):
        result, calls = self.invoke("download")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (
            100, "apt update\napt install\n", "Package download failed.\n" + MESSAGE
        ))
        self.assertEqual([tool for tool, _ in calls], ["sudo", "apt-get", "sudo", "apt-get"])

    def test_network_waits_and_entire_preparation_are_bounded(self):
        result, calls = self.invoke()
        self.assertEqual(result.returncode, 0)
        self.assertRegex(self.metadata, r"(?m)^        timeout-minutes: 10$")
        for tool, args in calls:
            if tool == "apt-get":
                for value in ("Acquire::Retries=0", "Acquire::http::Timeout=30",
                              "Acquire::https::Timeout=30"):
                    self.assertIn(["-o", value], [args[i:i + 2] for i in range(len(args) - 1)])


if __name__ == "__main__":
    unittest.main()
