#!/usr/bin/env python3
"""build.py - the bookkit tool.

One adapter for both book shapes:

* A **single volume**: a project directory with a ``manifest.yaml`` and no
  ``series.yaml``. The project directory is itself the volume.
* A **series**: a project directory with a ``series.yaml`` that holds the
  shared facts (collection, author, publisher, rights, language) and an
  ordered ``volumes`` list of volume directory names, each with its own
  ``manifest.yaml``.

Both YAML files are validated against this tool's own contract
(``manifest.schema.json`` and ``series.schema.json``) before anything else
happens. For every volume the tool then:

1. merges the series defaults under the volume's own overrides;
2. resolves every declared content path against the volume directory,
   failing when a printable file is missing, warning and skipping when an
   entry is declared ``optional``, and silently excluding ``print: false``
   entries;
3. generates the LaTeX mode-switch files (``\\mainmatter``, plus
   ``\\setcounter{chapter}`` when the volume declares ``chapter_start``,
   and ``\\appendix`` before the back matter) into the run output, so the
   content files carry no LaTeX markers;
4. writes one ``skelepress.config.yaml`` per volume into the run output;
5. renders it through the public CLI (``bin/skelepress render``), unless
   ``--check`` asked only for validation and the generated configurations.

The tool belongs to the book, not to the pdf.config contract: the toolkit
only ever sees a standard ``skelepress.config.yaml``. It runs from any working
directory, uses no absolute paths and no network, and reads YAML through the
toolkit's own shared loader (``scripts/runtime/schema_runtime.py``): PyYAML
when available, Ruby's stdlib YAML through a subprocess otherwise; without
either parser it fails with a clear message.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path, PurePosixPath
from tempfile import mkstemp
from typing import NoReturn

TOOL_DIR = Path(__file__).resolve().parent
TOOLKIT_ROOT = TOOL_DIR.parents[2]
RUNTIME_DIR = TOOLKIT_ROOT / "scripts" / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

# The shared runtime lives two directories up; it is imported by path so the
# tool works no matter where it is invoked from.
schema_runtime = importlib.import_module("schema_runtime")
load_yaml = schema_runtime.load_yaml
validate_with_schema = schema_runtime.validate_with_schema
template_runtime = importlib.import_module("template_runtime")
is_bare_name = template_runtime.is_bare_name

CLI = TOOLKIT_ROOT / "bin" / "skelepress"
MANIFEST_SCHEMA = TOOL_DIR / "manifest.schema.json"
SERIES_SCHEMA = TOOL_DIR / "series.schema.json"
# The default template is the builtin name: the toolkit ships templates/book.tex
# inside the artifact, so one generated configuration works in a checkout and in
# an installation. --template still accepts a path.
DEFAULT_TEMPLATE = "book"
DEFAULT_OUT = Path(".skelepress")
DATE_SUFFIX = "${date:YYYYMMDD}"

LANG_CODES = ("en", "es", "pt", "gl")

# How the contents are separated into blocks, at the two boundaries the
# adapter controls: before the first chapter and before the first appendix.
TOC_SEPARATORS = ("none", "space", "rule", "label")
DEFAULT_TOC_SEPARATORS = "space"
# The only format that consumes the LaTeX switches: format_gated_entry gates
# its entries to it and emit_config keeps xelatex in runtime.required_commands
# exactly when a volume requests it.
LATEX_ONLY_FORMAT = "pdf"


def die(message: str) -> NoReturn:
    print(f"build.py: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"build.py: warning: {message}", file=sys.stderr)


# --- Small helpers ----------------------------------------------------------


def slugify(value: str) -> str:
    """Lowercase, ASCII, single dashes; the toolkit's own naming rule.

    NFKD decomposition first, like the renderer's slugify (scripts/runtime/
    render-native.py): accented Latin letters transliterate to their base
    letter (Informe Ñandú -> informe-nandu, as docs/user/usage.md documents)
    instead of being silently dropped by a raw ASCII encode.
    """

    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-") or "volume"


def quoted(value: str) -> str:
    """A safe double-quoted YAML scalar."""

    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def relpath(target: Path, start: Path) -> str:
    """A relative path with forward slashes, usable inside a config."""

    return Path(os.path.relpath(target, start)).as_posix()


def natural_key(name: str) -> list[tuple[int, int, str]]:
    """Sort key where digit runs compare numerically (chapter-2 < chapter-10).

    Mirrors the toolkit's own 'natural' order (scripts/runtime/render-native.py).
    """

    return [(0, len(part), part) if part.isdigit() else (1, 0, part) for part in re.split(r"(\d+)", name.lower())]


def default_template_hint() -> str:
    """What to tell a consumer whose explicit template path does not exist."""
    return (
        "pass --template with a book-class LaTeX template, or omit it to use"
        f" the toolkit's builtin '{DEFAULT_TEMPLATE}' template"
    )


# --- Manifest model ---------------------------------------------------------


class Entry:
    """One declared content entry: a path string or a map with file/print/optional.

    The contract schemas already enforce the shape; these checks remain as
    the tool's own defense and keep the documented error messages.
    """

    section: str
    logical: str
    volume: str
    file: str
    do_print: bool
    optional: bool
    listed: bool

    def __init__(self, section: str, logical: str, raw: object, volume: str) -> None:
        self.section = section
        self.logical = logical
        self.volume = volume
        if isinstance(raw, str):
            self.file = raw
            self.do_print = True
            self.optional = False
            self.listed = True
            return
        if not isinstance(raw, dict):
            die(
                f"volume '{volume}': entry '{logical}' ({section})"
                " must be a path string or a mapping with 'file'"
            )
        file_value = raw.get("file")
        if not isinstance(file_value, str) or not file_value.strip():
            die(
                f"volume '{volume}': entry '{logical}' ({section})"
                " must declare a 'file' path"
            )
        self.file = file_value
        do_print = raw.get("print", True)
        if not isinstance(do_print, bool):
            die(f"volume '{volume}': entry '{logical}' ({section}): 'print' must be a boolean")
        self.do_print = do_print
        optional = raw.get("optional", False)
        if not isinstance(optional, bool):
            die(f"volume '{volume}': entry '{logical}' ({section}): 'optional' must be a boolean")
        self.optional = optional
        listed = raw.get("toc", True)
        if not isinstance(listed, bool):
            die(f"volume '{volume}': entry '{logical}' ({section}): 'toc' must be a boolean")
        self.listed = listed

    def resolve(self, volume_dir: Path) -> str | None:
        """The declared path when it belongs in the PDF, else None.

        ``print: false`` excludes the entry silently. A missing file fails
        with the volume, the logical name and the path, unless the entry is
        declared ``optional``, in which case it is skipped with a warning.
        """
        if not self.do_print:
            return None
        if not (volume_dir / self.file).is_file():
            if self.optional:
                warn(
                    f"volume '{self.volume}': {self.section} entry '{self.logical}'"
                    " is optional and its file was not found, skipped: "
                    f"{self.file}"
                )
                return None
            die(
                f"volume '{self.volume}': {self.section} entry '{self.logical}'"
                f" declares a missing file: {self.file}"
            )
        return self.file


def ordered_entries(section: str, raw: object, volume: str) -> list[Entry]:
    """front_matter/back_matter: an ordered map of logical name to entry."""

    if raw is None:
        return []
    if not isinstance(raw, dict) or not raw:
        die(f"volume '{volume}': '{section}' must be a non-empty map of name to entry")
    return [Entry(section, str(name), value, volume) for name, value in raw.items()]


def ordered_chapters(chapters_dir: str, volume: str, volume_dir: Path) -> list[Entry]:
    """chapters: ordered — every *.md in chapters_dir, in natural order."""

    base = volume_dir / chapters_dir
    if not base.is_dir():
        die(f"volume '{volume}': 'chapters_dir' is not a directory: {chapters_dir}")
    names = sorted((p.name for p in base.glob("*.md") if p.is_file()), key=natural_key)
    if not names:
        die(f"volume '{volume}': no chapters found in '{chapters_dir}'")
    return [
        Entry("chapters", str(index + 1), (Path(chapters_dir) / name).as_posix(), volume)
        for index, name in enumerate(names)
    ]


def chapter_entries(raw: object, volume: str) -> list[Entry]:
    """chapters: an explicit ordered list of entries (schema already enforced)."""

    if not isinstance(raw, list) or not raw:
        die(f"volume '{volume}': 'chapters' must be the keyword 'ordered' or a non-empty list")
    return [
        Entry("chapters", str(index + 1), item, volume)
        for index, item in enumerate(raw)
    ]


# --- Volume build -----------------------------------------------------------


def resolve_entries(entries: list[Entry], volume_dir: Path) -> list[str]:
    resolved = []
    for entry in entries:
        path = entry.resolve(volume_dir)
        if path is not None:
            resolved.append(path)
    return resolved


def resolve_listed(entries: list[Entry], volume_dir: Path) -> list[tuple[str, bool]]:
    """The same resolution, keeping whether each entry belongs in the contents."""
    resolved: list[tuple[str, bool]] = []
    for entry in entries:
        path = entry.resolve(volume_dir)
        if path is not None:
            resolved.append((path, entry.listed))
    return resolved


def with_toc_guards(
    pairs: list[tuple[str, bool]],
    generated_dir: Path,
    volume_dir: Path,
    counter: list[int],
) -> list[str]:
    """Interleave the switches the template understands around unlisted entries.

    An entry declared ``toc: false`` is surrounded by two generated mode files,
    so its heading stays out of the contents without the tool reading or
    rewriting the Markdown. The template keeps the quoted chapter command out of
    the table of contents until the switch is turned back on.
    """
    files: list[str] = []
    for path, listed in pairs:
        if listed:
            files.append(path)
            continue
        off = generated_dir / f"{counter[0]:02d}-toc-off.md"
        counter[0] += 1
        write_mode_file(off, "\\BookChaptersUnlisted\n")
        on = generated_dir / f"{counter[0]:02d}-toc-on.md"
        counter[0] += 1
        write_mode_file(on, "\\BookChaptersListed\n")
        files.append(relpath(off, volume_dir))
        files.append(path)
        files.append(relpath(on, volume_dir))
    return files


_LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "%": r"\%",
    "#": r"\#",
    "&": r"\&",
    "_": r"\_",
    "$": r"\$",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(text: str) -> str:
    """A short label, safe to embed in the contents file."""
    return "".join(_LATEX_SPECIALS.get(char, char) for char in text)


def toc_separator_block(style: str, label: str | None, macro: str) -> str:
    """The LaTeX that separates one block of the contents.

    The block defines its own macro before using it, so a volume built with a
    custom book-class template compiles without that template declaring anything.
    """
    if style == "none":
        return ""
    if style == "space":
        body = r"\protect\vspace{1.2em}"
    elif style == "rule":
        body = (
            r"\protect\vspace{0.8em}\protect\noindent"
            r"\protect\rule{\protect\linewidth}{0.4pt}"
            r"\protect\par\protect\vspace{0.6em}"
        )
    else:
        body = (
            r"\protect\vspace{1em}\protect\noindent{\protect\bfseries "
            + latex_escape(label or "")
            + r"}\protect\par\protect\vspace{0.4em}"
        )
    return (
        f"\\providecommand{{\\{macro}}}{{\\addtocontents{{toc}}{{{body}}}}}"
        f"\n\\{macro}\n"
    )


def write_mode_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def merge_defaults(manifest: dict, defaults: dict) -> dict:
    """Series facts sit under the volume's own overrides."""
    # Every field a series may set once for all of its volumes. A field missing
    # from this tuple is silently ignored at series level, which is why the two
    # contents fields belong here: the examples declare them exactly there.
    shared = (
        "collection",
        "author",
        "publisher",
        "rights",
        "language",
        "running_headers",
        "toc_separators",
        "toc_labels",
        "formats",
        "template",
    )
    merged = dict(manifest)
    for key in shared:
        if key not in merged and key in defaults:
            merged[key] = defaults[key]
    return merged


