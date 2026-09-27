#!/usr/bin/env python
"""cutplate.py -- cut a motion-reference plate, for a video model that follows a reference video: EXACTLY N frames,
24 fps, one size, no audio. The defaults (124 frames = 5.17 s, 1280x720) suit a 5-second 16:9 video model: set --frames
and --size to your model's (the reference's aspect must match the clip's).

    python tools/cutplate.py NAME SRC START END [--crop W:H:X:Y] [--freeze-in S] [--frames 124] [--size 1280x720]

The source window [START, END] is resampled to 24 fps, cropped (default: the largest centred box of the plate's
aspect), scaled to the plate size. --freeze-in holds the window's first frame for S seconds before it plays (sets WHEN
the key motion lands); whatever is left of the frames holds the window's last frame. If the window is too long it is
trimmed at the end. Writes notes/ref/plates/plate_NAME.mp4 and its 6 fps contact sheet plate_NAME_sheet.png."""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'notes', 'ref', 'plates')
W, H, FPS = 1280, 720, 24         # a bigger canvas costs more time per clip, but lines and faces hold

ap = argparse.ArgumentParser()
ap.add_argument('name')
ap.add_argument('src')
ap.add_argument('start', type=float)
ap.add_argument('end', type=float)
ap.add_argument('--crop', help='W:H:X:Y in source pixels (before scaling)')
ap.add_argument('--freeze-in', type=float, default=0.0)
ap.add_argument('--frames', type=int, default=124)
ap.add_argument('--vf-pre', help='ffmpeg filters applied in SOURCE pixels before the crop (e.g. delogo=x=..:y=..:w=..:h=..)')
ap.add_argument('--size', default='1280x720', help="plate size = the video model's canvas (16:9 by default)")
a = ap.parse_args()
W, H = [int(v) for v in a.size.lower().split('x')]

info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                  'stream=width,height', '-of', 'json', a.src], capture_output=True, text=True).stdout)
sw, sh = info['streams'][0]['width'], info['streams'][0]['height']
if a.crop:
    crop = a.crop
else:
    aspect = W / H
    if sw / sh > aspect:
        cw, ch = round(sh * aspect), sh
    else:
        cw, ch = sw, round(sw / aspect)
    crop = f'{cw}:{ch}:{(sw - cw) // 2}:{(sh - ch) // 2}'
vf = f'fps={FPS},{a.vf_pre + "," if a.vf_pre else ""}crop={crop},scale={W}:{H}:flags=lanczos,format=rgb24'
raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a.start:.3f}', '-to', f'{a.end:.3f}', '-i', a.src, '-an',
                      '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
if len(fr) == 0:
    sys.exit('no frames decoded')
nin = round(a.freeze_in * FPS)
seq = [fr[0]] * nin + list(fr)
seq = seq[:a.frames]
seq += [seq[-1]] * (a.frames - len(seq))
os.makedirs(OUT, exist_ok=True)
out = os.path.join(OUT, f'plate_{a.name}.mp4')
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                        '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', out],
                       stdin=subprocess.PIPE)
for f in seq:
    enc.stdin.write(f.tobytes())
enc.stdin.close()
enc.wait()
n = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                    'stream=nb_read_frames,r_frame_rate,width,height', '-of', 'csv=p=0', out],
                   capture_output=True, text=True).stdout.strip()
print(f'{out}: {n}  (window {len(fr)} frames, freeze-in {nin}, hold-out {a.frames - min(a.frames, nin + len(fr))})')
subprocess.run([sys.executable, os.path.join(HERE, 'contact.py'), out, '--fps', '6', '--w', '260', '--cols', '8',
                '--out', os.path.join(OUT, f'plate_{a.name}_sheet.png')], capture_output=True)
