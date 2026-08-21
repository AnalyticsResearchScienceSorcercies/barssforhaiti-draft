#!/usr/bin/env python3
"""
Sitewide nav + footer sweep for barssforhaiti.com. Trilingual.

Reads _components/nav[-LANG].html and _components/footer[-LANG].html and
injects them into every root-level .html page between the NAV:START/NAV:END and
FOOTER:START/FOOTER:END markers.

Page language comes from the filename suffix:
    index.html      -> en   (no suffix)
    index-fr.html   -> fr
    index-ht.html   -> ht

For each page the sweep also:
  - stamps aria-current="page" on the nav link matching that filename
  - replaces the <!-- LANG --> marker in the nav with a language switcher
    built for that page's own base name, so FR->HT stays on Services rather
    than dumping the reader back on the homepage
  - only links a language whose file actually exists, so a partial
    translation never ships a 404
  - enforces <html lang="..."> so it cannot drift from the filename

Same pattern as the konkret repo's _nav_sweep.py: edit the component once,
run the sweep, every page updates.

Usage:
    python _sweep.py            # write changes
    python _sweep.py --check    # report what would change, write nothing
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = ROOT / "_components"

DEFAULT_LANG = "en"
LANGS = ["en", "fr", "ht"]
LANG_LABEL = {"en": "EN", "fr": "FR", "ht": "HT"}
LANG_TITLE = {"en": "English", "fr": "Français", "ht": "Kreyòl"}
SWITCHER_LABEL = {"en": "Language", "fr": "Langue", "ht": "Lang"}


def split_page(filename: str):
    """'services-fr.html' -> ('services', 'fr'); 'services.html' -> ('services', 'en')"""
    stem = filename[: -len(".html")]
    if "-" in stem:
        base, _, suffix = stem.rpartition("-")
        if suffix in LANGS and base:
            return base, suffix
    return stem, DEFAULT_LANG


def page_name(base: str, lang: str) -> str:
    return "%s.html" % base if lang == DEFAULT_LANG else "%s-%s.html" % (base, lang)


def component(kind: str, lang: str) -> Path:
    name = "%s.html" % kind if lang == DEFAULT_LANG else "%s-%s.html" % (kind, lang)
    return COMPONENTS / name


def build_switcher(base: str, lang: str, available) -> str:
    links = []
    for code in LANGS:
        target = page_name(base, code)
        if target not in available:
            continue
        current = ' aria-current="true"' if code == lang else ""
        links.append(
            '        <a href="%s" hreflang="%s" lang="%s" title="%s"%s>%s</a>'
            % (target, code, code, LANG_TITLE[code], current, LANG_LABEL[code])
        )
    if len(links) < 2:
        return ""
    return '      <div class="lang" aria-label="%s">\n%s\n      </div>' % (
        SWITCHER_LABEL[lang],
        "\n".join(links),
    )


SITE = "https://barssforhaiti.com/"


def build_alternates(base: str, available) -> str:
    """rel=alternate hreflang set for this page's base name, plus x-default."""
    lines = []
    for code in LANGS:
        target = page_name(base, code)
        if target in available:
            lines.append(
                '  <link rel="alternate" hreflang="%s" href="%s%s">' % (code, SITE, target)
            )
    if len(lines) < 2:
        return ""
    default = page_name(base, DEFAULT_LANG)
    if default in available:
        lines.append(
            '  <link rel="alternate" hreflang="x-default" href="%s%s">' % (SITE, default)
        )
    return "\n".join(lines)


def inject(html: str, name: str, body: str):
    """Replace between <!-- NAME:START --> and <!-- NAME:END -->.

    Returns (html, found). The end marker may be indented -- head blocks are,
    body blocks are not -- and a missing marker is reported rather than
    silently skipped, which is how the ALT block quietly did nothing once.
    """
    pattern = re.compile(
        r"<!--\s*%s:START\s*-->(.*?)([ \t]*)<!--\s*%s:END\s*-->" % (name, name),
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        return html, False

    indent = match.group(2)
    if body:
        repl = "<!-- %s:START -->\n%s\n%s<!-- %s:END -->" % (name, body, indent, name)
    else:
        repl = "<!-- %s:START -->\n%s<!-- %s:END -->" % (name, indent, name)
    return html[: match.start()] + repl + html[match.end():], True


def mark_current(nav_html: str, filename: str) -> str:
    nav_html = nav_html.replace(' aria-current="page"', "")
    return nav_html.replace(
        '<a href="%s">' % filename,
        '<a href="%s" aria-current="page">' % filename,
        1,
    )


def main() -> int:
    check_only = "--check" in sys.argv

    pages = sorted(p for p in ROOT.glob("*.html") if not p.name.startswith("_"))
    if not pages:
        print("No pages found.")
        return 1
    available = {p.name for p in pages}

    missing = []
    for lang in {split_page(p.name)[1] for p in pages}:
        for kind in ("nav", "footer"):
            path = component(kind, lang)
            if not path.exists():
                missing.append(str(path.relative_to(ROOT)))
    if missing:
        print("Missing component(s): %s" % ", ".join(sorted(missing)))
        return 1

    cache = {}
    changed = 0

    for page in pages:
        base, lang = split_page(page.name)

        if lang not in cache:
            cache[lang] = (
                component("nav", lang).read_text(encoding="utf-8").rstrip("\n"),
                component("footer", lang).read_text(encoding="utf-8").rstrip("\n"),
            )
        nav_src, foot_src = cache[lang]

        nav = mark_current(nav_src, page.name)
        nav = nav.replace("      <!-- LANG -->", build_switcher(base, lang, available))
        nav = re.sub(r"\n\s*\n", "\n", nav)  # drop the blank line if no switcher

        original = page.read_text(encoding="utf-8")
        updated, ok_nav = inject(original, "NAV", nav)
        updated, ok_foot = inject(updated, "FOOTER", foot_src)
        updated, ok_alt = inject(updated, "ALT", build_alternates(base, available))
        updated = re.sub(r'<html lang="[^"]*">', '<html lang="%s">' % lang, updated, count=1)

        absent = [n for n, ok in (("NAV", ok_nav), ("FOOTER", ok_foot), ("ALT", ok_alt)) if not ok]
        if absent:
            print("  WARN    %-22s %s  missing marker(s): %s"
                  % (page.name, lang, ", ".join(absent)))

        if updated == original:
            print("  ok      %-22s %s" % (page.name, lang))
            continue

        changed += 1
        if check_only:
            print("  WOULD   %-22s %s" % (page.name, lang))
        else:
            page.write_text(updated, encoding="utf-8")
            print("  swept   %-22s %s" % (page.name, lang))

    verb = "would change" if check_only else "changed"
    print("\n%d of %d page(s) %s." % (changed, len(pages), verb))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
