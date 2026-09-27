#!/usr/bin/env python
"""refboard.py -- labelled zoom strips of candidate motion-reference windows, stacked into boards.

    python tools/refboard.py notes/ref/windows.json notes/ref/boards/     # one board per "group"

windows.json: [{"name": "jump_a", "group": "src1", "src": "notes/ref/src/X.mp4", "t0": 58.5, "t1": 63.0,
                "fps": 6, "crop": "W:H:X:Y" (optional, source pixels), "note": "..."}, ...]
Each window becomes one strip: a title row (name, source, times, note), then frames at `fps`, each stamped with its
SOURCE time, so a plate can be cut to the frame with tools/cutplate.py."""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

TW = 200          # thumb width
COLS = 12


def strip(w):
    info = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                           'stream=width,height', '-of', 'csv=p=0', w['src']], capture_output=True, text=True).stdout
    sw, sh = [int(v) for v in info.strip().split(',')[:2]]
    if w.get('crop'):
        cw, ch = [int(v) for v in w['crop'].split(':')[:2]]
    else:
        cw, ch = sw, sh
    th = round(ch * TW / cw)
    vf = (f"crop={w['crop']}," if w.get('crop') else '') + f"fps={w['fps']},scale={TW}:{th}"
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f"{w['t0']:.3f}", '-to', f"{w['t1']:.3f}", '-i', w['src'],
                          '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, th, TW, 3)
    n = len(fr)
    rows = max(1, (n + COLS - 1) // COLS)
    S = Image.new('RGB', (COLS * (TW + 2), 22 + rows * (th + 2)), (24, 24, 30))
    d = ImageDraw.Draw(S)
    d.text((6, 5), f"{w['name']}   {os.path.basename(w['src'])}  {w['t0']:.2f}-{w['t1']:.2f}s  "
                   f"@{w['fps']} fps   {w.get('note', '')}", fill=(255, 220, 120))
    for i, f in enumerate(fr):
        x, y = (i % COLS) * (TW + 2), 22 + (i // COLS) * (th + 2)
        S.paste(Image.fromarray(f), (x, y))
        t = w['t0'] + i / w['fps']
        d.rectangle((x, y, x + 46, y + 12), fill=(0, 0, 0))
        d.text((x + 2, y), f'{t:.2f}', fill=(255, 255, 0))
    return S


def main():
    wins = json.load(open(sys.argv[1], encoding='utf-8'))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    groups = {}
    for w in wins:
        groups.setdefault(w.get('group', 'all'), []).append(w)
    for g, ws in groups.items():
        strips = [strip(w) for w in ws]
        H = sum(s.height for s in strips) + 6 * len(strips)
        B = Image.new('RGB', (max(s.width for s in strips), H), (0, 0, 0))
        y = 0
        for s in strips:
            B.paste(s, (0, y))
            y += s.height + 6
        p = os.path.join(out, f'board_{g}.jpg')
        B.save(p, quality=90)
        print(p, B.size)


if __name__ == '__main__':
    main()
