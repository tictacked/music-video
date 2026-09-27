#!/usr/bin/env python
"""upscale.py -- image-to-video clips -> clean full-HD frames for the film, with an anime video upscaler.

    python tools/upscale.py run <model> <clip.mp4> [<clip.mp4> ...] [--size WxH]    # -> assets/clips/<name>/00000.jpg ...
    python tools/upscale.py raw [--model M] [--size WxH]    # every clip still on tools/rawframes.py's CPU frames (.raw)
    python tools/upscale.py picks [--model M] [--size WxH] [--force]    # every clip named in notes/clips/PICKS.txt
    python tools/upscale.py ab <clip.mp4> [--frame 60] [--out notes/work/ab.png] [--crop x,y,w,h]   # models side by side

Clips are read from assets/clips_in/<name>.mp4 (`raw`, `picks`) or from the paths given (`run`).

SETUP (once per machine). The upscaler needs torch + spandrel, which the kit's own venvs don't carry:
  1. a python with them:   pip install torch spandrel numpy pillow
     (for an NVIDIA GPU, install the CUDA build of torch: https://pytorch.org/get-started/locally/)
  2. the default model, realesr-animevideov3.pth (x4, Real-ESRGAN's anime VIDEO model), into a folder:
     https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth
     Optional, for `ab` and --model: the AnimeJaNai 2x Compact models (github.com/the-database/mpv-upscale-2x_animejanai):
     2x_AnimeJaNai_HD_V3_Compact.pth, 2x_AnimeJaNai_HD_V3Sharp1_Compact.pth, 2x_AnimeJaNai_SD_V1beta34_Compact.pth
     (SD_V1beta34 is made for SD sources, like most video-model output). Model names: animevideov3 (the default),
     janai_hd3, janai_hd3sharp, janai_sd.
  3. <kit>/machine.json:   "upscale_python": "<that python>",   "upscale_models": "<that folder>"
Then run this file with any python: it hands itself over to upscale_python. Without CUDA it runs on the CPU, many
times slower (it warns).

Every clip is resampled to 24 fps, exactly as tools/rawframes.py does, so the upscale overwrites rawframes' placeholder
frames in place: same names, same count. Frames are 5-digit JPGs from 00000 (the engine's 'clip:<name>/<frame>' key).
An x4 model's output is downsampled to --size (default 1920 wide, the clip's own aspect) so every clip lands at one
resolution. After an upscale the clip's .raw marker goes and assets/clips/clips.js is rebuilt.
film.json clipSkip = clips `raw` leaves alone: unused ones, and any whose CPU frames a painter has already drawn over
frame by frame (upscaling the base would no longer match the painted overlay)."""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from film import FILM, MACHINE, PY, ROOT  # noqa: E402

URL = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth'
MODELS = (MACHINE.get('upscale_models') or '').replace(os.sep, '/')
M = {
    'animevideov3': 'realesr-animevideov3.pth',
    'janai_hd3': '2x_AnimeJaNai_HD_V3_Compact.pth',
    'janai_hd3sharp': '2x_AnimeJaNai_HD_V3Sharp1_Compact.pth',
    'janai_sd': '2x_AnimeJaNai_SD_V1beta34_Compact.pth',
}
FPS = 24


def _torch_or_handover():
    """torch + spandrel here, or rerun this command with machine.json's upscale_python (which has them)."""
    try:
        import spandrel  # noqa: F401
        import torch  # noqa: F401
        return
    except ImportError:
        pass
    upy = MACHINE.get('upscale_python')
    if upy and os.path.isfile(upy) and os.path.realpath(upy) != os.path.realpath(sys.executable):
        sys.exit(subprocess.call([upy, os.path.abspath(sys.argv[0])] + sys.argv[1:]))
    sys.exit('the upscaler needs a python with torch + spandrel (pip install torch spandrel numpy pillow), named in '
             '<kit>/machine.json as "upscale_python"' + (f' (it says {upy!r}, which is not usable)' if upy else '') +
             '. See the top of tools/upscale.py.')


if __name__ == '__main__' and (len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help')):
    sys.exit(__doc__)
_torch_or_handover()
import numpy as np  # noqa: E402
import torch  # noqa: E402
from spandrel import ModelLoader  # noqa: E402

DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
_cache = {}


def model_path(name):
    return f'{MODELS}/{M[name]}' if MODELS else ''


def model(name):
    if name not in _cache:
        if name not in M:
            sys.exit(f'no model {name!r}: one of {", ".join(M)}')
        p = model_path(name)
        if not os.path.isfile(p):
            sys.exit(f'no model file {M[name]} in machine.json "upscale_models" ({MODELS or "not set"}).'
                     + (f'\n  Download it: {URL}' if name == 'animevideov3' else '  (see the top of tools/upscale.py)'))
        if DEV == 'cpu':
            print('WARNING: no CUDA GPU: upscaling on the CPU, which is SLOW (many times slower than a GPU; minutes '
                  'per clip). tools/rawframes.py frames already work in the film meanwhile.', file=sys.stderr, flush=True)
        d = ModelLoader().load_from_file(p)
        d.to(DEV).eval()
        half = DEV == 'cuda' and d.supports_half          # half precision on the GPU only
        if half:
            d.half()
        _cache[name] = (d, half)
    return _cache[name]


def probe(path):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames',
                                   '-show_entries', 'stream=width,height,nb_read_frames', '-of', 'csv=p=0', path]).decode()
    w, h, n = [int(x) for x in out.strip().split(',')[:3]]
    return w, h, n


def frames(path):
    w, h, n = probe(path)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'fps={FPS}', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                          '-'], stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.wait()


