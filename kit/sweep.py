#!/usr/bin/env python
"""sweep.py -- find the regenerable scratch in FINISHED films (render chunks, previews, painter stills), and delete it
only when told to. Default is a dry run: nothing is touched.

    python <kit>/sweep.py                          # every film in the films folder: sizes by kind
    python <kit>/sweep.py myfilm --list            # every file that would go
    python <kit>/sweep.py myfilm --delete          # really delete (ask the user first)
    python <kit>/sweep.py --quarantine <folder>    # move it aside instead (same drive), with a manifest.json
    python <kit>/sweep.py --restore <folder>       # put everything in a quarantine back
    [--root <folder of films>]    default: where new_film.py puts films ($MV_FILMS, else ~/music-videos)
A film is a name in the root, or a path to a film folder.
The safe way: quarantine on the SAME drive as the films (instant renames; a move across drives fails), render-check
every film (`node <kit>/test/regress.mjs <film> --self --every 24 --sheet 0`: a missing runtime file fails the strict
page), and only then delete the quarantine folder.

What counts as scratch (regenerable: the master exists, and git holds the code that made it):
  chunks    out/chunks-full/, out/chunks-preview*/     (a later fix then re-renders the whole film: ~5-7 min)
  previews  out/range_*.mp4, out/preview.mp4, out/qa_*.png, out/pass_*, out/share_check/, out/final_check/, out/kit/
  stills    notes/work/**, notes/stills/**, notes/review/** pictures and videos that NO scene reads
KEPT always: the master and share cuts (out/<name>*.mp4), assets/ (clips_in/ too), song/, notes/clips/, notes/ref/,
everything git tracks, and every file under notes/work/ that a scene, a lib or CREW.md mentions (painted-over frames,
hand-made mattes: they are runtime assets).
"""
import json
import os
import re
import shutil
import sys

MEDIA = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.mp4', '.mov', '.webm', '.wav', '.m4a', '.mp3', '.npz', '.npy')


def films_home():
    return os.environ.get('MV_FILMS') or os.path.join(os.path.expanduser('~'), 'music-videos')


def size_of(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    t = 0
    for r, _, fs in os.walk(p):
        for f in fs:
            try:
                t += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return t


def referenced(film):
    """every notes/... path fragment a scene, a lib or the crew notes mention: those files are runtime assets"""
    refs = set()
    srcs = []
    for d in ('web', 'render', 'tools'):
        for r, dirs, fs in os.walk(os.path.join(film, d)):
            dirs[:] = [x for x in dirs if x not in ('node_modules', '__pycache__', '.venv', '.sepvenv')]
            srcs += [os.path.join(r, f) for f in fs if f.endswith(('.js', '.mjs', '.py', '.html', '.sh'))]
    srcs += [os.path.join(film, 'notes', f) for f in ('CREW.md',) if os.path.exists(os.path.join(film, 'notes', f))]
    for p in srcs:
        try:
            s = open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for m in re.finditer(r'notes/(?:work|stills|review)/[A-Za-z0-9_./{}$*-]+', s):
            frag = re.split(r'[{$*]', m.group(0))[0].rstrip('/._-')
            if frag.count('/') >= 2:                       # at least notes/work/<something>
                refs.add(frag)
    return refs


def plan(film):
    out = {'chunks': [], 'previews': [], 'stills': []}
    o = os.path.join(film, 'out')
    if os.path.isdir(o):
        for f in os.listdir(o):
            p = os.path.join(o, f)
            if f.startswith('chunks-'):
                out['chunks'].append(p)
            elif (f.startswith(('range_', 'qa_', 'pass_')) or f == 'preview.mp4' or f in ('share_check', 'final_check', 'kit')
                  or f.endswith('.log')):
                out['previews'].append(p)
    refs = referenced(film)
    for d in ('notes/work', 'notes/stills', 'notes/review'):
        top = os.path.join(film, d)
        for r, dirs, fs in os.walk(top):
            for f in fs:
                if not f.lower().endswith(MEDIA):
                    continue
                p = os.path.join(r, f)
                rel = os.path.relpath(p, film).replace(os.sep, '/')
                if any(rel.startswith(x) for x in refs):
                    continue
                out['stills'].append(p)
    return out, refs


def restore(q):
    man = json.load(open(os.path.join(q, 'manifest.json'), encoding='utf-8'))
    n = 0
    for src, dst in reversed(man):
        if os.path.exists(dst) and not os.path.exists(src):
            os.makedirs(os.path.dirname(src), exist_ok=True)
            os.replace(dst, src)
            n += 1
    print(f'restored {n} of {len(man)} entries from {q}')


def main():
    argv = sys.argv[1:]
    val = lambda k: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else None
    if '--restore' in argv:
        return restore(val('--restore'))
    q = val('--quarantine')
    root = val('--root') or films_home()
    args = [a for a in argv if not a.startswith('--') and a not in (q, root)]
    films = [os.path.join(root, a) for a in args] or ([os.path.join(root, d) for d in sorted(os.listdir(root))
                                                      if os.path.isdir(os.path.join(root, d, 'out'))]
                                                     if os.path.isdir(root) else [])
    if not films:
        sys.exit(f'no films given, and none with an out/ folder in {root}')
    delete = '--delete' in argv
    moved = []
    grand = {}
    try:
        for film in films:
            film = os.path.abspath(film)
            p, refs = plan(film)
            sizes = {k: sum(size_of(x) for x in v) for k, v in p.items()}
            for k, v in sizes.items():
                grand[k] = grand.get(k, 0) + v
            kept = f'  (kept as runtime: {", ".join(sorted(refs))[:160]})' if refs else ''
            print(f"{os.path.basename(film):28s} chunks {sizes['chunks'] / 1e9:5.2f} GB  previews {sizes['previews'] / 1e9:5.2f} GB  "
                  f"stills {sizes['stills'] / 1e9:5.2f} GB ({len(p['stills'])} files){kept}")
            if '--list' in argv:
                for k, v in p.items():
                    for x in v:
                        print(f'   {k:8s} {x}')
            if q:
                for k, v in p.items():
                    for x in v:
                        dst = os.path.join(os.path.abspath(q), os.path.basename(film), os.path.relpath(x, film))
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        os.replace(x, dst)
                        moved.append((x, dst))
                print(f'   moved aside -> {q}')
            elif delete:
                for k, v in p.items():
                    for x in v:
                        if os.path.isdir(x):
                            shutil.rmtree(x, ignore_errors=True)
                        elif os.path.exists(x):
                            os.remove(x)
                print('   deleted')
    finally:
        if q:                                       # always: a move that stops halfway can still be put back
            os.makedirs(q, exist_ok=True)
            mp = os.path.join(q, 'manifest.json')
            before = json.load(open(mp, encoding='utf-8')) if os.path.exists(mp) else []   # an earlier sweep into q
            json.dump(before + moved, open(mp, 'w', encoding='utf-8'), indent=0)
    print(f"\nTOTAL  chunks {grand.get('chunks', 0) / 1e9:.1f} GB  previews {grand.get('previews', 0) / 1e9:.1f} GB  "
          f"stills {grand.get('stills', 0) / 1e9:.1f} GB  = {sum(grand.values()) / 1e9:.1f} GB"
          + ('' if (delete or q) else '   (dry run: nothing touched)'))


if __name__ == '__main__':
    main()
