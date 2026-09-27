#!/usr/bin/env python3
"""reelsheet.py -- the director's review: one frame per shot of a reel, pulled from a preview video, tiled + labelled.

    python render/reelsheet.py reel1 out/range_preview_0-33.mp4 [--from 0] [--at 0.5]   -> notes/review/<reel>.jpg

The reel is a shot-id prefix (shots reel1_*). --from = the song time of the video's first frame (range previews start
at their --from); --at = where in each shot to sample (0..1, default 0.5)."""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def font(size):
    for f in ('consola.ttf', 'DejaVuSansMono.ttf', 'Menlo.ttc'):   # a bare name: Pillow searches the system's fonts
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    reel, video = sys.argv[1], sys.argv[2]
    t_from = float(sys.argv[sys.argv.index('--from') + 1]) if '--from' in sys.argv else 0.0
    at = float(sys.argv[sys.argv.index('--at') + 1]) if '--at' in sys.argv else 0.5
    shots = json.loads(subprocess.run(['node', os.path.join(ROOT, 'render', 'shots.mjs'), '--json'], capture_output=True, text=True, cwd=ROOT).stdout)
    mine = [s for s in shots if s['id'].startswith(reel + '_')]
    TW, TH = 480, 270
    thumbs = []
    for s in mine:
        t = s['start'] + (s['end'] - s['start']) * at - t_from
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, t):.3f}', '-i', video, '-frames:v', '1', '-vf', f'scale={TW}:{TH}',
                              '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
        im = Image.frombytes('RGB', (TW, TH), raw) if len(raw) == TW * TH * 3 else Image.new('RGB', (TW, TH), (40, 0, 0))
        thumbs.append((s, im))
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    out = Image.new('RGB', (cols * TW, rows * (TH + 22)), (12, 12, 14))
    d = ImageDraw.Draw(out)
    f = font(15)
    for i, (s, im) in enumerate(thumbs):
        x, y = (i % cols) * TW, (i // cols) * (TH + 22)
        out.paste(im, (x, y))
        d.text((x + 4, y + TH + 3), f"{s['id']} {s['start']:.2f}-{s['end']:.2f}", fill=(230, 230, 230), font=f)
    os.makedirs(os.path.join(ROOT, 'notes', 'review'), exist_ok=True)
    p = os.path.join(ROOT, 'notes', 'review', f'{reel}.jpg')
    out.save(p, quality=85)
    print(p, len(thumbs), 'shots')


if __name__ == '__main__':
    main()
