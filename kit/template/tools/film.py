#!/usr/bin/env python
"""film.py -- this film's settings (film.json at the film root), plus where the kit and its runtimes live.

    from film import FILM, ROOT, KIT, PY, SEP, MACHINE, get     # in a tool (tools/ is on sys.path for tools/x.py)
    python tools/film.py name                                   # one value for a shell script
    python tools/film.py share.targetMiB                        # dotted keys reach into blocks

film.json is the ONE place a film's name, output files, clip lists, whole (never cut out) pictures, poster time and
share sizes live. Every tool reads it; no tool hardcodes a film's name. Tools copied from one film to another without
this file once read the OLD film's clip list: configure, don't copy.

The runtimes (Python venvs, node_modules, fonts) live in the kit, never in a film:
  PY   = <kit>/env/py   numpy, PIL, cv2, librosa, soundfile, rembg (cut-outs), yt-dlp, (faster-whisper if installed)
  SEP  = <kit>/env/sep  demucs + torch (CPU): stem separation
The kit is found from film.json "kit" (new_film.py writes it), else the MV_KIT environment variable, else the
default skill location (~/.claude/skills/music-video/kit).
MACHINE = <kit>/machine.json: this machine's own settings (never committed): e.g. {"a1111": "http://127.0.0.1:7860",
"upscale_python": "<a python with torch + spandrel>", "upscale_models": "<folder with realesr-animevideov3.pth>"}.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(os.sep, '/')
with open(os.path.join(ROOT, 'film.json'), encoding='utf-8') as _f:
    FILM = json.load(_f)


def _find_kit():
    for k in (FILM.get('kit'), os.environ.get('MV_KIT'),
              os.path.join(os.path.expanduser('~'), '.claude', 'skills', 'music-video', 'kit')):
        if k and os.path.isfile(os.path.join(k, 'new_film.py')):
            return os.path.abspath(k).replace(os.sep, '/')
    return (FILM.get('kit') or '').replace(os.sep, '/')


KIT = _find_kit()


def venv_python(name):
    """the python of a kit venv (Windows keeps it in Scripts/python.exe, macOS/Linux in bin/python)."""
    if os.name == 'nt':
        return f'{KIT}/env/{name}/Scripts/python.exe'
    return f'{KIT}/env/{name}/bin/python'


PY = venv_python('py')
SEP = venv_python('sep')

MACHINE = {}
_mj = os.path.join(KIT, 'machine.json') if KIT else ''
if _mj and os.path.isfile(_mj):
    with open(_mj, encoding='utf-8') as _f:
        MACHINE = json.load(_f)


def get(key, default=None):
    v = FILM
    for k in key.split('.'):
        if not isinstance(v, dict) or k not in v:
            return default
        v = v[k]
    return v


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if sys.argv[1] in ('PY', 'SEP', 'KIT'):
        print({'PY': PY, 'SEP': SEP, 'KIT': KIT}[sys.argv[1]])
        sys.exit()
    v = get(sys.argv[1])
    if v is None:
        sys.exit(f'film.json has no {sys.argv[1]!r}')
    print(' '.join(map(str, v)) if isinstance(v, list) else v)
