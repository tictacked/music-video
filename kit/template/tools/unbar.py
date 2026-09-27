#!/usr/bin/env python
"""unbar.py -- find generated pictures with black PILLARBOX / LETTERBOX bars ("anime screencap" draws 4:3 broadcast frames
inside 16:9) and move them out of assets/gen (to notes/work/_barred/), so the next gen.py run re-rolls those seeds with the
anti-bar negative.   python tools/unbar.py [--dry]"""
import glob
import os
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'notes' / 'work' / '_barred'
OUT.mkdir(parents=True, exist_ok=True)
dry = '--dry' in sys.argv
bad = []
for p in sorted((ROOT / 'assets' / 'gen').glob('*/*.png')):
    job = p.parent.name
    if job.startswith('sweep') or p.name.startswith('_'):
        continue
    a = np.asarray(Image.open(p).convert('L')).astype(np.float32)
    h, w = a.shape
    k = max(8, w // 40)
    edges = [a[:, :k], a[:, -k:], a[:k, :], a[-k:, :]]
    if any(e.mean() < 14 and e.std() < 6 for e in edges):
        bad.append(p)
for p in bad:
    print('barred:', p.parent.name + '/' + p.name)
    if not dry:
        shutil.move(str(p), str(OUT / f'{p.parent.name}_{p.name}'))
        j = p.with_suffix('.json')
        if j.exists():
            j.unlink()
print(len(bad), 'barred' + (' (dry run)' if dry else ', moved out: the next gen.py run re-rolls them'))
