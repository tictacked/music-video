#!/usr/bin/env python
"""board.py -- review several clips at once, big enough to judge: 4 frames per clip (0, 35, 70, 100 %) at 416x240
(letterboxed: a clip keeps its own aspect), one row per clip, labelled. (Tiny thumbnail strips lie: a slow move, like
a train pulling away, looks like no move at all. Look at frames big enough to judge.)

    python tools/board.py out.png a.mp4 b.mp4 ...   [--at 0,0.35,0.7,1]"""
import json
import subprocess
import sys
from io import BytesIO

from PIL import Image, ImageDraw

args = sys.argv[1:]
at = [0, 0.35, 0.7, 1.0]
if '--at' in args:
    i = args.index('--at')
    at = [float(x) for x in args[i + 1].split(',')]
    args = args[:i] + args[i + 2:]
out, clips = args[0], args[1:]
tw, th, lab = 416, 240, 18
S = Image.new('RGB', (len(at) * (tw + 4), len(clips) * (th + lab + 6)), (10, 10, 12))
d = ImageDraw.Draw(S)
for r, c in enumerate(clips):
    dur = float(json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json',
                                           c], capture_output=True, text=True).stdout)['format']['duration'])
    y = r * (th + lab + 6)
    d.text((4, y + 2), c.replace(chr(92), '/').split('/')[-1], fill=(255, 220, 90))
    for k, f in enumerate(at):
        t = min(max(0.0, dur * f), dur - 0.06)
        png = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', c, '-frames:v', '1', '-vf',
                              f'scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2',
                              '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
        im = Image.open(BytesIO(png)).convert('RGB')
        x = k * (tw + 4)
        S.paste(im, (x, y + lab))
        d.text((x + 4, y + lab + 3), f'{t:.1f}s', fill=(255, 255, 0))
S.save(out)
print(out)
