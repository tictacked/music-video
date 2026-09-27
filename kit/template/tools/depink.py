#!/usr/bin/env python
"""depink.py -- clean the flat HOT-PINK (magenta) ground that a cut-out keeps inside hair gaps and along its edges,
in every cut-out (in place). For pictures generated on a flat magenta ground (tools/cutout.py keys a MINT ground itself).

    python tools/depink.py                       # every assets/cut/*/*.png: the residue keyed out (transparent)
    python tools/depink.py --paint hero_,rival_  # jobs starting with these prefixes: the residue PAINTED instead
    python tools/depink.py --paint hero_ --colour 0b0d10     # the paint colour (default hair-black 0b0d10)
    python tools/depink.py --only hero_          # only jobs starting with these prefixes
    python tools/depink.py --dry                 # count what would change

rembg (isnet-anime) keeps the flat magenta ground wherever hair encloses it (a 14k-px patch between a hand and the
hair; pink strands along many hair edges). Measured, the residue is MAGENTA -- r - max(g, b) > 40 AND b - g > 12 --
while blush and mouths are red over skin (b <= g) and are NOT caught. Two modes:
  key    (default) the residue becomes TRANSPARENT: right for light hair, and wherever a hole just shows what is behind.
  paint  the residue is painted one solid colour: for DARK hair, where a transparent hole inside the silhouette would
         show the background through (white through a die-cut sticker ring).
Idempotent. Leave out figures that really have magenta in them (a creature's mouth, a pink dress): --only.
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAIR = np.array([11, 13, 16], np.float32)


def depink(arr, mode='key', colour=HAIR):
    """arr: HxWx4 uint8 (modified in place). Returns the number of pixels changed.
    mode 'key': make the magenta residue TRANSPARENT. mode 'paint': paint it `colour` (RGB), keeping the alpha."""
    rgb = arr[:, :, :3].astype(np.float32)
    e = rgb[..., 0] - np.maximum(rgb[..., 1], rgb[..., 2])
    # a DARKER pink ground leaves slivers of itself in hair gaps and a 1-px pink line along edges under rembg's hard
    # mask: catch weaker magenta (e > 18, ramp 30; b - g > 8). Blush is red over skin (b <= g): safe.
    k = np.clip((e - 18) / 30, 0, 1) * ((rgb[..., 2] - rgb[..., 1]) > 8) * (arr[:, :, 3] > 0)
    n = int((k > 0.02).sum())
    if n and mode == 'paint':
        c = np.asarray(colour, np.float32)
        arr[:, :, :3] = (rgb + (c - rgb) * k[..., None]).round().astype(np.uint8)
    elif n:
        arr[:, :, 3] = (arr[:, :, 3].astype(np.float32) * (1 - k)).round().astype(np.uint8)
    return n


def main():
    a = sys.argv[1:]
    opt = lambda k: tuple(p for p in a[a.index(k) + 1].split(',') if p) if k in a else ()
    dry = '--dry' in a
    paint, only = opt('--paint'), opt('--only')
    hexc = a[a.index('--colour') + 1].lstrip('#') if '--colour' in a else '0b0d10'
    colour = np.array([int(hexc[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
    tot = 0
    for f in sorted(glob.glob(os.path.join(ROOT, 'assets', 'cut', '*', '*.png'))):
        job = os.path.basename(os.path.dirname(f))
        if only and not job.startswith(only):
            continue
        arr = np.array(Image.open(f).convert('RGBA'))
        n = depink(arr, 'paint' if paint and job.startswith(paint) else 'key', colour)
        if n:
            tot += n
            print(f'{os.path.relpath(f, ROOT)}: {n} px')
            if not dry:
                Image.fromarray(arr).save(f, optimize=False, compress_level=3)
    print(f'{"would change" if dry else "changed"} {tot} px')


if __name__ == '__main__':
    main()
