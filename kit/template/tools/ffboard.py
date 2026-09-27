#!/usr/bin/env python
"""ffboard.py -- first-frame review board: for each ff_* job, the source frame (img2img init, if any) + every seed.

    python tools/ffboard.py ff_r1 [--out notes/clips/ff/_board_r1.jpg] [--cell 480]
    python tools/ffboard.py ff_r2_turn,ff_r2_run

The argument is a prefix (every assets/gen/<prefix>* job) or a comma list of jobs."""
import argparse
import glob
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('which')
    ap.add_argument('--out')
    ap.add_argument('--cell', type=int, default=480)
    a = ap.parse_args()
    if ',' in a.which:
        jobs = a.which.split(',')
    else:
        jobs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, 'assets', 'gen', a.which + '*')))
    rows = []
    for j in jobs:
        pngs = sorted(glob.glob(os.path.join(ROOT, 'assets', 'gen', j, '*.png')))
        pngs = [p for p in pngs if not os.path.basename(p).startswith('_')]
        if not pngs:
            continue
        sp = pngs[0][:-4] + '.json'                  # the generator's sidecar (a picture made elsewhere may have none)
        side = json.load(open(sp, encoding='utf-8')) if os.path.exists(sp) else {}
        init = side.get('init')
        cells = []
        if init:
            cells.append(('source', os.path.join(ROOT, init) if not os.path.isabs(init) else init))
        cells += [(os.path.basename(p)[:-4], p) for p in pngs]
        rows.append((j, cells))
    cw = a.cell
    ch = round(cw * 704 / 1280)
    ncol = max(len(c) for _, c in rows)
    S = Image.new('RGB', (ncol * cw, len(rows) * (ch + 20)), (18, 18, 20))
    d = ImageDraw.Draw(S)
    for r, (j, cells) in enumerate(rows):
        y = r * (ch + 20)
        for c, (lab, p) in enumerate(cells):
            im = Image.open(p).convert('RGB')
            im.thumbnail((cw, ch))
            S.paste(im, (c * cw + (cw - im.width) // 2, y + 20 + (ch - im.height) // 2))
            d.text((c * cw + 4, y + 4), f'{j}  {lab}' if c == 0 or lab != 'source' else lab, fill=(255, 210, 120))
    out = a.out or os.path.join(ROOT, 'notes', 'clips', 'ff', f'_board_{a.which.replace(",", "_")[:40]}.jpg')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    S.save(out, quality=86)
    print(out, S.size)


if __name__ == '__main__':
    main()
