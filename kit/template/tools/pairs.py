#!/usr/bin/env python
"""pairs.py -- a side-by-side reel: a source plate | the video model's version of it, synced, labelled.

    python tools/pairs.py out.mp4 plate.mp4 result.mp4 start "left label" "right label" [plate result start L R ...]

Each pair plays from `start` to the end of the result, both letterboxed into 832x480; the audio is the result's own
(silence when the result has none)."""
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, BAR, FPS = 832, 480, 44, 24


def frames(path, start):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{start:.3f}', '-i', path, '-vf',
                          f'fps={FPS},scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def load_font(size):
    for f in ('georgia.ttf', 'DejaVuSerif.ttf', 'Georgia.ttf'):   # a bare name: Pillow searches the system's fonts
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


font = load_font(22)
out, args = sys.argv[1], sys.argv[2:]
groups = [args[i:i + 5] for i in range(0, len(args), 5)]
tmp = tempfile.mkdtemp()
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W * 2 + 8}x{H + BAR}',
                        '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p',
                        os.path.join(tmp, 'v.mp4')], stdin=subprocess.PIPE)
auds = []
for k, (plate, result, start, left, right) in enumerate(groups):
    start = float(start)
    a, b = frames(plate, start), frames(result, start)
    n = len(b)
    for i in range(n):
        im = Image.new('RGB', (W * 2 + 8, H + BAR), (8, 8, 10))
        im.paste(Image.fromarray(a[min(i, len(a) - 1)]), (0, BAR))
        im.paste(Image.fromarray(b[i]), (W + 8, BAR))
        d = ImageDraw.Draw(im)
        d.text((14, 10), left, font=font, fill=(236, 232, 224))
        d.text((W + 22, 10), right, font=font, fill=(236, 232, 224))
        d.rectangle((W + 8, BAR - 3, W * 2 + 8, BAR - 1), fill=(170, 16, 30))
        enc.stdin.write(im.tobytes())
    ap = os.path.join(tmp, f'a{k}.wav')
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-i', result, '-vn', '-t', f'{n / FPS:.3f}',
                        '-ar', '48000', '-ac', '2', ap], capture_output=True)
    if r.returncode or not os.path.exists(ap):          # a clip with no sound of its own
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t',
                        f'{n / FPS:.3f}', ap], check=True)
    auds.append(ap)
enc.stdin.close()
enc.wait()
lst = os.path.join(tmp, 'a.txt')
with open(lst, 'w') as f:
    f.write(''.join(f"file '{p.replace(os.sep, '/')}'\n" for p in auds))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, os.path.join(tmp, 'a.wav')],
               check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(tmp, 'v.mp4'), '-i', os.path.join(tmp, 'a.wav'),
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', out], check=True)
print(out)
