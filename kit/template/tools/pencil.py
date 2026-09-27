#!/usr/bin/env python
"""pencil.py -- a PENCIL TWIN of a colour picture, procedurally (XDoG lines + soft graphite tone on warm paper), so
the pose, the eyes (open or CLOSED) and the framing match the colour picture EXACTLY. img2img twins keep the pose, but
at a strength that keeps it they stay a painting (a closed-eyes twin came back painted every time).

    <PY> tools/pencil.py <job>/<seed> [...] [--tone 0.35] [--sigma 1.0]
        -> assets/gen/pc_<job>/<seed>.png (whole) ; then tools/sketchcut.py pc_<job>/<seed> --mask-from <job>/<seed>
           cuts just the figure out of it (the world stays colour; only the figure is the sketch)
    <PY> tools/pencil.py --clip hero_turn 123    (a clip frame: assets/clips/<name>/<f>.jpg -> pc_clip_<name>/<f>.png)
    (PY = the kit's python: `python tools/film.py PY` prints its path)
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAPER = np.array([242, 238, 230], np.float32) / 255
GRAPHITE = np.array([38, 37, 42], np.float32) / 255


def xdog(gray, sigma=1.0, k=1.6, tau=0.985, eps=0.02, phi=38.0):
    g1 = ndimage.gaussian_filter(gray, sigma)
    g2 = ndimage.gaussian_filter(gray, sigma * k)
    d = g1 - tau * g2
    e = np.where(d >= eps, 1.0, 1.0 + np.tanh(phi * (d - eps)))
    return np.clip(e, 0, 1)                       # 1 = paper, 0 = line


def pencil(img, tone=0.35, sigma=1.0, seed=7):
    a = np.asarray(img.convert('RGB')).astype(np.float32) / 255
    gray = a @ np.array([0.299, 0.587, 0.114], np.float32)
    # lines at two scales (fine contour + a looser construction line)
    fine = xdog(gray, sigma=sigma)
    loose = xdog(gray, sigma=sigma * 2.2, phi=24.0)
    lines = np.minimum(fine, 0.35 + 0.65 * loose)
    # graphite tone: the darks as soft hatching (directional noise), light areas left as paper
    rng = np.random.default_rng(seed)
    h, w = gray.shape
    n = rng.random((h, w)).astype(np.float32)
    hatch = ndimage.gaussian_filter(n, (0.6, 4.0))                     # vertical strokes
    hatch = (hatch - hatch.min()) / (hatch.max() - hatch.min() + 1e-6)
    dark = np.clip((0.62 - ndimage.gaussian_filter(gray, 1.5)) / 0.62, 0, 1)
    shade = 1 - tone * dark * (0.55 + 0.45 * hatch)
    # a little paper tooth
    tooth = ndimage.gaussian_filter(rng.random((h, w)).astype(np.float32), 0.8)
    tooth = 1 - 0.05 * (tooth - 0.5)
    v = np.clip(lines * shade * tooth, 0, 1)[..., None]
    out = GRAPHITE + (PAPER - GRAPHITE) * v
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def main():
    a = sys.argv[1:]
    tone = float(a[a.index('--tone') + 1]) if '--tone' in a else 0.35
    sigma = float(a[a.index('--sigma') + 1]) if '--sigma' in a else 1.0
    if '--clip' in a:
        i = a.index('--clip')
        name, f = a[i + 1], int(a[i + 2])
        src = os.path.join(ROOT, 'assets', 'clips', name, f'{f:05d}.jpg')
        out = os.path.join(ROOT, 'assets', 'gen', f'pc_clip_{name}', f'{f}.png')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        pencil(Image.open(src), tone, sigma).save(out)
        print(out)
        return
    for spec in [x for x in a if '/' in x]:
        job, seed = spec.split('/')
        src = os.path.join(ROOT, 'assets', 'gen', job, seed + '.png')
        out = os.path.join(ROOT, 'assets', 'gen', 'pc_' + job, seed + '.png')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        pencil(Image.open(src), tone, sigma).save(out)
        print(out)


if __name__ == '__main__':
    main()
