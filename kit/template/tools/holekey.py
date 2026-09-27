#!/usr/bin/env python
"""holekey.py -- key out the flat background that rembg leaves INSIDE a figure (gaps between twintails and the face,
between an arm and the body). When every character is generated on a flat pastel ground (one colour each: pink, blue,
mint...), the ground's colour is known per row from the picture's own left/right border columns. Pixels inside the
matte that match the local ground (RGB distance < TOL), in connected blobs of at least MIN_AREA px, with low colour
variance (a flat ground, not an eye with highlights), get alpha 0 (feathered by 1 px). Eyes survive: an iris is a
deeper, outlined colour, far from the pastel ground.

    python tools/holekey.py assets/gen/hero_stand/6011.png assets/cut/hero_stand/6011.png [--flip] [--debug out.png]
      (prints how many pixels holekey() would key in that cut-out; --debug paints them magenta on the source picture)

keycut() below is the matte tools/cutout.py uses for film.json "keycut" jobs (no rembg at all).
"""
import sys

import numpy as np

TOL = 26.0        # RGB distance to the local ground
MIN_AREA = 60     # px: smaller blobs are left alone (anti-aliasing, eye whites)
MAX_STD = 9.0     # a ground blob is flat
MED_MAX = 11.0    # ...and IS the ground: its MEDIAN distance to the ground model is tiny (real gaps measure 1.7-7.1).
                  # Near-ground colours are not ground: a peach face (median 18.0 on pink) and a light-blue iris
                  # (20.4 on blue) were keyed out by TOL alone


def _smooth_fit(col):
    """col: (h, 3) border colours per row. The ground is a smooth gradient, but a figure crossing the border (an arm,
    a hand) contaminates some rows: fit a quadratic in y per channel, reject rows far from it, refit (3 rounds), and
    return the fit wherever a row was rejected (a pointing arm was keyed away before this)."""
    h = col.shape[0]
    y = np.linspace(-1, 1, h)
    good = np.ones(h, bool)
    fit = col.copy()
    for _ in range(3):
        if good.sum() < 8:
            break
        fit = np.stack([np.polyval(np.polyfit(y[good], col[good, c], 2), y) for c in range(3)], axis=1)
        err = np.sqrt(((col - fit) ** 2).sum(axis=1))
        good = err < 14
    return np.where(good[:, None], col, fit)


def ground_model(rgb):
    """per-row ground colour at the left and right borders (median of the outer 6 columns, contaminated rows replaced
    by a smooth fit), as float arrays (h, 3)"""
    left = np.median(rgb[:, :6, :].astype(np.float32), axis=1)
    right = np.median(rgb[:, -6:, :].astype(np.float32), axis=1)
    return _smooth_fit(left), _smooth_fit(right)


def holekey(src_rgb, arr, return_mask=False):
    """src_rgb: (h, w, 3) uint8 original (already flipped if the cut was flipped); arr: (h, w, 4) uint8 cut-out,
    modified in place. Returns the number of pixels keyed (and the mask if asked)."""
    from scipy import ndimage
    h, w = arr.shape[:2]
    L, R = ground_model(src_rgb)
    xs = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    ground = L[:, None, :] * (1 - xs) + R[:, None, :] * xs              # (h, w, 3) interpolated across the row
    rgb = arr[:, :, :3].astype(np.float32)
    dist = np.sqrt(((rgb - ground) ** 2).sum(axis=2))
    inside = arr[:, :, 3] > 127
    cand = inside & (dist < TOL)
    lab, n = ndimage.label(cand)
    if n == 0:
        return (0, cand) if return_mask else 0
    idx = np.arange(1, n + 1)
    area = ndimage.sum(np.ones_like(dist), lab, idx)
    # a blob touching the picture's edge is the FIGURE crossing the frame (the outer ground is already alpha 0)
    edge_lab = set(np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]]))) - {0}
    keep = np.zeros(n + 1, bool)
    for i, a in zip(idx, area):
        if a < MIN_AREA or i in edge_lab:
            continue
        m = lab == i
        if rgb[m].std(axis=0).max() > MAX_STD or float(np.median(dist[m])) > MED_MAX:
            continue
        keep[i] = True
    mask = keep[lab]
    if not mask.any():
        return (0, mask) if return_mask else 0
    grown = ndimage.binary_dilation(mask, iterations=1)
    a = arr[:, :, 3].astype(np.float32)
    a[mask] = 0
    edge = grown & ~mask
    a[edge] *= 0.5
    arr[:, :, 3] = a.astype(np.uint8)
    return (int(mask.sum()), mask) if return_mask else int(mask.sum())


def keycut(src_rgb, tol=30.0):
    """A matte from the flat ground ALONE (no rembg): for props rembg misreads (a red book on pink was matted away and
    only the small gold figurine on it survived). Pixels farther than `tol` from the local ground -> the largest blob ->
    holes filled -> a 1 px feather. Returns an (h, w, 4) uint8 RGBA array."""
    from scipy import ndimage
    h, w = src_rgb.shape[:2]
    L, R = ground_model(src_rgb)
    xs = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    ground = L[:, None, :] * (1 - xs) + R[:, None, :] * xs
    dist = np.sqrt(((src_rgb.astype(np.float32) - ground) ** 2).sum(axis=2))
    fg = dist > tol
    lab, n = ndimage.label(fg)
    if n:
        sizes = ndimage.sum(np.ones_like(dist), lab, range(1, n + 1))
        fg = lab == (1 + int(np.argmax(sizes)))
    fg = ndimage.binary_fill_holes(fg)
    fg = ndimage.binary_opening(fg, iterations=1)
    a = ndimage.gaussian_filter(fg.astype(np.float32), 0.8)
    out = np.dstack([src_rgb, (np.clip(a, 0, 1) * 255).astype(np.uint8)])
    return out


if __name__ == '__main__':
    from PIL import Image
    src, cut = sys.argv[1], sys.argv[2]
    im = Image.open(src).convert('RGB')
    if '--flip' in sys.argv:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    arr = np.array(Image.open(cut).convert('RGBA'))
    n, mask = holekey(np.array(im), arr, return_mask=True)
    print(n, 'px keyed')
    if '--debug' in sys.argv:
        out = sys.argv[sys.argv.index('--debug') + 1]
        dbg = np.array(im).copy()
        dbg[mask] = [255, 0, 255]
        Image.fromarray(dbg).save(out)
