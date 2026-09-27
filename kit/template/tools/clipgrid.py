#!/usr/bin/env python
"""clipgrid.py -- review a clip the way that doesn't lie: four FULL-SIZE frames (0 %, 33 %, 66 %, last) in a 2x2
grid, each labelled with its time. (A 6-tile thumbnail strip once hid a train's slow departure completely.)

    python tools/clipgrid.py assets/clips_in/hero_turn.mp4 [more.mp4 ...]   -> <clip>_grid.png beside each clip"""
import json
import subprocess
import sys

from PIL import Image, ImageDraw


def frame(path, t):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1', '-f', 'image2pipe',
                          '-vcodec', 'png', '-'], capture_output=True).stdout
    from io import BytesIO
    return Image.open(BytesIO(out)).convert('RGB')


for path in sys.argv[1:]:
    info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', path],
                                     capture_output=True, text=True).stdout)
    dur = float(info['format']['duration'])
    ts = [0.0, dur * 0.33, dur * 0.66, max(0.0, dur - 0.08)]
    ims = [frame(path, t) for t in ts]
    w, h = ims[0].size
    grid = Image.new('RGB', (w * 2 + 6, h * 2 + 6), (0, 0, 0))
    d = ImageDraw.Draw(grid)
    for i, (im, t) in enumerate(zip(ims, ts)):
        x, y = (i % 2) * (w + 6), (i // 2) * (h + 6)
        grid.paste(im, (x, y))
        d.rectangle((x, y, x + 70, y + 18), fill=(0, 0, 0))
        d.text((x + 4, y + 3), f'{t:.2f}s', fill=(255, 255, 0))
    out = path[:-4] + '_grid.png'
    grid.save(out)
    print(out)
