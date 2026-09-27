#!/usr/bin/env python
"""setup.py -- install the kit's runtimes, once per machine. Safe to re-run: it skips whatever is already done.

    python setup.py              everything below
    python setup.py --check      only report what's installed and what's missing (changes nothing)
    python setup.py --whisper    also faster-whisper (word timings from the vocals; optional)
    python setup.py --no-stems   skip the Demucs env (torch, ~1 GB): song/separate.py won't work without it
    python setup.py --force      rebuild the Python envs from scratch
    python setup.py --uv         install the Python packages with uv instead of pip (faster, if you have uv)

It needs, first (it tells you how to get each one):
    Python 3.10-3.13 (the python that runs this), Node.js >= 22.12 with npm, ffmpeg + ffprobe (with libx264), git
It makes, all inside this kit/ folder (delete env/, node_modules/ or fonts/ to redo one):
    node_modules/   puppeteer (a headless Chrome: the renderer) + roughjs
    env/py/         numpy, pillow, opencv, librosa, soundfile, scipy, scikit-image, rembg + onnxruntime, yt-dlp
    env/sep/        demucs + torch (CPU): splits the song into drums / bass / other / vocals
    fonts/          30 Google Fonts families (SIL Open Font License / Apache 2.0), from fonts.googleapis.com
    machine.json    this machine's own settings (a local A1111/Forge address, an upscaler); never shared
and fetches the models ahead of first use: rembg isnet-anime (~170 MB), Demucs htdemucs (~80 MB).
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request

KIT = os.path.dirname(os.path.abspath(__file__))
WIN = os.name == 'nt'
MAC = sys.platform == 'darwin'
NODE_MIN = (22, 12)

# the fonts web/index.html loads: (family, css2 axes or None, [(style, weight, file)])
FONTS = [
    ('Dela Gothic One', None, [('normal', 400, 'DelaGothicOne-Regular.ttf')]),
    ('Anton', None, [('normal', 400, 'Anton-Regular.ttf')]),
    ('Caveat Brush', None, [('normal', 400, 'CaveatBrush-Regular.ttf')]),
    ('Permanent Marker', None, [('normal', 400, 'PermanentMarker-Regular.ttf')]),
    ('Reenie Beanie', None, [('normal', 400, 'ReenieBeanie-Regular.ttf')]),
    ('Space Mono', 'wght@400;700', [('normal', 400, 'SpaceMono-Regular.ttf'), ('normal', 700, 'SpaceMono-Bold.ttf')]),
    ('DM Serif Display', 'ital@0;1', [('normal', 400, 'DMSerifDisplay-Regular.ttf'),
                                      ('italic', 400, 'DMSerifDisplay-Italic.ttf')]),
    ('Mochiy Pop One', None, [('normal', 400, 'MochiyPopOne-Regular.ttf')]),
    ('Ma Shan Zheng', None, [('normal', 400, 'MaShanZheng-Regular.ttf')]),
    ('Rubik Mono One', None, [('normal', 400, 'RubikMonoOne-Regular.ttf')]),
    ('Bungee', None, [('normal', 400, 'Bungee-Regular.ttf')]),
    ('Shrikhand', None, [('normal', 400, 'Shrikhand-Regular.ttf')]),
    ('Pacifico', None, [('normal', 400, 'Pacifico-Regular.ttf')]),
    ('Caprasimo', None, [('normal', 400, 'Caprasimo-Regular.ttf')]),
    ('Monoton', None, [('normal', 400, 'Monoton-Regular.ttf')]),
    ('Rock Salt', None, [('normal', 400, 'RockSalt-Regular.ttf')]),
    ('Special Elite', None, [('normal', 400, 'SpecialElite-Regular.ttf')]),
    ('Fontdiner Swanky', None, [('normal', 400, 'FontdinerSwanky-Regular.ttf')]),
    ('Yellowtail', None, [('normal', 400, 'Yellowtail-Regular.ttf')]),
    ('Righteous', None, [('normal', 400, 'Righteous-Regular.ttf')]),
    ('Limelight', None, [('normal', 400, 'Limelight-Regular.ttf')]),
    ('Knewave', None, [('normal', 400, 'Knewave-Regular.ttf')]),
    ('DotGothic16', None, [('normal', 400, 'DotGothic16-Regular.ttf')]),
    ('Shippori Mincho B1', 'wght@800', [('normal', 800, 'ShipporiMinchoB1-ExtraBold.ttf')]),
    ('VT323', None, [('normal', 400, 'VT323-Regular.ttf')]),
    ('Rampart One', None, [('normal', 400, 'RampartOne-Regular.ttf')]),
    ('Courier Prime', 'wght@400;700', [('normal', 400, 'CourierPrime-Regular.ttf'),
                                       ('normal', 700, 'CourierPrime-Bold.ttf')]),
    ('IM Fell English', 'ital@0;1', [('normal', 400, 'IMFellEnglish-Regular.ttf'),
                                     ('italic', 400, 'IMFellEnglish-Italic.ttf')]),
    ('Playfair Display SC', None, [('normal', 400, 'PlayfairDisplaySC-Regular.ttf')]),
    ('Graduate', None, [('normal', 400, 'Graduate-Regular.ttf')]),
]

PY_IMPORTS = ['numpy', 'PIL', 'cv2', 'librosa', 'soundfile', 'scipy', 'skimage', 'rembg', 'onnxruntime']
SEP_IMPORTS = ['torch', 'demucs.apply', 'demucs.pretrained', 'soundfile', 'julius']


def say(msg=''):
    print(msg, flush=True)


def run(cmd, cwd=None, check=True, quiet=False):
    if not quiet:
        say('  $ ' + ' '.join(str(c) for c in cmd))
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, text=True,
                       capture_output=quiet)
    if check and r.returncode:
        raise SystemExit(f'failed ({r.returncode}): {" ".join(str(c) for c in cmd)}'
                         + (('\n' + (r.stderr or '')[-1500:]) if quiet else ''))
    return r


def out_of(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (r.stdout or '') + (r.stderr or '')
    except (OSError, subprocess.TimeoutExpired):
        return ''


def hint(what):
    h = {
        'node': {'win': 'winget install OpenJS.NodeJS.LTS', 'mac': 'brew install node',
                 'linux': 'install Node 22+ from nodejs.org or with nvm (distro packages are often too old)'},
        'ffmpeg': {'win': 'winget install Gyan.FFmpeg', 'mac': 'brew install ffmpeg', 'linux': 'sudo apt install ffmpeg'},
        'git': {'win': 'winget install Git.Git', 'mac': 'xcode-select --install  (or: brew install git)',
                'linux': 'sudo apt install git'},
        'python': {'win': 'winget install Python.Python.3.12', 'mac': 'brew install python@3.12',
                   'linux': 'sudo apt install python3.12 python3.12-venv'},
    }[what]
    return h['win' if WIN else 'mac' if MAC else 'linux'] + '   (then open a NEW terminal so PATH updates)'


# ------------------------------------------------------------------ checks
def node_version():
    s = out_of(['node', '--version']).strip()
    m = re.match(r'v(\d+)\.(\d+)', s)
    return (int(m.group(1)), int(m.group(2))) if m else None


def venv_python(name):
    return os.path.join(KIT, 'env', name, 'Scripts' if WIN else 'bin', 'python.exe' if WIN else 'python')


def imports_ok(py, mods):
    if not os.path.isfile(py):
        return False, 'not installed'
    code = 'import importlib, sys\nbad = []\n' \
           f'for m in {mods!r}:\n' \
           '    try:\n        importlib.import_module(m)\n    except Exception as e:\n        bad.append(f"{m}: {e}")\n' \
           'print("; ".join(bad) or "ok")'
    for attempt in range(2):     # a first import compiles numba caches; two processes at once can collide: retry once
        r = subprocess.run([py, '-c', code], capture_output=True, text=True)
        msg = (r.stdout or r.stderr).strip().splitlines()[-1:] or ['?']
        if msg[0] == 'ok':
            break
    return msg[0] == 'ok', msg[0]


def fonts_missing():
    d = os.path.join(KIT, 'fonts')
    return [f for _, _, files in FONTS for _, _, f in files if not os.path.isfile(os.path.join(d, f))]


def chrome_check():
    """launch the renderer's own browser (render/browser.mjs) and ask for WebGL2: the engine needs it."""
    js = ("import { launch } from './template/render/browser.mjs';\n"
          "const b = await launch(); const p = await b.newPage();\n"
          "const r = await p.evaluate(() => { const c = document.createElement('canvas'); const gl = c.getContext('webgl2');"
          " if (!gl) return null; const d = gl.getExtension('WEBGL_debug_renderer_info');"
          " return (d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)); });\n"
          "console.log('WEBGL2 ' + r); await b.close();\n")
    tmp = os.path.join(KIT, '_webgl_check.mjs')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(js)
    try:
        r = subprocess.run(['node', tmp], cwd=KIT, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return False, 'timed out launching Chrome'
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    s = (r.stdout + r.stderr).strip()
    m = re.search(r'WEBGL2 (.+)', s)
    if m and m.group(1) != 'null':
        return True, m.group(1)
    return False, (s.splitlines() or ['no output'])[-1][:300]


def report():
    rows = []
    v = sys.version_info
    rows.append(('python', (3, 10) <= v[:2] < (3, 14), f'{platform.python_version()} ({sys.executable})',
                 hint('python')))
    nv = node_version()
    rows.append(('node >= 22.12', bool(nv and nv >= NODE_MIN), f'{nv[0]}.{nv[1]}' if nv else 'not found', hint('node')))
    rows.append(('npm', shutil.which('npm') is not None, shutil.which('npm') or 'not found', hint('node')))
    enc = out_of(['ffmpeg', '-hide_banner', '-encoders'])
    rows.append(('ffmpeg (libx264 + aac)', 'libx264' in enc and ' aac ' in enc,
                 shutil.which('ffmpeg') or 'not found', hint('ffmpeg')))
    rows.append(('ffprobe', shutil.which('ffprobe') is not None, shutil.which('ffprobe') or 'not found', hint('ffmpeg')))
    rows.append(('git (recommended)', shutil.which('git') is not None, shutil.which('git') or 'not found', hint('git')))
    rows.append(('node_modules (puppeteer)', os.path.isdir(os.path.join(KIT, 'node_modules', 'puppeteer')), '',
                 'python setup.py'))
    ok, msg = imports_ok(venv_python('py'), PY_IMPORTS)
    rows.append(('env/py', ok, msg, 'python setup.py'))
    ok, msg = imports_ok(venv_python('sep'), SEP_IMPORTS)
    rows.append(('env/sep (stems)', ok, msg, 'python setup.py'))
    ok, msg = imports_ok(venv_python('py'), ['faster_whisper'])
    rows.append(('faster-whisper (optional)', ok, msg, 'python setup.py --whisper'))
    miss = fonts_missing()
    rows.append(('fonts', not miss, f'{len(miss)} missing' if miss else 'all 34 files', 'python setup.py'))
    rows.append(('machine.json', os.path.isfile(os.path.join(KIT, 'machine.json')), '', 'python setup.py'))
    if os.path.isdir(os.path.join(KIT, 'node_modules', 'puppeteer')) and nv and nv >= NODE_MIN:
        ok, msg = chrome_check()
        fix = 'npx puppeteer browsers install chrome   (in the kit folder)'
        if not WIN and not MAC:
            fix += '; Linux may also need: sudo npx puppeteer browsers install chrome --install-deps'
        rows.append(('headless Chrome + WebGL2', ok, msg, fix))
    say()
    for name, ok, detail, fix in rows:
        mark = 'ok  ' if ok else 'MISS'
        say(f'  [{mark}] {name:28s} {detail}')
        if not ok:
            say(f'         -> {fix}')
    return all(ok for name, ok, _, _ in rows if 'optional' not in name and 'recommended' not in name)


# ------------------------------------------------------------------ installs
def ensure_prereqs():
    bad = []
    if not (3, 10) <= sys.version_info[:2] < (3, 14):
        bad.append(f'Python {platform.python_version()}: use 3.10-3.13 -> {hint("python")}')
    nv = node_version()
    if not nv or nv < NODE_MIN:
        bad.append(f'Node.js {"%d.%d" % nv if nv else "missing"}: need >= 22.12 -> {hint("node")}')
    if not shutil.which('npm'):
        bad.append(f'npm missing -> {hint("node")}')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        bad.append(f'ffmpeg/ffprobe missing -> {hint("ffmpeg")}')
    if bad:
        say('Install these first, then run setup.py again:')
        for b in bad:
            say('  - ' + b)
        sys.exit(1)
    if not shutil.which('git'):
        say(f'(git is missing: films will still work, but you lose their history -> {hint("git")})')


def npm_install():
    say('\n[1/5] node_modules: puppeteer + roughjs')
    npm = shutil.which('npm')
    if not os.path.isdir(os.path.join(KIT, 'node_modules', 'puppeteer')):
        run([npm, 'install', '--no-audit', '--no-fund'], cwd=KIT)
    else:
        say('  already there')
    # npm can skip puppeteer's own browser download: ask for it explicitly (a no-op when it's already cached)
    npx = shutil.which('npx')
    run([npx, 'puppeteer', 'browsers', 'install', 'chrome'], cwd=KIT)


USE_UV = False          # --uv: install with uv (faster) instead of pip


def installer(py):
    """the command that installs packages into the venv whose python is `py`"""
    uv = shutil.which('uv') if USE_UV else None
    if uv:
        return [uv, 'pip', 'install', '--python', py]
    if subprocess.run([py, '-m', 'pip', '--version'], capture_output=True).returncode:
        run([py, '-m', 'ensurepip', '--upgrade'])            # a venv made by uv has no pip of its own
    return [py, '-m', 'pip', 'install']


def make_venv(name, reqs, force=False, torch_cpu=False):
    env = os.path.join(KIT, 'env', name)
    py = venv_python(name)
    if force and os.path.isdir(env):
        shutil.rmtree(env)
    uv = shutil.which('uv') if USE_UV else None
    if not os.path.isfile(py):
        if uv:
            run([uv, 'venv', env, '--python', sys.executable])
        else:
            run([sys.executable, '-m', 'venv', env])
    pip = installer(py)
    if not uv:
        run(pip + ['--upgrade', 'pip', '-q'])
    if torch_cpu and not WIN and not MAC:
        # PyPI's Linux torch wheels carry CUDA (~2.5 GB); stem separation runs on the CPU anyway
        run(pip + ['--index-url', 'https://download.pytorch.org/whl/cpu', 'torch'])
    run(pip + ['-r', os.path.join(KIT, reqs)])


def fetch_family(d, family, axes, files):
    q = family.replace(' ', '+') + (':' + axes if axes else '')
    css = urllib.request.urlopen(f'https://fonts.googleapis.com/css2?family={q}', timeout=60).read().decode()
    faces = re.findall(r"@font-face\s*{[^}]*?font-style:\s*(\w+);[^}]*?font-weight:\s*(\d+);[^}]*?src:\s*url\(([^)]+)\)",
                       css)
    got = []
    for style, weight, fname in files:
        hit = [u for s, w, u in faces if s == style and int(w) == weight]
        if not hit:
            raise RuntimeError(f'no {family} {style} {weight} in the Google Fonts answer')
        data = urllib.request.urlopen(hit[0], timeout=120).read()
        with open(os.path.join(d, fname + '.part'), 'wb') as f:
            f.write(data)
        os.replace(os.path.join(d, fname + '.part'), os.path.join(d, fname))
        got.append(f'{fname}  {len(data) // 1024} KB')
    return got


def fetch_fonts():
    say('\n[4/5] fonts (Google Fonts)')
    from concurrent.futures import ThreadPoolExecutor
    d = os.path.join(KIT, 'fonts')
    os.makedirs(d, exist_ok=True)
    todo = [(fam, ax, files) for fam, ax, files in FONTS
            if not all(os.path.isfile(os.path.join(d, f)) for _, _, f in files)]
    bad = []
    with ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(fetch_family, d, *t): t[0] for t in todo}
        for fu, fam in futs.items():
            try:
                for line in fu.result():
                    say('  ' + line)
            except Exception as e:
                bad.append(f'{fam}: {e}')
    if bad:
        raise SystemExit('fonts failed (rerun setup.py to retry):\n  ' + '\n  '.join(bad))
    with open(os.path.join(d, 'LICENSES.txt'), 'w', encoding='utf-8') as f:
        f.write('These fonts come from Google Fonts (https://fonts.google.com), under the SIL Open Font License 1.1 or\n'
                'the Apache License 2.0 (each family\'s page lists its licence). setup.py downloads them; they are\n'
                'free to use in videos. Families: ' + ', '.join(fam for fam, _, _ in FONTS) + '\n')
    say('  fonts ready')


