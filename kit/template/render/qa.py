#!/usr/bin/env python3
"""
qa.py -- temporal QA for a rendered video: what a Claude can't see in stills.

    <PY> render/qa.py out/preview.mp4 [--from 0]      (--from = song time of the file's first frame)
    (PY = the kit's python: `python tools/film.py PY` prints its path)

Decodes the video at 160x90 greyscale and measures, per frame:
  lum   mean brightness (0..255)
  diff  mean absolute change from the previous frame (motion + boil + cuts)
Flags:
  BLANK   near-black frames outside the places the film is meant to be dark
  POP     a big jump that is NOT within 2 frames of a cut (a glitch, a missing layer, a one-frame flash)
  FROZEN  more than 2.5 s with no change at all (keep an intended freeze-frame shorter, ~2 s, or expect the flag)
Writes out/qa_<name>.png: brightness (amber) and change (white) over time, cuts as grey ticks, flags in red.
numpy + PIL + ffmpeg only.
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 24


def shots():
    out = subprocess.run(['node', os.path.join(ROOT, 'render', 'shots.mjs'), '--json'], capture_output=True, text=True, cwd=ROOT).stdout
    return [(x['id'], x['start'], x['end'], x.get('trans') or {}) for x in json.loads(out)]


def main():
    path = sys.argv[1]
    t0 = float(sys.argv[sys.argv.index('--from') + 1]) if '--from' in sys.argv else 0.0
    w, h = 160, 90
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         capture_output=True).stdout
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, h, w).astype(np.float32)
    n = len(frames)
    lum = frames.mean(axis=(1, 2))
    diff = np.concatenate([[0], np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))])
    t = t0 + np.arange(n) / FPS
    S = shots()
    cuts = np.array([s[1] for s in S if s[1] > 0])
    near_cut = np.array([np.min(np.abs(cuts - x)) * FPS <= 2.5 if len(cuts) else False for x in t])
    dark_tr = [(tr['t0'] - 0.1, tr['t1'] + 0.1) for (_, _, _, tr) in S if tr.get('type') in ('blink', 'ink', 'dip', 'irisdip')]   # irisdip closes to black by design
    DUR = json.load(open(os.path.join(ROOT, 'song', 'timing.json'), encoding='utf-8'))['duration']   # the end may fade out
    dark_ok = lambda x: x < 0.3 or x >= DUR - 1.0 or any(a <= x <= b for a, b in dark_tr)
    flags = []
    for i in range(n):
        if lum[i] < 3 and not dark_ok(t[i]):
            flags.append(('BLANK', t[i], f'lum {lum[i]:.1f}'))
    # pops: diff far above its local context, not at a cut
    k = 12
    for i in range(1, n):
        lo, hi = max(1, i - k), min(n, i + k + 1)
        ctx = np.median(diff[lo:hi])
        if diff[i] > max(10, 4 * ctx + 4) and not near_cut[i]:
            flags.append(('POP', t[i], f'diff {diff[i]:.1f} vs local {ctx:.1f}'))
    # frozen stretches
    run = 0
    for i in range(1, n):
        run = run + 1 if diff[i] < 0.05 else 0
        if run == int(2.5 * FPS):
            flags.append(('FROZEN', t[i] - 2.5, 'no change for 2.5 s'))
    # collapse consecutive flags of the same kind
    merged = []
    for f in flags:
        if merged and merged[-1][0] == f[0] and f[1] - merged[-1][2] < 0.5:
            merged[-1][2] = f[1]
        else:
            merged.append([f[0], f[1], f[1], f[2]])
    print(f'{os.path.basename(path)}: {n} frames ({n / FPS:.1f} s from {t0:.1f}); lum {lum.min():.0f}-{lum.max():.0f}, median change {np.median(diff):.2f}')
    for kind, a, b, note in merged:
        shot = next((s[0] for s in S if s[1] <= a < s[2]), '?')
        print(f'  {kind:6} {a:7.2f}' + (f'-{b:.2f}' if b > a else '') + f'  [{shot}]  {note}')
    if not merged:
        print('  no flags')
    # the picture
    W, H = 1800, 420
    im = Image.new('RGB', (W, H), (14, 15, 22))
    d = ImageDraw.Draw(im)
    X = lambda x: int((x - t[0]) / max(1e-6, t[-1] - t[0]) * (W - 20)) + 10
    for c in cuts:
        if t[0] <= c <= t[-1]:
            d.line([(X(c), 10), (X(c), H - 10)], fill=(60, 62, 72))
    lm, dm = 255, max(8, np.percentile(diff, 99.5))
    pl = [(X(t[i]), H - 10 - int(lum[i] / lm * (H - 20))) for i in range(n)]
    pd = [(X(t[i]), H - 10 - int(min(1, diff[i] / dm) * (H - 20))) for i in range(n)]
    d.line(pl, fill=(242, 163, 58), width=1)
    d.line(pd, fill=(200, 205, 215), width=1)
    for kind, a, b, note in merged:
        d.rectangle([X(a) - 2, 4, X(b) + 2, 14], fill=(220, 50, 50))
    for s in range(int(t[0] // 10 * 10), int(t[-1]) + 1, 10):
        if s >= t[0]:
            d.text((X(s) + 2, H - 22), f'{s}s', fill=(120, 120, 130))
    name = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(ROOT, 'out', f'qa_{name}.png')
    im.save(out)
    print('plot:', out)


if __name__ == '__main__':
    main()
