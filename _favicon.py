#!/usr/bin/env python3
"""
Generate the BARSS favicon set.

The mark: a bone "B" on black over a crimson rule. The rule is the site's
.ledger device (see css/barss.css) reduced to one stroke; the letterform is
set in Impact, which is the documented fallback in the site's Anton display
stack, so the favicon and the masthead wordmark share a family.

Palette is BARSS Visual System v0.2: bone #F4EFE2, Du Bois crimson #DC143C.

No SVG favicon is shipped on purpose. Rendering it would need either the
viewer to have Impact installed (not safe on Linux) or the glyph converted to
paths (no fontTools here), and a vector that drifts from the raster is worse
than no vector. PNG + ICO covers every browser.

Outputs:
    img/favicon-32.png        32x32    standard
    img/favicon-64.png        64x64    hi-DPI
    img/apple-touch-icon.png  180x180  iOS home screen
    favicon.ico               16/32/48 legacy, auto-requested at site root

Usage:
    python _favicon.py
"""

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
IMG = ROOT / "img"

BLACK = (0, 0, 0, 255)
BONE = (244, 239, 226, 255)
CRIMSON = (220, 20, 60, 255)

# Heavy condensed first, then progressively wider fallbacks.
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\ariblk.ttf",
    "/Library/Fonts/Impact.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]

# Proportions on a unit square.
LETTER_SCALE = 0.88     # cap height as a fraction of the canvas
BAR_X0, BAR_X1 = 0.14, 0.86
BAR_Y0, BAR_Y1 = 0.775, 0.868
LETTER_CENTER_Y = 0.40  # optical centre of the B within the field above the bar

SUPERSAMPLE = 8         # render large, downsample, so small sizes stay clean


def find_font() -> str:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit(
        "No heavy sans font found. Add one to FONT_CANDIDATES:\n  "
        + "\n  ".join(FONT_CANDIDATES)
    )


def render(size: int, font_path: str) -> Image.Image:
    big = size * SUPERSAMPLE
    img = Image.new("RGBA", (big, big), BLACK)
    draw = ImageDraw.Draw(img)

    draw.rectangle(
        [int(big * BAR_X0), int(big * BAR_Y0),
         int(big * BAR_X1), int(big * BAR_Y1)],
        fill=CRIMSON,
    )

    font = ImageFont.truetype(font_path, int(big * LETTER_SCALE))
    left, top, right, bottom = draw.textbbox((0, 0), "B", font=font)
    w, h = right - left, bottom - top
    draw.text(
        ((big - w) / 2 - left, big * LETTER_CENTER_Y - h / 2 - top),
        "B",
        font=font,
        fill=BONE,
    )

    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    IMG.mkdir(exist_ok=True)
    font_path = find_font()
    print("  font: %s" % font_path)

    for size in (32, 64):
        render(size, font_path).save(IMG / ("favicon-%d.png" % size))
        print("  wrote img/favicon-%d.png" % size)

    render(180, font_path).save(IMG / "apple-touch-icon.png")
    print("  wrote img/apple-touch-icon.png   180x180")

    render(48, font_path).save(
        ROOT / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )
    print("  wrote favicon.ico                16/32/48")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
