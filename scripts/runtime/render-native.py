#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import NoReturn

try:
    import template_runtime
except Exception:  # imported as a module from elsewhere: fix the path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import template_runtime

try:
    import top_level_division_runtime
except Exception:  # imported as a module from elsewhere: fix the path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import top_level_division_runtime

try:
    import yaml  # type: ignore
except Exception:  # PyYAML is optional: Ruby's stdlib YAML is the fallback.
    yaml = None

try:
    from i18n_runtime import t, t_for
except Exception:
    def t(_key: str, fallback: str, **kwargs: object) -> str:
        try:
            return fallback.format(**kwargs)
        except Exception:
            return fallback

    def t_for(lang: str, _key: str, fallback: str, **kwargs: object) -> str:
        return t(_key, fallback, **kwargs)

ORDER_NATURAL = "natural"
ORDER_ALPHABETICAL = "alphabetical"
ORDER_CHOICES = (ORDER_NATURAL, ORDER_ALPHABETICAL)

def slugify(value: str) -> str:
    """A file name derived from a title: lowercase, ASCII, single dashes."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    return slug or "document"


def file_stem(document: dict, output: dict) -> str:
    """One rule for both sources: a declared name, or the title, becomes a slug.

    Slugging by construction is also what makes a declared name unable to escape
    the output directory: nothing but [a-z0-9-] survives.
    """
    declared = str(output.get("file_prefix") or "").strip()
    return slugify(declared or str(document.get("title") or "document"))


DOCUMENT_VAR_FIELDS = ("title", "subtitle", "publisher", "author", "date", "rights")

# babel wants a language name, the contract uses the code.
BABEL_LANGS = {"en": "english", "es": "spanish", "pt": "portuguese", "gl": "galician", "fr": "french", "de": "german", "it": "italian", "ca": "catalan", "nl": "dutch", "da": "danish", "nb": "norsk", "sv": "swedish"}
# English is the default: the toolkit is consumed across languages, so the
# fallback cannot be the language of one of them. Declare document.language to
# get another one.
DEFAULT_BABEL_LANGUAGE = "english"

PLAN_VERSION = 1

FORMAT_PDF = "pdf"
FORMAT_EPUB = "epub"
FORMAT_HTML = "html"
FORMAT_CHOICES = (FORMAT_PDF, FORMAT_EPUB, FORMAT_HTML)

# EPUB records BCP 47 language tags, not babel names.
EPUB_LANGS = {"en": "en", "es": "es", "pt": "pt", "gl": "gl", "fr": "fr", "de": "de", "it": "it", "ca": "ca", "nl": "nl", "da": "da", "nb": "nb", "sv": "sv"}
DEFAULT_EPUB_LANGUAGE = "en"

# The HTML reader is a toolkit asset like the .tex styles: one path below the
# templates/ directory, never a builtin name a .tex configuration could select.
# It is resolved directly to keep the PDF template namespace clean.
HTML_READER_TEMPLATE = "templates/reader.html"

MISSING_SVG = (
    """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 16 16\">\n"
    "  <rect width=\"16\" height=\"16\" rx=\"2\" ry=\"2\" fill=\"#ddd\" stroke=\"#999\"/>\n"
    "  <text x=\"8\" y=\"11\" font-size=\"10\" text-anchor=\"middle\" fill=\"#666\">?</text>\n"
    "</svg>\n"""
)


def die(msg: str) -> NoReturn:
    print(f"❌ {msg}")
    raise SystemExit(1)


def natural_key(path: Path) -> list[tuple[int, int, str]]:
    """Sort key where digit runs compare numerically (chapter-2 < chapter-10)."""
    parts = re.split(r"(\d+)", path.name.lower())
    return [(0, len(part), part) if part.isdigit() else (1, 0, part) for part in parts]


def select_chapter_files(input_cfg: dict, chapters_dir: Path, format_name: str) -> list[Path]:
    explicit_files = input_cfg.get("explicit_files") or []
    if explicit_files:
        selected_files = []
        for name in explicit_files:
            # A file may gate itself to formats: a LaTeX-only switch is real for
            # the PDF and noise for an EPUB, so a plain string lands in every
            # format exactly as before, while an entry with a formats list only
            # joins the formats it names. The schema keeps the shape; here only
            # the per-format decision happens.
            if isinstance(name, dict):
                gated_formats = name.get("formats")
                if isinstance(gated_formats, list) and format_name not in gated_formats:
                    continue
                declared = name.get("file")
                if not isinstance(declared, str):
                    die(t(
                        "render.error.explicit_file_missing_field",
                        "Explicit file entry is missing its 'file' value: {entry}",
                        entry=json.dumps(name, sort_keys=True),
                    ))
                if not declared.strip():
                    die(t(
                        "render.error.explicit_file_blank",
                        "Explicit file entry has an empty 'file' value: {entry}",
                        entry=json.dumps(name, sort_keys=True),
                    ))
                name = declared
            candidate = chapters_dir / str(name)
            if not candidate.exists():
                die(t("render.error.explicit_file_missing", "Explicit file not found: {path}", path=candidate))
            selected_files.append(candidate)
        return selected_files

    pattern = str(input_cfg.get("glob", "*.md"))
    order = str(input_cfg.get("order", ORDER_NATURAL)).strip().lower()
    files = list(chapters_dir.glob(pattern))

    if order == ORDER_ALPHABETICAL:
        return sorted(files, key=lambda p: p.name)
    if order == ORDER_NATURAL:
        return sorted(files, key=natural_key)

    die(
        t(
            "render.error.order_invalid",
            "Invalid 'input.order' value: {value}. Supported values: {supported}",
            value=order,
            supported=", ".join(ORDER_CHOICES),
        )
    )


