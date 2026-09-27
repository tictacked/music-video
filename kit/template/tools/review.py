#!/usr/bin/env python
"""review.py -- the director's review at three scales, as one command.

    python tools/review.py film  [--from S --to E]   one frame per shot (middle) -> notes/review/film_<stamp>/sheet.png
    python tools/review.py cuts  [--from S --to E]   every boundary: 3 frames before | after -> notes/review/cuts_<stamp>/sheet.png
    python tools/review.py reel <prefix>             all shots whose id starts with <prefix> (e.g. m_), 3 frames each

(The third scale, time, is render.mjs --preview + render/qa.py.)
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def shots():
    out = subprocess.run(['node', 'render/shots.mjs', '--json'], capture_output=True, text=True, cwd=ROOT).stdout
    return json.loads(out)


def arg(k, d=None):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d


def stills(extra, out):
    cmd = ['node', 'render/stills.mjs', '--out', out, '--keep-going'] + extra
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    tail = [l for l in r.stdout.splitlines() if 'sheet' in l or 'failed' in l.lower()]
    print('\n'.join(tail[-3:]) or r.stdout[-800:])
    if r.returncode:
        print(r.stderr[-2000:])


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'film'
    S = shots()
    a, b = float(arg('--from', 0)), float(arg('--to', 1e9))
    stamp = time.strftime('%H%M%S')
    if mode == 'film':
        ids = [s['id'] for s in S if a <= s['start'] < b]
        stills(['--shots', ','.join(ids), '--n', '1', '--w', '640', '--cols', '6'], f'notes/review/film_{stamp}')
    elif mode == 'cuts':
        ts = []
        for s in S[1:]:
            if a <= s['start'] < b:
                ts += [round(s['start'] - 3 / 24, 3), round(s['start'] + 3 / 24, 3)]
        stills(['--times', ','.join(map(str, ts)), '--w', '640', '--cols', '6'], f'notes/review/cuts_{stamp}')
    elif mode == 'reel':
        pre = sys.argv[2]
        ids = [s['id'] for s in S if s['id'].startswith(pre)]
        stills(['--shots', ','.join(ids), '--n', '3', '--w', '640', '--cols', '6'], f'notes/review/reel_{pre}_{stamp}')


if __name__ == '__main__':
    main()
