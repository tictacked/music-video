#!/usr/bin/env python
"""contact.py -- a labelled contact sheet of a clip, for hunting moments (a head tilt, a jump, a glance) in a source.

    python tools/contact.py clip.mp4 [--fps 2] [--start 0] [--end 999] [--w 256] [--cols 10] [--out sheet.png]

Also prints the hard cuts (mean abs frame difference spikes) so a moment can be cut between them."""
import argparse
import json
import subprocess

import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('clip')
ap.add_argument('--fps', type=float, default=2.0)
ap.add_argument('--start', type=float, default=0.0)
ap.add_argument('--end', type=float, default=1e9)
ap.add_argument('--w', type=int, default=256)
ap.add_argument('--cols', type=int, default=10)
ap.add_argument('--out')
a = ap.parse_args()

info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                  'stream=width,height,r_frame_rate:format=duration', '-of', 'json', a.clip],
                                 capture_output=True, text=True).stdout)
st = info['streams'][0]
W, H = st['width'], st['height']
num, den = st['r_frame_rate'].split('/')
src_fps = float(num) / float(den)
dur = float(info['format']['duration'])
end = min(a.end, dur)
w = a.w
h = round(H * w / W)

# every frame at a small size (for cut detection) -- 64 px wide greyscale
sw, sh = 64, max(2, round(H * 64 / W))
raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a.start:.3f}', '-to', f'{end:.3f}', '-i', a.clip,
                      '-vf', f'scale={sw}:{sh},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, sh, sw).astype(np.float32)
d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
med = np.median(d) + 1e-3
cuts = [a.start + (i + 1) / src_fps for i in np.where(d > max(18.0, 6 * med))[0]]
print(f'{a.clip}: {W}x{H} @ {src_fps:.3f} fps, {dur:.2f}s; cuts:', ' '.join(f'{c:.2f}' for c in cuts))

# the sheet
raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a.start:.3f}', '-to', f'{end:.3f}', '-i', a.clip,
                      '-vf', f'fps={a.fps},scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                     capture_output=True).stdout
ims = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
n = len(ims)
cols = min(a.cols, n)
rows = (n + cols - 1) // cols
sheet = Image.new('RGB', (cols * (w + 2), rows * (h + 2)), (40, 0, 0))
dr = ImageDraw.Draw(sheet)
for i, im in enumerate(ims):
    x, y = (i % cols) * (w + 2), (i // cols) * (h + 2)
    sheet.paste(Image.fromarray(im), (x, y))
    t = a.start + i / a.fps
    dr.rectangle((x, y, x + 44, y + 13), fill=(0, 0, 0))
    dr.text((x + 2, y + 1), f'{t:.1f}', fill=(255, 255, 0))
out = a.out or a.clip.rsplit('.', 1)[0] + '_sheet.png'
sheet.save(out)
print(out, f'{n} frames')
