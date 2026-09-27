#!/usr/bin/env python
"""new_film.py -- start a music video from the kit: a folder that renders on day one.

    python <kit>/new_film.py <name> --title "TITLE" [--song "Song -- Artist (year)"] [--bpm 120]
                             [--dest <folder of films>] [--port N] [--no-git]

<kit> is the kit/ folder of the music-video skill (usually ~/.claude/skills/music-video/kit).
Films go to --dest, else $MV_FILMS, else ~/music-videos.

1. copies template/ into <dest>/<name>/ (a COPY: the film owns its files from then on; a later kit change never
   touches a film that already exists, so every finished film stays reproducible)
2. writes film.json (name, title, song, a free port, where the kit is, which kit commit)
3. links node_modules -> the kit's (a junction on Windows, a symlink elsewhere) and copies the fonts
4. writes a placeholder song/timing.json + web/timing.js (12 s at the given BPM) so the testcard reel renders at
   once; song/timing.py replaces both once the real song is analysed
5. git init + a first commit (skipped with a note if git is missing or has no user configured)
Run setup.py once first (the runtimes and fonts). Then: the song, PLAN.md, STORYBOARD.md, the reels: the skill's
SKILL.md has the order of work.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

KIT = os.path.dirname(os.path.abspath(__file__)).replace(os.sep, '/')
TEMPLATE = KIT + '/template'
DOCS = ('README.md', 'PLAN.md', 'STORYBOARD.md', 'STYLE.md', 'notes/BRIEF.md', 'notes/SPAWN.md')


def default_dest():
    return (os.environ.get('MV_FILMS') or os.path.join(os.path.expanduser('~'), 'music-videos')).replace(os.sep, '/')


def git_ok():
    return shutil.which('git') is not None


def kit_commit():
    if not git_ok():
        return 'unknown'
    r = subprocess.run(['git', '-C', KIT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True)
    if r.returncode:
        return 'unknown'
    dirty = subprocess.run(['git', '-C', KIT, 'status', '--porcelain', '--', 'template'],
                           capture_output=True, text=True).stdout.strip()
    return r.stdout.strip() + ('+dirty' if dirty else '')


def free_port(dest):
    used = set()
    if os.path.isdir(dest):
        for d in os.listdir(dest):
            f = os.path.join(dest, d, 'film.json')
            if os.path.exists(f):
                try:
                    used.add(int(json.load(open(f, encoding='utf-8')).get('port', 0)))
                except (ValueError, OSError):
                    pass
    p = 8700
    while p in used:
        p += 1
    return p


def link_dir(target, link):
    """node_modules is shared: a directory junction on Windows (no admin needed), a symlink elsewhere."""
    if os.name == 'nt':
        import _winapi
        _winapi.CreateJunction(os.path.normpath(target), os.path.normpath(link))
    else:
        os.symlink(target, link, target_is_directory=True)


def placeholder_timing(song, bpm=120.0, dur=12.0):
    fps, P = 24, 60 / bpm
    n = int(dur * fps) + 2
    zeros = [0.0] * n
    beats = [round(i * P, 4) for i in range(int(dur / P) + 1)]
    return dict(song=song, duration=dur, bpm=bpm, beat0=0.0, barOffset=0, barLen=round(4 * P, 5),
                note='PLACEHOLDER from new_film.py: analyse the real song (song/separate.py, analyze.py, timing.py)',
                sections=[dict(i=0, name='all', bar=0, start=0.0, end=dur, story='placeholder')],
                beats=beats, kicks=beats[::2], snares=beats[1::2], accents=[[b, 1.0, 'd'] for b in beats[::4]],
                vox=[], stops=[], bars=[], lines=[],
                env=dict(fps=fps, rms=zeros, low=zeros, mid=zeros, high=zeros, onset=zeros, voc=zeros))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('name', help='lowercase letters, digits, - and _ (the folder and out/<name>.mp4)')
    ap.add_argument('--title', required=True)
    ap.add_argument('--song', default='')
    ap.add_argument('--dest', default=default_dest())
    ap.add_argument('--port', type=int)
    ap.add_argument('--bpm', type=float, default=120)
    ap.add_argument('--no-git', action='store_true')
    a = ap.parse_args()
    if not a.name.replace('-', '').replace('_', '').isalnum() or a.name != a.name.lower():
        sys.exit('name: lowercase letters, digits, - and _ (it becomes the folder and out/<name>.mp4)')
    if not os.path.isdir(KIT + '/node_modules/puppeteer'):
        sys.exit(f'the kit has no node_modules yet: run  python {KIT}/setup.py  first')
    fonts = KIT + '/fonts'
    if not os.path.isdir(fonts) or not any(f.endswith('.ttf') for f in os.listdir(fonts)):
        sys.exit(f'the kit has no fonts yet: run  python {KIT}/setup.py  first')
    dest = os.path.abspath(a.dest).replace(os.sep, '/')
    film = f'{dest}/{a.name}'
    if os.path.exists(film) and os.listdir(film):
        sys.exit(f'{film} exists and is not empty')
    os.makedirs(dest, exist_ok=True)
    port = a.port or free_port(dest)                 # before the copy: the template's own port isn't a film's

    shutil.copytree(TEMPLATE, film, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'node_modules'))
    fj = os.path.join(film, 'film.json')
    F = json.load(open(fj, encoding='utf-8'))
    F.update(name=a.name, title=a.title, song=a.song, port=port, bpmHint=a.bpm, kit=KIT, kitCommit=kit_commit())
    with open(fj, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(F, f, indent=2, ensure_ascii=False)
        f.write('\n')

    subs = {'{TITLE}': a.title, '{NAME}': a.name, '{SONG}': a.song or 'the song', '{PORT}': str(F['port']),
            '{DATE}': datetime.date.today().isoformat(), '{FILM_DIR}': film, '{KIT}': KIT}
    for rel in DOCS:
        p = os.path.join(film, rel)
        s = open(p, encoding='utf-8').read()
        for k, v in subs.items():
            s = s.replace(k, v)
        open(p, 'w', encoding='utf-8', newline='\n').write(s)

    link_dir(KIT + '/node_modules', film + '/node_modules')
    os.makedirs(film + '/assets/fonts', exist_ok=True)
    for f in os.listdir(fonts):
        if f.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
            shutil.copy2(f'{fonts}/{f}', f'{film}/assets/fonts/{f}')

    t = placeholder_timing(a.song, a.bpm)
    for d in ('song/private', 'source', 'assets/gen', 'assets/cut', 'assets/inbox', 'assets/clips', 'assets/clips_in',
              'notes/clips/ff', 'notes/work', 'notes/review', 'tools/jobs', 'out'):
        os.makedirs(os.path.join(film, d), exist_ok=True)
    json.dump(t, open(os.path.join(film, 'song', 'timing.json'), 'w', encoding='utf-8'))
    with open(os.path.join(film, 'web', 'timing.js'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('// PLACEHOLDER from new_film.py -- song/timing.py writes the real one (NO LYRICS: times only)\n')
        fh.write('window.DT_TIMING = ' + json.dumps(t) + ';\n')
    for f, body in (('assets/manifest.js', 'window.DT_ASSETS = {};\n'),
                    ('assets/clips/clips.js', 'window.DT_CLIPS = {};\nwindow.DT_CLIPA = {};\n')):
        p = os.path.join(film, f)
        if not os.path.exists(p):
            open(p, 'w', encoding='utf-8', newline='\n').write(body)

    if not a.no_git:
        if not git_ok():
            print('  (git not found: no repo made; install git and run  git init  in the film later)')
        else:
            subprocess.run(['git', 'init', '-q', film], check=True)
            subprocess.run(['git', '-C', film, 'config', 'core.autocrlf', 'false'], check=True)
            subprocess.run(['git', '-C', film, 'add', '-A'], check=True)
            r = subprocess.run(['git', '-C', film, 'commit', '-q', '-m', f'Scaffold {a.title} from the kit ({F["kitCommit"]})'],
                               capture_output=True, text=True)
            if r.returncode:
                print('  (git: the first commit failed -- usually no user.name/user.email set yet:')
                print('   git config --global user.name "..." ; git config --global user.email "..."  then commit)')
    print(f'{film}: scaffolded from the kit ({F["kitCommit"]}), port {F["port"]}')
    print(f'  look:   cd "{film}" && node render/serve.mjs   -> http://127.0.0.1:{F["port"]}/web/index.html')
    print('  next:   the song into song/ (audio.wav + audio.m4a), then song/separate.py, analyze.py, timing.py;')
    print('          PLAN.md and STORYBOARD.md (SKILL.md has the order of work)')


if __name__ == '__main__':
    main()
