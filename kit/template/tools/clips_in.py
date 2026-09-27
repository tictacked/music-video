#!/usr/bin/env python
"""clips_in.py -- bring clips from ANY image-to-video model into the film.

    <PY> tools/clips_in.py              # every new assets/clips_in/<name>.mp4 (.webm, .mov) -> frames + clips.js
    <PY> tools/clips_in.py --redo hero_turn     # redo one (after replacing its file)
    <PY> tools/clips_in.py --no-upscale         # skip the upscale even if this machine has one

Make the clips wherever you like (an online video model or a local one), from the first frames in notes/clips/ff/
and the prompts in notes/clips/clips.json. Save each as assets/clips_in/<name>.mp4, where <name> is the clip's name in
the list. A re-roll is <name>_r2.mp4: it waits until you rename the keeper to <name>.mp4. Then this:
  1. frames at 24 fps, Lanczos to 1920 wide -> assets/clips/<name>/00000.jpg ... (tools/rawframes.py): usable at once
  2. an upscale in place, if this machine has one (the kit's machine.json upscale_python: tools/upscale.py raw)
  3. assets/clips/clips.js (tools/clipsjs.py), which the page reads
Scenes play a clip with K.s.use('<name>', {...}) (STYLE.md). Figures shot on flat mint or pink become alpha clips
with tools/keyclip.py.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from film import FILM, MACHINE, ROOT  # noqa: E402
from rawframes import make_frames  # noqa: E402

SRC = os.path.join(ROOT, 'assets', 'clips_in')
OUT = os.path.join(ROOT, 'assets', 'clips')
EXTS = ('.mp4', '.webm', '.mov', '.mkv')


def probe(path):
    try:
        out = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                       'stream=width,height,r_frame_rate:format=duration', '-of', 'json', path])
        j = json.loads(out)
        s = j['streams'][0]
        num, den = (int(x) for x in s['r_frame_rate'].split('/'))
        return s['width'], s['height'], num / max(1, den), float(j['format']['duration'])
    except Exception:
        return None


def listed():
    names = set()
    for f in FILM.get('clipLists') or []:
        p = os.path.join(ROOT, f)
        if os.path.isfile(p):
            try:
                names |= {c.get('name') for c in json.load(open(p, encoding='utf-8')) if isinstance(c, dict)}
            except ValueError:
                pass
    return names


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--redo', action='append', default=[])
    ap.add_argument('--no-upscale', action='store_true')
    a = ap.parse_args()
    os.makedirs(SRC, exist_ok=True)
    known = listed()
    made = []
    for f in sorted(os.listdir(SRC)):
        name, ext = os.path.splitext(f)
        if ext.lower() not in EXTS or re.search(r'_r[0-9]+$', name) or name.endswith('_BROKEN'):
            continue
        d = os.path.join(OUT, name)
        if os.path.isdir(d) and any(x.endswith('.jpg') for x in os.listdir(d)) and name not in a.redo:
            continue
        info = probe(os.path.join(SRC, f))
        n = make_frames(name, os.path.join(SRC, f))
        if not n:
            continue
        made.append(name)
        desc = f'{info[0]}x{info[1]} at {info[2]:.2f} fps, {info[3]:.2f} s' if info else '?'
        note = '' if not known or name in known else '   (not in the clip list: fine, but give it a line there)'
        aspect = f'   (aspect {info[0] / info[1]:.2f}: 16:9 clips fill the frame without cropping)' \
            if info and abs(info[0] / info[1] - 16 / 9) > 0.05 else ''
        print(f'{name}: {n} frames from {desc}{note}{aspect}', flush=True)
    waiting = [f for f in os.listdir(SRC) if re.search(r'_r[0-9]+\.[a-z0-9]+$', f)]
    if made and not a.no_upscale and MACHINE.get('upscale_python'):
        print('upscaling in place (machine.json upscale_python)...', flush=True)
        subprocess.run([sys.executable, os.path.join(HERE, 'upscale.py'), 'raw'], cwd=ROOT)
    subprocess.run([sys.executable, os.path.join(HERE, 'clipsjs.py')], cwd=ROOT)
    print(f'{len(made)} clip(s) brought in' + (f'; waiting for a verdict: {", ".join(sorted(waiting))}' if waiting else ''))
    if made and not MACHINE.get('upscale_python'):
        print('  (frames are Lanczos-scaled; for a cleaner upscale set up tools/upscale.py: see its header)')


if __name__ == '__main__':
    main()
