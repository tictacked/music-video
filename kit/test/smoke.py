#!/usr/bin/env python
"""smoke.py -- prove the kit works on this machine, end to end, with a made-up song, pictures, clip and roleplay.

    python <kit>/test/smoke.py          # 3-8 minutes; works in <kit>/test/work/ (emptied first, kept afterwards)
    python <kit>/test/smoke.py --quick  # skip the full render and the share cuts (about 1-2 minutes)

Every step prints PASS, WARN or FAIL, and the exit code is the number of FAILs. The steps:
  1. setup.py --check passes
  2. new_film.py scaffolds a film
  3. a synthetic song -> separate.py -> analyze.py -> timing.py (about 120 BPM; the silence at 12-14 s is found)
  4. rp2txt.py on a made-up SillyTavern folder (the chat, the card with its lorebook, a world, the persona)
  5. pictures: assets.py -> promptsheet.py -> intake.py (a NovelAI-style PNG files itself by the prompt inside it) ->
     cutout.py (a transparent picture keeps its alpha; a figure on mint goes through rembg)
  6. a clip: clips_in.py (24 fps frames + clips.js)
  7. the smoke reel (every layer once): stills, a strict full render, share.py, final_check.py
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.dirname(KIT)
WORK = os.path.join(KIT, 'test', 'work')
FILM = os.path.join(WORK, 'smoke')
WIN = os.name == 'nt'
PY = os.path.join(KIT, 'env', 'py', 'Scripts' if WIN else 'bin', 'python.exe' if WIN else 'python')
SEP = os.path.join(KIT, 'env', 'sep', 'Scripts' if WIN else 'bin', 'python.exe' if WIN else 'python')
NODE = shutil.which('node') or 'node'
results = []


def run(cmd, cwd=FILM, timeout=1800):
    t = time.time()
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=timeout)
    out = (r.stdout or '') + (r.stderr or '')
    return r.returncode, out, time.time() - t


def report(step, ok, detail='', warn=False):
    tag = 'PASS' if ok else ('WARN' if warn else 'FAIL')
    results.append(tag)
    print(f'[{tag}] {step}' + (f': {detail}' if detail else ''), flush=True)
    return ok


def tail(out, n=6):
    return ' | '.join(l.strip() for l in out.strip().splitlines()[-n:])


def unlink_dir_link(p):
    """remove a symlink or (Windows) directory junction WITHOUT touching what it points at"""
    if os.path.islink(p):
        os.unlink(p)
    elif os.name == 'nt' and os.path.isdir(p) and getattr(os.path, 'isjunction', lambda _: False)(p):
        os.rmdir(p)                      # rmdir on a junction removes the junction only
    elif os.name == 'nt' and os.path.isdir(p):
        try:                             # Python < 3.12 has no isjunction: a junction's rmdir succeeds while it's
            os.rmdir(p)                  # non-empty, a real non-empty folder's rmdir fails (and is left alone)
        except OSError:
            pass


def clean(path):
    """delete a test folder: first every film's node_modules LINK (never the kit's modules behind it), then the rest,
    making read-only files (git's objects) writable on the way"""
    if not os.path.isdir(path):
        return
    for d in os.listdir(path):
        unlink_dir_link(os.path.join(path, d, 'node_modules'))

    def onerror(func, p, exc):
        import stat
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    shutil.rmtree(path, onerror=onerror)


def main():
    quick = '--quick' in sys.argv
    print(f'kit: {KIT}\nwork: {WORK}\n', flush=True)
    code, out, _ = run([sys.executable, os.path.join(KIT, 'setup.py'), '--check'], cwd=KIT)
    if not report('1 setup.py --check', code == 0, '' if code == 0 else tail(out, 12)):
        print('\nRun setup.py first (it says what is missing).')
        sys.exit(1)

    clean(WORK)
    if os.path.isdir(WORK):
        sys.exit(f'could not empty {WORK} (a program may have a file open there): close it and rerun')
    os.makedirs(WORK)
    code, out, _ = run([sys.executable, os.path.join(KIT, 'new_film.py'), 'smoke', '--title', 'SMOKE TEST',
                        '--song', 'Test Tones -- the kit (demo)', '--dest', WORK], cwd=KIT)
    if not report('2 new_film.py', code == 0 and os.path.isfile(os.path.join(FILM, 'film.json')), tail(out, 3)):
        sys.exit(len([r for r in results if r == 'FAIL']))

    # 3. the song
    code, out, _ = run([PY, os.path.join(KIT, 'test', 'fixtures.py'), 'song', FILM])
    ok = code == 0
    code2, out2, _ = run(['ffmpeg', '-v', 'error', '-y', '-i', 'song/audio.wav', '-c:a', 'aac', '-b:a', '192k',
                          'song/audio.m4a'])
    report('3a the synthetic song', ok and code2 == 0, tail(out + out2, 2))
    code, out, dt = run([SEP, 'song/separate.py'])
    report('3b separate.py (Demucs)', code == 0 and os.path.isfile(os.path.join(FILM, 'song', 'stems', 'vocals.wav')),
           f'{dt:.0f} s' if code == 0 else tail(out))
    code, out, _ = run([PY, 'song/analyze.py'])
    report('3c analyze.py', code == 0, '' if code == 0 else tail(out))
    code, out, _ = run([PY, 'song/timing.py'])
    ok = code == 0
    detail = tail(out)
    if ok:
        T = json.load(open(os.path.join(FILM, 'song', 'timing.json'), encoding='utf-8'))
        stop_found = any(11.4 <= a <= 12.6 for a, b in json.load(open(os.path.join(FILM, 'song', 'reading.json'),
                                                                        encoding='utf-8')).get('stops', []))
        ok = 118 <= T['bpm'] <= 122 and 23 <= T['duration'] <= 25
        detail = f"{T['bpm']:.2f} BPM, {T['duration']} s, {len(T['kicks'])} kicks, the stop at 12 s " + \
                 ('found' if stop_found else 'NOT found by analyze.py')
        if ok and not stop_found:
            report('3d timing.py', False, detail, warn=True)
        else:
            report('3d timing.py', ok, detail)
    else:
        report('3d timing.py', False, detail)

    # 4. the roleplay
    st = os.path.join(WORK, 'st')
    run([PY, os.path.join(KIT, 'test', 'fixtures.py'), 'st', st])
    code, out, _ = run([sys.executable, os.path.join(SKILL, 'rp2txt.py'), '--st', os.path.join(st, 'SillyTavern'),
                        '--find', 'aria'])
    report('4a rp2txt.py --find', code == 0 and '1 chat(s)' in out, tail(out, 1))
    chat = os.path.join(st, 'SillyTavern', 'data', 'default-user', 'chats', 'Aria', 'Aria - 2020-01-01@12h00m00s.jsonl')
    code, out, _ = run([sys.executable, os.path.join(SKILL, 'rp2txt.py'), '--st', os.path.join(st, 'SillyTavern'), chat,
                        '--out', 'notes/chat.txt', '--card', 'Aria', '--world', 'Coast'])
    ok = code == 0
    if ok:
        c = open(os.path.join(FILM, 'notes', 'chat.txt'), encoding='utf-8').read()
        m = open(os.path.join(FILM, 'notes', 'card.md'), encoding='utf-8').read()
        ok = ('##### [5] Wren (user)' in c and 'an unused swipe' not in c and 'test-author' in m
              and 'Lorebook: embedded' in m and 'Harbor' in m and 'Persona: Wren' in m)
    report('4b rp2txt.py chat + card + world + persona', ok, tail(out, 2))

    # 5. pictures
    code, out, _ = run([sys.executable, 'tools/assets.py'])
    report('5a assets.py', code == 0 and os.path.isfile(os.path.join(FILM, 'tools', 'jobs', 'cast.json')), tail(out, 1))
    code, out, _ = run([sys.executable, 'tools/promptsheet.py'])
    report('5b promptsheet.py', code == 0 and os.path.isfile(os.path.join(FILM, 'notes', 'prompts.html')), tail(out, 2))
    run([PY, os.path.join(KIT, 'test', 'fixtures.py'), 'pictures', FILM])
    code, out, _ = run([PY, 'tools/intake.py'])
    side = os.path.join(FILM, 'assets', 'gen', 'hero_full', '1.json')
    ok = code == 0 and os.path.isfile(side) and json.load(open(side, encoding='utf-8')).get('generator') == 'novelai'
    stray_left = os.path.isfile(os.path.join(FILM, 'assets', 'inbox', 'stray.png'))
    report('5c intake.py (files by the prompt inside; leaves the stray)', ok and stray_left and 'UNMATCHED' in out,
           tail(out, 4))
    code, out, dt = run([PY, 'tools/cutout.py'])
    ok = code == 0
    detail = tail(out, 3)
    if ok:
        from_alpha = alpha_share(os.path.join(FILM, 'assets', 'cut', 'hero_full', '1.png'))
        mint_alpha = alpha_share(os.path.join(FILM, 'assets', 'cut', 'hero_mint', '1.png'))
        man = open(os.path.join(FILM, 'assets', 'manifest.js'), encoding='utf-8').read()
        ok = from_alpha is not None and 0.1 < from_alpha < 0.6 and 'hero_full/1' in man and 'pl_room/1' in man
        detail = f'transparent picture kept {from_alpha} opaque; ' + (
            f'rembg on mint: {mint_alpha} opaque' if mint_alpha is not None else 'rembg made no cut-out')
        report('5d cutout.py', ok, detail)
        report('5e rembg on a crude drawn figure', mint_alpha is not None and 0.05 < mint_alpha < 0.7,
               'a real anime picture cuts far better than this test drawing', warn=True)
    else:
        report('5d cutout.py', False, detail)

    # 6. a clip
    os.makedirs(os.path.join(FILM, 'assets', 'clips_in'), exist_ok=True)
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=1280x720:rate=30', '-t', '3',
         '-pix_fmt', 'yuv420p', 'assets/clips_in/test.mp4'])
    code, out, _ = run([PY, 'tools/clips_in.py'])
    cj = os.path.join(FILM, 'assets', 'clips', 'clips.js')
    ok = code == 0 and os.path.isfile(cj) and '"test"' in open(cj, encoding='utf-8').read()
    n = len([f for f in os.listdir(os.path.join(FILM, 'assets', 'clips', 'test')) if f.endswith('.jpg')]) if ok else 0
    report('6 clips_in.py', ok and n == 72, f'{n} frames (3 s at 30 fps -> 72 at 24 fps)')

    # 7. the smoke reel
    shutil.copy(os.path.join(KIT, 'test', 'smoke_reel.js'), os.path.join(FILM, 'web', 'scenes', 'reel1.js'))
    code, out, dt = run([NODE, 'render/stills.mjs', '--times', '1,3,5.2,9,13,15,19', '--sheet', '--label',
                         '--out', 'notes/work/smoke'])
    bad = [l for l in out.splitlines() if 'pageerror' in l or 'failed' in l.lower()]
    stills = sorted(glob.glob(os.path.join(FILM, 'notes', 'work', 'smoke', 'f*.png')))
    st = picture_stats(stills) if stills else []
    flat = [os.path.basename(p) for p, s in zip(stills, st) if s[1] < 6]
    ok = code == 0 and not bad and len(st) == 7 and not flat
    report('7a stills of every layer (and not blank)', ok,
           f'{dt:.0f} s -> notes/work/smoke/sheet.png' if ok else (f'BLANK stills: {flat}' if flat else tail(out, 8)))
    code, out, dt = run([NODE, 'render/check_assets.mjs', '0', '200'])
    report('7b check_assets.mjs (frames 0-200)', code == 0 and 'undeclared: none' in out and 'page messages: none' in out,
           tail(out, 4))
    if quick:
        print('\n(--quick: skipping the full render, the share cuts and the final check)')
    else:
        code, out, dt = run([NODE, 'render/render.mjs', '--workers', '2'])
        ok = code == 0 and os.path.isfile(os.path.join(FILM, 'out', 'smoke.mp4'))
        detail = f'{dt:.0f} s' if ok else tail(out, 8)
        if ok:                               # look at the master's pixels: a lost WebGL context renders black frames
            grabs = []
            for t in (1, 5, 9, 13, 19):
                g = os.path.join(FILM, 'notes', 'work', f'master_{t}.png')
                run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', 'out/smoke.mp4', '-frames:v', '1', g])
                grabs.append(g)
            st = picture_stats(grabs)
            flat = [t for t, s in zip((1, 5, 9, 13, 19), st) if s[1] < 6]
            ok = len(st) == 5 and not flat
            detail += ', frames look ' + ('alive' if ok else f'BLANK at {flat} s')
        if 'SwiftShader' in out:
            detail += ' (software WebGL: no usable GPU)'
        report('7c strict full render (and not blank)', ok, detail)
        code, out, dt = run([sys.executable, 'render/share.py'])
        report('7d share.py', code == 0, tail(out, 4))
        code, out, dt = run([PY, 'render/final_check.py'])
        fails = [l for l in out.splitlines() if l.strip().startswith('FAIL')]
        report('7e final_check.py', code == 0 and not fails, tail(out, 12) if fails or code else f'{len(out.splitlines())} lines, no FAIL')

    n_fail = len([r for r in results if r == 'FAIL'])
    n_warn = len([r for r in results if r == 'WARN'])
    print(f'\n{len(results) - n_fail - n_warn} passed, {n_warn} warnings, {n_fail} failed. The test film: {FILM}')
    sys.exit(n_fail)


def picture_stats(paths):
    """[(mean, std)] of each picture's grey levels (a blank render is flat: std ~0)"""
    code, out, _ = run([PY, '-c', 'import sys; from PIL import Image; import numpy as np\n'
                        'for p in sys.argv[1:]:\n'
                        '    a = np.asarray(Image.open(p).convert("L"), dtype=np.float32)\n'
                        '    print(round(float(a.mean()), 1), round(float(a.std()), 1))'] + list(paths))
    try:
        return [tuple(float(x) for x in l.split()) for l in out.strip().splitlines()[-len(paths):]]
    except ValueError:
        return []


def alpha_share(path):
    """the share of a cut-out's pixels that are opaque (alpha > 128), or None if there's no cut-out"""
    if not os.path.isfile(path):
        return None
    code, out, _ = run([PY, '-c', 'import sys; from PIL import Image; import numpy as np; '
                        'a = np.asarray(Image.open(sys.argv[1]).convert("RGBA"))[..., 3]; print(round(float((a > 128).mean()), 3))',
                        path])
    try:
        return float(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


if __name__ == '__main__':
    main()
