#!/usr/bin/env python
"""pickboard.py -- one labelled board of several jobs' seeds (each job a row), for picking.
    python tools/pickboard.py out.jpg job1 job2 ... [--w 420]
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    args = sys.argv[1:]
    w = 420
    if '--w' in args:
        i = args.index('--w'); w = int(args[i + 1]); del args[i:i + 2]
    out, jobs = args[0], args[1:]
    rows = []
    for j in jobs:
        d = os.path.join(ROOT, 'assets', 'gen', j)
        fs = sorted(f for f in os.listdir(d) if f.endswith('.png') and not f.startswith('_')) if os.path.isdir(d) else []
        rows.append((j, fs))
    ncol = max(len(fs) for _, fs in rows) or 1
    cells = []
    for j, fs in rows:
        ims = []
        for f in fs:
            im = Image.open(os.path.join(ROOT, 'assets', 'gen', j, f)).convert('RGB')
            h = int(w * im.height / im.width)
            ims.append((f, im.resize((w, h))))
        cells.append((j, ims))
    rh = [max([im.height for _, im in ims] + [60]) + 26 for _, ims in cells]
    S = Image.new('RGB', (ncol * (w + 6) + 6, sum(rh) + 6), (18, 18, 20))
    dr = ImageDraw.Draw(S)
    font = None
    for fn in ('segoeuib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf', 'Arial Bold.ttf'):   # Pillow searches system fonts
        try:
            font = ImageFont.truetype(fn, 18)
            break
        except OSError:
            pass
    y = 6
    for (j, ims), h in zip(cells, rh):
        for c, (f, im) in enumerate(ims):
            x = 6 + c * (w + 6)
            S.paste(im, (x, y + 24))
            dr.text((x + 2, y + 2), f'{j}/{f[:-4]}', fill=(255, 214, 120), font=font)
        y += h
    S.save(out, quality=86)
    print(out, S.size)


if __name__ == '__main__':
    main()
