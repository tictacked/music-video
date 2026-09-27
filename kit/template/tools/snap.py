#!/usr/bin/env python
"""snap.py -- retime a video model's slow head tilt into an anime SNAP.

Measured on real TV-anime cuts: the head moves in 6-10 frames (0.25-0.4 s) with a hard ease-OUT (most of the travel in
the first frames), then HOLDS while only hair/cloth settle. An image-to-video model draws the same tilt over 3-4 s.
So: measure the clip's motion progress (cumulative frame difference), then resample it on the anime curve.

    python tools/snap.py in.mp4 out.mp4 [--hold-in 14] [--snap 7] [--hold-out 30] [--tail] [--power 3]

  --hold-in   frames of the first pose before the snap
  --snap      frames the tilt takes (7 = 0.29 s at 24 fps)
  --hold-out  frames after the snap: a freeze of the end pose, or with --tail the clip's own remaining frames
              (the hair/cloth settle) at real speed, then a freeze
  --power     ease-out strength: progress = 1-(1-u)^power
The source is read at --fps (default 24), whatever rate the model made it at."""
import argparse
import json
import subprocess

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('src')
ap.add_argument('out')
ap.add_argument('--hold-in', type=int, default=14)
ap.add_argument('--snap', type=int, default=7)
ap.add_argument('--hold-out', type=int, default=30)
ap.add_argument('--tail', action='store_true')
ap.add_argument('--power', type=float, default=3.0)
ap.add_argument('--twos', action='store_true', help='animate the snap on twos (each drawing held 2 frames)')
ap.add_argument('--lo', type=float, default=0.03, help='progress where the move is said to start')
ap.add_argument('--hi', type=float, default=0.97, help='progress where the move is said to end')
ap.add_argument('--fps', type=int, default=24)
a = ap.parse_args()

info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                  'stream=width,height', '-of', 'json', a.src], capture_output=True, text=True).stdout)
W, H = info['streams'][0]['width'], info['streams'][0]['height']
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.src, '-vf', f'fps={a.fps}', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                      '-'], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
n = len(fr)

# progress = cumulative motion, measured small and grey so grain doesn't count as motion
small = fr[:, ::8, ::8].mean(axis=3)
d = np.abs(np.diff(small, axis=0)).mean(axis=(1, 2))
d = np.maximum(d - np.percentile(d, 20), 0)          # subtract the noise floor (boil, compression shimmer)
p = np.concatenate([[0.0], np.cumsum(d)])
p /= p[-1] if p[-1] > 0 else 1.0
i0 = int(np.searchsorted(p, a.lo))
i1 = int(np.searchsorted(p, a.hi))
print(f'{a.src}: {n} frames; move runs {i0}->{i1} ({i0 / 24:.2f}s -> {i1 / 24:.2f}s, {(i1 - i0) / 24:.2f}s)')

seq = [i0] * a.hold_in
for k in range(1, a.snap + 1):
    # --twos: hold each drawing two frames, as real anime snaps do (tools/motion.py: their curves spike every other
    # frame). Without it every frame is a new drawing and the first one carries a third of the move: reads as a cut.
    u = (min(a.snap, 2 * ((k + 1) // 2)) if a.twos else k) / a.snap
    q = 1 - (1 - u) ** a.power
    target = p[i0] + (p[i1] - p[i0]) * q
    seq.append(int(np.argmin(np.abs(p - target))))
if a.tail:
    rest = list(range(i1 + 1, n))[:a.hold_out]
    seq += rest + [seq[-1] if not rest else rest[-1]] * (a.hold_out - len(rest))
else:
    seq += [i1] * a.hold_out
print('frames:', seq[a.hold_in - 1:a.hold_in + a.snap + 1])

enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                        '-r', str(a.fps), '-i', '-', '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', a.out],
                       stdin=subprocess.PIPE)
for i in seq:
    enc.stdin.write(fr[i].tobytes())
enc.stdin.close()
enc.wait()
print(a.out, f'{len(seq)} frames = {len(seq) / a.fps:.2f}s')
