"""HTML -> plain text using only the standard library (keeps the project light)."""
from html.parser import HTMLParser
import re

SKIP = {"script", "style", "noscript", "svg"}
BLOCK = {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4", "section", "address", "td"}


class Page:
    def __init__(self, text, title, h1, source):
        self.text, self.title, self.h1, self.source = text, title, h1, source


class _P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title, self.h1 = [], "", ""
        self._skip = 0
        self._tag = None

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self._skip += 1
        if tag in BLOCK:
            self.parts.append("\n")
        self._tag = tag
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith("mailto:"):
                self.parts.append(" " + href[7:].split("?")[0] + " ")
            elif href.startswith("tel:"):
                self.parts.append(" " + href[4:] + " ")

    def handle_endtag(self, tag):
        if tag in SKIP and self._skip:
            self._skip -= 1
        if tag in BLOCK:
            self.parts.append("\n")
        self._tag = None

    def handle_data(self, data):
        if self._skip:
            return
        if self._tag == "title":
            self.title += data
        elif self._tag == "h1" and not self.h1:
            self.h1 = data.strip()
        self.parts.append(data)


def parse_html(html: str, source: str = "") -> Page:
    p = _P()
    p.feed(html)
    text = "".join(p.parts)
    text = re.sub(r"[ \t\r\f]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return Page(text, p.title.strip(), p.h1, source)
