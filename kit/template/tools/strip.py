#!/usr/bin/env python
"""strip.py -- 8 frames of a clip in a 4x2 grid (frame numbers burned in): python tools/strip.py <clip> [more clips]"""
import os
import sys
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for name in sys.argv[1:]:
    d = os.path.join(ROOT, 'assets', 'clips', name)
    fs = sorted(f for f in os.listdir(d) if f.endswith('.jpg'))
    idx = [round(i * (len(fs) - 1) / 7) for i in range(8)]
    ims = [Image.open(os.path.join(d, fs[i])).convert('RGB') for i in idx]
    w = 480; h = int(ims[0].height * w / ims[0].width)
    S = Image.new('RGB', (w * 4, h * 2)); dr = ImageDraw.Draw(S)
    for k, (i, im) in enumerate(zip(idx, ims)):
        S.paste(im.resize((w, h)), ((k % 4) * w, (k // 4) * h)); dr.text(((k % 4) * w + 6, (k // 4) * h + 4), f'{name} f{i}', fill=(255, 220, 120))
    out = os.path.join(ROOT, 'notes', 'review', f'clip_{name}.jpg'); S.save(out, quality=85); print(out)
