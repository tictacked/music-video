#!/usr/bin/env python
"""cutout.py -- cut every generated picture out of its flat background, and describe it for the engine.

    <PY> tools/cutout.py                          # all new pictures in assets/gen -> assets/cut
    <PY> tools/cutout.py --only hero_full,rival_full   [--force]
    <PY> tools/cutout.py --manifest               # just rebuild assets/manifest.js
    (PY = the kit's python: `python tools/film.py PY` prints its path)

Matte: rembg `isnet-anime` (made for anime figures; ~0.9 s/picture on CPU) + a clean-up that keeps the largest
figure blobs and drops floor shadows / specks. Then the flat MINT ground left in hair gaps is keyed (demint), and
tools/retouch.py applies any per-picture fix.
A picture that already has REAL transparency (some generators can output a transparent background: an alpha channel
with more than 1% of its pixels under alpha 16) is its own cut-out: its alpha is used as it is, and rembg is skipped.
WHAT IS NEVER CUT comes from film.json, the one list (three copies of it in three files once drifted apart): jobs
starting with one of `nocutPrefixes` (plates pl_, clip first frames ff_, img2img tests i2i_, sweeps, tests), and every
job in `whole` (scene pictures painted on their own ground). `keycut` jobs get a matte from the flat ground alone
instead of rembg (tools/holekey.py): for big-headed chibis that rembg mattes away, and for thin or splashy things it
cuts out (red blades, spray).

Manifest (assets/manifest.js -> window.DT_ASSETS, keyed 'job/seed'):
  w, h           PNG size
  bbox           [x0,y0,x1,y1] of the visible figure (alpha > 0.5)
  eyes           null from this tool. A scene that needs eye points (glows, tears) writes [[x,y],[x,y]] into the
                 picture's assets/cut/<job>/<seed>.meta.json by hand (K.eyes reads them; --force rewrites the file)
  cut            true if a cut-out exists (assets/cut/<id>.png), else the raw gen is the asset
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GEN = os.path.join(ROOT, 'assets', 'gen')
CUT = os.path.join(ROOT, 'assets', 'cut')
sys.path.insert(0, HERE)
from film import FILM  # noqa: E402

WHOLE = set(FILM.get('whole', []))                                   # used whole, never cut (film.json)
NOCUT = lambda aid: aid.startswith(tuple(FILM.get('nocutPrefixes', ['pl_', 'ff_', 'i2i_', 'sweep', 'test']))) or aid in WHOLE
KEYCUT = set(FILM.get('keycut', []))                                 # matte from the flat ground (holekey), not rembg

_session = None


def session():
    global _session
    if _session is None:
        from rembg import new_session
        _session = new_session('isnet-anime')
    return _session


def own_alpha(im):
    """the picture as RGBA if it has REAL transparency (> 1% of its pixels under alpha 16), else None"""
    if im.mode not in ('RGBA', 'LA', 'PA', 'RGBa', 'La') and not (im.mode == 'P' and 'transparency' in im.info):
        return None
    arr = np.array(im.convert('RGBA'))
    return arr if float((arr[:, :, 3] < 16).mean()) > 0.01 else None


def cut(src, dst, key=False):
    from scipy import ndimage
    src_im = Image.open(src)
    arr = own_alpha(src_im)
    if arr is not None:                          # the generator's own transparency IS the matte: no rembg, no keying
        from retouch import retouch
        key_ = f'{os.path.basename(os.path.dirname(dst))}/{os.path.basename(dst)[:-4]}'
        print(f'  {key_}: has its own transparency, used as the matte (rembg skipped)', flush=True)
        retouch(key_, arr)
        Image.fromarray(arr).save(dst, optimize=False, compress_level=3)
        return arr
    im = src_im.convert('RGB')
    rgb = np.array(im).astype(np.float32)
    sys.path.insert(0, HERE)
    if key:                                      # KEYCUT: a matte from the flat ground alone (no rembg)
        from holekey import keycut, ground_model
        arr = keycut(np.array(im))
        a = arr[:, :, 3].astype(np.float32) / 255
        L, R = ground_model(np.array(im))        # the per-row ground (it can be a gradient), for the defringe below
        xs = np.linspace(0, 1, rgb.shape[1], dtype=np.float32)[None, :, None]
        Bg = L[:, None, :] * (1 - xs) + R[:, None, :] * xs
    else:
        from rembg import remove
        out = remove(im, session=session(), post_process_mask=True)
        a = np.array(out)[:, :, 3].astype(np.float32) / 255
        # keep the big figure blobs; drop detached specks and floor shadows (< 1.5% of the figure)
        lab, n = ndimage.label(a > 0.5)
        if n > 1:
            sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
            keep = np.zeros(n + 1, bool)
            big = sizes.max()
            for i, s in enumerate(sizes, 1):
                keep[i] = s >= 0.015 * big
            mask = keep[lab]
            # soft edges survive: zero alpha only where a whole dropped blob was
            grown = ndimage.binary_dilation(mask, iterations=3)
            a = np.where(grown, a, 0)
        arr = np.array(out)
        arr[:, :, 3] = (a * 255).astype(np.uint8)
        corners = np.concatenate([rgb[:24, :24].reshape(-1, 3), rgb[:24, -24:].reshape(-1, 3), rgb[-24:, :24].reshape(-1, 3), rgb[-24:, -24:].reshape(-1, 3)])
        Bg = np.median(corners, axis=0)[None, None, :]
    # DEFRINGE: soft edges keep the flat ground's colour mixed in (C = aF + (1-a)B), which reads as a coloured rim light
    # over a dark background. The ground is flat, so solve for the foreground: F = (C - (1-a)B) / a.
    soft = (a > 0.02) & (a < 0.985)
    F = (rgb - (1 - a)[..., None] * Bg) / np.maximum(a, 0.08)[..., None]
    arr[:, :, :3][soft] = np.clip(F[soft], 0, 255).astype(np.uint8)
    demint(arr)                                  # the figures stand on flat MINT: key the mint left in hair gaps
    from retouch import retouch                  # per-picture fixes baked into the cut
    retouch(f'{os.path.basename(os.path.dirname(dst))}/{os.path.basename(dst)[:-4]}', arr)
    Image.fromarray(arr).save(dst, optimize=False, compress_level=3)
    return arr


def demint(arr):
    """the flat mint ground left inside hair gaps / along edges -> transparent. Mint is green-dominant with blue above
    red (#9fe6c8-ish); skin (r > g > b), amber eyes, white clothes and navy (b > g) are safe."""
    rgb = arr[:, :, :3].astype(np.float32)
    e = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
    # a saturated GREEN garment (~(0,166,128)) is green-dominant with b > r too, and keyed out 20 to 29% transparent.
    # The mint ground is BRIGHT (mean ~212) and such a garment is not (~98): gate on brightness.
    bright = np.clip((rgb.mean(axis=2) - 150) / 30, 0, 1)
    k = np.clip((e - 12) / 30, 0, 1) * ((rgb[..., 2] - rgb[..., 0]) > 10) * (arr[:, :, 3] > 0) * bright
    arr[:, :, 3] = (arr[:, :, 3].astype(np.float32) * (1 - k)).round().astype(np.uint8)
    return int((k > 0.02).sum())


def describe(arr):
    h, w = arr.shape[:2]
    a = arr[:, :, 3] > 127
    ys, xs = np.where(a)
    if len(xs) == 0:
        return {'w': w, 'h': h, 'bbox': [0, 0, w, h], 'eyes': None}
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    return {'w': w, 'h': h, 'bbox': bbox, 'eyes': None}


def build_manifest():
    man = {}
    for aid in sorted(os.listdir(GEN)):
        d = os.path.join(GEN, aid)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.png') or f.startswith('_'):
                continue
            key = f'{aid}/{f[:-4]}'
            meta_p = os.path.join(CUT, aid, f[:-4] + '.meta.json')
            if os.path.exists(meta_p):
                m = json.load(open(meta_p))
                m['cut'] = True
            else:
                im = Image.open(os.path.join(d, f))
                m = {'w': im.width, 'h': im.height, 'bbox': [0, 0, im.width, im.height], 'eyes': None, 'cut': False}
            man[key] = m
    js = '// generated by tools/cutout.py -- do not edit\nwindow.DT_ASSETS = ' + json.dumps(man, separators=(',', ':')) + ';\n'
    dst = os.path.join(ROOT, 'assets', 'manifest.js')
    tmp = dst + f'.{os.getpid()}.tmp'          # atomic: several painters may run this at once
    open(tmp, 'w', encoding='utf-8').write(js)
    for _ in range(20):
        try:
            os.replace(tmp, dst)
            break
        except PermissionError:                  # Windows: a reader has it open for a moment
            import time
            time.sleep(0.2)
    return man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only'); ap.add_argument('--force', action='store_true'); ap.add_argument('--manifest', action='store_true')
    a = ap.parse_args()
    if a.manifest:
        m = build_manifest(); print(len(m), 'entries'); return
    only = set(a.only.split(',')) if a.only else None
    done = 0
    for aid in sorted(os.listdir(GEN)):
        d = os.path.join(GEN, aid)
        if not os.path.isdir(d) or NOCUT(aid) or (only and aid not in only):
            continue
        os.makedirs(os.path.join(CUT, aid), exist_ok=True)
        for f in sorted(os.listdir(d)):
            if not f.endswith('.png') or f.startswith('_'):
                continue
            dst = os.path.join(CUT, aid, f)
            meta_p = dst[:-4] + '.meta.json'
            if os.path.exists(dst) and os.path.exists(meta_p) and not a.force:
                continue
            arr = cut(os.path.join(d, f), dst, key=aid in KEYCUT)
            m = describe(arr)
            json.dump(m, open(meta_p, 'w'))
            done += 1
            print(f'  cut {aid}/{f}  bbox {m["bbox"]}', flush=True)
    man = build_manifest()
    print(f'{done} new cut-outs; manifest has {len(man)} entries')


if __name__ == '__main__':
    main()
