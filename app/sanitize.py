"""Whitelist-based HTML sanitiser for rich-text learning story content.

The observation field is a contenteditable editor, so it submits HTML rather
than plain text. Anything a browser sends has to be treated as untrusted, so
this strips every tag and attribute that isn't explicitly allowed before the
content is stored or rendered.

Uses only the standard library so the project doesn't gain a dependency.
"""
from html.parser import HTMLParser
from html import escape
import re

# Tags the editor can produce. Everything else is dropped (its text is kept).
ALLOWED_TAGS = {
    'p', 'br', 'div', 'span', 'b', 'strong', 'i', 'em', 'u', 's',
    'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'blockquote', 'img',
}
SELF_CLOSING = {'br', 'img'}

# Tags whose *contents* are thrown away too, not just the tag itself.
DROP_CONTENT_TAGS = {'script', 'style', 'iframe', 'object', 'embed'}

ALLOWED_ATTRS = {
    'span': {'style'},
    'div': {'style'},
    'p': {'style'},
    'h1': {'style'}, 'h2': {'style'}, 'h3': {'style'},
    'li': {'style'}, 'ul': {'style'}, 'ol': {'style'},
    'img': {'src', 'alt'},
}

# Only these CSS properties survive, and only with values matching the patterns
# below - this blocks things like `background: url(javascript:...)`.
ALLOWED_STYLES = {
    'color': re.compile(r'^#[0-9a-fA-F]{3,8}$|^rgb\([\d,\s]+\)$|^[a-zA-Z]+$'),
    'background-color': re.compile(r'^#[0-9a-fA-F]{3,8}$|^rgb\([\d,\s]+\)$|^[a-zA-Z]+$'),
    'font-size': re.compile(r'^\d{1,3}(\.\d+)?(px|pt|em|rem|%)$'),
    'font-family': re.compile(r'^[\w\s,\'"\-]+$'),
    'font-weight': re.compile(r'^(bold|normal|[1-9]00)$'),
    'font-style': re.compile(r'^(italic|normal)$'),
    'text-align': re.compile(r'^(left|center|right|justify)$'),
    'text-decoration': re.compile(r'^(underline|line-through|none)$'),
}

# Images may only point at files this app itself stored.
SAFE_IMG_SRC = re.compile(r'^/static/uploads/[A-Za-z0-9._-]+$')


def _clean_style(value):
    kept = []
    for declaration in value.split(';'):
        if ':' not in declaration:
            continue
        prop, _, val = declaration.partition(':')
        prop = prop.strip().lower()
        val = val.strip()
        pattern = ALLOWED_STYLES.get(prop)
        if pattern and pattern.match(val):
            kept.append(f'{prop}: {val}')
    return '; '.join(kept)


class _Sanitiser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.open_tags = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in ALLOWED_TAGS:
            return
        allowed = ALLOWED_ATTRS.get(tag, set())
        pieces = []
        for name, value in attrs:
            name = name.lower()
            if name not in allowed or value is None:
                continue
            if name == 'style':
                value = _clean_style(value)
                if not value:
                    continue
            elif name == 'src':
                if not SAFE_IMG_SRC.match(value):
                    return  # drop the whole <img> if it points somewhere else
            pieces.append(f'{name}="{escape(value, quote=True)}"')

        attr_str = (' ' + ' '.join(pieces)) if pieces else ''
        if tag in SELF_CLOSING:
            self.out.append(f'<{tag}{attr_str} />')
        else:
            self.out.append(f'<{tag}{attr_str}>')
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag in ALLOWED_TAGS and tag not in SELF_CLOSING and tag in self.open_tags:
            self.out.append(f'</{tag}>')
            self.open_tags.remove(tag)

    def handle_data(self, data):
        if self.skip_depth:
            return
        self.out.append(escape(data, quote=False))

    def result(self):
        # Close anything the submitted markup left open.
        for tag in reversed(self.open_tags):
            self.out.append(f'</{tag}>')
        return ''.join(self.out)


def clean_html(raw):
    if not raw:
        return ''
    parser = _Sanitiser()
    parser.feed(raw)
    parser.close()
    return parser.result()


def html_to_text(raw, limit=None):
    """Plain-text version, used for list previews and for checking the
    observation isn't effectively empty."""
    text = re.sub(r'<br\s*/?>|</p>|</div>|</li>', ' ', raw or '')
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if limit and len(text) > limit:
        return text[:limit].rstrip() + '…'
    return text
