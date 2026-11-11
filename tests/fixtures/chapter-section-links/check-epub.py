"""Check public EPUB hrefs against the actual destination heading elements."""
import posixpath
import sys
import zipfile
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit


def check(ok, message):
    print(f'{0 if ok else 1}\t{message}')


class Element:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def get(self, name, default=None):
        return self.attrs.get(name, default)

    def iter(self):
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.iter()

    def itertext(self):
        for child in self.children:
            yield from child.itertext() if isinstance(child, Element) else [child]


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.root = Element()
        self.stack = [self.root]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        element = Element('}' + tag, attrs)
        self.stack[-1].children.append(element)
        if tag not in ('meta', 'link', 'br', 'hr', 'img', 'input'):
            self.stack.append(element)

    def handle_endtag(self, tag):
        if self.stack[-1].tag == '}' + tag:
            self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)


with zipfile.ZipFile(sys.argv[1]) as archive:
    roots = {name: Document(archive.read(name).decode('utf-8')).root
             for name in archive.namelist() if name.endswith('.xhtml')}
    links = {''.join(e.itertext()): (name, e) for name, root in roots.items()
             for e in root.iter() if e.tag.endswith('}a')}

    def destination(label):
        name, link = links[label]
        url = urlsplit(link.get('href', ''))
        path = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(url.path))) if url.path else name
        root = roots.get(path)
        return next((e for e in root.iter() if e.get('id') == unquote(url.fragment)), None) if root is not None else None

    if '--heading-mismatch' in sys.argv[2:]:
        migration = destination('migration')
        check(migration is not None and migration.get('id') == 'version-1-to-2',
              'heading fallback does not invalidate unrelated section destinations')
        target = destination('jump')
        check(target is not None and target.get('id') == 'heading-link'
              and any(e.tag in ('}h1', '}h2', '}h3') and
                      ''.join(e.itertext()).startswith('heading-link') for e in target.iter()),
              'fallback annotation preserves an existing local heading destination')
        check(links['heading-link'][1].get('href', '').endswith('#ch-migration'),
              'missing section in a heading still falls back to its chapter')
        check('heading-link (section unavailable)' in ''.join(roots[links['heading-link'][0]].itertext()),
              'heading fallback remains visible to readers')
        sys.exit(0)

    def heading_text(target):
        if target is None:
            return None
        # EPUB writers may put the heading ID on its enclosing section.
        heading = next((e for e in target.iter() if e.tag in ('}h1', '}h2', '}h3')), None)
        return ''.join(heading.itertext()) if heading is not None else None

    for label, title, identifier in [
        ('migration', 'Version 1 to 2', 'version-1-to-2'),
        ('second occurrence', 'Repeat', 'repeat-2'),
        ('explicit', 'Custom Upgrade', 'upgrade-now'),
        ('basename', 'Version 1 to 2', 'version-1-to-2'),
        ('encoded', 'Version 1 to 2', 'version-1-to-2'),
    ]:
        target = destination(label)
        check(target is not None and heading_text(target) == title and target.get('id') == identifier,
              f'{label} href reaches its exact target heading')

    missing = links['missing'][1]
    check(missing.get('href', '').endswith('#ch-migration'), 'missing fragment falls back to the chapter anchor')
    source = roots[links['missing'][0]]
    check('missing (section unavailable)' in ''.join(source.itertext()), 'missing fragment is visibly annotated for readers')
    check(links['chapter only'][1].get('href', '').endswith('#ch-migration'), 'chapter-only links retain their anchor')
    check(links['unselected'][1].get('href') == 'outside.md#leave-alone', 'unselected files retain their original path and fragment')
    local = destination('local')
    check(local is not None and local.get('id') == 'repeat' and heading_text(local) == 'Repeat',
          'intrachapter auto-ID links retain their heading destination')
    explicit = destination('local explicit')
    check(explicit is not None and explicit.get('id') == 'upgrade-now' and heading_text(explicit) == 'Custom Upgrade',
          'intrachapter explicit-ID links retain their heading destination')
    check('[example](migration.md#version-1-to-2)' in ''.join(source.itertext()), 'fenced link examples remain literal')
    target = destination('chapter only')
    migration_root = roots[links['local explicit'][0]]
    check(target is not None and any(e.get('id') == 'ch-migration' for e in migration_root.iter()),
          'chapter fallback stays inside the migration spine document')
