#!/usr/bin/env python
"""mask.py -- an inpaint mask (white = repaint) for tools/gen.py's "mask" key (or any inpainting tool), from ellipses
and boxes.

    python tools/mask.py assets/masks/hero_face.png --like assets/gen/hero_mid/42.png --ellipse 670,285,140,115
    python tools/mask.py out.png --size 1344x768 --box 100,200,300,400 --ellipse cx,cy,rx,ry

A recipe that worked for repainting part of a photo-based picture: init = the picture, w/h = its size, only_masked
true, padding 48, mask_blur 10, denoise 0.6-0.8. Coordinates are the PICTURE's pixels (read them off the full-size
picture, never a thumbnail).
"""
import argparse
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--like')
    ap.add_argument('--size')
    ap.add_argument('--ellipse', action='append', default=[])
    ap.add_argument('--box', action='append', default=[])
    a = ap.parse_args()
    if a.like:
        w, h = Image.open(a.like).size
    else:
        w, h = map(int, a.size.split('x'))
    m = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(m)
    for e in a.ellipse:
        cx, cy, rx, ry = map(float, e.split(','))
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    for b in a.box:
        x0, y0, x1, y1 = map(float, b.split(','))
        d.rectangle([x0, y0, x1, y1], fill=255)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    m.save(a.out)
    print(a.out, (w, h))


if __name__ == '__main__':
    main()
