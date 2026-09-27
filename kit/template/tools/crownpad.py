#!/usr/bin/env python
"""crownpad.py -- give a picture whose head touches the top edge its missing crown back (a figure drawn with the top of
its head cut off keeps that cut in every frame of an image-to-video clip made from it).

    python tools/crownpad.py <job/seed> [--scale 0.86] [--band 48]
      -> notes/work/crown/<job>_<seed>_init.png (the picture shrunk onto its own flat ground, bottom-aligned, so there is
         headroom) + ..._mask.png (white = repaint: the empty top plus `band` px of the old head top, so the new crown
         grows out of the old hair instead of sitting on a seam). Feed both to tools/gen.py as init + mask (an outpaint),
         or to any inpainting tool."""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    a = sys.argv[1:]
    key = a[0]
    s = float(a[a.index('--scale') + 1]) if '--scale' in a else 0.86
    band = int(a[a.index('--band') + 1]) if '--band' in a else 48
    im = Image.open(os.path.join(ROOT, 'assets', 'gen', key + '.png')).convert('RGB')
    W, H = im.size
    px = np.asarray(im).astype(np.float32)
    ground = np.median(np.concatenate([px[:, :24].reshape(-1, 3), px[:, -24:].reshape(-1, 3)]), 0)
    w, h = round(W * s), round(H * s)
    x0, y0 = (W - w) // 2, H - h
    canvas = Image.new('RGB', (W, H), tuple(int(v) for v in ground))
    canvas.paste(im.resize((w, h), Image.LANCZOS), (x0, y0))
    # THE SKETCH (a denoise-0.9 outpaint of an EMPTY band drew a second face above the head, 6 of 6 seeds): paint a
    # rough crown for the model to refine. Fit a circle to the head's silhouette just below the cut, fill the part of
    # it above the cut with the hair colour, and ink its arc.
    cv = np.asarray(canvas).astype(np.float32)
    fig = np.linalg.norm(cv - ground, axis=2) > 40
    ys, rows = range(y0 + 2, y0 + 70, 2), []
    for y in ys:
        xs = np.nonzero(fig[y])[0]
        if len(xs):
            runs = np.split(xs, np.nonzero(np.diff(xs) > 6)[0] + 1)
            head = max(runs, key=len)                              # the widest run = the head (not a stray strand)
            rows.append((y, head[0], head[-1]))
    widest = max(b - a for _, a, b in rows)
    pts = []
    for y, a0, b0 in rows:                                         # an ahoge or a lone strand is not the crown
        if b0 - a0 >= 0.3 * widest:
            pts += [(a0, y), (b0, y)]
    P = np.array(pts, np.float64)
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]           # algebraic circle fit: x^2+y^2 = 2ax + 2by + c
    ca, cb, cc = np.linalg.lstsq(A, (P ** 2).sum(1), rcond=None)[0]
    r = float(np.sqrt(cc + ca * ca + cb * cb))
    col = tuple(int(v) for v in np.median(cv[y0 + 2:y0 + 12][fig[y0 + 2:y0 + 12]], 0))
    from PIL import ImageDraw
    d = ImageDraw.Draw(canvas)
    bbox = (ca - r, cb - r, ca + r, cb + r)
    d.pieslice(bbox, 180, 360, fill=col)                           # the upper half-disc...
    canvas.paste(im.resize((w, h), Image.LANCZOS), (x0, y0))       # ...under the real picture (only the dome shows)
    d = ImageDraw.Draw(canvas)
    ink = (48, 30, 26)
    ang = np.linspace(np.pi, 2 * np.pi, 180)
    arc = [(ca + r * np.cos(t), cb + r * np.sin(t)) for t in ang if cb + r * np.sin(t) < y0 + 1]
    if len(arc) > 1:
        d.line(arc, fill=ink, width=4)
    print(f'  crown sketch: circle centre ({ca:.0f},{cb:.0f}) r {r:.0f}, dome top y {cb - r:.0f}, hair {col}')
    mask = Image.new('L', (W, H), 0)
    mask.paste(255, (0, 0, W, y0 + band))
    out = os.path.join(ROOT, 'notes', 'work', 'crown')
    os.makedirs(out, exist_ok=True)
    base = key.replace('/', '_')
    canvas.save(os.path.join(out, base + '_init.png'))
    mask.save(os.path.join(out, base + '_mask.png'))
    print(f'{key}: ground {[int(v) for v in ground]}, figure at {x0},{y0} {w}x{h}, repaint rows 0-{y0 + band}')


if __name__ == '__main__':
    main()
