#!/usr/bin/env python3
"""Build the spinning wireframe in the corner of every page.

The source is a turntable render: a folder of transparent PNG frames
(spin_0000.png, spin_0001.png, ...) covering one full turn. This packs them
into a sprite sheet of 12 columns by 6 rows, 72 frames, and keeps only the
alpha channel. site.css uses the sheet as a mask over the page's accent
colour, so the object takes any colour without a second file.

    python build-spin.py <frames folder>
    python build-spin.py <frames folder> --start 12

--start  which source frame becomes frame 0. That is the pose shown to
         visitors who ask for reduced motion, so pick a good one.

It writes the sheet twice. assets/spin.webp is what every visitor gets.
assets/spin-2x.webp is half as large again and twice the weight; site.css
only asks for it on a big desktop window, where the site scales itself up
and the small sheet would be stretched soft.

The sheet is cropped to the object, the same crop on every frame and
symmetric about the turn axis so it does not wobble. If the crop changes
shape the script says so: put the printed aspect-ratio into the
`.wrap::after` rule in assets/site.css.

Needs Pillow (pip install pillow).
"""
import argparse
import glob
import os
import sys

from PIL import Image, ImageChops

COLS, ROWS = 12, 6
FRAMES = COLS * ROWS
LEVELS = 4           # alpha steps kept. Thin lines need no more, and every extra step costs weight
FLOOR = 100          # source alpha below this is dropped: the faint lines on the far side of the mesh
GAMMA = 0.8          # lifts what is left after downscaling, so the lines stay solid
PAD = 4              # source pixels of air around the object
HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS = {'spin.webp': 168, 'spin-2x.webp': 252}   # file -> width of one frame in pixels


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('frames', help='folder of spin_*.png frames')
    ap.add_argument('--start', type=int, default=0)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.frames, 'spin_*.png')))
    if len(files) < FRAMES:
        sys.exit(f'need at least {FRAMES} frames, found {len(files)}')

    # Pick 72 evenly spaced frames, starting at --start.
    step = len(files) / FRAMES
    picked = [files[(args.start + round(i * step)) % len(files)] for i in range(FRAMES)]
    alphas = [Image.open(f).convert('RGBA').getchannel('A') for f in picked]

    union = alphas[0]
    for a in alphas[1:]:
        union = ImageChops.lighter(union, a)
    left, top, right, bottom = union.getbbox()
    axis = union.width // 2
    half = max(axis - left, right - axis) + PAD
    crop = (axis - half, max(top - PAD, 0), axis + half, min(bottom + PAD, union.height))
    cw, ch = crop[2] - crop[0], crop[3] - crop[1]

    q = 255 / (LEVELS - 1)
    for name, fw in SHEETS.items():
        fh = round(fw * ch / cw)
        sheet = Image.new('L', (fw * COLS, fh * ROWS), 0)
        for i, a in enumerate(alphas):
            frame = a.crop(crop).point(lambda v: 0 if v < FLOOR else v)
            frame = frame.resize((fw, fh), Image.LANCZOS)
            frame = frame.point(lambda v: round(255 * (v / 255) ** GAMMA))
            frame = frame.point(lambda v: round(round(v / q) * q))
            sheet.paste(frame, ((i % COLS) * fw, (i // COLS) * fh))

        # White with the lines in alpha: a CSS mask reads the alpha channel.
        out = os.path.join(HERE, 'assets', name)
        white = Image.new('L', sheet.size, 255)
        Image.merge('RGBA', (white, white, white, sheet)).save(out, lossless=True, quality=100, method=6)

        print(f'assets/{name}: {sheet.width}x{sheet.height}, {os.path.getsize(out) // 1024} KB, '
              f'frame {fw}x{fh}  ->  aspect-ratio: {fw} / {fh};')


if __name__ == '__main__':
    main()
