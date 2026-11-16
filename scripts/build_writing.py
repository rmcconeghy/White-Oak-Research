#!/usr/bin/env python3
"""Generate Writing from permanent essay HTML; standard library only."""
import argparse
from datetime import date
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import posixpath
import re
from urllib.parse import urlsplit, urlunsplit


class EssayParser(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.lines = [0]
        for match in re.finditer('\n', source):
            self.lines.append(match.end())
        self.start = self.end = None
        self.attrs = {}
        self.titles = []
        self.in_title = False
        self.times = []
        self.feed(source)

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article':
            if self.start is not None:
                raise ValueError('Each essay must contain exactly one article')
            self.start = self.source_offset()
            self.attrs = attrs
        if self.start is not None and self.end is None:
            if tag == 'h1':
                self.titles.append('')
                self.in_title = True
            if tag == 'time':
                self.times.append(attrs.get('datetime'))

    def handle_endtag(self, tag):
        if tag == 'h1':
            self.in_title = False
        if tag == 'article':
            self.end = self.source_offset() + len('</article>')

    def handle_data(self, data):
        if self.in_title:
            self.titles[-1] += data


def date_label(value):
    return f'{value:%B} {value.day}, {value.year}'


class RebaseLinks(HTMLParser):
    """Change URL attributes only, keeping the original article text untouched."""
    def __init__(self, source, slug):
        super().__init__(convert_charrefs=False)
        self.source, self.slug, self.changes = source, slug, []
        self.lines = [0] + [m.end() for m in re.finditer('\n', source)]
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        raw = self.get_starttag_text()
        line, column = self.getpos()
        offset = self.lines[line - 1] + column
        pattern = r'''\b(href|src|poster)\s*=\s*(["'])(.*?)\2'''
        for match in re.finditer(pattern, raw, re.I | re.S):
            value = match.group(3)
            parts = urlsplit(value)
            if parts.scheme or parts.netloc or value.startswith(('/', '#', '?')) or not value:
                continue
            path = posixpath.normpath(posixpath.join(self.slug, parts.path))
            if parts.path.endswith('/'):
                path += '/'
            new = urlunsplit(('', '', path, parts.query, parts.fragment))
            self.changes.append((offset + match.start(3), offset + match.end(3), new))

    handle_startendtag = handle_starttag

    def result(self):
        result = self.source
        for start, end, value in reversed(self.changes):
            result = result[:start] + value + result[end:]
        return result


def build(root):
    essays = []
    for path in sorted((root / 'writing').glob('*/index.html')):
        parsed = EssayParser(path.read_text(encoding='utf-8'))
        if parsed.attrs.get('data-status', 'published') == 'draft':
            continue
        if parsed.start is None or parsed.end is None or len(parsed.titles) != 1:
            raise ValueError(f'{path}: requires one article with one h1')
        published = date.fromisoformat(parsed.attrs.get('data-published', ''))
        if published.isoformat() not in parsed.times:
            raise ValueError(f'{path}: add a visible time matching data-published')
        article = parsed.source[parsed.start:parsed.end]
        essays.append((published, path.parent.name, parsed.titles[0], article))
    if not essays:
        raise ValueError('No published essays found')
    # Slug is the deterministic tie-breaker for essays published the same day.
    essays.sort(key=lambda essay: (essay[0], essay[1]), reverse=True)
    published, slug, title, article = essays[0]
    featured = RebaseLinks(article, slug).result()
    archive = []
    for published, slug_old, title_old, _ in essays[1:]:
        archive.append(f'<li><a href="./{escape(slug_old)}/">{escape(title_old)}</a>'
                       f'<time datetime="{published.isoformat()}">{date_label(published)}</time></li>')
    previous = '<ol>' + '\n'.join(archive) + '</ol>' if archive else '<p>This is the first essay.</p>'
    main = ('<main class="reading writing-index">\n<p class="writing-label">Writing</p>\n'
            + featured + f'\n<a class="permalink" href="./{escape(slug)}/">Permanent link to this essay</a>\n'
            + '<section class="previous-writing" aria-labelledby="previous-writing">'
            + '<h2 id="previous-writing">Previous writing</h2>' + previous + '</section>\n</main>')
    template = (root / 'scripts/templates/writing.html').read_text(encoding='utf-8')
    if template.count('{{WRITING_MAIN}}') != 1:
        raise ValueError('Writing template must have exactly one main placeholder')
    output = '<!-- Generated by scripts/build_writing.py; edit the permanent essay pages. -->\n' + template.replace('{{WRITING_MAIN}}', main)
    (root / 'writing/index.html').write_text(output, encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    build(args.root)
