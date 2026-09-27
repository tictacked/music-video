#!/usr/bin/env python
"""upstill.py -- one STILL through the upscaler (for a picture a scene zooms far into, e.g. an eye close-up at 2.2x).

    python tools/upstill.py <in.png> <out.png> [--model animevideov3] [--scale 4]
      (runs with machine.json's upscale_python, exactly like tools/upscale.py: its SETUP applies)

Alpha, if any, is resized (Lanczos) alongside. The scene must draw the result at its SOURCE size in source px
(e.g. drawImage(img, x, y, 1344 * s, 768 * s)), never at img.naturalWidth, so the upscale drops in without moving."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upscale import up  # noqa: E402  (hands this run to upscale_python when this python has no torch)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    src, dst = a[0], a[1]
    name = a[a.index('--model') + 1] if '--model' in a else 'animevideov3'
    k = int(a[a.index('--scale') + 1]) if '--scale' in a else 4
    im = Image.open(src)
    w, h = im.size
    size = (w * k, h * k)
    rgb = np.asarray(im.convert('RGB'))
    out = Image.fromarray(up(name, rgb, size), 'RGB')
    if im.mode in ('RGBA', 'LA', 'P') and 'A' in im.convert('RGBA').getbands():
        al = im.convert('RGBA').getchannel('A').resize(size, Image.LANCZOS)
        out.putalpha(al)
    out.save(dst, optimize=False, compress_level=6)
    print(f'{src} ({w}x{h}) -> {dst} ({size[0]}x{size[1]}, {name})')


if __name__ == '__main__':
    main()
