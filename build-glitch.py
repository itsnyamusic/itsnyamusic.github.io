#!/usr/bin/env python3
"""Draw the glitch masks in assets/.

    python build-glitch.py            # rewrite the three files
    python build-glitch.py --check    # verify without writing, exits 1 if stale

A new release never needs this. The masks are shapes without a colour:
site.css lays them over the page's accent, so every page, old or new, gets
them in its own colour. Run this only to change how the tears look.

    glitch-halo.svg        the torn fringe around a cover or the flyer
    glitch-halo-small.svg  the few small tears on the covers in a list row
    glitch-field.svg       the bands reaching in from the edges of the screen

Every file is a 1000-unit square of white rectangles at a few opacities,
stretched over whatever it masks. The shapes come from a seeded random
generator, so a run always gives the same files. To get a different tear,
change a SEED; to change its character, change the lists of sizes.

(glitch-bloom.svg, the corner bloom, is older and hand-made. It is not
drawn here.)
"""
import random
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"

HALO_SEED = 11
FIELD_SEED = 23

OPACITIES = [1, 1, 0.7, 0.7, 0.45, 0.45, 0.25]


def svg(rects, note, height=1000):
    body = "".join(
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}"'
        + (f' opacity="{o:g}"' if o < 1 else "")
        + "/>"
        for x, y, w, h, o in rects
    )
    return (
        f"<!-- {note} -->\n"
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" '
        f'viewBox="0 0 1000 {height}" preserveAspectRatio="none">'
        f'<g fill="#fff">{body}</g></svg>\n'
    )


def halo():
    """A torn fringe around a picture.

    site.css gives the picture a transparent border and stretches this file
    over picture plus border. The picture covers x 64.5..935.5 and y 32..903
    of the square, so only what lies outside that shows. Bands start at the
    picture's edge and stick out, like rows of it knocked sideways, and a few
    loose blocks float further out. The bottom is the heavy side, where a
    shadow would fall.
    """
    r = random.Random(HALO_SEED)
    left, right, top, bottom = 64.5, 935.5, 32, 903
    rects = []

    def side(edge_x, direction):
        y = top + r.uniform(0, 30)
        while y < bottom - 6:
            h = r.choice([3, 3, 4, 6, 6, 9, 12, 16, 22, 30])
            if r.random() < 0.62:
                length = r.choice([10, 14, 18, 24, 30, 38, 46, 56, 64.5])
                o = r.choice(OPACITIES)
                x = edge_x - length if direction < 0 else edge_x
                rects.append((round(x, 1), round(y, 1), length, h, o))
                if r.random() < 0.35:  # a loose block beyond the band
                    bw = r.choice([5, 7, 9, 12])
                    bh = min(h, r.choice([4, 6, 9]))
                    gap = r.choice([4, 6, 10])
                    bx = x - gap - bw if direction < 0 else x + length + gap
                    if 0 <= bx and bx + bw <= 1000:
                        rects.append((round(bx, 1), round(y, 1), bw, bh, r.choice([0.7, 0.45, 0.25])))
            y += h + r.choice([0, 0, 2, 4, 8, 14, 24, 40])

    side(left, -1)
    side(right, +1)

    # Top: sparse and short.
    x = left + r.uniform(0, 60)
    while x < right - 20:
        w = r.choice([14, 22, 36, 60, 90])
        if r.random() < 0.3:
            h = r.choice([6, 10, 14, 20, 32])
            rects.append((round(x, 1), top - h, w, h, r.choice([0.7, 0.45, 0.25])))
        x += w + r.choice([10, 30, 60, 90])

    # Bottom: blocks hanging off the picture's lower edge.
    x = 20
    while x < 980:
        w = r.choice([10, 16, 24, 40, 64, 96, 140])
        if r.random() < 0.6:
            h = r.choice([8, 12, 18, 26, 36, 50, 70, 97])
            rects.append((round(x, 1), bottom, min(w, 1000 - x), h, r.choice(OPACITIES)))
        x += w + r.choice([0, 0, 4, 8, 16, 30])

    for _ in range(9):  # thin displaced lines under the picture
        w = r.choice([120, 180, 260, 340, 480])
        x = r.uniform(0, 1000 - w)
        y = r.uniform(bottom + 8, 992)
        h = r.choice([3, 4, 6])
        rects.append((round(x, 1), round(y, 1), w, h, r.choice([0.7, 0.45, 0.25])))

    for _ in range(14):  # pixel debris
        s = r.choice([6, 8, 10, 14])
        x = r.uniform(0, 1000 - s)
        y = r.uniform(bottom + 20, 1000 - s)
        rects.append((round(x, 1), round(y, 1), s, s * r.choice([0.6, 1]), r.choice([1, 0.7, 0.45])))

    return svg(rects, "Mask for the torn fringe around covers. Stretched over the picture "
                      "plus its transparent border; see site.css.")


