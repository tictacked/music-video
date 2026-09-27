#!/usr/bin/env python
"""sweepsheet.py -- one labelled contact sheet of every picture in assets/gen/<prefix>*/ (default sw_*: a sweep of
styles, LoRA weights or settings), for the user to pick from: notes/sweep_sheet.jpg. Cells keep each picture's aspect
(portraits and landscapes mixed).

    python tools/sweepsheet.py [--prefix sw_] [--out notes/sweep_sheet.jpg] [--cell 460] [--cols 5]
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix', default='sw_')
    ap.add_argument('--out', default='notes/sweep_sheet.jpg')
    ap.add_argument('--cell', type=int, default=460)
    ap.add_argument('--cols', type=int, default=5)
    a = ap.parse_args()
    gen = os.path.join(ROOT, 'assets', 'gen')
    items = []
    for job in sorted(os.listdir(gen)):
        if not job.startswith(a.prefix):
            continue
        for f in sorted(os.listdir(os.path.join(gen, job))):
            if f.endswith('.png') and not f.startswith('_'):
                items.append((f'{job[len(a.prefix):]} {f[:-4]}', os.path.join(gen, job, f)))
    c, lab = a.cell, 26
    rows = (len(items) + a.cols - 1) // a.cols
    S = Image.new('RGB', (a.cols * c, rows * (c + lab)), (16, 16, 18))
    d = ImageDraw.Draw(S)
    font = ImageFont.load_default()
    for fn in ('consola.ttf', 'DejaVuSansMono.ttf', 'Menlo.ttc'):   # a bare name: Pillow searches the system's fonts
        try:
            font = ImageFont.truetype(fn, 18)
            break
        except OSError:
            pass
    for i, (name, p) in enumerate(items):
        im = Image.open(p).convert('RGB')
        im.thumbnail((c - 8, c - 8))
        x, y = (i % a.cols) * c, (i // a.cols) * (c + lab)
        S.paste(im, (x + (c - im.width) // 2, y + lab + (c - im.height) // 2))
        d.text((x + 8, y + 4), name, fill=(255, 205, 110), font=font)
    out = os.path.join(ROOT, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    S.save(out, quality=90)
    print(out, len(items), 'pictures')


if __name__ == '__main__':
    main()
