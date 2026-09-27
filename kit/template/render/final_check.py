#!/usr/bin/env python
"""final_check.py -- the delivery checklist, run on the finished master and cuts before anything is sent.

    <PY> render/final_check.py          -> a PASS / FAIL / LOOK list + notes/final_check/*.png
    (PY = the kit's python: `python tools/film.py PY` prints its path)

Checks what went wrong before:
  - FRAMES: the master holds every frame of the song, ceil(duration * 24) (a master once shipped 3,751 of 3,754: the
    mux's -shortest cut the credit's last frames; render.mjs no longer passes it).
  - the master's streams: 1920x1080, 24 fps, yuv420p, audio as long as the song (+-0.1 s).
  - the share cuts render/share.py makes (out/<name>_share.mp4, out/<name>_discord.mp4; their settings = share.py's
    defaults under film.json's "share" / "discord" blocks): present, no bigger than the cut's maxMiB (default
    targetMiB * 1.05: two-pass encodes overshoot a little), and the same frame count as the master. The discord cut
    must not open on black when film.json posterT is set: chat apps thumbnail a video from its first decoded frame.
  - LOOK: the credit, pulled at FULL resolution (notes/final_check/credit.png: read every letter; every credited
    artist and author spelled EXACTLY), the first frame, and the poster frame.
  - LOOK: the reserved colour (film.json reservedColour, e.g. a red only one character may wear): every second where
    more than 0.2% of the frame is that colour, so you can check each one belongs to its owner.
  - qa.py (blank / pop frames), and git: the delivery should be committed.
Nothing rendered yet is not a crash: a missing master is a FAIL line, a missing cut a LOOK line.
Run a STRICT render first (node render/render.mjs; strict is the default): a loose render can hide a missing asset.
"""
import json
import math
import os
import shutil
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from film import FILM  # noqa: E402

OUT = os.path.join(ROOT, 'notes', 'final_check')
FPS = 24
rows = []


def say(kind, what, detail=''):
    rows.append((kind, what, detail))
    print(f'{kind:5s} {what}' + (f'  ({detail})' if detail else ''), flush=True)


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-show_entries',
                        'stream=codec_type,width,height,r_frame_rate,pix_fmt,duration,nb_read_packets',
                        '-of', 'json', path], capture_output=True, text=True)
    try:
        return json.loads(r.stdout or '{}').get('streams', [])
    except ValueError:
        return []


def grab(src, t, dst, w=None):
    vf = ['-vf', f'scale={w}:-1'] if w else []
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', src, '-frames:v', '1', *vf, dst], check=False)


def cuts():
    """{cut: settings} for the cuts render/share.py makes: its DEFAULTS under film.json's block of the same name.
    Without share.py: every film.json block that has a targetMiB."""
    try:
        sys.path.insert(0, os.path.join(ROOT, 'render'))
        from share import DEFAULTS
    except Exception:
        DEFAULTS = {k: {} for k, v in FILM.items() if isinstance(v, dict) and 'targetMiB' in v}
    return {k: dict(DEFAULTS[k], **(FILM.get(k) or {})) for k in DEFAULTS}


POSTER_CUT = 'discord'        # render/share.py puts the frame at posterT on this cut's frame 0


def reserved_audit(src, hexcol, dur):
    """seconds (sampled at 2 fps, 480 px wide) where > 0.2% of the frame is within the reserved colour's hue"""
    c = np.array([int(hexcol[i:i + 2], 16) for i in (1, 3, 5)], float) / 255
    mx, mn = c.max(), c.min()
    if mx - mn < 0.2:
        return None
    hue = lambda r, g, b, M, m: np.where(M == r, ((g - b) / np.maximum(M - m, 1e-6)) % 6,
                                         np.where(M == g, (b - r) / np.maximum(M - m, 1e-6) + 2, (r - g) / np.maximum(M - m, 1e-6) + 4)) * 60
    h0 = float(hue(*c, mx, mn))
    w, h = 480, 270
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-vf', f'fps=2,scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         stdout=subprocess.PIPE)
    hits, i = [], 0
    while True:
        buf = p.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        a = np.frombuffer(buf, np.uint8).reshape(h, w, 3).astype(float) / 255
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        M, m = a.max(2), a.min(2)
        sat = (M - m) / np.maximum(M, 1e-6)
        dh = np.abs((hue(r, g, b, M, m) - h0 + 180) % 360 - 180)
        frac = float(((dh < 12) & (sat > 0.45) & (M > 0.25)).mean())
        if frac > 0.002:
            hits.append((i / 2, frac))
        i += 1
    p.wait()
    return hits


