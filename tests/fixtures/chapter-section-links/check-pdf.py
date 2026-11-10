"""Inspect actual PDF GoTo annotations and destinations (host-only dependency)."""
import json
import sys
from importlib import import_module
from pathlib import Path

try:
    PdfReader = import_module('pypdf').PdfReader
except ModuleNotFoundError:
    print('SKIP PDF destination inspection (pypdf unavailable)')
    sys.exit(77)

reader = PdfReader(sys.argv[1])
named = reader.named_destinations
annotations = []
for page_number, page in enumerate(reader.pages):
    for reference in page.get('/Annots', []):
        annotation = reference.get_object()
        action = annotation.get('/A', {})
        if action.get('/S') == '/GoTo':
            annotations.append((page_number, annotation['/Rect'], action['/D']))


def resolve(destination):
    # TeX can use generated names such as section.1 rather than Markdown IDs.
    if isinstance(destination, str):
        target = named[destination]
        return reader.get_destination_page_number(target), str(target.get('/Top'))
    page_ref = destination[0]
    page_index = next(i for i, page in enumerate(reader.pages)
                      if page.indirect_reference == page_ref)
    return page_index, str(destination[1:])


# The minimal template has no TOC; the fixture has exactly two links, on separate
# lines. Their annotation rectangles identify migration first, then missing.
annotations.sort(key=lambda a: (a[0], -float(a[1][3])))
checks = {'exactly_two_source_annotations': len(annotations) == 2}
report = {'checks': checks, 'annotations': [
    {'source_page': p + 1, 'rectangle': [float(v) for v in rect], 'destination': str(dest)}
    for p, rect, dest in annotations]}
if len(annotations) == 2:
    section_page, section_top = resolve(annotations[0][2])
    chapter_page, chapter_top = resolve(annotations[1][2])
    checks.update({
        'both_annotations_originate_on_source_page': all(a[0] == 0 for a in annotations),
        'section_is_not_chapter_start': section_page != chapter_page,
        'section_destination_contains_heading_and_body': all(
            text in reader.pages[section_page].extract_text()
            for text in ('Version 1 to 2', 'Migration section destination.')),
        'chapter_fallback_contains_introduction': 'Chapter introduction' in reader.pages[chapter_page].extract_text(),
        'missing_section_is_reader_visible': '(section unavailable)' in reader.pages[0].extract_text(),
    })
    report['section_destination'] = {'page': section_page + 1, 'top': section_top}
    report['chapter_destination'] = {'page': chapter_page + 1, 'top': chapter_top}
Path(sys.argv[2]).write_text(json.dumps(report, indent=2) + '\n')
for name, passed in checks.items():
    print(f'{"PASS" if passed else "FAIL"}: {name}')
sys.exit(0 if all(checks.values()) else 1)
