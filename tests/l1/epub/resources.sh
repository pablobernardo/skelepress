#!/bin/bash
# Resource resolution inside the publication.
# Sourced by tests/run.sh (not run standalone).

run_epub_resource_path_test() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "SKIP epub resources (pandoc not available)"
    return 0
  fi

  local sandbox elsewhere out epub code=0
  sandbox="$(new_epub_resource_sandbox)"
  elsewhere="$(mktemp -d)"
  out="$(mktemp)"
  epub="${sandbox}/work/out/epub-resources-manual.epub"

  # The cover image and the content image are declared relative to the project,
  # so the command must not depend on where it is invoked.
  (
    cd "$elsewhere" && "${sandbox}/bin/skelepress" render -c "${sandbox}/skelepress.config.yaml"
  ) >"$out" 2>&1 || code=$?
  assert_exit_code "0" "$code" "EPUB resources resolve when the command runs outside the project"

  if [[ -s "$epub" ]]; then
    pass "render writes the epub from an unrelated working directory"
  else
    fail "render must write the epub from an unrelated working directory ($(tail -3 "$out"))"
  fi

  while IFS=$'\t' read -r result message; do
    if [[ "$result" == "0" ]]; then pass "$message"; else fail "$message"; fi
  done < <("${REAL_PYTHON3}" - "$epub" "${sandbox}/work/assets" "${sandbox}/filters/emoji/2610.svg" <<'PY'
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile

epub = pathlib.Path(sys.argv[1])
assets = pathlib.Path(sys.argv[2])
ballot = pathlib.Path(sys.argv[3])


def check(ok, message):
    print(f"{0 if ok else 1}\t{message}")


try:
    archive = zipfile.ZipFile(epub)
except Exception as error:  # noqa: BLE001 - a broken archive is a test result
    check(False, "the epub is a readable zip archive")
    print(f"1\tdetail: {error}")
    sys.exit(0)

check(True, "the epub is a readable zip archive")
names = set(archive.namelist())
container = ET.fromstring(archive.read("META-INF/container.xml"))
rootfile = container.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
opf_path = rootfile.get("full-path")
opf_dir = opf_path.rsplit("/", 1)[0] if "/" in opf_path else ""
package = ET.fromstring(archive.read(opf_path))
opf = {"o": "http://www.idpf.org/2007/opf"}

items = package.findall(".//o:manifest/o:item", opf)
covers = [item for item in items if "cover-image" in (item.get("properties") or "").split()]
check(len(covers) == 1, "the manifest declares exactly one cover-image item")
cover_id = covers[0].get("id") if covers else ""
metas = package.findall(".//o:metadata/o:meta", opf)
# EPUB 3 identifies the cover by its manifest property. The EPUB 2 name/content
# meta is optional, but any supplied reference must identify that actual cover:
# https://www.w3.org/TR/epub-33/#pkg-legacy-support
# https://www.w3.org/TR/epub-33/#sec-cover-image

def valid_cover_reference(actual_id, references):
    return bool(actual_id) and (not references or references == [actual_id])


check(valid_cover_reference(cover_id, [m.get("content") for m in metas if m.get("name") == "cover"]),
      "the cover has an ID and any legacy cover meta points only to that cover-image item")

# Controls exercise the same validator used for the actual package above.
for actual_id, references, expected, message in [
    ("cover", [], True, "an EPUB 3 cover needs no legacy cover meta"),
    ("cover", ["cover"], True, "a single matching legacy cover reference remains valid"),
    ("cover", ["chapter"], False, "a legacy reference to a different item is rejected"),
    ("cover", ["missing"], False, "a dangling legacy cover reference is rejected"),
    ("cover", ["cover", "cover"], False, "duplicate matching legacy cover references are rejected"),
    ("cover", ["cover", "missing"], False, "mixed duplicate legacy cover references are rejected"),
    ("cover", [""], False, "an empty legacy cover reference is rejected"),
    ("cover", [None], False, "a legacy cover meta without content is rejected"),
    ("", [], False, "an absent cover ID is rejected even without legacy metadata"),
    ("", [""], False, "an empty cover ID cannot validate an empty legacy reference"),
    (None, [], False, "a missing cover item ID is rejected"),
]:
    check(valid_cover_reference(actual_id, references) == expected, message)

spine = package.findall(".//o:spine/o:itemref", opf)
first = spine[0].get("idref") if spine else ""
check(first == "cover_xhtml", "the image cover opens the spine")
by_id = {item.get("id"): item.get("href") for item in items}
cover_href = by_id.get(first) or ""
cover_path = f"{opf_dir}/{cover_href}" if opf_dir else cover_href
check(bool(cover_href) and cover_path in names, "the cover document exists in the archive")

media = {archive.read(name) for name in names if name.startswith(f"{opf_dir}/media/")}
check(assets.joinpath("figure.png").read_bytes() in media,
      "the content image is embedded byte for byte")
check(ballot.read_bytes() in media,
      "the emoji SVG comes from the versioned emoji directory")

chapter = next(name for name in names if name.endswith("ch001.xhtml"))
chapter_root = ET.fromstring(archive.read(chapter))
html = {"h": "http://www.w3.org/1999/xhtml"}
images = chapter_root.findall(".//h:img", html)
check(len([i for i in images if "emoji" in (i.get("class") or "").split()]) == 2,
      "each task-list box becomes an emoji image")
check(all(opf_dir + "/" + (image.get("src") or "").removeprefix("../") in names for image in images),
      "every chapter image resolves to an archive entry")
archive.close()
PY
)

  rm -rf "$sandbox" "$elsewhere"
  rm -f "$out"
}
