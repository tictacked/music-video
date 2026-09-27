#!/usr/bin/env python
"""motion.py -- how SNAPPY is a move? Per-frame motion curves for clips, drawn on one chart.

    python tools/motion.py out.png a.mp4 [b.mp4 ...]

For each clip: mean absolute frame difference (grey, 1/8 scale, noise floor removed) per frame at 24 fps, and the
SNAP = the shortest run of frames that holds half of the clip's motion. A TV-anime head-tilt snap: ~3-6 frames. An
image-to-video model's slow tilt: 30+ (tools/snap.py retimes one into the other)."""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw


def curve(path):
    info = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                           '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip().split(',')
    W, H = int(info[0]), int(info[1])
    w, h = W // 8, H // 8
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'fps=24,scale={w}:{h},format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    return np.maximum(d - np.percentile(d, 20), 0)


def snap(d, share=0.5):
    tot = d.sum()
    if tot <= 0:
        return 0, 0, 0
    c = np.concatenate([[0], np.cumsum(d)])
    best = (len(d), 0, len(d))
    for i in range(len(d)):
        j = int(np.searchsorted(c, c[i] + share * tot))
        if j <= len(d) and j - i < best[0]:
            best = (j - i, i, j)
    return best


out, clips = sys.argv[1], sys.argv[2:]
curves = [curve(c) for c in clips]
Wc, Hc, pad = 1200, 180, 30
img = Image.new('RGB', (Wc, (Hc + pad) * len(clips) + pad), (16, 16, 20))
dr = ImageDraw.Draw(img)
n = max(len(c) for c in curves)
for k, (path, d) in enumerate(zip(clips, curves)):
    y0 = pad + k * (Hc + pad)
    L, i, j = snap(d)
    m = d.max() or 1
    xs = lambda f: 40 + (Wc - 60) * f / max(1, n - 1)
    dr.rectangle((xs(i), y0, xs(j), y0 + Hc), fill=(60, 20, 24))
    pts = [(xs(f), y0 + Hc - Hc * v / m) for f, v in enumerate(d)]
    dr.line(pts, fill=(240, 200, 60), width=2)
    for s in range(0, n, 24):
        dr.line((xs(s), y0 + Hc, xs(s), y0 + Hc + 4), fill=(150, 150, 150))
        dr.text((xs(s) + 2, y0 + Hc + 4), f'{s // 24}s', fill=(150, 150, 150))
    name = path.replace('\\', '/').split('/')[-1]
    dr.text((44, y0 + 2), f'{name}: half the motion in {L} frames ({L / 24:.2f}s) at {i / 24:.2f}-{j / 24:.2f}s',
            fill=(255, 255, 255))
    print(f'{name}: snap {L} frames ({L / 24:.2f}s) at {i / 24:.2f}-{j / 24:.2f}s')
img.save(out)
print(out)
