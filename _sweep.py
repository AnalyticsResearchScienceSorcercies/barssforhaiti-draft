#!/usr/bin/env python3
"""
Sitewide nav + footer sweep for barssforhaiti.com.

Reads _components/nav.html and _components/footer.html and injects them into
every root-level .html file between the NAV:START/NAV:END and
FOOTER:START/FOOTER:END markers. Sets aria-current="page" on the nav link that
matches the file being written.

Same pattern as the _nav_sweep.py / _navjs_sweep.py scripts in the konkret repo:
edit the component once, run the sweep, every page updates.

Usage:
    python _sweep.py            # write changes
    python _sweep.py --check    # report what would change, write nothing
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = ROOT / "_components"

BLOCKS = {
    "NAV": COMPONENTS / "nav.html",
    "FOOTER": COMPONENTS / "footer.html",
}


def inject(html: str, name: str, body: str) -> str:
    """Replace the content between <!-- NAME:START --> and <!-- NAME:END -->."""
    pattern = re.compile(
        r"(<!--\s*%s:START\s*-->\n).*?(\n<!--\s*%s:END\s*-->)" % (name, name),
        re.DOTALL,
    )
    if not pattern.search(html):
        return html
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), html)


def mark_current(nav_html: str, filename: str) -> str:
    """Stamp aria-current="page" on the nav link for this page, strip it elsewhere."""
    nav_html = nav_html.replace(' aria-current="page"', "")
    return nav_html.replace(
        '<a href="%s">' % filename,
        '<a href="%s" aria-current="page">' % filename,
        1,
    )


def main() -> int:
    check_only = "--check" in sys.argv

    missing = [str(p) for p in BLOCKS.values() if not p.exists()]
    if missing:
        print("Missing component(s): %s" % ", ".join(missing))
        return 1

    nav_src = BLOCKS["NAV"].read_text(encoding="utf-8").rstrip("\n")
    foot_src = BLOCKS["FOOTER"].read_text(encoding="utf-8").rstrip("\n")

    pages = sorted(p for p in ROOT.glob("*.html") if not p.name.startswith("_"))
    if not pages:
        print("No pages found.")
        return 1

    changed = 0
    for page in pages:
        original = page.read_text(encoding="utf-8")
        updated = inject(original, "NAV", mark_current(nav_src, page.name))
        updated = inject(updated, "FOOTER", foot_src)

        if updated == original:
            print("  ok      %s" % page.name)
            continue

        changed += 1
        if check_only:
            print("  WOULD   %s" % page.name)
        else:
            page.write_text(updated, encoding="utf-8")
            print("  swept   %s" % page.name)

    verb = "would change" if check_only else "changed"
    print("\n%d of %d page(s) %s." % (changed, len(pages), verb))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
