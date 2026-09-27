#!/usr/bin/env python
"""keystill.py -- key ONE still picture on flat colour into a cut-out, with the same matte as the keyed clips
(tools/keyclip.py's key()): so a clip's first-frame picture can stand in for the keyed clip, pixel-compatible.

    python tools/keystill.py hero_walk/9420 rival_walk/9432   -> assets/cut/<job>/<seed>.png (+ .meta.json, manifest rebuilt)

The .meta.json marks the cut-out as done, so tools/cutout.py leaves it alone (without --force)."""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from cutout import build_manifest, describe  # noqa: E402
from keyclip import key  # noqa: E402

for arg in sys.argv[1:]:
    job, seed = arg.split('/')
    src = os.path.join(ROOT, 'assets', 'gen', job, f'{seed}.png')
    rgb = np.asarray(Image.open(src).convert('RGB'))
    out = key(rgb, 38, 78)
    d = os.path.join(ROOT, 'assets', 'cut', job)
    os.makedirs(d, exist_ok=True)
    Image.fromarray(out, 'RGBA').save(os.path.join(d, f'{seed}.png'))
    json.dump(describe(out), open(os.path.join(d, f'{seed}.meta.json'), 'w'))
    a = out[:, :, 3] > 127
    ys, xs = np.where(a)
    print(f'{arg}: keyed, figure bbox {[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}')
if sys.argv[1:]:
    print(len(build_manifest()), 'manifest entries')