def resolve_suffix(raw_suffix: str | None) -> str:
    if not raw_suffix:
        return datetime.now().strftime("%Y%m%d")
    return raw_suffix.replace("${date:YYYYMMDD}", datetime.now().strftime("%Y%m%d"))


RUBY_YAML_SCRIPT = r"""
require 'yaml'
require 'json'
path = ARGV[0]
begin
  data = YAML.safe_load(File.read(path), permitted_classes: [], aliases: false)
  puts JSON.generate(data)
rescue => e
  STDERR.puts e.message
  exit 2
end
"""


def load_yaml_via_ruby(path: Path) -> dict | None:
    """Parse YAML through Ruby's stdlib and return plain data. None when Ruby is unavailable."""
    ruby_bin = shutil.which("ruby")
    if ruby_bin is None:
        return None

    proc = subprocess.run(
        [ruby_bin, "-e", RUBY_YAML_SCRIPT, str(path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 2:
        die(t("render.error.yaml_parse", "Could not parse YAML: {error}", error=proc.stderr.strip() or "invalid YAML"))
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except Exception as e:
        die(t("render.error.yaml_parse", "Could not parse YAML: {error}", error=e))


def load_yaml_map(path: Path) -> dict:
    if yaml is not None:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as e:
            die(t("render.error.yaml_parse", "Could not parse YAML: {error}", error=e))
    else:
        data = load_yaml_via_ruby(path)
        if data is None:
            die(t("render.error.no_yaml_parser", "No YAML parser available (install PyYAML or Ruby with stdlib YAML)"))

    if data is None:
        return {}
    if not isinstance(data, dict):
        die(t("render.error.yaml_root_object", "Root of {path} must be an object/map", path=path))
    return data


def toolkit_version(root_dir: Path) -> str:
    version_file = root_dir / "VERSION"
    try:
        value = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return value


def override_formats_from_env() -> list[str] | None:
    """The --formats override the CLI forwarded, validated against the enum.

    The CLI accepts the flag and passes it through the environment, so the
    renderer and any reader of the effective selection agree without parsing
    the argument themselves. An empty value is the absence of an override.
    """
    raw = os.environ.get("SKELEPRESS_FORMATS", "").strip()
    if not raw:
        return None
    values = [part.strip() for part in raw.split(",") if part.strip()]
    invalid = [part for part in values if part not in FORMAT_CHOICES]
    if invalid or not values:
        die(t("render.error.format_invalid", "Invalid 'output.formats' value: {value}. Supported values: {supported}",
              value=raw, supported=", ".join(FORMAT_CHOICES)))
    return list(dict.fromkeys(values))


def build_plan(cfg_user: dict, cfg_path: Path, root_dir: Path) -> dict:
    """Preserve single-format plans; use an ordered v2 job list for multiple outputs."""
    formats = cfg_user.get("output", {}).get("formats", [FORMAT_PDF])
    if not isinstance(formats, list) or not formats or any(f not in FORMAT_CHOICES for f in formats):
        die(t("render.error.format_invalid", "Invalid 'output.formats' value: {value}. Supported values: {supported}",
              value=formats, supported=", ".join(FORMAT_CHOICES)))
    override = override_formats_from_env()
    if override is not None:
        formats = override
    formats = list(dict.fromkeys(formats))
    jobs = [build_single_plan(cfg_user, cfg_path, root_dir, name) for name in formats]
    return jobs[0] if len(jobs) == 1 else {"plan_version": 2, "jobs": jobs}


def relative_cover_image(metadata_path: Path | None, document: dict, base_dir_path: Path) -> str | None:
    """The declared cover image when its value needs the project base to resolve.

    Precedence matches the rest of the contract: a metadata file wins and the
    free-form document map is only read when no file is configured. An already
    absolute value needs no help and is left to pandoc.
    """
    raw = ""
    if metadata_path is not None and metadata_path.exists():
        value = load_yaml_map(metadata_path).get("cover-image")
        raw = value if isinstance(value, str) else ""
    else:
        metadata_map = document.get("metadata")
        if isinstance(metadata_map, dict):
            value = metadata_map.get("cover-image")
            raw = value if isinstance(value, str) else ""

    raw = raw.strip()
    if not raw or Path(raw).is_absolute():
        return None
    return str((base_dir_path / raw).resolve())


def build_single_plan(cfg_user: dict, cfg_path: Path, root_dir: Path, format_name: str) -> dict:
    """Compute one render job without writing files or launching processes."""
    cfg = cfg_user

    required = ["project", "document", "input", "output", "pandoc"]
    for key in required:
        if key not in cfg or not isinstance(cfg[key], dict):
            die(t("render.error.required_section", "Invalid or missing required section: {section}", section=key))

    project = cfg["project"]
    document = cfg["document"]
    input_cfg = cfg["input"]
    output = cfg["output"]
    pandoc = cfg["pandoc"]

    base_dir = project.get("base_dir")
    if not base_dir:
        die(t("render.error.base_dir_required", "'project.base_dir' is required"))

    base_dir_path = (cfg_path.parent / str(base_dir)).resolve()
    stem = file_stem(document, output)
    # HTML-only plan details; an empty dict keeps PDF/EPUB plans byte-identical.
    html_plan_side_effects: dict = {}
    suffix = resolve_suffix(output.get("suffix"))

    chapters_dir = base_dir_path / str(input_cfg.get("chapters_dir", "chapters"))
    if not chapters_dir.exists():
        die(t("render.error.chapters_dir_missing", "input.chapters_dir does not exist: {path}", path=chapters_dir))

    selected_files = select_chapter_files(input_cfg, chapters_dir, format_name)
    if not selected_files:
        die(t("render.error.no_chapters", "No chapters found to render"))

    # Normalise: a consumer using "../out" should not see that in the report.
    output_dir = (base_dir_path / str(output.get("dir", "output"))).resolve()
    filename_out = f"{stem}-{suffix}"

    artifact_out = output_dir / f"{filename_out}.{format_name}"
    md_out = output_dir / f"{filename_out}.md"

    keep_merged_markdown = bool(output.get("keep_merged_markdown", True))

    compat = cfg.get("compat", {})
    # \clearpage is a LaTeX command: an EPUB has no TeX to interpret it, and an EPUB
    # plan carries no LaTeX-only markup. The compatibility switch is a typesetting
    # decision, so it only ever applies to the PDF.
    #
    # compat.clearpage_between_heading_level, when set, subsumes the legacy H1
    # rule: it selects the deepest heading level that starts a page (1..6) and
    # keeps the format gate, while the legacy flag keeps governing renders that
    # do not name the level. Configs that only set the flag are unchanged.
    heading_break_level = compat.get("clearpage_between_heading_level", 1)
    if isinstance(heading_break_level, bool) or not isinstance(heading_break_level, int) or not 1 <= heading_break_level <= 6:
        die(
            t(
                "render.error.heading_break_level_invalid",
                "'compat.clearpage_between_heading_level' must be an integer between 1 and 6",
            )
        )
    if "clearpage_between_heading_level" in compat:
        insert_clearpage = format_name == FORMAT_PDF
    else:
        insert_clearpage = format_name == FORMAT_PDF and bool(compat.get("legacy_clearpage_between_h1", True))

    raw_user_pandoc = cfg_user.get("pandoc")
    user_pandoc_cfg = raw_user_pandoc if isinstance(raw_user_pandoc, dict) else {}
    user_template_raw = str(user_pandoc_cfg.get("template", "")).strip()

    # The HTML target is decided by its output.html section: the reader shell is
    # the default, and the template it uses is always the toolkit's own.
    output_html_cfg = output.get("html") if isinstance(output.get("html"), dict) else {}
    html_reader = bool(output_html_cfg.get("reader", True))

    if user_template_raw:
        if template_runtime.is_bare_name(user_template_raw):
            builtin_template = template_runtime.builtin_path(root_dir, user_template_raw)
            if builtin_template is None:
                die(
                    t(
                        "template.error.unknown_name",
                        "Unknown template name '{name}'; use a path or one of: {allowed}",
                        name=user_template_raw,
                        allowed=", ".join(template_runtime.known_names()),
                    )
                )
            template_path = builtin_template
        else:
            template_path = Path(user_template_raw)
            if not template_path.is_absolute():
                template_path = (base_dir_path / template_path).resolve()
    else:
        template_path = template_runtime.default_path(root_dir)

    metadata_path = None
    metadata_raw = str(pandoc.get("metadata_file", ""))
    if metadata_raw.strip():
        metadata_path = Path(metadata_raw)
        if not metadata_path.is_absolute():
            metadata_path = (base_dir_path / metadata_path).resolve()

    resource_path_values = []
    for item in pandoc.get("resource_path", []):
        p = Path(str(item))
        if not p.is_absolute():
            p = (base_dir_path / p).resolve()
        resource_path_values.append(str(p))

    filters = cfg.get("filters", {})
    emoji_cfg = filters.get("emoji", {})
    mermaid_cfg = filters.get("mermaid", {})

    emoji_enabled = bool(emoji_cfg.get("enabled", True))
    mermaid_enabled = bool(mermaid_cfg.get("enabled", True))

    emoji_dir = Path(str(emoji_cfg.get("emoji_dir", "output/emoji")))
    if not emoji_dir.is_absolute():
        emoji_dir = (base_dir_path / emoji_dir).resolve()

    mermaid_output_dir = Path(str(mermaid_cfg.get("output_dir", "output/mermaid")))
    if not mermaid_output_dir.is_absolute():
        mermaid_output_dir = (base_dir_path / mermaid_output_dir).resolve()

    prepare_script = root_dir / "scripts/runtime/prepare-emojis.py"
    prepare_argv = None
    if emoji_enabled and prepare_script.exists():
        prepare_argv = [
            "python3",
            str(prepare_script),
            str(md_out),
            str(emoji_dir),
            str(root_dir / "filters/emoji"),
        ]

    cmd = ["pandoc", str(md_out)]
    # EPUB is not typeset: a TeX engine and the LaTeX template are PDF-only, and
    # pandoc leaves pdf_engine unused for it (the field stays required for now).
    # HTML is not typeset either: the reader template replaces the LaTeX one, and
    # a consumer's pandoc.template (a .tex asset) cannot speak to the HTML writer.
    if format_name == FORMAT_PDF:
        cmd.extend([
            f"--pdf-engine={pandoc.get('pdf_engine', 'xelatex')}",
            f"--template={template_path}",
        ])
        # What a top-level Markdown heading becomes (\section, \chapter, ...).
        # A typesetting decision, so PDF-only like the template; absent, empty
        # or 'default' passes no flag and Pandoc keeps its own behaviour.
        try:
            top_level_division_argument = top_level_division_runtime.argument(
                pandoc.get("top_level_division")
            )
        except ValueError as e:
            die(
                t(
                    top_level_division_runtime.ERROR_KEY,
                    top_level_division_runtime.ERROR_FALLBACK,
                    value=e.args[0] if e.args else "",
                    supported=", ".join(top_level_division_runtime.allowed_values()),
                )
            )
        if top_level_division_argument:
            cmd.append(top_level_division_argument)

    elif format_name == FORMAT_HTML:
        html_template_path: Path | None = None
        html_template_note = False
        if html_reader:
            # A declared template is a .tex asset: it cannot render HTML. The
            # pure plan records the note; execution prints it.
            html_template_note = user_template_raw != ""
            html_template_path = root_dir / HTML_READER_TEMPLATE
            if not html_template_path.is_file():
                die(
                    t(
                        "render.error.html_reader_template_missing",
                        "The HTML reader template is missing from the toolkit: {path}",
                        path=html_template_path,
                    )
                )
        # One self-contained artifact: section divs give the template the
        # chapter structure it navigates, and embed-resources inlines images as
        # data URIs, so the reading copy needs nothing from the project tree.
        cmd.extend(["-s", "--section-divs"])
        if html_reader and html_template_path is not None:
            cmd.append(f"--template={html_template_path}")
        cmd.append("--embed-resources")
        # HTML only: image work is deferred to the moment the reader gets there.
        cmd.append(f"--lua-filter={root_dir / 'filters/lazy-images.lua'}")
        html_plan_side_effects = {"html": {"reader": html_reader, "template_note": html_template_note}}

    if emoji_enabled:
        cmd.append(f"--lua-filter={root_dir / 'filters/emoji.lua'}")
    if mermaid_enabled:
        cmd.append(f"--lua-filter={root_dir / 'filters/mermaid.lua'}")

    # Always on: inline code cannot break in LaTeX, and a long path running past
    # the margin is not something a consumer should have to configure away.
    cmd.append(f"--lua-filter={root_dir / 'filters/inline-code-breaks.lua'}")

    # Always on: a {.page-break} heading class becomes \clearpage in LaTeX and
    # keeps the class elsewhere, where the EPUB stylesheet exposes the CSS hook.
    cmd.append(f"--lua-filter={root_dir / 'filters/heading-page-break.lua'}")

    for extra in filters.get("extra_lua_filters", []):
        extra_path = Path(str(extra))
        if not extra_path.is_absolute():
            extra_path = (base_dir_path / extra_path).resolve()
        cmd.append(f"--lua-filter={extra_path}")

    if bool(pandoc.get("toc", True)):
        cmd.append("--toc")
        cmd.append(f"--toc-depth={int(pandoc.get('toc_depth', 2))}")
    if bool(pandoc.get("number_sections", True)):
        cmd.append("--number-sections")

    if format_name == FORMAT_PDF:
        # The cover switch is emitted below with the rest of the document options;
        # an unconditional -V here would make titlepage: false impossible.
        cmd.extend(["-V", "fig-pos=!htbp"])
        # A PDF typesetting request, independent of metadata-file precedence.
        # False/absent emits nothing; consumer templates decide how to adopt it.
        if pandoc.get("running_headers") is True:
            cmd.extend(["-V", "running-headers=true"])
    # Pandoc resolves a relative asset against the working directory and then the
    # resource path. The project base is appended last, so a declared resource_path
    # keeps its priority and a project-relative asset resolves no matter where the
    # command was invoked. It is the directory the project declares as its own, not
    # a hidden default asset folder.
    resource_search = list(dict.fromkeys([*resource_path_values, str(base_dir_path)]))
    cmd.append(f"--resource-path={os.pathsep.join(resource_search)}")

    language = str(document.get("language") or "").strip()

    if format_name == FORMAT_EPUB:
        cmd.append(f"--include-in-header={root_dir / 'templates/epub-header.html'}")
        # A relative cover is resolved once, below. Pandoc's EPUB writer opens the
        # cover image directly and ignores the resource path, so a relative value
        # only resolves when the command happens to run from the project directory.
        cover_image = relative_cover_image(metadata_path, document, base_dir_path)
        # An EPUB3 package needs dc:title and dc:language to be a valid
        # publication; pandoc writes them from metadata, not from -V variables.
        # Match PDF precedence: a metadata file replaces document text fields;
        # document.language remains authoritative for either format.
        if metadata_path is not None and metadata_path.exists():
            cmd.append(f"--metadata-file={metadata_path}")
        else:
            for field in DOCUMENT_VAR_FIELDS:
                value = document.get(field)
                if isinstance(value, str) and value.strip():
                    cmd.extend(["--metadata", f"{field}={value}"])
            for key, value in (document.get("metadata") or {}).items():
                # Two --metadata values for one key arrive at pandoc as a MetaList,
                # and the EPUB writer then rejects the cover, so the resolved value
                # below is the only one emitted.
                if key == "cover-image" and cover_image is not None:
                    continue
                cmd.extend(["--metadata", f"{key}={value}"])
        cmd.extend(["--metadata", f"lang={EPUB_LANGS.get(language, DEFAULT_EPUB_LANGUAGE)}"])
        # CLI metadata outranks the metadata file, so this corrects the location of
        # the declared value without ever inventing a cover.
        if cover_image is not None:
            cmd.extend(["--metadata", f"cover-image={cover_image}"])
        cmd.extend(["-o", str(artifact_out)])
    elif format_name == FORMAT_HTML:
        # The HTML writer reads metadata, not LaTeX variables: same precedence
        # as the EPUB branch, with document.language carried as the lang code.
        if metadata_path is not None and metadata_path.exists():
            cmd.append(f"--metadata-file={metadata_path}")
        else:
            for field in DOCUMENT_VAR_FIELDS:
                value = document.get(field)
                if isinstance(value, str) and value.strip():
                    cmd.extend(["--metadata", f"{field}={value}"])
        cmd.extend(["--metadata", f"lang={EPUB_LANGS.get(language, DEFAULT_EPUB_LANGUAGE)}"])
        cmd.extend(["-o", str(artifact_out)])
    else:
        uses_metadata_file = metadata_path is not None and metadata_path.exists()
        # The image cover is a PDF page too, not just an EPUB artifact: resolve
        # the declared value once, against the project base, like the EPUB path.
        cover_image = relative_cover_image(metadata_path, document, base_dir_path)
        if uses_metadata_file:
            cmd.append(f"--metadata-file={metadata_path}")
        else:
            for field in DOCUMENT_VAR_FIELDS:
                value = document.get(field)
                if isinstance(value, str) and value.strip():
                    cmd.extend(["-V", f"{field}={value}"])

            # Free-form metadata is only meaningful when no metadata file wins (D5).
            extra_metadata = document.get("metadata")
            if isinstance(extra_metadata, dict):
                for key, value in extra_metadata.items():
                    # A relative cover-image is emitted below with its resolved
                    # location; two values for one key would reach the template
                    # ambiguously.
                    if key == "cover-image" and cover_image is not None:
                        continue
                    cmd.extend(["--metadata", f"{key}={value}"])

        # Language and the cover switch are typesetting decisions, not cover text, so
        # they apply even when a metadata file provides the title page.
        cmd.extend(["-V", f"babel-lang={BABEL_LANGS.get(language, DEFAULT_BABEL_LANGUAGE)}"])
        titlepage = document.get("titlepage", True)
        cmd.extend(["--metadata", "titlepage=true" if titlepage is not False else "titlepage=false"])
        # CLI metadata outranks the metadata file, so this corrects the location
        # of the declared value without ever inventing a cover. The template
        # prints the image page when the variable is set, before the title page
        # and independently of the titlepage switch.
        if cover_image is not None:
            cmd.extend(["--metadata", f"cover-image={cover_image}"])
        cmd.extend(["-o", str(artifact_out)])

    return {
        "plan_version": PLAN_VERSION,
        "toolkit": {"version": toolkit_version(root_dir), "root": str(root_dir)},
        "config": {"path": str(cfg_path), "base_dir": str(base_dir_path)},
        "chapters": [str(p) for p in selected_files],
        "pandoc": {
            # The produced artifact is named after the format, so a PDF plan keeps
            # its recorded shape and an EPUB plan cannot claim to produce a PDF.
            "target": {"markdown": str(md_out), format_name: str(artifact_out)},
            "argv": cmd,
            "cwd": None,
        },
        "env": {
            "PANDOC_EMOJI_DIR": str(emoji_dir),
            "PANDOC_EMOJI_BALLOT_ICONS": "1" if bool(emoji_cfg.get("include_ballot_icons", True)) else "0",
            "PANDOC_MERMAID_OUTPUT_DIR": str(mermaid_output_dir),
            "PANDOC_MERMAID_BACKGROUND": str(mermaid_cfg.get("background", "transparent")),
            "PANDOC_MERMAID_BACKGROUND_EXPLICIT": "1" if "background" in mermaid_cfg else "0",
        },
        "side_effects": {
            "keep_merged_markdown": keep_merged_markdown,
            "clearpage_between_h1": insert_clearpage,
            "heading_break_level": heading_break_level,
            **html_plan_side_effects,
            "emoji": {
                "enabled": emoji_enabled,
                "dir": str(emoji_dir),
                "missing_svg": str(emoji_dir / "_missing.svg"),
                "prepare_argv": prepare_argv,
            },
            "mermaid": {
                "enabled": mermaid_enabled,
                "dir": str(mermaid_output_dir),
                "background": str(mermaid_cfg.get("background", "transparent")),
            },
        },
    }


# A Markdown link to one of the selected chapter files. Absolute URLs and paths
# rooted at the filesystem are never siblings.
SIBLING_LINK = re.compile(r"\]\((?!https?://|/)([^)\s#]+?\.md)(#[^)\s]*)?\)")


def sibling_link_markers(chapters: list[str], texts: list[str]) -> dict[str, str]:
    """One anchor per chapter file that another chapter links to.

    Empty for a project with no cross-references, which keeps its merged Markdown
    byte-identical: nothing is injected when nothing needs it.
    """
    names = {Path(path).name for path in chapters}
    targets = set()
    for text in texts:
        for match in SIBLING_LINK.finditer(text):
            name = Path(match.group(1)).name
            if name in names:
                targets.add(name)
    return {name: f"ch-{slugify(Path(name).stem)}" for name in sorted(targets)}


def fenced_lines(text: str) -> set[int]:
    """Line numbers (0-based) that belong to fenced code, CommonMark-shaped.

    A fence opens on a run of at least three backticks or tildes and stays
    open until a closing run of the same character with at least that length,
followed only by spaces or tabs on its line. A shorter or mixed
    run inside a fence is content, not a boundary: a ~~~ block holding a
    literal ``` line closes at its own ~~~, and a 4-backtick block keeps a
    literal ``` fenced. The one answer feeds rewriting, id planning and id
    injection, so the three passes cannot disagree about what is code.
    """
    fenced: set[int] = set()
    delim_char = ""
    delim_len = 0
    for index, line in enumerate(text.splitlines(keepends=True)):
        run = line.lstrip()
        ch = run[:1]
        run_len = len(run) - len(run.lstrip(ch)) if ch in ("`", "~") else 0
        if delim_char:
            fenced.add(index)
            if run_len >= delim_len and ch == delim_char and not run[run_len:].strip():
                # Both delimiters need a bare closer: trailing text after the
                # run makes the line content, not a boundary (CommonMark
                # closing fence).
                delim_char = ""
        elif run_len >= 3:
            info = run[run_len:].strip()
            if ch == "`" and "`" in info:
                # A backtick opener must not carry backticks in its info
                # string; such a line is a paragraph, not a fence.
                continue
            delim_char = ch
            delim_len = run_len
            fenced.add(index)
    return fenced


# A bare same-chapter anchor link. Unlike SIBLING_LINK it carries no file
# path: Pandoc resolves it against the current document's own auto ids.
SELF_LINK = re.compile(r"\]\(#([^)\s]+)\)")


def rewrite_sibling_links(
    text: str,
    markers: dict[str, str],
    fragment_ids: dict[str, dict[str, str]] | None = None,
    missing_note: str = "",
    self_ids: dict[str, str] | None = None,
) -> str:
    """Point a link at an in-document anchor instead of a file the merge removes.

    A link with a fragment lands on the explicit id of the matching target
    heading. A fragment naming no heading falls back to the chapter anchor with
    a reader-visible note, so the degradation is visible, not silent. Fenced
    code is left alone: a chapter that documents the link syntax must not have
    its example rewritten.

    A same-chapter self-link (](#slug)) keeps Pandoc's auto id, which still
    exists — unless the target heading is one whose explicit derived id this
    very run injects, because an explicit id replaces the auto id and the bare
    link would dangle (issue #241). When self_ids carries the chapter's own
    mapping, such a self-link follows the rename like any cross-chapter link.
    """
    fragment_ids = fragment_ids or {}
    self_ids = self_ids or {}

    def replace(match: re.Match[str]) -> str:
        name = Path(match.group(1)).name
        marker = markers.get(name)
        fragment = match.group(2)
        if fragment:
            body = fragment[1:]
            target_id = fragment_ids.get(name, {}).get(slugify(body)) if body else None
            if target_id:
                return f"](#{target_id})"
            # No heading answers the fragment: land on the chapter and say so.
            # A fragment that named a missing section gets the visible note; an
            # empty fragment ("file.md#") names the top of the file, so it
            # degrades to the chapter anchor without the note.
            if marker:
                if body and missing_note:
                    return f"](#{marker}) *{missing_note}*"
                return f"](#{marker})"
            return match.group(0)
        return f"](#{marker})" if marker else match.group(0)

    rewritten = []
    fenced = fenced_lines(text)
    for index, line in enumerate(text.splitlines(keepends=True)):
        if index in fenced:
            rewritten.append(line)
            continue
        line = SIBLING_LINK.sub(replace, line)
        if self_ids:
            # Only a slug this run renames needs the follow; every other
            # bare anchor still resolves to Pandoc's own auto id.
            line = SELF_LINK.sub(
                lambda m: f"](#{self_ids[m.group(1)]})" if m.group(1) in self_ids else m.group(0),
                line,
            )
        rewritten.append(line)
    return "".join(rewritten)


def with_marker(text: str, marker: str) -> str:
    """Place the anchor inside the chapter's own spine document.

    Pandoc splits the merged document at top-level headings, so an anchor written
    before the heading would belong to the previous section. A chapter without a
    heading is not a split point, so its content stays with the previous document
    and the anchor belongs at its start.
    """
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            lines.insert(index + 1, f"\n\n[]{{#{marker}}}\n\n")
            return "".join(lines)
        break
    return "[]{#" + marker + "}\n\n" + text


def sibling_fragment_ids(chapters: list[str], texts: list[str], markers: dict[str, str]) -> dict[str, dict[str, str]]:
    """Per-target-chapter fragment slugs that resolve, with the id each heading gets.

    Only fragments actually referenced across chapters are planned, and only for
    chapters whose fragment links resolve. A heading-less target has no section
    to point at, so its fragments degrade visibly instead of inventing ids.
    """
    wanted: dict[str, set[str]] = {}
    for text in texts:
        # The planner must see what rewrite_sibling_links sees: fenced lines
        # are never rewritten, so a fragment link quoted inside an example is
        # not a real reference and must not plan any id.
        fenced = fenced_lines(text)
        for index, line in enumerate(text.splitlines()):
            if index in fenced:
                continue
            for match in SIBLING_LINK.finditer(line):
                name = Path(match.group(1)).name
                fragment = match.group(2)
                if not fragment or not fragment[1:] or name not in markers:
                    continue
                wanted.setdefault(name, set()).add(slugify(fragment[1:]))

    resolved: dict[str, dict[str, str]] = {}
    # Derived ids reserve globally: the textual marker of a differently named
    # chapter (ch-<stem> of a-b.md) can spell the same string as a derived
    # heading id (ch-<stem>-<slug> of a.md), so the reservation starts from
    # every chapter marker and every id an earlier chapter already took.
    used_global: set[str] = set(markers.values())
    for name, slugs in wanted.items():
        path = next(path for path in chapters if Path(path).name == name)
        text = texts[chapters.index(path)]
        used: set[str] = set(used_global)
        mapping: dict[str, str] = {}
        prefix = markers[name]
        # The planner must agree with with_explicit_ids on what is a heading:
        # fenced lines are never injected, and a heading carrying an
        # author-written {#id} is author-owned and never injected either.
        # Planning an id the injector would not emit would rewrite the link to
        # a dangling anchor instead of the visible missing-section fallback.
        fenced = fenced_lines(text)
        for line_number, line in enumerate(text.splitlines()):
            if line_number in fenced:
                continue
            if re.search(r"\{#[^}]*\}", line):
                continue
            heading = re.match(r"#{1,6} (.+?)\s*$", line)
            if not heading:
                continue
            slug = slugify(heading.group(1))
            if slug not in slugs:
                continue
            candidate = f"{prefix}-{slug}"
            deduped, suffix = candidate, 1
            while deduped in used:
                deduped, suffix = f"{candidate}-{suffix}", suffix + 1
            used.add(deduped)
            mapping.setdefault(slug, deduped)
        used_global.update(mapping.values())
        if mapping:
            resolved[name] = mapping
    return resolved


def with_explicit_ids(text: str, mapping: dict[str, str]) -> str:
    """Append the explicit id to the headings the mapping assigns.

    Only the first occurrence of a repeated heading keeps the derived id; later
    duplicates carry a suffix so explicit ids never collide. Fenced code is left
    alone, like sibling-link rewriting.
    """
    lines = text.splitlines(keepends=True)
    fenced = fenced_lines(text)
    used: set[str] = set()
    for index, line in enumerate(lines):
        if index in fenced:
            continue
        heading = re.match(r"(#{1,6} .+?)(\s*\{#[^}]*\})?(\s*)$", line)
        if not heading or heading.group(2):
            # A heading that already carries an author-written explicit id is
            # author-owned and stays untouched.
            continue
        slug = slugify(heading.group(1)[heading.group(1).index(" ") + 1:])
        if slug not in mapping:
            continue
        candidate = mapping[slug]
        suffix = 1
        while candidate in used:
            candidate = f"{mapping[slug]}-{suffix}"
            suffix += 1
        used.add(candidate)
        lines[index] = f"{heading.group(1)} {{#{candidate}}}{heading.group(3)}"
    return "".join(lines)


def merged_markdown(
    chapters: list[str],
    insert_clearpage: bool,
    heading_break_level: int = 1,
    document_language: str = "",
) -> str:
    texts = [Path(raw_path).read_text(encoding="utf-8", errors="ignore") for raw_path in chapters]
    # Chapters become sections of one document, so a link to a sibling file would
    # point at a file the publication does not contain. Anchors are injected only
    # for chapters something actually links to.
    markers = sibling_link_markers(chapters, texts)
    fragment_ids = sibling_fragment_ids(chapters, texts, markers) if markers else {}
    # A fragment naming no heading lands on the chapter with a reader-visible
    # note; the note belongs to the document, so it follows the configured
    # language, not the operator's environment.
    missing_note = t_for(
        document_language,
        "render.fragment.section_not_found",
        "section not found",
    ) if any(
        link_match.group(2) and link_match.group(2)[1:]
        for text in texts
        for link_match in SIBLING_LINK.finditer(text)
    ) else ""
    parts = []
    # Unequal lists must fail loudly, never truncate silently: this keeps the
    # guarantee zip(..., strict=True) gave on Python 3.10, which 3.9 does not
    # support.
    if len(chapters) != len(texts):
        die(
            t(
                "render.error.chapter_count_mismatch",
                "Chapter count mismatch: {chapters} chapters but {texts} chapter texts",
                chapters=len(chapters),
                texts=len(texts),
            )
        )
    # Index access instead of zip(): the parameter that would pin this pair
    # (strict=True) needs Python 3.10, and the equality check above is the 3.9
    # way to keep the same guarantee.
    for index, raw_path in enumerate(chapters):
        text = texts[index]
        if markers:
            text = rewrite_sibling_links(
                text, markers, fragment_ids, missing_note,
                fragment_ids.get(Path(raw_path).name),
            )
            # Explicit ids are only planned when a fragment actually resolves;
            # injecting ids for planned slugs that the chapter does not own
            # would fabricate anchors the links cannot use.
            mapping = fragment_ids.get(Path(raw_path).name)
            if mapping:
                text = with_explicit_ids(text, mapping)
        if index > 0 and insert_clearpage:
            first_nonempty = ""
            for line in text.splitlines():
                if line.strip():
                    first_nonempty = line
                    break
            # A heading at heading_break_level or shallower starts a page. With
            # the default level 1 this is exactly the legacy "# " check.
            if re.match(r"#{1," + str(heading_break_level) + r"} ", first_nonempty):
                parts.append("\n\n\\clearpage\n\n")
        marker = markers.get(Path(raw_path).name)
        if marker:
            # An empty span with an id is \phantomsection\label in LaTeX and a
            # <span id> in HTML and EPUB, so one anchor serves both formats.
            text = with_marker(text, marker)
        parts.append("\n")
        parts.append(text)
        parts.append("\n\n")
    return "".join(parts)


def plan_document_language(plan: dict) -> str:
    """The configured document language; reader-visible merge content follows it."""
    try:
        document = load_yaml_map(Path(plan["config"]["path"])).get("document") or {}
    except SystemExit:
        # The config was validated during planning; a failure here means the
        # file vanished mid-run, so merge content keeps the neutral default.
        return ""
    language = str(document.get("language") or "").strip()
    return language or "en"


def artifact_target(plan: dict) -> tuple[str, str]:
    """The artifact the plan produces: the single target that is not the merged markdown."""
    target = plan["pandoc"]["target"]
    for name in FORMAT_CHOICES:
        if name in target:
            return name, target[name]
    die(t("render.error.plan_target_missing", "Render plan declares no output artifact"))


def output_label_key(format_name: str) -> str:
    if format_name == FORMAT_EPUB:
        return "render.output.epub"
    if format_name == FORMAT_HTML:
        return "render.output.html"
    return "render.output.pdf"


def execute_plan(plan: dict) -> int:
    """Attempt every format; keep successful artifacts and diagnostics on failure."""
    if "jobs" not in plan:
        return execute_single_plan(plan)
    failed = False
    for job in plan["jobs"]:
        # Keep Markdown until every job succeeds, including failures before a
        # later successful job which would otherwise delete diagnostic input.
        retained = {**job, "side_effects": {**job["side_effects"], "keep_merged_markdown": True}}
        try:
            code = execute_single_plan(retained)
        except OSError as error:
            print(str(error), file=sys.stderr)
            code = 1
        if code:
            failed = True
            name, _ = artifact_target(job)
            print(t("render.error.format_failed",
                    "Export failed ({format}); successful outputs are kept.", format=name))
    if not failed:
        for job in plan["jobs"]:
            if not job["side_effects"]["keep_merged_markdown"]:
                Path(job["pandoc"]["target"]["markdown"]).unlink(missing_ok=True)
    return 1 if failed else 0


def execute_single_plan(plan: dict) -> int:
    """Materialise and run one job; PDF behavior is unchanged."""
    target = plan["pandoc"]["target"]
    format_name, artifact_raw = artifact_target(plan)
    md_out = Path(target["markdown"])
    artifact_out = Path(artifact_raw)
    side_effects = plan["side_effects"]
    html_effects = side_effects.get("html") or {}
    if html_effects.get("template_note"):
        # Recorded by the pure plan when a configured pandoc.template cannot
        # speak to the HTML writer; execution prints it beside the command.
        print(
            f"⚠️  {t('render.error.html_template_conflict', 'A configured pandoc.template only applies to PDF: the HTML target uses the toolkit reader template.')}"
        )

    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(
        merged_markdown(
            plan["chapters"],
            bool(side_effects["clearpage_between_h1"]),
            int(side_effects.get("heading_break_level", 1)),
            document_language=plan_document_language(plan),
        ),
        encoding="utf-8",
    )

    emoji = side_effects["emoji"]
    if emoji["enabled"]:
        emoji_dir = Path(emoji["dir"])
        emoji_dir.mkdir(parents=True, exist_ok=True)
        missing_svg = Path(emoji["missing_svg"])
        if not missing_svg.exists():
            missing_svg.write_text(MISSING_SVG, encoding="utf-8")

        prepare_argv = emoji["prepare_argv"]
        if prepare_argv:
            prep = subprocess.run(prepare_argv)
            if prep.returncode != 0:
                print(f"⚠️  {t('render.warn.emoji_prepare', 'Could not auto-prepare emojis; continuing with fallback')}")

    if side_effects["mermaid"]["enabled"]:
        Path(side_effects["mermaid"]["dir"]).mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(plan["env"])

    mermaid_failures = Path(side_effects["mermaid"]["dir"]) / "_failed.txt"
    if mermaid_failures.exists():
        mermaid_failures.unlink(missing_ok=True)

    print(f"✅ {t('render.mode.native', 'Native mode enabled')}")
    print(f"📄 {t('render.output.markdown', 'Merged markdown: {path}', path=md_out)}")
    print(f"🖨️  {t(output_label_key(format_name), 'Output: {path}', path=artifact_out)}")
    print(f"▶ {t('render.command.exec', 'Running: {command}', command=' '.join(plan['pandoc']['argv']))}")

    result = subprocess.run(plan["pandoc"]["argv"], env=env)
    if result.returncode == 0 and not side_effects["keep_merged_markdown"]:
        md_out.unlink(missing_ok=True)

    failed = []
    if mermaid_failures.exists():
        failed = [line for line in mermaid_failures.read_text(encoding="utf-8").splitlines() if line.strip()]
        mermaid_failures.unlink(missing_ok=True)

    if result.returncode == 0 and failed:
        printed = ", ".join(failed[:10])
        print(
            t(
                "render.error.mermaid_failed",
                "❌ {count} Mermaid diagram(s) could not be rendered and would print as code: {diagrams}",
                count=len(failed),
                diagrams=printed,
            )
        )
        print(
            t(
                "render.error.mermaid_failed.hint",
                "   Run `skelepress doctor` to diagnose, or set filters.mermaid.enabled: false to drop the diagrams on purpose.",
            )
        )
        return 1

    return result.returncode


def print_plan(plan: dict) -> None:
    if "jobs" in plan:
        for job in plan["jobs"]:
            print_plan(job)
        return
    target = plan["pandoc"]["target"]
    format_name, artifact_raw = artifact_target(plan)
    print(t("render.plan.title", "Render plan (dry run, nothing written)"))
    print(f"📄 {t('render.output.markdown', 'Merged markdown: {path}', path=target['markdown'])}")
    print(f"🖨️  {t(output_label_key(format_name), 'Output: {path}', path=artifact_raw)}")
    print(
        f"▶ {t('render.plan.command', 'Command: {command}', command=' '.join(plan['pandoc']['argv']))}"
    )


def main() -> None:
    argv = sys.argv[1:]
    plan_mode = None
    positional: list[str] = []
    for arg in argv:
        if arg == "--plan-json":
            plan_mode = "json"
        elif arg == "--plan":
            plan_mode = plan_mode or "human"
        else:
            positional.append(arg)

    if len(positional) < 2:
        die(t("render.error.usage", "Usage: render-native.py <config.yaml> <toolkit_root> [--plan|--plan-json]"))

    cfg_path = Path(positional[0])
    root_dir = Path(positional[1])

    if not cfg_path.exists():
        die(t("render.error.config_not_found", "Config not found: {path}", path=cfg_path))

    cfg_user = load_yaml_map(cfg_path)
    plan = build_plan(cfg_user, cfg_path, root_dir)

    if plan_mode == "json":
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        raise SystemExit(0)
    if plan_mode == "human":
        print_plan(plan)
        raise SystemExit(0)

    # An execution-only guard: plans/defaults/custom templates/EPUB stay inert.
    # Share the exact doctor predicate, lookup and localized failure surface.
    if cfg_user.get("pandoc", {}).get("running_headers") is True:
        import preflight

        if not preflight.guard_running_headers(cfg_user, cfg_path):
            raise SystemExit(1)
    raise SystemExit(execute_plan(plan))


if __name__ == "__main__":
    main()