def resolve_template(raw: str, base: Path, volume_name: str) -> str:
    """A declared template: a bare name is shipped, any other value is a path.

    The path is relative to the directory holding the manifest that declared
    it (the volume directory, or the series directory for a series default)
    and must exist before anything is built, exactly like the flag's own path.
    """
    value = raw.strip()
    if is_bare_name(value):
        # A name is a template the toolkit ships, so the validator and the
        # renderer resolve it and there is no path to check here.
        return value
    if PurePosixPath(value).is_absolute():
        # The contract keeps declared templates inside the project: a path is
        # relative to the directory holding the file that declares it, and an
        # absolute value would reach outside it. The --template flag is the
        # one-shot escape hatch and resolves its own value instead.
        die(
            f"volume '{volume_name}': 'template' must be a builtin name or a"
            f" path relative to the directory holding the file, got: {value}"
        )
    resolved = (base / value).resolve()
    if not resolved.is_file():
        die(f"volume '{volume_name}': template file not found: {resolved}")
    return str(resolved)


def volume_output_dir(out_root: Path, project: Path, volume_name: str, is_series: bool) -> Path:
    # A series nests one output directory per volume; a single-volume project
    # is its own volume and does not repeat its name.
    project_out = out_root / project.name
    return project_out / volume_name if is_series else project_out


