#!/usr/bin/env python
"""ff.py -- first frames for image-to-video clips, from picked pictures.

    python tools/ff.py            # every entry of notes/clips/ff_picks.json -> notes/clips/ff/<name>.png + _sheet.jpg

ff_picks.json: {"<clip name>": {"src": "hero_tap/9351" (assets/gen/<id>.png) | "art:hero_rival" (assets/art/<name>.png),
"size": [1280, 720] (the default: 16:9, what most video models take; set the model's own input size if it wants
another; bigger holds faces better),
"dx": 0.5, "dy": 0.4 (the cover-crop anchor, 0..1), "fit": "contain" (+ "scale", "ox", "bottom": pad a portrait figure
onto its flat ground instead of cropping), "mirror": true (the picture faces the wrong way for the prompt)}}.
Upload notes/clips/ff/<name>.png as the clip's first frame; the downloaded clip goes to assets/clips_in/<name>.mp4."""
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'notes', 'clips', 'ff')


def src_path(s):
    if s.startswith('art:'):
        return os.path.join(ROOT, 'assets', 'art', s[4:] + '.png')
    return os.path.join(ROOT, 'assets', 'gen', s + '.png')


def cover(im, W, H, dx=0.5, dy=0.5):
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = round((im.width - W) * dx), round((im.height - H) * dy)
    return im.crop((x, y, x + W, y + H))


def main():
    picks = json.load(open(os.path.join(ROOT, 'notes', 'clips', 'ff_picks.json'), encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    made = []
    for name, p in picks.items():
        W, H = p.get('size', [1280, 720])
        im = Image.open(src_path(p['src'])).convert('RGB')
        if p.get('fit') == 'contain':          # a portrait figure on flat colour: pad it into the frame (no crop)
            ground = im.getpixel((6, 6))
            s = min(W / im.width, H / im.height) * p.get('scale', 1.0)
            fg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            ff = Image.new('RGB', (W, H), ground)
            ff.paste(fg, ((W - fg.width) // 2 + p.get('ox', 0), H - fg.height if p.get('bottom') else (H - fg.height) // 2))
        else:
            ff = cover(im, W, H, p.get('dx', 0.5), p.get('dy', 0.4))
        if p.get('mirror'):                    # the picture faces the wrong way for the prompt
            from PIL import ImageOps
            ff = ImageOps.mirror(ff)
        fn = os.path.join(OUT, f'{name}.png')
        ff.save(fn)
        made.append((name, ff))
        print(f'{name:<18} {p["src"]:<26} -> {W}x{H}')
    cols, tw, th = 4, 416, 240
    S = Image.new('RGB', (cols * tw, ((len(made) + cols - 1) // cols) * (th + 18)), (18, 18, 20))
    d = ImageDraw.Draw(S)
    for i, (name, ff) in enumerate(made):
        t = ff.resize((tw, th))
        x, y = (i % cols) * tw, (i // cols) * (th + 18)
        S.paste(t, (x, y + 18)); d.text((x + 4, y + 3), name, fill=(255, 210, 120))
    S.save(os.path.join(OUT, '_sheet.jpg'), quality=88)
    print('sheet', os.path.join(OUT, '_sheet.jpg'))


if __name__ == '__main__':
    main()
