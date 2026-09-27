#!/usr/bin/env python
"""drift.py -- where has a film's copy of a kit file drifted from the kit it came from, and which way?

    python <kit>/drift.py [film folder ...]     (default: every film in $MV_FILMS, else ~/music-videos)

Each film is compared with the kit its film.json names ("kit"; this kit when that one is gone), three ways: against
the kit NOW and against the kit AS IT WAS when the film was made (film.json "kitCommit", read from the kit's git):
    =          the film has the kit's current file
    kit newer  the kit improved it since; the film has the old one (bring it over if the film is still being worked on)
    FILM       the film changed it and the kit didn't: a fix to consider bringing INTO the kit (then run test/regress.mjs)
    both       both changed it: merge by hand
    missing    the film has no such file
Without a kitCommit (or when the kit has no git history), files are compared with the kit now: same / differs /
missing. Film-owned files are skipped (film.json, the docs, notes/, timeline.js, scenes/, cast.js, vocab.js,
assets.py, retouch.py, timing). Finished films stay FROZEN: this is for knowing, not for rewriting them.
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__)).replace(os.sep, '/')
OWNED = {'film.json', 'README.md', 'PLAN.md', 'STORYBOARD.md', 'STYLE.md', 'ASSETS.md', 'web/timeline.js', 'web/timing.js',
         'web/lib/cast.js', 'web/lib/vocab.js', 'tools/assets.py', 'tools/retouch.py', 'song/timing.json', '.gitignore',
         '.gitattributes'}
SKIP_DIRS = ('notes/', 'web/scenes/', 'assets/', 'out/', 'node_modules')


def films_home():
    return (os.environ.get('MV_FILMS') or os.path.join(os.path.expanduser('~'), 'music-videos')).replace(os.sep, '/')


def norm(b):
    return hashlib.md5(b.replace(b'\r\n', b'\n')).hexdigest()


def kit_files(kit):
    out = []
    for root, dirs, files in os.walk(kit + '/template'):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', 'node_modules')]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), kit + '/template').replace(os.sep, '/')
            if rel in OWNED or rel.startswith(SKIP_DIRS) or f.endswith('.pyc'):
                continue
            out.append(rel)
    return sorted(out)


def at_commit(kit, commit, rel):
    # ./ = relative to the kit folder, wherever it sits inside its git repository
    r = subprocess.run(['git', '-C', kit, 'show', f'{commit}:./template/{rel}'], capture_output=True)
    return norm(r.stdout) if r.returncode == 0 else None


def kit_of(film, fj):
    k = (fj.get('kit') or '').replace(os.sep, '/')
    return k if k and os.path.isdir(k + '/template') else HERE


def check(film):
    p = os.path.join(film, 'film.json')
    fj = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    kit = kit_of(film, fj)
    base = (fj.get('kitCommit') or '').replace('+dirty', '') or None
    if base == 'unknown':
        base = None
    files = kit_files(kit)
    rows = []
    for rel in files:
        fp = os.path.join(film, rel)
        now = norm(open(os.path.join(kit, 'template', rel), 'rb').read())
        if not os.path.exists(fp):
            rows.append((rel, 'missing'))
            continue
        mine = norm(open(fp, 'rb').read())
        if mine == now:
            continue
        if not base:
            rows.append((rel, 'differs'))
            continue
        was = at_commit(kit, base, rel)
        if was is None or mine == was:
            rows.append((rel, 'kit newer' if was is not None else 'differs'))
        elif now == was:
            rows.append((rel, 'FILM'))
        else:
            rows.append((rel, 'both'))
    return kit, base, len(files), rows


def main():
    home = films_home()
    films = sys.argv[1:] or ([os.path.join(home, d) for d in sorted(os.listdir(home))
                              if os.path.isfile(os.path.join(home, d, 'film.json'))] if os.path.isdir(home) else [])
    if not films:
        sys.exit(f'no films given, and none in {home}')
    for film in films:
        kit, base, nfiles, rows = check(film)
        print(f"\n{os.path.basename(os.path.abspath(film))}  (kit {kit}{' @ ' + base if base else ', no kit commit'}): "
              f'{nfiles - len(rows)} files as the kit')
        for rel, st in rows:
            print(f'  {st:10s} {rel}')


if __name__ == '__main__':
    main()
