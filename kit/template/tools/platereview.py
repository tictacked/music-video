#!/usr/bin/env python
"""platereview.py -- one image, one row per plate: 16 evenly spaced frames each, labelled in seconds (24 fps plates).
    python tools/platereview.py out.png notes/ref/plates/plate_a.mp4 notes/ref/plates/plate_b.mp4 ..."""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

out, clips = sys.argv[1], sys.argv[2:]
tw, th, n = 150, 87, 16
S = Image.new('RGB', (n * (tw + 2) + 150, len(clips) * (th + 4)), (20, 0, 0))
d = ImageDraw.Draw(S)
for r, c in enumerate(clips):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', c, '-vf', f'scale={tw}:{th}', '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, th, tw, 3)
    idx = np.linspace(0, len(fr) - 1, n).round().astype(int)
    y = r * (th + 4)
    d.text((4, y + 30), c.replace(chr(92), '/').split('/')[-1][6:-4], fill=(255, 255, 0))
    for k, i in enumerate(idx):
        S.paste(Image.fromarray(fr[i]), (150 + k * (tw + 2), y))
        d.text((152 + k * (tw + 2), y + 1), f'{i / 24:.1f}', fill=(255, 255, 0))
S.save(out)
print(out)
