#!/usr/bin/env python3
"""Exercise the opt-in HTML WebP image conversion through the public CLI.

Plan assertions run dry and need no pandoc. The performance and degradation
renders need a real pandoc and probe the actually installed Pillow capability:
the tests skip explicitly when the capability the case needs is unavailable,
never claiming a pass the machine could not observe.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000400000003008020000006b4a474900000001"
    "515a0000002574584574646174653a63726561746500000000000000000000000000000000"
    "000000000000"
)


def pillow_webp_available() -> bool:
    proc = subprocess.run(
        ["python3", "-c", "from PIL import features; raise SystemExit(0 if features.check('webp') else 1)"],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def render_pandoc_available() -> bool:
    from shutil import which
    return which("pandoc") is not None


def webp_config(base_dir: Path) -> dict:
    return {
        "version": 1,
        "project": {"name": "webp", "base_dir": str(base_dir)},
        "document": {"title": "WebP", "language": "en"},
        "input": {"chapters_dir": "chapters", "glob": "*.md", "order": "natural", "explicit_files": []},
        "output": {"dir": "out", "suffix": "webp", "keep_merged_markdown": False,
                   "formats": ["html"], "html": {"image_conversion": True}},
        "pandoc": {"pdf_engine": "xelatex", "toc": False, "toc_depth": 2,
                   "number_sections": False, "resource_path": ["chapters"]},
        "filters": {"emoji": {"enabled": False}, "mermaid": {"enabled": False}, "extra_lua_filters": []},
        "runtime": {"required_commands": ["pandoc"], "strict": True},
    }


class WebpPlanTest(unittest.TestCase):
    """Plan shape: the opt-in conversion is recorded HTML-only side effects."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "chapters").mkdir()
        (self.root / "chapters/one.md").write_text("# One\n\nHello.\n")
        self.config = webp_config(self.root)
        self.path = self.root / "skelepress.config.yaml"

    def run_cli(self, *args):
        self.path.write_text(json.dumps(self.config))
        return subprocess.run([str(ROOT / "bin/skelepress"), *args, "-c", str(self.path)],
                              capture_output=True, text=True,
                              env={**os.environ, "SKELEPRESS_LANG": "en"})

    def plan_job(self):
        result = self.run_cli("render", "--dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(result.stdout)
        return plan if "jobs" not in plan else plan["jobs"][0]

    def test_conversion_declared_in_plan_and_argv(self):
        job = self.plan_job()
        self.assertEqual(
            job["side_effects"]["html"],
            {"reader": True, "template_note": False, "image_conversion": True},
        )
        self.assertTrue(
            any("filters/webp-image.lua" in flag for flag in job["pandoc"]["argv"]),
            job["pandoc"]["argv"],
        )

    def test_off_by_default_keeps_plan_and_argv_unchanged(self):
        self.config["output"]["html"] = {"reader": True}
        job = self.plan_job()
        self.assertEqual(
            job["side_effects"]["html"],
            {"reader": True, "template_note": False, "image_conversion": False},
        )
        self.assertFalse(any("webp-image.lua" in flag for flag in job["pandoc"]["argv"]), job["pandoc"]["argv"])

    def test_absent_html_section_keeps_plan_unchanged(self):
        del self.config["output"]["html"]
        job = self.plan_job()
        self.assertEqual(
            job["side_effects"]["html"],
            {"reader": True, "template_note": False, "image_conversion": False},
        )
        self.assertFalse(any("webp-image.lua" in flag for flag in job["pandoc"]["argv"]), job["pandoc"]["argv"])

    def test_pdf_job_never_carries_the_conversion(self):
        self.config["output"]["formats"] = ["pdf", "html"]
        result = self.run_cli("render", "--dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(result.stdout)
        by_format = {next(k for k in j["pandoc"]["target"] if k != "markdown"): j for j in plan["jobs"]}
        self.assertNotIn("html", by_format["pdf"]["side_effects"])
        self.assertFalse(any("webp-image.lua" in flag for flag in by_format["pdf"]["pandoc"]["argv"]))

    def test_unknown_conversion_value_is_rejected(self):
        self.config["output"]["html"]["image_conversion"] = "yes"
        result = self.run_cli("validate-config")
        self.assertEqual(result.returncode, 1)


@unittest.skipUnless(render_pandoc_available(), "requires a real pandoc")
@unittest.skipUnless(pillow_webp_available(), "requires Pillow with WebP support")
class WebpArtifactTest(unittest.TestCase):
    """The real render embeds WebP bytes and never touches the source files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        media = self.root / "chapters" / "media"
        media.mkdir(parents=True)

        import io

        from PIL import Image  # type: ignore[import-not-found]  # capability-guarded above

        # A gradient compresses well as lossless WebP, so the not-smaller
        # guard cannot silently reject the conversion.
        img = Image.new("RGB", (64, 48))
        for x in range(64):
            for y in range(48):
                img.putpixel((x, y), ((x * 4) % 256, (y * 5) % 256, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        (media / "pic.png").write_bytes(buf.getvalue())
        self.png_size = (media / "pic.png").stat().st_size

        (self.root / "chapters/one.md").write_text("# One\n\n![a diagram](media/pic.png)\n\nBye.\n")
        self.config = webp_config(self.root)
        self.path = self.root / "skelepress.config.yaml"

    def render(self):
        self.path.write_text(json.dumps(self.config))
        return subprocess.run(
            [str(ROOT / "bin/skelepress"), "render", "-c", str(self.path)],
            capture_output=True, text=True,
            env={**os.environ, "SKELEPRESS_LANG": "en"},
        )

    def test_png_becomes_webp_in_the_html(self):
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        artifact = next((self.root / "out").glob("*.html"))
        text = artifact.read_text(encoding="utf-8")
        self.assertIn("data:image/webp;", text)
        self.assertNotIn("data:image/png;", text)
        self.assertIn('loading="lazy"', text)
        # The conversion summary names one converted image.
        self.assertIn("Converted 1 image", result.stdout)
        # Source images stay untouched: the copies live in a work directory.
        self.assertEqual((self.root / "chapters/media/pic.png").stat().st_size, self.png_size)
        # The temporary work directory never outlives the render.
        leftovers = [p for p in (self.root / "out").iterdir() if p.name.startswith("skelepress-webp-")]
        self.assertEqual(leftovers, [])

    def test_svg_and_gif_stay_untouched_and_unknown_targets_are_skipped(self):
        (self.root / "chapters/media/vector.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        chapter = self.root / "chapters/one.md"
        chapter.write_text(
            "# One\n\n![a diagram](media/pic.png)\n\n"
            "![vector](media/vector.svg)\n\n"
            "![missing](media/nope.png)\n\nBye.\n"
        )
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        artifact = next((self.root / "out").glob("*.html"))
        text = artifact.read_text(encoding="utf-8")
        self.assertIn("data:image/webp;", text)
        self.assertIn("data:image/svg+xml;", text)
        self.assertIn("Not converted", result.stdout)
        self.assertIn("media/nope.png", result.stdout)

    def test_config_without_conversion_keeps_png_bytes(self):
        self.config["output"]["html"] = {"reader": True}
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        artifact = next((self.root / "out").glob("*.html"))
        text = artifact.read_text(encoding="utf-8")
        self.assertIn("data:image/png;", text)
        self.assertNotIn("data:image/webp;", text)


@unittest.skipUnless(render_pandoc_available(), "requires a real pandoc")
@unittest.skipIf(pillow_webp_available(), "degradation needs Pillow to be absent")
class WebpDegradationTest(unittest.TestCase):
    """Without the capability the render continues with the original bytes."""

    def mock_path(self) -> str:
        """Stub the doctor's required commands; python3 stays the real one."""
        import shutil
        bin_dir = Path(self.tmp.name) / "mockbin"
        bin_dir.mkdir(exist_ok=True)
        for command in ("pandoc", "curl", "mmdc"):
            (bin_dir / command).write_text("#!/bin/bash\nexit 0\n")
            (bin_dir / command).chmod(0o755)
        python3 = bin_dir / "python3"
        python3_path = shutil.which("python3")
        python3.write_text("#!/bin/bash\nexec " + repr(python3_path) + ' "$@"\n')
        python3.chmod(0o755)
        return str(bin_dir)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "chapters").mkdir()
        # `--embed-resources` does not validate bytes, so this non-image PNG
        # is enough to observe the writer's choice.
        (self.root / "chapters/media").mkdir()
        (self.root / "chapters/media/pic.png").write_bytes(b"fake png bytes")
        (self.root / "chapters/one.md").write_text("# One\n\n![a diagram](media/pic.png)\n\nBye.\n")
        self.config = webp_config(self.root)
        self.path = self.root / "skelepress.config.yaml"

    def test_missing_pillow_degrades_with_a_note(self):
        self.path.write_text(json.dumps(self.config))
        result = subprocess.run(
            [str(ROOT / "bin/skelepress"), "render", "-c", str(self.path)],
            capture_output=True, text=True,
            env={**os.environ, "SKELEPRESS_LANG": "en"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WebP conversion is enabled but Pillow", result.stdout)
        artifact = next((self.root / "out").glob("*.html"))
        self.assertIn("data:image/png;", artifact.read_text(encoding="utf-8"))

    def test_doctor_names_the_missing_capability(self):
        mocked = self.mock_path()
        env = {**os.environ, "SKELEPRESS_LANG": "en", "PATH": mocked + os.pathsep + "/usr/bin" + os.pathsep + "/bin"}

        self.path.write_text(json.dumps(self.config))
        result = subprocess.run(
            [str(ROOT / "bin/skelepress"), "doctor", "-c", str(self.path)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Pillow", result.stdout)

        # The standard configuration without the option keeps passing here.
        self.config["output"]["html"] = {"reader": True}
        self.path.write_text(json.dumps(self.config))
        ok = subprocess.run(
            [str(ROOT / "bin/skelepress"), "doctor", "-c", str(self.path)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