def main():
    os.makedirs(OUT, exist_ok=True)
    name = FILM['name']
    tools_ok = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))
    if not tools_ok:
        say('FAIL', 'ffmpeg and ffprobe on the PATH', 'every video check below needs them')
    dur = want = None
    try:
        timing = json.load(open(os.path.join(ROOT, 'song', 'timing.json'), encoding='utf-8'))
        dur = float(timing['duration'])
        want = math.ceil(dur * FPS)
    except (OSError, ValueError, KeyError) as e:
        say('FAIL', 'song/timing.json (song/timing.py)', f'unreadable: {e}')
    master = os.path.join(ROOT, 'out', f'{name}.mp4')
    have_master = tools_ok and os.path.exists(master)
    n = None
    if not os.path.exists(master):
        say('FAIL', f'no master at out/{name}.mp4 (node render/render.mjs)')
    elif have_master:
        st = probe(master)
        v = next((s for s in st if s.get('codec_type') == 'video'), {})
        a = next((s for s in st if s.get('codec_type') == 'audio'), {})
        n = int(v.get('nb_read_packets', 0) or 0)
        if want is not None:
            say('PASS' if n == want else 'FAIL', f'master frames {n} / song {want}', f'{dur:.3f} s at {FPS} fps')
        ok = v.get('width') == 1920 and v.get('height') == 1080 and v.get('r_frame_rate') == '24/1' and v.get('pix_fmt') == 'yuv420p'
        say('PASS' if ok else 'FAIL', 'master stream 1920x1080 24/1 yuv420p', f"{v.get('width')}x{v.get('height')} {v.get('r_frame_rate')} {v.get('pix_fmt')}")
        ad = float(a.get('duration', 0) or 0)
        if dur is not None:
            say('PASS' if a and abs(ad - dur) < 0.1 else 'FAIL', 'master audio as long as the song', f'{ad:.3f} s')
    for cut, blk in cuts().items():
        p = os.path.join(ROOT, 'out', f'{name}_{cut}.mp4')
        cap = float(blk.get('maxMiB') or float(blk['targetMiB']) * 1.05)
        if not os.path.exists(p):
            say('LOOK', f'no {cut} cut yet at out/{name}_{cut}.mp4 (python render/share.py)')
            continue
        size = os.path.getsize(p) / 2 ** 20
        say('PASS' if size <= cap else 'FAIL', f'{cut} cut at most {cap:.2f} MiB', f'{size:.2f} MiB')
        if not tools_ok:
            continue
        cn = int(next((s for s in probe(p) if s.get('codec_type') == 'video'), {}).get('nb_read_packets', 0) or 0)
        if n is not None:
            say('PASS' if cn == n else 'FAIL', f'{cut} cut frames = master', f'{cn}')
        if cut == POSTER_CUT and (FILM.get('posterT') or 0) > 0:
            f0 = os.path.join(OUT, f'{cut}_frame0.png')
            grab(p, 0, f0, 480)
            from PIL import Image
            luma = float(np.asarray(Image.open(f0).convert('L')).mean()) if os.path.exists(f0) else 0
            say('PASS' if luma > 12 else 'FAIL', f"{cut} cut's frame 0 is the poster, not black",
                f'mean luma {luma:.0f}; notes/final_check/{cut}_frame0.png')
    if have_master:
        grab(master, 0, os.path.join(OUT, 'first.png'))
        grab(master, max(0, (dur or 1.0) - 1.0), os.path.join(OUT, 'credit.png'))
        say('LOOK', 'the credit at FULL resolution: read every letter', 'notes/final_check/credit.png (the last second; first.png too)')
        rc = FILM.get('reservedColour')
        if rc:
            hits = reserved_audit(master, rc, dur)
            if hits is None:
                say('LOOK', f'reservedColour {rc} is too grey to audit by hue')
            else:
                spans, last = [], None
                for t, _ in hits:
                    if last is not None and t - last <= 0.5:
                        spans[-1][1] = t
                    else:
                        spans.append([t, t])
                    last = t
                say('LOOK', f"reserved colour {rc} on screen in {len(spans)} spans: check each is its owner's",
                    ', '.join(f'{a:.1f}-{b + 0.5:.1f}s' for a, b in spans[:40]) + (' ...' if len(spans) > 40 else ''))
        q = subprocess.run([sys.executable, os.path.join(ROOT, 'render', 'qa.py'), master], capture_output=True, text=True)
        tail = [l for l in (q.stdout or '').splitlines() if l.strip()][-3:]
        say('LOOK', 'qa.py (blank frames should all be designed blacks; pops should be painted hits)', ' | '.join(tail))
    if not shutil.which('git'):
        say('LOOK', 'git: not installed, so the delivered state is not versioned')
    else:
        g = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain'], capture_output=True, text=True)
        dirty = [l for l in g.stdout.splitlines() if l.strip()]
        if g.returncode:
            say('LOOK', 'git: the film is not a git repository', (g.stderr or '').strip()[:120])
        else:
            say('PASS' if not dirty else 'LOOK', 'git: the delivered state is committed', f'{len(dirty)} uncommitted changes' if dirty else 'clean')
    json.dump(rows, open(os.path.join(OUT, 'final_check.json'), 'w'), indent=1)
    fails = sum(1 for k, _, _ in rows if k == 'FAIL')
    print(f'\n{fails} FAIL, {sum(1 for k, _, _ in rows if k == "LOOK")} LOOK -> notes/final_check/')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