def warm_models(stems):
    say('\n[5/5] models (downloaded once, before the first film needs them)')
    r = run([venv_python('py'), '-c', "from rembg import new_session; new_session('isnet-anime'); print('rembg isnet-anime ok')"],
            check=False)
    if r.returncode:
        say('  (rembg model download failed: it will retry on the first cut-out)')
    if stems:
        r = run([venv_python('sep'), '-c', "from demucs.pretrained import get_model; get_model('htdemucs'); print('demucs htdemucs ok')"],
                check=False)
        if r.returncode:
            say('  (Demucs model download failed: it will retry on the first song/separate.py)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--whisper', action='store_true')
    ap.add_argument('--no-stems', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--uv', action='store_true', help='install with uv instead of pip (faster)')
    a = ap.parse_args()
    global USE_UV
    USE_UV = a.uv
    if a.check:
        sys.exit(0 if report() else 1)
    ensure_prereqs()
    npm_install()
    say('\n[2/5] env/py (pictures, song analysis)')
    make_venv('py', 'requirements-py.txt', a.force)
    if a.whisper:
        say('\n[2b] faster-whisper (optional)')
        r = run(installer(venv_python('py')) + ['-r', os.path.join(KIT, 'requirements-whisper.txt')], check=False)
        if r.returncode:
            say('  (faster-whisper did not install: word timings are optional, everything else still works)')
    if a.no_stems:
        say('\n[3/5] env/sep skipped (--no-stems)')
    else:
        say('\n[3/5] env/sep (Demucs stems, CPU)')
        make_venv('sep', 'requirements-sep.txt', a.force, torch_cpu=True)
    fetch_fonts()
    mj = os.path.join(KIT, 'machine.json')
    if not os.path.isfile(mj):
        with open(mj, 'w', encoding='utf-8') as f:
            json.dump({'a1111': 'http://127.0.0.1:7860', 'upscale_python': '', 'upscale_models': ''}, f, indent=2)
            f.write('\n')
    warm_models(not a.no_stems)
    say('\nChecking everything:')
    ok = report()
    say('\n' + ('READY. Start a film:  python ' + os.path.join(KIT, 'new_film.py').replace(os.sep, '/')
                + ' <name> --title "TITLE"' if ok else 'Some pieces are missing (see above).'))


if __name__ == '__main__':
    main()