@torch.inference_mode()
def up(name, rgb, size=None):
    d, half = model(name)
    x = torch.from_numpy(rgb.copy()).to(DEV).permute(2, 0, 1)[None].float() / 255
    if half:
        x = x.half()
    y = d(x).clamp(0, 1)
    if size and (y.shape[-1], y.shape[-2]) != size:
        y = torch.nn.functional.interpolate(y.float(), size=(size[1], size[0]), mode='bicubic', antialias=True).clamp(0, 1)
    return (y[0].permute(1, 2, 0).float().cpu().numpy() * 255 + 0.5).astype(np.uint8)


def run(name, clip, size=None, q=2):
    base = os.path.splitext(os.path.basename(clip))[0]
    if not size:                                   # default: 1920 wide, the clip's own aspect (full-screen = 1:1)
        w, h, _ = probe(clip)
        size = (1920, round(1920 * h / w / 2) * 2)
    out = f'{ROOT}/assets/clips/{base}'
    os.makedirs(out, exist_ok=True)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}',
                            '-r', str(FPS), '-i', '-', '-q:v', str(q), '-start_number', '0', f'{out}/%05d.jpg'], stdin=subprocess.PIPE)
    t0, n = time.time(), 0
    for f in frames(clip):
        enc.stdin.write(up(name, f, size).tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    if enc.returncode or not n:
        print(f'{base}: FAILED ({n} frames decoded, encoder exit {enc.returncode})', flush=True)
        return 0
    for x in os.listdir(out):                      # frames past the new count (an older, longer take) would linger
        if x.endswith('.jpg') and x[:-4].isdigit() and int(x[:-4]) >= n:
            os.remove(f'{out}/{x}')
    if os.path.exists(f'{out}/.raw'):              # no longer placeholder frames
        os.remove(f'{out}/.raw')
    print(f'{base}: {n} frames -> {out} ({time.time() - t0:.1f} s, {name}, {DEV})', flush=True)
    return n


def clipsjs():
    py = PY if os.path.isfile(PY) else sys.executable        # clipsjs.py wants numpy + PIL: the kit's python has both
    subprocess.run([py, f'{HERE}/clipsjs.py'])


def ab(clip, k=60, out=None, crop=None):
    """one frame through every model that is present, at 1920 wide, side by side as crops of the middle (real size)"""
    from PIL import Image, ImageDraw, ImageFont
    if not any(os.path.isfile(model_path(n)) for n in M):
        model('animevideov3')                      # no model at all: exits with where to get one
    f = None
    for i, fr in enumerate(frames(clip)):
        if i == k:
            f = fr
            break
    if f is None:
        sys.exit('frame out of range')
    tw, th = 1920, round(1920 * f.shape[0] / f.shape[1])
    tiles = [('bicubic (what the browser would do)', np.asarray(Image.fromarray(f).resize((tw, th), Image.BICUBIC)))]
    for name in M:
        if not os.path.isfile(model_path(name)):
            continue
        t0 = time.time()
        y = up(name, f, (tw, th))
        tiles.append((f'{name} ({(time.time() - t0) * 1000:.0f} ms)', y))
    cx, cy, cw, ch = crop or (tw // 2 - 320, th // 2 - 300, 640, 600)
    S = Image.new('RGB', (cw * 3, (ch + 30) * 2), (0, 0, 0))
    d = ImageDraw.Draw(S)
    font = None
    for fn in ('consola.ttf', 'DejaVuSansMono.ttf', 'Menlo.ttc'):   # a bare name: Pillow searches the system's fonts
        try:
            font = ImageFont.truetype(fn, 20)
            break
        except OSError:
            pass
    for i, (label, im) in enumerate(tiles[:6]):
        x, y = (i % 3) * cw, (i // 3) * (ch + 30)
        S.paste(Image.fromarray(im[cy:cy + ch, cx:cx + cw]), (x, y + 30))
        d.text((x + 6, y + 4), label, fill=(255, 255, 0), font=font)
    out = out or f'{ROOT}/notes/work/ab.png'
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    S.save(out)
    print('wrote', out)


def src_of(n):
    return f'{ROOT}/assets/clips_in/{n}.mp4'


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    sz = tuple(int(v) for v in opt('--size').lower().split('x')) if opt('--size') else None
    if a[0] == 'ab':
        crop = tuple(int(v) for v in opt('--crop').split(',')) if opt('--crop') else None
        ab(a[1], int(opt('--frame', 60)), opt('--out'), crop)
    elif a[0] == 'run':
        clips = [c for c in a[2:] if c.endswith('.mp4')]
        for c in clips:
            run(a[1], c, sz)
        clipsjs()
    elif a[0] in ('picks', 'raw'):
        name = opt('--model', 'animevideov3')
        if a[0] == 'picks':
            with open(f'{ROOT}/notes/clips/PICKS.txt', encoding='utf-8') as fh:
                names = [n for n in (l.split('#')[0].strip() for l in fh) if n]
        else:
            skip = set(FILM.get('clipSkip', []))
            D = f'{ROOT}/assets/clips'
            names = sorted(n for n in (os.listdir(D) if os.path.isdir(D) else [])
                           if os.path.exists(f'{D}/{n}/.raw') and n not in skip)
        done = 0
        for n in names:
            d = f'{ROOT}/assets/clips/{n}'
            upscaled = os.path.exists(f'{d}/00000.jpg') and not os.path.exists(f'{d}/.raw')
            if a[0] == 'picks' and upscaled and '--force' not in a:
                continue
            if not os.path.exists(src_of(n)):
                print('MISSING', src_of(n), flush=True)
                continue
            done += bool(run(name, src_of(n), sz))
        clipsjs()
        print(f'{a[0]}: {done} clips upscaled ({name})', flush=True)
    else:
        sys.exit(__doc__)