def volume_prefix(project: Path, position: int) -> str:
    """The composed file_prefix opener for one series volume.

    A series volume's file name must sort with its series and identify it
    without the folder tree, so the generated prefix opens with the series
    slug and the 1-based volume ordinal — the same value \\#230's cross-check
    validates and templates receive as ``$volume$``. Single-volume projects
    keep the title-only prefix, so their naming does not change.
    """
    return f"{slugify(project.name)}-vol-{position}-"


def output_formats(merged: dict) -> list[str]:
    return merged.get("formats") or ["pdf"]


def generation_suffix(destinations: list[tuple[Path, list[str]]], now: datetime) -> str:
    """Pick a suffix unused by every planned artifact in this invocation."""

    def available(suffix: str) -> bool:
        return not any(
            os.path.lexists(stem.with_name(f"{stem.name}-{suffix}.{ext}"))
            for stem, formats in destinations
            # The renderer also writes a temporary merged Markdown file.
            for ext in (*formats, "md")
        )

    day = now.strftime("%Y%m%d")
    if available(day):
        return day
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    suffix = timestamp
    sequence = 2
    while not available(suffix):
        suffix = f"{timestamp}-{sequence:04d}"
        sequence += 1
    return suffix


def build_volume(
    manifest: dict,
    volume_name: str,
    volume_dir: Path,
    defaults: dict,
    out_volume_dir: Path,
    template: str | None,
    suffix: str | None,
    prefix_slug: str,
) -> tuple[Path, str | None]:
    """Write the reusable config and prepare an invocation-specific render config."""

    merged = merge_defaults(manifest, defaults)

    title_value = merged.get("title")
    if not isinstance(title_value, str) or not title_value.strip():
        die(f"volume '{volume_name}': manifest must declare a non-empty 'title'")
    title: str = title_value

    chapter_start = merged.get("chapter_start")
    if chapter_start is not None and (
        not isinstance(chapter_start, int)
        or isinstance(chapter_start, bool)
        or chapter_start < 1
    ):
        die(f"volume '{volume_name}': 'chapter_start' must be an integer of 1 or more")

    language = merged.get("language")
    if language is not None and language not in LANG_CODES:
        die(
            f"volume '{volume_name}': 'language' must be one of"
            f" {', '.join(LANG_CODES)} (got {language!r})"
        )

    # The template walks the declared precedence: the one-shot --template flag
    # outranks the volume's own template, which outranks the series default,
    # which outranks the builtin name. A flag path was already validated in
    # main(); declared values validate here, before anything is built.
    if template is not None:
        template_used = template
    elif "template" in manifest:
        # A declared template path is relative to the directory holding the
        # volume's manifest.yaml.
        template_used = resolve_template(manifest["template"], volume_dir, volume_name)
    elif "template" in defaults:
        # An inherited series template path is relative to the directory
        # holding series.yaml, not to the volume.
        template_used = resolve_template(defaults["template"], volume_dir.parent, volume_name)
    else:
        template_used = DEFAULT_TEMPLATE

    # Where the volume's output is decided. The contract pins the vocabulary
    # (pdf, epub), so the shape and values are already validated; the format
    # list only decides what the generated configuration asks for.
    formats = output_formats(merged)
    epub_requested = "epub" in formats

    front = resolve_listed(
        ordered_entries("front_matter", merged.get("front_matter"), volume_name), volume_dir
    )
    chapters_raw = merged.get("chapters")
    if isinstance(chapters_raw, str):
        chapters_dir = merged.get("chapters_dir", "chapters")
        chapters = resolve_entries(ordered_chapters(chapters_dir, volume_name, volume_dir), volume_dir)
    else:
        chapters = resolve_entries(chapter_entries(chapters_raw, volume_name), volume_dir)
    back = resolve_listed(
        ordered_entries("back_matter", merged.get("back_matter"), volume_name), volume_dir
    )

    toc_separators = merged.get("toc_separators", DEFAULT_TOC_SEPARATORS)
    if toc_separators not in TOC_SEPARATORS:
        die(
            f"volume '{volume_name}': 'toc_separators' must be one of"
            f" {', '.join(TOC_SEPARATORS)} (got {toc_separators!r})"
        )
    toc_labels = merged.get("toc_labels") or {}
    if not isinstance(toc_labels, dict):
        die(f"volume '{volume_name}': 'toc_labels' must be a map of label names")
    if toc_separators == "label":
        needed = ["chapters"] + (["appendices"] if back else [])
        missing = [name for name in needed if not str(toc_labels.get(name, "")).strip()]
        if missing:
            die(
                f"volume '{volume_name}': 'toc_separators: label' needs a"
                f" 'toc_labels' entry for {', '.join(missing)}"
            )

    # Generated mode files live in the run output, never inside the content
    # directories. explicit_files resolves against the volume directory
    # (input.chapters_dir is "."), so the tool computes the relative hops.
    # The switches are LaTeX: when the volume outputs more than PDF they are
    # format-gated entries, so an EPUB never receives them.
    generated_dir = out_volume_dir / "generated"
    # The gate is "any requested format that cannot consume LaTeX switches";
    # today the only such format is epub, so this stays a boolean read off the
    # declared formats. format_gated_entry hardcodes the LaTeX job as pdf and
    # emit_config keys the xelatex entry in runtime.required_commands on the
    # same fact: extend the format vocabulary and re-check all three spots
    # (LATEX_ONLY_FORMAT is the marker they must agree on).
    latex_switches_gated = epub_requested
    mainmatter_file = generated_dir / "00-mainmatter.md"
    mainmatter_text = "\\mainmatter\n"
    if chapter_start is not None:
        # The first chapter of this volume gets the declared number: the
        # counter is set to N-1 because the chapter command steps it.
        mainmatter_text += f"\\setcounter{{chapter}}{{{chapter_start - 1}}}\n"
    mainmatter_text += toc_separator_block(
        toc_separators, toc_labels.get("chapters"), "BookTocSeparatorChapters"
    )
    write_mode_file(mainmatter_file, mainmatter_text)

    # 00 and 01 name the two structural switches; the contents guards start at
    # 10 so the numbering never collides as entries are added.
    guard_counter = [10]
    explicit_files: list[str | dict] = []
    explicit_files.extend(
        format_gated_entry(entry, latex_switches_gated)
        for entry in with_toc_guards(front, generated_dir, volume_dir, guard_counter)
    )
    explicit_files.append(
        format_gated_entry(relpath(mainmatter_file, volume_dir), latex_switches_gated)
    )
    explicit_files += list(chapters)
    if back:
        appendix_file = generated_dir / "01-appendix.md"
        write_mode_file(
            appendix_file,
            "\\appendix\n"
            + toc_separator_block(
                toc_separators, toc_labels.get("appendices"), "BookTocSeparatorAppendices"
            ),
        )
        explicit_files.append(
            format_gated_entry(relpath(appendix_file, volume_dir), latex_switches_gated)
        )
        explicit_files.extend(
            format_gated_entry(entry, latex_switches_gated)
            for entry in with_toc_guards(back, generated_dir, volume_dir, guard_counter)
        )

    out_volume_dir.mkdir(parents=True, exist_ok=True)
    config_path = out_volume_dir / "skelepress.config.yaml"

    def config_text(output_suffix: str) -> str:
        return emit_config(
            merged, title, volume_dir, out_volume_dir, explicit_files,
            template_used, formats, output_suffix, prefix_slug,
        )

    config_path.write_text(config_text(DATE_SUFFIX), encoding="utf-8")
    return config_path, config_text(suffix) if suffix is not None else None


