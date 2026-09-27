#!/usr/bin/env python
"""reel.py -- string downloaded clips into one labelled review reel, in storyboard order.
Each clip plays whole with its own sound (silence if it has none), under a bar naming it and the moment it serves.

    python tools/reel.py out.mp4 name1 name2 ...   [--crf 24] [--title "REEL 1 CLIPS"] [--size 1280x720]
      (clips: assets/clips_in/<name>.mp4; moments: the clip lists, film.json clipLists = notes/clips/clips.json)
Each clip is letterboxed into the reel's size (default 1280x720), so a clip of any aspect keeps its shape."""
import glob
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from film import FILM, ROOT  # noqa: E402

CLIPS = os.path.join(ROOT, 'assets', 'clips_in')
W, H, BAR, FPS = 1280, 720, 40, 24

args = sys.argv[1:]
crf, title = '24', None
if '--crf' in args:
    i = args.index('--crf'); crf = args[i + 1]; args = args[:i] + args[i + 2:]
if '--size' in args:
    i = args.index('--size'); W, H = [int(v) for v in args[i + 1].lower().split('x')]; args = args[:i] + args[i + 2:]
if '--title' in args:
    i = args.index('--title'); title = args[i + 1]; args = args[:i] + args[i + 2:]
if not args:
    sys.exit(__doc__)
out, names = args[0], args[1:]

moments = {}
lists = [os.path.normpath(os.path.join(ROOT, p)) for p in FILM.get('clipLists', [])]
lists += [p for p in map(os.path.normpath, sorted(glob.glob(os.path.join(ROOT, 'notes', 'clips', 'clips*.json'))))
          if p not in lists]
for f in lists:
    if os.path.exists(f):
        for c in json.load(open(f, encoding='utf-8')):
            moments[c['name']] = c.get('moment', '')


def font(size, bold=False):
    names = ('georgiab.ttf', 'DejaVuSerif-Bold.ttf', 'Georgia Bold.ttf') if bold else ('georgia.ttf', 'DejaVuSerif.ttf', 'Georgia.ttf')
    for f in names:                                   # a bare name: Pillow searches the system's fonts
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


F1, F2, FT = font(19, True), font(15), font(44, True)

tmp = tempfile.mkdtemp()
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H + BAR}',
                        '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', crf, '-preset', 'slow', '-pix_fmt',
                        'yuv420p', os.path.join(tmp, 'v.mp4')], stdin=subprocess.PIPE)
auds = []


def silence(n, k):
    p = os.path.join(tmp, f's{k}.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t',
                    f'{n / FPS:.4f}', p], check=True)
    return p


if title:
    card = Image.new('RGB', (W, H + BAR), (8, 8, 10))
    d = ImageDraw.Draw(card)
    tw = d.textlength(title, font=FT)
    d.text(((W - tw) / 2, (H + BAR) / 2 - 30), title, font=FT, fill=(236, 232, 224))
    d.rectangle((W / 2 - 120, (H + BAR) / 2 + 30, W / 2 + 120, (H + BAR) / 2 + 33), fill=(170, 16, 30))
    for _ in range(36):
        enc.stdin.write(card.tobytes())
    auds.append(silence(36, 'title'))

for k, name in enumerate(names):
    path = os.path.join(CLIPS, f'{name}.mp4')
    if not os.path.exists(path):
        print('missing', name)
        continue
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf',
                          f'fps={FPS},scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    bar = Image.new('RGB', (W, BAR), (8, 8, 10))
    d = ImageDraw.Draw(bar)
    d.text((12, 9), name, font=F1, fill=(236, 232, 224))
    x = 24 + d.textlength(name, font=F1)
    d.text((x, 12), moments.get(name, ''), font=F2, fill=(200, 160, 150))
    d.rectangle((0, BAR - 2, W, BAR), fill=(170, 16, 30))
    barb = np.array(bar)
    for f in fr:
        enc.stdin.write(np.concatenate([barb, f], axis=0).tobytes())
    ap = os.path.join(tmp, f'a{k}.wav')
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-vn', '-t', f'{len(fr) / FPS:.4f}', '-ar', '48000',
                        '-ac', '2', '-af', 'apad', ap], capture_output=True)       # no sound of its own: silence below
    auds.append(ap if r.returncode == 0 and os.path.exists(ap) else silence(len(fr), k))
enc.stdin.close()
enc.wait()
lst = os.path.join(tmp, 'a.txt')
with open(lst, 'w') as f:
    f.write(''.join(f"file '{p.replace(os.sep, '/')}'\n" for p in auds))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, os.path.join(tmp, 'a.wav')],
               check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(tmp, 'v.mp4'), '-i', os.path.join(tmp, 'a.wav'),
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', out], check=True)
print(out, round(os.path.getsize(out) / 2 ** 20, 1), 'MB')
