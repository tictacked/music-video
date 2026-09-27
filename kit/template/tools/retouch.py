#!/usr/bin/env python
"""retouch.py -- per-picture fixes baked into the cut-out (tools/cutout.py calls retouch() after the matte), so every
reel that draws the picture gets the fix and nobody duplicates it in a scene file. The film owns this file.

RETOUCH maps 'job/seed' -> a function(arr) that edits the (h, w, 4) uint8 RGBA cut-out in place. Coordinates are the
CUT-OUT's pixels. After adding one: `python tools/cutout.py --only <job> --force`.
The kind of thing that goes here: a neck repainted with skin sampled right beside it, a ground sliver the matte kept
keyed out, a stray shine covered, stitches drawn on.
"""
import numpy as np


def poly_mask(h, w, pts):
    """a boolean (h, w) mask of a polygon given as [[x, y], ...]"""
    from PIL import Image, ImageDraw
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in pts], fill=255)
    return np.array(m) > 127


def fill(arr, pts, rgb):
    """paint a polygon with one colour (sample it from the picture right beside the flaw)"""
    m = poly_mask(arr.shape[0], arr.shape[1], pts)
    arr[m, 0], arr[m, 1], arr[m, 2] = rgb


def clear(arr, pts):
    """make a polygon transparent (a ground sliver the matte kept)"""
    arr[poly_mask(arr.shape[0], arr.shape[1], pts), 3] = 0


RETOUCH = {
    # 'hero_face/2': lambda arr: fill(arr, [[822, 454], [887, 454], [887, 481], [826, 494]], (0xfe, 0xb9, 0x7d)),
}


def retouch(key, arr):
    fn = RETOUCH.get(key)
    if fn:
        fn(arr)
        return True
    return False
