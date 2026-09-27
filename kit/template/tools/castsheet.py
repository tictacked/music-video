#!/usr/bin/env python
"""castsheet.py -- one labelled contact sheet for several cast-sheet jobs (the director's review).

    python tools/castsheet.py hero_stand hero_run rival_stand --out notes/review/cast_model.jpg [--cell 300] [--cut]
    python tools/castsheet.py --prefix env_ --out notes/review/cast_env.jpg

Every image of each job in a row, seed labelled; cut-outs shown on a checker so the matte is visible.
"""
import argparse
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, 'assets', 'gen')
CUT = os.path.join(ROOT, 'assets', 'cut')


def checker(w, h, s=16):
    im = Image.new('RGB', (w, h), (70, 70, 78))
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range((y // s) % 2 * s, w, 2 * s):
            d.rectangle([x, y, x + s - 1, y + s - 1], fill=(92, 92, 102))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('jobs', nargs='*')
    ap.add_argument('--prefix')
    ap.add_argument('--out', required=True)
    ap.add_argument('--cell', type=int, default=300)
    ap.add_argument('--cut', action='store_true', help='show cut-outs (on a checker) instead of the raw pictures')
    a = ap.parse_args()
    jobs = list(a.jobs)
    if a.prefix:
        jobs += sorted(j for j in os.listdir(GEN) if j.startswith(a.prefix) and os.path.isdir(os.path.join(GEN, j)))
    rows = []
    for j in jobs:
        d = os.path.join(GEN, j)
        if not os.path.isdir(d):
            continue
        fs = sorted(f for f in os.listdir(d) if f.endswith('.png') and not f.startswith('_'))
        rows.append((j, fs))
    if not rows:
        raise SystemExit('nothing to show')
    cell = a.cell
    ncol = max(len(fs) for _, fs in rows)
    S = Image.new('RGB', (ncol * cell + 10, len(rows) * (cell + 22)), (20, 20, 24))
    dr = ImageDraw.Draw(S)
    for r, (j, fs) in enumerate(rows):
        for c, f in enumerate(fs):
            src = os.path.join(CUT, j, f) if a.cut and os.path.exists(os.path.join(CUT, j, f)) else os.path.join(GEN, j, f)
            im = Image.open(src)
            im.thumbnail((cell, cell))
            x, y = c * cell + (cell - im.width) // 2, r * (cell + 22) + 20 + (cell - im.height) // 2
            if im.mode == 'RGBA':
                bg = checker(im.width, im.height)
                bg.paste(im, (0, 0), im)
                im = bg
            S.paste(im.convert('RGB'), (x, y))
            dr.text((c * cell + 4, r * (cell + 22) + 4), f'{j}/{f[:-4]}', fill=(255, 210, 120))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    S.save(a.out, quality=86)
    print(a.out, S.size)


if __name__ == '__main__':
    main()
