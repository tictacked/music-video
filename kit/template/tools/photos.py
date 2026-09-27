#!/usr/bin/env python
"""photos.py -- REAL photos of the film's places (Wikimedia Commons, freely licensed) as img2img sources for the plates:
real places, real signs, real light. The film's look goes on top by img2img, then the engine's grade.

    python tools/photos.py add <key> "<search terms>"     # remember a search and run it
    python tools/photos.py search [<key> ...]             # run remembered searches again (default: all of them)
    python tools/photos.py crop <key>/<NN> [x0 y0 x1 y1] [--size 1344x768]   # -> assets/photos/_src/<key>_<NN>.png
    [--n 12]   photos per search

<key> is a short folder name of your choosing ("harbour", "station"); the terms are what you would type into
Commons' search box ("harbour crane night", "train station platform rain"). Searches are remembered in
assets/photos/queries.json. Each search -> assets/photos/<key>/NN.jpg, 1280 px wide (a STANDARD Commons thumbnail size:
1600 got HTTP 429, rate-limited), + a labelled _sheet.jpg to pick from. `crop` cuts a pick to the plate's size (a
cover crop, centred; give a box in the photo's pixels to aim it).
Pick photos whose light already matches the shot: img2img keeps the light where it was, and the grade can't move
light sources. Every photo's source page, licence and author are in assets/photos/<key>/sources.json: credit them the
way their licence asks.
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'photos')
QFILE = os.path.join(OUT, 'queries.json')
UA = {'User-Agent': 'music-video-kit/1.0 (img2img references for a music video) python-urllib'}
API = 'https://commons.wikimedia.org/w/api.php'


def queries():
    try:
        return json.load(open(QFILE, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def remember(key, terms):
    q = queries()
    q[key] = terms
    os.makedirs(OUT, exist_ok=True)
    json.dump(q, open(QFILE, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def search(key, q, n=12):
    params = dict(action='query', format='json', generator='search', gsrnamespace='6', gsrsearch=q, gsrlimit=str(n),
                  prop='imageinfo', iiprop='url|size|mime|extmetadata', iiurlwidth='1280')
    data = json.loads(get(API + '?' + urllib.parse.urlencode(params)))
    pages = sorted((data.get('query') or {}).get('pages', {}).values(), key=lambda p: p.get('index', 0))
    d = os.path.join(OUT, key)
    os.makedirs(d, exist_ok=True)
    src = []
    k = 0
    for p in pages:
        ii = (p.get('imageinfo') or [{}])[0]
        if ii.get('mime') not in ('image/jpeg', 'image/png') or not ii.get('thumburl'):
            continue
        if ii.get('width', 0) < 900:
            continue
        fn = os.path.join(d, f'{k:02d}.jpg')
        if not os.path.exists(fn):
            time.sleep(0.8)                    # gently: Commons rate-limits bursts
            try:
                raw = get(ii['thumburl'])
            except Exception as e:
                print('  skip', p.get('title'), e)
                continue
            from PIL import Image
            Image.open(io.BytesIO(raw)).convert('RGB').save(fn, quality=92)
        md = ii.get('extmetadata') or {}
        src.append(dict(n=k, title=p.get('title'), page=ii.get('descriptionurl'),
                        licence=(md.get('LicenseShortName') or {}).get('value'),
                        artist=(md.get('Artist') or {}).get('value', '')[:160]))
        k += 1
    json.dump(src, open(os.path.join(d, 'sources.json'), 'w', encoding='utf-8'), indent=1)
    sheet(key)
    print(f'{key}: {k} photos ({q!r})')


def sheet(key, cell=400, cols=4):
    from PIL import Image, ImageDraw
    d = os.path.join(OUT, key)
    fs = sorted(f for f in os.listdir(d) if f.endswith('.jpg') and not f.startswith('_'))
    if not fs:
        return
    rows = (len(fs) + cols - 1) // cols
    S = Image.new('RGB', (cols * cell, rows * (cell * 9 // 16 + 22)), (18, 18, 20))
    dr = ImageDraw.Draw(S)
    for i, f in enumerate(fs):
        im = Image.open(os.path.join(d, f)).convert('RGB')
        im.thumbnail((cell, cell * 9 // 16))
        x, y = (i % cols) * cell, (i // cols) * (cell * 9 // 16 + 22)
        S.paste(im, (x + (cell - im.width) // 2, y + 22))
        dr.text((x + 4, y + 4), f'{key}/{f[:-4]}  {im.width}x{im.height}', fill=(255, 210, 120))
    S.save(os.path.join(d, '_sheet.jpg'), quality=85)


def crop(spec, box=None, size=(1344, 768)):
    from PIL import Image
    key, n = spec.split('/')
    im = Image.open(os.path.join(OUT, key, f'{int(n):02d}.jpg')).convert('RGB')
    if box:
        im = im.crop(tuple(int(v) for v in box))
    tw, th = size
    s = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x0, y0 = (im.width - tw) // 2, (im.height - th) // 2
    im = im.crop((x0, y0, x0 + tw, y0 + th))
    os.makedirs(os.path.join(OUT, '_src'), exist_ok=True)
    fn = os.path.join(OUT, '_src', f'{key}_{int(n):02d}.png')
    im.save(fn)
    print(fn)
    return fn


def main():
    a = sys.argv[1:]
    opts = {}
    for k in ('--n', '--size'):
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    n = int(opts.get('--n', 12))
    if len(a) >= 3 and a[0] == 'add':
        key, terms = a[1], ' '.join(a[2:])
        remember(key, terms)
        search(key, terms, n)
    elif a and a[0] == 'search':
        q = queries()
        if not q:
            sys.exit('no searches yet: python tools/photos.py add <key> "<search terms>"')
        for k in (a[1:] or q):
            if k not in q:
                print(k, 'FAILED: no such search (python tools/photos.py add', k, '"<search terms>")')
                continue
            try:
                search(k, q[k], n)
            except Exception as e:
                print(k, 'FAILED', e)
    elif len(a) >= 2 and a[0] == 'crop':
        size = tuple(int(v) for v in opts['--size'].lower().split('x')) if '--size' in opts else (1344, 768)
        crop(a[1], a[2:6] if len(a) >= 6 else None, size)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