def field():
    """The screen tearing at its own edges.

    The halo one size up: bands anchored to the edge of the viewport that
    reach a little way in, with loose blocks at their tips. Right edge in
    the upper two thirds, left edge in the lower half, so the corner bloom
    (top left) and the wireframe (bottom right) keep their corners.
    """
    r = random.Random(FIELD_SEED)
    rects = []

    def edge(side, y0, y1, count, max_length):
        for y in sorted(r.uniform(y0, y1) for _ in range(count)):
            h = r.choice([3, 3, 4, 6, 8, 11, 15, 22])
            length = min(r.choice([30, 50, 70, 95, 130, 170, 220, 280]), max_length)
            o = r.choice([1, 0.7, 0.7, 0.45, 0.45, 0.25])
            x = 0 if side < 0 else 1000 - length
            rects.append((x, round(y, 1), length, h, o))
            for _ in range(r.choice([0, 1, 1, 2, 3])):
                bw = r.choice([4, 6, 8, 12])
                bh = r.choice([4, 6, 9, 13])
                gap = r.choice([5, 9, 16, 30])
                bx = length + gap if side < 0 else 1000 - length - gap - bw
                by = y + r.choice([-6, 0, 0, h, h + 5])
                rects.append((round(bx, 1), round(by, 1), bw, bh, r.choice([0.7, 0.45, 0.25])))

    edge(+1, 90, 660, 15, 280)
    edge(-1, 430, 960, 9, 200)
    return svg(rects, "Mask for the bands tearing in from the edges of the screen. "
                      "Stretched over the viewport; see site.css.")


# The small tears are few enough to place by hand. Three variants, stacked
# in one file like a sprite; site.css shows one per row and the rows take
# turns. The picture covers 88..912 of each 1000-unit square.
SMALL = [
    [(0, 300, 88, 45, 1), (40, 362, 48, 28, 0.6), (912, 620, 88, 58, 0.8),
     (952, 704, 40, 40, 0.5), (150, 912, 270, 46, 0.7), (480, 912, 60, 88, 0.45)],
    [(912, 180, 88, 40, 1), (912, 236, 48, 28, 0.5), (0, 540, 88, 68, 0.8),
     (0, 636, 44, 40, 0.45), (560, 912, 300, 40, 0.6), (600, 42, 120, 46, 0.5)],
    [(0, 120, 88, 30, 0.9), (0, 760, 88, 54, 0.7), (912, 430, 88, 44, 1),
     (912, 486, 58, 26, 0.5), (100, 912, 80, 88, 0.6), (300, 940, 400, 30, 0.4)],
]


def small():
    rects = [(x, y + 1000 * i, w, h, o) for i, variant in enumerate(SMALL) for x, y, w, h, o in variant]
    return svg(rects, "Mask for the small tears on row covers: three variants stacked, "
                      "one shown per row. See site.css.", height=1000 * len(SMALL))


FILES = {
    "glitch-halo.svg": halo,
    "glitch-halo-small.svg": small,
    "glitch-field.svg": field,
}


def main():
    check = "--check" in sys.argv[1:]
    stale = False
    for name, draw in FILES.items():
        path = ASSETS / name
        new = draw()
        old = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else None
        if new == old:
            print(f"  up to date   assets/{name}")
        elif check:
            print(f"  STALE        assets/{name}")
            stale = True
        else:
            path.write_text(new, encoding="utf-8", newline="\n")
            print(f"  written      assets/{name}")
    if stale:
        sys.exit(1)


if __name__ == "__main__":
    main()
