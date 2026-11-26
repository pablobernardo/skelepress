#!/usr/bin/env python3
"""Exercise the html output format through the public CLI.

The plan assertions run dry and need no pandoc at all: the reader template,
--section-divs and --embed-resources are behaviors of the real HTML writer, not
of a plan shape, and the structural class below renders only where a real
pandoc exists.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class HtmlPlanTest(unittest.TestCase):
    """Plan shape: the html job is a full v1-compatible plan with its details."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "chapters").mkdir()
        (self.root / "chapters/one.md").write_text("# One\n\nHello.\n")
        (self.root / "chapters/two.md").write_text("# Two\n\nAgain.\n")
        self.config = {
            "version": 1, "project": {"name": "formats", "base_dir": str(self.root)},
            "document": {"title": "Formats", "author": "Example Author", "language": "es"},
            "input": {"chapters_dir": "chapters", "glob": "*.md", "order": "natural", "explicit_files": []},
            "output": {"dir": "out", "suffix": "test", "keep_merged_markdown": False,
                       "formats": ["html"]},
            "pandoc": {"pdf_engine": "xelatex", "toc": True, "toc_depth": 2,
                       "number_sections": False, "resource_path": ["chapters"]},
            "filters": {"emoji": {"enabled": False}, "mermaid": {"enabled": False}, "extra_lua_filters": []},
            "runtime": {"required_commands": ["pandoc"], "strict": True},
        }
        self.path = self.root / "skelepress.config.yaml"

    def run_cli(self, *args):
        self.path.write_text(json.dumps(self.config))
        return subprocess.run([str(ROOT / "bin/skelepress"), *args, "-c", str(self.path)],
                              capture_output=True, text=True,
                              env={**os.environ, "SKELEPRESS_LANG": "en"})

    def single_job(self, artifact_format):
        result = self.run_cli("render", "--dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(result.stdout)
        # A single format keeps the version-1 plan shape; only the envelope differs.
        job = plan if "jobs" not in plan else plan["jobs"][0]
        self.assertIn(artifact_format, job["pandoc"]["target"])
        return plan, job

    def test_html_job_plan_shape_and_argv(self):
        _, job = self.single_job("html")
        argv = job["pandoc"]["argv"]
        self.assertIn("--section-divs", argv)
        self.assertIn("--embed-resources", argv)
        self.assertTrue(any("templates/reader.html" in flag for flag in argv), argv)
        self.assertTrue(any("filters/lazy-images.lua" in flag for flag in argv), argv)
        joined = " ".join(argv)
        self.assertIn("--metadata title=Formats", joined)
        self.assertIn("--metadata lang=es", joined)
        self.assertEqual(job["side_effects"]["html"], {"reader": True, "template_note": False})
        # The html job does not claim typesetting that only LaTeX can decide.
        self.assertNotIn("-V", argv)

    def test_html_artifact_named_by_format(self):
        _, job = self.single_job("html")
        self.assertTrue(str(job["pandoc"]["target"]["html"]).endswith("out/formats-test.html"))

    def test_reader_false_leaves_the_default_template(self):
        self.config["output"]["html"] = {"reader": False}
        _, job = self.single_job("html")
        argv = job["pandoc"]["argv"]
        self.assertEqual(job["side_effects"]["html"], {"reader": False, "template_note": False})
        self.assertFalse(any("reader.html" in flag for flag in argv), argv)
        self.assertIn("--section-divs", argv)
        self.assertIn("--embed-resources", argv)

    def test_template_note_is_recorded_but_pdf_job_unchanged(self):
        self.config["pandoc"]["template"] = "book"
        self.config["output"]["formats"] = ["pdf", "html"]
        result = self.run_cli("render", "--dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(result.stdout)
        by_format = {next(k for k in j["pandoc"]["target"] if k != "markdown"): j for j in plan["jobs"]}
        self.assertNotIn("html", by_format["pdf"]["side_effects"])
        self.assertEqual(by_format["html"]["side_effects"]["html"]["template_note"], True)

    def test_unknown_html_field_is_rejected(self):
        self.config["output"]["html"] = {"reader": True, "pages": 2}
        result = self.run_cli("validate-config")
        self.assertEqual(result.returncode, 1)
        self.assertIn("disallowed fields: pages", result.stdout)

    def test_format_gated_files_stay_out_of_html(self):
        self.config["input"]["explicit_files"] = [
            {"file": "one.md", "formats": ["pdf"]},
            "two.md",
        ]
        result = self.run_cli("render", "--dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(result.stdout)
        # macOS resolves /var to /private/var; the format gate is the assertion.
        self.assertEqual([Path(p).name for p in plan["chapters"]], ["two.md"])


@unittest.skipUnless(shutil.which("pandoc"), "requires a real pandoc")
class HtmlArtifactTest(unittest.TestCase):
    """The real render keeps the reader promises: structure, TOC, lazy images."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        chapters = self.root / "chapters"
        chapters.mkdir()
        (chapters / "one.md").write_text(
            "# First\n\nHello.\n\n![a diagram](media/pic.png)\n\nBye.\n"
        )
        media = self.root / "chapters/media"
        media.mkdir()
        hot, path = tempfile.mkstemp(suffix=".png")
        with os.fdopen(hot, "wb") as fh:
            fh.write(b" fak_png ")
        shutil.copy(path, media / "pic.png")
        os.unlink(path)
        self.config = {
            "version": 1, "project": {"name": "formats", "base_dir": str(self.root)},
            "document": {"title": "Html Reader", "language": "en"},
            "input": {"chapters_dir": "chapters", "glob": "*.md", "order": "natural",
                      "explicit_files": []},
            "output": {"dir": "out", "suffix": "test", "keep_merged_markdown": False,
                       "formats": ["html"]},
            "pandoc": {"pdf_engine": "xelatex", "toc": True, "toc_depth": 2,
                       "number_sections": False, "resource_path": ["chapters", "chapters/media"]},
            "filters": {"emoji": {"enabled": False}, "mermaid": {"enabled": False},
                        "extra_lua_filters": []},
            "runtime": {"required_commands": ["pandoc"], "strict": True},
        }
        self.path = self.root / "skelepress.config.yaml"

    def run_cli(self, *args):
        self.path.write_text(json.dumps(self.config))
        return subprocess.run([str(ROOT / "bin/skelepress"), *args, "-c", str(self.path)],
                              capture_output=True, text=True,
                              env={**os.environ, "SKELEPRESS_LANG": "en"})

    def test_reader_artifact_structure(self):
        result = self.run_cli("render")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        artifact = self.root / "out/html-reader-test.html"
        text = artifact.read_text(encoding="utf-8")
        # One self-contained artifact: the stylesheet travels inside the file.
        self.assertIn("skelepress reader", text)
        # The generated-with credit rides in the header and links the toolkit.
        self.assertIn('class="credit"', text)
        self.assertIn("github.com/pablobernardo/skelepress", text)
        self.assertIn('<html lang="en">', text)
        # Pandoc section divs and the populated sidebar TOC the reader navigates.
        self.assertIn("<section id=", text)
        self.assertIn('id="TOC"', text)
        self.assertIn("#content", text)
        # Images resolve and travel lazy: no external references remain.
        self.assertIn('loading="lazy"', text)
        self.assertIn('decoding="async"', text)
        self.assertIn("data:image/", text)
        # Nothing may reach back to the project tree: the artifact is all
        # the reader needs.
        self.assertNotIn("media/pic.png", text)

    def test_wave2_reader_shell(self):
        result = self.run_cli("render")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        artifact = self.root / "out/html-reader-test.html"
        text = artifact.read_text(encoding="utf-8")
        # Manual theme control: the toggle button and the attribute-based
        # palette switch, with the stored choice surviving a reload.
        self.assertIn("theme-toggle", text)
        self.assertIn('data-theme="dark"', text)
        self.assertIn("localStorage", text)
        # The chapter search box is a real input, not just CSS.
        self.assertIn('type="search"', text)
        self.assertIn("aria-label=", text)
        # The mobile drawer carries a second TOC container with its own id.
        self.assertIn("toc-drawer", text)
        self.assertIn('id="TOC-drawer"', text)
        # Render deferral is guarded by a support query, never unconditional.
        self.assertIn("@supports (content-visibility: auto)", text)
        self.assertIn("contain-intrinsic-size", text)
        # The reading bar is a full-width header above the layout: it comes
        # before both the sidebar and the content, holding every control; the
        # title itself lives over the reading column, not in the bar.
        self.assertIn("reader-bar", text)
        self.assertLess(text.index('reader-bar'), text.index('class="layout"'))
        self.assertLess(text.index('reader-bar'), text.index('class="content-title"'))
        # The sidebar toggle starts as a fold arrow with an accessible name.
        self.assertIn('aria-label="Show or hide the side contents panel"', text)
        # Navigation is per chapter: the script installs a pager at the end of
        # each top-level section; no single document-ending pager exists.
        self.assertNotIn('class="pager" hidden', text)
        self.assertIn("installPager", text)
        # Chapter mode is an explicit script-applied choice, and its hiding
        # rules never apply when the script is absent.
        self.assertIn("mode-toggle", text)
        self.assertIn('aria-pressed="false"', text)
        self.assertIn("main.chapter-mode > section[id]", text)
        self.assertNotIn('class="chapter-mode"', text)
        # Chapter mode is the default shape: the script applies it unless a
        # stored scroll choice says otherwise.
        self.assertIn('!== "scroll"', text)
        # The search box takes keyboard rails: arrows walk the results.
        self.assertIn("ArrowDown", text)
        self.assertIn("ArrowUp", text)
        # The view switch is one fixed stacked-sheets icon; the highlight
        # (aria-pressed styling) carries the mode, not the icon.
        self.assertIn('aria-label="Switch between chapter view and full view"', text)
        self.assertIn("view-icon", text)
        self.assertNotIn("view-icon view-full", text)
        self.assertIn('.mode-toggle[aria-pressed="true"]', text)

    def test_reader_false_artifact_has_no_reader_shell(self):
        self.config["output"]["html"] = {"reader": False}
        result = self.run_cli("render")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        artifact = self.root / "out/html-reader-test.html"
        text = artifact.read_text(encoding="utf-8")
        self.assertNotIn("skelepress reader", text)
        # The document itself is still a complete html publication.
        self.assertIn("<h1", text)
        self.assertIn('loading="lazy"', text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
