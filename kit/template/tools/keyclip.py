#!/usr/bin/env python
"""keyclip.py -- key a clip shot on a FLAT colour (a figure walking on mint or hot pink) into alpha PNG frames.

    python tools/keyclip.py <name> [--src assets/clips/<name>] [--lo 38 --hi 78] [--spill mint|pink] [--fill auto]
      -> assets/clipa/<name>/00000.png ... (RGBA) + assets/clipa/<name>/_check.jpg (on checkers, 6 frames)

The ground is estimated PER ROW from the two border strips (a video model's flat grounds drift into soft gradients),
and each pixel's colour distance to its row's ground sets alpha: <= lo -> 0, >= hi -> 1, smooth between (hair wisps
stay soft). Then the largest blob wins (specks and the odd shadow go), holes the ground can't reach are filled, and
the edge is despilled (the ground's colour pulled out of semi-transparent pixels). Reads the clip's JPG frames
(assets/clips/<name>/). Then python tools/clipsjs.py, so the engine knows the keyed clip ('clipa:<name>/<frame>')."""
import argparse
import glob
import os

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def key(rgb, lo, hi, strip=24, spill=None, fill='auto'):
    a = rgb.astype(np.float32)
    h, w, _ = a.shape
    L, R = a[:, :strip].reshape(h, -1, 3), a[:, -strip:].reshape(h, -1, 3)
    both = np.concatenate([L, R], 1)
    ground = np.median(both, 1)                                      # per-row ground (h, 3)
    # a row whose border strips disagree (the figure touches a side): take the side nearer the frame's median ground
    gm = np.median(ground, 0)
    lm, rm = np.median(L, 1), np.median(R, 1)
    use_l = np.linalg.norm(lm - gm, axis=1) < np.linalg.norm(rm - gm, axis=1)
    ground = np.where(use_l[:, None], lm, rm)
    ground = ndimage.median_filter(ground, size=(15, 1))
    d = np.linalg.norm(a - ground[:, None, :], axis=2)
    alpha = np.clip((d - lo) / max(1.0, hi - lo), 0, 1)
    solid = alpha > 0.5
    lab, n = ndimage.label(solid)
    if n > 1:
        sizes = ndimage.sum(solid, lab, range(1, n + 1))
        keep = 1 + int(np.argmax(sizes))
        body = ndimage.binary_dilation(lab == keep, iterations=6)
        alpha = alpha * body
    if fill in (True, 'all'):   # every enclosed hole (also re-closes the ground seen between hair strands = a fringe)
        filled = ndimage.binary_fill_holes(alpha > 0.5)
        alpha = np.maximum(alpha, filled.astype(np.float32) * (alpha > 0.02))
    elif fill == 'auto':
        # fill only the enclosed holes that are NOT the ground: on a pale peach/pink ground, SKIN sits within `lo` of it
        # and keys out, punching the face and hands out of the figure. Measured on four keyed clips: skin holes have
        # median distance 37 to 46 to the row ground, real gaps (hair strands, arm/body) 4 to 20; one shadowed mint gap
        # reached 51 but kept the ground's HUE. So: fill if far from the ground AND not its hue.
        solid = alpha > 0.5
        holes = ndimage.binary_fill_holes(solid) & ~solid
        lab, n = ndimage.label(holes)
        fam = 'mint' if gm[1] > max(gm[0], gm[2]) + 10 else ('pink' if gm[0] > gm[1] and gm[2] > gm[1] else None)
        # SPEED: rough ink hatching gives a close-up ~4,000 tiny enclosed holes per frame (clean line art: 10 to 28). A
        # full-frame mask per label (`lab == i`, 2M px) just to find most were < 200 px cost 8.6 s/frame. Same
        # decisions, now: every label's size in one bincount, then only the big holes, each inside its own bounding box.
        if n:
            sizes = np.bincount(lab.ravel(), minlength=n + 1)
            objs = ndimage.find_objects(lab)
            for i in (np.nonzero(sizes[1:] >= 200)[0] + 1):
                sl = objs[i - 1]
                m = lab[sl] == i
                c = np.median(a[sl][m], 0)
                groundish = (fam == 'mint' and c[1] > max(c[0], c[2]) + 10) or (fam == 'pink' and c[0] > c[1] and c[2] > c[1])
                if float(np.median(d[sl][m])) > max(25.0, 0.66 * lo) and not groundish:
                    alpha[sl][m] = 1.0
    # the CORE: pixels well inside the figure are opaque, whatever their colour distance. Without this, shaded khaki
    # clothing sits close enough to a pink ground to get partial alpha, and the despill below then subtracts pink and
    # turns it OLIVE. Only the outer edge band stays soft.
    core = ndimage.binary_erosion(alpha > 0.3, iterations=2)
    alpha = np.where(core, 1.0, alpha)
    # despill: pull the ground colour out of partly transparent pixels, (c - (1-a) g) / a
    A = alpha[..., None]
    with np.errstate(divide='ignore', invalid='ignore'):
        un = np.where(A > 0.05, (a - (1 - A) * ground[:, None, :]) / np.maximum(A, 1e-3), a)
    un = np.clip(un, 0, 255)
    if spill:
        # the ground's colour survives on hair tips as a thin fringe: neutralise it in the EDGE BAND (partly transparent,
        # or within 3 px of transparency). Check the figure's own colours against these rules first:
        # mint: clamp green to max(r, b) (safe for a figure with no green-dominant colour: brown hair, skin, white, navy).
        # pink: magenta pixels (r > g and b > g) are pulled toward grey (khaki, skin and brown hair have b < g; light
        # blue has r < g: all safe).
        band = np.ones_like(alpha, bool) if spill == 'mint' else ((alpha < 0.98) | ndimage.binary_dilation(alpha < 0.5, iterations=3))
        r, g, b = un[..., 0], un[..., 1], un[..., 2]
        if spill == 'mint':
            g2 = np.minimum(g, np.maximum(r, b))
            un[..., 1] = np.where(band, g2, g)
        elif spill == 'pink':
            mag = (r > g) & (b > g) & band
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            for c in range(3):
                un[..., c] = np.where(mag, un[..., c] * 0.2 + lum * 0.8, un[..., c])
    out = np.dstack([un, alpha * 255]).astype(np.uint8)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--src')
    ap.add_argument('--lo', type=float, default=38)
    ap.add_argument('--hi', type=float, default=78)
    ap.add_argument('--spill', choices=['mint', 'pink'], help='neutralise the ground colour fringing the edges')
    ap.add_argument('--fill', choices=['off', 'all', 'auto'], default='auto',
                    help='enclosed holes: auto = fill only holes that are not the ground (skin on a peach/pink ground), '
                         'all = every hole (hair gaps become fringes), off = none')
    a = ap.parse_args()
    src = a.src or os.path.join(ROOT, 'assets', 'clips', a.name)
    dst = os.path.join(ROOT, 'assets', 'clipa', a.name)
    os.makedirs(dst, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src, '*.jpg')))
    assert files, 'no frames in ' + src
    checks = []
    for i, f in enumerate(files):
        rgb = np.asarray(Image.open(f).convert('RGB'))
        out = key(rgb, a.lo, a.hi, spill=a.spill, fill=a.fill)
        Image.fromarray(out, 'RGBA').save(os.path.join(dst, os.path.basename(f)[:-4] + '.png'), optimize=False, compress_level=3)
        if i in {0, len(files) // 5, 2 * len(files) // 5, 3 * len(files) // 5, 4 * len(files) // 5, len(files) - 1}:
            checks.append(out)
    # the check sheet: frames on a checkerboard
    tw = 480
    sheet = []
    for o in checks:
        h, w = o.shape[:2]
        th = int(h * tw / w)
        im = Image.fromarray(o, 'RGBA').resize((tw, th))
        yy, xx = np.mgrid[0:th, 0:tw]
        cb = np.where(((yy // 16) + (xx // 16)) % 2 == 0, 90, 150).astype(np.uint8)
        bg = Image.fromarray(np.dstack([cb, cb, cb]), 'RGB')
        bg.paste(im, (0, 0), im)
        sheet.append(bg)
    S = Image.new('RGB', (tw * 3, sheet[0].height * 2))
    for k, im in enumerate(sheet):
        S.paste(im, ((k % 3) * tw, (k // 3) * im.height))
    S.save(os.path.join(dst, '_check.jpg'), quality=85)
    print(f'{a.name}: {len(files)} frames keyed -> {dst} (check: _check.jpg)')


if __name__ == '__main__':
    main()
