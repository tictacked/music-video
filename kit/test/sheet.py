#!/usr/bin/env python
"""sheet.py -- the look after test/regress.mjs: each sampled frame from the film's MASTER (the video that was
delivered) beside the same frame drawn by the kit's engine, labelled, two pairs a row.

    <PY> test/sheet.py test/out/<film>        -> test/out/<film>/sheet.jpg
    (PY = the kit's python, <kit>/env/py)
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

FPS = 24
TW, TH, LAB = 480, 270, 26


def master_of(film):
    out = os.path.join(film, 'out')
    mp4 = [os.path.join(out, f) for f in os.listdir(out) if f.endswith('.mp4') and '_share' not in f and '_discord' not in f]
    return max(mp4, key=os.path.getsize)


def frame(master, f, dst):
    t = max(0.0, (f - 0.25) / FPS)          # the first frame at or after t is frame f
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.4f}', '-i', master, '-frames:v', '1',
                    '-vf', f'scale={TW}:{TH}', dst], check=True)
    return Image.open(dst).convert('RGB')


def font(size):
    for f in ('consola.ttf', 'DejaVuSansMono.ttf', 'Menlo.ttc'):   # a bare name: Pillow searches the system's fonts
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def main(d):
    rep = json.load(open(os.path.join(d, 'report.json'), encoding='utf-8'))
    master = master_of(rep['film'])
    pairs = sorted(rep['sheet'], key=lambda s: s['f'])
    rows = (len(pairs) + 1) // 2
    W, H = 4 * TW + 3 * 6, rows * (TH + LAB) + 40
    sheet = Image.new('RGB', (W, H), (24, 22, 28))
    dr = ImageDraw.Draw(sheet)
    font_ = font(18)
    dr.text((8, 10), f"{rep['name']}: master (left) vs the kit engine (right). {rep['checked']} frames checked: "
                      f"{rep['identical']} identical, {rep['noise']} render noise, {len(rep['mismatches'])} different",
            fill=(246, 241, 231), font=font_)
    for i, p in enumerate(pairs):
        r, c = divmod(i, 2)
        x0, y0 = c * (2 * TW + 12), 40 + r * (TH + LAB)
        m = frame(master, p['f'], os.path.join(d, f"master_{p['f']:05d}.png"))
        k = Image.open(os.path.join(d, p['file'])).convert('RGB').resize((TW, TH), Image.LANCZOS)
        sheet.paste(m, (x0, y0 + LAB)); sheet.paste(k, (x0 + TW + 6, y0 + LAB))
        dr.text((x0 + 4, y0 + 4), f"master  f{p['f']}  {p['f'] / FPS:.2f}s", fill=(217, 199, 164), font=font_)
        dr.text((x0 + TW + 10, y0 + 4), 'kit engine', fill=(217, 199, 164), font=font_)
    dst = os.path.join(d, 'sheet.jpg')
    sheet.save(dst, quality=90)
    print(dst)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
