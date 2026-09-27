#!/usr/bin/env python
"""sketchcut.py -- a SKETCH of a figure as a PAPER CUT-OUT: the pencil drawing on its paper, cut out along the
figure's silhouette (holes filled, a thin paper margin), so it can be KEYED over a colour world. A whole-frame sketch
next to colour shots reads stark, plain and unfinished; a cut-out one sits in them. The world stays colour; only the
figure is the sketch.

    <PY> tools/sketchcut.py sk_hero/2202 sk_rival/2202 ...
        -> assets/cut/<job>/<seed>.png (+ .meta.json); use 'cut:sk_hero/2202' (K.img / K.sticker)
    <PY> tools/sketchcut.py pc_hero_bed/1101 --mask-from hero_bed/1101
        a TWIN (a whole-frame sketch of a colour picture: tools/pencil.py, or img2img) cut with the matte of its COLOUR
        original (same pose), so the pencil figure can sit over the colour frame (the room stays colour, only the
        figure is pencil)
    (PY = the kit's python: `python tools/film.py PY` prints its path)
Options: --margin 5 (px of paper around the figure); --color keeps the sketch's own colours (default: its tones on warm
paper, which also removes a model's colour cast).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def matte(im):
    from cutout import session
    from rembg import remove
    from scipy import ndimage
    out = remove(im.convert('RGB'), session=session(), post_process_mask=True)
    a = np.array(out)[:, :, 3].astype(np.float32) / 255
    m = a > 0.5
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
        keep = np.zeros(n + 1, bool)
        big = sizes.max()
        for i, s in enumerate(sizes, 1):
            keep[i] = s >= 0.02 * big
        m = keep[lab]
    return m


def sketchcut(spec, mask_from=None, margin=5, grey=True):
    from scipy import ndimage
    job, seed = spec.split('/')
    src = os.path.join(ROOT, 'assets', 'gen', job, seed + '.png')
    im = Image.open(src).convert('RGB')
    if mask_from:
        mj, ms = mask_from.split('/')
        base = Image.open(os.path.join(ROOT, 'assets', 'gen', mj, ms + '.png')).convert('RGB').resize(im.size)
        m = matte(base)
    else:
        m = matte(im)
    m = ndimage.binary_fill_holes(m)
    if margin:
        m = ndimage.binary_dilation(m, iterations=margin)
        m = ndimage.binary_fill_holes(m)
    a = ndimage.gaussian_filter(m.astype(np.float32), 1.2)
    rgb = np.array(im).astype(np.float32)
    if grey:
        L = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        paper = np.array([242, 238, 230], np.float32) / 255      # warm paper (tools/pencil.py's PAPER)
        rgb = (L[..., None] / 255.0) * paper[None, None, :] * 255
    arr = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), (np.clip(a, 0, 1) * 255).astype(np.uint8)])
    d = os.path.join(ROOT, 'assets', 'cut', job)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, seed + '.png')
    Image.fromarray(arr, 'RGBA').save(dst)
    ys, xs = np.where(arr[:, :, 3] > 127)
    meta = {'w': im.width, 'h': im.height, 'bbox': [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
            'eyes': None}
    json.dump(meta, open(dst[:-4] + '.meta.json', 'w'))
    print(f'  {job}/{seed}: bbox {meta["bbox"]}  ({"mask from " + mask_from if mask_from else "own matte"})', flush=True)


def main():
    a = sys.argv[1:]
    mask_from = None
    margin = 5
    if '--mask-from' in a:
        i = a.index('--mask-from'); mask_from = a[i + 1]; del a[i:i + 2]
    if '--margin' in a:
        i = a.index('--margin'); margin = int(a[i + 1]); del a[i:i + 2]
    grey = '--color' not in a
    a = [x for x in a if not x.startswith('--')]
    for spec in a:
        sketchcut(spec, mask_from, margin, grey)
    from cutout import build_manifest
    print(len(build_manifest()), 'manifest entries')


if __name__ == '__main__':
    main()
