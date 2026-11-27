#!/usr/bin/env python3
"""Exercise the opt-in HTML WebP image conversion through the public CLI.

Plan assertions run dry and need no pandoc. The conversion renders need a real
pandoc and a real `cwebp`; the degradation class hides `cwebp` behind a stub
PATH, so it observes the note instead of depending on what the host lacks.
"""
import contextlib
import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# PNG fixtures are built with the standard library, so no imaging package in
# needed to make them: cwebp reads the bytes and re-encodes.
def make_png(width, height, pixel):
    """One 8-bit RGB PNG from a per-pixel callable."""
    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)  # filter type: none
        for x in range(width):
            scanlines.extend(pixel(x, y))
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(scanlines)))
            + chunk(b"IEND", b""))

PNG_A = make_png(64, 48, lambda x, y: ((x * 4) % 256, (y * 5) % 256, 128))
PNG_B = make_png(40, 30, lambda x, y: ((10 + 2 * x) % 256, 220, (30 + y * 3) % 256))


def cwebp_available() -> bool:
    return shutil.which("cwebp") is not None


def render_pandoc_available() -> bool:
    return shutil.which("pandoc") is not None


def webp_config(base_dir: Path) -> dict:
    return {
        "version": 1,
        "project": {"name": "webp", "base_dir": str(base_dir)},
        "document": {"title": "WebP", "language": "en"},
        "input": {"chapters_dir": "chapters", "glob": "*.md", "order": "natural", "explicit_files": []},
        "output": {"dir": "out", "suffix": "webp", "keep_merged_markdown": False,
                   "formats": ["html"], "html": {"reader": True, "image_conversion": True}},
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


@unittest.skipUnless(render_pandoc_available() and cwebp_available(), "requires real pandoc and cwebp")
class WebpArtifactTest(unittest.TestCase):
    """The real render embeds WebP bytes and never touches the source files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        media = self.root / "chapters" / "media"
        media.mkdir(parents=True)
        (media / "pic.png").write_bytes(PNG_A)
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
        self.assertIn("Converted 1 image", result.stdout)
        # Source images stay untouched: the copies live in a work directory.
        self.assertEqual((self.root / "chapters/media/pic.png").stat().st_size, self.png_size)

    def test_svg_stays_untouched_and_unknown_targets_are_skipped(self):
        (self.root / "chapters/media/vector.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        (self.root / "chapters/one.md").write_text(
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
        # One unconvertible PNG must not break the render.
        self.assertIn("data:image/svg+xml", text)

    def test_same_stem_images_in_different_directories_never_share_a_copy(self):
        # Two-pic.png sources must each keep their own embedded bytes.
        media = self.root / "chapters"
        for data, rel in ((PNG_A, "one/pic.png"), (PNG_B, "two/pic.png")):
            (media / rel).parent.mkdir(parents=True, exist_ok=True)
            (media / rel).write_bytes(data)
        (media / "one.md").write_text("# One\n\n![a](one/pic.png)\n\n![b](two/pic.png)\n\nBye.\n")
        result = self.render()
        artifact = next((self.root / "out").glob("*.html"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(artifact.read_text(encoding="utf-8").count("data:image/webp;"), 2)

    def test_config_without_conversion_keeps_png_bytes(self):
        self.config["output"]["html"] = {"reader": True}
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        artifact = next((self.root / "out").glob("*.html"))
        text = artifact.read_text(encoding="utf-8")
        self.assertIn("data:image/png;", text)
        self.assertNotIn("data:image/webp;", text)


class WebpDegradationTest(unittest.TestCase):
    """Without cwebp on PATH the render continues with the original bytes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "chapters/media").mkdir(parents=True)
        # embed-resources does not validate bytes, so a plain payload is enough
        # to observe that the writer kept it (and that nothing converted it).
        (self.root / "chapters/media/pic.png").write_bytes(b"fake png bytes")
        (self.root / "chapters/one.md").write_text("# One\n\n![a diagram](media/pic.png)\n\nBye.\n")
        self.config = webp_config(self.root)
        self.path = self.root / "skelepress.config.yaml"

    def mocked_env(self):
        """A PATH without cwebp, with pandoc and python3 forwarded to the real
        ones, so the render keeps producing a real artifact while the codec
        is genuinely absent."""
        bin_dir = Path(self.tmp.name) / "mockbin"
        bin_dir.mkdir()
        for command in ("curl", "mmdc", "xelatex"):
            (bin_dir / command).write_text("#!/bin/sh\nexit 0\n")
            (bin_dir / command).chmod(0o755)
        for forwarded in ("pandoc", "python3"):
            real = shutil.which(forwarded) or forwarded
            shim = bin_dir / forwarded
            shim.write_text("#!/bin/sh\nexec '" + real + "' \"$@\"\n")
            shim.chmod(0o755)
        # Mirror every other executable the runner's own PATH provides, but
        # never the codec: whether cwebp degrades must not depend on where
        # (or whether) the host installed it, /usr/bin included.
        masked = {"cwebp"}
        provided = {entry.name for entry in bin_dir.iterdir()}
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            if not directory or not Path(directory).is_dir():
                continue
            for entry in Path(directory).iterdir():
                if entry.name in masked or entry.name in provided:
                    continue
                if entry.is_file() and os.access(entry, os.X_OK):
                    with contextlib.suppress(OSError):
                        (bin_dir / entry.name).symlink_to(entry)
                provided.add(entry.name)
        return {**os.environ, "SKELEPRESS_LANG": "en",
                "PATH": str(bin_dir)}

    def render(self, env):
        self.path.write_text(json.dumps(self.config))
        return subprocess.run(
            [str(ROOT / "bin/skelepress"), "render", "-c", str(self.path)],
            capture_output=True, text=True, env=env,
        )

    def test_missing_cwebp_degrades_with_a_note(self):
        result = self.render(self.mocked_env())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WebP conversion is enabled but cwebp", result.stdout)
        artifact = next((self.root / "out").glob("*.html"))
        text = artifact.read_text(encoding="utf-8")
        self.assertNotIn("data:image/webp;", text)
        self.assertIn("data:image/png;", text)

    def test_doctor_names_the_missing_capability(self):
        env = self.mocked_env()
        self.path.write_text(json.dumps(self.config))
        result = subprocess.run(
            [str(ROOT / "bin/skelepress"), "doctor", "-c", str(self.path)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("cwebp", result.stdout)

        # The configuration built without the option keeps passing here.
        self.config["output"]["html"] = {"reader": True}
        self.path.write_text(json.dumps(self.config))
        ok = subprocess.run(
            [str(ROOT / "bin/skelepress"), "doctor", "-c", str(self.path)],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
