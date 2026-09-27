#!/usr/bin/env python
"""platereel.py -- one labelled review reel of the motion-reference plates (tools/cutplate.py), each playing only its
moving part, with a quarter-second hold between plates.

    python tools/platereel.py notes/ref/plates/_plate_reel.mp4 [--list notes/ref/plates/reel.json]

reel.json lists the plates in the order to show them, each [plate name, from s, to s, label]:
    [["jump", 0.0, 2.2, "JUMP: take-off ~1.1 s (source 1:53)"], ["turn", 0.9, 2.4, "TURN: the look back"]]
Without a list: every notes/ref/plates/plate_<name>.mp4, whole, labelled with its name.
Plates live in notes/ref/plates/plate_<name>.mp4 (any plate size: each is shown at 832x480)."""
import glob
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = os.path.join(ROOT, 'notes', 'ref', 'plates')
W, H, BAR, FPS = 832, 480, 44, 24


def font(sz):
    for f in ('segoeuib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf', 'Arial Bold.ttf'):   # Pillow searches system fonts
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def reel_list(a):
    p = a[a.index('--list') + 1] if '--list' in a else os.path.join(PL, 'reel.json')
    if os.path.exists(p):
        return [tuple(x) for x in json.load(open(p, encoding='utf-8'))]
    names = sorted(os.path.basename(f)[6:-4] for f in glob.glob(os.path.join(PL, 'plate_*.mp4')))
    return [(n, 0.0, 1e6, n) for n in names]


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith('--'):
        sys.exit(__doc__)
    out = a[0]
    reel = reel_list(a)
    if not reel:
        sys.exit(f'no plates in {PL}')
    F = font(20)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s',
                            f'{W}x{H + BAR}', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-crf', '20',
                            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for k, (name, t0, t1, label) in enumerate(reel, 1):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t0:.3f}', '-to', f'{t1:.3f}', '-i',
                              os.path.join(PL, f'plate_{name}.mp4'), '-vf', f'scale={W}:{H}', '-f', 'rawvideo',
                              '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
        fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
        if not len(fr):
            print(f'  skipped {name}: no frames between {t0} and {t1} s')
            continue
        for f in list(fr) + [fr[-1]] * 6:           # a quarter-second hold between plates
            im = Image.new('RGB', (W, H + BAR), (14, 14, 18))
            im.paste(Image.fromarray(f), (0, BAR))
            ImageDraw.Draw(im).text((10, 10), f'{k:2d}. {label}', font=F, fill=(255, 225, 130))
            enc.stdin.write(im.tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)


if __name__ == '__main__':
    main()