def render_volume(config_dir: Path, text: str) -> subprocess.CompletedProcess:
    # Keep the config beside the reusable one so relative paths mean the same
    # thing. The chosen suffix belongs only to this invocation.
    fd, name = mkstemp(dir=config_dir, prefix=".book-render-", suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        return subprocess.run([str(CLI), "render", "-c", name])
    finally:
        Path(name).unlink(missing_ok=True)


def format_gated_entry(relative: str, gated: bool) -> str | dict:
    """One explicit_files entry, gated to LATEX_ONLY_FORMAT so EPUB never gets it.

    The LaTeX switches only make sense to a PDF job, so a volume that asks
    for an EPUB publishes them as gated entries; a PDF-only volume keeps the
    plain string form, which lands in every format exactly as before. The
    hardcoded LATEX_ONLY_FORMAT here and the pdf_requested check in emit_config
    (which keeps xelatex in runtime.required_commands) express the same fact:
    pdf is the only format that consumes these entries.
    """
    if not gated:
        return relative
    return {
        "file": relative,
        "formats": [LATEX_ONLY_FORMAT],
    }


def emit_config(
    manifest: dict,
    title: str,
    volume_dir: Path,
    out_volume_dir: Path,
    explicit_files: list[str | dict],
    template: str,
    formats: list[str],
    suffix: str,
    prefix_slug: str = "",
) -> str:
    """One standard skelepress.config.yaml per volume, emitted as canonical text.

    The text is written by hand instead of a YAML dumper so the result is
    byte-identical whichever parser read the manifests.
    """
    slug = slugify(title)
    # A series volume's generated file name must sort with its series and
    # identify it without the folder tree, so the prefix opens with the
    # composed series-vol-n opener and the title slug closes it. A
    # single-volume project keeps the title-only name.
    file_prefix = f"{prefix_slug}{slug}" if prefix_slug else slug
    # A TeX engine is a PDF requirement (LATEX_ONLY_FORMAT): when no PDF is
    # requested the generated configuration must not make preflight demand one
    # for the other formats.
    pdf_requested = LATEX_ONLY_FORMAT in formats
    lines = [
        "# Generated by scripts/tools/bookkit/build.py. Do not edit:",
        "# change the volume's manifest.yaml (and series.yaml) instead.",
        "version: 1",
        "",
        "project:",
        f"  name: {quoted(slug)}",
        f"  base_dir: {quoted(relpath(volume_dir, out_volume_dir))}",
        "",
        "document:",
        f"  title: {quoted(title)}",
    ]
    for key in ("subtitle", "author", "publisher", "date", "rights"):
        value = manifest.get(key)
        if isinstance(value, str) and value.strip():
            lines.append(f"  {key}: {quoted(value)}")
    language = manifest.get("language")
    if isinstance(language, str) and language:
        lines.append(f"  language: {quoted(language)}")
    lines.append("  titlepage: true")
    metadata = {
        key: str(manifest[key])
        # volume is an integer by contract, the rest are strings; the
        # isinstance pair with the bool exclusion passes exactly one shape
        # per key (a bool would stringify as "True" and fabricate a value).
        for key in ("collection", "isbn", "audience", "description", "volume", "volume_label")
        if isinstance(manifest.get(key), (int, str))
        and not isinstance(manifest.get(key), bool)
        and str(manifest[key]).strip()
    }
    if metadata:
        lines.append("  metadata:")
        lines.extend(f"    {key}: {quoted(value)}" for key, value in metadata.items())
    lines.extend(
        [
            "",
            "input:",
            '  chapters_dir: "."',
            '  glob: "*.md"',
            "  order: natural",
            "  explicit_files:",
        ]
    )
    # Declared order is document order: a gated entry keeps exactly its place
    # instead of being grouped after the plain entries.
    for entry in explicit_files:
        if isinstance(entry, dict):
            lines.append(f"    - file: {quoted(entry['file'])}")
            lines.append(f"      formats: [{', '.join(entry['formats'])}]")
        else:
            lines.append(f"    - {quoted(entry)}")
    lines.extend(
        [
            "",
            "output:",
            f"  formats: [{', '.join(formats)}]",
            f"  dir: {quoted(relpath(out_volume_dir, volume_dir))}",
            f"  file_prefix: {quoted(file_prefix)}",
            f"  suffix: {quoted(suffix)}",
            "  keep_merged_markdown: false",
            "",
            "pandoc:",
            "  pdf_engine: xelatex",
            "  toc: true",
            "  toc_depth: 2",
            "  number_sections: true",
            # The book template receives \chapter for top-level headings through
            # the contract instead of a \let heading shift in the template.
            "  top_level_division: chapter",
            # Emit only declared/inherited values: absent manifests keep their
            # previous generated configuration, while explicit false survives.
            *([f"  running_headers: {str(manifest['running_headers']).lower()}"]
              if "running_headers" in manifest else []),
            f"  template: {quoted(template if is_bare_name(template) else relpath(Path(template), volume_dir))}",
            "  resource_path:",
            # Assets a chapter references resolve from the volume root, which is
            # where the content folders and any media directory now live.
            '    - "."',
            "",
            "filters:",
            "  emoji:",
            "    enabled: false",
            "  mermaid:",
            "    enabled: false",
            "  extra_lua_filters: []",
            "",
            "runtime:",
            "  required_commands:",
            "    - pandoc",
            # A TeX engine is a PDF requirement: when no PDF is requested the
            # generated configuration must not make preflight demand one.
            *([] if not pdf_requested else ["    - xelatex"]),
            "    - python3",
            "  strict: true",
            "",
        ]
    )
    return "\n".join(lines)


# --- Contracts --------------------------------------------------------------


def load_contract(path: Path, schema_path: Path) -> dict:
    """Load a YAML file and validate it against one of this tool's schemas."""

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as error:
        die(f"invalid contract schema {schema_path.name}: {error}")
    data = load_yaml(path)
    if not isinstance(data, dict):
        die(f"root of {path} must be a mapping")
    validate_with_schema(data, schema)
    return data


# --- Main -------------------------------------------------------------------


def help_text(key: str, **values: object) -> str:
    return importlib.import_module("i18n_runtime").t(key, key, **values)


class BookArgumentParser(argparse.ArgumentParser):
    def format_help(self, formatter: argparse.HelpFormatter | None = None) -> str:
        # Keep the existing program name in errors; only help uses the public CLI.
        original = self.prog
        self.prog = "skelepress book"
        try:
            # Python 3.15 passes a formatter made before the public name is set.
            # Rebuild it here; older Python versions call without one.
            if formatter is not None:
                return super().format_help(self._get_formatter())
            return super().format_help()
        finally:
            self.prog = original


def main() -> None:
    parser = BookArgumentParser(
        description=help_text("book.help.description"),
        epilog=help_text("book.help.examples"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser._positionals.title = help_text("book.help.positionals")
    parser._optionals.title = help_text("book.help.options")
    parser.add_argument("-h", "--help", action="help", help=help_text("book.help.help"))
    parser.add_argument(
        "projects",
        nargs="+",
        help=help_text("book.help.projects"),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=help_text("book.help.check"),
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=help_text("book.help.out", out=DEFAULT_OUT.as_posix()),
    )
    parser.add_argument(
        "--template",
        default=None,
        help=help_text("book.help.template", template=DEFAULT_TEMPLATE),
    )
    args = parser.parse_args()

    explicit_template: str | None = None
    if args.template:
        raw_template = args.template.strip()
        if is_bare_name(raw_template):
            # A name is a template the toolkit ships, so the validator and the
            # renderer resolve it and there is no path to check here.
            explicit_template = raw_template
        else:
            resolved_template = Path(raw_template).resolve()
            if not resolved_template.is_file():
                die(f"book template not found: {resolved_template}")
            explicit_template = str(resolved_template)

    projects: list[tuple[Path, str | None]] = []
    for raw in args.projects:
        # Resolve the project before anything computes a path against it. The
        # output directory is already resolved, and on a platform where the two
        # spellings differ -- macOS gives /var/folders and resolves it to
        # /private/var/folders -- a relative path built from one and applied to
        # the other points outside the tree. The generated configuration then
        # names files that do not exist, and the render fails with a path that
        # looks plausible.
        project = Path(raw).resolve()
        if not project.is_dir():
            die(f"not a directory: {project}")
        if not (project / "series.yaml").is_file() and not (project / "manifest.yaml").is_file():
            die(f"no series.yaml or manifest.yaml in: {project}")
        projects.append((project, explicit_template))

    # Contract validation first, for every project, before anything is built:
    # a manifest that fails validation never reaches the build.
    plans: list[tuple[Path, str, Path, dict, dict, bool, str | None, int]] = []
    for project, template in projects:
        series_path = project / "series.yaml"
        if series_path.is_file():
            series = load_contract(series_path, SERIES_SCHEMA)
            # Issue #230's cross-check: a volume-declared 'volume' ordinal is
            # meaningful only where the tool can see both sides. In the series
            # shape the declared value must equal the volume's 1-based position
            # in the volumes list, or the build fails with a message naming
            # all three facts. The label is free text and is never checked.
            for position, volume_name in enumerate(series["volumes"], 1):
                volume_dir = project / volume_name
                if not (volume_dir / "manifest.yaml").is_file():
                    die(f"series '{project.name}': volume '{volume_name}' has no manifest.yaml")
                manifest = load_contract(volume_dir / "manifest.yaml", MANIFEST_SCHEMA)
                declared_volume = manifest.get("volume")
                if isinstance(declared_volume, int) and not isinstance(declared_volume, bool) \
                        and declared_volume != position:
                    die(
                        f"series '{project.name}': volume '{volume_name}' declares "
                        f"volume {declared_volume}, expected {position}"
                    )
                plans.append((project, volume_name, volume_dir, series, manifest, True, template, position))
        else:
            manifest = load_contract(project / "manifest.yaml", MANIFEST_SCHEMA)
            plans.append((project, project.name, project, {}, manifest, False, template, 0))

    if not args.check and not CLI.is_file():
        die(f"skelepress CLI not found: {CLI}")

    out_root = Path(args.out).resolve()
    suffix = None
    if not args.check:
        destinations = []
        for project, volume_name, _, defaults, manifest, _, _, position in plans:
            title = manifest.get("title")  # Titles are per-volume, never inherited.
            if isinstance(title, str) and title.strip():
                out_dir = volume_output_dir(out_root, project, volume_name, bool(position))
                formats = output_formats(merge_defaults(manifest, defaults))
                opener = f"{slugify(project.name)}-vol-{position}-" if position else ""
                destinations.append((out_dir / f"{opener}{slugify(title)}", formats))
        # Each volume renders in its own process. Freeze one suffix here so
        # neither a partial collision nor a clock boundary splits a generation.
        suffix = generation_suffix(destinations, datetime.now())

    failures: list[str] = []
    for project, volume_name, volume_dir, defaults, manifest, is_series, explicit_template, position in plans:
        out_volume_dir = volume_output_dir(out_root, project, volume_name, is_series)
        print(f"==> {project.name}/{volume_name}")
        config_path, render_config = build_volume(
            manifest, volume_name, volume_dir, defaults, out_volume_dir, explicit_template, suffix,
            f"{slugify(project.name)}-vol-{position}-" if is_series else "",
        )
        print(f"    config: {relpath(config_path, Path.cwd())}")

        if render_config is None:
            continue

        result = render_volume(config_path.parent, render_config)
        pdfs = sorted(out_volume_dir.glob("*.pdf"))
        if result.returncode == 0 and pdfs:
            for pdf in pdfs:
                print(f"    [ok] {relpath(pdf, Path.cwd())}")
        else:
            failures.append(f"{project.name}/{volume_name}")
            print(f"    [FAIL] {project.name}/{volume_name} (exit {result.returncode})")

    if args.check:
        print(f"Check ok: {len(plans)} volume(s) validated, configurations in {relpath(out_root, Path.cwd())}")
        return
    if failures:
        die(f"render failed for: {', '.join(failures)}")
    print(f"Done: {len(plans)} volume(s) rendered into {relpath(out_root, Path.cwd())}")


if __name__ == "__main__":
    main()
